/**
 * collab-gateway 集成测试
 *
 * 真实 Hocuspocus server (随机端口) + @hocuspocus/provider 客户端;
 * app 回调 (fetch) 全部 mock, 校验网关与 app 的契约:
 *   auth 契约 / 文档种子 / 双端 CRDT 同步 / 只读拒绝 / 显式保存广播
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  appMock,
  AUTH_OK_READER,
  AUTH_OK_WRITER,
  DOC,
  installAppMock,
  makeProvider,
  waitFor,
} from "./support.mjs";

const SECRET = "test-internal-secret";

installAppMock();

process.env.PERSEUS_COLLAB_INTERNAL_SECRET = SECRET;
process.env.PERSEUS_APP_URL = "http://app.test:8000";
// 本文件为无外部依赖的集成测试: 显式禁用 Redis, 避免宿主环境变量串入
delete process.env.REDIS_URL;
delete process.env.PERSEUS_COLLAB_REDIS_URL;

const { startGateway } = await import("../server.mjs");

describe("collab-gateway", () => {
  let gw;

  beforeEach(async () => {
    appMock.reset({
      "POST /api/v1/collab/auth": (body) =>
        body?.token === "writer-token" ? AUTH_OK_WRITER : AUTH_OK_READER,
      "GET /api/v1/collab/doc": { status: 200, data: { content: "hello", branch: "main", path: "src/app.py" } },
      "POST /api/v1/collab/save": { status: 200, data: { commit_id: "abc1234", saved_by: "alice", message: "save", branch: "main", path: "src/app.py" } },
    });
    gw = await startGateway();
  });

  afterEach(async () => {
    await gw?.close();
    vi.clearAllMocks();
  });

  it("文档以 app 返回的内容为种子, 且两个客户端完成 CRDT 同步", async () => {
    const a = makeProvider(gw.port, DOC, "writer-token", { name: "alice" });
    const b = makeProvider(gw.port, DOC, "reader-token", { name: "bob" });

    await waitFor(() => a.document && b.document, "documents created");
    await waitFor(
      () =>
        a.document.getText("content").toString() === "hello" &&
        b.document.getText("content").toString() === "hello",
      "seed content synced"
    );

    // 写端编辑 → 读端收敛
    a.document.getText("content").insert(5, " world");
    await waitFor(() => b.document.getText("content").toString() === "hello world", "edit propagated");
    a.destroy();
    b.destroy();
  });

  it("只读客户端的编辑不会传播给其他端 (服务端 readOnly 强制)", async () => {
    const writer = makeProvider(gw.port, DOC, "writer-token", { name: "alice" });
    const reader = makeProvider(gw.port, DOC, "reader-token", { name: "bob" });

    await waitFor(
      () => writer.document?.getText("content").toString() === "hello",
      "writer synced"
    );
    // bob 是 viewer → readOnly; 本地编辑应被服务端拒绝
    reader.document.getText("content").insert(0, "HACKED ");
    await new Promise((r) => setTimeout(r, 300));
    expect(writer.document.getText("content").toString()).toBe("hello");
    writer.destroy();
    reader.destroy();
  });

  it("显式保存: stateless 消息触发 /collab/save, 全员收到 collab-saved 广播", async () => {
    const a = makeProvider(gw.port, DOC, "writer-token", { name: "alice" });
    await waitFor(() => a.document?.getText("content").toString() === "hello", "synced");

    a.document.getText("content").insert(5, "!");
    await waitFor(() => a.document.getText("content").toString() === "hello!", "edit applied");

    const savedPromise = new Promise((resolve) => a.on("stateless", ({ payload }) => {
      const msg = JSON.parse(payload);
      if (msg.type === "collab-saved") resolve(msg);
    }));

    a.sendStateless(JSON.stringify({ type: "collab-save", message: "collab save" }));

    const saved = await savedPromise;
    expect(saved.commit_id).toBe("abc1234");
    expect(saved.docKey).toBe(DOC);
    // 收紧后广播仅含提交标识, 不泄漏 saved_by/message/branch/path
    expect(saved.saved_by).toBeUndefined();

    const saveCall = appMock.calls.find((c) => c.path === "/api/v1/collab/save");
    expect(saveCall).toBeTruthy();
    expect(saveCall.body.content).toBe("hello!");
    expect(saveCall.body.token).toBe("writer-token");
    expect(saveCall.body.docKey).toBe(DOC);
    // 内部密钥头随调用传递
    const authHeader = vi.mocked(fetch).mock.calls.at(-1)[1].headers["X-Collab-Internal-Secret"];
    expect(authHeader).toBe(SECRET);
    a.destroy();
  });

  it("只读客户端请求保存: 不调用 app, 收到 collab-save-error", async () => {
    const reader = makeProvider(gw.port, DOC, "reader-token", { name: "bob" });
    await waitFor(() => reader.document?.getText("content").toString() === "hello", "synced");

    const errPromise = new Promise((resolve) => reader.on("stateless", ({ payload }) => {
      const msg = JSON.parse(payload);
      if (msg.type === "collab-save-error") resolve(msg);
    }));

    reader.sendStateless(JSON.stringify({ type: "collab-save", message: "nope" }));
    const err = await errPromise;
    expect(err.error).toContain("写入权限");
    expect(appMock.calls.some((c) => c.path === "/api/v1/collab/save")).toBe(false);
    reader.destroy();
  });

  it("无效 token: 认证失败, 连接被拒绝", async () => {
    appMock.reset({
      "POST /api/v1/collab/auth": { status: 401, data: { detail: "无效或过期的 token" } },
    });
    const failed = new Promise((resolve) => {
      const p = makeProvider(gw.port, DOC, "bad-token", { name: "eve" });
      p.on("authenticationFailed", ({ reason }) => resolve({ p, reason }));
    });
    const { p, reason } = await failed;
    expect(reason).toContain("token");
    p.destroy();
  });

  it("邀请链接访客: JSON token 中的 invite_token 透传给 auth 与 save", async () => {
    const a = makeProvider(
      gw.port,
      DOC,
      JSON.stringify({ access_token: "writer-token", invite_token: "invite-abc" }),
      { name: "guest" }
    );
    await waitFor(() => a.document?.getText("content").toString() === "hello", "synced");

    const authCall = appMock.calls.find((c) => c.path === "/api/v1/collab/auth");
    expect(authCall.body.token).toBe("writer-token");
    expect(authCall.body.invite_token).toBe("invite-abc");

    const savedPromise = new Promise((resolve) => a.on("stateless", ({ payload }) => {
      const msg = JSON.parse(payload);
      if (msg.type === "collab-saved") resolve(msg);
    }));
    a.sendStateless(JSON.stringify({ type: "collab-save", message: "guest save" }));
    await savedPromise;

    const saveCall = appMock.calls.find((c) => c.path === "/api/v1/collab/save");
    expect(saveCall.body.token).toBe("writer-token");
    expect(saveCall.body.invite_token).toBe("invite-abc");
    a.destroy();
  });

  it("会话 TTL: 窗口内重连复用内存现场, 不重新向 app 加载", async () => {
    const a = makeProvider(gw.port, DOC, "writer-token", { name: "alice" });
    await waitFor(() => a.document?.getText("content").toString() === "hello", "synced");
    a.document.getText("content").insert(5, " warm");
    await waitFor(() => a.document.getText("content").toString() === "hello warm", "edit applied");
    a.destroy();

    await waitFor(() => gw.sessionTtl.heldDocuments().includes(DOC), "doc kept warm");
    expect(gw.hocuspocus.getDocumentsCount()).toBe(1);

    const b = makeProvider(gw.port, DOC, "writer-token", { name: "alice" });
    await waitFor(() => b.document?.getText("content").toString() === "hello warm", "warm doc reused");
    expect(appMock.calls.filter((c) => c.path === "/api/v1/collab/doc")).toHaveLength(1);
    b.destroy();
  });

  it("会话 TTL: 到期后卸载, 重连重新从 app 加载播种", async () => {
    await gw.close();
    gw = await startGateway({ sessionTtlMs: 120 });

    const a = makeProvider(gw.port, DOC, "writer-token", { name: "alice" });
    await waitFor(() => a.document?.getText("content").toString() === "hello", "synced");
    a.document.getText("content").insert(5, " stale");
    await waitFor(() => a.document.getText("content").toString() === "hello stale", "edit applied");
    a.destroy();

    await waitFor(() => gw.hocuspocus.getDocumentsCount() === 0, "doc unloaded after TTL");
    expect(gw.sessionTtl.heldDocuments()).toHaveLength(0);

    const b = makeProvider(gw.port, DOC, "writer-token", { name: "alice" });
    await waitFor(() => b.document?.getText("content").toString() === "hello", "reloaded from app");
    expect(appMock.calls.filter((c) => c.path === "/api/v1/collab/doc")).toHaveLength(2);
    b.destroy();
  });

  it("会话 TTL=0: 禁用保留, 断开即卸载", async () => {
    await gw.close();
    gw = await startGateway({ sessionTtlMs: 0 });

    const a = makeProvider(gw.port, DOC, "writer-token", { name: "alice" });
    await waitFor(() => a.document?.getText("content").toString() === "hello", "synced");
    a.destroy();

    await waitFor(() => gw.hocuspocus.getDocumentsCount() === 0, "doc unloaded immediately");
    expect(gw.sessionTtl.heldDocuments()).toHaveLength(0);
  });
});
