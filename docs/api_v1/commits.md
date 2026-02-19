# 提交管理 API 设计

> 本文档提供前端开发所需的完整 API 调用指南，包含请求示例、TypeScript 类型定义和常见使用场景。

## 目录

- [提交列表](#提交列表)
- [提交历史树](#提交历史树)
- [统计提交数量](#统计提交数量)
- [搜索提交](#搜索提交)
- [根据作者获取提交](#根据作者获取提交)
- [获取最新提交](#获取最新提交)
- [获取提交详情](#获取提交详情)
- [创建提交](#创建提交)
- [获取分支提交](#获取分支提交)
- [统计分支提交数量](#统计分支提交数量)
- [TypeScript 类型定义](#typescript-类型定义)
- [前端调用示例](#前端调用示例)

---

## 提交列表

### GET /api/v1/v1/repositories/{repo_id}/commits

获取仓库的提交记录（需要认证）。

#### 请求参数

| 参数 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| repo_id | path | 是 | 仓库ID | `1` |
| limit | query | 否 | 返回记录数量限制，默认100，最大1000 | `50` |
| offset | query | 否 | 记录偏移量，默认0 | `0` |
| branch_name | query | 否 | 分支名称，默认获取所有分支 | `main` |

#### 请求头

| 参数 | 必填 | 说明 | 示例 |
|------|------|------|------|
| Authorization | 是 | Bearer Token | `Bearer eyJhbGciOiJIUzI1NiIs...` |

#### 响应

**200 OK**
```json
[
  {
    "id": 1,
    "hash": "abc123def456...",
    "repository_id": 1,
    "branch_id": 1,
    "author_name": "John Doe",
    "author_email": "john@example.com",
    "committer_name": "John Doe",
    "committer_email": "john@example.com",
    "commit_message": "Initial commit",
    "commit_date": "2024-01-01T00:00:00",
    "parent_hashes": "",
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-01-01T00:00:00"
  }
]
```

---

## 提交历史树

### GET /api/v1/v1/repositories/{repo_id}/commits/history

获取仓库的提交历史树。

#### 请求参数

| 参数 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| repo_id | path | 是 | 仓库ID | `1` |
| branch_name | query | 否 | 分支名称，默认获取所有分支 | `main` |
| limit | query | 否 | 返回记录数量限制，默认50，最大100 | `50` |

#### 响应

**200 OK**
```json
[
  {
    "id": 1,
    "hash": "abc123def456...",
    "repository_id": 1,
    "branch_id": 1,
    "author_name": "John Doe",
    "author_email": "john@example.com",
    "committer_name": "John Doe",
    "committer_email": "john@example.com",
    "commit_message": "Initial commit",
    "commit_date": "2024-01-01T00:00:00",
    "parent_hashes": "",
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-01-01T00:00:00"
  }
]
```

---

## 统计提交数量

### GET /api/v1/v1/repositories/{repo_id}/commits/count

统计仓库的提交数量。

#### 请求参数

| 参数 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| repo_id | path | 是 | 仓库ID | `1` |

#### 响应

**200 OK**
```json
{
  "count": 150
}
```

---

## 搜索提交

### GET /api/v1/v1/repositories/{repo_id}/commits/search

搜索提交记录。

#### 请求参数

| 参数 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| repo_id | path | 是 | 仓库ID | `1` |
| query | query | 是 | 搜索关键词，最小长度1 | `fix bug` |
| limit | query | 否 | 返回记录数量限制，默认50，最大100 | `30` |

#### 响应

**200 OK**
```json
[
  {
    "id": 1,
    "hash": "abc123def456...",
    "repository_id": 1,
    "branch_id": 1,
    "author_name": "John Doe",
    "author_email": "john@example.com",
    "committer_name": "John Doe",
    "committer_email": "john@example.com",
    "commit_message": "Initial commit",
    "commit_date": "2024-01-01T00:00:00",
    "parent_hashes": "",
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-01-01T00:00:00"
  }
]
```

---

## 根据作者获取提交

### GET /api/v1/v1/repositories/{repo_id}/commits/author

根据作者邮箱获取提交记录。

#### 请求参数

| 参数 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| repo_id | path | 是 | 仓库ID | `1` |
| author_email | query | 是 | 作者邮箱 | `john@example.com` |
| limit | query | 否 | 返回记录数量限制，默认50，最大100 | `30` |

#### 响应

**200 OK**
```json
[
  {
    "id": 1,
    "hash": "abc123def456...",
    "repository_id": 1,
    "branch_id": 1,
    "author_name": "John Doe",
    "author_email": "john@example.com",
    "committer_name": "John Doe",
    "committer_email": "john@example.com",
    "commit_message": "Initial commit",
    "commit_date": "2024-01-01T00:00:00",
    "parent_hashes": "",
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-01-01T00:00:00"
  }
]
```

---

## 获取最新提交

### GET /api/v1/v1/repositories/{repo_id}/commits/latest

获取仓库的最新提交。

#### 请求参数

| 参数 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| repo_id | path | 是 | 仓库ID | `1` |
| branch_name | query | 否 | 分支名称，默认获取所有分支的最新提交 | `main` |

#### 响应

**200 OK**
```json
{
  "id": 1,
  "hash": "abc123def456...",
  "repository_id": 1,
  "branch_id": 1,
  "author_name": "John Doe",
  "author_email": "john@example.com",
  "committer_name": "John Doe",
  "committer_email": "john@example.com",
  "commit_message": "Initial commit",
  "commit_date": "2024-01-01T00:00:00",
  "parent_hashes": "",
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00"
}
```

**404 Not Found**
```json
{
  "detail": "No commits found"
}
```

---

## 获取提交详情

### GET /api/v1/v1/repositories/{repo_id}/commits/{commit_hash}

根据提交哈希获取提交详情。

#### 请求参数

| 参数 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| repo_id | path | 是 | 仓库ID | `1` |
| commit_hash | path | 是 | 提交哈希值 | `abc123def456` |

#### 响应

**200 OK**
```json
{
  "id": 1,
  "hash": "abc123def456...",
  "repository_id": 1,
  "branch_id": 1,
  "author_name": "John Doe",
  "author_email": "john@example.com",
  "committer_name": "John Doe",
  "committer_email": "john@example.com",
  "commit_message": "Initial commit",
  "commit_date": "2024-01-01T00:00:00",
  "parent_hashes": "",
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00"
}
```

**404 Not Found**
```json
{
  "detail": "Commit not found"
}
```

---

## 创建提交

### POST /api/v1/v1/repositories/{repo_id}/commits

创建提交记录（需要认证）。

#### 请求参数

| 参数 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| repo_id | path | 是 | 仓库ID | `1` |

#### 请求头

| 参数 | 必填 | 说明 | 示例 |
|------|------|------|------|
| Authorization | 是 | Bearer Token | `Bearer eyJhbGciOiJIUzI1NiIs...` |
| Content-Type | 是 | 内容类型 | `application/json` |

#### 请求体

```json
{
  "hash": "abc123def456...",
  "branch_id": 1,
  "author_name": "John Doe",
  "author_email": "john@example.com",
  "committer_name": "John Doe",
  "committer_email": "john@example.com",
  "commit_message": "Initial commit",
  "commit_date": "2024-01-01T00:00:00",
  "parent_hashes": ""
}
```

#### 请求字段说明

| 字段 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| hash | string | 是 | 提交哈希值 | `abc123def456...` |
| branch_id | int | 是 | 分支ID | `1` |
| author_name | string | 是 | 作者名称 | `John Doe` |
| author_email | string | 是 | 作者邮箱 | `john@example.com` |
| committer_name | string | 是 | 提交者名称 | `John Doe` |
| committer_email | string | 是 | 提交者邮箱 | `john@example.com` |
| commit_message | string | 是 | 提交信息 | `Initial commit` |
| commit_date | string | 是 | 提交时间 | `2024-01-01T00:00:00` |
| parent_hashes | string | 否 | 父提交哈希，多个用逗号分隔 | `def789...` |

#### 响应

**201 Created**
```json
{
  "id": 1,
  "hash": "abc123def456...",
  "repository_id": 1,
  "branch_id": 1,
  "author_name": "John Doe",
  "author_email": "john@example.com",
  "committer_name": "John Doe",
  "committer_email": "john@example.com",
  "commit_message": "Initial commit",
  "commit_date": "2024-01-01T00:00:00",
  "parent_hashes": "",
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00"
}
```

**409 Conflict**
```json
{
  "detail": "Commit hash already exists"
}
```

---

## 获取分支提交

### GET /api/v1/v1/repositories/{repo_id}/branches/{branch_name}/commits

获取特定分支的提交记录。

#### 请求参数

| 参数 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| repo_id | path | 是 | 仓库ID | `1` |
| branch_name | path | 是 | 分支名称 | `main` |
| limit | query | 否 | 返回记录数量限制，默认100，最大1000 | `50` |
| offset | query | 否 | 记录偏移量，默认0 | `0` |

#### 响应

**200 OK**
```json
[
  {
    "id": 1,
    "hash": "abc123def456...",
    "repository_id": 1,
    "branch_id": 1,
    "author_name": "John Doe",
    "author_email": "john@example.com",
    "committer_name": "John Doe",
    "committer_email": "john@example.com",
    "commit_message": "Initial commit",
    "commit_date": "2024-01-01T00:00:00",
    "parent_hashes": "",
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-01-01T00:00:00"
  }
]
```

---

## 统计分支提交数量

### GET /api/v1/v1/repositories/{repo_id}/branches/{branch_name}/commits/count

统计特定分支的提交数量。

#### 请求参数

| 参数 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| repo_id | path | 是 | 仓库ID | `1` |
| branch_name | path | 是 | 分支名称 | `main` |

#### 响应

**200 OK**
```json
{
  "count": 50
}
```

---

## TypeScript 类型定义

```typescript
// 提交对象
interface Commit {
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

// 提交数量统计
interface CommitCount {
  count: number;
}

// 创建提交请求
interface CreateCommitRequest {
  hash: string;
  branch_id: number;
  author_name: string;
  author_email: string;
  committer_name: string;
  committer_email: string;
  commit_message: string;
  commit_date: string;
  parent_hashes?: string;
}

// 提交查询参数
interface CommitQueryParams {
  limit?: number;
  offset?: number;
  branch_name?: string;
}

// 提交搜索参数
interface CommitSearchParams {
  query: string;
  limit?: number;
}

// 作者提交查询参数
interface AuthorCommitsParams {
  author_email: string;
  limit?: number;
}
```

---

## 前端调用示例

### 使用 Fetch API

```typescript
// 获取提交列表
async function getCommits(
  repoId: number,
  params?: CommitQueryParams,
  token?: string
): Promise<Commit[]> {
  const queryParams = new URLSearchParams();
  if (params?.limit) queryParams.append('limit', params.limit.toString());
  if (params?.offset) queryParams.append('offset', params.offset.toString());
  if (params?.branch_name) queryParams.append('branch_name', params.branch_name);
  
  const url = `/api/v1/v1/repositories/${repoId}/commits?${queryParams.toString()}`;
  const response = await fetch(url, {
    headers: token ? { 'Authorization': `Bearer ${token}` } : {},
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail);
  }
  
  return response.json();
}

// 搜索提交
async function searchCommits(
  repoId: number,
  params: CommitSearchParams,
  token?: string
): Promise<Commit[]> {
  const queryParams = new URLSearchParams();
  queryParams.append('query', params.query);
  if (params.limit) queryParams.append('limit', params.limit.toString());
  
  const url = `/api/v1/v1/repositories/${repoId}/commits/search?${queryParams.toString()}`;
  const response = await fetch(url, {
    headers: token ? { 'Authorization': `Bearer ${token}` } : {},
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail);
  }
  
  return response.json();
}

// 获取提交详情
async function getCommitDetail(
  repoId: number,
  commitHash: string,
  token?: string
): Promise<Commit> {
  const url = `/api/v1/v1/repositories/${repoId}/commits/${commitHash}`;
  const response = await fetch(url, {
    headers: token ? { 'Authorization': `Bearer ${token}` } : {},
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail);
  }
  
  return response.json();
}
```

### 使用 Axios

```typescript
import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
});

// 添加认证拦截器
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 提交 API
export const commitApi = {
  // 获取提交列表
  getCommits: (repoId: number, params?: CommitQueryParams) => 
    api.get<Commit[]>(`/repositories/${repoId}/commits`, { params }),
  
  // 获取提交历史树
  getCommitHistory: (repoId: number, branchName?: string, limit?: number) => 
    api.get<Commit[]>(`/repositories/${repoId}/commits/history`, { 
      params: { branch_name: branchName, limit } 
    }),
  
  // 统计提交数量
  getCommitCount: (repoId: number) => 
    api.get<CommitCount>(`/repositories/${repoId}/commits/count`),
  
  // 搜索提交
  searchCommits: (repoId: number, params: CommitSearchParams) => 
    api.get<Commit[]>(`/repositories/${repoId}/commits/search`, { params }),
  
  // 根据作者获取提交
  getCommitsByAuthor: (repoId: number, params: AuthorCommitsParams) => 
    api.get<Commit[]>(`/repositories/${repoId}/commits/author`, { params }),
  
  // 获取最新提交
  getLatestCommit: (repoId: number, branchName?: string) => 
    api.get<Commit>(`/repositories/${repoId}/commits/latest`, { 
      params: { branch_name: branchName } 
    }),
  
  // 获取提交详情
  getCommitDetail: (repoId: number, commitHash: string) => 
    api.get<Commit>(`/repositories/${repoId}/commits/${commitHash}`),
  
  // 创建提交
  createCommit: (repoId: number, data: CreateCommitRequest) => 
    api.post<Commit>(`/repositories/${repoId}/commits`, data),
  
  // 获取分支提交
  getBranchCommits: (repoId: number, branchName: string, params?: CommitQueryParams) => 
    api.get<Commit[]>(`/repositories/${repoId}/branches/${encodeURIComponent(branchName)}/commits`, { params }),
  
  // 统计分支提交数量
  getBranchCommitCount: (repoId: number, branchName: string) => 
    api.get<CommitCount>(`/repositories/${repoId}/branches/${encodeURIComponent(branchName)}/commits/count`),
};
```

### Vue 3 Composition API 示例

```typescript
import { ref, onMounted } from 'vue';
import { commitApi } from './api';

export function useCommits(repoId: number) {
  const commits = ref<Commit[]>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);
  const hasMore = ref(true);
  const offset = ref(0);
  const limit = 20;
  
  // 获取提交列表
  const fetchCommits = async (branchName?: string, reset = false) => {
    if (reset) {
      offset.value = 0;
      commits.value = [];
    }
    
    if (!hasMore.value && !reset) return;
    
    loading.value = true;
    error.value = null;
    
    try {
      const { data } = await commitApi.getCommits(repoId, {
        limit,
        offset: offset.value,
        branch_name: branchName,
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
  
  // 搜索提交
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
  
  // 获取提交详情
  const getCommitDetail = async (commitHash: string): Promise<Commit | null> => {
    try {
      const { data } = await commitApi.getCommitDetail(repoId, commitHash);
      return data;
    } catch (err: any) {
      error.value = err.response?.data?.detail || '获取提交详情失败';
      return null;
    }
  };
  
  return {
    commits,
    loading,
    error,
    hasMore,
    fetchCommits,
    searchCommits,
    getCommitDetail,
  };
}
```

---

## 响应字段说明

### 提交对象 (Commit)

| 字段 | 类型 | 说明 | 前端使用场景 |
|------|------|------|-------------|
| id | number | 提交记录ID | 唯一标识 |
| hash | string | 提交哈希值 | 显示短哈希、链接到详情 |
| repository_id | number | 所属仓库ID | 关联仓库 |
| branch_id | number | 所属分支ID | 关联分支 |
| author_name | string | 作者名称 | 显示作者 |
| author_email | string | 作者邮箱 | 显示作者邮箱、头像 |
| committer_name | string | 提交者名称 | 显示提交者（可能与作者不同） |
| committer_email | string | 提交者邮箱 | 显示提交者邮箱 |
| commit_message | string | 提交信息 | 显示提交说明 |
| commit_date | string | 提交时间 | 显示提交日期、相对时间 |
| parent_hashes | string | 父提交哈希 | 显示提交关系图 |
| created_at | string | 记录创建时间 | 系统记录 |
| updated_at | string | 记录更新时间 | 系统记录 |

---

## 错误处理指南

### 常见错误码处理

| HTTP状态码 | 场景 | 前端处理建议 |
|------------|------|-------------|
| 400 | 请求参数错误 | 检查查询参数格式 |
| 401 | 未认证 | 跳转登录页面 |
| 404 | 提交不存在 | 显示404页面或空状态 |
| 409 | 提交哈希已存在 | 提示提交已存在 |
| 422 | 语义错误 | 检查提交数据完整性 |
| 500 | 服务器错误 | 显示"服务器繁忙，请稍后重试" |

### 提交信息格式化

```typescript
// 格式化提交哈希（显示短哈希）
function formatCommitHash(hash: string): string {
  return hash.substring(0, 7);
}

// 格式化提交日期（显示相对时间）
function formatCommitDate(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);
  
  if (minutes < 1) return '刚刚';
  if (minutes < 60) return `${minutes}分钟前`;
  if (hours < 24) return `${hours}小时前`;
  if (days < 30) return `${days}天前`;
  
  return date.toLocaleDateString('zh-CN');
}

// 解析提交信息（提取标题和描述）
function parseCommitMessage(message: string): { title: string; body: string } {
  const lines = message.split('\n');
  const title = lines[0];
  const body = lines.slice(2).join('\n'); // 跳过空行
  return { title, body };
}
```
