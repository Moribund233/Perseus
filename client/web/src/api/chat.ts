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
  repository_id: string;
  name: string;
  topic: string | null;
  is_active: boolean;
  created_at: string | null;
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

  getRepositoryRoom: (repoId: string) =>
    apiRequest<RealtimeRoom>(`/api/v1/repositories/${repoId}/room`),
};
