import { proxyRequest } from './client';

export interface PaginationResponse<T> {
  items: T[];
  total: number;
  page: number;
  limit: number;
  pages: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface Webhook {
  id: string;
  url: string;
  events: string[];
  content_type: string;
  is_active: boolean;
  last_triggered_at: string | null;
  last_response_status: number | null;
  created_at: string;
  updated_at: string;
  secret?: string;
}

export interface CreateWebhookRequest {
  url: string;
  events: string[];
  secret?: string;
  content_type?: string;
  is_active?: boolean;
}

export interface RepoMember {
  id: string;
  user_id: string;
  repository_id: string;
  role: string;
  is_active: boolean;
  user?: { id: string; username: string; full_name: string | null };
}

export interface RepoUser {
  id: string;
  username: string;
  full_name: string | null;
}

export interface AddMemberRequest {
  user_id: string;
  role: string;
}

export async function listWebhooks(serverId: string, repoId: string): Promise<Webhook[]> {
  const data = await proxyRequest<PaginationResponse<Webhook> | Webhook[]>(
    serverId,
    `/api/v1/repositories/${repoId}/webhooks`,
  );
  return Array.isArray(data) ? data : data.items;
}

export async function createWebhook(serverId: string, repoId: string, data: CreateWebhookRequest): Promise<Webhook> {
  return proxyRequest<Webhook>(serverId, `/api/v1/repositories/${repoId}/webhooks`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateWebhook(serverId: string, repoId: string, webhookId: string, data: Partial<CreateWebhookRequest>): Promise<Webhook> {
  return proxyRequest<Webhook>(serverId, `/api/v1/repositories/${repoId}/webhooks/${webhookId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

export async function deleteWebhook(serverId: string, repoId: string, webhookId: string): Promise<void> {
  return proxyRequest<void>(serverId, `/api/v1/repositories/${repoId}/webhooks/${webhookId}`, {
    method: 'DELETE',
  });
}

export async function testWebhook(serverId: string, repoId: string, webhookId: string): Promise<void> {
  return proxyRequest<void>(serverId, `/api/v1/repositories/${repoId}/webhooks/${webhookId}/test`, {
    method: 'POST',
  });
}

export async function listMembers(serverId: string, repoId: string): Promise<RepoMember[]> {
  return proxyRequest<RepoMember[]>(serverId, `/api/v1/repositories/${repoId}/members`);
}

export async function addMember(serverId: string, repoId: string, data: AddMemberRequest): Promise<RepoMember> {
  return proxyRequest<RepoMember>(serverId, `/api/v1/repositories/${repoId}/members`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateMemberRole(serverId: string, repoId: string, userId: string, role: string): Promise<RepoMember> {
  return proxyRequest<RepoMember>(serverId, `/api/v1/repositories/${repoId}/members/${userId}/role`, {
    method: 'PUT',
    body: JSON.stringify({ role }),
  });
}

export async function removeMember(serverId: string, repoId: string, userId: string): Promise<void> {
  return proxyRequest<void>(serverId, `/api/v1/repositories/${repoId}/members/${userId}`, {
    method: 'DELETE',
  });
}

export async function listUsers(serverId: string): Promise<RepoUser[]> {
  return proxyRequest<RepoUser[]>(serverId, `/api/v1/users`);
}

export const repositorySettingsApi = {
  listWebhooks,
  createWebhook,
  updateWebhook,
  deleteWebhook,
  testWebhook,
  listMembers,
  addMember,
  updateMemberRole,
  removeMember,
  listUsers,
};
