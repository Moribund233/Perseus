import { proxyRequest } from './client';

export interface Issue {
  id: string;
  repository_id: string;
  issue_number: number;
  title: string;
  description: string;
  author_id: string;
  status: 'open' | 'closed';
  priority: 'low' | 'medium' | 'high' | 'critical';
  assignee_id: string | null;
  closed_by: { id: string; username: string; full_name: string | null } | null;
  created_at: string;
  updated_at: string;
  author?: { id: string; username: string; full_name: string | null };
  assignee?: { id: string; username: string; full_name: string | null };
  labels?: { id: string; name: string; color: string; description?: string }[];
  comment_count?: number;
}

export interface CreateIssueRequest {
  title: string;
  description?: string;
  priority?: 'low' | 'medium' | 'high' | 'critical';
  assignee_id?: string;
  label_ids?: string[];
}

export interface UpdateIssueRequest {
  title?: string;
  description?: string;
  priority?: 'low' | 'medium' | 'high' | 'critical';
  assignee_id?: string | null;
  label_ids?: string[];
}

export interface IssueComment {
  id: string;
  issue_id: string;
  author_id: string;
  content: string;
  created_at: string;
  author?: { id: string; username: string; full_name: string | null };
}

export interface CreateIssueCommentRequest {
  content: string;
}

export interface IssueFilter {
  statuses?: string[];
  priorities?: string[];
  assignee_ids?: string[];
  author_ids?: string[];
  label_ids?: string[];
  search?: string;
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

// issuesApi：全部经本地网关 proxy 转发到目标服务器，首个参数为服务器 id。
export const issuesApi = {
  list: (serverId: string, repoId: string, params?: { status?: string; page?: number; per_page?: number }) => {
    const qs = params ? '?' + new URLSearchParams(params as Record<string, string>).toString() : '';
    return proxyRequest<PaginationResponse<Issue>>(serverId, `/api/v1/repositories/${repoId}/issues${qs}`);
  },

  filter: (serverId: string, repoId: string, data: IssueFilter) =>
    proxyRequest<PaginationResponse<Issue>>(serverId, `/api/v1/repositories/${repoId}/issues/filter`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  get: (serverId: string, repoId: string, issueNumber: number) =>
    proxyRequest<Issue>(serverId, `/api/v1/repositories/${repoId}/issues/${issueNumber}`),

  create: (serverId: string, repoId: string, data: CreateIssueRequest) =>
    proxyRequest<Issue>(serverId, `/api/v1/repositories/${repoId}/issues`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  update: (serverId: string, repoId: string, issueNumber: number, data: UpdateIssueRequest) =>
    proxyRequest<Issue>(serverId, `/api/v1/repositories/${repoId}/issues/${issueNumber}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  close: (serverId: string, repoId: string, issueNumber: number) =>
    proxyRequest<Issue>(serverId, `/api/v1/repositories/${repoId}/issues/${issueNumber}/close`, {
      method: 'POST',
    }),

  reopen: (serverId: string, repoId: string, issueNumber: number) =>
    proxyRequest<Issue>(serverId, `/api/v1/repositories/${repoId}/issues/${issueNumber}/reopen`, {
      method: 'POST',
    }),

  getComments: (serverId: string, repoId: string, issueNumber: number) =>
    proxyRequest<IssueComment[]>(serverId, `/api/v1/repositories/${repoId}/issues/${issueNumber}/comments`),

  createComment: (serverId: string, repoId: string, issueNumber: number, data: CreateIssueCommentRequest) =>
    proxyRequest<IssueComment>(serverId, `/api/v1/repositories/${repoId}/issues/${issueNumber}/comments`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
};