import { useAuthStore } from '../stores/auth';

export type LogSocketStatus = 'connecting' | 'connected' | 'disconnected';

/** 服务端 /ws/logs 推送的单条日志（api/websocket/handlers/log_handler.py） */
export interface StreamLogEntry {
  timestamp: string;
  level: string;
  logger: string;
  message: string;
}

export interface LogFilters {
  levels?: string[];
  loggers?: string[];
  keywords?: string[];
}

interface LogSocketHandlers {
  onHistory?: (logs: StreamLogEntry[]) => void;
  onLog?: (entry: StreamLogEntry) => void;
  onStatusChange?: (status: LogSocketStatus) => void;
  onError?: (message: string) => void;
}

function resolveWsUrl(): string {
  const base = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8002';
  // VITE_API_URL 为空字符串 = 与页面同源 (走网关)
  if (base === '') {
    if (typeof location === 'undefined') return '';
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    return `${proto}://${location.host}`;
  }
  return base.replace(/^http/, 'ws');
}

/** 构造 subscribe_logs 消息（空过滤项不下发，交由服务端默认处理） */
export function buildSubscribePayload(
  filters: LogFilters,
  historyCount: number,
): Record<string, unknown> {
  const f: Record<string, unknown> = {};
  if (filters.levels?.length) f.levels = filters.levels;
  if (filters.loggers?.length) f.loggers = filters.loggers;
  if (filters.keywords?.length) f.keywords = filters.keywords;
  return { type: 'subscribe_logs', filters: f, history_count: historyCount };
}

/** 把服务端 log 消息解析为条目（字段缺失时返回 null） */
export function parseLogMessage(data: Record<string, unknown>): StreamLogEntry | null {
  if (data.type !== 'log') return null;
  const { timestamp, level, logger, message } = data;
  if (typeof timestamp !== 'string' || typeof level !== 'string' || typeof message !== 'string') {
    return null;
  }
  return {
    timestamp,
    level,
    logger: typeof logger === 'string' ? logger : '',
    message,
  };
}

/** 把结构化条目格式化为终端行（与后端 formatter 一致，供 splitLine 着色复用） */
export function formatStreamLine(entry: StreamLogEntry): string {
  return `${entry.timestamp} - ${entry.logger} - ${entry.level} - ${entry.message}`;
}

/**
 * 实时日志 WebSocket 客户端（管理控制台）
 *
 * 协议（api/websocket/router.py /logs）：
 *   连接:  /ws/logs?token=<jwt>（仅管理员）
 *   发送:  {"type":"subscribe_logs","filters":{levels,loggers,keywords},"history_count"}
 *   接收:  connected / logs_subscribed / log_history / log / error
 *   心跳:  30s ping（服务端 120s 超时清理），断线指数退避重连。
 */
class LogSocketClient {
  private ws: WebSocket | null = null;
  private handlers: LogSocketHandlers = {};
  private reconnectAttempts = 0;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private pingTimer: ReturnType<typeof setInterval> | null = null;
  private enabled = false;
  private filters: LogFilters = {};
  private historyCount = 100;

  setHandlers(handlers: LogSocketHandlers) {
    this.handlers = handlers;
  }

  start(filters: LogFilters, historyCount = 100) {
    this.enabled = true;
    this.filters = filters;
    this.historyCount = historyCount;
    this.connect();
  }

  stop() {
    this.enabled = false;
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.clearPing();
    this.ws?.close();
    this.ws = null;
  }

  /** 过滤条件变化时重新订阅（若已连接，服务端会重发 logs_subscribed + log_history） */
  updateFilters(filters: LogFilters, historyCount?: number) {
    this.filters = filters;
    if (historyCount !== undefined) this.historyCount = historyCount;
    if (this.isConnected) {
      this.send(buildSubscribePayload(this.filters, this.historyCount));
    }
  }

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  private send(payload: Record<string, unknown>) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(payload));
    }
  }

  private clearPing() {
    if (this.pingTimer) {
      clearInterval(this.pingTimer);
      this.pingTimer = null;
    }
  }

  private connect() {
    if (!this.enabled || this.ws) return;

    const token = useAuthStore.getState().accessToken;
    this.handlers.onStatusChange?.('connecting');
    const ws = new WebSocket(`${resolveWsUrl()}/ws/logs?token=${encodeURIComponent(token ?? '')}`);
    this.ws = ws;

    ws.onopen = () => {
      this.pingTimer = setInterval(() => {
        this.send({ type: 'ping', timestamp: new Date().toISOString() });
      }, 30_000);
    };

    ws.onmessage = (ev) => {
      let data: Record<string, unknown>;
      try {
        data = JSON.parse(ev.data as string);
      } catch {
        return;
      }
      switch (data.type) {
        case 'connected':
          this.reconnectAttempts = 0;
          this.handlers.onStatusChange?.('connected');
          // 认证通过后再订阅，保证服务端已进入消息循环
          this.send(buildSubscribePayload(this.filters, this.historyCount));
          break;
        case 'log_history':
          this.handlers.onHistory?.(
            Array.isArray(data.logs) ? (data.logs as StreamLogEntry[]) : [],
          );
          break;
        case 'log': {
          const entry = parseLogMessage(data);
          if (entry) this.handlers.onLog?.(entry);
          break;
        }
        case 'error':
          this.handlers.onError?.(typeof data.error === 'string' ? data.error : 'log stream error');
          break;
      }
    };

    ws.onclose = () => {
      this.clearPing();
      this.ws = null;
      this.handlers.onStatusChange?.('disconnected');
      if (this.enabled && useAuthStore.getState().accessToken) {
        const delay = Math.min(1000 * 2 ** this.reconnectAttempts, 15_000);
        this.reconnectAttempts += 1;
        this.reconnectTimer = setTimeout(() => this.connect(), delay);
      }
    };

    ws.onerror = () => {
      ws.close();
    };
  }
}

export const logSocket = new LogSocketClient();
