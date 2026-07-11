# Perseus 开发规划

> **更新日期**: 2026-07-11
> **开发方针**: 所有新功能必须采用 **TDD（测试驱动开发）**
> **开发环境**: wsl docker-compose / command: `wsl docker-compose -f docker-compose-dev.yml up -d`
> **当前阶段**: Phase 0 完成 — OAuth2 认证 + 实时引擎基础设施 ✅
> **下一阶段**: 阶段一 — 代码托管 MVP 🎯

---

## 📊 开发进度速览

### 阶段一：基础功能完善 (1-2周) ✅

| 模块 | 已完成 | 待完成 | 进度 |
|------|--------|--------|------|
| P0 — 物理仓库创建 | F-006, F-007 | - | 100% ✅ |
| P0 — 配置系统验证 | F-008, **F-009** | - | **100% ✅** |
| P1 — JWT Token 刷新 | F-010 | - | 100% ✅ |
| P1 — PR 合并实现 | F-013, F-014, F-015, F-016 | - | 100% ✅ |

**阶段一总结**: 7个功能已完成，基础设施就绪。

### 基础设施完善

| 模块 | 状态 |
|------|------|
| Docker backend entrypoint + 自动配置初始化 | ✅ |
| OpenResty 反向代理（Git HTTP Smart Protocol + API + WS）| ✅ |
| 管理员自动引导（`PERSEUS_ADMIN_*` 环境变量）| ✅ |
| 移除硬编码测试数据 | ✅ |
| 后端启动优化（`asyncio` engine / `ConfigManager.reload()` 修复）| ✅ |

### 当前阶段：阶段二 — 核心协作能力 ✅

| 模块 | 已完成 | 进度 |
|------|--------|------|
| P0 — SSH Key 管理 | F-019, F-020, **F-021** | 100% ✅ |
| P0 — 代码查看器 | **F-022**, **F-023**, **F-024** | 100% ✅ |
| P1 — Issue 看板 | **F-025**, **F-027** | 100% ✅ |
| P1 — Code Review | F-028, F-029 | 100% ✅ |
| P1 — Webhook | F-031, F-032, F-033 | 100% ✅ |

> **状态说明**:
> - **阶段二全部后端功能已完成** ✅ — Controller + API 测试已全部完成，路由已注册
> - **F-009 启动配置校验已实现** ✅ — `validate_config()` 验证数据库/存储/安全/服务器/日志配置
> - **建议**: 阶段二后端 100% 完成，可以进入阶段三开发

---

## 目录

