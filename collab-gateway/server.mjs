/**
 * Perseus Yjs 协作网关 (Hocuspocus 哑管道)
 *
 * 职责边界 (对齐 git-cgi 模式: 同步协议全在库内, 业务逻辑留在 app):
 *   - CRDT 同步/感知(光标)/只读强制: @hocuspocus/server 内置
 *   - 鉴权: onAuthenticate → app POST /api/v1/collab/auth
 *   - 文档加载: onLoadDocument → app GET /api/v1/collab/doc
 *   - 协作保存: onStateless("collab-save") → app POST /api/v1/collab/save
 *
 * 保存语义: 与旧 F-204 一致 —— 仅显式保存落 Git;
 * onStoreDocument (debounce/断开自动触发) 一律 no-op, 防止高频自动 commit。
 *
 * 文档约定: Y.Doc 中唯一共享文本类型为 getText("content"), 客户端
 * yCollab(ydoc.getText("content"), provider.awareness) 必须同名。
 *
 * 环境变量:
 *   PERSEUS_COLLAB_INTERNAL_SECRET  必填, 与 app 共享的内部密钥
 *   PERSEUS_APP_URL                 app 内部地址 (默认 http://app:8000)
 *   PORT / HEALTH_PORT              WS 端口(默认 4444) / 健康检查端口(默认 4445)
 *   PERSEUS_APP_TIMEOUT_MS          回调超时 (默认 10000)
 *   PERSEUS_COLLAB_SESSION_TTL_MS   断开后保留内存会话的时长 (默认 600000; 0=禁用)
 *   REDIS_URL                       Redis 连接串; 配置后启用多副本同步 + 会话快照持久化
 *   PERSEUS_COLLAB_REDIS_URL        可选, 覆盖 REDIS_URL
 *   PERSEUS_COLLAB_MAX_CONTENT_CHARS      单文档文本上限 (默认 2000000), 超限拒绝加载/保存
 *   PERSEUS_COLLAB_MAX_CONNECTIONS_PER_DOC 单文档并发连接上限 (默认 50), 超限拒绝新连接
 *   PERSEUS_COLLAB_MAX_AWARENESS_BYTES    单条 awareness 状态上限 (默认 8192), 超限剔除可选字段/丢弃
 *
 * 跟随模式 (Follow me): awareness 扩展字段 viewport/follow 由网关校验盖章
 * (beforeHandleAwareness), "跟我来"信令走 stateless collab-spotlight (写权限者)。
 */
import http from "node:http";
import { pathToFileURL } from "node:url";

import RedisClient from "ioredis";
import { Server } from "@hocuspocus/server";

import { createRedisPersistence, resolveRedisUrl } from "./redisPersistence.mjs";
import { createSessionTtlExtension, DEFAULT_SESSION_TTL_MS } from "./sessionTtl.mjs";

export const APP_URL = process.env.PERSEUS_APP_URL || "http://app:8000";
export const INTERNAL_SECRET = process.env.PERSEUS_COLLAB_INTERNAL_SECRET || "";
export const APP_TIMEOUT_MS = Number(process.env.PERSEUS_APP_TIMEOUT_MS || 10000);
export const SESSION_TTL_MS = Number(
  process.env.PERSEUS_COLLAB_SESSION_TTL_MS || DEFAULT_SESSION_TTL_MS
);
export const REDIS_URL = resolveRedisUrl(undefined, process.env);
export const MAX_CONTENT_CHARS = Number(
  process.env.PERSEUS_COLLAB_MAX_CONTENT_CHARS || 2_000_000
);
export const MAX_CONNECTIONS_PER_DOC = Number(
  process.env.PERSEUS_COLLAB_MAX_CONNECTIONS_PER_DOC || 50
);
export const MAX_AWARENESS_BYTES = Number(
  process.env.PERSEUS_COLLAB_MAX_AWARENESS_BYTES || 8192
);

export const log = (...args) =>
  console.log(new Date().toISOString(), "[collab-gateway]", ...args);

