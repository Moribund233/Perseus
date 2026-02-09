# 仓库管理 API 设计

## 仓库列表

### GET /api/repositories

获取所有仓库（需要认证）。

#### 请求头

| 参数 | 必填 | 说明 |
|------|------|------|
| Authorization | 是 | Bearer Token |

#### 响应

**200 OK**
```json
[
  {
    "id": 1,
    "name": "my-project",
    "path": "user/my-project",
    "description": "My awesome project",
    "is_public": true,
    "owner_id": 1,
    "default_branch": "main",
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-01-01T00:00:00",
    "status": {
      "initialized": true
    }
  }
]
```

---

## 公开仓库列表

### GET /api/repositories/public

获取所有公开仓库（无需认证）。

#### 响应

**200 OK**
```json
[
  {
    "id": 1,
    "name": "public-project",
    "path": "user/public-project",
    "description": "A public project",
    "is_public": true,
    "owner_id": 1,
    "default_branch": "main",
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-01-01T00:00:00",
    "status": {
      "initialized": true
    }
  }
]
```

---

## 获取用户的仓库

### GET /api/repositories/user/{user_id}

根据用户ID获取仓库列表（需要认证）。

#### 请求参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| user_id | path | 是 | 用户ID |

#### 请求头

| 参数 | 必填 | 说明 |
|------|------|------|
| Authorization | 是 | Bearer Token |

#### 响应

**200 OK**
```json
[
  {
    "id": 1,
    "name": "my-project",
    "path": "user/my-project",
    "description": "My awesome project",
    "is_public": true,
    "owner_id": 1,
    "default_branch": "main",
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-01-01T00:00:00",
    "status": {
      "initialized": true
    }
  }
]
```

---

## 获取单个仓库

### GET /api/repositories/{repo_id}

根据ID获取仓库信息（需要认证）。

#### 请求参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| repo_id | path | 是 | 仓库ID |

#### 请求头

| 参数 | 必填 | 说明 |
|------|------|------|
| Authorization | 是 | Bearer Token |

#### 响应

**200 OK**
```json
{
  "id": 1,
  "name": "my-project",
  "path": "user/my-project",
  "description": "My awesome project",
  "is_public": true,
  "owner_id": 1,
  "default_branch": "main",
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00",
  "status": {
    "initialized": true
  }
}
```

**404 Not Found**
```json
{
  "detail": "Repository not found"
}
```

---

## 创建仓库

### POST /api/repositories/

创建新仓库（需要认证）。

#### 请求头

| 参数 | 必填 | 说明 |
|------|------|------|
| Authorization | 是 | Bearer Token |

#### 请求体

```json
{
  "name": "new-project",
  "path": "user/new-project",
  "description": "A new project",
  "is_public": true,
  "default_branch": "main"
}
```

#### 请求字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | 是 | 仓库名称 |
| path | string | 是 | 仓库路径（唯一） |
| description | string | 否 | 仓库描述 |
| is_public | boolean | 否 | 是否公开，默认 true |
| default_branch | string | 否 | 默认分支，默认 "master" |

#### 响应

**201 Created**
```json
{
  "id": 2,
  "name": "new-project",
  "path": "user/new-project",
  "description": "A new project",
  "is_public": true,
  "owner_id": 1,
  "default_branch": "main",
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00",
  "status": {
    "initialized": true
  }
}
```

**409 Conflict**
```json
{
  "detail": "Repository path already exists"
}
```

---

## 更新仓库

### PUT /api/repositories/{repo_id}

更新仓库信息（需要认证，仅所有者或管理员可更新）。

#### 请求参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| repo_id | path | 是 | 仓库ID |

#### 请求头

| 参数 | 必填 | 说明 |
|------|------|------|
| Authorization | 是 | Bearer Token |

#### 请求体

```json
{
  "name": "updated-project",
  "description": "Updated description",
  "is_public": false,
  "default_branch": "develop"
}
```

#### 响应

**200 OK**
```json
{
  "id": 1,
  "name": "updated-project",
  "path": "user/my-project",
  "description": "Updated description",
  "is_public": false,
  "owner_id": 1,
  "default_branch": "develop",
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-02T00:00:00",
  "status": {
    "initialized": true
  }
}
```

**403 Forbidden**
```json
{
  "detail": "You don't have permission to update this repository"
}
```

---

## 删除仓库

### DELETE /api/repositories/{repo_id}

删除仓库（需要认证，仅所有者可删除）。

#### 请求参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| repo_id | path | 是 | 仓库ID |

#### 请求头

| 参数 | 必填 | 说明 |
|------|------|------|
| Authorization | 是 | Bearer Token |

#### 响应

**200 OK**
```json
{
  "message": "Repository deleted successfully"
}
```

**403 Forbidden**
```json
{
  "detail": "You don't have permission to delete this repository"
}
```

---

## 响应字段说明

### 仓库对象

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | 仓库ID |
| name | string | 仓库名称 |
| path | string | 仓库路径 |
| description | string | 仓库描述 |
| is_public | boolean | 是否公开 |
| owner_id | int | 所有者ID |
| default_branch | string | 默认分支 |
| created_at | string | 创建时间（ISO格式） |
| updated_at | string | 更新时间（ISO格式） |
| status | object | 状态信息 |
| status.initialized | boolean | 物理仓库是否已初始化 |

---

## 错误响应

所有接口在发生错误时返回统一的错误格式：

```json
{
  "detail": "错误描述信息"
}
```

### 常见错误码

| HTTP状态码 | 说明 |
|------------|------|
| 400 | 请求参数错误 |
| 401 | 未认证或认证失败 |
| 403 | 无权限访问 |
| 404 | 资源不存在 |
| 409 | 资源冲突（如仓库路径已存在） |
| 422 | 请求格式正确但语义错误 |
| 429 | 请求过于频繁（速率限制） |
| 500 | 服务器内部错误 |
