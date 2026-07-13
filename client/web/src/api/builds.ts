import { apiRequest } from './client';

export interface Build {
  id: number;
  repo_id: number;
  branch: string;
  commit_sha: string;
  commit_message: string;
  status: string;
  triggered_by: number;
  started_at: string | null;
  finished_at: string | null;
  details_url: string | null;
}

export interface CreateBuildRequest {
  branch: string;
  commit_sha: string;
  commit_message: string;
}

export const buildsApi = {
  list: (repoId: number, params?: { page?: number; per_page?: number; status?: string }) => {
    const qs = params ? '?' + new URLSearchParams(params as Record<string, string>).toString() : '';
    return apiRequest<Build[]>(`/api/v1/repositories/${repoId}/builds${qs}`);
  },

  get: (repoId: number, buildId: number) =>
    apiRequest<Build>(`/api/v1/repositories/${repoId}/builds/${buildId}`),

  create: (repoId: number, data: CreateBuildRequest) =>
    apiRequest<Build>(`/api/v1/repositories/${repoId}/builds`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getLogs: (repoId: number, buildId: number) =>
    apiRequest<string[]>(`/api/v1/repositories/${repoId}/builds/${buildId}/logs`),
};
