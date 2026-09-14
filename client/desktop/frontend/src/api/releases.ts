import { proxyRequest, proxyRequestBlob } from './client';

export interface ReleaseAsset {
  id: string;
  release_id: string;
  name: string;
  file_size: number;
  content_type: string;
  uploader_id: string;
  download_count?: number;
  created_at: string;
}

export interface Release {
  id: string;
  repository_id: string;
  release_number: number;
  tag_name: string;
  name: string;
  description: string;
  commit_hash: string;
  author_id: string;
  is_draft: boolean;
  is_prerelease: boolean;
  created_at: string;
  author?: { id: string; username: string; full_name: string | null };
  assets?: ReleaseAsset[];
}

export interface CreateReleaseRequest {
  tag_name: string;
  name: string;
  description?: string;
  commit_hash?: string;
  is_draft?: boolean;
  is_prerelease?: boolean;
  create_git_tag?: boolean;
}

export interface PaginationResponse<T> {
  items: T[];
  total: number;
  page: number;
  limit: number;
  pages: number;
  has_next: boolean;
  has_prev: boolean;
}

// releasesApi：Release 管理，经本地网关 proxy 转发到目标服务器。
export const releasesApi = {
  list: (serverId: string, repoId: string, params?: { include_drafts?: boolean; include_prereleases?: boolean; page?: number; limit?: number }) => {
    const qparams: Record<string, string> = {};
    if (params?.include_drafts) qparams['include_drafts'] = 'true';
    if (params?.include_prereleases === false) qparams['include_prereleases'] = 'false';
    if (params?.page) qparams['page'] = String(params.page);
    if (params?.limit) qparams['limit'] = String(params.limit);
    const qs = Object.keys(qparams).length ? '?' + new URLSearchParams(qparams).toString() : '';
    return proxyRequest<PaginationResponse<Release>>(serverId, `/api/v1/repositories/${repoId}/releases${qs}`);
  },

  create: (serverId: string, repoId: string, data: CreateReleaseRequest) =>
    proxyRequest<Release>(serverId, `/api/v1/repositories/${repoId}/releases`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  update: (serverId: string, repoId: string, releaseNumber: number, data: Partial<CreateReleaseRequest>) =>
    proxyRequest<Release>(serverId, `/api/v1/repositories/${repoId}/releases/${releaseNumber}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  delete: (serverId: string, repoId: string, releaseNumber: number) =>
    proxyRequest<void>(serverId, `/api/v1/repositories/${repoId}/releases/${releaseNumber}`, {
      method: 'DELETE',
    }),

  uploadAsset: (serverId: string, repoId: string, releaseNumber: number, file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return proxyRequest<ReleaseAsset>(
      serverId,
      `/api/v1/repositories/${repoId}/releases/${releaseNumber}/assets/upload`,
      { method: 'POST', body: formData },
    );
  },

  deleteAsset: (serverId: string, repoId: string, releaseNumber: number, assetId: string) =>
    proxyRequest<void>(
      serverId,
      `/api/v1/repositories/${repoId}/releases/${releaseNumber}/assets/${assetId}`,
      { method: 'DELETE' },
    ),

  // 附件下载: 网关 REST 鉴权仅认 header, 需经 fetch 拉取 blob 再触发保存
  downloadAsset: async (serverId: string, repoId: string, releaseNumber: number, assetId: string, filename: string) => {
    const blob = await proxyRequestBlob(
      serverId,
      `/api/v1/repositories/${repoId}/releases/${releaseNumber}/assets/${assetId}/download`,
    );
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  },
};
