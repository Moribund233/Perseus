# 通知系统实现设计

> **日期**: 2026-06-22
> **阶段**: Phase 3 — 后端高级功能
> **任务 ID**: F-043 ~ F-045
> **开发方针**: TDD（测试驱动开发）

---

## 概述

为 Perseus 平台实现站内通知系统，支持 PR/Issue/Review/Comment 相关通知的创建、存储、查询和实时推送。基于现有 WebSocket 基础设施实现即时通知，同时提供 REST API 供前端查询通知历史。

## 设计目标

1. **通知持久化**：通知存储到数据库，用户可查看历史和未读状态
2. **实时推送**：通过现有 WebSocket 系统即时推送通知
3. **简洁 API**：基础通知操作，易于前端对接
4. **TDD 驱动**：所有功能先写测试，再实现
5. **与现有架构一致**：遵循 Model → Service → Controller 分层

## 架构

```
┌─────────────────────────────────────────────────────────┐
│                    通知系统模块                           │
├─────────────────────────────────────────────────────────┤
│  Controller          Service           Model             │
│  ┌──────────┐       ┌──────────┐      ┌──────────────┐ │
│  │Notif API │──────→│NotifSvc  │─────→│Notification  │ │
│  │(REST)    │       │          │      │(DB Model)    │ │
│  └──────────┘       └──────────┘      └──────────────┘ │
│                           │                             │
│                     ┌──────────┐      ┌──────────────┐ │
│                     │WS Push   │─────→│WebSocket     │ │
│                     │(realtime)│      │Manager       │ │
│                     └──────────┘      └──────────────┘ │
└─────────────────────────────────────────────────────────┘
```

## 文件结构

```
perseus/
├── models/notification.py                      # 通知数据模型
├── services/notification_service.py            # 通知业务逻辑
├── controller/notification_controller.py       # 通知 API 端点
├── alembic/versions/xxx_create_notifications.py # 数据库迁移
└── tests/test_notification_model.py            # 模型测试
    tests/test_notification_service.py          # 服务测试
    tests/test_notification_api.py              # API 测试
```

## 核心组件

### 1. Notification Model (`models/notification.py`)

通知数据模型，使用 SQLAlchemy ORM。

**字段：**
- `id` (Integer, PK): 通知 ID
- `user_id` (Integer, FK → users.id): 接收用户
- `type` (String(50)): 通知类型 (pull_request, issue, review, comment)
- `title` (String(255)): 通知标题
- `message` (Text): 通知内容
- `repository_id` (Integer, FK → repositories.id): 关联仓库
- `target_type` (String(50)): 目标类型 (pull_request, issue)
- `target_id` (Integer): 目标 ID
- `is_read` (Boolean, default=False): 已读状态
- `created_at` (DateTime): 创建时间
- `read_at` (DateTime, nullable): 阅读时间

**索引：**
- `ix_notifications_user_id`: 用户查询
- `ix_notifications_user_id_is_read`: 未读计数
- `ix_notifications_created_at`: 时间排序

### 2. Notification Service (`services/notification_service.py`)

业务逻辑层。

**方法：**
- `create_notification(user_id, type, title, message, repo_id, target_type, target_id, db) -> Notification` — 创建通知
- `get_user_notifications(user_id, unread_only, skip, limit, db) -> list[Notification]` — 获取用户通知
- `get_unread_count(user_id, db) -> int` — 获取未读数量
- `mark_as_read(notification_id, user_id, db) -> Notification` — 标记已读
- `mark_all_as_read(user_id, db) -> int` — 全部标记已读
- `delete_notification(notification_id, user_id, db) -> bool` — 删除通知
- `send_realtime_notification(user_id, notification) -> None` — WebSocket 实时推送

**事件触发方法：**
- `notify_pull_request(user_id, repo_id, pr_id, action, pr_title, db)` — PR 通知
- `notify_issue(user_id, repo_id, issue_id, action, issue_title, db)` — Issue 通知
- `notify_review(user_id, repo_id, pr_id, action, reviewer_name, db)` — Review 通知
- `notify_comment(user_id, repo_id, target_type, target_id, commenter_name, db)` — 评论通知

### 3. Notification Controller (`controller/notification_controller.py`)

API 端点。

```
GET    /api/v1/notifications                # 获取当前用户通知列表
GET    /api/v1/notifications/unread-count   # 获取未读数量
PATCH  /api/v1/notifications/{id}/read      # 标记单条已读
POST   /api/v1/notifications/read-all       # 全部标记已读
DELETE /api/v1/notifications/{id}           # 删除通知
```

**响应示例：**
```json
{
  "notifications": [
    {
      "id": 1,
      "type": "pull_request",
      "title": "PR #12 合并",
      "message": "PR 'fix: 修复登录问题' 已合并到 main",
      "repository_id": 5,
      "target_type": "pull_request",
      "target_id": 12,
      "is_read": false,
      "created_at": "2026-06-22T10:30:00Z",
      "read_at": null
    }
  ],
  "total": 1,
  "unread_count": 1
}
```

## TDD 测试用例

### F-043: 站内通知

| 测试 | 场景 |
|------|------|
| `test_create_notification()` | 创建通知 |
| `test_create_notification_with_repo()` | 创建带仓库关联的通知 |
| `test_notification_model_structure()` | 模型字段完整性 |
| `test_notification_default_is_read()` | 默认未读状态 |

### F-044: 邮件通知（暂不实现）

跳过，后续迭代实现。

### F-045: 通知偏好设置

| 测试 | 场景 |
|------|------|
| `test_get_user_notifications()` | 获取用户通知列表 |
| `test_get_unread_count()` | 获取未读数量 |
| `test_mark_as_read()` | 标记单条已读 |
| `test_mark_all_as_read()` | 全部标记已读 |
| `test_delete_notification()` | 删除通知 |
| `test_get_notifications_unread_only()` | 只获取未读通知 |

## 配置

```toml
[notification]
enabled = true
max_notifications_per_user = 1000
default_page_size = 20
```

## 依赖

- 无新 Python 依赖
- 使用现有 SQLAlchemy + WebSocket 基础设施

## 实施顺序

1. **TDD RED**: 编写模型和服务测试
2. **TDD GREEN**: 实现 Model → Service → Controller
3. **TDD REFACTOR**: 优化代码结构，消除重复
4. **数据库迁移**: 生成 Alembic 迁移脚本
5. **验证**: 运行全部测试确认通过
