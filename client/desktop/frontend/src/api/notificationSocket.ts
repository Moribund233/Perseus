import { useGatewayStore } from '../stores/gateway';
import { useServersStore } from '../stores/servers';
import type { Notification } from './notifications';

export type NotificationSocketStatus = 'connecting' | 'connected' | 'disconnected';

// 服务端 user_notification 推送载荷（上游 api/websocket/handlers/notification.py notify_user）
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

/**
 * 桌面端通知 WebSocket 客户端（F-205 实时推送，经本地网关 WS 透传）。
 *
 * 连接地址 <gatewayBase>/api/local/proxy/{serverId}/ws/notifications：
 *  - 网关鉴权用查询参数 _token（浏览器 WS 无法携带自定义 header）
 *  - 服务器鉴权 token 由 Go 侧透传时以 ?token= 注入，前端不接触 account token
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

  private resolveWsUrl(): string {
    const { config } = useGatewayStore.getState();
    const serverId = useServersStore.getState().currentServerId;
    const base = config?.baseURL ?? '';
    return `${base.replace(/^http/, 'ws')}/api/local/proxy/${serverId}/ws/notifications?_token=${encodeURIComponent(config?.gatewayToken ?? '')}`;
  }

  private connect() {
    if (!this.enabled || !useServersStore.getState().currentServerId || this.ws) return;

    this.handlers.onStatusChange?.('connecting');
    const ws = new WebSocket(this.resolveWsUrl());
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
      if (this.enabled && useServersStore.getState().currentServerId) {
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
