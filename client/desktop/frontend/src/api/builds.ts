import { proxyRequest } from './client';

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

// buildsApi：构建记录，经本地网关 proxy 转发到目标服务器。
export const buildsApi = {
  list: (serverId: string, repoId: string, params?: { page?: number; per_page?: number; status?: string; branch?: string }) => {
    const qparams: Record<string, string> = {};
    if (params?.page) qparams['page'] = String(params.page);
    if (params?.per_page) qparams['per_page'] = String(params.per_page);
    if (params?.status) qparams['status'] = params.status;
    if (params?.branch) qparams['branch'] = params.branch;
    const qs = Object.keys(qparams).length ? '?' + new URLSearchParams(qparams).toString() : '';
    return proxyRequest<Build[]>(serverId, `/api/v1/repositories/${repoId}/builds${qs}`);
  },

  getLogs: (serverId: string, repoId: string, buildId: string) =>
    proxyRequest<{ logs: string }>(serverId, `/api/v1/repositories/${repoId}/builds/${buildId}/logs`),
};
