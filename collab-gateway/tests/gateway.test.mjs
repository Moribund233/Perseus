/**
 * collab-gateway 集成测试
 *
 * 真实 Hocuspocus server (随机端口) + @hocuspocus/provider 客户端;
 * app 回调 (fetch) 全部 mock, 校验网关与 app 的契约:
 *   auth 契约 / 文档种子 / 双端 CRDT 同步 / 只读拒绝 / 显式保存广播
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { HocuspocusProvider } from "@hocuspocus/provider";

const SECRET = "test-internal-secret";
const DOC = "11111111-1111-1111-1111-111111111111:main:src/app.py";

// app 回调路由 mock 表 (每个用例可覆盖)
const appMock = {
  responses: {},
  calls: [],
  reset(responses = {}) {
    this.responses = responses;
    this.calls = [];
  },
};

vi.stubGlobal(
  "fetch",
  vi.fn(async (url, init = {}) => {
    const path = url.replace(/^https?:\/\/[^/]+/, "").split("?")[0];
    const method = init.method || "GET";
    let body = null;
    try {
      body = JSON.parse(init.body || "null");
    } catch {
      body = init.body ?? null;
    }
    appMock.calls.push({ path, method, body, url });
    const handler = appMock.responses[`${method} ${path}`];
    if (!handler) throw new Error(`unexpected app call: ${method} ${path}`);
    const { status = 200, data = {} } = typeof handler === "function" ? handler(body) : handler;
    return new Response(JSON.stringify(data), {
      status,
      headers: { "Content-Type": "application/json" },
    });
  })
);

process.env.PERSEUS_COLLAB_INTERNAL_SECRET = SECRET;
process.env.PERSEUS_APP_URL = "http://app.test:8000";

const { startGateway } = await import("../server.mjs");

const AUTH_OK_WRITER = {
  status: 200,
  data: { user_id: "u-writer", username: "alice", can_write: true },
};
const AUTH_OK_READER = {
  status: 200,
  data: { user_id: "u-reader", username: "bob", can_write: false },
};

async function waitFor(fn, desc) {
  const start = Date.now();
  for (;;) {
    try {
      const v = fn();
      if (v !== false) return v;
    } catch {
      // 条件尚未满足
    }
    if (Date.now() - start > 5000) throw new Error(`timeout waiting: ${desc}`);
    await new Promise((r) => setTimeout(r, 25));
  }
}

function makeProvider(port, name, token, user) {
  return new HocuspocusProvider({
    url: `ws://127.0.0.1:${port}`,
    name,
    token,
    awareness: undefined,
    onAwarenessUpdate: () => {},
    user,
  });
}

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
    expect(saved.saved_by).toBe("alice");

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
});
