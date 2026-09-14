import { apiRequest } from './client';

export interface SearchHit {
  file: string;
  line: number;
  content: string;
}

export interface RepoSearchResult {
  repository_id: string;
  repository_name: string;
  repository_path: string;
  results: SearchHit[];
  total_count: number;
  truncated: boolean;
}

export interface GlobalSearchResponse {
  query: string;
  repositories: RepoSearchResult[];
  total_count: number;
  truncated: boolean;
}

export interface AggregateRepoHit {
  repository_id: string;
  name: string;
  path: string;
  description: string | null;
  is_public: boolean;
}

export interface AggregateIssueHit {
  repository_id: string;
  repository_name: string;
  repository_path: string;
  issue_number: number;
  title: string;
  status: string;
}

export interface AggregatePRHit {
  repository_id: string;
  repository_name: string;
  repository_path: string;
  pr_number: number;
  title: string;
  status: string;
}

export interface GlobalAggregateResponse {
  query: string;
  repositories: AggregateRepoHit[];
  issues: AggregateIssueHit[];
  pull_requests: AggregatePRHit[];
}

export const searchApi = {
  searchCode: (q: string, params?: { path?: string; max_results?: number; per_repo_max?: number }) => {
    const qs = new URLSearchParams({ q });
    if (params?.path) qs.set('path', params.path);
    if (params?.max_results != null) qs.set('max_results', String(params.max_results));
    if (params?.per_repo_max != null) qs.set('per_repo_max', String(params.per_repo_max));
    return apiRequest<GlobalSearchResponse>(`/api/v1/search/code?${qs.toString()}`);
  },
  searchGlobal: (q: string, params?: { per_type?: number }) => {
    const qs = new URLSearchParams({ q });
    if (params?.per_type != null) qs.set('per_type', String(params.per_type));
    return apiRequest<GlobalAggregateResponse>(`/api/v1/search/global?${qs.toString()}`);
  },
};