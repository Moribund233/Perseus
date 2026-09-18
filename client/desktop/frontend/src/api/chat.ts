import { proxyRequest, apiRequest } from './client';

export interface ChatMessage {
  id: string;
  room_id: string;
  sender_id: string;
  sender_username: string;
  message_type: string;
  content: string;
  reply_to: string | null;
  edited_at: string | null;
  created_at: string | null;
  reactions?: { emoji: string; count: number; active: boolean }[];
}

export interface RoomMember {
  id: string;
  room_id: string;
  user_id: string;
  username: string;
  role: string;
  joined_at: string | null;
  is_muted: boolean;
}

export interface MessagesResponse {
  messages: ChatMessage[];
  has_more: boolean;
  next_before: string | null;
}

export interface RealtimeRoom {
  id: string;
  repository_id: string | null;
  name: string;
  topic: string | null;
  room_type: string;
  is_active: boolean;
  created_at: string | null;
}

export interface ChatAttachment {
  name: string;
  size: number;
  content_type: string;
  url: string;
}

export interface RoomUnread {
  room_id: string;
  repository_id: string;
  room_name: string;
  unread_count: number;
}

export interface DMSession {
  room_id: string;
  room_name: string;
  room_type: string;
  peer_user_id: string;
  peer_username: string;
  created_at: string | null;
  unread_count: number;
}

export interface MessageSearchHit {
  id: string;
  room_id: string;
  room_name: string;
  room_type: string;
  repository_id: string | null;
  sender_id: string;
  sender_username: string;
  message_type: string;
  content: string;
  reply_to: string | null;
  created_at: string | null;
  reactions?: { emoji: string; count: number; active: boolean }[];
}

export interface MessageSearchResponse {
  messages: MessageSearchHit[];
}

// chatApi：桌面端聊天 REST，全部经本地网关 proxy 转发，首个参数为服务器 id。
export const chatApi = {
  getRoomMessages: (serverId: string, roomId: string, params?: { limit?: number; before?: string }) => {
    const qs = params ? '?' + new URLSearchParams(params as Record<string, string>).toString() : '';
    return proxyRequest<MessagesResponse>(serverId, `/api/v1/rooms/${roomId}/messages${qs}`);
  },

  getRoomMembers: (serverId: string, roomId: string) =>
    proxyRequest<RoomMember[]>(serverId, `/api/v1/rooms/${roomId}/members`),

  deleteMessage: (serverId: string, roomId: string, msgId: string) =>
    proxyRequest<void>(serverId, `/api/v1/rooms/${roomId}/messages/${msgId}`, { method: 'DELETE' }),

  addReaction: (serverId: string, roomId: string, msgId: string, emoji: string) =>
    proxyRequest<ChatMessage>(serverId, `/api/v1/rooms/${roomId}/messages/${msgId}/reactions`, {
      method: 'POST',
      body: JSON.stringify({ emoji }),
    }),

  removeReaction: (serverId: string, roomId: string, msgId: string, emoji: string) =>
    proxyRequest<ChatMessage>(serverId, `/api/v1/rooms/${roomId}/messages/${msgId}/reactions`, {
      method: 'DELETE',
      body: JSON.stringify({ emoji }),
    }),

  getRepositoryRoom: (serverId: string, repoId: string) =>
    proxyRequest<RealtimeRoom>(serverId, `/api/v1/repositories/${repoId}/room`),

  listRooms: (serverId: string) =>
    proxyRequest<RealtimeRoom[]>(serverId, '/api/v1/rooms'),

  getUnreadCounts: (serverId: string) =>
    proxyRequest<RoomUnread[]>(serverId, '/api/v1/rooms/unread'),

  markRead: (serverId: string, roomId: string) =>
    proxyRequest<{ success: boolean }>(serverId, `/api/v1/rooms/${roomId}/read`, { method: 'POST' }),

  searchMessages: (serverId: string, q: string, limit = 20) =>
    proxyRequest<MessageSearchResponse>(serverId, `/api/v1/messages/search?q=${encodeURIComponent(q)}&limit=${limit}`),

  uploadAttachment: (serverId: string, roomId: string, file: File) => {
    const form = new FormData();
    form.append('file', file);
    return apiRequest<ChatAttachment>(`/api/local/proxy/${serverId}/api/v1/rooms/${roomId}/attachments`, {
      method: 'POST',
      body: form,
    });
  },
};

// dmApi：桌面端私聊，经本地网关 proxy 转发。
export const dmApi = {
  listDms: (serverId: string) =>
    proxyRequest<DMSession[]>(serverId, '/api/v1/dm'),

  createDm: (serverId: string, peerUserId: string) =>
    proxyRequest<RealtimeRoom>(serverId, '/api/v1/dm', {
      method: 'POST',
      body: JSON.stringify({ peer_user_id: peerUserId }),
    }),
};
