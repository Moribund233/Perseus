# LanGit 第一阶段开发规划路线图（API v1）

> 本文档记录 LanGit 项目第一阶段开发规划（代号 API v1）的完整开发历程、技术实现和当前状态
> 
> 最后更新：2026-02-10（第一阶段功能已完整，WebSocket 基础集成完成）

---

## 📋 关于开发规划代号的说明

**重要提示**：本文档中的 "API v1" 和 "API v2" 是开发规划的代号，用于区分不同阶段的开发目标，**不代表实际的路由版本**。

### 实际路由情况
- 应用使用统一的 `api_v1_router` 注册所有路由（见 `api/api_v1.py`）
- REST API 统一使用 `/api` 前缀
- WebSocket 统一使用 `/ws` 前缀
- 不严格区分 v1/v2 版本路径

### 本文档的用途
- 记录第一阶段的功能开发历程（P0、P1、P2 阶段）
- 作为已完成功能的参考文档
- 与 [第二阶段开发规划](../api_v2/ROADMAP.md) 形成完整的项目开发历程

---

## 📋 项目概述

第一阶段（API v1）专注于构建一个功能完整的局域网 Git 服务器，包含核心 Git 操作、Web 代码浏览和团队协作功能。

### 开发阶段状态

| 阶段 | 状态 | 说明 |
|-----|------|------|
| 第一阶段（API v1） | ✅ 已完成 | 基础功能完整，可用于生产环境 |
| 第二阶段（API v2） | 🟡 规划中 | 扩展实时通信功能（详见 [第二阶段开发规划](../api_v2/ROADMAP.md)）|

### WebSocket 基础集成状态

| 功能 | 状态 | 说明 |
|-----|------|------|
| WebSocket 连接管理 | ✅ | 基础连接、心跳检测、断线重连 |
| 身份验证集成 | ✅ | Token 认证、权限校验 |
| 实时通知广播 | ✅ | 同步状态广播（用于实时协作） |
| 测试覆盖 | ✅ | 82 个测试通过 |

**说明**：WebSocket 基础功能已完成集成，为 API v2 的实时消息通知服务和聊天室功能奠定了基础。API v2 将在此基础上扩展更丰富的实时通信功能。

---

## ✅ 功能完成状态

### P0 阶段：核心 Git 功能（已完成）

| 功能模块 | 状态 | 测试覆盖 | 说明 |
|---------|------|---------|------|
| Git Smart HTTP 协议 | ✅ | 35 个测试 | 支持 clone/push/pull |
| 权限控制 | ✅ | 全覆盖 | 读写权限验证、角色管理 |
| 用户管理 | ✅ | 13 个测试 | 注册/登录/信息管理 |
| 仓库管理 | ✅ | 17 个测试 | CRUD、Fork、Star |

### P1 阶段：Web 代码浏览（已完成）

| 功能模块 | 状态 | 测试覆盖 | 说明 |
|---------|------|---------|------|
| 文件树浏览 | ✅ | 8 个测试 | 目录结构浏览 |
| 文件内容查看 | ✅ | 8 个测试 | 支持语法高亮、二进制检测 |
| 提交历史 | ✅ | 6 个测试 | 分页、筛选 |
| 代码对比 | ✅ | 5 个测试 | Diff 视图 |
| 分支管理 | ✅ | 19 个测试 | CRUD、保护、默认分支 |
| 提交管理 | ✅ | 11 个测试 | 提交历史、统计 |

### P2 阶段：协作功能 + 代码质量优化 + 安全加固（已完成）

| 功能模块 | 状态 | 测试覆盖 | 说明 |
|---------|------|---------|------|
| Pull Request | ✅ | 22 个测试 | 完整 PR 工作流 |
| Issue 跟踪 | ✅ | 27 个测试 | 生命周期管理 |
| 代码审查 | ✅ | 集成测试 | 行级评论 |
| 成员管理 | ✅ | 8 个测试 | 角色权限控制 |
| 代码质量优化 | ✅ | - | 消除重复、统一风格 |
| 安全加固 | ✅ | 51 个测试 | 100% 安全评分 |
| API 文档 | ✅ | 11 份文档 | 完整文档体系 |

