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
 */
import http from "node:http";
import { pathToFileURL } from "node:url";

import { Server } from "@hocuspocus/server";

export const APP_URL = process.env.PERSEUS_APP_URL || "http://app:8000";
export const INTERNAL_SECRET = process.env.PERSEUS_COLLAB_INTERNAL_SECRET || "";
export const APP_TIMEOUT_MS = Number(process.env.PERSEUS_APP_TIMEOUT_MS || 10000);

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

/** 构建协作网关 (未监听, 供测试复用) */
export function buildGateway() {
  return new Server({
    name: "perseus-collab-gateway",

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

    async onLoadDocument({ documentName, document }) {
      const { status, data } = await callApp(
        `/api/v1/collab/doc?docKey=${encodeURIComponent(documentName)}`
      );
      if (status === 404) throw deny(404, data?.detail || "文件不存在");
      if (status === 415) throw deny(415, data?.detail || "不支持协作编辑二进制文件");
      if (status !== 200) throw deny(status, data?.detail || "文档加载失败");

      const content = data?.content ?? "";
      if (content.length > 0) document.getText("content").insert(0, content);
      log(`load doc=${documentName} chars=${content.length}`);
    },

    async onStoreDocument({ documentName }) {
      // 显式保存语义: Git 提交仅由 collab-save stateless 消息触发
      log(`skip auto-persist doc=${documentName} (explicit-save semantics)`);
    },

    async onStateless({ connection, document, documentName, payload }) {
      let msg;
      try {
        msg = JSON.parse(payload);
      } catch {
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
      const { status, data } = await callApp("/api/v1/collab/save", {
        method: "POST",
        body: { token: context.token, docKey: documentName, content, message: msg.message, invite_token: context.invite_token },
      });

      if (status !== 200) {
        const error = data?.detail || "保存失败";
        log(`save failed doc=${documentName} user=${context.username} status=${status}: ${error}`);
        connection.sendStateless(
          JSON.stringify({ type: "collab-save-error", docKey: documentName, error })
        );
        return;
      }

      log(`saved doc=${documentName} user=${data.saved_by} commit=${data.commit_id}`);
      // 全员广播 (含提交者), 客户端据此更新 "Git 已提交" 徽标
      document.broadcastStateless(
        JSON.stringify({
          type: "collab-saved",
          docKey: documentName,
          commit_id: data.commit_id,
          saved_by: data.saved_by,
          message: data.message,
          branch: data.branch,
          path: data.path,
        })
      );
    },
  });
}

/** 启动网关 + 健康检查端点 */
export async function startGateway({ port, healthPort } = {}) {
  const gateway = buildGateway();
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
    close: async () => {
      health.close();
      await gateway.destroy();
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
