import { proxyRequest } from './client';

export interface DiscussionComment {
  id: string;
  repository_id: string;
  author_id: string;
  author_username: string;
  content: string;
  file_path: string;
  line_number: number | null;
  branch: string | null;
  commit_hash: string | null;
  parent_id: string | null;
  resolved: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export interface CreateDiscussionInput {
  content: string;
  file_path: string;
  line_number?: number | null;
  branch?: string | null;
  commit_hash?: string | null;
  parent_id?: string | null;
}

// discussionsApi：桌面端行内评论，经本地网关 proxy 转发。
export const discussionsApi = {
  list: (
    serverId: string,
    repoId: string,
    params?: { file_path?: string; branch?: string; line_number?: number; include_resolved?: boolean },
  ) => {
    const qs = params
      ? '?' + new URLSearchParams(params as Record<string, string>).toString()
      : '';
    return proxyRequest<DiscussionComment[]>(serverId, `/api/v1/repositories/${repoId}/discussions${qs}`);
  },

  create: (serverId: string, repoId: string, body: CreateDiscussionInput) =>
    proxyRequest<DiscussionComment>(serverId, `/api/v1/repositories/${repoId}/discussions`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  resolve: (serverId: string, repoId: string, commentId: string, resolved: boolean) =>
    proxyRequest<DiscussionComment>(serverId, `/api/v1/repositories/${repoId}/discussions/${commentId}`, {
      method: 'PATCH',
      body: JSON.stringify({ resolved }),
    }),

  remove: (serverId: string, repoId: string, commentId: string) =>
    proxyRequest<{ success: boolean }>(serverId, `/api/v1/repositories/${repoId}/discussions/${commentId}`, {
      method: 'DELETE',
    }),
};