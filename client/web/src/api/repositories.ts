import { apiRequest } from './client';

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

export const repositoriesApi = {
  list: (params?: { page?: number; per_page?: number }) => {
    const qs = params ? '?' + new URLSearchParams(params as Record<string, string>).toString() : '';
    return apiRequest<Repository[]>(`/api/v1/repositories${qs}`);
  },

  listPublic: (params?: { page?: number; per_page?: number }) => {
    const qs = params ? '?' + new URLSearchParams(params as Record<string, string>).toString() : '';
    return apiRequest<Repository[]>(`/api/v1/repositories/public${qs}`);
  },

  listByUser: (userId: string) =>
    apiRequest<Repository[]>(`/api/v1/repositories/user/${userId}`),

  get: (repoId: string) =>
    apiRequest<Repository>(`/api/v1/repositories/${repoId}`),

  getByPath: (owner: string, repo: string) =>
    apiRequest<Repository>(`/api/v1/repositories/${owner}/${repo}`),

  create: (data: CreateRepoRequest) =>
    apiRequest<Repository>('/api/v1/repositories', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  update: (repoId: string, data: UpdateRepoRequest) =>
    apiRequest<Repository>(`/api/v1/repositories/${repoId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  delete: (repoId: string) =>
    apiRequest<void>(`/api/v1/repositories/${repoId}`, { method: 'DELETE' }),

  archive: (repoId: string) =>
    apiRequest<void>(`/api/v1/repositories/${repoId}/archive`, { method: 'POST' }),

  unarchive: (repoId: string) =>
    apiRequest<void>(`/api/v1/repositories/${repoId}/unarchive`, { method: 'POST' }),

  checkAccess: (repoId: string) =>
    apiRequest<{ has_access: boolean; role?: string }>(`/api/v1/repositories/${repoId}/access`),

  getTree: async (repoId: string, ref?: string, path?: string) => {
    const params = new URLSearchParams();
    if (ref) params.set('ref', ref);
    if (path) params.set('path', path);
    const qs = params.toString() ? `?${params.toString()}` : '';
    const data = await apiRequest<{ entries: RepoFile[] }>(`/api/v1/repositories/${repoId}/tree${qs}`);
    return data.entries.map((e) => ({
      ...e,
      type: e.type === 'tree' ? 'directory' as const : e.type === 'blob' ? 'file' as const : e.type,
    }));
  },

  getBlob: (repoId: string, path: string, ref?: string) => {
    const qs = `?path=${encodeURIComponent(path)}${ref ? `&ref=${encodeURIComponent(ref)}` : ''}`;
    return apiRequest<RepoBlob>(`/api/v1/repositories/${repoId}/blob${qs}`);
  },

  getReadme: (repoId: string, ref?: string) => {
    const qs = ref ? `?ref=${encodeURIComponent(ref)}` : '';
    return apiRequest<{ content: string; encoding: string }>(`/api/v1/repositories/${repoId}/readme${qs}`);
  },

  getCommits: (repoId: string, params?: { page?: number; per_page?: number; branch?: string }) => {
    const qparams: Record<string, string> = {};
    if (params?.page) qparams['page'] = String(params.page);
    if (params?.per_page) qparams['per_page'] = String(params.per_page);
    if (params?.branch) qparams['ref'] = params.branch;
    const qs = Object.keys(qparams).length ? '?' + new URLSearchParams(qparams).toString() : '';
    return apiRequest<{ commits: RepoCommit[]; pagination: { page: number; per_page: number } }>(`/api/v1/repositories/${repoId}/commits${qs}`);
  },

  getCommitHistory: (repoId: string, params?: { page?: number; per_page?: number; branch?: string }) => {
    const qs = params ? '?' + new URLSearchParams(params as Record<string, string>).toString() : '';
    return apiRequest<RepoCommit[]>(`/api/v1/repositories/${repoId}/commits/history${qs}`);
  },

  getBranches: (repoId: string) =>
    apiRequest<RepoBranch[]>(`/api/v1/repositories/${repoId}/branches`),

  getDefaultBranch: (repoId: string) =>
    apiRequest<RepoBranch>(`/api/v1/repositories/${repoId}/branches/default`),

  star: (repoId: string) =>
    apiRequest<void>(`/api/v1/repositories/${repoId}/star`, { method: 'POST' }),

  unstar: (repoId: string) =>
    apiRequest<void>(`/api/v1/repositories/${repoId}/star`, { method: 'DELETE' }),

  getStarStatus: (repoId: string) =>
    apiRequest<{ starred: boolean }>(`/api/v1/repositories/${repoId}/star`),

  getStargazers: (repoId: string) =>
    apiRequest<{ id: string; username: string }[]>(`/api/v1/repositories/${repoId}/stargazers`),

  fork: (repoId: string, data?: { name?: string; description?: string; is_public?: boolean }) =>
    apiRequest<Repository>(`/api/v1/repositories/${repoId}/forks`, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    }),

  listForks: (repoId: string) =>
    apiRequest<Repository[]>(`/api/v1/repositories/${repoId}/forks`),

  getForkSource: (repoId: string) =>
    apiRequest<Repository>(`/api/v1/repositories/${repoId}/forks/source`),

  syncFork: (repoId: string) =>
    apiRequest<void>(`/api/v1/repositories/${repoId}/forks/sync`, { method: 'POST' }),

  getMembers: (repoId: string) =>
    apiRequest<RepoMember[]>(`/api/v1/repositories/${repoId}/members`),

  addMember: (repoId: string, data: { user_id: string; role: string }) =>
    apiRequest<RepoMember>(`/api/v1/repositories/${repoId}/members`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  updateMember: (repoId: string, userId: string, data: { role: string }) =>
    apiRequest<RepoMember>(`/api/v1/repositories/${repoId}/members/${userId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  removeMember: (repoId: string, userId: string) =>
    apiRequest<void>(`/api/v1/repositories/${repoId}/members/${userId}`, { method: 'DELETE' }),

  checkMemberPermission: (repoId: string, userId: string) =>
    apiRequest<{ role: string; permissions: string[] }>(`/api/v1/repositories/${repoId}/members/${userId}/permission`),

  getStats: (repoId: string) =>
    apiRequest<Record<string, unknown>>(`/api/v1/repositories/${repoId}/stats`),

  getActivities: (repoId: string, params?: { page?: number; per_page?: number }) => {
    const qs = params ? '?' + new URLSearchParams(params as Record<string, string>).toString() : '';
    return apiRequest<Record<string, unknown>[]>(`/api/v1/repositories/${repoId}/activities${qs}`);
  },

  getLabels: (repoId: string) =>
    apiRequest<{ id: string; name: string; color: string; description?: string }[]>(`/api/v1/repositories/${repoId}/labels`),

  createLabel: (repoId: string, data: { name: string; color: string; description?: string }) =>
    apiRequest<{ id: string; name: string; color: string; description?: string }>(`/api/v1/repositories/${repoId}/labels`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  searchCode: (repoId: string, query: string) => {
    const qs = `?q=${encodeURIComponent(query)}`;
    return apiRequest<{ path: string; line: number; content: string }[]>(`/api/v1/repositories/${repoId}/search${qs}`);
  },
};
