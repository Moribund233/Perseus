/**
 * 协作版本计数器单测: 内存回退 / Redis INCR / 失败容错
 */
import { describe, expect, it, vi } from "vitest";

import {
  createVersionCounter,
  DEFAULT_VERSION_KEY_PREFIX,
} from "../versionCounter.mjs";

describe("createVersionCounter (内存回退)", () => {
  it("连续保存按文档单调递增", async () => {
    const c = createVersionCounter({});
    expect(await c.next("repo:main:a.py")).toBe(1);
    expect(await c.next("repo:main:a.py")).toBe(2);
    expect(await c.next("repo:main:a.py")).toBe(3);
  });

  it("不同文档独立计数", async () => {
    const c = createVersionCounter({});
    await c.next("doc-a");
    await c.next("doc-a");
    expect(await c.next("doc-b")).toBe(1);
  });
});

describe("createVersionCounter (Redis INCR)", () => {
  it("优先走 redis.incr, key 带前缀, 返回其值", async () => {
    const values = new Map();
    const redis = {
      incr: vi.fn(async (k) => {
        const next = (values.get(k) || 0) + 1;
        values.set(k, next);
        return next;
      }),
    };
    const c = createVersionCounter({ redis });
    expect(await c.next("z")).toBe(1);
    expect(await c.next("z")).toBe(2);
    expect(redis.incr).toHaveBeenCalledWith(`${DEFAULT_VERSION_KEY_PREFIX}z`);
  });

  it("INCR 失败回退本地计数, 检索不中断保存广播", async () => {
    const redis = {
      incr: vi.fn(async () => {
        throw new Error("redis down");
      }),
    };
    const logs = [];
    const c = createVersionCounter({ redis, log: (m) => logs.push(m) });
    expect(await c.next("doc")).toBe(1);
    expect(await c.next("doc")).toBe(2);
    expect(logs.some((m) => m.includes("falling back"))).toBe(true);
  });
});