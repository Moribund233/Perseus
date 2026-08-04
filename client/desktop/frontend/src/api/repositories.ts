import { proxyRequest } from './client';

export interface Repository {
  id: string;
  name: string;
  path: string;
  description: string;
  is_public: boolean;
  owner_id: string;
  default_branch: string;
  fork_count: number;
  star_count: number;
  is_archived: boolean;
  created_at: string;
  updated_at: string;
  owner?: { id: string; username: string; full_name: string | null };
  physical_exists?: boolean;
  status?: { initialized: boolean };
}

export interface CreateRepoRequest {
  name: string;
  description?: string;
  is_public?: boolean;
}

export interface UpdateRepoRequest {
  name?: string;
  description?: string;
  is_public?: boolean;
  default_branch?: string;
}

export interface RepoFile {
  name: string;
  path: string;
  type: 'file' | 'directory' | 'symlink';
  size?: number;
  sha?: string;
}

export interface RepoBlob {
  content: string;
  encoding: string;
  path: string;
  size: number;
}

export interface RepoBranch {
  id: string;
  name: string;
  commit_hash: string;
  is_default: boolean;
  is_protected: boolean;
}

export interface RepoCommit {
  id: string;
  hash: string;
  message: string;
  author_name: string;
  author_email: string;
  author_date: string;
}

