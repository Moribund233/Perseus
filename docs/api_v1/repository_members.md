# 仓库成员管理 API 设计

## 成员列表

### GET /api/v1/v1/repositories/{repo_id}/members

获取仓库成员列表（需要认证）。

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
[
  {
    "id": 1,
    "user_id": 2,
    "username": "jane_doe",
    "full_name": "Jane Doe",
    "email": "jane@example.com",
    "role": "developer",
    "is_active": true,
    "joined_at": "2024-01-01T00:00:00"
  }
]
```

---

## 添加成员

### POST /api/v1/v1/repositories/{repo_id}/members

添加成员到仓库（需要管理员权限）。

#### 请求头

| 参数 | 必填 | 说明 |
|------|------|------|
| Authorization | 是 | Bearer Token |

#### 请求体

```json
{
  "user_id": 2,
  "role": "developer"
}
```

#### 角色说明

| 角色 | 权限 |
|------|------|
| owner | 所有者，拥有所有权限 |
| admin | 管理员，可管理仓库设置和成员 |
| developer | 开发者，可推送代码、创建PR |
| readonly | 只读，仅可查看代码 |

#### 响应

**201 Created**
```json
{
  "id": 1,
  "user_id": 2,
  "repository_id": 1,
  "role": "developer",
  "is_active": true,
  "joined_at": "2024-01-01T00:00:00"
}
```

---

## 更新成员角色

### PUT /api/v1/v1/repositories/{repo_id}/members/{user_id}

更新成员角色（需要管理员权限）。

#### 请求参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| repo_id | path | 是 | 仓库ID |
| user_id | path | 是 | 用户ID |

#### 请求体

```json
{
  "role": "admin"
}
```

---

## 移除成员

### DELETE /api/v1/v1/repositories/{repo_id}/members/{user_id}

从仓库移除成员（需要管理员权限）。

#### 请求参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| repo_id | path | 是 | 仓库ID |
| user_id | path | 是 | 用户ID |

#### 响应

**200 OK**
```json
{
  "message": "Member removed successfully"
}
```

---

## 响应字段说明

### 成员对象

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | 成员记录ID |
| user_id | int | 用户ID |
| username | string | 用户名 |
| full_name | string | 全名 |
| email | string | 邮箱 |
| role | string | 角色：owner/admin/developer/readonly |
| is_active | boolean | 是否激活 |
| joined_at | string | 加入时间 |

---

## 错误响应

```json
{
  "detail": "错误描述信息"
}
```