/** 服务间调用 app; 返回 {status, data}, 网络/超时归一为 502 */
export async function callApp(path, { method = "GET", body } = {}) {
  try {
    const res = await fetch(`${APP_URL}${path}`, {
      method,
      headers: {
        "Content-Type": "application/json",
        "X-Collab-Internal-Secret": INTERNAL_SECRET,
      },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: AbortSignal.timeout(APP_TIMEOUT_MS),
    });
    let data = null;
    try {
      data = await res.json();
    } catch {
      // 非 JSON 响应体 (如裸文本), data 保持 null
    }
    return { status: res.status, data };
  } catch (err) {
    log("app 回调失败", path, err.message);
    return { status: 502, data: null };
  }
}

/** 构造连接拒绝错误: error.reason 会经 writePermissionDenied 发送给客户端 */
export function deny(status, detail) {
  const err = new Error(detail);
  err.status = status;
  err.reason = detail;
  return err;
}

/** awareness 状态序列化字节数 (无法序列化时视为超限) */
function awarenessBytes(state) {
  try {
    return Buffer.byteLength(JSON.stringify(state));
  } catch {
    return Infinity;
  }
}

/** 视口锚点: 仅接受 >=0 整数, 否则移除该字段 (跟随模式滚动同步用) */
function sanitizeViewport(state) {
  const vp = state.viewport;
  if (vp === undefined) return;
  if (vp && typeof vp === "object" && Number.isInteger(vp.anchor) && vp.anchor >= 0) {
    state.viewport = { anchor: vp.anchor };
  } else {
    delete state.viewport;
  }
}

/** 跟随目标: 仅接受 {target: 整数 clientID | null}, 否则移除该字段 */
function sanitizeFollow(state) {
  const follow = state.follow;
  if (follow === undefined) return;
  if (
    follow &&
    typeof follow === "object" &&
    (follow.target === null || Number.isInteger(follow.target))
  ) {
    state.follow = { target: follow.target };
  } else {
    delete state.follow;
  }
}

/**
 * 服务端 awareness 策略 (beforeHandleAwareness):
 *   - 用连接上下文 (onAuthenticate 已校验的身份) 盖章 user, 防客户端冒名;
 *     保留客户端自带的 color 等展示字段。
 *   - 校验/归一化跟随模式扩展字段 viewport / follow。
 *   - 单条状态超过 maxBytes 时先剔除可选字段, 再剔除白名单 (user/cursor) 外的
 *     其余字段; 仍超限则收敛为最小身份, 防止感知通道被滥用。
 * 仅对客户端来源 (context 存在) 盖章; Redis 对端同步 (context 为 undefined) 直接跳过。
 *
 * @param {Map<number, Record<string, any>>} states
 * @param {any} context
 * @param {number} maxBytes
 */
export function applyAwarenessPolicy(states, context, maxBytes = MAX_AWARENESS_BYTES) {
  for (const [clientId, state] of states) {
    if (!state || typeof state !== "object") {
      states.delete(clientId);
      continue;
    }
    if (context) {
      const base = state.user && typeof state.user === "object" ? state.user : {};
      state.user = { ...base, user_id: context.user_id, name: context.username };
    }
    sanitizeViewport(state);
    sanitizeFollow(state);
    if (awarenessBytes(state) <= maxBytes) continue;
    // 超限: 先剔除跟随模式可选字段, 再剔除白名单外的其余字段 (保留 user/cursor)
    delete state.viewport;
    delete state.follow;
    for (const key of Object.keys(state)) {
      if (key !== "user" && key !== "cursor") delete state[key];
    }
    if (awarenessBytes(state) > maxBytes) {
      state.user = context ? { user_id: context.user_id, name: context.username } : {};
      delete state.cursor;
    }
  }
}

/** 等待 Y.Text 被对端更新填充 (多副本播种协调); 返回是否等到 */
function waitForText(text, timeoutMs) {
  return new Promise((resolve) => {
    if (text.length > 0) return resolve(true);
    let settled = false;
    const done = (v) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      text.unobserve(observer);
      resolve(v);
    };
    const observer = () => {
      if (text.length > 0) done(true);
    };
    const timer = setTimeout(() => done(false), timeoutMs);
    text.observe(observer);
  });
}

/**
 * 解析连接 token:
 * - 纯字符串 = 用户 access token (旧行为)
 * - JSON 字符串 {access_token, invite_token} = 邀请链接访客 (会话级临时权限)
 */
