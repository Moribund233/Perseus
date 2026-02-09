# LanGit 前端 SDK 使用指南

> 本文档提供完整的前端 API 调用 SDK，包含 TypeScript 类型定义、API 封装和常用组合式函数。

## 目录

- [快速开始](#快速开始)
- [TypeScript 类型定义](#typescript-类型定义)
- [API 客户端配置](#api-客户端配置)
- [API 模块](#api-模块)
- [组合式函数 (Composables)](#组合式函数-composables)
- [错误处理](#错误处理)
- [工具函数](#工具函数)

---

## 快速开始

### 1. 安装依赖

```bash
npm install axios
```

### 2. 配置 API 客户端

```typescript
// api/client.ts
import axios from 'axios';

export const apiClient = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器 - 添加认证
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// 响应拦截器 - 统一错误处理
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token 过期，清除并跳转登录
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);
```

---

## TypeScript 类型定义

```typescript
// api/types.ts

// ==================== 通用类型 ====================

export interface ApiResponse<T> {
  data: T;
}

export interface ApiError {
  detail: string;
}

export interface PaginationParams {
  page?: number;
  limit?: number;
}

export interface PaginationResponse<T> {
  items: T[];
  pagination: {
    page: number;
    per_page: number;
    total: number;
  };
}

// ==================== 用户类型 ====================

export interface User {
  id: number;
  username: string;
  email: string;
  full_name: string | null;
  bio: string | null;
  avatar_url: string | null;
  is_active: boolean;
  is_admin: boolean;
  created_at: string;
  updated_at: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface RegisterRequest {
  username: string;
  email: string;
  password: string;
  full_name?: string;
}

export interface UpdateUserRequest {
  email?: string;
  full_name?: string;
  bio?: string;
}

export interface ChangePasswordRequest {
  old_password: string;
  new_password: string;
}

// ==================== 仓库类型 ====================

export interface Repository {
  id: number;
  name: string;
  description: string | null;
  owner_id: number;
  owner_username: string;
  is_public: boolean;
  default_branch: string;
  stars_count: number;
  forks_count: number;
  open_issues_count: number;
  created_at: string;
  updated_at: string;
}

export interface CreateRepositoryRequest {
  name: string;
  description?: string;
  is_public?: boolean;
  default_branch?: string;
}

export interface UpdateRepositoryRequest {
  name?: string;
  description?: string;
  is_public?: boolean;
}

export interface ForkRepositoryRequest {
  name?: string;
  description?: string;
  is_public?: boolean;
}

// ==================== 分支类型 ====================

export interface Branch {
  id: number;
  name: string;
  repository_id: number;
  is_protected: boolean;
  require_code_review: boolean;
  require_status_checks: boolean;
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

export interface BranchProtectionStatus {
  is_protected: boolean;
  require_code_review: boolean;
  require_status_checks: boolean;
}

export interface CreateBranchRequest {
  name: string;
  base_branch: string;
}

export interface UpdateBranchRequest {
  name: string;
}

export interface ProtectBranchRequest {
  require_code_review?: boolean;
  require_status_checks?: boolean;
}

// ==================== 提交类型 ====================

export interface Commit {
  id: number;
  hash: string;
  repository_id: number;
  branch_id: number;
  author_name: string;
  author_email: string;
  committer_name: string;
  committer_email: string;
  commit_message: string;
  commit_date: string;
  parent_hashes: string;
  created_at: string;
  updated_at: string;
}

export interface CommitCount {
  count: number;
}

export interface CommitQueryParams {
  limit?: number;
  offset?: number;
  branch_name?: string;
}

export interface CommitSearchParams {
  query: string;
  limit?: number;
}

// ==================== 文件类型 ====================

export interface FileNode {
  name: string;
  type: 'file' | 'directory';
  path: string;
  size?: number;
  mode: string;
}

export interface FileContent {
  content: string;
  encoding: 'utf-8' | 'base64';
  size: number;
  sha: string;
}

export interface DirectoryContent {
  files: FileNode[];
}

export interface DiffResult {
  old_content: string;
  new_content: string;
  diff: string;
}

// ==================== PR 类型 ====================

export interface PullRequest {
  id: number;
  number: number;
  title: string;
  description: string | null;
  repository_id: number;
  author_id: number;
  author_username: string;
  source_branch: string;
  target_branch: string;
  status: 'open' | 'merged' | 'closed';
  is_draft: boolean;
  created_at: string;
  updated_at: string;
  merged_at: string | null;
  merged_by: number | null;
  merged_by_username: string | null;
}

export interface CreatePullRequestRequest {
  title: string;
  description?: string;
  source_branch: string;
  target_branch: string;
  is_draft?: boolean;
}

export interface UpdatePullRequestRequest {
  title?: string;
  description?: string;
  is_draft?: boolean;
}

export interface PullRequestReview {
  id: number;
  pull_request_id: number;
  reviewer_id: number;
  reviewer_username: string;
  status: 'approved' | 'changes_requested' | 'commented';
  comment: string | null;
  created_at: string;
}

export interface CreateReviewRequest {
  status: 'approved' | 'changes_requested' | 'commented';
  comment?: string;
}

// ==================== Issue 类型 ====================

export interface Issue {
  id: number;
  number: number;
  title: string;
  description: string | null;
  repository_id: number;
  author_id: number;
  author_username: string;
  assignee_id: number | null;
  assignee_username: string | null;
  status: 'open' | 'closed';
  labels: Label[];
  created_at: string;
  updated_at: string;
  closed_at: string | null;
  closed_by: number | null;
  closed_by_username: string | null;
}

export interface Label {
  id: number;
  name: string;
  color: string;
  description: string | null;
}

export interface CreateIssueRequest {
  title: string;
  description?: string;
  assignee_id?: number;
  labels?: string[];
}

export interface UpdateIssueRequest {
  title?: string;
  description?: string;
  assignee_id?: number | null;
  labels?: string[];
  status?: 'open' | 'closed';
}

export interface IssueComment {
  id: number;
  issue_id: number;
  author_id: number;
  author_username: string;
  content: string;
  created_at: string;
  updated_at: string;
}

export interface CreateLabelRequest {
  name: string;
  color: string;
  description?: string;
}

// ==================== 成员类型 ====================

export interface RepositoryMember {
  id: number;
  user_id: number;
  username: string;
  full_name: string | null;
  email: string;
  role: 'owner' | 'admin' | 'developer' | 'readonly';
  is_active: boolean;
  joined_at: string;
}

export interface AddMemberRequest {
  user_id: number;
  role: 'admin' | 'developer' | 'readonly';
}

export interface UpdateMemberRequest {
  role: 'admin' | 'developer' | 'readonly';
}
```

---

## API 客户端配置

```typescript
// api/index.ts
export { apiClient } from './client';
export * from './types';
export * from './modules/auth';
export * from './modules/user';
export * from './modules/repository';
export * from './modules/branch';
export * from './modules/commit';
export * from './modules/file';
export * from './modules/pullRequest';
export * from './modules/issue';
export * from './modules/member';
```

---

## API 模块

### 认证模块

```typescript
// api/modules/auth.ts
import { apiClient } from '../client';
import type { LoginRequest, LoginResponse, RegisterRequest, User } from '../types';

export const authApi = {
  login: (data: LoginRequest) =>
    apiClient.post<LoginResponse>('/auth/login', data),

  register: (data: RegisterRequest) =>
    apiClient.post<User>('/auth/register', data),

  logout: () =>
    apiClient.post('/auth/logout'),

  refreshToken: () =>
    apiClient.post<LoginResponse>('/auth/refresh'),

  getCurrentUser: () =>
    apiClient.get<User>('/auth/me'),
};
```

### 用户模块

```typescript
// api/modules/user.ts
import { apiClient } from '../client';
import type { User, UpdateUserRequest, ChangePasswordRequest } from '../types';

export const userApi = {
  getUser: (userId: number) =>
    apiClient.get<User>(`/users/${userId}`),

  updateUser: (userId: number, data: UpdateUserRequest) =>
    apiClient.put<User>(`/users/${userId}`, data),

  deleteUser: (userId: number) =>
    apiClient.delete(`/users/${userId}`),

  changePassword: (userId: number, data: ChangePasswordRequest) =>
    apiClient.put(`/users/${userId}/password`, data),

  uploadAvatar: (userId: number, file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return apiClient.post(`/users/${userId}/avatar`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },

  listUserRepositories: (userId: number) =>
    apiClient.get(`/users/${userId}/repositories`),
};
```

### 仓库模块

```typescript
// api/modules/repository.ts
import { apiClient } from '../client';
import type { 
  Repository, 
  CreateRepositoryRequest, 
  UpdateRepositoryRequest,
  ForkRepositoryRequest,
  PaginationParams 
} from '../types';

export const repositoryApi = {
  listRepositories: (params?: PaginationParams & { search?: string }) =>
    apiClient.get<Repository[]>('/repositories', { params }),

  getRepository: (repoId: number) =>
    apiClient.get<Repository>(`/repositories/${repoId}`),

  createRepository: (data: CreateRepositoryRequest) =>
    apiClient.post<Repository>('/repositories', data),

  updateRepository: (repoId: number, data: UpdateRepositoryRequest) =>
    apiClient.put<Repository>(`/repositories/${repoId}`, data),

  deleteRepository: (repoId: number) =>
    apiClient.delete(`/repositories/${repoId}`),

  forkRepository: (repoId: number, data?: ForkRepositoryRequest) =>
    apiClient.post<Repository>(`/repositories/${repoId}/fork`, data),

  starRepository: (repoId: number) =>
    apiClient.post(`/repositories/${repoId}/star`),

  unstarRepository: (repoId: number) =>
    apiClient.delete(`/repositories/${repoId}/star`),

  checkStarStatus: (repoId: number) =>
    apiClient.get<{ is_starred: boolean }>(`/repositories/${repoId}/star`),
};
```

### 分支模块

```typescript
// api/modules/branch.ts
import { apiClient } from '../client';
import type { 
  Branch, 
  BranchProtectionStatus,
  CreateBranchRequest,
  UpdateBranchRequest,
  ProtectBranchRequest 
} from '../types';

export const branchApi = {
  getBranches: (repoId: number) =>
    apiClient.get<Branch[]>(`/repositories/${repoId}/branches`),

  getDefaultBranch: (repoId: number) =>
    apiClient.get<Branch>(`/repositories/${repoId}/branches/default`),

  getBranch: (repoId: number, branchName: string) =>
    apiClient.get<Branch>(`/repositories/${repoId}/branches/${encodeURIComponent(branchName)}`),

  createBranch: (repoId: number, data: CreateBranchRequest) =>
    apiClient.post<Branch>(`/repositories/${repoId}/branches`, data),

  updateBranch: (repoId: number, branchName: string, data: UpdateBranchRequest) =>
    apiClient.put<Branch>(`/repositories/${repoId}/branches/${encodeURIComponent(branchName)}`, data),

  deleteBranch: (repoId: number, branchName: string) =>
    apiClient.delete(`/repositories/${repoId}/branches/${encodeURIComponent(branchName)}`),

  setDefaultBranch: (repoId: number, branchName: string) =>
    apiClient.put(`/repositories/${repoId}/branches/${encodeURIComponent(branchName)}/default`),

  protectBranch: (repoId: number, branchName: string, data?: ProtectBranchRequest) =>
    apiClient.put<Branch>(`/repositories/${repoId}/branches/${encodeURIComponent(branchName)}/protect`, data),

  unprotectBranch: (repoId: number, branchName: string) =>
    apiClient.put<Branch>(`/repositories/${repoId}/branches/${encodeURIComponent(branchName)}/unprotect`),

  checkProtection: (repoId: number, branchName: string) =>
    apiClient.get<BranchProtectionStatus>(`/repositories/${repoId}/branches/${encodeURIComponent(branchName)}/protection`),
};
```

### 提交模块

```typescript
// api/modules/commit.ts
import { apiClient } from '../client';
import type { Commit, CommitCount, CommitQueryParams, CommitSearchParams } from '../types';

export const commitApi = {
  getCommits: (repoId: number, params?: CommitQueryParams) =>
    apiClient.get<Commit[]>(`/repositories/${repoId}/commits`, { params }),

  getCommitHistory: (repoId: number, branchName?: string, limit?: number) =>
    apiClient.get<Commit[]>(`/repositories/${repoId}/commits/history`, { 
      params: { branch_name: branchName, limit } 
    }),

  getCommitCount: (repoId: number) =>
    apiClient.get<CommitCount>(`/repositories/${repoId}/commits/count`),

  searchCommits: (repoId: number, params: CommitSearchParams) =>
    apiClient.get<Commit[]>(`/repositories/${repoId}/commits/search`, { params }),

  getCommitsByAuthor: (repoId: number, authorEmail: string, limit?: number) =>
    apiClient.get<Commit[]>(`/repositories/${repoId}/commits/author`, { 
      params: { author_email: authorEmail, limit } 
    }),

  getLatestCommit: (repoId: number, branchName?: string) =>
    apiClient.get<Commit>(`/repositories/${repoId}/commits/latest`, { 
      params: { branch_name: branchName } 
    }),

  getCommitDetail: (repoId: number, commitHash: string) =>
    apiClient.get<Commit>(`/repositories/${repoId}/commits/${commitHash}`),

  getBranchCommits: (repoId: number, branchName: string, params?: CommitQueryParams) =>
    apiClient.get<Commit[]>(`/repositories/${repoId}/branches/${encodeURIComponent(branchName)}/commits`, { params }),

  getBranchCommitCount: (repoId: number, branchName: string) =>
    apiClient.get<CommitCount>(`/repositories/${repoId}/branches/${encodeURIComponent(branchName)}/commits/count`),
};
```

### 文件模块

```typescript
// api/modules/file.ts
import { apiClient } from '../client';
import type { FileNode, FileContent, DirectoryContent, DiffResult } from '../types';

export const fileApi = {
  getFileTree: (repoId: number, branchName: string = 'main', path: string = '') =>
    apiClient.get<FileNode[]>(`/repositories/${repoId}/tree`, {
      params: { branch_name: branchName, path },
    }),

  getFileContent: (repoId: number, branchName: string, filePath: string) =>
    apiClient.get<FileContent>(`/repositories/${repoId}/content`, {
      params: { branch_name: branchName, file_path: filePath },
    }),

  getDirectoryContent: (repoId: number, branchName: string, dirPath: string) =>
    apiClient.get<DirectoryContent>(`/repositories/${repoId}/directory`, {
      params: { branch_name: branchName, dir_path: dirPath },
    }),

  getDiff: (repoId: number, sourceBranch: string, targetBranch: string, filePath?: string) =>
    apiClient.get<DiffResult>(`/repositories/${repoId}/diff`, {
      params: { 
        source_branch: sourceBranch, 
        target_branch: targetBranch,
        file_path: filePath 
      },
    }),
};
```

### PR 模块

```typescript
// api/modules/pullRequest.ts
import { apiClient } from '../client';
import type { 
  PullRequest, 
  CreatePullRequestRequest, 
  UpdatePullRequestRequest,
  PullRequestReview,
  CreateReviewRequest,
  PaginationParams 
} from '../types';

export const pullRequestApi = {
  listPullRequests: (repoId: number, params?: PaginationParams & { status?: string }) =>
    apiClient.get<PullRequest[]>(`/repositories/${repoId}/pull-requests`, { params }),

  getPullRequest: (repoId: number, prNumber: number) =>
    apiClient.get<PullRequest>(`/repositories/${repoId}/pull-requests/${prNumber}`),

  createPullRequest: (repoId: number, data: CreatePullRequestRequest) =>
    apiClient.post<PullRequest>(`/repositories/${repoId}/pull-requests`, data),

  updatePullRequest: (repoId: number, prNumber: number, data: UpdatePullRequestRequest) =>
    apiClient.put<PullRequest>(`/repositories/${repoId}/pull-requests/${prNumber}`, data),

  closePullRequest: (repoId: number, prNumber: number) =>
    apiClient.put<PullRequest>(`/repositories/${repoId}/pull-requests/${prNumber}/close`),

  reopenPullRequest: (repoId: number, prNumber: number) =>
    apiClient.put<PullRequest>(`/repositories/${repoId}/pull-requests/${prNumber}/reopen`),

  mergePullRequest: (repoId: number, prNumber: number, commitMessage?: string) =>
    apiClient.put<PullRequest>(`/repositories/${repoId}/pull-requests/${prNumber}/merge`, {
      commit_message: commitMessage,
    }),

  listReviews: (repoId: number, prNumber: number) =>
    apiClient.get<PullRequestReview[]>(`/repositories/${repoId}/pull-requests/${prNumber}/reviews`),

  createReview: (repoId: number, prNumber: number, data: CreateReviewRequest) =>
    apiClient.post<PullRequestReview>(`/repositories/${repoId}/pull-requests/${prNumber}/reviews`, data),
};
```

### Issue 模块

```typescript
// api/modules/issue.ts
import { apiClient } from '../client';
import type { 
  Issue, 
  Label,
  CreateIssueRequest, 
  UpdateIssueRequest,
  IssueComment,
  CreateLabelRequest,
  PaginationParams 
} from '../types';

export const issueApi = {
  listIssues: (repoId: number, params?: PaginationParams & { status?: string; label?: string }) =>
    apiClient.get<Issue[]>(`/repositories/${repoId}/issues`, { params }),

  getIssue: (repoId: number, issueNumber: number) =>
    apiClient.get<Issue>(`/repositories/${repoId}/issues/${issueNumber}`),

  createIssue: (repoId: number, data: CreateIssueRequest) =>
    apiClient.post<Issue>(`/repositories/${repoId}/issues`, data),

  updateIssue: (repoId: number, issueNumber: number, data: UpdateIssueRequest) =>
    apiClient.put<Issue>(`/repositories/${repoId}/issues/${issueNumber}`, data),

  closeIssue: (repoId: number, issueNumber: number) =>
    apiClient.put<Issue>(`/repositories/${repoId}/issues/${issueNumber}/close`),

  reopenIssue: (repoId: number, issueNumber: number) =>
    apiClient.put<Issue>(`/repositories/${repoId}/issues/${issueNumber}/reopen`),

  listComments: (repoId: number, issueNumber: number) =>
    apiClient.get<IssueComment[]>(`/repositories/${repoId}/issues/${issueNumber}/comments`),

  createComment: (repoId: number, issueNumber: number, content: string) =>
    apiClient.post<IssueComment>(`/repositories/${repoId}/issues/${issueNumber}/comments`, { content }),

  updateComment: (repoId: number, issueNumber: number, commentId: number, content: string) =>
    apiClient.put<IssueComment>(`/repositories/${repoId}/issues/${issueNumber}/comments/${commentId}`, { content }),

  deleteComment: (repoId: number, issueNumber: number, commentId: number) =>
    apiClient.delete(`/repositories/${repoId}/issues/${issueNumber}/comments/${commentId}`),

  listLabels: (repoId: number) =>
    apiClient.get<Label[]>(`/repositories/${repoId}/labels`),

  createLabel: (repoId: number, data: CreateLabelRequest) =>
    apiClient.post<Label>(`/repositories/${repoId}/labels`, data),

  updateLabel: (repoId: number, labelName: string, data: Partial<CreateLabelRequest>) =>
    apiClient.put<Label>(`/repositories/${repoId}/labels/${encodeURIComponent(labelName)}`, data),

  deleteLabel: (repoId: number, labelName: string) =>
    apiClient.delete(`/repositories/${repoId}/labels/${encodeURIComponent(labelName)}`),
};
```

### 成员模块

```typescript
// api/modules/member.ts
import { apiClient } from '../client';
import type { RepositoryMember, AddMemberRequest, UpdateMemberRequest } from '../types';

export const memberApi = {
  listMembers: (repoId: number) =>
    apiClient.get<RepositoryMember[]>(`/repositories/${repoId}/members`),

  addMember: (repoId: number, data: AddMemberRequest) =>
    apiClient.post<RepositoryMember>(`/repositories/${repoId}/members`, data),

  updateMember: (repoId: number, userId: number, data: UpdateMemberRequest) =>
    apiClient.put<RepositoryMember>(`/repositories/${repoId}/members/${userId}`, data),

  removeMember: (repoId: number, userId: number) =>
    apiClient.delete(`/repositories/${repoId}/members/${userId}`),
};
```

---

## 组合式函数 (Composables)

### 使用分支

```typescript
// composables/useBranches.ts
import { ref, onMounted } from 'vue';
import { branchApi } from '@/api';
import type { Branch, CreateBranchRequest } from '@/api';

export function useBranches(repoId: number) {
  const branches = ref<Branch[]>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);

  const fetchBranches = async () => {
    loading.value = true;
    error.value = null;
    try {
      const { data } = await branchApi.getBranches(repoId);
      branches.value = data;
    } catch (err: any) {
      error.value = err.response?.data?.detail || '获取分支列表失败';
    } finally {
      loading.value = false;
    }
  };

  const createBranch = async (data: CreateBranchRequest) => {
    try {
      const { data: newBranch } = await branchApi.createBranch(repoId, data);
      branches.value.push(newBranch);
      return newBranch;
    } catch (err: any) {
      throw new Error(err.response?.data?.detail || '创建分支失败');
    }
  };

  const deleteBranch = async (branchName: string) => {
    try {
      await branchApi.deleteBranch(repoId, branchName);
      branches.value = branches.value.filter(b => b.name !== branchName);
    } catch (err: any) {
      throw new Error(err.response?.data?.detail || '删除分支失败');
    }
  };

  onMounted(fetchBranches);

  return {
    branches,
    loading,
    error,
    fetchBranches,
    createBranch,
    deleteBranch,
  };
}
```

### 使用提交

```typescript
// composables/useCommits.ts
import { ref } from 'vue';
import { commitApi } from '@/api';
import type { Commit, CommitQueryParams } from '@/api';

export function useCommits(repoId: number) {
  const commits = ref<Commit[]>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);
  const hasMore = ref(true);
  const offset = ref(0);
  const limit = 20;

  const fetchCommits = async (params?: CommitQueryParams, reset = false) => {
    if (reset) {
      offset.value = 0;
      commits.value = [];
      hasMore.value = true;
    }

    if (!hasMore.value && !reset) return;

    loading.value = true;
    error.value = null;

    try {
      const { data } = await commitApi.getCommits(repoId, {
        limit,
        offset: offset.value,
        ...params,
      });

      if (data.length < limit) {
        hasMore.value = false;
      }

      commits.value.push(...data);
      offset.value += data.length;
    } catch (err: any) {
      error.value = err.response?.data?.detail || '获取提交列表失败';
    } finally {
      loading.value = false;
    }
  };

  const searchCommits = async (query: string) => {
    loading.value = true;
    error.value = null;

    try {
      const { data } = await commitApi.searchCommits(repoId, { query, limit: 50 });
      commits.value = data;
      hasMore.value = false;
    } catch (err: any) {
      error.value = err.response?.data?.detail || '搜索提交失败';
    } finally {
      loading.value = false;
    }
  };

  return {
    commits,
    loading,
    error,
    hasMore,
    fetchCommits,
    searchCommits,
  };
}
```

### 使用 PR

```typescript
// composables/usePullRequests.ts
import { ref, onMounted } from 'vue';
import { pullRequestApi } from '@/api';
import type { PullRequest, CreatePullRequestRequest } from '@/api';

export function usePullRequests(repoId: number, status?: string) {
  const pullRequests = ref<PullRequest[]>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);

  const fetchPullRequests = async () => {
    loading.value = true;
    error.value = null;
    try {
      const { data } = await pullRequestApi.listPullRequests(repoId, { status });
      pullRequests.value = data;
    } catch (err: any) {
      error.value = err.response?.data?.detail || '获取 PR 列表失败';
    } finally {
      loading.value = false;
    }
  };

  const createPullRequest = async (data: CreatePullRequestRequest) => {
    try {
      const { data: newPR } = await pullRequestApi.createPullRequest(repoId, data);
      pullRequests.value.unshift(newPR);
      return newPR;
    } catch (err: any) {
      throw new Error(err.response?.data?.detail || '创建 PR 失败');
    }
  };

  const mergePullRequest = async (prNumber: number, commitMessage?: string) => {
    try {
      const { data } = await pullRequestApi.mergePullRequest(repoId, prNumber, commitMessage);
      const index = pullRequests.value.findIndex(pr => pr.number === prNumber);
      if (index !== -1) {
        pullRequests.value[index] = data;
      }
      return data;
    } catch (err: any) {
      throw new Error(err.response?.data?.detail || '合并 PR 失败');
    }
  };

  onMounted(fetchPullRequests);

  return {
    pullRequests,
    loading,
    error,
    fetchPullRequests,
    createPullRequest,
    mergePullRequest,
  };
}
```

### 使用 Issue

```typescript
// composables/useIssues.ts
import { ref, onMounted } from 'vue';
import { issueApi } from '@/api';
import type { Issue, CreateIssueRequest, Label } from '@/api';

export function useIssues(repoId: number, status?: string) {
  const issues = ref<Issue[]>([]);
  const labels = ref<Label[]>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);

  const fetchIssues = async () => {
    loading.value = true;
    error.value = null;
    try {
      const { data } = await issueApi.listIssues(repoId, { status });
      issues.value = data;
    } catch (err: any) {
      error.value = err.response?.data?.detail || '获取 Issue 列表失败';
    } finally {
      loading.value = false;
    }
  };

  const fetchLabels = async () => {
    try {
      const { data } = await issueApi.listLabels(repoId);
      labels.value = data;
    } catch (err: any) {
      console.error('获取标签列表失败:', err);
    }
  };

  const createIssue = async (data: CreateIssueRequest) => {
    try {
      const { data: newIssue } = await issueApi.createIssue(repoId, data);
      issues.value.unshift(newIssue);
      return newIssue;
    } catch (err: any) {
      throw new Error(err.response?.data?.detail || '创建 Issue 失败');
    }
  };

  const closeIssue = async (issueNumber: number) => {
    try {
      const { data } = await issueApi.closeIssue(repoId, issueNumber);
      const index = issues.value.findIndex(i => i.number === issueNumber);
      if (index !== -1) {
        issues.value[index] = data;
      }
      return data;
    } catch (err: any) {
      throw new Error(err.response?.data?.detail || '关闭 Issue 失败');
    }
  };

  onMounted(() => {
    fetchIssues();
    fetchLabels();
  });

  return {
    issues,
    labels,
    loading,
    error,
    fetchIssues,
    fetchLabels,
    createIssue,
    closeIssue,
  };
}
```

---

## 错误处理

### 统一错误处理函数

```typescript
// utils/errorHandler.ts
import type { AxiosError } from 'axios';

export interface ApiErrorResponse {
  detail: string;
}

export function handleApiError(error: AxiosError<ApiErrorResponse>): string {
  if (!error.response) {
    return '网络连接失败，请检查网络';
  }

  const { status, data } = error.response;

  switch (status) {
    case 400:
      return data?.detail || '请求参数错误';
    case 401:
      return '登录已过期，请重新登录';
    case 403:
      return '您没有权限执行此操作';
    case 404:
      return '请求的资源不存在';
    case 409:
      return data?.detail || '资源冲突';
    case 422:
      return data?.detail || '请求参数错误';
    case 429:
      return '操作太频繁，请稍后再试';
    case 500:
      return '服务器繁忙，请稍后重试';
    default:
      return data?.detail || '操作失败，请重试';
  }
}

// 使用示例
import { handleApiError } from '@/utils/errorHandler';

try {
  await api.someOperation();
} catch (error: any) {
  const message = handleApiError(error);
  // 显示错误消息
  ElMessage.error(message);
}
```

---

## 工具函数

### 提交相关

```typescript
// utils/commit.ts

/**
 * 格式化提交哈希（显示短哈希）
 */
export function formatCommitHash(hash: string, length: number = 7): string {
  return hash.substring(0, length);
}

/**
 * 格式化提交日期（显示相对时间）
 */
export function formatCommitDate(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diff = now.getTime() - date.getTime();

  const seconds = Math.floor(diff / 1000);
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);

  if (seconds < 60) return '刚刚';
  if (minutes < 60) return `${minutes}分钟前`;
  if (hours < 24) return `${hours}小时前`;
  if (days < 30) return `${days}天前`;
  if (days < 365) return `${Math.floor(days / 30)}个月前`;

  return date.toLocaleDateString('zh-CN');
}

/**
 * 解析提交信息（提取标题和描述）
 */
export function parseCommitMessage(message: string): { title: string; body: string } {
  const lines = message.split('\n');
  const title = lines[0];
  const body = lines.slice(2).join('\n'); // 跳过空行
  return { title, body };
}
```

### 文件相关

```typescript
// utils/file.ts

/**
 * 获取文件扩展名
 */
export function getFileExtension(filename: string): string {
  return filename.slice(((filename.lastIndexOf('.') - 1) >>> 0) + 2);
}

/**
 * 格式化文件大小
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * 根据扩展名判断文件类型
 */
export function getFileType(filename: string): 'image' | 'code' | 'text' | 'binary' {
  const ext = getFileExtension(filename).toLowerCase();
  
  const imageExts = ['jpg', 'jpeg', 'png', 'gif', 'svg', 'webp', 'bmp'];
  const codeExts = ['js', 'ts', 'vue', 'jsx', 'tsx', 'py', 'java', 'go', 'rs', 'cpp', 'c', 'h', 'php', 'rb'];
  const textExts = ['txt', 'md', 'json', 'xml', 'yaml', 'yml', 'csv'];
  
  if (imageExts.includes(ext)) return 'image';
  if (codeExts.includes(ext)) return 'code';
  if (textExts.includes(ext)) return 'text';
  return 'binary';
}
```

---

## 使用示例

### 在 Vue 组件中使用

```vue
<template>
  <div class="branch-list">
    <div v-if="loading" class="loading">加载中...</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else>
      <div 
        v-for="branch in branches" 
        :key="branch.id"
        class="branch-item"
        :class="{ 'is-default': branch.is_default, 'is-protected': branch.is_protected }"
      >
        <span class="branch-name">{{ branch.name }}</span>
        <span v-if="branch.is_default" class="badge default">默认</span>
        <span v-if="branch.is_protected" class="badge protected">受保护</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useBranches } from '@/composables/useBranches';

const props = defineProps<{
  repoId: number;
}>();

const { branches, loading, error } = useBranches(props.repoId);
</script>
```

---

## 目录结构建议

```
src/
├── api/
│   ├── client.ts          # Axios 客户端配置
│   ├── index.ts           # API 导出
│   ├── types.ts           # TypeScript 类型定义
│   └── modules/
│       ├── auth.ts
│       ├── user.ts
│       ├── repository.ts
│       ├── branch.ts
│       ├── commit.ts
│       ├── file.ts
│       ├── pullRequest.ts
│       ├── issue.ts
│       └── member.ts
├── composables/
│   ├── useBranches.ts
│   ├── useCommits.ts
│   ├── usePullRequests.ts
│   ├── useIssues.ts
│   └── ...
└── utils/
    ├── errorHandler.ts
    ├── commit.ts
    └── file.ts
```
