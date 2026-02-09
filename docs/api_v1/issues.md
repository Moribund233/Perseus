# Issue API 设计

## Issue 列表

### GET /api/repositories/{repo_id}/issues

获取 Issue 列表。

#### 请求参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| repo_id | path | 是 | 仓库ID |
| status | query | 否 | 状态筛选：open/closed |
| author | query | 否 | 作者ID筛选 |
| assignee | query | 否 | 指派者ID筛选 |
| label | query | 否 | 标签名称筛选 |
| page | query | 否 | 页码，默认1 |
| limit | query | 否 | 每页数量，默认20，最大100 |

#### 响应

**200 OK**
```json
{
  "items": [
    {
      "id": 1,
      "issue_number": 1,
      "title": "Bug: Login not working",
      "description": "Users cannot login with valid credentials",
      "status": "open",
      "priority": "high",
      "author": {
        "id": 1,
        "username": "john_doe",
        "full_name": "John Doe"
      },
      "assignee": {
        "id": 2,
        "username": "jane_doe",
        "full_name": "Jane Doe"
      },
      "labels": [
        {
          "id": 1,
          "name": "bug",
          "color": "#ff0000",
          "description": "Something isn't working"
        }
      ],
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

## 创建 Issue

### POST /api/repositories/{repo_id}/issues

创建 Issue（需要认证）。

#### 请求头

| 参数 | 必填 | 说明 |
|------|------|------|
| Authorization | 是 | Bearer Token |

#### 请求体

```json
{
  "title": "Bug: Login not working",
  "description": "Users cannot login with valid credentials",
  "priority": "high",
  "label_ids": [1, 2]
}
```

#### 优先级

- `low`: 低优先级
- `medium`: 中优先级
- `high`: 高优先级
- `critical`: 紧急

---

## 获取 Issue 详情

### GET /api/repositories/{repo_id}/issues/{issue_number}

获取 Issue 详情（包含评论）。

#### 请求参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| repo_id | path | 是 | 仓库ID |
| issue_number | path | 是 | Issue 编号 |

---

## 更新 Issue

### PATCH /api/repositories/{repo_id}/issues/{issue_number}

更新 Issue（需要认证）。

#### 请求体

```json
{
  "title": "Updated title",
  "description": "Updated description",
  "priority": "medium",
  "assignee_id": 2,
  "label_ids": [1, 3]
}
```

---

## 关闭 Issue

### POST /api/repositories/{repo_id}/issues/{issue_number}/close

关闭 Issue（需要认证）。

---

## 重新打开 Issue

### POST /api/repositories/{repo_id}/issues/{issue_number}/reopen

重新打开 Issue（需要认证）。

---

## Issue 评论

### GET /api/repositories/{repo_id}/issues/{issue_number}/comments

获取 Issue 评论列表。

### POST /api/repositories/{repo_id}/issues/{issue_number}/comments

创建 Issue 评论（需要认证）。

#### 请求体

```json
{
  "content": "I can reproduce this bug"
}
```

---

## 标签管理

### 获取标签列表

#### GET /api/repositories/{repo_id}/labels

### 创建标签

#### POST /api/repositories/{repo_id}/labels

```json
{
  "name": "bug",
  "color": "#ff0000",
  "description": "Something isn't working"
}
```

### 更新标签

#### PATCH /api/repositories/{repo_id}/labels/{label_id}

### 删除标签

#### DELETE /api/repositories/{repo_id}/labels/{label_id}

---

## 响应字段说明

### Issue 对象

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | Issue ID |
| issue_number | int | Issue 编号 |
| title | string | 标题 |
| description | string | 描述 |
| status | string | 状态：open/closed |
| priority | string | 优先级：low/medium/high/critical |
| author | object | 作者信息 |
| assignee | object | 指派者信息 |
| labels | array | 标签列表 |
| repository_id | int | 仓库ID |
| created_at | string | 创建时间 |
| updated_at | string | 更新时间 |
| closed_by | object | 关闭者信息（仅关闭状态） |

### 标签对象

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | 标签ID |
| name | string | 标签名称 |
| color | string | 标签颜色（HEX格式） |
| description | string | 标签描述 |

---

## 错误响应

```json
{
  "detail": "错误描述信息"
}
```
