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
  languages?: Record<string, number>;
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
  last_commit?: { hash: string; message: string; author: string; date: string } | null;
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

// ==================== Git 浏览器（Diff / Blame / Graph / Compare / Tag） ====================

export interface DiffLine {
  origin: string;
  content: string;
}

export interface DiffHunk {
  old_start: number;
  old_lines: number;
  new_start: number;
  new_lines: number;
  lines: DiffLine[];
}

export interface DiffFile {
  old_path: string;
  new_path: string;
  status: string;
  additions: number;
  deletions: number;
  hunks?: DiffHunk[];
}

export interface DiffResponse {
  files: DiffFile[];
  stats: { files_changed: number; additions: number; deletions: number };
}

export interface BlameHunk {
  final_start_line_number: number;
  lines_in_hunk: number;
  orig_start_line_number: number;
  orig_commit_id: string;
  final_commit_id: string;
  orig_path: string | null;
  boundary: boolean;
  commit: {
    sha: string;
    summary: string;
    message: string;
    author: { name: string; email: string; date: string };
  };
}

export interface BlameResponse {
  path: string;
  ref: string;
  hunks: BlameHunk[];
  is_empty?: boolean;
}

export interface CommitGraphNode {
  sha: string;
  parents: string[];
  summary: string;
  message: string;
  author: { name: string; email: string; date: string };
  committer: { name: string; email: string; date: string };
  date: string;
  labels: string[];
  is_merge: boolean;
}

export interface CommitGraphResponse {
  ref: string;
  commits: CommitGraphNode[];
  is_empty?: boolean;
}

export interface RepoTag {
  name: string;
  message: string;
  commit_hash: string;
}

export interface CompareResponse extends DiffResponse {
  base: string;
  head: string;
  merge_base: string | null;
  ahead_by: number;
  commits: CommitGraphNode[];
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

  getTree: async (serverId: string, repoId: string, ref?: string, path?: string, opts?: { last_commit?: boolean }) => {
    const params = new URLSearchParams();
    if (ref) params.set('ref', ref);
    if (path) params.set('path', path);
    if (opts?.last_commit) params.set('last_commit', 'true');
    const qs = params.toString() ? `?${params.toString()}` : '';
    const data = await proxyRequest<{ entries: Array<{ name: string; path: string; type: 'tree' | 'blob' | 'symlink'; size?: number; sha?: string; last_commit?: { hash: string; message: string; author: string; date: string } | null }> }>(
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

  getDiff: (serverId: string, repoId: string, head: string, base?: string, path?: string) => {
    const params = new URLSearchParams({ head });
    if (base) params.set('base', base);
    if (path) params.set('path', path);
    return proxyRequest<DiffResponse>(serverId, `/api/v1/repositories/${repoId}/diff?${params.toString()}`);
  },

  getBlame: (serverId: string, repoId: string, path: string, ref?: string) => {
    const params = new URLSearchParams({ path });
    if (ref) params.set('ref', ref);
    return proxyRequest<BlameResponse>(serverId, `/api/v1/repositories/${repoId}/blame?${params.toString()}`);
  },

  getGraph: (serverId: string, repoId: string, params?: { ref?: string; limit?: number }) => {
    const q = new URLSearchParams();
    if (params?.ref) q.set('ref', params.ref);
    if (params?.limit) q.set('limit', String(params.limit));
    const qs = q.toString() ? `?${q.toString()}` : '';
    return proxyRequest<CommitGraphResponse>(serverId, `/api/v1/repositories/${repoId}/graph${qs}`);
  },

  getCompare: (serverId: string, repoId: string, base: string, head: string, path?: string) => {
    const params = new URLSearchParams({ base, head });
    if (path) params.set('path', path);
    return proxyRequest<CompareResponse>(serverId, `/api/v1/repositories/${repoId}/compare?${params.toString()}`);
  },

  listTags: (serverId: string, repoId: string, pattern?: string) => {
    const qs = pattern ? `?pattern=${encodeURIComponent(pattern)}` : '';
    return proxyRequest<RepoTag[]>(serverId, `/api/v1/repositories/${repoId}/tags${qs}`);
  },

  getTag: (serverId: string, repoId: string, name: string) =>
    proxyRequest<RepoTag>(serverId, `/api/v1/repositories/${repoId}/tags/${encodeURIComponent(name)}`),

  createTag: (serverId: string, repoId: string, data: { name: string; target?: string; message?: string }) =>
    proxyRequest<RepoTag>(serverId, `/api/v1/repositories/${repoId}/tags`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  deleteTag: (serverId: string, repoId: string, name: string) =>
    proxyRequest<void>(serverId, `/api/v1/repositories/${repoId}/tags/${encodeURIComponent(name)}`, { method: 'DELETE' }),

  getBranches: (serverId: string, repoId: string) =>
    proxyRequest<RepoBranch[]>(serverId, `/api/v1/repositories/${repoId}/branches`),

  protectBranch: (serverId: string, repoId: string, branchName: string, settings: BranchProtectionSettings = { require_code_review: false, require_status_checks: false }) =>
    proxyRequest<RepoBranch>(serverId, `/api/v1/repositories/${repoId}/branches/${encodeURIComponent(branchName)}/protect`, {
      method: 'PUT',
      body: JSON.stringify(settings),
    }),

  unprotectBranch: (serverId: string, repoId: string, branchName: string) =>
    proxyRequest<RepoBranch>(serverId, `/api/v1/repositories/${repoId}/branches/${encodeURIComponent(branchName)}/unprotect`, {
      method: 'PUT',
    }),

  getDefaultBranch: (serverId: string, repoId: string) =>
    proxyRequest<RepoBranch>(serverId, `/api/v1/repositories/${repoId}/branches/default`),

  deleteBranch: (serverId: string, repoId: string, branchName: string) =>
    proxyRequest<{ message: string }>(serverId, `/api/v1/repositories/${repoId}/branches/${encodeURIComponent(branchName)}`, {
      method: 'DELETE',
    }),

  setDefaultBranch: (serverId: string, repoId: string, branchName: string) =>
    proxyRequest<RepoBranch>(serverId, `/api/v1/repositories/${repoId}/branches/${encodeURIComponent(branchName)}/default`, {
      method: 'PUT',
    }),

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

  createCollabInvite: (serverId: string, repoId: string, data: { doc_key: string; scope?: 'read' | 'write'; ttl_minutes?: number }) =>
    proxyRequest<{ token: string; url: string; doc_key: string; scope: string; expires_at: string }>(
      serverId,
      `/api/v1/repositories/${repoId}/collab/invites`,
      {
        method: 'POST',
        body: JSON.stringify(data),
      },
    ),
};