---

## 📊 P0 + P1 阶段测试报告（2026-02-10）


### 新增测试文件

| 测试文件 | 用例数 | 功能覆盖 |
|---------|-------|---------|
| `tests/test_git_http_permissions.py` | 23 | Git HTTP 权限边界测试 |
| `tests/test_physical_repository_integration.py` | 16 | 物理仓库生命周期测试 |
| `docs/P1_TEST_REPORT.md` | - | P1 阶段完整测试报告文档 |

### 测试统计

| 阶段 | 测试文件 | 用例数 | 状态 |
|-----|---------|-------|------|
| **P0** | `test_git_http_api.py` | 12 | ✅ |
| **P0** | `test_git_http_permissions.py` | 23 | ✅ |
| **P1** | `test_repository_browser_api.py` | 18 | ✅ |
| **P1** | `test_repository_browser_service.py` | 16 | ✅ |
| **P1** | `test_branch_api.py` | 19 | ✅ |
| **P1** | `test_commit_api.py` | 11 | ✅ |
| **P1** | `test_physical_repository_integration.py` | 16 | ✅ |
| **P0+P1 总计** | **7** | **115** | **✅** |

---

## 📋 P2 阶段开发总结（2026-02-08 ~ 2026-02-09）

### 1. 协作功能完善

| 功能模块 | 完成状态 | 测试覆盖 | 说明 |
|---------|---------|---------|------|
| Pull Request 系统 | ✅ | 22 个测试 | 完整的 PR 工作流（创建、审查、合并） |
| Issue 跟踪系统 | ✅ | 27 个测试 | Issue 生命周期管理（标签、指派、评论） |
| 代码审查 | ✅ | 集成测试 | 行级评论和审查状态 |
| Git 合并操作 | ✅ | 集成测试 | 实际的 Git 合并（pygit2） |
| 权限检查 | ✅ | 全覆盖 | 完善的仓库权限控制 |

### 2. 代码质量优化

| 优化项 | 完成状态 | 改进内容 |
|-------|---------|---------|
| 响应构建函数提取 | ✅ | 创建 `utils/response_builder.py`，统一 7 个响应构建函数 |
| 权限检查统一 | ✅ | 完善 `utils/permission_utils.py`，统一权限检查逻辑 |
| 数据库查询工具 | ✅ | 创建 `utils/db_utils.py`，提供通用查询和分页功能 |
| Git 操作封装 | ✅ | 创建 `utils/git_utils.py`，封装 GitService 类 |
| 敏感数据过滤 | ✅ | 创建 `utils/security_utils.py`，统一敏感数据处理 |
| 同步/异步统一 | ✅ | 所有服务层和控制器层函数统一为同步函数 |
| 导入语句规范 | ✅ | 统一导入语句位置，移除函数内导入 |
| 常量提取 | ✅ | 提取 `MAX_PASSWORD_LENGTH`、`ROLE_PRIORITY` 等常量 |

**优化成果**：
- 消除 6 处重复权限检查代码
- 消除 8 处重复查询模式
- 优化多处 N+1 查询问题
- 统一代码风格，提升可维护性

### 3. 安全加固

| 安全措施 | 完成状态 | 测试评分 |
|---------|---------|---------|
| 安全响应头 | ✅ | 100% |
| 路径遍历防护 | ✅ | 100% |
| SQL 注入防护 | ✅ | 100% |
| XSS 防护 | ✅ | 100% |
| 认证绕过防护 | ✅ | 100% |
| 敏感信息泄露防护 | ✅ | 100% |
| 速率限制 | ✅ | 100% |
| 命令注入防护 | ✅ | 100% |

**安全测试总评**：安全评分 **100.0%**，51 个测试全部通过。

### 4. API 文档完善

