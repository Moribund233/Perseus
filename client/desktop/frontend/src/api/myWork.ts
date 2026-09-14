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

export interface DashboardActivity {
  id: string;
  repository_id: string;
  actor_id: string | null;
  actor_username: string | null;
  entity_type: string;
  entity_id: string | null;
  action: string;
  details: string | null;
  created_at: string;
}

// 与后端 GET /users/me/dashboard 聚合响应对齐（仅取 UI 使用字段）。
export interface DashboardData {
  repo_count: number;
  open_prs: number;
  open_issues: number;
  recent_activities: DashboardActivity[];
  /** 近 30 天按日活动聚合, key 为 "YYYY-MM-DD" */
  contributions_by_day: Record<string, number>;
}

// myWorkApi：跨仓库聚合（我的 PR / 我的 Issue / 仪表盘统计），经本地网关 proxy 转发到目标服务器。
export const myWorkApi = {
  getMyPullRequests: (serverId: string, params?: { status?: string; page?: number; limit?: number }) => {
    const qs = params ? '?' + new URLSearchParams(params as Record<string, string>).toString() : '';
    return proxyRequest<PaginationResponse<MyPullRequest>>(serverId, `/api/v1/users/me/pull-requests${qs}`);
  },

  getMyIssues: (serverId: string, params?: { status?: string; page?: number; limit?: number }) => {
    const qs = params ? '?' + new URLSearchParams(params as Record<string, string>).toString() : '';
    return proxyRequest<PaginationResponse<MyIssue>>(serverId, `/api/v1/users/me/issues${qs}`);
  },

  getDashboard: (serverId: string) =>
    proxyRequest<DashboardData>(serverId, '/api/v1/users/me/dashboard'),
};
