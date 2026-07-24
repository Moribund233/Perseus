import { apiRequest } from './client';

export interface Build {
  id: string;
  repo_id: string;
  branch: string;
  commit_sha: string;
  commit_message: string;
  status: string;
  triggered_by: string;
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
  list: (repoId: string, params?: { page?: number; per_page?: number; status?: string }) => {
    const qs = params ? '?' + new URLSearchParams(params as Record<string, string>).toString() : '';
    return apiRequest<Build[]>(`/api/v1/repositories/${repoId}/builds${qs}`);
  },

  get: (repoId: string, buildId: string) =>
    apiRequest<Build>(`/api/v1/repositories/${repoId}/builds/${buildId}`),

  create: (repoId: string, data: CreateBuildRequest) =>
    apiRequest<Build>(`/api/v1/repositories/${repoId}/builds`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getLogs: (repoId: string, buildId: string) =>
    apiRequest<{ logs: string }>(`/api/v1/repositories/${repoId}/builds/${buildId}/logs`),
};
