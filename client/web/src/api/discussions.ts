import { apiRequest } from './client';

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

export const discussionsApi = {
  list: (
    repoId: string,
    params?: { file_path?: string; branch?: string; line_number?: number; include_resolved?: boolean },
  ) => {
    const qs = params
      ? '?' + new URLSearchParams(params as Record<string, string>).toString()
      : '';
    return apiRequest<DiscussionComment[]>(`/api/v1/repositories/${repoId}/discussions${qs}`);
  },

  create: (repoId: string, body: CreateDiscussionInput) =>
    apiRequest<DiscussionComment>(`/api/v1/repositories/${repoId}/discussions`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  resolve: (repoId: string, commentId: string, resolved: boolean) =>
    apiRequest<DiscussionComment>(`/api/v1/repositories/${repoId}/discussions/${commentId}`, {
      method: 'PATCH',
      body: JSON.stringify({ resolved }),
    }),

  remove: (repoId: string, commentId: string) =>
    apiRequest<{ success: boolean }>(`/api/v1/repositories/${repoId}/discussions/${commentId}`, {
      method: 'DELETE',
    }),
};