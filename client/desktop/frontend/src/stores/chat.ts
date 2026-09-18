import { create } from 'zustand';
import {
  chatApi,
  dmApi,
  type ChatMessage,
  type DMSession,
  type MessageSearchHit,
  type RealtimeRoom,
  type RoomMember,
  type RoomUnread,
} from '../api/chat';
import { chatSocket, type PresenceUser } from '../api/chatSocket';
import { useServersStore } from './servers';

function serverId(): string | null {
  return useServersStore.getState().currentServerId;
}

export interface TypingUser {
  user_id: string;
  username: string;
  ts: number;
}

interface ChatState {
  rooms: RealtimeRoom[];
  messages: Record<string, ChatMessage[]>;
  members: Record<string, RoomMember[]>;
  unreadByRoom: Record<string, number>;
  unreadByRepo: Record<string, number>;
  totalUnread: number;
  activeRoomId: string | null;
  onlineUsers: Record<string, PresenceUser[]>;
  typingByRoom: Record<string, Record<string, TypingUser>>;
  status: 'idle' | 'connecting' | 'connected' | 'disconnected' | 'error';
  error: string | null;
  dms: DMSession[];
  dmLoaded: boolean;

  start: () => void;
  stop: () => void;
  reset: () => void;
  setActiveRoom: (roomId: string | null) => void;
  openChannel: (repoId: string) => Promise<void>;
  openDm: (session: DMSession) => Promise<void>;
  startDm: (peerUserId: string, peerUsername: string) => Promise<void>;
  fetchDms: () => Promise<void>;
  searchMessages: (q: string, limit?: number) => Promise<{ messages: MessageSearchHit[] }>;
  fetchRoom: (repoId: string) => Promise<RealtimeRoom | null>;
  fetchChatRooms: () => Promise<void>;
  fetchMessages: (roomId: string) => Promise<void>;
  fetchMembers: (roomId: string) => Promise<void>;
  fetchUnread: () => Promise<void>;
  sendMessage: (roomId: string, content: string, replyTo?: string) => void;
  sendTyping: (roomId: string, isTyping: boolean) => void;
  toggleReaction: (roomId: string, msgId: string, emoji: string, add: boolean) => void;
  pickReaction: (roomId: string, msgId: string, emoji: string) => Promise<void>;
  deleteMessage: (roomId: string, msgId: string) => Promise<void>;
}

function bumpUnread(
  s: ChatState,
  roomId: string,
): Partial<Pick<ChatState, 'unreadByRoom' | 'unreadByRepo' | 'totalUnread'>> {
  const byRoom = { ...s.unreadByRoom, [roomId]: (s.unreadByRoom[roomId] ?? 0) + 1 };
  const repoId = s.rooms.find((r) => r.id === roomId)?.repository_id;
  const byRepo = repoId
    ? { ...s.unreadByRepo, [repoId]: (s.unreadByRepo[repoId] ?? 0) + 1 }
    : s.unreadByRepo;
  return {
    unreadByRoom: byRoom,
    unreadByRepo: byRepo,
    totalUnread: Object.values(byRoom).reduce((a, b) => a + b, 0),
  };
}

function upsertMessage(s: ChatState, msg: ChatMessage): Record<string, ChatMessage[]> {
  const list = s.messages[msg.room_id] ?? [];
  if (list.some((m) => m.id === msg.id)) {
    return { ...s.messages, [msg.room_id]: list.map((m) => (m.id === msg.id ? msg : m)) };
  }
  return { ...s.messages, [msg.room_id]: [...list, msg] };
}

