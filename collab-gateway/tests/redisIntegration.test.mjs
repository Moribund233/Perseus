/**
 * Redis 多副本 + 会话持久化集成测试 (需要真实 Redis)
 *
 * 运行方式: 提供 TEST_REDIS_URL 指向一个**可丢弃**的 Redis DB, 例如
 *   TEST_REDIS_URL=redis://127.0.0.1:6379/15 npm test
 * 未设置时全部 skip, 因此默认 CI/本地测试不依赖 Redis。
 *
 * DB 会被 flushdb, 切勿指向生产库。
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import RedisClient from "ioredis";

import {
  appMock,
  AUTH_OK_READER,
  AUTH_OK_WRITER,
  DOC,
  freePort,
  installAppMock,
  makeProvider,
  waitFor,
  waitForAsync,
} from "./support.mjs";
import { DEFAULT_KEY_PREFIX } from "../redisPersistence.mjs";

const REDIS_URL = process.env.TEST_REDIS_URL;
const redisIt = REDIS_URL ? it : it.skip;

installAppMock();

process.env.PERSEUS_COLLAB_INTERNAL_SECRET = "test-internal-secret";
process.env.PERSEUS_APP_URL = "http://app.test:8000";
delete process.env.REDIS_URL;
delete process.env.PERSEUS_COLLAB_REDIS_URL;

const { startGateway } = await import("../server.mjs");

const SNAPSHOT_KEY = `${DEFAULT_KEY_PREFIX}${DOC}`;

describe.skipIf(!REDIS_URL)("collab-gateway + Redis", () => {
  let admin = null;
  let gateways = [];

  const startRedisGateway = async (overrides = {}) =>
    startGateway({
      port: await freePort(),
      healthPort: await freePort(),
      redisUrl: REDIS_URL,
      createRedisClient: () => new RedisClient(REDIS_URL),
      ...overrides,
    });

  beforeEach(async () => {
    admin = new RedisClient(REDIS_URL);
    await admin.flushdb();
    appMock.reset({
      "POST /api/v1/collab/auth": (body) =>
        body?.token === "writer-token" ? AUTH_OK_WRITER : AUTH_OK_READER,
      "GET /api/v1/collab/doc": {
        status: 200,
        data: { content: "hello", branch: "main", path: "src/app.py" },
      },
      "POST /api/v1/collab/save": {
        status: 200,
        data: { commit_id: "abc1234", saved_by: "alice", message: "save", branch: "main", path: "src/app.py" },
      },
    });
    gateways = [];
  });

  afterEach(async () => {
    await Promise.all(gateways.map((gw) => gw?.close()));
    gateways = [];
    if (admin) {
      admin.disconnect();
      admin = null;
    }
    vi.clearAllMocks();
  });

  redisIt("两个副本经 Redis pub/sub 同步 CRDT 变更", async () => {
    const gw1 = await startRedisGateway();
    const gw2 = await startRedisGateway();
    gateways.push(gw1, gw2);

    const writer = makeProvider(gw1.port, DOC, "writer-token", { name: "alice" });
    await waitFor(() => writer.document?.getText("content").toString() === "hello", "writer synced");

    const reader = makeProvider(gw2.port, DOC, "reader-token", { name: "bob" });
    await waitFor(() => reader.document?.getText("content").toString() === "hello", "reader synced");

    writer.document.getText("content").insert(5, " via-redis");
    await waitFor(
      () => reader.document.getText("content").toString() === "hello via-redis",
      "cross-replica edit propagated"
    );

    writer.destroy();
    reader.destroy();
  }, 20000);

  redisIt("协作版本号跨副本持久递增: 两次保存 version=1,2 (Redis INCR)", async () => {
    const gw1 = await startRedisGateway();
    const gw2 = await startRedisGateway();
    gateways.push(gw1, gw2);

    const a = makeProvider(gw1.port, DOC, "writer-token", { name: "alice" });
    await waitFor(() => a.document?.getText("content").toString() === "hello", "synced");

    const savedOn = (provider, port) =>
      new Promise((resolve) => {
        const handler = ({ payload }) => {
          const msg = JSON.parse(payload);
          if (msg.type === "collab-saved") {
            provider.off("stateless", handler);
            resolve(msg);
          }
        };
        provider.on("stateless", handler);
        provider.sendStateless(JSON.stringify({ type: "collab-save", message: `save@${port}` }));
      });

    const first = await savedOn(a, gw1.port);
    expect(first.version).toBe(1);

    // 第二个副本上的客户端保存 → INCR 延续 (跨副本共享计数)
    const b = makeProvider(gw2.port, DOC, "writer-token", { name: "bob" });
    await waitFor(() => b.document?.getText("content").toString() === "hello", "b synced");
    const second = await savedOn(b, gw2.port);
    expect(second.version).toBe(2);

    a.destroy();
    b.destroy();
  }, 20000);

  redisIt("会话快照持久化: 网关重启后从 Redis 恢复未提交编辑, 不回源 Git", async () => {
    const gw1 = await startRedisGateway();
    gateways.push(gw1);

    const a = makeProvider(gw1.port, DOC, "writer-token", { name: "alice" });
    await waitFor(() => a.document?.getText("content").toString() === "hello", "synced");
    a.document.getText("content").insert(5, " persisted");
    await waitFor(() => a.document.getText("content").toString() === "hello persisted", "edited");
    a.destroy();

    await waitForAsync(async () => (await admin.exists(SNAPSHOT_KEY)) === 1, "snapshot stored");
    const gitLoadsBefore = appMock.calls.filter((c) => c.path === "/api/v1/collab/doc").length;
    await gw1.close();

    const gw2 = await startRedisGateway();
    gateways.push(gw2);
    const b = makeProvider(gw2.port, DOC, "writer-token", { name: "alice" });
    await waitFor(
      () => b.document?.getText("content").toString() === "hello persisted",
      "restored from snapshot"
    );
    // 恢复自快照时不应再次向 app 拉取 Git 原文 (仍为 "hello")
    expect(appMock.calls.filter((c) => c.path === "/api/v1/collab/doc")).toHaveLength(gitLoadsBefore);
    b.destroy();
  }, 20000);
});
