import { useGatewayStore } from '../stores/gateway';
import { useServersStore } from '../stores/servers';
import type { ChatMessage } from './chat';

export type ChatSocketStatus = 'connecting' | 'connected' | 'disconnected';

export interface PresenceUser {
  user_id: string;
  username: string;
}

export interface TypingEvent {
  room_id: string;
  user_id: string;
  username: string;
  is_typing: boolean;
}

interface ChatSocketHandlers {
  onChatMessage?: (msg: ChatMessage) => void;
  onAck?: (msg: ChatMessage) => void;
  onStatusChange?: (status: ChatSocketStatus) => void;
  onError?: (error: string, originalType?: string) => void;
  onPresence?: (roomId: string, users: PresenceUser[]) => void;
  onPresenceJoin?: (roomId: string, user: PresenceUser) => void;
  onPresenceLeave?: (roomId: string, user: PresenceUser) => void;
  onTyping?: (evt: TypingEvent) => void;
  onReaction?: (msg: ChatMessage) => void;
  onReactionAck?: (msg: ChatMessage) => void;
}

/**
 * 桌面端 WebSocket 客户端（经本地网关 WS 透传）。
 *
 * 与 web 版差异：
 *  - 连接地址为 <gatewayBase>/api/local/proxy/{serverId}/ws/
 *  - 网关鉴权用查询参数 _token（浏览器 WS 无法携带自定义 header）
 *  - 服务器鉴权 token 由 Go 侧在透传时注入，前端不接触 account token
 *
 * 上游协议与 web 一致（见 api/websocket/）：
 *  送出: {"type":"chat_message","room_id","content"} → 回 chat_message_ack，
 *        再被广播 chat_message
 *  送出: {"type":"room_join"/"room_leave","room_id"}
 *  送出: {"type":"chat_typing","room_id","is_typing"}
 *  送出: {"type":"presence_list","room_id"}
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

  sendReaction(roomId: string, messageId: string, emoji: string, add: boolean) {
    this.send({ type: 'chat_reaction', room_id: roomId, message_id: messageId, emoji, add });
  }

  sendTyping(roomId: string, isTyping: boolean) {
    this.send({ type: 'chat_typing', room_id: roomId, is_typing: isTyping });
  }

  requestPresenceList(roomId: string) {
    this.send({ type: 'presence_list', room_id: roomId });
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
    return `${base.replace(/^http/, 'ws')}/api/local/proxy/${serverId}/ws/?_token=${encodeURIComponent(config?.gatewayToken ?? '')}`;
  }

  private connect() {
    if (!this.enabled || !useServersStore.getState().currentServerId || this.ws) return;

    this.handlers.onStatusChange?.('connecting');
    const ws = new WebSocket(this.resolveWsUrl());
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
        case 'chat_reaction_ack':
          this.handlers.onReactionAck?.(data.message as ChatMessage);
          break;
        case 'chat_reaction':
          this.handlers.onReaction?.(data.message as ChatMessage);
          break;
        case 'presence_list':
          this.handlers.onPresence?.(data.room_id as string, (data.users ?? []) as PresenceUser[]);
          break;
        case 'presence_join': {
          const user = { user_id: data.user_id, username: data.username } as PresenceUser;
          this.handlers.onPresenceJoin?.(data.room_id as string, user);
          break;
        }
        case 'presence_leave': {
          const user = { user_id: data.user_id, username: data.username } as PresenceUser;
          this.handlers.onPresenceLeave?.(data.room_id as string, user);
          break;
        }
        case 'chat_typing':
          this.handlers.onTyping?.({
            room_id: data.room_id,
            user_id: data.user_id,
            username: data.username,
            is_typing: data.is_typing,
          } as TypingEvent);
          break;
        case 'error':
          this.handlers.onError?.(data.error as string, data.original_type as string | undefined);
          break;
      }
    };

    ws.onclose = () => {
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

export const chatSocket = new ChatSocketClient();
