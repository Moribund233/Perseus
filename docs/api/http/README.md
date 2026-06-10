# Perseus HTTP API

> **基础路径**: `/api/v1`（除非另行注明）
> **认证方式**: JWT Bearer Token（通过 `Authorization: Bearer <token>` 请求头传递）
> **响应格式**: JSON

---

## 目录

1. [通用说明](#1-通用说明)
2. [认证](#2-认证)
3. [用户管理](#3-用户管理)
4. [仓库管理](#4-仓库管理)
5. [仓库成员](#5-仓库成员)
6. [分支管理](#6-分支管理)
7. [提交管理](#7-提交管理)
8. [Pull Request](#8-pull-request)
9. [Issue 管理](#9-issue-管理)
10. [Release 管理](#10-release-管理)
11. [Webhook](#11-webhook)
12. [仓库浏览器](#12-仓库浏览器)
13. [应用管理](#13-应用管理)
14. [调试接口](#14-调试接口)
15. [错误处理](#15-错误处理)

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
| `limit` | int | 20 | 每页条数（最大 100）|

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
| email | string | ✅ | 合法邮箱格式 |
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

## 4. 仓库管理

所有仓库相关接口的基础路径：`/api/v1/repositories`

### 获取仓库列表

```
GET /api/v1/repositories
```

认证：❌ 可选（公开仓库无需认证）

Query 参数：
| 参数 | 类型 | 说明 |
|------|------|------|
| search | string | 按名称/描述搜索 |
| page | int | 页码（默认 1）|
| limit | int | 每页条数（默认 20）|
| owner_id | int | 按所有者筛选 |

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

### 获取仓库详情

```
GET /api/v1/repositories/{id}
```

### 更新仓库

```
PUT /api/v1/repositories/{id}
```

### 删除仓库

```
DELETE /api/v1/repositories/{id}
```

### Fork 仓库

```
POST /api/v1/repositories/{id}/forks
```

认证：✅ 需要

Request Body:
```json
{
  "name": "my-fork",
  "description": "Forked from awesome-project",
  "is_public": true
}
```

Response:
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
GET /api/v1/repositories/{id}/forks
```

### 同步 Fork

```
POST /api/v1/repositories/{id}/sync
```

认证：✅ 需要（仅 Fork 所有者）

---

## 5. 仓库成员

### 获取成员列表

```
GET /api/v1/repositories/{id}/members
```

### 添加成员

```
POST /api/v1/repositories/{id}/members
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

### 更新成员角色

```
PUT /api/v1/repositories/{id}/members/{user_id}
```

```json
{
  "role": "admin"
}
```

### 移除成员

```
DELETE /api/v1/repositories/{id}/members/{user_id}
```

---

## 6. 分支管理

### 获取分支列表

```
GET /api/v1/repositories/{id}/branches
```

### 创建分支

```
POST /api/v1/repositories/{id}/branches
```

```json
{
  "name": "feature-xyz",
  "source_branch": "main",
  "source_commit_hash": "abc123..."
}
```

### 获取分支详情

```
GET /api/v1/repositories/{id}/branches/{name}
```

### 删除分支

```
DELETE /api/v1/repositories/{id}/branches/{name}
```

### 设置分支保护

```
PUT /api/v1/repositories/{id}/branches/{name}/protect
```

```json
{
  "is_protected": true,
  "require_code_review": true,
  "require_status_checks": true
}
```

---

## 7. 提交管理

### 获取提交历史

```
GET /api/v1/repositories/{id}/commits
```

| 参数 | 类型 | 说明 |
|------|------|------|
| branch | string | 分支名（默认 default_branch）|
| page | int | 页码 |
| limit | int | 每页条数 |

### 获取提交详情

```
GET /api/v1/repositories/{id}/commits/{hash}
```

### 获取提交差异

```
GET /api/v1/repositories/{id}/commits/{hash}/diff
```

### 比较分支/提交

```
GET /api/v1/repositories/{id}/commits/compare
```

| 参数 | 类型 | 说明 |
|------|------|------|
| base | string | 基准分支/提交 |
| head | string | 比较分支/提交 |
| diff | bool | 是否包含差异内容（默认 true）|

---

## 8. Pull Request

### 获取 PR 列表

```
GET /api/v1/repositories/{id}/pulls
```

| 参数 | 类型 | 说明 |
|------|------|------|
| state | string | open / closed / merged / all（默认 open）|
| page | int | |
| limit | int | |

### 创建 PR

```
POST /api/v1/repositories/{id}/pulls
```

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
GET /api/v1/repositories/{id}/pulls/{number}
```

### 更新 PR

```
PUT /api/v1/repositories/{id}/pulls/{number}
```

### 合并 PR

```
POST /api/v1/repositories/{id}/pulls/{number}/merge
```

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

### 关闭 PR

```
POST /api/v1/repositories/{id}/pulls/{number}/close
```

### 重新打开 PR

```
POST /api/v1/repositories/{id}/pulls/{number}/reopen
```

### 获取 PR 评论

```
GET /api/v1/repositories/{id}/pulls/{number}/comments
```

### 添加 PR 评论

```
POST /api/v1/repositories/{id}/pulls/{number}/comments
```

```json
{
  "content": "Great change!",
  "file_path": "src/main.py",
  "line_number": 42,
  "commit_hash": "abc123"
}
```

---

## 9. Issue 管理

### 获取 Issue 列表

```
GET /api/v1/repositories/{id}/issues
```

| 参数 | 类型 | 说明 |
|------|------|------|
| status | string | open / closed（默认 open）|
| priority | string | low / medium / high / critical |
| label | string | 按标签名筛选 |
| assignee_id | int | 按负责人筛选 |
| page | int | |
| limit | int | |

### 创建 Issue

```
POST /api/v1/repositories/{id}/issues
```

```json
{
  "title": "Bug: login fails on special chars",
  "description": "## Steps to reproduce\n1. Enter...",
  "priority": "high",
  "assignee_id": 2,
  "labels": ["bug", "security"]
}
```

### 获取 Issue 详情

```
GET /api/v1/repositories/{id}/issues/{number}
```

可选参数：`include_details=true`（包含评论）

### 更新 Issue

```
PUT /api/v1/repositories/{id}/issues/{number}
```

### 关闭 Issue

```
POST /api/v1/repositories/{id}/issues/{number}/close
```

### 重新打开 Issue

```
POST /api/v1/repositories/{id}/issues/{number}/reopen
```

### 标签管理

#### 获取标签列表

```
GET /api/v1/repositories/{id}/labels
```

#### 创建标签

```
POST /api/v1/repositories/{id}/labels
```

```json
{
  "name": "bug",
  "color": "#d73a4a",
  "description": "Something isn't working"
}
```

#### 为 Issue 设置标签

```
POST /api/v1/repositories/{id}/issues/{number}/labels
```

```json
{
  "labels": ["bug", "urgent"]
}
```

### 评论管理

```
GET /api/v1/repositories/{id}/issues/{number}/comments
POST /api/v1/repositories/{id}/issues/{number}/comments
```

```json
{
  "content": "I can reproduce this on v1.2.3"
}
```

---

## 10. Release 管理

### 获取 Release 列表

```
GET /api/v1/repositories/{id}/releases
```

### 创建 Release

```
POST /api/v1/repositories/{id}/releases
```

```json
{
  "tag_name": "v1.0.0",
  "target_commitish": "main",
  "name": "Version 1.0.0",
  "body": "## Changes\n- Initial release",
  "draft": false,
  "prerelease": false
}
```

### 获取 Release 详情

```
GET /api/v1/repositories/{id}/releases/{tag}
```

### 删除 Release

```
DELETE /api/v1/repositories/{id}/releases/{tag}
```

---

## 11. Webhook

### 获取 Webhook 列表

```
GET /api/v1/repositories/{id}/webhooks
```

### 创建 Webhook

```
POST /api/v1/repositories/{id}/webhooks
```

```json
{
  "url": "https://example.com/webhook",
  "secret": "your_secret",
  "events": ["push", "pull_request", "issues"],
  "active": true
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

### 更新 Webhook

```
PUT /api/v1/repositories/{id}/webhooks/{webhook_id}
```

### 删除 Webhook

```
DELETE /api/v1/repositories/{id}/webhooks/{webhook_id}
```

---

## 12. 仓库浏览器

### 获取文件树

```
GET /api/v1/repositories/{id}/tree/{path}
```

认证：私有仓库需要成员权限

Response:
```json
{
  "path": "src",
  "type": "dir",
  "entries": [
    {
      "name": "main.py",
      "type": "blob",
      "path": "src/main.py",
      "size": 2048,
      "mode": "100644"
    },
    {
      "name": "utils",
      "type": "dir",
      "path": "src/utils"
    }
  ]
}
```

### 获取文件内容

```
GET /api/v1/repositories/{id}/blob/{path}
```

Response:
```json
{
  "path": "README.md",
  "content": "# Project Title\n...",
  "encoding": "utf-8",
  "size": 1234,
  "sha": "abc123def..."
}
```

### 获取原始文件

```
GET /api/v1/repositories/{id}/raw/{path}
```

返回原始文件内容（Content-Type 自动检测，二进制文件返回 base64）。

---

## 13. 应用管理

**基础路径**: `/api/app`（注意：不在 `/api/v1/` 下）

认证：多数接口需要管理员权限或调试模式

### 健康检查

```
GET /api/app/health
```

认证：无

```json
{
  "status": "healthy",
  "timestamp": "2026-06-10T12:00:00"
}
```

### 系统状态

```
GET /api/app/status
```

认证：✅ 管理员 / 调试模式

```json
{
  "status": "running",
  "debug_mode": false,
  "uptime_seconds": 86400,
  "version": "1.0.0",
  "process": {
    "pid": 1234,
    "memory_mb": 128.5,
    "cpu_percent": 2.3,
    "threads": 12
  }
}
```

### 获取配置

```
GET /api/app/config?section=server
```

认证：✅ 管理员 / 调试模式

| 参数 | 说明 |
|------|------|
| section | 可选，配置节名称（server/app/storage/database 等）|

### 更新配置

```
POST /api/app/config
```

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

⚠️ 部分配置更新后需要重启应用才能生效。

### 重置配置

```
POST /api/app/config/reset
```

### 验证配置

```
POST /api/app/config/validate
```

### 查看日志

```
GET /api/app/logs?date=2026-06-10&log_name=perseus&lines=100&level=ERROR
```

### 清理日志

```
POST /api/app/logs/cleanup
```

```json
{
  "keep_days": 30
}
```

### 关闭应用

```
POST /api/app/shutdown
```

⚠️ 关闭后需手动重启容器/进程。

### 重启应用

```
POST /api/app/restart
```

---

## 14. 调试接口

**基础路径**: `/api/v1/debug`

所有调试接口仅在 `PERSEUS_APP_DEBUG=true` 时可用。

### 调试状态

```
GET /api/v1/debug/status
```

### 重置数据库

```
POST /api/v1/debug/db/reset
```

```json
{
  "create_test_data": true,
  "preserve_config": true
}
```

### 重置配置文件

```
POST /api/v1/debug/initconf?force=true&backup=true
```

---

## 15. 错误处理

### 获取错误码信息

```
GET /api/v1/errors/info/{error_code}
```

认证：❌ 可选（调试模式或管理员可查看详细信息）

### 上报前端错误

```
POST /api/v1/errors/report
```

```json
{
  "message": "Uncaught TypeError: ...",
  "stack": "at Object...",
  "url": "/dashboard",
  "level": "error"
}
```

认证：❌ 可选
