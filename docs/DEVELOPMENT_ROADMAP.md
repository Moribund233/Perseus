# LanGit 开发规划路线图

> 本文档记录 LanGit 项目的当前状态、功能缺口和开发规划，用于指导后续开发工作。
> 
> 最后更新：2026-02-08

---

## 📊 当前功能状态

### ✅ 已实现功能

| 模块 | 功能 | 状态 | 说明 |
|------|------|------|------|
| **用户管理** | 用户注册/登录 | ✅ | 基础认证功能 |
| **用户管理** | 用户信息管理 | ✅ | CRUD 操作 |
| **仓库管理** | 仓库 CRUD | ✅ | 创建、读取、更新、删除 |
| **仓库管理** | 物理仓库创建 | ✅ | 使用 pygit2 创建 bare 仓库 |
| **仓库管理** | 物理仓库删除 | ✅ | 删除时同步删除物理目录 |
| **仓库管理** | 物理信息 API | ✅ | API 返回 physical 字段 |
| **分支管理** | 分支 CRUD | ✅ | 数据库层面的分支管理 |
| **提交管理** | 提交记录 | ✅ | 数据库层面的提交记录 |
| **成员管理** | 仓库成员 | ✅ | 添加/移除成员、权限控制 |
| **WebSocket** | 实时通知 | ✅ | 同步状态广播 |
| **客户端** | 桌面应用 | ✅ | PySide6 桌面客户端 |
| **客户端** | Nginx 集成 | ✅ | 自动配置反向代理 |
| **安全** | 速率限制 | ✅ | 防止暴力破解和 DDoS |
| **安全** | 安全响应头 | ✅ | CSP、HSTS、XSS 防护 |
| **安全** | 审计日志 | ✅ | 记录所有敏感操作 |
| **安全** | Token 认证 | ✅ | JWT Token 认证服务 |

### ❌ 缺失功能（核心）

| 模块 | 功能 | 优先级 | 说明 |
|------|------|--------|------|
| **Git 协议** | Smart HTTP | ✅ | 支持 git clone/push/pull |
| **Git 协议** | 权限控制 | ✅ | 读写权限验证 |
| **代码浏览** | 文件树 | 🟡 P1 | 浏览仓库文件结构 |
| **代码浏览** | 文件内容 | 🟡 P1 | 查看文件源代码 |
| **提交浏览** | 提交历史 | 🟡 P1 | 查看 Commit 列表 |
| **提交浏览** | 代码对比 | 🟡 P1 | Diff 视图 |

---

## 🎯 开发阶段规划

### 第一阶段：核心 Git 功能（P0）

**目标**：让用户能够使用 Git 客户端与服务器交互

#### 1.1 Git Smart HTTP 协议 ✅

**功能需求**：
- [x] 实现 `git-upload-pack` 服务（处理 clone/fetch/pull）
- [x] 实现 `git-receive-pack` 服务（处理 push）
- [x] 支持 Git 智能传输协议
- [x] 支持 Git 引用发现

**技术方案**：
```python
# 实现方式：使用 pygit2 实现协议处理，FastAPI 路由处理 Git 请求

# 路由设计 - 已实现
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
- `dulwich` - 纯 Python Git 实现，支持协议处理
- 或 `pygit2` - 已安装，可扩展使用

**参考文档**：
- [Git HTTP Protocol](https://git-scm.com/docs/http-protocol)
- [Dulwich Documentation](https://www.dulwich.io/docs/)

#### 1.2 权限控制集成 ✅

**功能需求**：
- [x] 验证用户是否有读权限（clone/pull）
- [x] 验证用户是否有写权限（push）
- [x] 支持 HTTP Basic Auth
- [x] 支持 Token 认证（JWT 实现）

**实现要点**：
```python
# 在 Git 协议处理前验证权限 - 已实现
def check_git_permission(repo_path: str, user: Optional[User], action: str, db: Session) -> bool:
    """
    action: "read" | "write"
    """
    # 1. 解析 repo_path 获取仓库 ID
    # 2. 检查用户权限（公开仓库允许匿名读取）
    # 3. 检查成员角色（maintainer/owner 才能写入）
    # 4. 返回是否允许
    pass
