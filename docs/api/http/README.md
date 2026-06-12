# Perseus HTTP API

> **基础路径**: `/api/v1`（除非另行注明）
> **认证方式**: JWT Bearer Token（通过 `Authorization: Bearer <token>` 请求头传递）
> **响应格式**: JSON
> **更新日期**: 2026-06-13

---

## 目录

1. [通用说明](#1-通用说明)
2. [认证](#2-认证)
3. [用户管理](#3-用户管理)
4. [SSH Key 管理](#4-ssh-key-管理)
5. [仓库管理](#5-仓库管理)
6. [公开仓库](#6-公开仓库)
7. [Fork 管理](#7-fork-管理)
8. [仓库成员](#8-仓库成员)
9. [仓库浏览器](#9-仓库浏览器)
10. [分支管理](#10-分支管理)
11. [提交管理](#11-提交管理)
12. [Pull Request](#12-pull-request)
13. [Release 管理](#13-release-管理)
14. [Issue 管理](#14-issue-管理)
15. [Webhook](#15-webhook)
16. [应用管理](#16-应用管理)
17. [调试接口](#17-调试接口)
18. [错误处理](#18-错误处理)

---

## 1. 通用说明

### 认证头

```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

### 分页参数

所有列表接口支持统一分页：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `page` | int | 1 | 页码 |
| `limit` / `per_page` | int | 20 | 每页条数（最大 100）|

分页响应格式：

```json
{
  "items": [],
  "total": 100,
  "page": 1,
  "limit": 20,
  "pages": 5,
  "has_next": true,
  "has_prev": false
}
```

### 错误响应格式

```json
{
  "detail": "错误描述",
  "error": {
    "code": 404,
    "message": "错误描述",
    "type": "NotFoundException"
  }
}
```

通用 HTTP 状态码：

| 状态码 | 含义 |
|--------|------|
| 200 | 成功 |
| 201 | 创建成功 |
| 204 | 删除成功（无内容）|
| 400 | 请求参数错误 (`ValidationException`) |
| 401 | 未认证 (`AuthenticationException`) |
| 403 | 权限不足 (`AuthorizationException`) |
| 404 | 资源不存在 (`NotFoundException`) |
| 409 | 资源冲突 (`ConflictException`) |
| 422 | 请求体校验失败 (Pydantic ValidationError) |
| 429 | 请求过于频繁 (限流) |
| 500 | 服务器内部错误 |

---

## 2. 认证

### 用户登录

```
POST /api/v1/auth/login
```

认证方式：无（公开端点）

Request Body:
```json
{
  "username": "admin",
  "password": "password123"
}
```

Response (200):
```json
{
  "access_token": "eyJhbG...",
  "refresh_token": "eyJhbG...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "username": "admin",
    "email": "admin@example.com"
  }
}
```

限速：10次/分钟/IP（Nginx 层）

### 刷新 Token

```
POST /api/v1/auth/refresh
```

认证方式：无（使用 refresh_token 换取新令牌对）

Request Body:
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

Response (200):
```json
{
  "access_token": "eyJhbG...",
  "refresh_token": "eyJhbG...",
  "token_type": "bearer"
}
```

Raises:
- 401: 刷新令牌无效或过期

---

## 3. 用户管理

### 获取所有用户

```
GET /api/v1/users
```

认证：✅ 需要

Response (200):
```json
[
  {
    "id": 1,
    "username": "admin",
    "email": "admin@example.com",
    "full_name": "Admin User",
    "is_active": true,
    "is_admin": true
  }
]
```

### 创建用户

```
POST /api/v1/users
```

认证：无

Request Body:
```json
{
  "username": "newuser",
  "email": "new@example.com",
  "password": "securepassword",
  "full_name": "New User",
  "is_active": true,
  "is_admin": false
}
```

| 字段 | 类型 | 必填 | 约束 |
|------|------|------|------|
| username | string | ✅ | 3-50 字符 |
| email | EmailStr | ✅ | 合法邮箱格式 |
| password | string | ✅ | 6-128 字符 |
| full_name | string | ❌ | 最多 100 字符 |
| is_active | bool | ❌ | 默认 true |
| is_admin | bool | ❌ | 默认 false |

### 获取当前用户

```
GET /api/v1/users/me
```

认证：✅ 需要

Response: 当前用户的 User 对象

### 获取指定用户

```
GET /api/v1/users/{user_id}
```

认证：✅ 需要

### 更新用户

```
PUT /api/v1/users/{user_id}
```

认证：✅ 需要（普通用户仅能更新自己，管理员可更新任何人）

Request Body（全部可选）:
```json
{
  "username": "newname",
  "email": "new@example.com",
  "full_name": "Updated Name",
  "is_active": true
}
```

### 删除用户

```
DELETE /api/v1/users/{user_id}
```

认证：✅ 需要管理员权限

---

## 4. SSH Key 管理

**基础路径**: `/api/v1/keys`

### 添加 SSH Key

```
POST /api/v1/keys
```

认证：✅ 需要

Request Body:
```json
{
  "name": "My Laptop",
  "public_key": "ssh-rsa AAAAB3NzaC1yc2E..."
}
```

| 字段 | 类型 | 必填 | 约束 |
|------|------|------|------|
| name | string | ✅ | 1-100 字符 |
| public_key | string | ✅ | 合法 SSH 公钥 |

Response (201):
```json
{
  "id": 1,
  "name": "My Laptop",
  "public_key": "ssh-rsa AAAAB...",
  "fingerprint": "SHA256:abc123def...",
  "user_id": 1,
  "created_at": "2026-06-10T12:00:00"
}
```

### 列出 SSH Keys

```
GET /api/v1/keys
```

认证：✅ 需要

Response (200): List of SSHKeyResponse

### 删除 SSH Key

```
DELETE /api/v1/keys/{key_id}
```

认证：✅ 需要

Response: 204 No Content

---

## 5. 仓库管理

所有仓库相关接口的基础路径：`/api/v1/repositories`

### 获取仓库列表

```
GET /api/v1/repositories
```

认证：✅ 需要

### 创建仓库

```
POST /api/v1/repositories
```

认证：✅ 需要

Request Body:
```json
{
  "name": "my-repo",
  "description": "My awesome project",
  "is_public": true,
  "default_branch": "main"
}
```

路径自动生成，格式为: `{username}/{repo_name}`

### 获取仓库详情

```
GET /api/v1/repositories/{repo_id}
```

### 更新仓库

```
PUT /api/v1/repositories/{repo_id}
```

认证：✅ 需要（所有者或管理员权限）

### 删除仓库

```
DELETE /api/v1/repositories/{repo_id}
```

认证：✅ 需要（仅所有者）

### 获取用户仓库

```
GET /api/v1/repositories/user/{user_id}
```

认证：✅ 需要

### 检查仓库访问权限

```
GET /api/v1/repositories/{repo_id}/access?user_id={user_id}
```

认证：✅ 需要

Response:
```json
{
  "has_access": true
}
```

---

## 6. 公开仓库

### 获取所有公开仓库

```
GET /api/v1/repositories/public
```

认证：❌ 不需要

---

## 7. Fork 管理

### 创建 Fork

```
POST /api/v1/repositories/{repo_id}/forks
```

认证：✅ 需要

Request Body（全部可选）:
```json
{
  "name": "my-fork",
  "description": "Forked from awesome-project",
  "is_public": true
}
```

Response (201):
```json
{
  "id": 2,
  "name": "my-fork",
  "path": "username/my-fork",
  "is_fork": true,
  "forked_from_id": 1,
  "source": {
    "id": 1,
    "name": "original-repo",
    "path": "owner/original-repo",
    "owner_id": 1
  }
}
```

### 获取仓库 Fork 列表

```
GET /api/v1/repositories/{repo_id}/forks?page=1&limit=20
```

### 获取 Fork 源仓库

```
GET /api/v1/repositories/{repo_id}/forks/source
```

认证：❌ 不需要

Response: 源仓库信息，如果不是 Fork 则返回 null

### 同步 Fork

```
POST /api/v1/repositories/{repo_id}/forks/sync
```

认证：✅ 需要（仅 Fork 所有者）

从源仓库拉取最新更改 (`git fetch origin`)

---

## 8. 仓库成员

### 获取成员列表

```
GET /api/v1/repositories/{repo_id}/members
```

### 获取指定成员

```
GET /api/v1/repositories/{repo_id}/members/{user_id}
```

### 添加成员

```
POST /api/v1/repositories/{repo_id}/members
```

Request Body:
```json
{
  "user_id": 3,
  "role": "write"
}
```

| 角色 | 权限 |
|------|------|
| read | 只读（clone、查看） |
| write | 读写（push、管理 Issue/PR） |
| admin | 管理（成员管理、仓库设置） |

### 更新成员

```
PUT /api/v1/repositories/{repo_id}/members/{user_id}
```

### 更新成员角色

```
PUT /api/v1/repositories/{repo_id}/members/{user_id}/role
```

```json
{
  "role": "admin"
}
```

### 激活成员

```
PUT /api/v1/repositories/{repo_id}/members/{user_id}/activate
```

### 停用成员

```
PUT /api/v1/repositories/{repo_id}/members/{user_id}/deactivate
```

### 检查成员权限

```
GET /api/v1/repositories/{repo_id}/members/{user_id}/permission?permission={permission_name}
```

### 移除成员

```
DELETE /api/v1/repositories/{repo_id}/members/{user_id}
```

---

## 9. 仓库浏览器

所有浏览器端点的基础路径：`/api/v1/repositories`

### 获取文件树

```
GET /api/v1/repositories/{repo_id}/tree?ref=HEAD&path=
```

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| ref | string | HEAD | 分支名或提交 SHA |
| path | string | "" | 子目录路径 |

### 获取文件内容

```
GET /api/v1/repositories/{repo_id}/blob?ref=HEAD&path=README.md
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| path | string | ✅ | 文件路径 |
| ref | string | ❌ | 分支名或提交 SHA，默认 HEAD |

### 获取提交历史

```
GET /api/v1/repositories/{repo_id}/commits?ref=HEAD&path=&page=1&per_page=30
```

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| ref | string | HEAD | 分支名 |
| path | string | null | 特定文件路径 |
| page | int | 1 | 页码 |
| per_page | int | 30 | 每页数量（最大 100）|

### 获取代码差异

```
GET /api/v1/repositories/{repo_id}/diff?head={sha}&base={sha}&path=
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| head | string | ✅ | 对比提交 SHA |
| base | string | ❌ | 基准提交 SHA，null 表示与空树对比 |
| path | string | ❌ | 特定文件路径 |

### 获取 README

```
GET /api/v1/repositories/{repo_id}/readme?ref=HEAD
```

自动查找 README.md, README.rst, README.txt, README 等常见文件。

Response:
```json
{
  "found": true,
  "filename": "README.md",
  "content": "# Project Title\n...",
  "language": "markdown",
  "encoding": "utf-8"
}
```

### 获取文件符号

```
GET /api/v1/repositories/{repo_id}/symbols?ref=HEAD&path=src/main.py
```

返回文件中定义的函数、类、变量等符号（目前支持 Python）。

Response:
```json
{
  "path": "src/main.py",
  "language": "python",
  "symbols": [
    {"name": "MyClass", "type": "class", "line": 1},
    {"name": "my_function", "type": "function", "line": 10}
  ]
}
```

### 检测文件语言

```
GET /api/v1/repositories/{repo_id}/language?path=src/main.py
```

Response:
```json
{
  "path": "src/main.py",
  "language": "python"
}
```

---

## 10. 分支管理

### 获取分支列表

```
GET /api/v1/repositories/{repo_id}/branches
```

认证：✅ 需要

### 获取默认分支

```
GET /api/v1/repositories/{repo_id}/branches/default
```

### 创建分支

```
POST /api/v1/repositories/{repo_id}/branches
```

认证：✅ 需要

```json
{
  "name": "feature-xyz",
  "source_branch": "main",
  "source_commit_hash": "abc123..."
}
```

### 获取分支详情

```
GET /api/v1/repositories/{repo_id}/branches/{branch_name}
```

### 更新分支

```
PUT /api/v1/repositories/{repo_id}/branches/{branch_name}
```

认证：✅ 需要

### 删除分支

```
DELETE /api/v1/repositories/{repo_id}/branches/{branch_name}
```

认证：✅ 需要

### 设置默认分支

```
PUT /api/v1/repositories/{repo_id}/branches/{branch_name}/default
```

认证：✅ 需要

### 保护分支

```
PUT /api/v1/repositories/{repo_id}/branches/{branch_name}/protect
```

认证：✅ 需要

```json
{
  "is_protected": true,
  "require_code_review": true,
  "require_status_checks": true
}
```

### 取消分支保护

```
PUT /api/v1/repositories/{repo_id}/branches/{branch_name}/unprotect
```

认证：✅ 需要

### 检查分支保护状态

```
GET /api/v1/repositories/{repo_id}/branches/{branch_name}/protection
```

认证：✅ 需要

---

## 11. 提交管理

### 获取提交列表

```
GET /api/v1/repositories/{repo_id}/commits?limit=100&offset=0&branch_name=
```

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| limit | int | 100 | 返回数量（最大 1000）|
| offset | int | 0 | 偏移量 |
| branch_name | string | null | 分支名称（可选，默认所有分支）|

认证：✅ 需要

### 获取提交历史树

```
GET /api/v1/repositories/{repo_id}/commits/history?branch_name=&limit=50
```

返回提交历史树，不需要认证。

### 统计提交数量

```
GET /api/v1/repositories/{repo_id}/commits/count
```

Response: `{"count": 42}`

### 搜索提交

```
GET /api/v1/repositories/{repo_id}/commits/search?query={keyword}&limit=50
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| query | string | ✅ | 搜索关键词 |
| limit | int | ❌ | 默认 50，最大 100 |

### 按作者查询提交

```
GET /api/v1/repositories/{repo_id}/commits/author?author_email={email}&limit=50
```

### 获取最新提交

```
GET /api/v1/repositories/{repo_id}/commits/latest?branch_name=
```

### 获取提交详情

```
GET /api/v1/repositories/{repo_id}/commits/{commit_hash}
```

### 创建提交记录

```
POST /api/v1/repositories/{repo_id}/commits
```

认证：✅ 需要

### 获取分支提交列表

```
GET /api/v1/repositories/{repo_id}/branches/{branch_name}/commits?limit=100&offset=0
```

### 统计分支提交数量

```
GET /api/v1/repositories/{repo_id}/branches/{branch_name}/commits/count
```

Response: `{"count": 42}`

---

## 12. Pull Request

### 获取 PR 列表

```
GET /api/v1/repositories/{repo_id}/pull-requests?status=open&author=&page=1&limit=20
```

| 参数 | 类型 | 说明 |
|------|------|------|
| status | string | open / merged / closed |
| author | int | 作者 ID 筛选 |
| page | int | |
| limit | int | |

### 创建 PR

```
POST /api/v1/repositories/{repo_id}/pull-requests
```

认证：✅ 需要

```json
{
  "title": "Add new feature",
  "description": "## Summary\nThis PR adds...",
  "source_branch": "feature-xyz",
  "target_branch": "main"
}
```

### 获取 PR 详情

```
GET /api/v1/repositories/{repo_id}/pull-requests/{pr_number}
```

### 更新 PR

```
PATCH /api/v1/repositories/{repo_id}/pull-requests/{pr_number}
```

认证：✅ 需要

```json
{
  "title": "Updated title",
  "description": "Updated description"
}
```

### 关闭 PR

```
POST /api/v1/repositories/{repo_id}/pull-requests/{pr_number}/close
```

认证：✅ 需要

### 合并 PR

```
POST /api/v1/repositories/{repo_id}/pull-requests/{pr_number}/merge
```

认证：✅ 需要

```json
{
  "merge_method": "merge"
}
```

| merge_method | 说明 |
|-------------|------|
| merge | 创建合并提交（默认）|
| squash | 压缩为单个提交 |
| rebase | 变基合并 |

### 获取 PR 评论

```
GET /api/v1/repositories/{repo_id}/pull-requests/{pr_number}/comments
```

### 添加 PR 评论

```
POST /api/v1/repositories/{repo_id}/pull-requests/{pr_number}/comments
```

认证：✅ 需要

```json
{
  "content": "Great change!",
  "file_path": "src/main.py",
  "line_number": 42,
  "commit_hash": "abc123",
  "parent_id": null
}
```

支持行级评论和回复（`parent_id` 为回复时填写父评论 ID）。

### 创建 PR 审查

```
POST /api/v1/repositories/{repo_id}/pull-requests/{pr_number}/reviews
```

认证：✅ 需要

```json
{
  "status": "approved",
  "comment": "LGTM!"
}
```

| status | 说明 |
|--------|------|
| approved | 通过 |
| changes_requested | 请求修改 |

---

## 13. Release 管理

### 获取 Release 列表

```
GET /api/v1/repositories/{repo_id}/releases?include_drafts=false&include_prereleases=true&page=1&limit=20
```

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| include_drafts | bool | false | 是否包含草稿 |
| include_prereleases | bool | true | 是否包含预发布版本 |

### 创建 Release

```
POST /api/v1/repositories/{repo_id}/releases
```

认证：✅ 需要

```json
{
  "tag_name": "v1.0.0",
  "name": "Version 1.0.0",
  "description": "## Changes\n- Initial release",
  "commit_hash": "abc123",
  "is_draft": false,
  "is_prerelease": false,
  "create_git_tag": true
}
```

### 获取 Release 详情

```
GET /api/v1/repositories/{repo_id}/releases/{release_number}
```

### 按标签获取 Release

```
GET /api/v1/repositories/{repo_id}/releases/tag/{tag_name}
```

### 更新 Release

```
PATCH /api/v1/repositories/{repo_id}/releases/{release_number}
```

认证：✅ 需要

```json
{
  "name": "Updated Title",
  "description": "Updated description",
  "is_draft": false,
  "is_prerelease": false
}
```

### 删除 Release

```
DELETE /api/v1/repositories/{repo_id}/releases/{release_number}
```

认证：✅ 需要

Response: 204 No Content

### 添加 Release 附件

```
POST /api/v1/repositories/{repo_id}/releases/{release_number}/assets
```

认证：✅ 需要

```json
{
  "name": "release.zip",
  "file_path": "/data/releases/repo_1/release_1/release.zip",
  "file_size": 1048576,
  "content_type": "application/zip"
}
```

### 删除 Release 附件

```
DELETE /api/v1/repositories/{repo_id}/releases/{release_number}/assets/{asset_id}
```

认证：✅ 需要

Response: 204 No Content

---

## 14. Issue 管理

### 获取 Issue 列表

```
GET /api/v1/repositories/{repo_id}/issues?status=open&label=&assignee=&author=&page=1&limit=20
```

| 参数 | 类型 | 说明 |
|------|------|------|
| status | string | open / closed |
| label | string | 按标签名称筛选 |
| assignee | int | 指派人 ID |
| author | int | 作者 ID |
| page | int | 页码 |
| limit | int | 每页条数 |

### 创建 Issue

```
POST /api/v1/repositories/{repo_id}/issues
```

认证：✅ 需要

```json
{
  "title": "Bug: login fails on special chars",
  "description": "## Steps to reproduce\n1. Enter...",
  "priority": "high",
  "assignee_id": 2,
  "label_ids": [1, 2]
}
```

### 高级筛选 Issue

```
POST /api/v1/repositories/{repo_id}/issues/filter?sort_by=created_at&sort_order=desc&page=1&per_page=20
```

认证：✅ 需要

```json
{
  "statuses": ["open"],
  "priorities": ["high", "critical"],
  "assignee_ids": [1],
  "author_ids": [2],
  "label_ids": [1, 3],
  "search": "keyword"
}
```

### 批量关闭 Issue

```
POST /api/v1/repositories/{repo_id}/issues/batch/close
```

认证：✅ 需要

```json
{
  "issue_numbers": [1, 2, 3]
}
```

### 批量重新打开 Issue

```
POST /api/v1/repositories/{repo_id}/issues/batch/reopen
```

认证：✅ 需要

```json
{
  "issue_numbers": [1, 2, 3]
}
```

### 批量更新 Issue

```
PATCH /api/v1/repositories/{repo_id}/issues/batch
```

认证：✅ 需要

```json
{
  "issue_numbers": [1, 2],
  "updates": {"priority": "low", "assignee_id": 3}
}
```

### 批量添加标签

```
POST /api/v1/repositories/{repo_id}/issues/batch/labels
```

认证：✅ 需要

```json
{
  "issue_numbers": [1, 2],
  "label_ids": [1, 3]
}
```

### 批量移除标签

```
DELETE /api/v1/repositories/{repo_id}/issues/batch/labels
```

认证：✅ 需要

```json
{
  "issue_numbers": [1, 2],
  "label_ids": [1, 3]
}
```

### 获取 Issue 详情

```
GET /api/v1/repositories/{repo_id}/issues/{issue_number}
```

### 更新 Issue

```
PATCH /api/v1/repositories/{repo_id}/issues/{issue_number}
```

认证：✅ 需要

```json
{
  "title": "Updated title",
  "description": "Updated description",
  "priority": "low",
  "assignee_id": 3,
  "label_ids": [1, 2]
}
```

### 关闭 Issue

```
POST /api/v1/repositories/{repo_id}/issues/{issue_number}/close
```

认证：✅ 需要

### 重新打开 Issue

```
POST /api/v1/repositories/{repo_id}/issues/{issue_number}/reopen
```

认证：✅ 需要

### 获取 Issue 评论列表

```
GET /api/v1/repositories/{repo_id}/issues/{issue_number}/comments
```

### 创建 Issue 评论

```
POST /api/v1/repositories/{repo_id}/issues/{issue_number}/comments
```

认证：✅ 需要

```json
{
  "content": "I can reproduce this on v1.2.3"
}
```

### 标签管理

#### 获取标签列表

```
GET /api/v1/repositories/{repo_id}/labels
```

#### 创建标签

```
POST /api/v1/repositories/{repo_id}/labels
```

```json
{
  "name": "bug",
  "color": "#d73a4a",
  "description": "Something isn't working"
}
```

#### 更新标签

```
PATCH /api/v1/repositories/{repo_id}/labels/{label_id}
```

```json
{
  "name": "bug",
  "color": "#d73a4a",
  "description": "Updated description"
}
```

#### 删除标签

```
DELETE /api/v1/repositories/{repo_id}/labels/{label_id}
```

---

## 15. Webhook

### 创建 Webhook

```
POST /api/v1/repositories/{repo_id}/webhooks
```

认证：✅ 需要

```json
{
  "url": "https://example.com/webhook",
  "events": ["push", "pull_request", "issues"],
  "secret": "your_secret",
  "content_type": "application/json",
  "is_active": true
}
```

支持的事件类型：

| 事件 | 说明 |
|------|------|
| push | 代码推送 |
| pull_request | PR 创建/合并/关闭 |
| issues | Issue 创建/关闭 |
| fork | Fork 创建 |
| release | Release 发布/删除 |
| member | 成员变更 |

### 获取 Webhook 列表

```
GET /api/v1/repositories/{repo_id}/webhooks?page=1&limit=20
```

认证：✅ 需要

### 获取 Webhook 详情

```
GET /api/v1/repositories/{repo_id}/webhooks/{webhook_id}
```

认证：✅ 需要

### 更新 Webhook

```
PATCH /api/v1/repositories/{repo_id}/webhooks/{webhook_id}
```

认证：✅ 需要

```json
{
  "url": "https://example.com/new-webhook",
  "events": ["push"],
  "secret": "new_secret",
  "content_type": "application/json",
  "is_active": true
}
```

### 删除 Webhook

```
DELETE /api/v1/repositories/{repo_id}/webhooks/{webhook_id}
```

认证：✅ 需要

Response: 204 No Content

### 测试 Webhook

```
POST /api/v1/repositories/{repo_id}/webhooks/{webhook_id}/test
```

认证：✅ 需要

发送测试事件（`ping`）到 Webhook URL。

### 获取投递记录列表

```
GET /api/v1/repositories/{repo_id}/webhooks/{webhook_id}/deliveries?page=1&limit=20
```

认证：✅ 需要

### 获取投递记录详情

```
GET /api/v1/repositories/{repo_id}/webhooks/{webhook_id}/deliveries/{delivery_id}
```

认证：✅ 需要

---

## 16. 应用管理

**基础路径**: `/` 和 `/api/app`（注意：这些端点不属于 `/api/v1/`）

### 根路由

```
GET /
```

认证：无

```json
{
  "message": "Welcome to Perseus API",
  "title": "Perseus",
  "version": "1.0.0",
  "status": "running"
}
```

### 健康检查

```
GET /health
```

认证：无

```json
{
  "status": "healthy",
  "timestamp": "2026-06-10T12:00:00",
  "service": "Perseus"
}
```

### 系统状态

```
GET /api/app/status
```

认证：无（公开端点）

```json
{
  "status": "running",
  "debug_mode": false,
  "uptime_seconds": 86400,
  "uptime_formatted": "1 day",
  "version": "1.0.0",
  "server_time": "2026-06-10T12:00:00",
  "process": {
    "pid": 1234,
    "memory_mb": 128.5,
    "cpu_percent": 2.3,
    "threads": 12
  },
  "requests": {
    "total": 1000,
    "success": 950,
    "errors": 50
  },
  "git_operations": {
    "total": 500,
    "success": 498,
    "failed": 2
  }
}
```

### 获取配置

```
GET /api/app/config?section=server
```

认证：✅ 需要管理员权限或调试模式

| 参数 | 说明 |
|------|------|
| section | 可选，配置节名称（server/app/storage/database/logging/security 等）|

Response:
```json
{
  "success": true,
  "data": { "...": "..." },
  "errors": []
}
```

### 更新配置

```
POST /api/app/config
```

认证：✅ 需要管理员权限或调试模式

```json
{
  "config": {
    "server": {
      "host": "0.0.0.0",
      "port": 8000
    },
    "app": {
      "debug": true
    }
  }
}
```

Response:
```json
{
  "success": true,
  "errors": [],
  "hints": ["重启应用使配置生效"]
}
```

### 重置配置

```
POST /api/app/config/reset
```

认证：✅ 需要管理员权限或调试模式

### 验证配置

```
POST /api/app/config/validate
```

认证：✅ 需要管理员权限或调试模式

```json
{
  "config": { "app": { "debug": true } }
}
```

### 获取日志信息

```
GET /api/app/logs
```

认证：✅ 需要管理员权限或调试模式

Response:
```json
{
  "log_dir": "/var/log/perseus",
  "today_dir": "/var/log/perseus/2026-06-10",
  "today_files": ["app.log", "error.log"],
  "available_dates": ["2026-06-10", "2026-06-09"]
}
```

### 查看日志内容

```
GET /api/app/logs/content?date=2026-06-10&log_name=app&lines=100&level=ERROR
```

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| date | string | 今天 | 日期 (YYYY-MM-DD) |
| log_name | string | "app" | 日志文件名（不含扩展名）|
| lines | int | 100 | 返回行数（1-1000）|
| level | string | null | 过滤级别 (debug/info/warning/error/critical) |

认证：✅ 需要管理员权限或调试模式

### 清理日志

```
POST /api/app/logs/cleanup?keep_days=30
```

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| keep_days | int | 30 | 保留天数（1-365）|

认证：✅ 需要管理员权限或调试模式

### 关闭应用

```
POST /api/app/shutdown
```

认证：✅ 需要管理员权限或调试模式

⚠️ 关闭后需手动重启容器/进程。

### 重启应用

```
POST /api/app/restart
```

认证：✅ 需要管理员权限或调试模式

仅在调试模式（Uvicorn）下可用。

---

## 17. 调试接口

**基础路径**: `/api/v1/debug`

所有调试接口仅在 `app.debug=true` 时可用，且需要管理员权限。

### 调试状态

```
GET /api/v1/debug/status
```

Response:
```json
{
  "debug_mode": true,
  "config_path": "config.toml",
  "config_exists": true,
  "database_url": "sqlite+aiosqlite:///data/perseus.db",
  "database_type": "sqlite",
  "environment": {
    "PERSEUS_APP_DEBUG": "true"
  },
  "stress_test_mode": false
}
```

### 初始化数据库

```
POST /api/v1/debug/initdb?force=false&create_test_data=true
```

删除所有表并重新创建。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| force | bool | false | 是否强制重置 |
| create_test_data | bool | true | 是否创建测试数据 |

### 重置配置文件

```
POST /api/v1/debug/initconf?force=false&backup=true
```

删除当前配置文件并从 config.example.toml 恢复。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| force | bool | false | 是否强制重置 |
| backup | bool | true | 是否备份原配置文件 |

---

## 18. 错误处理

### 获取错误码信息

```
GET /api/v1/errors/info/{error_code}
```

认证：❌ 可选（调试模式或管理员可查看详细信息）

### 获取错误码信息

```
GET /api/v1/errors/info/{error_code}?message=&error_type=&details=&request_id=
```

认证：❌ 可选（调试模式或管理员可查看详细信息）

### 获取最近错误日志

```
GET /api/v1/errors/recent?limit=10
```

认证：✅ 需要管理员权限

### 上报前端错误

```
POST /api/v1/errors/report
```

认证：❌ 可选

```json
{
  "message": "Uncaught TypeError: ...",
  "stack": "at Object...",
  "url": "/dashboard",
  "level": "error"
}
```
