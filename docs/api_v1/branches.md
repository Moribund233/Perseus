# 分支管理 API 设计

> 本文档提供前端开发所需的完整 API 调用指南，包含请求示例、TypeScript 类型定义和常见使用场景。

## 目录

- [分支列表](#分支列表)
- [获取默认分支](#获取默认分支)
- [获取单个分支](#获取单个分支)
- [创建分支](#创建分支)
- [更新分支](#更新分支)
- [删除分支](#删除分支)
- [设置默认分支](#设置默认分支)
- [保护分支](#保护分支)
- [取消分支保护](#取消分支保护)
- [检查分支保护状态](#检查分支保护状态)
- [TypeScript 类型定义](#typescript-类型定义)
- [前端调用示例](#前端调用示例)

---

## 分支列表

### GET /api/v1/v1/repositories/{repo_id}/branches

获取仓库的所有分支（需要认证）。

#### 请求参数

| 参数 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| repo_id | path | 是 | 仓库ID | `1` |

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
    "name": "main",
    "repository_id": 1,
    "is_protected": true,
    "require_code_review": true,
    "require_status_checks": true,
    "is_default": true,
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-01-01T00:00:00"
  },
  {
    "id": 2,
    "name": "develop",
    "repository_id": 1,
    "is_protected": false,
    "require_code_review": false,
    "require_status_checks": false,
    "is_default": false,
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-01-01T00:00:00"
  }
]
```

**401 Unauthorized**
```json
{
  "detail": "Invalid or expired token"
}
```

**404 Not Found**
```json
{
  "detail": "Repository not found"
}
```

---

## 获取默认分支

### GET /api/v1/v1/repositories/{repo_id}/branches/default

获取仓库的默认分支。

#### 请求参数

| 参数 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| repo_id | path | 是 | 仓库ID | `1` |

#### 响应

**200 OK**
```json
{
  "id": 1,
  "name": "main",
  "repository_id": 1,
  "is_protected": true,
  "require_code_review": true,
  "require_status_checks": true,
  "is_default": true,
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00"
}
```

**404 Not Found**
```json
{
  "detail": "No default branch found"
}
```

---

## 获取单个分支

### GET /api/v1/v1/repositories/{repo_id}/branches/{branch_name}

获取仓库的特定分支。

#### 请求参数

| 参数 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| repo_id | path | 是 | 仓库ID | `1` |
| branch_name | path | 是 | 分支名称 | `feature/login` |

#### 响应

**200 OK**
```json
{
  "id": 2,
  "name": "feature/login",
  "repository_id": 1,
  "is_protected": false,
  "require_code_review": false,
  "require_status_checks": false,
  "is_default": false,
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00"
}
```

**404 Not Found**
```json
{
  "detail": "Branch 'feature/login' not found"
}
```

---

## 创建分支

### POST /api/v1/v1/repositories/{repo_id}/branches

创建新分支（需要认证）。

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
  "name": "feature/new-feature",
  "base_branch": "main"
}
```

#### 请求字段说明

| 字段 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| name | string | 是 | 分支名称 | `feature/new-feature` |
| base_branch | string | 是 | 基于哪个分支创建 | `main` |

#### 响应

**201 Created**
```json
{
  "id": 3,
  "name": "feature/new-feature",
  "repository_id": 1,
  "is_protected": false,
  "require_code_review": false,
  "require_status_checks": false,
  "is_default": false,
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00"
}
```

**400 Bad Request**
```json
{
  "detail": "Branch name is required"
}
```

**409 Conflict**
```json
{
  "detail": "Branch 'feature/new-feature' already exists"
}
```

---

## 更新分支

### PUT /api/v1/v1/repositories/{repo_id}/branches/{branch_name}

更新分支信息（需要认证）。

#### 请求参数

| 参数 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| repo_id | path | 是 | 仓库ID | `1` |
| branch_name | path | 是 | 分支名称 | `feature/old-name` |

#### 请求头

| 参数 | 必填 | 说明 | 示例 |
|------|------|------|------|
| Authorization | 是 | Bearer Token | `Bearer eyJhbGciOiJIUzI1NiIs...` |
| Content-Type | 是 | 内容类型 | `application/json` |

#### 请求体

```json
{
  "name": "feature/renamed-feature"
}
```

#### 响应

**200 OK**
```json
{
  "id": 3,
  "name": "feature/renamed-feature",
  "repository_id": 1,
  "is_protected": false,
  "require_code_review": false,
  "require_status_checks": false,
  "is_default": false,
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-02T00:00:00"
}
```

---

## 删除分支

### DELETE /api/v1/v1/repositories/{repo_id}/branches/{branch_name}

删除分支（需要认证）。

#### 请求参数

| 参数 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| repo_id | path | 是 | 仓库ID | `1` |
| branch_name | path | 是 | 分支名称 | `feature/old-feature` |

#### 请求头

| 参数 | 必填 | 说明 | 示例 |
|------|------|------|------|
| Authorization | 是 | Bearer Token | `Bearer eyJhbGciOiJIUzI1NiIs...` |

#### 响应

**200 OK**
```json
{
  "message": "Branch 'feature/old-feature' deleted successfully"
}
```

**403 Forbidden**
```json
{
  "detail": "Cannot delete protected branch"
}
```

**409 Conflict**
```json
{
  "detail": "Cannot delete default branch"
}
```

---

## 设置默认分支

### PUT /api/v1/v1/repositories/{repo_id}/branches/{branch_name}/default

设置默认分支（需要认证，仅仓库所有者或管理员）。

#### 请求参数

| 参数 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| repo_id | path | 是 | 仓库ID | `1` |
| branch_name | path | 是 | 分支名称 | `main` |

#### 请求头

| 参数 | 必填 | 说明 | 示例 |
|------|------|------|------|
| Authorization | 是 | Bearer Token | `Bearer eyJhbGciOiJIUzI1NiIs...` |

#### 响应

**200 OK**
```json
{
  "message": "Default branch set to 'main'"
}
```

**403 Forbidden**
```json
{
  "detail": "Admin privileges required"
}
```

---

## 保护分支

### PUT /api/v1/v1/repositories/{repo_id}/branches/{branch_name}/protect

保护分支（需要认证，仅仓库所有者或管理员）。

#### 请求参数

| 参数 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| repo_id | path | 是 | 仓库ID | `1` |
| branch_name | path | 是 | 分支名称 | `main` |

#### 请求头

| 参数 | 必填 | 说明 | 示例 |
|------|------|------|------|
| Authorization | 是 | Bearer Token | `Bearer eyJhbGciOiJIUzI1NiIs...` |
| Content-Type | 是 | 内容类型 | `application/json` |

#### 请求体

```json
{
  "require_code_review": true,
  "require_status_checks": true
}
```

#### 响应

**200 OK**
```json
{
  "id": 1,
  "name": "main",
  "repository_id": 1,
  "is_protected": true,
  "require_code_review": true,
  "require_status_checks": true,
  "is_default": true,
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-02T00:00:00"
}
```

---

## 取消分支保护

### PUT /api/v1/v1/repositories/{repo_id}/branches/{branch_name}/unprotect

取消分支保护（需要认证，仅仓库所有者或管理员）。

#### 请求参数

| 参数 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| repo_id | path | 是 | 仓库ID | `1` |
| branch_name | path | 是 | 分支名称 | `main` |

#### 请求头

| 参数 | 必填 | 说明 | 示例 |
|------|------|------|------|
| Authorization | 是 | Bearer Token | `Bearer eyJhbGciOiJIUzI1NiIs...` |

#### 响应

**200 OK**
```json
{
  "id": 1,
  "name": "main",
  "repository_id": 1,
  "is_protected": false,
  "require_code_review": false,
  "require_status_checks": false,
  "is_default": true,
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-02T00:00:00"
}
```

---

## 检查分支保护状态

### GET /api/v1/v1/repositories/{repo_id}/branches/{branch_name}/protection

检查分支是否受保护（需要认证）。

#### 请求参数

| 参数 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| repo_id | path | 是 | 仓库ID | `1` |
| branch_name | path | 是 | 分支名称 | `main` |

#### 请求头

| 参数 | 必填 | 说明 | 示例 |
|------|------|------|------|
| Authorization | 是 | Bearer Token | `Bearer eyJhbGciOiJIUzI1NiIs...` |

#### 响应

**200 OK**
```json
{
  "is_protected": true,
  "require_code_review": true,
  "require_status_checks": true
}
```

---

## TypeScript 类型定义

```typescript
// 分支对象
interface Branch {
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

// 分支保护状态
interface BranchProtectionStatus {
  is_protected: boolean;
  require_code_review: boolean;
  require_status_checks: boolean;
}

// 创建分支请求
interface CreateBranchRequest {
  name: string;
  base_branch: string;
}

// 更新分支请求
interface UpdateBranchRequest {
  name: string;
}

// 保护分支请求
interface ProtectBranchRequest {
  require_code_review?: boolean;
  require_status_checks?: boolean;
}

// API 响应类型
interface ApiResponse<T> {
  data?: T;
  error?: {
    detail: string;
  };
}
```

---

## 前端调用示例

### 使用 Fetch API

```typescript
// 获取分支列表
async function getBranches(repoId: number, token: string): Promise<Branch[]> {
  const response = await fetch(`/api/v1/v1/repositories/${repoId}/branches`, {
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail);
  }
  
  return response.json();
}

// 创建分支
async function createBranch(
  repoId: number,
  data: CreateBranchRequest,
  token: string
): Promise<Branch> {
  const response = await fetch(`/api/v1/v1/repositories/${repoId}/branches`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail);
  }
  
  return response.json();
}

// 删除分支
async function deleteBranch(
  repoId: number,
  branchName: string,
  token: string
): Promise<void> {
  const response = await fetch(
    `/api/v1/v1/repositories/${repoId}/branches/${encodeURIComponent(branchName)}`,
    {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    }
  );
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail);
  }
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

// 分支 API
export const branchApi = {
  // 获取分支列表
  getBranches: (repoId: number) => 
    api.get<Branch[]>(`/repositories/${repoId}/branches`),
  
  // 获取默认分支
  getDefaultBranch: (repoId: number) => 
    api.get<Branch>(`/repositories/${repoId}/branches/default`),
  
  // 获取单个分支
  getBranch: (repoId: number, branchName: string) => 
    api.get<Branch>(`/repositories/${repoId}/branches/${encodeURIComponent(branchName)}`),
  
  // 创建分支
  createBranch: (repoId: number, data: CreateBranchRequest) => 
    api.post<Branch>(`/repositories/${repoId}/branches`, data),
  
  // 更新分支
  updateBranch: (repoId: number, branchName: string, data: UpdateBranchRequest) => 
    api.put<Branch>(`/repositories/${repoId}/branches/${encodeURIComponent(branchName)}`, data),
  
  // 删除分支
  deleteBranch: (repoId: number, branchName: string) => 
    api.delete(`/repositories/${repoId}/branches/${encodeURIComponent(branchName)}`),
  
  // 设置默认分支
  setDefaultBranch: (repoId: number, branchName: string) => 
    api.put(`/repositories/${repoId}/branches/${encodeURIComponent(branchName)}/default`),
  
  // 保护分支
  protectBranch: (repoId: number, branchName: string, data?: ProtectBranchRequest) => 
    api.put<Branch>(`/repositories/${repoId}/branches/${encodeURIComponent(branchName)}/protect`, data),
  
  // 取消分支保护
  unprotectBranch: (repoId: number, branchName: string) => 
    api.put<Branch>(`/repositories/${repoId}/branches/${encodeURIComponent(branchName)}/unprotect`),
  
  // 检查分支保护状态
  checkProtection: (repoId: number, branchName: string) => 
    api.get<BranchProtectionStatus>(`/repositories/${repoId}/branches/${encodeURIComponent(branchName)}/protection`),
};
```

### Vue 3 Composition API 示例

```typescript
import { ref, onMounted } from 'vue';
import { branchApi } from './api';

export function useBranches(repoId: number) {
  const branches = ref<Branch[]>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);
  
  // 获取分支列表
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
  
  // 创建分支
  const createBranch = async (name: string, baseBranch: string) => {
    try {
      const { data } = await branchApi.createBranch(repoId, {
        name,
        base_branch: baseBranch,
      });
      branches.value.push(data);
      return data;
    } catch (err: any) {
      throw new Error(err.response?.data?.detail || '创建分支失败');
    }
  };
  
  // 删除分支
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

---

## 响应字段说明

### 分支对象 (Branch)

| 字段 | 类型 | 说明 | 前端使用场景 |
|------|------|------|-------------|
| id | number | 分支ID | 唯一标识 |
| name | string | 分支名称 | 显示分支名、切换分支 |
| repository_id | number | 所属仓库ID | 关联仓库 |
| is_protected | boolean | 是否受保护 | 控制删除/强制推送按钮显示 |
| require_code_review | boolean | 是否需要代码审查 | 显示审查状态图标 |
| require_status_checks | boolean | 是否需要状态检查 | 显示CI状态检查 |
| is_default | boolean | 是否为默认分支 | 高亮显示默认分支 |
| created_at | string | 创建时间 | 显示创建日期 |
| updated_at | string | 更新时间 | 显示最后更新 |

---

## 错误处理指南

### 常见错误码处理

| HTTP状态码 | 场景 | 前端处理建议 |
|------------|------|-------------|
| 400 | 请求参数错误 | 检查表单验证，显示具体字段错误 |
| 401 | 未认证 | 跳转登录页面或刷新 Token |
| 403 | 无权限 | 禁用操作按钮，显示权限不足提示 |
| 404 | 资源不存在 | 显示404页面或空状态 |
| 409 | 资源冲突 | 显示冲突信息（如分支已存在） |
| 422 | 语义错误 | 检查业务逻辑（如删除默认分支） |
| 429 | 请求过于频繁 | 显示"操作太频繁，请稍后再试" |
| 500 | 服务器错误 | 显示"服务器繁忙，请稍后重试" |

### 错误提示示例

```typescript
function handleApiError(error: any): string {
  if (!error.response) {
    return '网络连接失败，请检查网络';
  }
  
  const { status, data } = error.response;
  
  switch (status) {
    case 401:
      return '登录已过期，请重新登录';
    case 403:
      return '您没有权限执行此操作';
    case 404:
      return '请求的资源不存在';
    case 409:
      return data.detail || '资源冲突';
    case 422:
      return data.detail || '请求参数错误';
    case 429:
      return '操作太频繁，请稍后再试';
    case 500:
      return '服务器繁忙，请稍后重试';
    default:
      return data.detail || '操作失败，请重试';
  }
}
```
