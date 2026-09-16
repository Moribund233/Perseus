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
  watch_count: number;
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
  last_commit?: {
    hash: string;
    message: string;
    author: string;
    date: string;
  } | null;
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

export interface BranchProtectionSettings {
  require_code_review: boolean;
  require_status_checks: boolean;
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

export interface FileCommitResponse {
  commit_id: string;
  branch: string;
  path: string;
}

export const repositoriesApi = {
  list: (params?: { page?: number; per_page?: number }) => {
    const qs = params ? '?' + new URLSearchParams(params as Record<string, string>).toString() : '';
    return apiRequest<PaginationResponse<Repository>>(`/api/v1/repositories${qs}`);
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

  checkAccess: (repoId: string, userId: string) =>
    apiRequest<{ has_access: boolean; role?: string }>(`/api/v1/repositories/${repoId}/access?user_id=${encodeURIComponent(userId)}`),

  getTree: async (repoId: string, ref?: string, path?: string) => {
    const params = new URLSearchParams();
    if (ref) params.set('ref', ref);
    if (path) params.set('path', path);
    // 逐文件附带最近提交, 保证任意层级文件树 last-commit 列均有数据
    params.set('last_commit', 'true');
    const qs = params.toString() ? `?${params.toString()}` : '';
    const data = await apiRequest<{ entries: Array<{ name: string; path: string; type: 'tree' | 'blob' | 'symlink'; size?: number; sha?: string; last_commit?: RepoFile['last_commit'] }> }>(
      `/api/v1/repositories/${repoId}/tree${qs}`
    );
    return data.entries.map((e) => ({
      ...e,
      type: e.type === 'tree' ? ('directory' as const) : e.type === 'blob' ? ('file' as const) : e.type,
    }));
  },

  getBlob: (repoId: string, path: string, ref?: string) => {
    const qs = `?path=${encodeURIComponent(path)}${ref ? `&ref=${encodeURIComponent(ref)}` : ''}`;
    return apiRequest<RepoBlob>(`/api/v1/repositories/${repoId}/blob${qs}`);
  },

  commitFile: (repoId: string, path: string, data: { content: string; message?: string; branch?: string }) => {
    // 保留路径分隔符, 仅对各段做 URI 编码 (后端 {file_path:path} 路由)
    const encoded = path.split('/').map(encodeURIComponent).join('/');
    return apiRequest<FileCommitResponse>(`/api/v1/repositories/${repoId}/contents/${encoded}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  deleteFile: (repoId: string, path: string, branch?: string) => {
    const encoded = path.split('/').map(encodeURIComponent).join('/');
    const qs = branch ? `?branch=${encodeURIComponent(branch)}` : '';
    return apiRequest<FileCommitResponse>(`/api/v1/repositories/${repoId}/contents/${encoded}${qs}`, {
      method: 'DELETE',
    });
  },

  moveFile: (repoId: string, data: { from_path: string; to_path: string; message?: string; branch?: string }) =>
    apiRequest<{ commit_id: string; branch: string; from: string; to: string }>(
      `/api/v1/repositories/${repoId}/contents/move`,
      {
        method: 'POST',
        body: JSON.stringify(data),
      },
    ),

  createCollabInvite: (
    repoId: string,
    data: { doc_key: string; scope?: 'read' | 'write'; ttl_minutes?: number },
  ) =>
    apiRequest<{ token: string; url: string; doc_key: string; scope: string; expires_at: string }>(
      `/api/v1/repositories/${repoId}/collab/invites`,
      {
        method: 'POST',
        body: JSON.stringify(data),
      },
    ),

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
    return apiRequest<CommitListResponse>(`/api/v1/repositories/${repoId}/commits${qs}`);
  },

  getCommitHistory: (repoId: string, params?: { page?: number; per_page?: number; branch?: string }) => {
    const qs = params ? '?' + new URLSearchParams(params as Record<string, string>).toString() : '';
    return apiRequest<RepoCommit[]>(`/api/v1/repositories/${repoId}/commits/history${qs}`);
  },

  getBranches: (repoId: string) =>
    apiRequest<RepoBranch[]>(`/api/v1/repositories/${repoId}/branches`),

  protectBranch: (repoId: string, branchName: string, settings: BranchProtectionSettings = { require_code_review: false, require_status_checks: false }) =>
    apiRequest<RepoBranch>(`/api/v1/repositories/${repoId}/branches/${encodeURIComponent(branchName)}/protect`, {
      method: 'PUT',
      body: JSON.stringify(settings),
    }),

  unprotectBranch: (repoId: string, branchName: string) =>
    apiRequest<RepoBranch>(`/api/v1/repositories/${repoId}/branches/${encodeURIComponent(branchName)}/unprotect`, {
      method: 'PUT',
    }),

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

  watch: (repoId: string) =>
    apiRequest<void>(`/api/v1/repositories/${repoId}/watch`, { method: 'POST' }),

  unwatch: (repoId: string) =>
    apiRequest<void>(`/api/v1/repositories/${repoId}/watch`, { method: 'DELETE' }),

  getWatchStatus: (repoId: string) =>
    apiRequest<{ watching: boolean; watch_count: number }>(`/api/v1/repositories/${repoId}/watch`),

  getWatchers: (repoId: string) =>
    apiRequest<{ id: string; user_id: string; created_at: string | null }[]>(`/api/v1/repositories/${repoId}/watchers`),

  fork: (repoId: string, data?: { name?: string; description?: string; is_public?: boolean }) =>
    apiRequest<Repository>(`/api/v1/repositories/${repoId}/forks`, {
      method: 'POST',
      // FastAPI 对 Pydantic body 参数要求请求体存在, 即使所有字段可选
      body: JSON.stringify(data ?? {}),
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

  checkMemberPermission: (repoId: string, userId: string, permission: string) =>
    apiRequest<{ role: string; permissions: string[] }>(`/api/v1/repositories/${repoId}/members/${userId}/permission?permission=${encodeURIComponent(permission)}`),

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
    return apiRequest<CodeSearchResponse>(`/api/v1/repositories/${repoId}/search${qs}`);
  },
};
