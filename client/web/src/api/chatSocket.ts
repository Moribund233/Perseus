import { useAuthStore } from '../stores/auth';
import type { ChatMessage } from './chat';

export type ChatSocketStatus = 'connecting' | 'connected' | 'disconnected';

interface ChatSocketHandlers {
  onChatMessage?: (msg: ChatMessage) => void;
  onAck?: (msg: ChatMessage) => void;
  onStatusChange?: (status: ChatSocketStatus) => void;
  onError?: (error: string, originalType?: string) => void;
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
 * 聊天 WebSocket 客户端
 *
 * 协议 (后端 api/websocket/):
 *   连接:  /ws/?token=<jwt>
 *   发送:  {"type": "chat_message", "room_id", "content"} -> 回执 chat_message_ack,
 *          房间内其他用户收到 chat_message 广播
 *   房间:  {"type": "room_join"/"room_leave", "room_id"}
 *   断线:  指数退避自动重连
 */
class ChatSocketClient {
  private ws: WebSocket | null = null;
  private handlers: ChatSocketHandlers = {};
  private reconnectAttempts = 0;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private enabled = false;

  setHandlers(handlers: ChatSocketHandlers) {
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
    this.ws?.close();
    this.ws = null;
  }

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  joinRoom(roomId: string) {
    this.send({ type: 'room_join', room_id: roomId });
  }

  leaveRoom(roomId: string) {
    this.send({ type: 'room_leave', room_id: roomId });
  }

  sendChatMessage(roomId: string, content: string, replyTo?: string) {
    this.send({ type: 'chat_message', room_id: roomId, content, reply_to: replyTo });
  }

  sendTyping(roomId: string, isTyping: boolean) {
    this.send({ type: 'chat_typing', room_id: roomId, is_typing: isTyping });
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
    const ws = new WebSocket(`${resolveWsUrl()}/ws/?token=${encodeURIComponent(token ?? '')}`);
    this.ws = ws;

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
        case 'chat_message_ack':
          this.handlers.onAck?.(data.message as ChatMessage);
          break;
        case 'chat_message':
          this.handlers.onChatMessage?.(data.message as ChatMessage);
          break;
        case 'error':
          this.handlers.onError?.(data.error as string, data.original_type as string | undefined);
          break;
      }
    };

    ws.onclose = () => {
      this.ws = null;
      this.handlers.onStatusChange?.('disconnected');
      if (this.enabled) {
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

export const chatSocket = new ChatSocketClient();
