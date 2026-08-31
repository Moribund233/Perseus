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

export const searchApi = {
  searchCode: (q: string, params?: { path?: string; max_results?: number; per_repo_max?: number }) => {
    const qs = new URLSearchParams({ q });
    if (params?.path) qs.set('path', params.path);
    if (params?.max_results != null) qs.set('max_results', String(params.max_results));
    if (params?.per_repo_max != null) qs.set('per_repo_max', String(params.per_repo_max));
    return apiRequest<GlobalSearchResponse>(`/api/v1/search/code?${qs.toString()}`);
  },
};