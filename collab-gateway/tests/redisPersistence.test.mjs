/**
 * Redis 会话持久化单元测试
 *
 * 覆盖不依赖真实 Redis 的部分: URL 解析 + Y.Doc 快照存取适配器
 * (用假 redis 客户端, 校验 key 前缀与二进制读写契约)。
 */
import { describe, expect, it, vi } from "vitest";

import { createRedisStorage, resolveRedisUrl, DEFAULT_KEY_PREFIX } from "../redisPersistence.mjs";

function makeFakeRedis() {
  return {
    values: new Map(),
    async getBuffer(key) {
      return this.values.get(key) ?? null;
    },
    async set(key, value) {
      this.values.set(key, value);
    },
  };
}

describe("resolveRedisUrl", () => {
  it("显式传入优先", () => {
    expect(resolveRedisUrl("redis://explicit:6379/1", { REDIS_URL: "redis://env:6379" })).toBe(
      "redis://explicit:6379/1"
    );
  });

  it("回退到 REDIS_URL 环境变量, 并去除空白", () => {
    expect(resolveRedisUrl(undefined, { REDIS_URL: "  redis://env:6379/0  " })).toBe(
      "redis://env:6379/0"
    );
  });

  it("未配置返回 null", () => {
    expect(resolveRedisUrl(undefined, {})).toBeNull();
    expect(resolveRedisUrl("   ", {})).toBeNull();
  });
});

describe("createRedisStorage", () => {
  it("store 以带前缀的 key 写入 Y.Doc 二进制快照", async () => {
    const redis = makeFakeRedis();
    const storage = createRedisStorage(redis);
    const state = new Uint8Array([1, 2, 3]);
    await storage.store({ documentName: "repo:main:a.py", state });

    const stored = redis.values.get(`${DEFAULT_KEY_PREFIX}repo:main:a.py`);
    expect(Buffer.isBuffer(stored)).toBe(true);
    expect([...stored]).toEqual([1, 2, 3]);
  });

  it("fetch 命中返回快照, 未命中返回 null", async () => {
    const redis = makeFakeRedis();
    const storage = createRedisStorage(redis);
    redis.values.set(`${DEFAULT_KEY_PREFIX}doc-a`, Buffer.from([9, 8]));

    expect([...(await storage.fetch({ documentName: "doc-a" }))]).toEqual([9, 8]);
    expect(await storage.fetch({ documentName: "missing" })).toBeNull();
  });

  it("支持自定义 key 前缀", async () => {
    const redis = makeFakeRedis();
    const storage = createRedisStorage(redis, { prefix: "custom:" });
    await storage.store({ documentName: "d", state: new Uint8Array([7]) });
    expect(redis.values.has("custom:d")).toBe(true);
  });

  it("store 将 Y.Doc 快照原样传递 (encodeStateAsUpdate 输入兼容)", async () => {
    const redis = makeFakeRedis();
    const spy = vi.spyOn(redis, "set");
    const storage = createRedisStorage(redis);
    const state = new Uint8Array([0, 255]);
    await storage.store({ documentName: "x", state });
    expect(spy).toHaveBeenCalledTimes(1);
    expect(spy.mock.calls[0][0]).toBe(`${DEFAULT_KEY_PREFIX}x`);
  });
});