1. [TDD 开发准则](#1-tdd-开发准则)
2. [开发阶段规划](#2-开发阶段规划)
3. [阶段一：基础功能完善](#3-阶段一基础功能完善-1-2-周)
4. [阶段二：核心协作能力](#4-阶段二核心协作能力-2-3-周)
5. [阶段三：高级功能](#5-阶段三高级功能-3-4-周)
6. [阶段四：生产准备](#6-阶段四生产准备持续)

---

## 1. TDD 开发准则

### 1.1 为什么选择 TDD

- 项目已有 16 个测试文件覆盖所有 Service 层，复用现有测试基础设施
- 后端采用 async SQLAlchemy，测试 fixture 体系已成熟（`conftest.py`）
- 全量 API 文档已完成，测试用例可直接从 API 规格推导
- 避免回归：Git 托管平台涉及数据一致性，回归测试至关重要

### 1.2 TDD 工作流

```
红 (RED)           →  绿 (GREEN)          →  重构 (REFACTOR)
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│ 编写测试用例   │      │ 实现最小代码   │      │ 优化代码质量   │
│ 预期失败      │ ───→ │ 使测试通过     │ ───→ │ 保持测试通过   │
│ (断言先行)    │      │ (不追求完美)   │      │ (消除重复)    │
└──────────────┘      └──────────────┘      └──────────────┘
```

### 1.3 测试结构规范

```
tests/
├── conftest.py              # 共享 fixture（引擎、会话、用户、仓库）
├── test_<feature>_async.py  # 异步 Service 测试（已存在）
├── test_<feature>_api.py    # HTTP API 集成测试（新增）
└── test_<feature>_ws.py     # WebSocket 测试（新增）
```

### 1.4 测试命名约定

```
# Service 层测试 — 功能导向
async def test_create_repository_success():
async def test_create_repository_duplicate_name():
async def test_create_repository_empty_owner():

# API 集成测试 — 端点导向
async def test_post_repository_returns_201():
async def test_get_repository_returns_404_if_not_found():
async def test_post_repository_requires_auth():

# 边界场景 — 条件导向
async def test_fork_private_repo_without_permission():
async def test_push_to_protected_branch_as_non_maintainer():
```

### 1.5 测试覆盖要求

| 层级 | 覆盖要求 | 运行速度 | 运行频率 |
|------|---------|----------|----------|
| **Unit**（工具函数） | 100% 关键路径 | <1ms | 每次保存 |
| **Service**（业务逻辑） | 所有正向 + 异常分支 | <100ms | 每次提交 |
| **Integration**（API 端点） | 每端点至少 1 正 1 负 | <1s | 每次推送 |
| **E2E**（完整场景） | 核心用户故事 | <10s | CI/CD |

### 1.6 测试工具链

```bash
# 运行所有测试
pytest -v

# 运行指定测试文件
pytest tests/test_fork_service_async.py -v

# 运行带覆盖率报告
pytest --cov=services --cov=api --cov-report=term-missing

# 运行并显示 print 输出（调试用）
pytest -v -s

# 仅运行标记为 e2e 的测试
pytest -v -m e2e
```

### 1.7 新功能开发清单模板

每个新功能开发应遵循以下步骤：

```markdown
- [ ] **RED**: 编写测试用例
  - [ ] 正向场景测试
  - [ ] 异常/边界场景测试
  - [ ] 权限/认证场景测试
  - [ ] 运行确认全部失败
- [ ] **GREEN**: 实现功能
  - [ ] Service 层逻辑
  - [ ] Controller 层端点
  - [ ] 参数校验（Pydantic model）
  - [ ] 运行确认全部通过
- [ ] **REFACTOR**: 代码优化
  - [ ] 消除重复（如有）
  - [ ] 统一错误处理
  - [ ] 补充 docstring
  - [ ] 运行确认全部通过
- [ ] **文档**: 更新 API 文档
  - [ ] 更新 `docs/api/http/README.md`
  - [ ] 更新 `docs/api/README.md`
```

---

## 2. 开发阶段规划

### 总体路线图

```
阶段一 (1-2周)         阶段二 (2-3周)         阶段三 (3-4周)         阶段四 (持续)
┌─────────────┐       ┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│ 基础功能完善   │       │ 核心协作能力    │       │ 高级功能      │       │ 生产准备      │
│             │       │             │       │             │       │             │
│ API 接入层    │ ───→ │ Git HTTP     │ ───→ │ Git LFS      │ ───→ │ 性能压测     │
│ 物理仓库创建   │       │ SSH Key 管理  │       │ 代码搜索      │       │ Docker 完善  │
│ 注册登录打通   │       │ 代码查看器     │       │ WebSocket     │       │ 监控集成     │
│ PR 合并实现   │       │ Issue 看板    │       │ CI/CD 集成    │       │ 文档完善     │
│ 配置系统验证   │       │ Review 系统   │       │ 通知系统      │       │ 测试覆盖     │
│             │       │ Webhook 投递  │       │ 国际化        │       │             │
└─────────────┘       └─────────────┘       └─────────────┘       └─────────────┘
```

---

## 3. 阶段一：基础功能完善（1-2 周）

**目标**：让已有后端接口真正跑通，前端能真实调用

### P0 — 物理仓库创建 ✅

| ID | 任务 | TDD 要点 | 涉及文件 | 状态 |
|----|------|---------|----------|------|
| F-006 | 创建仓库时初始化 bare repo | `test_create_repo_initializes_git_dir()` | `repository_service.py`, `git_utils.py` | ✅ |
| F-007 | 物理仓库存在性检查 | `test_repo_physical_status_detection()` | `repository_service.py` | ✅ |

### P0 — 配置系统验证 ✅

| ID | 任务 | TDD 要点 | 涉及文件 | 状态 |
|----|------|---------|----------|------|
| F-008 | ConfigManager 集成测试 | `test_config_toml_merge_with_env()` | `test_config.py`（新增）| ✅ |
| F-009 | 启动时配置完整性校验 | `test_config_invalid_db_url_fails_startup()` | `core/config.py` | ✅ 已实现 `validate_config()` |

### P1 — JWT Token 刷新 ✅

| ID | 任务 | TDD 要点 | 涉及文件 | 状态 |
|----|------|---------|----------|------|
| F-010 | JWT Token 刷新 | `test_refresh_token_works()` | `token_service.py`, `auth_controller.py` | ✅ |

### P1 — PR 合并实现 ✅

| ID | 任务 | TDD 要点 | 涉及文件 | 状态 |
|----|------|---------|----------|------|
| F-013 | git merge 操作 | `test_merge_pr_performs_git_merge()` | `pull_request_service.py`, `git_utils.py` | ✅ |
| F-014 | squash merge | `test_squash_merge_creates_single_commit()` | `pull_request_service.py`, `git_utils.py` | ✅ |
| F-015 | rebase merge | `test_rebase_merge_replays_commits()` | `pull_request_service.py`, `git_utils.py` | ✅ |
| F-016 | 合并冲突检测 | `test_detect_merge_conflict()` | `pull_request_service.py`, `git_utils.py` | ✅ |

---

## 4. 阶段二：核心协作能力（2-3 周）

**目标**：实现可用的代码托管协作流程

### P0 — Git HTTP Smart Protocol

| ID | 任务 | TDD 要点 | 涉及文件 |
|----|------|---------|----------|
| F-017 | git-http-backend 集成测试 | ~~`test_git_clone_over_http()`~~（E2E） | docker-compose, nginx |
| F-018 | git push over HTTP | ~~`test_git_push_over_http()`~~（E2E） | docker-compose, git-cgi |

> 注：F-017/018 为 E2E 测试，需在 Docker 环境中运行，不纳入单元测试。

### P0 — SSH Key 管理 🔄

| ID | 任务 | TDD 要点 | 涉及文件 | 状态 |
|----|------|---------|----------|------|
| F-019 | SSH Key CRUD | `test_add_ssh_key()`, `test_delete_ssh_key()` | `models/ssh_key.py`, `services/key_service.py` | ✅ |
| F-020 | SSH 认证集成 | `test_add_ssh_key_endpoint()` | `controller/key_controller.py` | ✅ |
| F-021 | Authorized Keys 同步 | `test_authorized_keys_file_updated()` | `services/key_service.py` | ✅ |

### P0 — 代码查看器

| ID | 任务 | TDD 要点 | 涉及文件 |
|----|------|---------|----------|
| F-022 | 文件树后端 | `test_get_file_tree_returns_structure()` | `repository_browser_service.py` | ✅ |
| F-023 | 文件内容语法高亮 | `test_get_blob_content_syntax_highlight()` | `repository_browser_service.py` | ✅ |
| F-024 | 前端文件导航 | `test_get_readme_content()`, `test_get_file_symbols()` | `repository_browser_service.py` | ✅ |

### P1 — Issue 看板

| ID | 任务 | TDD 要点 | 涉及文件 |
|----|------|---------|----------|
| F-025 | Issue 高级筛选 | `test_filter_issues_by_multiple_criteria()` | `issue_service.py` | ✅ |
| F-027 | Issue 批量操作 | `test_batch_update_issue_status()` | `issue_service.py` | ✅ |

### P1 — Code Review 系统

| ID | 任务 | TDD 要点 | 涉及文件 | 状态 |
|----|------|---------|----------|------|
| F-028 | 逐行评论（含行级定位） | `test_add_inline_comment_to_pr()` | `pull_request_service.py`, `pull_request_controller.py` | ✅ |
| F-029 | Review 状态流转（approve/changes_requested） | `test_review_approval_workflow()` | `pull_request_service.py`, `pull_request_controller.py` | ✅ |

### P1 — Webhook 真实投递

| ID | 任务 | TDD 要点 | 涉及文件 | 状态 |
|----|------|---------|----------|------|
| F-031 | Webhook 触发与投递 | `test_webhook_delivery_with_retry()` | `webhook_service.py` | ✅ Controller 已创建 |
| F-032 | HMAC-SHA256 签名验证 | `test_webhook_hmac_signature()` | `webhook_service.py` | ✅ 已实现 `_generate_signature()` |
| F-033 | 事件负载标准格式 | `test_push_event_payload_format()` | `webhook_service.py` | ✅ 已实现标准 Payload 格式 |

---

## 5. 阶段三：高级功能（3-4 周）

**目标**：从 "可用" 到 "好用"

### P1 — Git LFS

| ID | 任务 | TDD 要点 | 涉及文件 |
|----|------|---------|----------|
| F-034 | LFS 指针文件管理 | `test_create_lfs_pointer()` | `utils/lfs_utils.py`（新增）|
| F-035 | LFS 存储后端 | `test_lfs_upload_and_download()` | `services/lfs_service.py`（新增）|
| F-036 | LFS API 端点 | `test_lfs_batch_api()` | `controller/lfs_controller.py`（新增）|

### P1 — 代码搜索

| ID | 任务 | TDD 要点 | 涉及文件 |
|----|------|---------|----------|
| F-037 | 仓库内全文搜索 | `test_search_code_in_repository()` | `services/search_service.py`（新增）|
| F-038 | 跨仓库搜索 | `test_cross_repo_search()` | `services/search_service.py` |
| F-039 | 搜索索引维护 | `test_search_index_update_on_push()` | `services/search_service.py` |

### P1 — WebSocket 实时协作

| ID | 任务 | TDD 要点 | 涉及文件 |
|----|------|---------|----------|
| F-040 | 实时 PR 变更推送 | `test_pr_change_broadcasts_to_subscribers()` | `api/websocket/handlers/` |
| F-041 | 仓库事件广播 | `test_push_event_broadcast()` | `api/websocket/manager.py` |
| F-042 | 在线状态跟踪 | `test_online_user_tracking()` | `api/websocket/manager.py` |

### P2 — 通知系统

| ID | 任务 | TDD 要点 | 涉及文件 |
|----|------|---------|----------|
| F-043 | 站内通知 | `test_create_mention_notification()` | `services/notification_service.py`（新增）|
| F-044 | 邮件通知 | `test_send_email_notification()` | `utils/email_utils.py`（新增）|
| F-045 | 通知偏好设置 | `test_notification_preferences()` | `services/notification_service.py` |

### P2 — CI/CD 集成

| ID | 任务 | TDD 要点 | 涉及文件 |
|----|------|---------|----------|
| F-046 | Webhook → CI 触发 | `test_ci_webhook_payload()` | `webhook_trigger.py` |
| F-047 | 构建状态展示 | — | 前端新组件 |

### P2 — 国际化

| ID | 任务 | 涉及文件 |
|----|------|---------|
| F-048 | 全量中英文翻译 | `locales/zh-CN.ts`, `locales/en-US.ts` |
| F-049 | 语言切换 UI | 前端设置页 |
| F-050 | API 错误消息国际化 | `core/exception.py` |

---

## 6. 阶段四：生产准备（持续）

| ID | 任务 | 说明 |
|----|------|------|
| F-051 | Docker Compose 完善 | PostgreSQL + Nginx + git-cgi + Redis 一键部署 |
| F-052 | 性能压测 | 使用 `tests/stress_test.py` + locust/wrk |
| F-053 | 监控集成 | Prometheus metrics + Sentry 错误追踪 |
| F-054 | 文档完善 | Swagger/Redoc + 部署文档 + 用户手册 |
| F-055 | 单元测试覆盖率 | Controller 层测试，目标 >80% |
| F-056 | 安全审计 | 依赖扫描 + CORS/CSRF/SSRF 防护检查 |
| F-057 | 日志告警 | 错误日志告警规则（Error Rate > 1%）|

---

## 附录：现有测试基础

### 当前测试覆盖

| 服务模块 | 测试文件 | 状态 |
|---------|---------|------|
| 用户服务 | `test_user_service_async.py` | ✅ |
| Token 服务 | `test_token_service_async.py` | ✅ |
| Token 认证 | `test_token_service_auth_async.py` | ✅ |
| 认证控制器 | `test_auth_controller.py` | ✅ **(新增)** |
| 配置管理 | `test_config.py` | ✅ **(新增)** |
| 仓库服务 | `test_repository_service_async.py` | ✅ |
| 分支服务 | `test_branch_service_async.py` | ✅ |
| 提交服务 | `test_commit_service_async.py` | ✅ |
| Fork 服务 | `test_fork_service_async.py` | ✅ |
| PR 服务 | `test_pull_request_service_async.py` | ✅ |
| PR Diff | `test_pr_diff_async.py` | ✅ |
| Issue 服务 | `test_issue_service_async.py` | ✅ |
| Issue 标签 | `test_issue_label_management_async.py` | ✅ |
| 成员服务 | `test_member_service_async.py` | ✅ |
| Release 服务 | `test_release_service_async.py` | ✅ |
| Webhook 服务 | `test_webhook_service_async.py` | ✅ |

### 待新增测试

| 模块 | 测试文件 | 优先级 | 关联阶段 |
|------|---------|--------|---------|
| 配置管理 | `test_config.py` | P1 | 阶段一 |
| 应用服务 | `test_app_service.py` | P1 | 阶段一 |
| 仓库浏览器 | `test_repository_browser_async.py` | P1 | 阶段一 |
| 数据库管理 | `test_database_manager.py` | P2 | 阶段四 |
| API 集成测试 | `test_api_auth.py`, `test_api_repo.py`, ... | P0 | **阶段一** |
| Controller 测试 | `test_controller_*.py` | P2 | 阶段四 |
| WebSocket 测试 | `test_websocket_*.py` | P1 | 阶段三 |
| SSH Key | `test_key_service_async.py` | P0 | 阶段二 |
| 通知 | `test_notification_service.py` | P2 | 阶段三 |
| 搜索 | `test_search_service.py` | P2 | 阶段三 |
| LFS | `test_lfs_service.py` | P2 | 阶段三 |
