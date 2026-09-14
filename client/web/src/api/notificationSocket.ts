import { useAuthStore } from '../stores/auth';
import type { Notification } from './notifications';

export type NotificationSocketStatus = 'connecting' | 'connected' | 'disconnected';

// 服务端 user_notification 推送载荷 (api/websocket/handlers/notification.py notify_user)
export interface UserNotificationPayload {
  notification_type: string;
  data: Notification;
  unread_count?: number;
  timestamp: string;
}

interface NotificationSocketHandlers {
  onNotification?: (payload: UserNotificationPayload) => void;
  onStatusChange?: (status: NotificationSocketStatus) => void;
}

function resolveWsUrl(): string {
  const base = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000';
  // VITE_API_URL 为空字符串 = 与页面同源 (走网关)
  if (base === '') {
    if (typeof location === 'undefined') return '';
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    return `${proto}://${location.host}`;
  }
  return base.replace(/^http/, 'ws');
}

/**
 * 通知 WebSocket 客户端 (F-205 实时推送)
 *
 * 连接专用端点 /ws/notifications?token=<jwt>（服务端自动绑定用户并推送
 * user_notification 消息），仅收发 ping/pong 与推送，不参与聊天/房间。
 * 心跳 30s（服务端 120s 超时清理），断线指数退避重连。
 */
class NotificationSocketClient {
  private ws: WebSocket | null = null;
  private handlers: NotificationSocketHandlers = {};
  private reconnectAttempts = 0;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private pingTimer: ReturnType<typeof setInterval> | null = null;
  private enabled = false;

  setHandlers(handlers: NotificationSocketHandlers) {
    this.handlers = handlers;
  }

  start() {
    this.enabled = true;
    this.connect();
  }

  stop() {
    this.enabled = false;
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.pingTimer) {
      clearInterval(this.pingTimer);
      this.pingTimer = null;
    }
    this.ws?.close();
    this.ws = null;
  }

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  private send(payload: Record<string, unknown>) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(payload));
    }
  }

  private connect() {
    if (!this.enabled || this.ws) return;

    const token = useAuthStore.getState().accessToken;
    this.handlers.onStatusChange?.('connecting');
    const ws = new WebSocket(`${resolveWsUrl()}/ws/notifications?token=${encodeURIComponent(token ?? '')}`);
    this.ws = ws;

    ws.onopen = () => {
      // 心跳保活
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
          break;
        case 'user_notification':
          this.handlers.onNotification?.({
            notification_type: data.notification_type as string,
            data: data.data as Notification,
            unread_count: data.unread_count as number | undefined,
            timestamp: data.timestamp as string,
          });
          break;
      }
    };

    ws.onclose = () => {
      if (this.pingTimer) {
        clearInterval(this.pingTimer);
        this.pingTimer = null;
      }
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

export const notificationSocket = new NotificationSocketClient();