```

**认证方式**：
- HTTP Basic Auth: 已支持，通过 `Authorization: Basic <base64>` 头部
- Token 认证: 预留接口，待后续实现

**预估工作量**：3-5 天

---

### 第二阶段：Web 代码浏览（P1）

**目标**：让用户能在浏览器中查看代码

#### 2.1 文件树浏览

**功能需求**：
- [ ] 获取指定分支/提交的文件树
- [ ] 支持目录展开/折叠
- [ ] 显示文件类型图标

**API 设计**：
```http
GET /api/repositories/{repo_id}/tree?ref=master&path=/src

Response:
{
  "path": "/src",
  "items": [
    {"name": "main.py", "type": "file", "size": 1024},
    {"name": "utils", "type": "directory"}
  ]
}
```

**技术实现**：
```python
# 使用 pygit2 读取树对象
import pygit2

def get_tree(repo_path: str, ref: str, sub_path: str = ""):
    repo = pygit2.Repository(repo_path)
    commit = repo.revparse_single(ref)
    tree = commit.tree
    
    # 遍历子路径
    if sub_path:
        for part in sub_path.strip("/").split("/"):
            tree = repo[tree[part].id]
    
    return tree
```

#### 2.2 文件内容查看

**功能需求**：
- [ ] 获取文件原始内容
- [ ] 支持语法高亮（返回 HTML 或前端处理）
- [ ] 支持大文件分片加载

**API 设计**：
```http
GET /api/repositories/{repo_id}/blob?ref=master&path=/src/main.py

Response:
{
  "path": "/src/main.py",
  "content": "import os\n...",
  "size": 1024,
  "encoding": "utf-8"
}
```

#### 2.3 提交历史

**功能需求**：
- [ ] 获取提交列表
- [ ] 支持分页
- [ ] 显示提交信息（作者、时间、消息）

**API 设计**：
```http
GET /api/repositories/{repo_id}/commits?ref=master&limit=20&offset=0

Response:
{
  "commits": [
    {
      "hash": "abc123...",
      "message": "Fix bug",
      "author": "John Doe",
      "email": "john@example.com",
      "timestamp": "2024-01-01T00:00:00Z"
    }
  ],
  "total": 100
}
```

**技术实现**：
```python
# 使用 pygit2 遍历提交历史
def get_commits(repo_path: str, ref: str, limit: int = 20):
    repo = pygit2.Repository(repo_path)
    commit = repo.revparse_single(ref)
    
    commits = []
    walker = repo.walk(commit.id, pygit2.GIT_SORT_TIME)
    
    for i, c in enumerate(walker):
        if i >= limit:
            break
        commits.append({
            "hash": str(c.id),
            "message": c.message,
            "author": c.author.name,
            "email": c.author.email,
            "timestamp": c.author.time
        })
    
    return commits
```

#### 2.4 代码对比（Diff）

**功能需求**：
- [ ] 对比两个提交
- [ ] 对比工作区与最新提交
- [ ] 显示行级差异

**API 设计**：
```http
GET /api/repositories/{repo_id}/diff?from=abc123&to=def456

