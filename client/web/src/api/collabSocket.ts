import { useAuthStore } from '../stores/auth';

export type CollabSocketStatus = 'connecting' | 'connected' | 'disconnected';

export interface CollabParticipant {
  clientID: string;
  user_id: string;
  username: string;
  cursor: { anchor: number; head: number } | null;
}

/** 服务端广播的变更集列表 (CM6 ChangeSet.toJSON 格式) */
export interface CollabUpdateMsg {
  docKey: string;
  changes: unknown[][];
  clientID: string | null;
  version: number;
}

export interface CollabSavedMsg {
  docKey: string;
  commit_id: string;
  path: string;
  branch: string;
  saved_by: string;
  message: string;
}

export interface CollabCursorMsg {
  docKey: string;
  clientID: string;
  user_id: string;
  username: string;
  anchor: number;
  head: number;
  version: number | null;
}

export interface CollabRejectMsg {
  docKey: string;
  version: number;
  changes: { changes: unknown[]; clientID: string }[];
  resync: boolean;
}

interface CollabSocketHandlers {
  onStatusChange?: (status: CollabSocketStatus) => void;
  onInit?: (msg: {
    docKey: string;
    doc: string;
    version: number;
    participants: CollabParticipant[];
  }) => void;
  onUpdate?: (msg: CollabUpdateMsg) => void;
  onReject?: (msg: CollabRejectMsg) => void;
  onCursor?: (msg: CollabCursorMsg) => void;
  onPeerJoined?: (msg: { docKey: string; clientID: string; user_id: string; username: string }) => void;
  onPeerLeft?: (msg: { docKey: string; user_id: string | null }) => void;
  onSaved?: (msg: CollabSavedMsg) => void;
  onResync?: (docKey: string) => void;
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
 * 协作编辑 WebSocket 客户端 (F-204)
 *
 * 协议 (后端 api/websocket/handlers/collab.py):
 *   连接:  /ws/collab?token=<jwt> (必需认证)
 *   加入:  {"type": "collab_join", repository_id, branch, path, clientID} -> collab_init
 *   推送:  {"type": "collab_push", docKey, version, changes[], clientID} -> collab_update 广播
 *   拉取:  {"type": "collab_pull", docKey, version}                      -> collab_update | collab_resync
 *   光标:  {"type": "collab_cursor", docKey, anchor, head}               -> collab_cursor 广播
 *   保存:  {"type": "collab_save", docKey, message}                      -> collab_saved 广播
 *   离开:  {"type": "collab_leave", docKey}                              -> collab_peer_left 广播
 *   过期:  服务端返回 collab_reject {version, changes} — 客户端 rebase 后重发
 *   断线:  指数退避自动重连
 */
class CollabSocketClient {
  private ws: WebSocket | null = null;
  private handlers: CollabSocketHandlers = {};
  private reconnectAttempts = 0;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private enabled = false;

  setHandlers(handlers: CollabSocketHandlers) {
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

  joinDoc(docKey: string, repositoryId: string, branch: string, path: string, clientID: string) {
    this.send({ type: 'collab_join', repository_id: repositoryId, branch, path, clientID, docKey });
  }

  leaveDoc(docKey: string) {
    this.send({ type: 'collab_leave', docKey });
  }

  push(docKey: string, version: number, changes: unknown[][], clientID: string) {
    this.send({ type: 'collab_push', docKey, version, changes, clientID });
  }

  pull(docKey: string, version: number) {
    this.send({ type: 'collab_pull', docKey, version });
  }

  sendCursor(docKey: string, anchor: number, head: number, version: number) {
    this.send({ type: 'collab_cursor', docKey, anchor, head, version });
  }

  saveDoc(docKey: string, message: string) {
    this.send({ type: 'collab_save', docKey, message });
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
    const ws = new WebSocket(`${resolveWsUrl()}/ws/collab?token=${encodeURIComponent(token ?? '')}`);
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
        case 'collab_init':
          this.handlers.onInit?.({
            docKey: data.docKey as string,
            doc: data.doc as string,
            version: data.version as number,
            participants: (data.participants ?? []) as CollabParticipant[],
          });
          break;
        case 'collab_update':
          this.handlers.onUpdate?.({
            docKey: data.docKey as string,
            changes: (data.changes ?? []) as unknown[][],
            clientID: (data.clientID as string | null) ?? null,
            version: data.version as number,
          });
          break;
        case 'collab_reject':
          this.handlers.onReject?.({
            docKey: data.docKey as string,
            version: data.version as number,
            changes: (data.changes ?? []) as CollabRejectMsg['changes'],
            resync: Boolean(data.resync),
          });
          break;
        case 'collab_cursor':
          this.handlers.onCursor?.(data as unknown as CollabCursorMsg);
          break;
        case 'collab_peer_joined':
          this.handlers.onPeerJoined?.({
            docKey: data.docKey as string,
            clientID: data.clientID as string,
            user_id: data.user_id as string,
            username: data.username as string,
          });
          break;
        case 'collab_peer_left':
          this.handlers.onPeerLeft?.({
            docKey: data.docKey as string,
            user_id: (data.user_id as string | null) ?? null,
          });
          break;
        case 'collab_saved':
          this.handlers.onSaved?.(data as unknown as CollabSavedMsg);
          break;
        case 'collab_resync':
          this.handlers.onResync?.(data.docKey as string);
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

export const collabSocket = new CollabSocketClient();