export function parseConnectionToken(raw) {
  if (typeof raw !== "string") return { token: raw ?? "", invite_token: undefined };
  const trimmed = raw.trim();
  if (!trimmed.startsWith("{")) return { token: raw, invite_token: undefined };
  try {
    const parsed = JSON.parse(trimmed);
    return {
      token: parsed.access_token || parsed.token || "",
      invite_token: parsed.invite_token || undefined,
    };
  } catch {
    return { token: raw, invite_token: undefined };
  }
}

/**
 * 构建协作网关 (未监听, 供测试复用)。
 * 会话 TTL 扩展挂在返回的 Server 上 (gateway.sessionTtl), 关闭前需 releaseAll()。
 */
export function buildGateway({
  sessionTtlMs = SESSION_TTL_MS,
  sessionTtl,
  redisUrl = REDIS_URL,
  createRedisClient,
  maxContentChars = MAX_CONTENT_CHARS,
  maxConnectionsPerDoc = MAX_CONNECTIONS_PER_DOC,
  maxAwarenessBytes = MAX_AWARENESS_BYTES,
} = {}) {
  const ttl = sessionTtl ?? createSessionTtlExtension({ ttlMs: sessionTtlMs, log });
  const extensions = [ttl];

  // 每文档实时连接计数 (本副本维度): 连接建立时 +1, 断开时 -1。
  // 多副本下 nginx 将同一文档分发到各副本, 故上限按副本生效。
  const connectionsByDoc = new Map();
  const countedContexts = new WeakSet();
  const releaseConnection = (documentName, context) => {
    if (!context || !countedContexts.has(context)) return;
    countedContexts.delete(context);
    const next = Math.max(0, (connectionsByDoc.get(documentName) || 0) - 1);
    if (next === 0) connectionsByDoc.delete(documentName);
    else connectionsByDoc.set(documentName, next);
  };

  let redisPersistence = null;
  if (redisUrl) {
    const factory = createRedisClient ?? (() => new RedisClient(redisUrl));
    redisPersistence = createRedisPersistence({ url: redisUrl, log, createClient: factory });
    extensions.push(...redisPersistence.extensions);
  }

  const server = new Server({
    name: "perseus-collab-gateway",
    extensions,

    async onAuthenticate({ token, documentName, connectionConfig }) {
      const creds = parseConnectionToken(token);
      const { status, data } = await callApp("/api/v1/collab/auth", {
        method: "POST",
        body: { token: creds.token, docKey: documentName, invite_token: creds.invite_token },
      });
      if (status === 401) throw deny(401, data?.detail || "无效或过期的 token");
      if (status === 404) throw deny(404, data?.detail || "仓库不存在");
      if (status === 403) throw deny(403, data?.detail || "没有该仓库的访问权限");
      if (status !== 200) throw deny(status, data?.detail || "协作服务暂不可用");

      // 连接数上限: 多副本下防止单文档连接打爆某一副本内存
      if ((connectionsByDoc.get(documentName) || 0) >= maxConnectionsPerDoc) {
        throw deny(429, `该文档连接数已达上限 (${maxConnectionsPerDoc})`);
      }

      connectionConfig.readOnly = !data.can_write;
      log(`auth doc=${documentName} user=${data.username} can_write=${data.can_write} via_invite=${!!data.via_invite}`);
      // token 存入连接上下文, 供显式保存时实时鉴权
      return {
        user_id: data.user_id,
        username: data.username,
        can_write: data.can_write,
        token: creds.token,
        invite_token: creds.invite_token,
      };
    },

    // 跟随模式 (Follow me): 感知层字段策略。
    // viewport / follow 由客户端写入 awareness, 网关只做盖章与校验, 不做业务转发
    // (awareness 经 extension-redis 跨副本同步, 跟随关系由客户端从感知状态派生)。
    async beforeHandleAwareness({ states, context }) {
      applyAwarenessPolicy(states, context, maxAwarenessBytes);
    },

    // 连接建立后登记计数 (以实际建立为准, 避免加载失败时计数泄漏);
    // 并发竞争下超限则直接关闭连接。
    async connected({ documentName, connection, context }) {
      const current = connectionsByDoc.get(documentName) || 0;
      if (current >= maxConnectionsPerDoc) {
        log(`connection refused doc=${documentName} count=${current}/${maxConnectionsPerDoc}`);
        connection.close({ code: 4429, reason: `该文档连接数已达上限 (${maxConnectionsPerDoc})` });
        return;
      }
      connectionsByDoc.set(documentName, current + 1);
      if (context && typeof context === "object") countedContexts.add(context);
    },

    async onDisconnect({ documentName, context, document }) {
      releaseConnection(documentName, context);
      // 跟随模式: 发起者离开即广播取消, 避免对端持续跟随已离线的目标。
      if (context && context.spotlight) {
        context.spotlight = false;
        document.broadcastStateless(
          JSON.stringify({
            type: "collab-spotlight",
            docKey: documentName,
            from: { user_id: context.user_id, username: context.username },
            on: false,
          })
        );
        log(`spotlight ended (disconnect) doc=${documentName} user=${context.username}`);
      }
    },

    // 播种放在 afterLoadDocument: 此时 Redis 扩展已完成会话快照恢复与跨副本
    // 初始同步。优先复用快照/对端状态, 仍为空才从 Git 播种, 且多副本用
    // seedGuard 串行化, 避免各自独立 insert 造成 "hellohello" 重复。
    async afterLoadDocument({ documentName, document }) {
      const text = document.getText("content");
      if (text.length > 0) {
        log(`load doc=${documentName} restored from session/peer, skip git seed`);
        return;
      }

      const seedGuard = redisPersistence?.seedGuard;
      if (seedGuard && !(await seedGuard.tryAcquire(documentName))) {
        await waitForText(text, 5000);
        if (text.length > 0) {
          log(`load doc=${documentName} seeded by peer, skip git seed`);
          return;
        }
        log(`load doc=${documentName} peer seed timed out, seeding from git`);
      }

      const { status, data } = await callApp(
        `/api/v1/collab/doc?docKey=${encodeURIComponent(documentName)}`
      );
      if (status === 404) throw deny(404, data?.detail || "文件不存在");
      if (status === 415) throw deny(415, data?.detail || "不支持协作编辑二进制文件");
      if (status !== 200) throw deny(status, data?.detail || "文档加载失败");

      const content = data?.content ?? "";
      if (content.length > maxContentChars) {
        throw deny(
          413,
          `文档内容过大 (${content.length} > ${maxContentChars} 字符), 拒绝加载`
        );
      }
      if (content.length > 0) text.insert(0, content);
      log(`load doc=${documentName} seeded from git chars=${content.length}`);
    },

    async onStoreDocument({ documentName }) {
      // Git 提交仅由 collab-save stateless 消息触发;
      // 此处的 debounced 落盘在启用 Redis 时写入会话快照 (非 Git commit)。
      log(`auto snapshot doc=${documentName} (git commit stays explicit)`);
    },

    async onStateless({ connection, document, documentName, payload }) {
      let msg;
      try {
        msg = JSON.parse(payload);
      } catch {
        return;
      }

      // 跟随模式 (Follow me) 的"跟我来"信令: 仅写权限者可发起, 全员广播。
      // 接收端据 from.user_id 在 awareness 中定位发起者 clientID 并设置 follow.target。
      if (msg?.type === "collab-spotlight") {
        const spotContext = connection.context || {};
        const on = msg.on !== false;
        if (!spotContext.can_write) {
          connection.sendStateless(
            JSON.stringify({
              type: "collab-spotlight-error",
              docKey: documentName,
              error: "没有发起跟随的权限",
            })
          );
          return;
        }
        spotContext.spotlight = on;
        document.broadcastStateless(
          JSON.stringify({
            type: "collab-spotlight",
            docKey: documentName,
            from: { user_id: spotContext.user_id, username: spotContext.username },
            on,
          })
        );
        log(`spotlight doc=${documentName} user=${spotContext.username} on=${on}`);
        return;
      }

      if (msg?.type !== "collab-save") return;

      const context = connection.context || {};
      if (!context.can_write) {
        connection.sendStateless(
          JSON.stringify({ type: "collab-save-error", docKey: documentName, error: "没有该仓库的写入权限" })
        );
        return;
      }

      const content = document.getText("content").toString();
      if (content.length > maxContentChars) {
        connection.sendStateless(
          JSON.stringify({
            type: "collab-save-error",
            docKey: documentName,
            error: `文档内容过大 (${content.length} > ${maxContentChars} 字符), 拒绝保存`,
          })
        );
        return;
      }

      const { status, data } = await callApp("/api/v1/collab/save", {
        method: "POST",
        body: { token: context.token, docKey: documentName, content, message: msg.message, invite_token: context.invite_token, draft: msg.draft === true },
      });

      if (status === 403) {
        // 权限即时性: app 判定写入权限已吊销 → 断开连接强制重认证,
        // 避免该连接继续以陈旧权限读写 (多副本下尤为重要)。
        const error = data?.detail || "没有该仓库的写入权限";
        log(`save denied doc=${documentName} user=${context.username}: ${error}, closing connection`);
        connection.sendStateless(
          JSON.stringify({ type: "collab-save-error", docKey: documentName, error })
        );
        connection.close({ code: 4403, reason: "写入权限已吊销, 请重新连接" });
        return;
      }

      if (status !== 200) {
        const error = data?.detail || "保存失败";
        log(`save failed doc=${documentName} user=${context.username} status=${status}: ${error}`);
        connection.sendStateless(
          JSON.stringify({ type: "collab-save-error", docKey: documentName, error })
        );
        return;
      }

      log(`saved doc=${documentName} user=${data.saved_by} commit=${data.commit_id}`);
      // 全员广播 (含提交者), 客户端据此更新 "Git 已提交" 徽标。
      // 私密性收紧: 仅广播提交标识, 不泄漏 saved_by/message/branch/path 等元数据。
      document.broadcastStateless(
        JSON.stringify({
          type: "collab-saved",
          docKey: documentName,
          commit_id: data.commit_id,
        })
      );
    },
  });

  server.sessionTtl = ttl;
  server.redisPersistence = redisPersistence;
  return server;
}

