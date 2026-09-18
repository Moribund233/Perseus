/**
 * Redis 多副本 + 会话持久化 (collab-f204-vs-cwm 5.6 / M4)
 *
 * 两个正交能力:
 *   1. 多副本同步 —— @hocuspocus/extension-redis: 各网关实例经 Redis pub/sub
 *      互相广播 CRDT 变更与感知状态, 客户端连到任一副本都能收敛。
 *      解除 "同一文档必须落在同一进程" 的隐性约束 (配合 nginx 负载均衡)。
 *   2. 会话持久化 —— @hocuspocus/extension-database + Redis 快照: 每次
 *      debounced 落盘把 Y.Doc 全量状态写入 Redis, 冷加载时优先恢复,
 *      因此未显式保存的编辑也能跨副本/跨短重启恢复。
 *
 * 权限边界不变: Redis 只存 Y.Doc 快照, Git 提交仍仅由显式 collab-save 触发。
 */

import { randomUUID } from "node:crypto";

import { Database } from "@hocuspocus/extension-database";
import { Redis } from "@hocuspocus/extension-redis";

import { createVersionCounter } from "./versionCounter.mjs";

export const DEFAULT_KEY_PREFIX = "perseus:collab:doc:";

/** 解析 Redis 连接串: 显式参数 > PERSEUS_COLLAB_REDIS_URL > REDIS_URL > null */
export function resolveRedisUrl(url, env = process.env) {
  const value = (url ?? env.PERSEUS_COLLAB_REDIS_URL ?? env.REDIS_URL ?? "").trim();
  return value || null;
}

/**
 * 把 Y.Doc 二进制快照存到 Redis 的存取适配器 (供 @hocuspocus/extension-database)。
 * @param {{ getBuffer: Function, set: Function }} redis ioredis 兼容客户端
 */
export function createRedisStorage(redis, { prefix = DEFAULT_KEY_PREFIX } = {}) {
  const keyFor = (documentName) => `${prefix}${documentName}`;
  return {
    async fetch({ documentName }) {
      const state = await redis.getBuffer(keyFor(documentName));
      return state ?? null;
    },
    async store({ documentName, state }) {
      await redis.set(keyFor(documentName), Buffer.from(state));
    },
  };
}

/**
 * 冷启动播种锁: 多副本同时首次打开同一文档时, 只允许一个副本从 Git 播种,
 * 其余副本等待被广播的 Yjs 更新, 避免各自独立 insert 造成内容重复
 * (两段独立的 CRDT 文本合并会得到 "hellohello")。
 */
export function createSeedGuard(redis, { prefix = DEFAULT_KEY_PREFIX, lockTtlMs = 15000 } = {}) {
  return {
    /** 抢占成功返回 true; 失败表示已有副本在播种 */
    async tryAcquire(documentName) {
      const key = `${prefix}${documentName}:seed-lock`;
      const result = await redis.set(key, "1", "PX", lockTtlMs, "NX");
      return result === "OK";
    },
  };
}

/**
 * 创建 Redis 能力集 (未连接前的构造, 惰性连接由 ioredis 负责)。
 * @param {object} options
 * @param {string} options.url                 Redis 连接串
 * @param {(msg: string) => void} [options.log]
 * @param {() => import("ioredis").default} options.createClient 注入便于测试
 * @returns {{ extensions: object[], storage: object, seedGuard: object, close: () => Promise<void> }}
 */
export function createRedisPersistence({ url, log = () => {}, createClient, identifier } = {}) {
  if (typeof createClient !== "function") {
    throw new Error("createRedisPersistence 需要 createClient 注入 (禁止硬编码连接)");
  }

  const redisExt = new Redis({
    // 每次调用返回新客户端: 扩展内部需要独立的 pub 与 sub 连接
    createClient: () => createClient(),
    // 各副本唯一, 用于过滤 Redis 上其他实例的消息
    identifier: identifier ?? `perseus-collab-${randomUUID()}`,
  });

  const snapshotClient = createClient();
  const storage = createRedisStorage(snapshotClient);
  const databaseExt = new Database({ fetch: storage.fetch, store: storage.store });
  // 协作版本号: 与快照共用长连客户端, Redis INCR 持久计数 (跨副本/重启一致)
  const versionCounter = createVersionCounter({ redis: snapshotClient, log });

  log(`redis enabled url=${url}`);
  return {
    extensions: [redisExt, databaseExt],
    storage,
    seedGuard: createSeedGuard(snapshotClient),
    versionCounter,
    async close() {
      try {
        await snapshotClient.quit();
      } catch (err) {
        log(`redis snapshot client close failed: ${err?.message ?? err}`);
      }
    },
  };
}
