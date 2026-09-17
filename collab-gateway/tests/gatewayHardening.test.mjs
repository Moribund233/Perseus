/**
 * collab-gateway 收紧 (multi-replica bugfix) 集成测试
 *
 * 三个安全/容量缺口:
 *   2a  collab-saved 广播私密性: 只向订阅者确认 commit_id+docKey,
 *       不泄漏 saved_by/branch/path/message 等保存元数据。
 *   2b  容量上限: 种子内容超过 maxContentChars 拒绝文档加载 (413);
 *       保存内容超过 maxContentChars 不得调用 app (collab-save-error);
 *       每文档并发连接超过 maxConnectionsPerDoc 拒绝新连接。
 *   2d  权限即时性网关侧: app 对保存回 403 = 写入权限已吊销,
 *       网关断开该连接强制重认证 (多副本即时吊销)。
 */
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import {
  appMock,
  AUTH_OK_WRITER,
  AUTH_OK_READER,
  DOC,
  freePort,
  installAppMock,
  makeProvider,
  waitFor,
} from "./support.mjs";

const SECRET = "test-internal-secret";

installAppMock();

process.env.PERSEUS_COLLAB_INTERNAL_SECRET = SECRET;
process.env.PERSEUS_APP_URL = "http://app.test:8000";
delete process.env.REDIS_URL;
delete process.env.PERSEUS_COLLAB_REDIS_URL;

const { startGateway } = await import("../server.mjs");

const longText = (len) => "x".repeat(len);

describe("collab-gateway 收紧", () => {
  let gw;

  const seedDoc = async (provider) => {
    await waitFor(
      () => provider.document?.getText("content").toString() === "hello",
      "seed synced"
    );
    return provider;
  };

  const startHardenedGateway = async (overrides = {}) =>
    startGateway({
      port: await freePort(),
      healthPort: await freePort(),
      ...overrides,
    });

  beforeEach(() => {
    appMock.reset({
      "POST /api/v1/collab/auth": (body) =>
        body?.token === "writer-token" ? AUTH_OK_WRITER : AUTH_OK_READER,
      "GET /api/v1/collab/doc": { status: 200, data: { content: "hello", branch: "main", path: "src/app.py" } },
      "POST /api/v1/collab/save": { status: 200, data: { commit_id: "abc1234", saved_by: "alice", message: "save", branch: "main", path: "src/app.py" } },
    });
  });

  afterEach(async () => {
    await gw?.close();
    gw = null;
  });

  it("2a: collab-saved 广播不泄漏保存元数据 (仅 commit_id + docKey)", async () => {
    gw = await startHardenedGateway();

    const a = makeProvider(gw.port, DOC, "writer-token", { name: "alice" });
    await seedDoc(a);
    a.document.getText("content").insert(5, "!");

    const savedPromise = new Promise((resolve) =>
      a.on("stateless", ({ payload }) => {
        const msg = JSON.parse(payload);
        if (msg.type === "collab-saved") resolve(msg);
      })
    );

    a.sendStateless(JSON.stringify({ type: "collab-save", message: "collab save" }));
    const saved = await savedPromise;

    expect(saved.docKey).toBe(DOC);
    expect(saved.commit_id).toBe("abc1234");
    // 私密性: 以下元数据不得广播给文档全部订阅者
    expect(saved.saved_by).toBeUndefined();
    expect(saved.branch).toBeUndefined();
    expect(saved.path).toBeUndefined();
    expect(saved.message).toBeUndefined();
    a.destroy();
  });

  it("2b: 种子内容超过 maxContentChars, 文档加载被拒 (413)", async () => {
    appMock.reset({
      "POST /api/v1/collab/auth": AUTH_OK_WRITER,
      "GET /api/v1/collab/doc": { status: 200, data: { content: longText(256), branch: "main", path: "src/app.py" } },
    });
    gw = await startHardenedGateway({ maxContentChars: 64 });

    const { p, reason } = await new Promise((resolve) => {
      const provider = makeProvider(gw.port, DOC, "writer-token", { name: "alice" });
      provider.on("authenticationFailed", ({ reason }) => resolve({ p: provider, reason }));
      provider.on("close", ({ event }) => resolve({ p: provider, reason: event?.reason || "" }));
    });
    expect(reason).toMatch(/413|过大|太大/i);
    p.destroy();
  });

  it("2b: 保存内容超过 maxContentChars, 不调用 app, 收到 collab-save-error", async () => {
    gw = await startHardenedGateway({ maxContentChars: 64 });

    const a = makeProvider(gw.port, DOC, "writer-token", { name: "alice" });
    await seedDoc(a);
    a.document.getText("content").insert(5, longText(128));

    const errPromise = new Promise((resolve) =>
      a.on("stateless", ({ payload }) => {
        const msg = JSON.parse(payload);
        if (msg.type === "collab-save-error") resolve(msg);
      })
    );

    a.sendStateless(JSON.stringify({ type: "collab-save", message: "too big" }));
    const err = await errPromise;
    expect(err.error).toMatch(/过大|太大/i);
    expect(appMock.calls.some((c) => c.path === "/api/v1/collab/save")).toBe(false);
    a.destroy();
  });

  it("2b: 每文档并发连接超过 maxConnectionsPerDoc, 新连接被拒", async () => {
    gw = await startHardenedGateway({ maxConnectionsPerDoc: 2 });

    const a = makeProvider(gw.port, DOC, "writer-token", { name: "alice" });
    const b = makeProvider(gw.port, DOC, "writer-token", { name: "alice" });
    await seedDoc(a);
    await seedDoc(b);

    const denied = await new Promise((resolve) => {
      const p = makeProvider(gw.port, DOC, "writer-token", { name: "alice" });
      p.on("authenticationFailed", ({ reason }) => resolve({ p, reason }));
      p.on("close", ({ event }) => resolve({ p, reason: event?.reason || "" }));
    });
    expect(denied.reason).toMatch(/连接|上限|limit|429/i);
    denied.p.destroy();
    a.destroy();
    b.destroy();
  });

  it("2d: 保存被 app 回 403 (权限吊销) → 断开该连接强制重认证", async () => {
    appMock.reset({
      "POST /api/v1/collab/auth": (body) =>
        body?.token === "writer-token" ? AUTH_OK_WRITER : AUTH_OK_READER,
      "GET /api/v1/collab/doc": { status: 200, data: { content: "hello", branch: "main", path: "src/app.py" } },
      "POST /api/v1/collab/save": { status: 403, data: { detail: "写入权限已吊销" } },
    });
    gw = await startHardenedGateway();

    const a = makeProvider(gw.port, DOC, "writer-token", { name: "alice" });
    await seedDoc(a);
    a.document.getText("content").insert(5, "!");

    const errPromise = new Promise((resolve) =>
      a.on("stateless", ({ payload }) => {
        const msg = JSON.parse(payload);
        if (msg.type === "collab-save-error") resolve(msg);
      })
    );
    const closeProbe = new Promise((resolve) =>
      a.on("close", ({ event }) => resolve(event?.reason || ""))
    );

    a.sendStateless(JSON.stringify({ type: "collab-save", message: "revoked" }));
    const err = await errPromise;
    expect(err.error).toContain("写入权限已吊销");

    // 网关必须断开该连接, 而非继续以陈旧权限提供读服务
    const closeReason = await closeProbe;
    expect(closeReason).toMatch(/吊销|权限/i);
    a.destroy();
  });
});