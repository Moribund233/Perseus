import { create } from 'zustand';
import {
  chatApi,
  type ChatMessage,
  type RealtimeRoom,
  type RoomMember,
  type RoomUnread,
} from '../api/chat';
import { chatSocket } from '../api/chatSocket';
import { useServersStore } from './servers';

function serverId(): string | null {
  return useServersStore.getState().currentServerId;
}

interface ChatState {
  rooms: RealtimeRoom[];
  messages: Record<string, ChatMessage[]>;
  members: Record<string, RoomMember[]>;
  unreadByRoom: Record<string, number>;
  totalUnread: number;
  activeRoomId: string | null;
  status: 'idle' | 'connecting' | 'connected' | 'disconnected' | 'error';
  error: string | null;

  start: () => void;
  stop: () => void;
  setActiveRoom: (roomId: string | null) => void;
  fetchRoom: (repoId: string) => Promise<RealtimeRoom | null>;
  fetchMessages: (roomId: string) => Promise<void>;
  fetchMembers: (roomId: string) => Promise<void>;
  fetchUnread: () => Promise<void>;
  sendMessage: (roomId: string, content: string, replyTo?: string) => void;
  sendTyping: (roomId: string, isTyping: boolean) => void;
}

function wireSocket(set: (fn: (s: ChatState) => Partial<ChatState>) => void) {
  chatSocket.setHandlers({
    onStatusChange: (status) =>
      set(() => ({ status: status as ChatState['status'] })),
    onChatMessage: (msg) =>
      set((s) => ({
        messages: {
          ...s.messages,
          [msg.room_id]: [...(s.messages[msg.room_id] ?? []).filter((m) => m.id !== msg.id), msg],
        },
        unreadByRoom:
          s.activeRoomId === msg.room_id
            ? s.unreadByRoom
            : { ...s.unreadByRoom, [msg.room_id]: (s.unreadByRoom[msg.room_id] ?? 0) + 1 },
      })),
    onAck: (msg) =>
      set((s) => ({
        messages: {
          ...s.messages,
          [msg.room_id]: [...(s.messages[msg.room_id] ?? []).filter((m) => m.id !== msg.id), msg],
        },
      })),
    onReaction: (msg) =>
      set((s) => ({
        messages: {
          ...s.messages,
          [msg.room_id]: (s.messages[msg.room_id] ?? []).map((m) =>
            m.id === msg.id ? msg : m),
        },
      })),
    onReactionAck: (msg) =>
      set((s) => ({
        messages: {
          ...s.messages,
          [msg.room_id]: (s.messages[msg.room_id] ?? []).map((m) =>
            m.id === msg.id ? msg : m),
        },
      })),
  });
}

export const useChatStore = create<ChatState>((set, get) => ({
  rooms: [],
  messages: {},
  members: {},
  unreadByRoom: {},
  totalUnread: 0,
  activeRoomId: null,
  status: 'idle',
  error: null,

  start: () => {
    wireSocket(set);
    chatSocket.start();
  },

  stop: () => {
    chatSocket.stop();
    set({ status: 'idle' });
  },

  setActiveRoom: (roomId) => {
    set({ activeRoomId: roomId });
    if (roomId) {
      chatSocket.joinRoom(roomId);
      chatSocket.requestPresenceList(roomId);
      const sid = serverId();
      if (sid) {
        void chatApi.markRead(sid, roomId);
        set((s) => {
          const cleared = { ...s.unreadByRoom, [roomId]: 0 };
          const total = Object.values(cleared).reduce((a, b) => a + b, 0);
          return { unreadByRoom: cleared, totalUnread: total };
        });
      }
    }
  },

  fetchRoom: async (repoId) => {
    const sid = serverId();
    if (!sid) return null;
    try {
      const room = await chatApi.getRepositoryRoom(sid, repoId);
      set((s) => ({
        rooms: s.rooms.some((x) => x.id === room.id)
          ? s.rooms.map((x) => (x.id === room.id ? room : x))
          : [...s.rooms, room],
      }));
      return room;
    } catch (e) {
      set({ error: (e as Error).message });
      return null;
    }
  },

  fetchMessages: async (roomId) => {
    const sid = serverId();
    if (!sid) return;
    try {
      const res = await chatApi.getRoomMessages(sid, roomId, { limit: 100 });
      set((s) => ({ messages: { ...s.messages, [roomId]: res.messages ?? [] } }));
    } catch (e) {
      set({ error: (e as Error).message });
    }
  },

  fetchMembers: async (roomId) => {
    const sid = serverId();
    if (!sid) return;
    try {
      const members = await chatApi.getRoomMembers(sid, roomId);
      set((s) => ({ members: { ...s.members, [roomId]: members } }));
    } catch (e) {
      set({ error: (e as Error).message });
    }
  },

  fetchUnread: async () => {
    const sid = serverId();
    if (!sid) return;
    try {
      const list = await chatApi.getUnreadCounts(sid);
      const byRoom: Record<string, number> = {};
      let total = 0;
      for (const u of list ?? []) {
        byRoom[u.room_id] = u.unread_count;
        total += u.unread_count;
      }
      set({ unreadByRoom: byRoom, totalUnread: total });
    } catch {
      /* 离线时保留上次未读数 */
    }
  },

  sendMessage: (roomId, content, replyTo) => {
    chatSocket.sendChatMessage(roomId, content, replyTo);
  },

  sendTyping: (roomId, isTyping) => {
    chatSocket.sendTyping(roomId, isTyping);
  },
}));

// 供 Chat 视图初始化房间列表——留空占位，后续 UI 接入后由仓库/房间聚合填充。
export function useChatRoomList(): RealtimeRoom[] {
  return useChatStore((s) => s.rooms);
}

export type { RealtimeRoom, RoomMember, RoomUnread };