| 文档 | 完成状态 | 内容 |
|------|---------|------|
| `api_v1/README.md` | ✅ | API 文档首页，包含所有模块索引 |
| `api_v1/frontend-sdk.md` | ✅ | 前端 SDK 完整指南（TypeScript 类型、API 封装、组合式函数） |
| `api_v1/git_http.md` | ✅ | Git HTTP API 使用指南 |
| `api_v1/users.md` | ✅ | 用户管理 API 文档 |
| `api_v1/repositories.md` | ✅ | 仓库管理 API 文档 |
| `api_v1/repository_members.md` | ✅ | 仓库成员管理 API 文档 |
| `api_v1/repository_browser.md` | ✅ | 代码浏览 API 文档 |
| `api_v1/branches.md` | ✅ | 分支管理 API 文档（含前端调用示例） |
| `api_v1/commits.md` | ✅ | 提交管理 API 文档（含前端调用示例） |
| `api_v1/pull_requests.md` | ✅ | 合并请求 API 文档 |
| `api_v1/issues.md` | ✅ | 问题跟踪 API 文档 |

### 5. 测试覆盖

| 测试类别 | 测试文件数 | 测试用例数 | 通过率 |
|---------|-----------|-----------|--------|
| 单元测试 | 5 | 55 | 100% |
| API 集成测试 | 5 | 92 | 100% |
| 安全测试 | 1 | 51 | 100% |
| WebSocket 测试 | 3 | 82 | 100% |
| **总计** | **14** | **280** | **100%** |

### 6. P2 阶段代码统计

| 类别 | 文件数 | 代码行数 | 变更 |
|------|--------|---------|------|
| 新增工具模块 | 4 | ~740 | `permission_utils.py`, `query_utils.py`, `rate_limiter.py`, `exception_handler.py` |
| 新增 API 文档 | 11 | ~3000 | 完整的 API v1 文档 |
| 重构服务层 | 10 | ~3200 | 优化代码结构，消除重复 |
| 重构控制器 | 9 | ~1600 | 统一同步函数，简化异常处理 |
| **总计** | **34** | **~8540** | - |

---

## 📊 当前功能状态总览

### ✅ 已实现功能（API v1 完整）

| 模块 | 功能 | 状态 | 说明 |
|------|------|------|------|
| **用户管理** | 用户注册/登录 | ✅ | JWT Token 认证 |
| **用户管理** | 用户信息管理 | ✅ | CRUD 操作、头像上传 |
| **仓库管理** | 仓库 CRUD | ✅ | 创建、读取、更新、删除 |
| **仓库管理** | 物理仓库创建 | ✅ | 使用 pygit2 创建 bare 仓库 |
| **仓库管理** | 物理仓库删除 | ✅ | 删除时同步删除物理目录 |
| **仓库管理** | Fork 仓库 | ✅ | 支持仓库 Fork |
| **仓库管理** | Star 仓库 | ✅ | 仓库收藏功能 |
| **Git 协议** | Smart HTTP | ✅ | 支持 git clone/push/pull |
| **Git 协议** | 权限控制 | ✅ | 读写权限验证 |
| **代码浏览** | 文件树 | ✅ | 浏览仓库文件结构 |
| **代码浏览** | 文件内容 | ✅ | 查看文件源代码 |
| **代码浏览** | 代码对比 | ✅ | Diff 视图 |
| **分支管理** | 分支 CRUD | ✅ | 创建、更新、删除分支 |
| **分支管理** | 默认分支 | ✅ | 设置默认分支 |
| **分支管理** | 分支保护 | ✅ | 保护分支、代码审查要求 |
| **提交管理** | 提交记录 | ✅ | 提交历史、搜索、统计 |
| **成员管理** | 仓库成员 | ✅ | 添加/移除成员、角色管理 |
| **协作** | Pull Request | ✅ | 完整的 PR 工作流 |
| **协作** | Issue 跟踪 | ✅ | Issue 生命周期管理 |
| **协作** | 代码审查 | ✅ | 行级评论和审查状态 |
| **协作** | Git 合并 | ✅ | 实际的 Git 合并（pygit2） |
| **安全** | 速率限制 | ✅ | 防止暴力破解和 DDoS |
| **安全** | 安全响应头 | ✅ | CSP、HSTS、XSS 防护（100% 测试通过） |
| **安全** | 审计日志 | ✅ | 记录所有敏感操作 |
| **安全** | SQL 注入防护 | ✅ | 参数化查询（100% 测试通过） |
| **安全** | XSS 防护 | ✅ | 输入验证（100% 测试通过） |
| **安全** | 路径遍历防护 | ✅ | 路径验证（100% 测试通过） |
| **WebSocket** | 基础连接 | ✅ | 连接管理、认证、心跳检测 |
| **WebSocket** | 实时通知 | ✅ | 同步状态广播 |
| **客户端** | 桌面应用 | ✅ | PySide6 桌面客户端 |
| **客户端** | Nginx 集成 | ✅ | 自动配置反向代理 |
| **文档** | API 文档 | ✅ | 完整的 API v1 文档（11 份） |
| **文档** | 前端 SDK | ✅ | TypeScript 类型、Vue 3 示例 |