function wireSocket(set: (fn: (s: ChatState) => Partial<ChatState>) => void) {
  chatSocket.setHandlers({
    onStatusChange: (status) =>
      set(() => ({ status: status as ChatState['status'] })),
    onChatMessage: (msg) => {
      const activeRoomId = useChatStore.getState().activeRoomId;
      set((s) => ({
        messages: upsertMessage(s, msg),
        ...(activeRoomId === msg.room_id ? {} : bumpUnread(s, msg.room_id)),
      }));
      if (activeRoomId !== msg.room_id) {
        void useChatStore.getState().fetchDms();
      }
    },
    onAck: (msg) =>
      set((s) => ({ messages: upsertMessage(s, msg) })),
    onReaction: (msg) =>
      set((s) => ({ messages: upsertMessage(s, msg) })),
    onReactionAck: (msg) =>
      set((s) => ({ messages: upsertMessage(s, msg) })),
    onPresence: (roomId, users) =>
      set((s) => ({ onlineUsers: { ...s.onlineUsers, [roomId]: users } })),
    onPresenceJoin: (roomId, user) =>
      set((s) => {
        const list = s.onlineUsers[roomId] ?? [];
        if (list.some((u) => u.user_id === user.user_id)) return {};
        return { onlineUsers: { ...s.onlineUsers, [roomId]: [...list, user] } };
      }),
    onPresenceLeave: (roomId, user) =>
      set((s) => ({
        onlineUsers: {
          ...s.onlineUsers,
          [roomId]: (s.onlineUsers[roomId] ?? []).filter((u) => u.user_id !== user.user_id),
        },
      })),
    onTyping: (evt) =>
      set((s) => {
        const roomTyping = { ...(s.typingByRoom[evt.room_id] ?? {}) };
        if (evt.is_typing) {
          roomTyping[evt.user_id] = { user_id: evt.user_id, username: evt.username, ts: Date.now() };
        } else {
          delete roomTyping[evt.user_id];
        }
        return { typingByRoom: { ...s.typingByRoom, [evt.room_id]: roomTyping } };
      }),
  });
}