export interface RepoMember {
  id: string;
  user_id: string;
  repository_id: string;
  role: string;
  is_active: boolean;
  user?: { id: string; username: string; full_name: string | null };
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

export interface CommitListResponse {
  commits: Array<{
    sha: string;
    message: string;
    author: { name: string; email: string; date: string };
    committer?: { name: string; email: string; date: string };
    parents?: string[];
  }>;
  pagination: { page: number; per_page: number };
}

export interface CodeSearchResult {
  path: string;
  line: number;
  content: string;
}

export interface CodeSearchResponse {
  results: CodeSearchResult[];
  total_count: number;
  truncated: boolean;
}

// repositoriesApi：全部经本地网关 proxy 转发到目标服务器，首个参数为服务器 id。
export const repositoriesApi = {
  list: (serverId: string, params?: { page?: number; per_page?: number }) => {
    const qs = params ? '?' + new URLSearchParams(params as Record<string, string>).toString() : '';
    return proxyRequest<PaginationResponse<Repository>>(serverId, `/api/v1/repositories${qs}`);
  },

  listPublic: (serverId: string, params?: { page?: number; per_page?: number }) => {
    const qs = params ? '?' + new URLSearchParams(params as Record<string, string>).toString() : '';
    return proxyRequest<Repository[]>(serverId, `/api/v1/repositories/public${qs}`);
  },

  listByUser: (serverId: string, userId: string) =>
    proxyRequest<Repository[]>(serverId, `/api/v1/repositories/user/${userId}`),

  get: (serverId: string, repoId: string) =>
    proxyRequest<Repository>(serverId, `/api/v1/repositories/${repoId}`),

  getByPath: (serverId: string, owner: string, repo: string) =>
    proxyRequest<Repository>(serverId, `/api/v1/repositories/${owner}/${repo}`),

  create: (serverId: string, data: CreateRepoRequest) =>
    proxyRequest<Repository>(serverId, '/api/v1/repositories', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  update: (serverId: string, repoId: string, data: UpdateRepoRequest) =>
    proxyRequest<Repository>(serverId, `/api/v1/repositories/${repoId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  delete: (serverId: string, repoId: string) =>
    proxyRequest<void>(serverId, `/api/v1/repositories/${repoId}`, { method: 'DELETE' }),

  archive: (serverId: string, repoId: string) =>
    proxyRequest<void>(serverId, `/api/v1/repositories/${repoId}/archive`, { method: 'POST' }),

  unarchive: (serverId: string, repoId: string) =>
    proxyRequest<void>(serverId, `/api/v1/repositories/${repoId}/unarchive`, { method: 'POST' }),

  checkAccess: (serverId: string, repoId: string, userId: string) =>
    proxyRequest<{ has_access: boolean; role?: string }>(serverId, `/api/v1/repositories/${repoId}/access?user_id=${encodeURIComponent(userId)}`),

  getTree: async (serverId: string, repoId: string, ref?: string, path?: string) => {
    const params = new URLSearchParams();
    if (ref) params.set('ref', ref);
    if (path) params.set('path', path);
    const qs = params.toString() ? `?${params.toString()}` : '';
    const data = await proxyRequest<{ entries: Array<{ name: string; path: string; type: 'tree' | 'blob' | 'symlink'; size?: number; sha?: string }> }>(
      serverId,
      `/api/v1/repositories/${repoId}/tree${qs}`
    );
    return data.entries.map((e) => ({
      ...e,
      type: e.type === 'tree' ? ('directory' as const) : e.type === 'blob' ? ('file' as const) : e.type,
    }));
  },

  getBlob: (serverId: string, repoId: string, path: string, ref?: string) => {
    const qs = `?path=${encodeURIComponent(path)}${ref ? `&ref=${encodeURIComponent(ref)}` : ''}`;
    return proxyRequest<RepoBlob>(serverId, `/api/v1/repositories/${repoId}/blob${qs}`);
  },

  getReadme: (serverId: string, repoId: string, ref?: string) => {
    const qs = ref ? `?ref=${encodeURIComponent(ref)}` : '';
    return proxyRequest<{ content: string; encoding: string }>(serverId, `/api/v1/repositories/${repoId}/readme${qs}`);
  },

  getCommits: (serverId: string, repoId: string, params?: { page?: number; per_page?: number; branch?: string }) => {
    const qparams: Record<string, string> = {};
    if (params?.page) qparams['page'] = String(params.page);
    if (params?.per_page) qparams['per_page'] = String(params.per_page);
    if (params?.branch) qparams['ref'] = params.branch;
    const qs = Object.keys(qparams).length ? '?' + new URLSearchParams(qparams).toString() : '';
    return proxyRequest<CommitListResponse>(serverId, `/api/v1/repositories/${repoId}/commits${qs}`);
  },

  getCommitHistory: (serverId: string, repoId: string, params?: { page?: number; per_page?: number; branch?: string }) => {
    const qs = params ? '?' + new URLSearchParams(params as Record<string, string>).toString() : '';
    return proxyRequest<RepoCommit[]>(serverId, `/api/v1/repositories/${repoId}/commits/history${qs}`);
  },

  getBranches: (serverId: string, repoId: string) =>
    proxyRequest<RepoBranch[]>(serverId, `/api/v1/repositories/${repoId}/branches`),

  getDefaultBranch: (serverId: string, repoId: string) =>
    proxyRequest<RepoBranch>(serverId, `/api/v1/repositories/${repoId}/branches/default`),

  star: (serverId: string, repoId: string) =>
    proxyRequest<void>(serverId, `/api/v1/repositories/${repoId}/star`, { method: 'POST' }),

  unstar: (serverId: string, repoId: string) =>
    proxyRequest<void>(serverId, `/api/v1/repositories/${repoId}/star`, { method: 'DELETE' }),

  getStarStatus: (serverId: string, repoId: string) =>
    proxyRequest<{ starred: boolean }>(serverId, `/api/v1/repositories/${repoId}/star`),

  getStargazers: (serverId: string, repoId: string) =>
    proxyRequest<{ id: string; username: string }[]>(serverId, `/api/v1/repositories/${repoId}/stargazers`),

  fork: (serverId: string, repoId: string, data?: { name?: string; description?: string; is_public?: boolean }) =>
    proxyRequest<Repository>(serverId, `/api/v1/repositories/${repoId}/forks`, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    }),

  listForks: (serverId: string, repoId: string) =>
    proxyRequest<Repository[]>(serverId, `/api/v1/repositories/${repoId}/forks`),

  getForkSource: (serverId: string, repoId: string) =>
    proxyRequest<Repository>(serverId, `/api/v1/repositories/${repoId}/forks/source`),

  syncFork: (serverId: string, repoId: string) =>
    proxyRequest<void>(serverId, `/api/v1/repositories/${repoId}/forks/sync`, { method: 'POST' }),

  getMembers: (serverId: string, repoId: string) =>
    proxyRequest<RepoMember[]>(serverId, `/api/v1/repositories/${repoId}/members`),

  addMember: (serverId: string, repoId: string, data: { user_id: string; role: string }) =>
    proxyRequest<RepoMember>(serverId, `/api/v1/repositories/${repoId}/members`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  updateMember: (serverId: string, repoId: string, userId: string, data: { role: string }) =>
    proxyRequest<RepoMember>(serverId, `/api/v1/repositories/${repoId}/members/${userId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  removeMember: (serverId: string, repoId: string, userId: string) =>
    proxyRequest<void>(serverId, `/api/v1/repositories/${repoId}/members/${userId}`, { method: 'DELETE' }),

  checkMemberPermission: (serverId: string, repoId: string, userId: string, permission: string) =>
    proxyRequest<{ role: string; permissions: string[] }>(serverId, `/api/v1/repositories/${repoId}/members/${userId}/permission?permission=${encodeURIComponent(permission)}`),

  getStats: (serverId: string, repoId: string) =>
    proxyRequest<Record<string, unknown>>(serverId, `/api/v1/repositories/${repoId}/stats`),

  getActivities: (serverId: string, repoId: string, params?: { page?: number; per_page?: number }) => {
    const qs = params ? '?' + new URLSearchParams(params as Record<string, string>).toString() : '';
    return proxyRequest<Record<string, unknown>[]>(serverId, `/api/v1/repositories/${repoId}/activities${qs}`);
  },

  getLabels: (serverId: string, repoId: string) =>
    proxyRequest<{ id: string; name: string; color: string; description?: string }[]>(serverId, `/api/v1/repositories/${repoId}/labels`),

  createLabel: (serverId: string, repoId: string, data: { name: string; color: string; description?: string }) =>
    proxyRequest<{ id: string; name: string; color: string; description?: string }>(serverId, `/api/v1/repositories/${repoId}/labels`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  searchCode: (serverId: string, repoId: string, query: string) => {
    const qs = `?q=${encodeURIComponent(query)}`;
    return proxyRequest<CodeSearchResponse>(serverId, `/api/v1/repositories/${repoId}/search${qs}`);
  },
};