---

## 🎯 技术实现详情

### Git Smart HTTP 协议实现

**路由设计**：
```python
@app.get("/git/{repo_path}/info/refs")
async def git_refs(repo_path: str, service: str = None):
    # 处理引用发现
    pass

@app.post("/git/{repo_path}/git-upload-pack")
async def git_upload_pack(repo_path: str, request: Request):
    # 处理 clone/fetch
    pass

@app.post("/git/{repo_path}/git-receive-pack")
async def git_receive_pack(repo_path: str, request: Request):
    # 处理 push
    pass
```

**实现文件**：
- `services/git_http_service.py` - Git HTTP 服务层
- `controller/git_http_controller.py` - Git HTTP 控制器层
- `api/git_http.py` - Git HTTP API 路由

**依赖库**：
- `pygit2` - Git 操作库
- `dulwich` - 纯 Python Git 实现

### 代码浏览功能实现

**文件树浏览**：
```python
def get_tree_entries(repo_path: str, ref: str = "HEAD", path: str = ""):
    """获取指定路径的文件树条目"""
    repo = pygit2.Repository(repo_path)
    commit = repo.revparse_single(ref)
    tree = commit.tree
    
    # 遍历子路径
    if path:
        for part in path.strip("/").split("/"):
            if part in tree:
                entry = tree[part]
                tree = repo[entry.id]
    
    # 收集条目
    entries = []
    for entry in tree:
        entries.append({
            "name": entry.name,
            "type": "blob" if entry.type == 3 else "tree",
            "path": f"{path}/{entry.name}".strip("/")
        })
    
    return {"path": path, "ref": ref, "entries": entries}
```

**API 端点**：
```http
GET /api/v1/repositories/{repo_id}/tree?ref=master&path=/src
GET /api/v1/repositories/{repo_id}/blob?ref=master&path=/src/main.py
GET /api/v1/repositories/{repo_id}/commits?ref=master&limit=20&offset=0
GET /api/v1/repositories/{repo_id}/diff?head=HEAD&base=HEAD~1
```

### Pull Request 实现

**数据模型**：
```python
class PullRequest(BaseModel):
    id: int
    repository_id: int
    title: str
    description: str
    source_branch: str
    target_branch: str
    author_id: int
    status: str  # "open", "merged", "closed"
    created_at: datetime
    updated_at: datetime
```

