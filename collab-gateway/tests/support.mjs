/**
 * 协作网关测试共享工具: app 回调 mock / 等待 / provider 构造
 */
import net from "node:net";

import { vi } from "vitest";
import { HocuspocusProvider } from "@hocuspocus/provider";

/** 申请一个空闲端口 (Hocuspocus 的 listen 不接受 0, 会退化成 80) */
export async function freePort() {
  return new Promise((resolve, reject) => {
    const srv = net.createServer();
    srv.unref();
    srv.on("error", reject);
    srv.listen(0, "127.0.0.1", () => {
      const { port } = srv.address();
      srv.close(() => resolve(port));
    });
  });
}

export const DOC = "11111111-1111-1111-1111-111111111111:main:src/app.py";

export const AUTH_OK_WRITER = {
  status: 200,
  data: { user_id: "u-writer", username: "alice", can_write: true },
};
export const AUTH_OK_READER = {
  status: 200,
  data: { user_id: "u-reader", username: "bob", can_write: false },
};

/** app 回调路由 mock 表 (每个用例可覆盖) */
export const appMock = {
  responses: {},
  calls: [],
  reset(responses = {}) {
    this.responses = responses;
    this.calls = [];
  },
};

/** 安装全局 fetch stub, 按 `${method} ${path}` 命中 appMock.responses */
export function installAppMock() {
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
}

export async function waitFor(fn, desc) {
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

export async function waitForAsync(fn, desc, timeoutMs = 5000) {
  const start = Date.now();
  for (;;) {
    try {
      const v = await fn();
      if (v) return v;
    } catch {
      // 条件尚未满足
    }
    if (Date.now() - start > timeoutMs) throw new Error(`timeout waiting: ${desc}`);
    await new Promise((r) => setTimeout(r, 25));
  }
}

export function makeProvider(port, name, token, user) {
  return new HocuspocusProvider({
    url: `ws://127.0.0.1:${port}`,
    name,
    token,
    awareness: undefined,
    onAwarenessUpdate: () => {},
    user,
  });
}
