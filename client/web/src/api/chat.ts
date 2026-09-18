import { apiRequest } from './client';

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

export const chatApi = {
  getRoomMessages: (roomId: string, params?: { limit?: number; before?: string }) => {
    const qs = params ? '?' + new URLSearchParams(params as Record<string, string>).toString() : '';
    return apiRequest<MessagesResponse>(`/api/v1/rooms/${roomId}/messages${qs}`);
  },

  getRoomMembers: (roomId: string) =>
    apiRequest<RoomMember[]>(`/api/v1/rooms/${roomId}/members`),

  deleteMessage: (roomId: string, msgId: string) =>
    apiRequest<void>(`/api/v1/rooms/${roomId}/messages/${msgId}`, { method: 'DELETE' }),

  addReaction: (roomId: string, msgId: string, emoji: string) =>
    apiRequest<ChatMessage>(`/api/v1/rooms/${roomId}/messages/${msgId}/reactions`, {
      method: 'POST',
      body: JSON.stringify({ emoji }),
    }),

  removeReaction: (roomId: string, msgId: string, emoji: string) =>
    apiRequest<ChatMessage>(`/api/v1/rooms/${roomId}/messages/${msgId}/reactions`, {
      method: 'DELETE',
      body: JSON.stringify({ emoji }),
    }),

  getRepositoryRoom: (repoId: string) =>
    apiRequest<RealtimeRoom>(`/api/v1/repositories/${repoId}/room`),

  searchMessages: (q: string, limit = 20) =>
    apiRequest<MessageSearchResponse>(
      `/api/v1/messages/search?q=${encodeURIComponent(q)}&limit=${limit}`
    ),

  getUnreadCounts: () =>
    apiRequest<RoomUnread[]>('/api/v1/rooms/unread'),

  markRead: (roomId: string) =>
    apiRequest<{ success: boolean }>(`/api/v1/rooms/${roomId}/read`, { method: 'POST' }),

  uploadAttachment: (roomId: string, file: File) => {
    const form = new FormData();
    form.append('file', file);
    return apiRequest<ChatAttachment>(`/api/v1/rooms/${roomId}/attachments`, {
      method: 'POST',
      body: form,
    });
  },
};

export const dmApi = {
  listDms: () => apiRequest<DMSession[]>('/api/v1/dm'),

  createDm: (peerUserId: string) =>
    apiRequest<RealtimeRoom>('/api/v1/dm', {
      method: 'POST',
      body: JSON.stringify({ peer_user_id: peerUserId }),
    }),
};
