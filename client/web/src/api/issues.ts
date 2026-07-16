import { apiRequest } from './client';

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
  closed_by: string | null;
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

export const issuesApi = {
  list: (repoId: string, params?: { status?: string; page?: number; per_page?: number }) => {
    const qs = params ? '?' + new URLSearchParams(params as Record<string, string>).toString() : '';
    return apiRequest<Issue[]>(`/api/v1/repositories/${repoId}/issues${qs}`);
  },

  filter: (repoId: string, data: IssueFilter) =>
    apiRequest<Issue[]>(`/api/v1/repositories/${repoId}/issues/filter`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  get: (repoId: string, issueNumber: number) =>
    apiRequest<Issue>(`/api/v1/repositories/${repoId}/issues/${issueNumber}`),

  create: (repoId: string, data: CreateIssueRequest) =>
    apiRequest<Issue>(`/api/v1/repositories/${repoId}/issues`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  update: (repoId: string, issueNumber: number, data: UpdateIssueRequest) =>
    apiRequest<Issue>(`/api/v1/repositories/${repoId}/issues/${issueNumber}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  close: (repoId: string, issueNumber: number) =>
    apiRequest<Issue>(`/api/v1/repositories/${repoId}/issues/${issueNumber}/close`, {
      method: 'POST',
    }),

  reopen: (repoId: string, issueNumber: number) =>
    apiRequest<Issue>(`/api/v1/repositories/${repoId}/issues/${issueNumber}/reopen`, {
      method: 'POST',
    }),

  batchClose: (repoId: string, issueNumbers: number[]) =>
    apiRequest<void>(`/api/v1/repositories/${repoId}/issues/batch/close`, {
      method: 'POST',
      body: JSON.stringify({ issue_numbers: issueNumbers }),
    }),

  batchReopen: (repoId: string, issueNumbers: number[]) =>
    apiRequest<void>(`/api/v1/repositories/${repoId}/issues/batch/reopen`, {
      method: 'POST',
      body: JSON.stringify({ issue_numbers: issueNumbers }),
    }),

  getComments: (repoId: string, issueNumber: number) =>
    apiRequest<IssueComment[]>(`/api/v1/repositories/${repoId}/issues/${issueNumber}/comments`),

  createComment: (repoId: string, issueNumber: number, data: CreateIssueCommentRequest) =>
    apiRequest<IssueComment>(`/api/v1/repositories/${repoId}/issues/${issueNumber}/comments`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
};
