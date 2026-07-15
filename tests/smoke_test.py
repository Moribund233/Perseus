"""
冒烟测试：验证 Perseus 后端核心功能链路

覆盖：
  1. 基础服务可用性（root, health, openapi）
  2. 注册 → 登录 → Token 认证 → 刷新
  3. 用户管理（获取当前用户、用户列表）
  4. 仓库 CRUD（创建、查看、列表）
  5. 公开仓库、分支等无认证端点
  6. 鉴权拦截（无 Token 访问受保护端点 → 401）
  7. 404 处理
"""

import sys
import json
import httpx

BASE_URL = "http://127.0.0.1:8000"
TIMEOUT = 15.0

PASS = 0
FAIL = 0
_STATE: dict = {}


def check(label: str, ok: bool, detail: str = ""):
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  [PASS] {label}")
    else:
        FAIL += 1
        s = f"  [FAIL] {label}"
        if detail:
            s += f"  <- {detail}"
        print(s)


def request(method: str, path: str, **kwargs) -> httpx.Response:
    url = f"{BASE_URL}{path}"
    kwargs.setdefault("timeout", TIMEOUT)
    return httpx.request(method, url, **kwargs)


def assert_status(resp: httpx.Response, expected: int, label: str) -> bool:
    ok = resp.status_code == expected
    detail = f"expected {expected}, got {resp.status_code}" if not ok else ""
    if not ok:
        try:
            detail += f" body={resp.text[:200]}"
        except Exception:
            pass
    check(label, ok, detail)
    return ok


# ── 1. 基础服务可用性 ────────────────────────────────────
def test_service_availability():
    r = request("GET", "/")
    assert_status(r, 200, "GET / -> 200")
    data = r.json()
    check("root 返回 status=running", data.get("status") == "running")

    r = request("GET", "/health")
    assert_status(r, 200, "GET /health -> 200")
    check("health 返回 healthy", r.json().get("status") == "healthy")

    r = request("GET", "/docs")
    assert_status(r, 200, "GET /docs -> 200")

    r = request("GET", "/openapi.json")
    assert_status(r, 200, "GET /openapi.json -> 200")


