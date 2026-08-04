import { apiRequest } from './client';

export interface ServerRecord {
  id: string;
  name: string;
  base_url: string;
  auth_method: 'password' | 'token';
  username?: string;
  health: 'online' | 'offline' | 'unknown';
  last_checked?: string;
  last_success?: string;
  created_at: string;
}

export interface RegisterServerInput {
  name: string;
  base_url: string;
  username?: string;
  password?: string;
  token?: string;
}

export interface UpdateServerInput {
  name?: string;
  base_url?: string;
}

export const serversApi = {
  list: () => apiRequest<ServerRecord[]>('/api/local/servers'),
  register: (data: RegisterServerInput) =>
    apiRequest<ServerRecord>('/api/local/servers', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: string, data: UpdateServerInput) =>
    apiRequest<ServerRecord>(`/api/local/servers/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  remove: (id: string) =>
    apiRequest<void>(`/api/local/servers/${id}`, { method: 'DELETE' }),
  health: (id: string) =>
    apiRequest<{ health: string }>(`/api/local/servers/${id}/health`),
  refresh: (id: string, data?: { password?: string; token?: string }) =>
    apiRequest<ServerRecord>(`/api/local/servers/${id}/refresh`, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    }),
};