export const useChatStore = create<ChatState>((set, get) => ({
  rooms: [],
  messages: {},
  members: {},
  unreadByRoom: {},
  unreadByRepo: {},
  totalUnread: 0,
  activeRoomId: null,
  onlineUsers: {},
  typingByRoom: {},
  status: 'idle',
  error: null,
  dms: [],
  dmLoaded: false,

  start: () => {
    wireSocket(set);
    chatSocket.start();
  },

  stop: () => {
    chatSocket.stop();
    set({ status: 'idle' });
  },

  // 切换服务器时重置：断开旧连接并清空状态。
  reset: () => {
    chatSocket.stop();
    set({
      rooms: [],
      messages: {},
      members: {},
      unreadByRoom: {},
      unreadByRepo: {},
      totalUnread: 0,
      activeRoomId: null,
      onlineUsers: {},
      typingByRoom: {},
      status: 'idle',
      error: null,
      dms: [],
      dmLoaded: false,
    });
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
          const repoId = s.rooms.find((r) => r.id === roomId)?.repository_id;
          const byRepo = repoId ? { ...s.unreadByRepo, [repoId]: 0 } : s.unreadByRepo;
          const total = Object.values(cleared).reduce((a, b) => a + b, 0);
          return { unreadByRoom: cleared, unreadByRepo: byRepo, totalUnread: total };
        });
      }
    }
  },

  // 门户频道 = 仓库房间：进入即自动入房（服务端按仓库访问权限 auto-join）。
  openChannel: async (repoId) => {
    const room = await get().fetchRoom(repoId);
    if (!room) return;
    get().setActiveRoom(room.id);
    await Promise.all([get().fetchMessages(room.id), get().fetchMembers(room.id)]);
  },

  // 打开私聊会话：将 DM 房间并入 rooms（对齐频道渲染路径），标记已读。
  openDm: async (session) => {
    const rid = session.room_id;
    set((s) => ({
      dms: s.dms.some((d) => d.room_id === rid)
        ? s.dms.map((d) => (d.room_id === rid ? { ...d, unread_count: 0 } : d))
        : s.dms,
      rooms: s.rooms.some((r) => r.id === rid)
        ? s.rooms
        : [
            ...s.rooms,
            {
              id: rid,
              repository_id: null,
              name: session.room_name,
              topic: null,
              room_type: session.room_type,
              is_active: true,
              created_at: session.created_at,
            } as RealtimeRoom,
          ],
    }));
    get().setActiveRoom(rid);
    await Promise.all([get().fetchMessages(rid), get().fetchMembers(rid)]);
  },

  // 发起/打开与某成员的私聊（幂等：已存在则直接打开）。
  startDm: async (peerUserId, peerUsername) => {
    const sid = serverId();
    if (!sid) return;
    const existing = get().dms.find((d) => d.peer_user_id === peerUserId);
    if (existing) {
      await get().openDm(existing);
      return;
    }
    const created = await dmApi.createDm(sid, peerUserId);
    const session: DMSession = {
      room_id: created.id,
      room_name: created.name || peerUsername,
      room_type: created.room_type,
      peer_user_id: peerUserId,
      peer_username: peerUsername,
      created_at: created.created_at,
      unread_count: 0,
    };
    set((s) => ({ dms: [session, ...s.dms.filter((d) => d.room_id !== session.room_id)] }));
    await get().openDm(session);
    // 以服务端为准刷新列表顺序与名称。
    void get().fetchDms();
  },

  fetchDms: async () => {
    const sid = serverId();
    if (!sid) return;
    try {
      const items = await dmApi.listDms(sid);
      set({ dms: items });
    } catch {
      /* 离线时保留上次私聊列表 */
    } finally {
      set({ dmLoaded: true });
    }
  },

  searchMessages: async (q: string, limit = 20) => {
    const sid = serverId();
    if (!sid) return { messages: [] };
    return chatApi.searchMessages(sid, q, limit);
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

  // 聚合房间列表：后端 listRooms（已加入）+ 未读映射（按 repository_id）。
  fetchChatRooms: async () => {
    const sid = serverId();
    if (!sid) return;
    try {
      const joined = await chatApi.listRooms(sid);
      set((s) => {
        const known = new Map(s.rooms.map((r) => [r.id, r]));
        for (const r of joined) known.set(r.id, { ...known.get(r.id), ...r });
        return { rooms: Array.from(known.values()) };
      });
    } catch {
      /* 离线时保留已有房间 */
    }
    await get().fetchUnread();
  },

  fetchMessages: async (roomId) => {
    const sid = serverId();
    if (!sid) return;
    try {
      const res = await chatApi.getRoomMessages(sid, roomId, { limit: 100 });
      // 后端按 created_at 倒序返回，反转为正序展示（对齐 web 端）。
      set((s) => ({ messages: { ...s.messages, [roomId]: [...(res.messages ?? [])].reverse() } }));
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
      const byRepo: Record<string, number> = {};
      let total = 0;
      for (const u of list ?? []) {
        byRoom[u.room_id] = u.unread_count;
        byRepo[u.repository_id] = u.unread_count;
        total += u.unread_count;
      }
      set({ unreadByRoom: byRoom, unreadByRepo: byRepo, totalUnread: total });
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

  toggleReaction: (roomId, msgId, emoji, add) => {
    chatSocket.sendReaction(roomId, msgId, emoji, add);
  },

  // 表情面板追加 reaction：REST 直加（与 web 端一致），ack 后本地更新。
  pickReaction: async (roomId, msgId, emoji) => {
    const sid = serverId();
    if (!sid) return;
    try {
      const updated = await chatApi.addReaction(sid, roomId, msgId, emoji);
      set((s) => ({ messages: upsertMessage(s, updated) }));
    } catch (e) {
      set({ error: (e as Error).message });
    }
  },

  deleteMessage: async (roomId, msgId) => {
    const sid = serverId();
    if (!sid) return;
    try {
      await chatApi.deleteMessage(sid, roomId, msgId);
      set((s) => ({
        messages: {
          ...s.messages,
          [roomId]: (s.messages[roomId] ?? []).filter((m) => m.id !== msgId),
        },
      }));
    } catch (e) {
      set({ error: (e as Error).message });
    }
  },
}));

// 供 Chat 视图读取房间列表。
export function useChatRoomList(): RealtimeRoom[] {
  return useChatStore((s) => s.rooms);
}

export type { RealtimeRoom, RoomMember, RoomUnread };
