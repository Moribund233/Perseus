import { proxyRequest } from './client';

interface MyUserRef {
  id: string;
  username: string;
  full_name: string | null;
}

export interface MyPullRequest {
  id: string;
  pr_number: number;
  title: string;
  status: string;
  is_draft: boolean;
  repository_id: string;
  author: MyUserRef;
  created_at: string;
}

export interface MyIssue {
  id: string;
  issue_number: number;
  title: string;
  status: string;
  priority: string;
  repository_id: string;
  author: MyUserRef;
  assignee: MyUserRef | null;
  created_at: string;
}

export interface PaginationResponse<T> {
  items: T[];
  total: number;
  page: number;
  limit: number;
}

// myWorkApi：跨仓库聚合（我的 PR / 我的 Issue），经本地网关 proxy 转发到目标服务器。
export const myWorkApi = {
  getMyPullRequests: (serverId: string, params?: { status?: string; page?: number; limit?: number }) => {
    const qs = params ? '?' + new URLSearchParams(params as Record<string, string>).toString() : '';
    return proxyRequest<PaginationResponse<MyPullRequest>>(serverId, `/api/v1/users/me/pull-requests${qs}`);
  },

  getMyIssues: (serverId: string, params?: { status?: string; page?: number; limit?: number }) => {
    const qs = params ? '?' + new URLSearchParams(params as Record<string, string>).toString() : '';
    return proxyRequest<PaginationResponse<MyIssue>>(serverId, `/api/v1/users/me/issues${qs}`);
  },
};