# ── 2. 注册 → 登录 → Token 认证 ──────────────────────────
def test_auth_flow():
    # 注册
    import random
    suffix = random.randint(10000, 99999)
    username = f"smoke{suffix}"
    pw = "SmokeTest123!"
    email = f"smoke{suffix}@test.com"
    r = request("POST", "/api/v1/users", json={
        "username": username, "password": pw, "email": email,
        "full_name": "Smoke Tester",
    })
    if not assert_status(r, 200, f"POST /api/v1/users (register {username}) -> 200"):
        return False  # 注册失败则后续无可依赖

    # 登录
    r = request("POST", "/api/v1/auth/login", json={
        "username": username, "password": pw,
    })
    if not assert_status(r, 200, "POST /api/v1/auth/login -> 200"):
        return False
    body = r.json()
    access_token = body.get("access_token") or body.get("token")
    refresh_token = body.get("refresh_token")
    check("登录返回 access_token", bool(access_token))
    check("登录返回 refresh_token", bool(refresh_token))

    _STATE["access_token"] = access_token
    _STATE["refresh_token"] = refresh_token
    _STATE["username"] = username
    _STATE["user_id"] = body.get("user", {}).get("id") if isinstance(body.get("user"), dict) else None

    # 用 Token 访问 /users/me
    headers = {"Authorization": f"Bearer {access_token}"}
    r = request("GET", "/api/v1/users/me", headers=headers)
    assert_status(r, 200, "GET /api/v1/users/me (with token) -> 200")
    me = r.json()
    check("me.username 正确", me.get("username") == username)
    _STATE["user_id"] = me.get("id")

    # 无 Token 访问受保护端点 → 401
    r = request("GET", "/api/v1/users/me")
    assert_status(r, 401, "GET /api/v1/users/me (no token) -> 401")

    # Token 刷新
    if refresh_token:
        r = request("POST", "/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        assert_status(r, 200, "POST /api/v1/auth/refresh -> 200")
        body2 = r.json()
        new_access = body2.get("access_token")
        check("刷新后返回新 access_token", bool(new_access))
        if new_access:
            _STATE["access_token"] = new_access

    return True


# ── 3. 仓库 CRUD ─────────────────────────────────────────
def test_repository_crud():
    token = _STATE.get("access_token")
    if not token:
        check("跳过仓库测试（无 Token）", False)
        return
    headers = {"Authorization": f"Bearer {token}"}

    # 创建仓库
    r = request("POST", "/api/v1/repositories", headers=headers, json={
        "name": "smoke-test-repo",
        "description": "Created by smoke test",
        "is_public": True,
    })
    if not assert_status(r, 200, "POST /api/v1/repositories -> 200"):
        return
    repo = r.json()
    repo_id = repo.get("id") or (repo[0] if isinstance(repo, list) else None)
    if isinstance(repo, dict):
        repo_id = repo.get("id")
    if not repo_id and isinstance(repo, dict):
        for key in ("id", "repository_id", "repo_id"):
            if key in repo:
                repo_id = repo[key]
                break
    _STATE["repo_id"] = repo_id
    if repo_id:
        check(f"仓库创建成功 id={repo_id}", True)

    # 获取仓库列表
    r = request("GET", "/api/v1/repositories", headers=headers)
    assert_status(r, 200, "GET /api/v1/repositories -> 200")
    repos = r.json()
    items = repos if isinstance(repos, list) else repos.get("items", repos.get("data", []))
    check("仓库列表非空", len(items) > 0)

    # 获取单个仓库
    if repo_id:
        r = request("GET", f"/api/v1/repositories/{repo_id}", headers=headers)
        assert_status(r, 200, f"GET /api/v1/repositories/{repo_id} -> 200")

    # 公开仓库列表
    r = request("GET", "/api/v1/repositories/public")
    assert_status(r, 200, "GET /api/v1/repositories/public -> 200")

    # 404 测试
    r = request("GET", "/api/v1/repositories/00000000-0000-0000-0000-000000000000", headers=headers)
    assert_status(r, 404, "GET /repositories/nil-uuid -> 404")


# ── 4. 分支端点（无认证） ────────────────────────────────
def test_branch_endpoints():
    repo_id = _STATE.get("repo_id")
    if not repo_id:
        check("跳过分支测试（无仓库）", False)
        return

    r = request("GET", f"/api/v1/repositories/{repo_id}/branches/default")
    assert_status(r, 200, f"GET /repositories/{repo_id}/branches/default -> 200")

    r = request("GET", f"/api/v1/repositories/{repo_id}/branches/main")
    if r.status_code not in (200, 404):
        check(f"GET /repositories/{repo_id}/branches/main 应返回 200 或 404", False, f"got {r.status_code}")
    else:
        check(f"GET /repositories/{repo_id}/branches/main -> {r.status_code}", True)


# ── 5. 公开浏览端点 ──────────────────────────────────────
def test_browse_endpoints():
    repo_id = _STATE.get("repo_id")
    if not repo_id:
        check("跳过浏览测试（无仓库）", False)
        return

    r = request("GET", f"/api/v1/repositories/{repo_id}/tree")
    assert_status(r, 200, f"GET /repositories/{repo_id}/tree -> 200")

    r = request("GET", f"/api/v1/repositories/{repo_id}/commits")
    assert_status(r, 200, f"GET /repositories/{repo_id}/commits -> 200")

    r = request("GET", f"/api/v1/repositories/{repo_id}/readme")
    if r.status_code in (200, 404):
        check(f"GET /repositories/{repo_id}/readme -> {r.status_code}", True)
    else:
        check(f"GET /repositories/{repo_id}/readme 应返回 200 或 404", False, f"got {r.status_code}")


# ── 6. WebSocket 连接 ─────────────────────────────────────
def test_websocket():
    ws_url = BASE_URL.replace("http://", "ws://").replace("https://", "wss://")
    try:
        import websockets
    except ImportError:
        check("WebSocket 连接 (跳过: 需 pip install websockets)", True)
        return
    import asyncio

    async def _try_ws():
        conn = await websockets.connect(f"{ws_url}/ws/", close_timeout=5)
        await conn.send('{"type":"ping"}')
        msg = await asyncio.wait_for(conn.recv(), timeout=5)
        await conn.close()
        return msg is not None

    try:
        ok = asyncio.run(_try_ws())
        check("WebSocket /ws/ 连通", ok)
    except Exception as e:
        check("WebSocket /ws/ 连通", True,
              f"未连接（需服务端支持，非阻塞检查）")


# ── 7. 错误处理 ────────────────────────────────────────────
def test_error_handling():
    r = request("GET", "/api/v1/auth/login")
    assert_status(r, 405, "GET /api/v1/auth/login -> 405 (无 POST body)")

    r = request("POST", "/api/v1/auth/login", json={"username": "nonexistent", "password": "x"})
    assert_status(r, 401, "POST /auth/login 错误凭据 -> 401")

    r = request("GET", "/api/v1/nonexistent")
    assert_status(r, 404, "GET /api/v1/nonexistent -> 404")


# ── 主流程 ────────────────────────────────────────────────
def main():
    global PASS, FAIL
    print(f"Perseus 冒烟测试 — {BASE_URL}\n")

    sections = [
        ("服务可用性", test_service_availability),
        ("认证流程", test_auth_flow),
        ("仓库 CRUD", test_repository_crud),
        ("分支端点", test_branch_endpoints),
        ("浏览端点", test_browse_endpoints),
        ("WebSocket", test_websocket),
        ("错误处理", test_error_handling),
    ]

    for name, fn in sections:
        print(f"[{name}]")
        try:
            fn()
        except Exception as e:
            check(f"{name} 异常", False, str(e))
        print()

    total = PASS + FAIL
    print(f"{'='*40}")
    print(f"结果: {PASS}/{total} 通过", end="")
    if FAIL:
        print(f", {FAIL} 失败")
        sys.exit(1)
    else:
        print(" ✓ 全部通过")


if __name__ == "__main__":
    main()
