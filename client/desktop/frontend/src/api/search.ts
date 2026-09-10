import { apiRequest, proxyRequest } from './client';

export interface LocalSearchHit {
  file: string;
  line: number;
  content: string;
}

export interface LocalSearchResponse {
  query: string;
  path: string;
  results: LocalSearchHit[];
  total: number;
  truncated: boolean;
}

// workspaceSearchApi：本地工作区搜索（不经服务器，直接查本地文件）。
export const workspaceSearchApi = {
  search: (workspaceId: string, q: string, params?: { path?: string; max_results?: number }) => {
    const qs = new URLSearchParams({ q: q });
    if (params?.path) qs.set('path', params.path);
    if (params?.max_results != null) qs.set('max_results', String(params.max_results));
    return apiRequest<LocalSearchResponse>(`/api/local/workspaces/${workspaceId}/search?${qs.toString()}`);
  },
};

export interface GlobalRepoHit {
  repository_id: string;
  name: string;
  path: string;
  description: string | null;
  is_public: boolean;
}

export interface GlobalIssueHit {
  repository_id: string;
  repository_name: string;
  repository_path: string;
  issue_number: number;
  title: string;
  status: string;
}

export interface GlobalPRHit {
  repository_id: string;
  repository_name: string;
  repository_path: string;
  pr_number: number;
  title: string;
  status: string;
}

export interface GlobalSearchResponse {
  query: string;
  repositories: GlobalRepoHit[];
  issues: GlobalIssueHit[];
  pull_requests: GlobalPRHit[];
}

// globalSearchApi：门户聚合搜索（仓库/Issue/PR），经本地网关代理转发到服务器。
export const globalSearchApi = {
  search: (serverId: string, q: string, params?: { per_type?: number }) => {
    const qs = new URLSearchParams({ q });
    if (params?.per_type != null) qs.set('per_type', String(params.per_type));
    return proxyRequest<GlobalSearchResponse>(serverId, `/api/v1/search/global?${qs.toString()}`);
  },
};