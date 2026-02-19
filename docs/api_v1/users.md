# 用户管理 API 设计

## 用户列表

### GET /api/v1/users

获取所有用户列表（需要认证）。

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
    "username": "john_doe",
    "email": "john@example.com",
    "full_name": "John Doe",
    "is_active": true,
    "is_admin": false,
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

---

## 获取单个用户

### GET /api/v1/users/{user_id}

根据ID获取用户信息（需要认证）。

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
{
  "id": 1,
  "username": "john_doe",
  "email": "john@example.com",
  "full_name": "John Doe",
  "is_active": true,
  "is_admin": false,
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00"
}
```

**404 Not Found**
```json
{
  "detail": "User not found"
}
```

---

## 创建用户

### POST /api/v1/users/

创建新用户。

#### 请求体

```json
{
  "username": "jane_doe",
  "email": "jane@example.com",
  "password": "secure_password",
  "full_name": "Jane Doe",
  "is_active": true,
  "is_admin": false
}
```

#### 请求字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| username | string | 是 | 用户名（唯一） |
| email | string | 是 | 邮箱（唯一） |
| password | string | 是 | 密码 |
| full_name | string | 否 | 全名 |
| is_active | boolean | 否 | 是否激活，默认 true |
| is_admin | boolean | 否 | 是否管理员，默认 false |

#### 响应

**201 Created**
```json
{
  "id": 2,
  "username": "jane_doe",
  "email": "jane@example.com",
  "full_name": "Jane Doe",
  "is_active": true,
  "is_admin": false,
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00"
}
```

**409 Conflict**
```json
{
  "detail": "Username already exists"
}
```

---

## 更新用户

### PUT /api/v1/users/{user_id}

更新用户信息（需要认证，只能更新自己的信息或管理员可更新任何用户）。

#### 请求参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| user_id | path | 是 | 用户ID |

#### 请求头

| 参数 | 必填 | 说明 |
|------|------|------|
| Authorization | 是 | Bearer Token |

#### 请求体

```json
{
  "email": "new_email@example.com",
  "full_name": "New Name",
  "is_active": true
}
```

#### 响应

**200 OK**
```json
{
  "id": 1,
  "username": "john_doe",
  "email": "new_email@example.com",
  "full_name": "New Name",
  "is_active": true,
  "is_admin": false,
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-02T00:00:00"
}
```

**403 Forbidden**
```json
{
  "detail": "You don't have permission to update this user"
}
```

---

## 删除用户

### DELETE /api/v1/users/{user_id}

删除用户（需要管理员权限）。

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
{
  "message": "User deleted successfully"
}
```

**403 Forbidden**
```json
{
  "detail": "Admin privileges required"
}
```

---

## 用户登录

### POST /api/v1/auth/login

用户登录，获取访问令牌。

#### 请求体

```json
{
  "username": "john_doe",
  "password": "secure_password"
}
```

#### 响应

**200 OK**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "username": "john_doe",
    "email": "john@example.com",
    "full_name": "John Doe",
    "is_active": true,
    "is_admin": false,
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-01-01T00:00:00"
  }
}
```

**401 Unauthorized**
```json
{
  "detail": "Invalid username or password"
}
```

---

## 响应字段说明

### 用户对象

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | 用户ID |
| username | string | 用户名 |
| email | string | 邮箱 |
| full_name | string | 全名 |
| is_active | boolean | 是否激活 |
| is_admin | boolean | 是否管理员 |
| created_at | string | 创建时间（ISO格式） |
| updated_at | string | 更新时间（ISO格式） |

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
| 409 | 资源冲突（如用户名已存在） |
| 422 | 请求格式正确但语义错误 |
| 429 | 请求过于频繁（速率限制） |
| 500 | 服务器内部错误 |
