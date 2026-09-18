/**
 * collab-gateway 跟随模式 (Follow me) 集成测试
 *
 * 协议 (见 docs/api/websocket/README.md 第 7 节):
 *   - 感知层扩展: awareness 的 viewport(视口锚点) / follow(被跟随 clientID) 字段,
 *     由网关 beforeHandleAwareness 盖章与校验, 跟随关系由客户端从感知状态派生。
 *   - "跟我来"信令: stateless collab-spotlight, 仅写权限者可发起, 全员广播;
 *     发起者断开时网关广播 on=false。
 *
 * 覆盖:
 *   1. 服务端盖章 user (防冒名, 保留展示字段)
 *   2. viewport / follow 合法字段透传
 *   3. 非法 viewport / follow 被剔除
 *   4. awareness 超限时白名单外字段被剔除, 状态仍同步
 *   5. spotlight 写者广播 / 只读者拒绝 / 断开收尾
 */
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import {
  appMock,
  AUTH_OK_READER,
  AUTH_OK_WRITER,
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

/** 在对端感知状态中按已认证 user_id 定位某协作者 */
function findPeer(provider, userId) {
  for (const state of provider.awareness.getStates().values()) {
    if (state?.user?.user_id === userId) return state;
  }
  return null;
}

/** 收集 provider 收到的 stateless 消息 (解析后的对象数组) */
function collectStateless(provider) {
  const msgs = [];
  provider.on("stateless", ({ payload }) => {
    try {
      msgs.push(JSON.parse(payload));
    } catch {
      // 忽略非 JSON
    }
  });
  return msgs;
}

describe("collab-gateway 跟随模式 (Follow me)", () => {
  let gw;

  const start = async (overrides = {}) =>
    startGateway({ port: await freePort(), healthPort: await freePort(), ...overrides });

  const seed = async (provider) => {
    await waitFor(
      () => provider.document?.getText("content").toString() === "hello",
      "seed synced"
    );
    return provider;
  };

  beforeEach(() => {
    appMock.reset({
      "POST /api/v1/collab/auth": (body) =>
        body?.token === "writer-token" ? AUTH_OK_WRITER : AUTH_OK_READER,
      "GET /api/v1/collab/doc": {
        status: 200,
        data: { content: "hello", branch: "main", path: "src/app.py" },
      },
    });
  });

  afterEach(async () => {
    await gw?.close();
    gw = null;
  });

  it("服务端盖章 user: 客户端自报身份被覆盖为已认证身份, 展示字段保留", async () => {
    gw = await start();
    const a = makeProvider(gw.port, DOC, "writer-token", {});
    const b = makeProvider(gw.port, DOC, "reader-token", {});
    await seed(a);
    await seed(b);

    a.awareness.setLocalStateField("user", {
      name: "evil",
      user_id: "hacker",
      color: "#ffffff",
    });

    await waitFor(() => !!findPeer(b, "u-writer"), "stamped user propagated");
    const stamped = findPeer(b, "u-writer");
    expect(stamped.user.name).toBe("alice");
    expect(stamped.user.user_id).toBe("u-writer");
    expect(stamped.user.color).toBe("#ffffff");
    expect(findPeer(b, "hacker")).toBeNull();

    a.destroy();
    b.destroy();
  });

  it("viewport / follow 合法字段透传给对端", async () => {
    gw = await start();
    const a = makeProvider(gw.port, DOC, "writer-token", {});
    const b = makeProvider(gw.port, DOC, "reader-token", {});
    await seed(a);
    await seed(b);

    a.awareness.setLocalStateField("viewport", { anchor: 42 });
    a.awareness.setLocalStateField("follow", { target: 123 });

    await waitFor(() => {
      const s = findPeer(b, "u-writer");
      return s?.viewport?.anchor === 42 && s?.follow?.target === 123;
    }, "follow fields propagated");

    a.destroy();
    b.destroy();
  });

  it("非法 viewport / follow 被剔除, 其余感知字段仍同步", async () => {
    gw = await start();
    const a = makeProvider(gw.port, DOC, "writer-token", {});
    const b = makeProvider(gw.port, DOC, "reader-token", {});
    await seed(a);
    await seed(b);

    a.awareness.setLocalStateField("viewport", { anchor: -5 });
    a.awareness.setLocalStateField("follow", { target: "not-a-client-id" });

    await waitFor(() => !!findPeer(b, "u-writer"), "state propagated");
    await new Promise((r) => setTimeout(r, 250));

    const s = findPeer(b, "u-writer");
    expect(s.user.user_id).toBe("u-writer");
    expect(s.viewport).toBeUndefined();
    expect(s.follow).toBeUndefined();

    a.destroy();
    b.destroy();
  });

  it("awareness 超限: 白名单外字段被剔除, 状态仍同步 (不泄漏大字段)", async () => {
    gw = await start({ maxAwarenessBytes: 128 });
    const a = makeProvider(gw.port, DOC, "writer-token", {});
    const b = makeProvider(gw.port, DOC, "reader-token", {});
    await seed(a);
    await seed(b);

    a.awareness.setLocalStateField("viewport", { anchor: 1 });
    a.awareness.setLocalStateField("blob", "x".repeat(4096));

    await waitFor(() => {
      const s = findPeer(b, "u-writer");
      return !!(s && s.user && s.blob === undefined);
    }, "oversized field stripped");

    const s = findPeer(b, "u-writer");
    expect(s.viewport).toBeUndefined();
    expect(s.blob).toBeUndefined();

    a.destroy();
    b.destroy();
  });

  it("spotlight: 写权限者发起, 全员收到广播", async () => {
    gw = await start();
    const a = makeProvider(gw.port, DOC, "writer-token", {});
    const b = makeProvider(gw.port, DOC, "reader-token", {});
    await seed(a);
    await seed(b);
    const aMsgs = collectStateless(a);
    const bMsgs = collectStateless(b);

    a.sendStateless(JSON.stringify({ type: "collab-spotlight", on: true }));

    await waitFor(() => !!bMsgs.find((m) => m.type === "collab-spotlight"), "peer receives spotlight");
    const msg = bMsgs.find((m) => m.type === "collab-spotlight");
    expect(msg.on).toBe(true);
    expect(msg.from.username).toBe("alice");
    expect(msg.from.user_id).toBe("u-writer");

    // 发起者本人也收到广播 (可据此更新自身 UI 状态)
    await waitFor(() => !!aMsgs.find((m) => m.type === "collab-spotlight"), "sender receives broadcast");

    a.destroy();
    b.destroy();
  });

  it("spotlight: 只读者发起被拒, 对端不收到广播", async () => {
    gw = await start();
    const a = makeProvider(gw.port, DOC, "writer-token", {});
    const b = makeProvider(gw.port, DOC, "reader-token", {});
    await seed(a);
    await seed(b);
    const aMsgs = collectStateless(a);
    const bMsgs = collectStateless(b);

    b.sendStateless(JSON.stringify({ type: "collab-spotlight", on: true }));

    await waitFor(
      () => !!bMsgs.find((m) => m.type === "collab-spotlight-error"),
      "reader receives error"
    );
    await new Promise((r) => setTimeout(r, 250));

    expect(aMsgs.find((m) => m.type === "collab-spotlight")).toBeUndefined();
    expect(bMsgs.find((m) => m.type === "collab-spotlight")).toBeUndefined();

    a.destroy();
    b.destroy();
  });

  it("spotlight: 发起者断开后广播 on=false", async () => {
    gw = await start();
    const a = makeProvider(gw.port, DOC, "writer-token", {});
    const b = makeProvider(gw.port, DOC, "reader-token", {});
    await seed(a);
    await seed(b);
    const bMsgs = collectStateless(b);

    a.sendStateless(JSON.stringify({ type: "collab-spotlight", on: true }));
    await waitFor(
      () => !!bMsgs.find((m) => m.type === "collab-spotlight" && m.on === true),
      "spotlight started"
    );

    a.destroy();
    await waitFor(
      () => !!bMsgs.find((m) => m.type === "collab-spotlight" && m.on === false),
      "spotlight ended on disconnect"
    );

    b.destroy();
  });
});
