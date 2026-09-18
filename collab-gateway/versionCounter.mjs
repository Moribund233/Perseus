/**
 * 协作版本计数器 (「会话已同步 ✓ (版本 N)」的 N)
 *
 * 语义: 每个文档的 "协作保存次数" 单调递增版本号, 随 collab-saved 广播,
 * 两端状态栏展示 v{N}, 供协作者对齐 "当前已保存到第几版"。
 *
 * 跨副本一致性:
 *   - Redis 模式下用 INCR (prefix + docKey) 持久计数: 多副本共享、网关重启延续;
 *   - 无 Redis (或 INCR 暂时失败) 时回退到进程内 Map, 保证保存广播不被计数中断。
 *
 * 注意: collab-save 幂等/顺序不保证严格事务 —— INCR 并发竞态下版本号可能乱序
 * (2 先于 1 广播), 但每个版本号唯一且单调, 满足 UX 对齐心智。
 */
export const DEFAULT_VERSION_KEY_PREFIX = "perseus:collab:version:";

/**
 * @param {object} [options]
 * @param {{ incr: (key: string) => Promise<number> }} [options.redis] ioredis 兼容客户端
 * @param {string} [options.prefix]
 * @param {(msg: string) => void} [options.log]
 * @returns {{ next: (documentName: string) => Promise<number> }}
 */
export function createVersionCounter({ redis, prefix = DEFAULT_VERSION_KEY_PREFIX, log = () => {} } = {}) {
  const local = new Map();
  return {
    async next(documentName) {
      if (redis) {
        try {
          return await redis.incr(`${prefix}${documentName}`);
        } catch (err) {
          log(`version counter redis failed (${err?.message ?? err}), falling back to local`);
        }
      }
      const n = (local.get(documentName) || 0) + 1;
      local.set(documentName, n);
      return n;
    },
  };
}