# 应用管理 API 设计

提供应用级别的管理功能，包括根路由、健康检查、配置管理、应用控制和系统状态监控。

> **注意**：配置管理、关机、重启等敏感 API 仅在调试模式或管理员权限下可用。

---

## 根路由

### GET /

获取应用基本信息和欢迎信息（无需认证）。

#### 响应

**200 OK**
```json
{
  "message": "Welcome to LanGit API",
  "title": "LanGit",
  "version": "1.0.0",
  "status": "running"
}
```

---

## 健康检查

### GET /health

检查应用健康状态（无需认证）。

#### 响应

**200 OK**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00.000000",
  "service": "LanGit"
}
```

---

## 获取应用配置

### GET /api/v1/v1/app/config

获取应用配置信息（需要调试模式或管理员权限）。

#### 请求头

| 参数 | 必填 | 说明 |
|------|------|------|
| Authorization | 是 | Bearer Token（管理员） |

#### 查询参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| section | string | 否 | 配置节名称，如 'server', 'app', 'storage' 等 |

#### 响应

**200 OK**
```json
{
  "success": true,
  "data": {
    "app": {
      "title": "LanGit",
      "version": "1.0.0",
      "debug": false
    },
    "server": {
      "host": "0.0.0.0",
      "port": 8000
    }
  },
  "errors": []
}
```

**403 Forbidden**
```json
{
  "detail": "该操作仅在调试模式或管理员权限下可用"
}
```

---

## 更新应用配置

### POST /api/v1/v1/app/config

更新应用配置（需要调试模式或管理员权限）。

#### 请求头

| 参数 | 必填 | 说明 |
|------|------|------|
| Authorization | 是 | Bearer Token（管理员） |
| Content-Type | 是 | application/json |

#### 请求体

```json
{
  "config": {
    "app": {
      "debug": true
    },
    "server": {
      "port": 8080
    }
  }
}
```

#### 请求字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| config | object | 是 | 新的配置数据，包含要更新的配置节 |

#### 响应

**200 OK**
```json
{
  "success": true,
  "data": null,
  "errors": [],
  "hints": [
    "配置已更新，部分设置需要重启应用后生效"
  ]
}
```

**400 Bad Request**
```json
{
  "success": false,
  "data": null,
  "errors": [
    "无效的配置项: server.invalid_key"
  ],
  "hints": []
}
```

---

## 重置应用配置

### POST /api/v1/v1/app/config/reset

将配置重置为默认值（需要调试模式或管理员权限）。

#### 请求头

| 参数 | 必填 | 说明 |
|------|------|------|
| Authorization | 是 | Bearer Token（管理员） |

#### 响应

**200 OK**
```json
{
  "success": true,
  "data": null,
  "errors": [],
  "hints": [
    "配置已重置为默认值，建议重启应用"
  ]
}
```

---

## 验证配置数据

### POST /api/v1/v1/app/config/validate

验证配置数据的有效性（需要调试模式或管理员权限）。

#### 请求头

| 参数 | 必填 | 说明 |
|------|------|------|
| Authorization | 是 | Bearer Token（管理员） |
| Content-Type | 是 | application/json |

#### 请求体

```json
{
  "server": {
    "port": 8080
  },
  "app": {
    "debug": true
  }
}
```

> 请求体为空时，验证当前应用的配置。

#### 响应

**200 OK - 验证通过**
```json
{
  "success": true,
  "data": null,
  "errors": [],
  "hints": []
}
```

**200 OK - 验证失败**
```json
{
  "success": false,
  "data": null,
  "errors": [
    "server.port: 必须是 1-65535 之间的整数"
  ],
  "hints": []
}
```

---

## 获取应用状态

### GET /api/v1/v1/app/status

获取应用运行状态和系统信息（无需认证）。

#### 响应

**200 OK**
```json
{
  "status": "running",
  "debug_mode": false,
  "uptime_seconds": 3600,
  "uptime_formatted": "1小时 0分钟",
  "system": {
    "cpu_percent": 15.5,
    "memory_percent": 45.2,
    "disk_usage": {
      "total": 107374182400,
      "used": 53687091200,
      "free": 53687091200,
      "percent": 50.0
    }
  },
  "version": "1.0.0"
}
```

#### 响应字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| status | string | 应用运行状态 |
| debug_mode | boolean | 是否处于调试模式 |
| uptime_seconds | int | 运行时间（秒） |
| uptime_formatted | string | 格式化后的运行时间 |
| system | object | 系统资源使用情况 |
| version | string | 应用版本号 |

---

## 关闭应用

### POST /api/v1/v1/app/shutdown

优雅地关闭应用（需要调试模式或管理员权限）。

#### 请求头

| 参数 | 必填 | 说明 |
|------|------|------|
| Authorization | 是 | Bearer Token（管理员） |

#### 响应

**200 OK**
```json
{
  "success": true,
  "message": "应用将在稍后关闭"
}
```

**403 Forbidden**
```json
{
  "detail": "该操作仅在调试模式或管理员权限下可用"
}
```

---

## 重启应用

### POST /api/v1/v1/app/restart

重启应用（需要调试模式或管理员权限）。

> **注意**：仅在调试模式下可用（使用 Uvicorn 时）。

#### 请求头

| 参数 | 必填 | 说明 |
|------|------|------|
| Authorization | 是 | Bearer Token（管理员） |

#### 响应

**200 OK**
```json
{
  "success": true,
  "message": "应用将在稍后重启"
}
```

**403 Forbidden**
```json
{
  "detail": "该操作仅在调试模式或管理员权限下可用"
}
```

---

## 获取日志信息

### GET /api/v1/v1/app/logs

获取日志系统的目录和文件信息（需要调试模式或管理员权限）。

#### 请求头

| 参数 | 必填 | 说明 |
|------|------|------|
| Authorization | 是 | Bearer Token（管理员） |

#### 响应

**200 OK**
```json
{
  "log_dir": "/var/log/langit",
  "today_dir": "/var/log/langit/2024-01-01",
  "today_files": [
    "app.log",
    "error.log",
    "access.log"
  ],
  "available_dates": [
    "2024-01-01",
    "2023-12-31",
    "2023-12-30"
  ]
}
```

---

## 获取日志内容

### GET /api/v1/v1/app/logs/content

获取指定日志文件的内容（需要调试模式或管理员权限）。

#### 请求头

| 参数 | 必填 | 说明 |
|------|------|------|
| Authorization | 是 | Bearer Token（管理员） |

#### 查询参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| date | string | 否 | 日期 (YYYY-MM-DD)，默认为今天 |
| log_name | string | 否 | 日志文件名，如 app, error，默认 "app" |
| lines | int | 否 | 返回行数（1-1000），默认 100 |
| level | string | 否 | 过滤级别 (debug/info/warning/error/critical) |

#### 响应

**200 OK**
```json
{
  "date": "2024-01-01",
  "log_name": "app",
  "lines": 100,
  "total_lines": 1523,
  "content": "2024-01-01 10:00:00 [INFO] Application started...\n2024-01-01 10:00:01 [INFO] Server listening on port 8000...",
  "exists": true
}
```

**200 OK - 日志不存在**
```json
{
  "date": "2024-01-01",
  "log_name": "nonexistent",
  "lines": 0,
  "total_lines": 0,
  "content": "",
  "exists": false
}
```

---

## 清理旧日志

### POST /api/v1/v1/app/logs/cleanup

清理指定天数之前的日志文件（需要调试模式或管理员权限）。

#### 请求头

| 参数 | 必填 | 说明 |
|------|------|------|
| Authorization | 是 | Bearer Token（管理员） |

#### 查询参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| keep_days | int | 否 | 保留天数（1-365），默认 30 |

#### 响应

**200 OK**
```json
{
  "success": true,
  "deleted_count": 5,
  "keep_days": 30
}
```

---

## 权限说明

### 访问控制

以下接口需要调试模式或管理员权限：

- `GET /api/v1/app/config`
- `POST /api/v1/app/config`
- `POST /api/v1/app/config/reset`
- `POST /api/v1/app/config/validate`
- `POST /api/v1/app/shutdown`
- `POST /api/v1/app/restart`
- `GET /api/v1/app/logs`
- `GET /api/v1/app/logs/content`
- `POST /api/v1/app/logs/cleanup`

### 权限检查逻辑

1. **调试模式**：当 `config.app.debug = true` 时，所有权限检查通过
2. **管理员权限**：用户角色为 `admin` 时，具有管理员权限
3. **权限不足**：返回 403 错误，提示"该操作仅在调试模式或管理员权限下可用"

---

## 错误响应

### 401 Unauthorized

未提供有效的认证令牌：
```json
{
  "detail": "Invalid or expired token"
}
```

### 403 Forbidden

权限不足：
```json
{
  "detail": "该操作仅在调试模式或管理员权限下可用"
}
```

### 422 Unprocessable Entity

请求参数验证失败：
```json
{
  "detail": [
    {
      "loc": ["query", "lines"],
      "msg": "ensure this value is less than or equal to 1000",
      "type": "value_error.number.not_le"
    }
  ]
}
```
