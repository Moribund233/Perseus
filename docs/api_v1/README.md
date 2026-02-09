# LanGit API 文档

本文档描述了 LanGit 平台的所有 API 接口。

## 文档列表

### 核心 API

| 文档 | 描述 |
|------|------|
| [users.md](./users.md) | 用户管理 API（注册、登录、用户信息管理） |
| [repositories.md](./repositories.md) | 仓库管理 API（创建、更新、删除仓库） |
| [repository_members.md](./repository_members.md) | 仓库成员管理 API（添加、移除、权限管理） |

### 代码管理 API

| 文档 | 描述 |
|------|------|
| [repository_browser.md](./repository_browser.md) | 代码浏览 API（文件树、文件内容、提交历史、代码对比） |
| [branches.md](./branches.md) | 分支管理 API（创建、删除、保护分支等） |
| [commits.md](./commits.md) | 提交管理 API（查看提交、提交统计等） |

### 协作 API

| 文档 | 描述 |
|------|------|
| [pull_requests.md](./pull_requests.md) | 合并请求 API（创建、审查、合并 PR） |
| [issues.md](./issues.md) | 问题跟踪 API（创建、管理 Issue 和标签） |

### 前端开发

| 文档 | 描述 |
|------|------|
| [frontend-sdk.md](./frontend-sdk.md) | 前端 SDK 完整指南（TypeScript 类型、API 封装、组合式函数） |

### Git 操作 API

| 文档 | 描述 |
|------|------|
| [git_http.md](./git_http.md) | Git Smart HTTP 协议（clone/push/pull 命令行操作） |

### 其他 API

| 模块 | 路径 | 描述 |
|------|------|------|
| WebSocket API | `api/websocket/` | 实时通信（通知、进度、协作） |

## 通用规范

### 认证方式

所有需要认证的 API 都使用 Bearer Token：

```
Authorization: Bearer <access_token>
```

Token 通过登录接口获取，见 [users.md](./users.md) 的登录接口。

### 响应格式

#### 成功响应

成功时返回对应的数据结构，HTTP 状态码为 200-299。

#### 错误响应

错误时返回统一格式：

```json
{
  "detail": "错误描述信息"
}
```

常见 HTTP 状态码：

| 状态码 | 说明 |
|--------|------|
| 400 | 请求参数错误 |
| 401 | 未认证或认证失败 |
| 403 | 无权限访问 |
| 404 | 资源不存在 |
| 409 | 资源冲突 |
| 422 | 请求格式正确但语义错误 |
| 429 | 请求过于频繁（速率限制） |
| 500 | 服务器内部错误 |

### 分页参数

支持分页的列表接口使用以下参数：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| page | int | 否 | 页码，默认 1 |
| per_page / limit | int | 否 | 每页数量，默认 20-30，最大 100 |

分页响应格式：

```json
{
  "items": [...],
  "pagination": {
    "page": 1,
    "per_page": 30,
    "total": 100
  }
}
```

### 时间格式

所有时间字段使用 ISO 8601 格式：

```
2024-01-01T00:00:00
```

### 速率限制

部分敏感接口（如登录、修改操作）有速率限制，超过限制会返回 429 状态码。

## 基础端点

### 健康检查

```
GET /health
```

响应：

```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00",
  "service": "LanGit API"
}
```

### 根路径

```
GET /
```

响应：

```json
{
  "message": "Welcome to LanGit API",
  "title": "LanGit",
  "version": "1.0.0",
  "status": "running"
}
```

## API 版本

当前 API 版本为 v1，所有端点以 `/api` 为前缀。

## 权限说明

| 角色 | 权限 |
|------|------|
| 系统管理员 | 所有权限 |
| 仓库所有者 | 管理仓库设置、成员、删除仓库 |
| 仓库管理员 | 管理仓库设置、成员 |
| 开发者 | 推送代码、创建分支、创建 PR/Issue |
| 只读用户 | 查看代码、评论 |
