import { apiRequest } from './client';

export interface PR {
  id: number;
  repository_id: number;
  pr_number: number;
  title: string;
  description: string;
  source_branch: string;
  target_branch: string;
  author_id: number;
  status: 'open' | 'merged' | 'closed';
  is_draft: boolean;
  merged_by: number | null;
  merged_commit_hash: string | null;
  created_at: string;
  updated_at: string;
  author?: { id: number; username: string; full_name: string | null };
  labels?: { id: number; name: string; color: string; description?: string }[];
  comment_count?: number;
  review_count?: number;
}

export interface CreatePRRequest {
  title: string;
  description?: string;
  source_branch: string;
  target_branch: string;
}

export interface UpdatePRRequest {
  title?: string;
  description?: string;
}

export interface PRComment {
  id: number;
  pull_request_id: number;
  author_id: number;
  content: string;
  file_path?: string;
  line_number?: number;
  commit_hash?: string;
  parent_id?: number;
  created_at: string;
  author?: { id: number; username: string; full_name: string | null };
}

export interface CreatePRCommentRequest {
  content: string;
  file_path?: string;
  line_number?: number;
  commit_hash?: string;
  parent_id?: number;
}

export interface PRReview {
  id: number;
  pull_request_id: number;
  reviewer_id: number;
  status: 'approved' | 'changes_requested' | 'commented' | 'dismissed';
  comment: string;
  created_at: string;
  reviewer?: { id: number; username: string; full_name: string | null };
}

export interface CreatePRReviewRequest {
  status: 'approved' | 'changes_requested' | 'commented';
  comment: string;
}

export const pullRequestsApi = {
  list: (repoId: number, params?: { status?: string; page?: number; per_page?: number }) => {
    const qs = params ? '?' + new URLSearchParams(params as Record<string, string>).toString() : '';
    return apiRequest<PR[]>(`/api/v1/repositories/${repoId}/pull-requests${qs}`);
  },

  get: (repoId: number, prNumber: number) =>
    apiRequest<PR>(`/api/v1/repositories/${repoId}/pull-requests/${prNumber}`),

  create: (repoId: number, data: CreatePRRequest) =>
    apiRequest<PR>(`/api/v1/repositories/${repoId}/pull-requests`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  update: (repoId: number, prNumber: number, data: UpdatePRRequest) =>
    apiRequest<PR>(`/api/v1/repositories/${repoId}/pull-requests/${prNumber}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  close: (repoId: number, prNumber: number) =>
    apiRequest<PR>(`/api/v1/repositories/${repoId}/pull-requests/${prNumber}/close`, {
      method: 'POST',
    }),

  merge: (repoId: number, prNumber: number, data?: { merge_method?: 'merge' | 'squash' | 'rebase' }) =>
    apiRequest<PR>(`/api/v1/repositories/${repoId}/pull-requests/${prNumber}/merge`, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    }),

  getComments: (repoId: number, prNumber: number) =>
    apiRequest<PRComment[]>(`/api/v1/repositories/${repoId}/pull-requests/${prNumber}/comments`),

  createComment: (repoId: number, prNumber: number, data: CreatePRCommentRequest) =>
    apiRequest<PRComment>(`/api/v1/repositories/${repoId}/pull-requests/${prNumber}/comments`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  createReview: (repoId: number, prNumber: number, data: CreatePRReviewRequest) =>
    apiRequest<PRReview>(`/api/v1/repositories/${repoId}/pull-requests/${prNumber}/reviews`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getLabels: (repoId: number) =>
    apiRequest<{ id: number; name: string; color: string; description?: string }[]>(`/api/v1/repositories/${repoId}/pr-labels`),

  createLabel: (repoId: number, data: { name: string; color: string; description?: string }) =>
    apiRequest<{ id: number; name: string; color: string; description?: string }>(`/api/v1/repositories/${repoId}/pr-labels`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  addLabel: (prId: number, labelId: number) =>
    apiRequest<void>(`/pull-requests/${prId}/labels/${labelId}`, {
      method: 'POST',
    }),

  removeLabel: (prId: number, labelId: number) =>
    apiRequest<void>(`/pull-requests/${prId}/labels/${labelId}`, {
      method: 'DELETE',
    }),
};
