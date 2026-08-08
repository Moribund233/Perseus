import { proxyRequest } from './client';

export interface PR {
  id: string;
  repository_id: string;
  pr_number: number;
  title: string;
  description: string;
  source_branch: string;
  target_branch: string;
  author_id: string;
  status: 'open' | 'merged' | 'closed';
  is_draft: boolean;
  merged_by: string | null;
  merged_commit_hash: string | null;
  created_at: string;
  updated_at: string;
  author?: { id: string; username: string; full_name: string | null };
  labels?: { id: string; name: string; color: string; description?: string }[];
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
  id: string;
  pull_request_id: string;
  author_id: string;
  content: string;
  file_path?: string;
  line_number?: number;
  commit_hash?: string;
  parent_id?: string;
  created_at: string;
  author?: { id: string; username: string; full_name: string | null };
}

export interface CreatePRCommentRequest {
  content: string;
  file_path?: string;
  line_number?: number;
  commit_hash?: string;
  parent_id?: string;
}

export interface PRReview {
  id: string;
  pull_request_id: string;
  reviewer_id: string;
  status: 'approved' | 'changes_requested' | 'commented' | 'dismissed';
  comment: string;
  created_at: string;
  reviewer?: { id: string; username: string; full_name: string | null };
}

export interface CreatePRReviewRequest {
  status: 'approved' | 'changes_requested' | 'commented';
  comment: string;
}

export interface PaginationResponse<T> {
  items: T[];
  total: number;
  page: number;
  limit: number;
  pages: number;
  has_next: boolean;
  has_prev: boolean;
}

// pullRequestsApi：全部经本地网关 proxy 转发到目标服务器，首个参数为服务器 id。
export const pullRequestsApi = {
  list: (serverId: string, repoId: string, params?: { status?: string; page?: number; per_page?: number }) => {
    const qs = params ? '?' + new URLSearchParams(params as Record<string, string>).toString() : '';
    return proxyRequest<PaginationResponse<PR>>(serverId, `/api/v1/repositories/${repoId}/pull-requests${qs}`);
  },

  get: (serverId: string, repoId: string, prNumber: number) =>
    proxyRequest<PR>(serverId, `/api/v1/repositories/${repoId}/pull-requests/${prNumber}`),

  create: (serverId: string, repoId: string, data: CreatePRRequest) =>
    proxyRequest<PR>(serverId, `/api/v1/repositories/${repoId}/pull-requests`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  update: (serverId: string, repoId: string, prNumber: number, data: UpdatePRRequest) =>
    proxyRequest<PR>(serverId, `/api/v1/repositories/${repoId}/pull-requests/${prNumber}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  close: (serverId: string, repoId: string, prNumber: number) =>
    proxyRequest<PR>(serverId, `/api/v1/repositories/${repoId}/pull-requests/${prNumber}/close`, {
      method: 'POST',
    }),

  merge: (serverId: string, repoId: string, prNumber: number, data?: { merge_method?: 'merge' | 'squash' | 'rebase' }) =>
    proxyRequest<PR>(serverId, `/api/v1/repositories/${repoId}/pull-requests/${prNumber}/merge`, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    }),

  getComments: (serverId: string, repoId: string, prNumber: number) =>
    proxyRequest<PRComment[]>(serverId, `/api/v1/repositories/${repoId}/pull-requests/${prNumber}/comments`),

  createComment: (serverId: string, repoId: string, prNumber: number, data: CreatePRCommentRequest) =>
    proxyRequest<PRComment>(serverId, `/api/v1/repositories/${repoId}/pull-requests/${prNumber}/comments`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  createReview: (serverId: string, repoId: string, prNumber: number, data: CreatePRReviewRequest) =>
    proxyRequest<PRReview>(serverId, `/api/v1/repositories/${repoId}/pull-requests/${prNumber}/reviews`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
};