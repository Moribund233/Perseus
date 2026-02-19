# Pull Request API 设计

## PR 列表

### GET /api/v1/v1/repositories/{repo_id}/pull-requests

获取 PR 列表。

#### 请求参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| repo_id | path | 是 | 仓库ID |
| status | query | 否 | 状态筛选：open/merged/closed |
| author | query | 否 | 作者ID筛选 |
| page | query | 否 | 页码，默认1 |
| limit | query | 否 | 每页数量，默认20，最大100 |

#### 响应

**200 OK**
```json
{
  "items": [
    {
      "id": 1,
      "pr_number": 1,
      "title": "Add new feature",
      "description": "This PR adds a new feature",
      "status": "open",
      "source_branch": "feature/new-feature",
      "target_branch": "main",
      "author": {
        "id": 1,
        "username": "john_doe",
        "full_name": "John Doe"
      },
      "repository_id": 1,
      "created_at": "2024-01-01T00:00:00",
      "updated_at": "2024-01-01T00:00:00"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 50
  }
}
```

---

## 创建 PR

### POST /api/v1/v1/repositories/{repo_id}/pull-requests

创建 Pull Request（需要认证）。

#### 请求头

| 参数 | 必填 | 说明 |
|------|------|------|
| Authorization | 是 | Bearer Token |

#### 请求体

```json
{
  "title": "Add new feature",
  "description": "This PR adds a new feature",
  "source_branch": "feature/new-feature",
  "target_branch": "main"
}
```

#### 响应

**201 Created**
```json
{
  "id": 1,
  "pr_number": 1,
  "title": "Add new feature",
  "description": "This PR adds a new feature",
  "status": "open",
  "source_branch": "feature/new-feature",
  "target_branch": "main",
  "author": {
    "id": 1,
    "username": "john_doe",
    "full_name": "John Doe"
  },
  "repository_id": 1,
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00"
}
```

---

## 获取 PR 详情

### GET /api/v1/v1/repositories/{repo_id}/pull-requests/{pr_number}

获取 PR 详情（包含评论和审查）。

#### 请求参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| repo_id | path | 是 | 仓库ID |
| pr_number | path | 是 | PR 编号 |

#### 响应

**200 OK**
```json
{
  "id": 1,
  "pr_number": 1,
  "title": "Add new feature",
  "description": "This PR adds a new feature",
  "status": "open",
  "source_branch": "feature/new-feature",
  "target_branch": "main",
  "author": {
    "id": 1,
    "username": "john_doe",
    "full_name": "John Doe"
  },
  "repository_id": 1,
  "comments": [...],
  "reviews": [...],
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00"
}
```

---

## 更新 PR

### PATCH /api/v1/v1/repositories/{repo_id}/pull-requests/{pr_number}

更新 Pull Request（需要认证）。

#### 请求体

```json
{
  "title": "Updated title",
  "description": "Updated description"
}
```

---

## 关闭 PR

### POST /api/v1/v1/repositories/{repo_id}/pull-requests/{pr_number}/close

关闭 Pull Request（需要认证）。

---

## 合并 PR

### POST /api/v1/v1/repositories/{repo_id}/pull-requests/{pr_number}/merge

合并 Pull Request（需要认证）。

#### 请求体

```json
{
  "merge_method": "merge"
}
```

#### 合并方式

- `merge`: 创建合并提交
- `squash`: 压缩合并
- `rebase`: 变基合并

---

## PR 评论

### GET /api/v1/v1/repositories/{repo_id}/pull-requests/{pr_number}/comments

获取 PR 评论列表。

### POST /api/v1/v1/repositories/{repo_id}/pull-requests/{pr_number}/comments

创建 PR 评论（需要认证）。

#### 请求体

```json
{
  "content": "Great work!",
  "file_path": "src/app.py",
  "line_number": 10,
  "commit_hash": "abc123...",
  "parent_id": null
}
```

---

## PR 审查

### POST /api/v1/v1/repositories/{repo_id}/pull-requests/{pr_number}/reviews

创建 PR 审查（需要认证）。

#### 请求体

```json
{
  "status": "approved",
  "comment": "LGTM"
}
```

#### 审查状态

- `approved`: 批准
- `changes_requested`: 请求修改

---

## 响应字段说明

### PR 对象

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | PR ID |
| pr_number | int | PR 编号 |
| title | string | 标题 |
| description | string | 描述 |
| status | string | 状态：open/merged/closed |
| source_branch | string | 源分支 |
| target_branch | string | 目标分支 |
| author | object | 作者信息 |
| repository_id | int | 仓库ID |
| created_at | string | 创建时间 |
| updated_at | string | 更新时间 |

---

## 错误响应

```json
{
  "detail": "错误描述信息"
}
```