/** 启动网关 + 健康检查端点 */
export async function startGateway({
  port,
  healthPort,
  sessionTtlMs,
  redisUrl,
  createRedisClient,
  maxContentChars,
  maxConnectionsPerDoc,
  maxAwarenessBytes,
} = {}) {
  const gateway = buildGateway({
    ...(sessionTtlMs === undefined ? {} : { sessionTtlMs }),
    ...(redisUrl === undefined ? {} : { redisUrl }),
    ...(createRedisClient === undefined ? {} : { createRedisClient }),
    ...(maxContentChars === undefined ? {} : { maxContentChars }),
    ...(maxConnectionsPerDoc === undefined ? {} : { maxConnectionsPerDoc }),
    ...(maxAwarenessBytes === undefined ? {} : { maxAwarenessBytes }),
  });
  const hocuspocus = await gateway.listen(port ?? Number(process.env.PORT || 4444));
  const health = http
    .createServer((req, res) => {
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(
        JSON.stringify({
          status: "ok",
          connections: hocuspocus.getConnectionsCount?.() ?? null,
        })
      );
    })
    .listen(healthPort ?? Number(process.env.HEALTH_PORT || 4445));

  log(`listening on :${gateway.address?.port ?? "?"}, app=${APP_URL}`);
  return {
    hocuspocus,
    port: gateway.address.port,
    sessionTtl: gateway.sessionTtl,
    redisPersistence: gateway.redisPersistence,
    close: async () => {
      health.close();
      // 解除会话保留, 否则 destroy() 会等待文档卸载而挂起
      gateway.sessionTtl.releaseAll();
      await gateway.destroy();
      // 文档卸载期间可能还有最后一次快照落盘, 故在 destroy 之后再关快照连接
      await gateway.redisPersistence?.close();
    },
  };
}

// 直接运行时启动 (被测试导入时不启动)
const isMain = process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href;
if (isMain) {
  if (!INTERNAL_SECRET.trim()) {
    console.error("[collab-gateway] PERSEUS_COLLAB_INTERNAL_SECRET 未配置, 拒绝启动");
    process.exit(1);
  }
  startGateway();
  for (const signal of ["SIGINT", "SIGTERM"]) {
    process.on(signal, () => {
      log(`${signal} received, shutting down`);
      process.exit(0);
    });
  }
}
