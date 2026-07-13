import { apiRequest } from './client';

export interface Issue {
  id: number;
  repository_id: number;
  issue_number: number;
  title: string;
  description: string;
  author_id: number;
  status: 'open' | 'closed';
  priority: 'low' | 'medium' | 'high' | 'critical';
  assignee_id: number | null;
  closed_by: number | null;
  created_at: string;
  updated_at: string;
  author?: { id: number; username: string; full_name: string | null };
  assignee?: { id: number; username: string; full_name: string | null };
  labels?: { id: number; name: string; color: string; description?: string }[];
  comment_count?: number;
}

export interface CreateIssueRequest {
  title: string;
  description?: string;
  priority?: 'low' | 'medium' | 'high' | 'critical';
  assignee_id?: number;
  label_ids?: number[];
}

export interface UpdateIssueRequest {
  title?: string;
  description?: string;
  priority?: 'low' | 'medium' | 'high' | 'critical';
  assignee_id?: number | null;
  label_ids?: number[];
}

export interface IssueComment {
  id: number;
  issue_id: number;
  author_id: number;
  content: string;
  created_at: string;
  author?: { id: number; username: string; full_name: string | null };
}

export interface CreateIssueCommentRequest {
  content: string;
}

export interface IssueFilter {
  statuses?: string[];
  priorities?: string[];
  assignee_ids?: number[];
  author_ids?: number[];
  label_ids?: number[];
  search?: string;
}

export const issuesApi = {
  list: (repoId: number, params?: { status?: string; page?: number; per_page?: number }) => {
    const qs = params ? '?' + new URLSearchParams(params as Record<string, string>).toString() : '';
    return apiRequest<Issue[]>(`/api/v1/repositories/${repoId}/issues${qs}`);
  },

  filter: (repoId: number, data: IssueFilter) =>
    apiRequest<Issue[]>(`/api/v1/repositories/${repoId}/issues/filter`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  get: (repoId: number, issueNumber: number) =>
    apiRequest<Issue>(`/api/v1/repositories/${repoId}/issues/${issueNumber}`),

  create: (repoId: number, data: CreateIssueRequest) =>
    apiRequest<Issue>(`/api/v1/repositories/${repoId}/issues`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  update: (repoId: number, issueNumber: number, data: UpdateIssueRequest) =>
    apiRequest<Issue>(`/api/v1/repositories/${repoId}/issues/${issueNumber}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  close: (repoId: number, issueNumber: number) =>
    apiRequest<Issue>(`/api/v1/repositories/${repoId}/issues/${issueNumber}/close`, {
      method: 'POST',
    }),

  reopen: (repoId: number, issueNumber: number) =>
    apiRequest<Issue>(`/api/v1/repositories/${repoId}/issues/${issueNumber}/reopen`, {
      method: 'POST',
    }),

  batchClose: (repoId: number, issueNumbers: number[]) =>
    apiRequest<void>(`/api/v1/repositories/${repoId}/issues/batch/close`, {
      method: 'POST',
      body: JSON.stringify({ issue_numbers: issueNumbers }),
    }),

  batchReopen: (repoId: number, issueNumbers: number[]) =>
    apiRequest<void>(`/api/v1/repositories/${repoId}/issues/batch/reopen`, {
      method: 'POST',
      body: JSON.stringify({ issue_numbers: issueNumbers }),
    }),

  getComments: (repoId: number, issueNumber: number) =>
    apiRequest<IssueComment[]>(`/api/v1/repositories/${repoId}/issues/${issueNumber}/comments`),

  createComment: (repoId: number, issueNumber: number, data: CreateIssueCommentRequest) =>
    apiRequest<IssueComment>(`/api/v1/repositories/${repoId}/issues/${issueNumber}/comments`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
};
