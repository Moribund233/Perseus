#!/usr/bin/env python3
"""F-204 协作编辑端到端冒烟测试 (在 perseus-app 容器内运行)

验证链路: 登录 -> 建仓 -> 提交文件 -> 双 WS 连接协作编辑
(join / init / push 广播 / reject 重发 / cursor / save -> Git)

用法:
    docker exec perseus-app python /tmp/smoke_collab.py
"""
import asyncio
import json
import os
import sys
import urllib.request

import httpx
import websockets

BASE = "http://localhost:8000"
API = f"{BASE}/api/v1"


def login() -> str:
    password = os.environ["SMOKE_ADMIN_PASSWORD"]
    req = urllib.request.Request(
        f"{API}/auth/login",
        data=json.dumps({"username": "admin", "password": password}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())["token"]


def api(token: str, method: str, path: str, payload=None):
    req = urllib.request.Request(
        f"{API}{path}",
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
        method=method,
    )
    with urllib.request.urlopen(req) as resp:
        body = resp.read()
        return json.loads(body) if body else {}


async def recv(ws, want_type, timeout=5.0):
    """接收直到出现指定 type 的消息 (跳过心跳等)"""
    while True:
        raw = await asyncio.wait_for(ws.recv(), timeout)
        msg = json.loads(raw)
        if msg.get("type") == want_type:
            return msg
        if msg.get("type") == "error":
            raise AssertionError(f"unexpected error: {msg}")


async def main() -> int:
    # 等待应用就绪
    for _ in range(30):
        try:
            await asyncio.to_thread(urllib.request.urlopen, f"{BASE}/health")
            break
        except Exception:
            await asyncio.sleep(1)
    token = login()
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(base_url=BASE) as http:
        repo_name = f"collab-smoke-{int(asyncio.get_event_loop().time() * 1000)}"
        r = await http.post(f"{API}/repositories", json={"name": repo_name}, headers=headers)
        r.raise_for_status()
        repo = r.json()
        repo_id, branch = repo["id"], repo.get("default_branch") or "master"
        print(f"[1] repo created {repo_id} branch={branch}")

        r = await http.put(
            f"{API}/repositories/{repo_id}/contents/smoke.txt",
            json={"content": "hello world", "branch": branch},
            headers=headers,
        )
        r.raise_for_status()
        print("[2] file committed")

        doc_key = f"{repo_id}:{branch}:smoke.txt"
        uri = f"ws://localhost:8000/ws/collab?token={token}"

        async with websockets.connect(uri) as ws1, websockets.connect(uri) as ws2:
            for ws, cid in ((ws1, "cli-a"), (ws2, "cli-b")):
                await ws.send(json.dumps({
                    "type": "collab_join", "repository_id": repo_id,
                    "branch": branch, "path": "smoke.txt", "clientID": cid,
                }))
            init1 = await recv(ws1, "collab_init")
            init2 = await recv(ws2, "collab_init")
            assert init1["doc"] == "hello world" and init1["version"] == 0, init1
            # ws1 先加入 (init 只有自己), ws2 加入时 init 已含双方, ws1 另收 peer_joined
            assert init2["doc"] == "hello world" and len(init2["participants"]) == 2, init2
            joined = await recv(ws1, "collab_peer_joined")
            assert joined["clientID"] == "cli-b", joined
            print("[3] both joined, authoritative doc ok")

            # A 推送: 末尾追加 "!" (部件: 未修改11 + [0,"!"])
            await ws1.send(json.dumps({
                "type": "collab_push", "docKey": doc_key,
                "version": 0, "changes": [[11, [0, "!"]]], "clientID": "cli-a",
            }))
            up_a = await recv(ws1, "collab_update")
            up_b = await recv(ws2, "collab_update")
            assert up_a["clientID"] == "cli-a" and up_a["version"] == 1
            assert up_b["clientID"] == "cli-a" and up_b["version"] == 1
            print("[4] push broadcast ok")

            # B 基于过期版本推送 -> reject, 按自身意图基于新版本重发
            # changeset: 部件 [0, "B:"] = 在 0 处插入 "B:"; changes 为变更集数组
            await ws2.send(json.dumps({
                "type": "collab_push", "docKey": doc_key,
                "version": 0, "changes": [[[0, "B:"]]], "clientID": "cli-b",
            }))
            reject = await recv(ws2, "collab_reject")
            assert reject["version"] == 1 and reject["changes"], reject
            await ws2.send(json.dumps({
                "type": "collab_push", "docKey": doc_key,
                "version": reject["version"], "changes": [[[0, "B:"]]], "clientID": "cli-b",
            }))
            up_b2 = await recv(ws2, "collab_update")
            assert up_b2["version"] == 2, up_b2
            print("[5] stale push rejected & resent ok")

            # A 收光标
            await ws2.send(json.dumps({
                "type": "collab_cursor", "docKey": doc_key,
                "anchor": 4, "head": 4, "version": 2,
            }))
            cur = await recv(ws1, "collab_cursor")
            assert cur["clientID"] == "cli-b" and cur["anchor"] == 4, cur
            print("[6] cursor broadcast ok")

            # A 触发协作保存 -> 双方收到 collab_saved, Git 中内容为权威文本
            await ws1.send(json.dumps({
                "type": "collab_save", "docKey": doc_key, "message": "collab smoke edit",
            }))
            saved_a = await recv(ws1, "collab_save_ack")
            saved_b = await recv(ws2, "collab_saved")
            assert saved_a["saved_by"] == "admin" and saved_b["commit_id"], (saved_a, saved_b)
            print("[7] collab save ok, commit:", saved_a["commit_id"][:7])

            r = await http.get(
                f"{API}/repositories/{repo_id}/blob",
                params={"path": "smoke.txt", "ref": branch},
                headers=headers,
            )
            content = r.json()["content"]
            assert content == "B:hello world!", content
            print(f"[8] git content verified: {content!r}")

        # 清理冒烟仓库
        await http.delete(f"{API}/repositories/{repo_id}", headers=headers)
        print("[9] repo cleaned up")

    print("SMOKE OK")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
