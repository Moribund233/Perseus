import { apiRequest } from './client';

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