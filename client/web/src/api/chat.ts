import { apiRequest } from './client';

export interface ChatMessage {
  id: number;
  room_id: number;
  user_id: number;
  content: string;
  message_type: string;
  metadata: Record<string, unknown> | null;
  created_at: string;
  user?: { id: number; username: string; full_name: string | null };
}

export interface RoomMember {
  id: number;
  room_id: number;
  user_id: number;
  role: string;
  joined_at: string;
  user?: { id: number; username: string; full_name: string | null };
}

export interface RealtimeRoom {
  id: number;
  repository_id: number;
  name: string;
  topic: string | null;
  is_active: boolean;
}

export const chatApi = {
  getRoomMessages: (roomId: number, params?: { limit?: number; before?: number }) => {
    const qs = params ? '?' + new URLSearchParams(params as Record<string, string>).toString() : '';
    return apiRequest<ChatMessage[]>(`/api/v1/rooms/${roomId}/messages${qs}`);
  },

  getRoomMembers: (roomId: number) =>
    apiRequest<RoomMember[]>(`/api/v1/rooms/${roomId}/members`),

  deleteMessage: (roomId: number, msgId: number) =>
    apiRequest<void>(`/api/v1/rooms/${roomId}/messages/${msgId}`, { method: 'DELETE' }),

  getRepositoryRoom: (repoId: number) =>
    apiRequest<RealtimeRoom>(`/api/v1/repositories/${repoId}/room`),
};