Response:
{
  "files": [
    {
      "path": "main.py",
      "status": "modified",
      "additions": 10,
      "deletions": 5,
      "diff": "@@ -1,5 +1,5 @@..."
    }
  ]
}
```

**预估工作量**：5-7 天

---

### 第三阶段：协作功能（P2）

**目标**：支持团队协作开发

#### 3.1 Pull Request / Merge Request

**功能需求**：
- [ ] 创建 PR（源分支 → 目标分支）
- [ ] PR 列表和详情
- [ ] 代码审查（行级评论）
- [ ] 合并 PR

**数据库设计**：
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

**预估工作量**：7-10 天

#### 3.2 Issue 跟踪

**功能需求**：
- [ ] 创建/编辑/关闭 Issue
- [ ] Issue 标签和分类
- [ ] 指派负责人
- [ ] 关联提交

**预估工作量**：5-7 天

---

### 第四阶段：高级功能（P3）

#### 4.1 Webhook

**功能需求**：
- [ ] 配置 Webhook URL
- [ ] 推送事件（push、PR、issue）
- [ ] 签名验证

**预估工作量**：3-5 天

#### 4.2 CI/CD 集成

**功能需求**：
- [ ] 简单的构建脚本配置
- [ ] 构建状态显示
- [ ] 构建日志查看

**预估工作量**：10-15 天

#### 4.3 代码搜索

**功能需求**：
- [ ] 全文代码搜索
- [ ] 支持正则表达式
- [ ] 跨仓库搜索

**预估工作量**：5-7 天

---

## 🛠️ 技术栈建议

### 后端
- **框架**：FastAPI（已使用）
- **Git 操作**：pygit2（已安装）
- **数据库**：SQLite（开发）/ PostgreSQL（生产）
- **缓存**：Redis（可选，用于会话和缓存）
- **消息队列**：Celery + Redis（可选，用于异步任务）

### 前端
- **框架**：Vue.js 3（已使用）
- **UI 组件**：Element Plus（已使用）
- **代码高亮**：highlight.js 或 Prism.js
- **Diff 显示**：diff2html 或自研

### 部署
- **Web 服务器**：Nginx（已集成）
- **WSGI**：Gunicorn + Uvicorn
- **进程管理**：Supervisor 或 systemd
- **容器化**：Docker + Docker Compose

---

## 📅 推荐开发顺序

### 第 1 周：Git HTTP 协议
1. 研究 Git Smart HTTP 协议
2. 实现 `git-upload-pack`（clone/pull）
3. 实现 `git-receive-pack`（push）
4. 集成权限验证
5. 测试各种 Git 操作

### 第 2 周：代码浏览
1. 实现文件树 API
2. 实现文件内容 API
3. 前端文件浏览器组件
4. 实现提交历史 API
5. 前端提交历史组件

### 第 3 周：代码审查
1. 实现 Diff API
2. 前端 Diff 显示组件
3. 设计 PR 数据库模型
4. 实现 PR CRUD API
5. 前端 PR 界面

### 第 4 周：Issue 和优化
1. 实现 Issue 功能
2. 添加 Webhook 支持
3. 性能优化
4. 完善文档

---

## 📝 待办事项清单

### 立即开始 ✅
- [x] 创建 Git HTTP 协议控制器
- [x] 实现引用发现端点
- [x] 实现 upload-pack 服务
- [x] 实现 receive-pack 服务
- [x] 添加 Git 路由到主应用
- [x] 实现速率限制
- [x] 添加安全响应头中间件
- [x] 配置审计日志系统
- [x] 实现 Token 认证服务

### 短期计划
- [ ] 设计文件树 API
- [ ] 实现文件浏览功能
- [ ] 设计提交历史 API
- [ ] 实现提交浏览功能
- [ ] 前端代码浏览器组件

### 中期计划
- [ ] 设计 PR 数据模型
- [ ] 实现 PR 功能
- [ ] 实现代码审查
- [ ] 设计 Issue 数据模型
- [ ] 实现 Issue 功能

### 长期计划
- [ ] Webhook 系统
- [ ] CI/CD 集成
- [ ] 代码搜索
- [ ] 性能优化
- [ ] 生产部署文档

---

## 🔗 参考资源

### Git 协议
- [Git Internals - Transfer Protocols](https://git-scm.com/book/en/v2/Git-Internals-Transfer-Protocols)
- [Git HTTP Protocol Documentation](https://git-scm.com/docs/http-protocol)
- [Dulwich - Python Git Library](https://www.dulwich.io/)

### 类似项目
- [Gitea](https://gitea.io/) - 轻量级 Git 服务
- [GitBucket](https://gitbucket.github.io/) - Scala 实现的 Git 平台
- [Gogs](https://gogs.io/) - 极易搭建的自助 Git 服务

### 技术参考
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pygit2 Documentation](https://www.pygit2.org/)
- [Vue.js 3 Documentation](https://vuejs.org/)

---

## 💡 开发建议

1. **先实现核心功能**：Git HTTP 协议是最重要的，没有它其他功能都没意义

2. **使用现有库**：不要自己实现 Git 协议，使用 dulwich 或 pygit2

3. **逐步迭代**：不要试图一次性实现所有功能，先让基础功能可用

4. **充分测试**：Git 操作涉及数据安全，务必充分测试

5. **文档同步**：每实现一个功能，同步更新 API 文档

---

## 📞 问题反馈

如果在开发过程中遇到问题，可以：
1. 查看本文档的参考资源
2. 参考类似开源项目的实现
3. 在团队内讨论技术方案

---

**祝开发顺利！**
