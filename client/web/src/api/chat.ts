import { apiRequest } from './client';

export interface ChatMessage {
  id: string;
  room_id: string;
  user_id: string;
  content: string;
  message_type: string;
  metadata: Record<string, unknown> | null;
  created_at: string;
  user?: { id: string; username: string; full_name: string | null };
}

export interface RoomMember {
  id: string;
  room_id: string;
  user_id: string;
  role: string;
  joined_at: string;
  user?: { id: string; username: string; full_name: string | null };
}

export interface RealtimeRoom {
  id: string;
  repository_id: string;
  name: string;
  topic: string | null;
  is_active: boolean;
}

export const chatApi = {
  getRoomMessages: (roomId: string, params?: { limit?: number; before?: number }) => {
    const qs = params ? '?' + new URLSearchParams(params as Record<string, string>).toString() : '';
    return apiRequest<ChatMessage[]>(`/api/v1/rooms/${roomId}/messages${qs}`);
  },

  getRoomMembers: (roomId: string) =>
    apiRequest<RoomMember[]>(`/api/v1/rooms/${roomId}/members`),

  deleteMessage: (roomId: string, msgId: string) =>
    apiRequest<void>(`/api/v1/rooms/${roomId}/messages/${msgId}`, { method: 'DELETE' }),

  getRepositoryRoom: (repoId: string) =>
    apiRequest<RealtimeRoom>(`/api/v1/repositories/${repoId}/room`),
};