**API 端点**：
```
GET    /api/v1/repositories/{repo_id}/pull-requests              # PR 列表
POST   /api/v1/repositories/{repo_id}/pull-requests              # 创建 PR
GET    /api/v1/repositories/{repo_id}/pull-requests/{pr_number}  # PR 详情
PATCH  /api/v1/repositories/{repo_id}/pull-requests/{pr_number}  # 更新 PR
POST   /api/v1/repositories/{repo_id}/pull-requests/{pr_number}/close   # 关闭 PR
POST   /api/v1/repositories/{repo_id}/pull-requests/{pr_number}/merge   # 合并 PR
GET    /api/v1/repositories/{repo_id}/pull-requests/{pr_number}/comments # 评论列表
POST   /api/v1/repositories/{repo_id}/pull-requests/{pr_number}/comments # 创建评论
POST   /api/v1/repositories/{repo_id}/pull-requests/{pr_number}/reviews  # 创建审查
```

### WebSocket 基础实现

**说明**：WebSocket 功能在 API v1 开发阶段完成基础集成，为后续实时功能扩展奠定基础。应用路由不区分 v1/v2 版本，统一通过 `/ws` 路径访问。

**连接端点**：
```
WS /ws/notifications              # 通知频道
WS /ws/sync/{repo_id}             # 同步状态频道
```

**消息协议**：
```typescript
interface WebSocketMessage {
  type: string;           // 消息类型
  timestamp: number;      // 时间戳
  sender: {
    id: string;
    username: string;
    avatar?: string;
  };
  payload: any;           // 消息内容
}
```

**实现文件**：
- `services/websocket_service.py` - WebSocket 服务层
- `controller/websocket_controller.py` - WebSocket 控制器
- `tests/test_websocket.py` - WebSocket 测试

---

## 🛠️ 技术栈

### 后端
- **框架**：FastAPI
- **Git 操作**：pygit2
- **数据库**：SQLite（开发）/ PostgreSQL（生产）
- **缓存**：Redis（可选）
- **消息队列**：Celery + Redis（可选）

### 前端
- **框架**：Vue.js 3
- **UI 组件**：Element Plus
- **代码高亮**：highlight.js
- **Diff 显示**：diff2html

### 部署
- **Web 服务器**：Nginx
- **WSGI**：Gunicorn + Uvicorn
- **进程管理**：Supervisor
- **容器化**：Docker + Docker Compose

---

## 📅 开发历程

### 第 1 阶段：Git HTTP 协议 ✅
- 研究 Git Smart HTTP 协议
- 实现 `git-upload-pack`（clone/pull）
- 实现 `git-receive-pack`（push）
- 集成权限验证
- 测试各种 Git 操作

### 第 2 阶段：代码浏览 ✅
- 实现文件树 API
- 实现文件内容 API
- 前端文件浏览器组件
- 实现提交历史 API
- 前端提交历史组件

### 第 3 阶段：代码审查 ✅
- 实现 Diff API
- 前端 Diff 显示组件
- 设计 PR 数据库模型
- 实现 PR CRUD API
- 前端 PR 界面

### 第 4 阶段：协作功能 + 优化 ✅
- 实现 Issue 功能
- 代码质量优化
- 安全加固
- 完善文档
- WebSocket 基础集成

---

## 🎯 后续规划

API v1 功能已完整，可用于生产环境。后续开发将在 **API v2** 中进行，重点扩展 WebSocket 实时功能：

- **实时消息通知服务** - 仓库事件实时推送
- **简易组内聊天室** - 团队即时通讯
- **在线协作功能** - 实时编辑、在线状态

详见：[API v2 开发规划](../api_v2/ROADMAP.md)

---

## 📚 相关文档

- [P1 测试报告](../P1_TEST_REPORT.md) - P1 阶段详细测试报告
- [API v2 开发规划](../api_v2/ROADMAP.md) - 实时功能扩展规划
- [安全测试报告](../shared/api_v1/SECURITY_TEST_REPORT.md) - 安全测试详细报告
- [代码审查报告](../shared/api_v1/code_review_report.md) - 代码质量审查报告
- [API v1 接口文档](./README.md) - API v1 文档首页
- [前端 SDK 指南](./frontend-sdk.md) - 前端 SDK 指南

---

**API v1 开发完成，祝使用愉快！**
