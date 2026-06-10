# Perseus

一个基于 Git 的本地化协作开发平台，提供完整的代码仓库管理、协作开发和部署能力。

## 技术架构

```
┌─────────────────────────────────────────────────────────────┐
│                      Perseus Platform                        │
├─────────────────┬─────────────────┬─────────────────────────┤
│  Desktop Client │   Web Frontend  │      Backend API        │
│   (Tauri+Rust)  │   (Vue 3+TS)    │    (FastAPI+Python)     │
└─────────────────┴─────────────────┴─────────────────────────┘
```

## 技术栈

### 后端服务

| 组件 | 技术 | 说明 |
|------|------|------|
| Web框架 | FastAPI | 高性能异步API框架 |
| ASGI服务器 | Uvicorn / Gunicorn | 开发/生产环境 |
| ORM | SQLAlchemy 2.0 | 异步数据库操作 |
| Git引擎 | pygit2 | libgit2的Python绑定 |
| 认证 | python-jose | JWT令牌认证 |
| 密码加密 | passlib + bcrypt | 安全密码哈希 |

### 前端应用

| 组件 | 技术 | 说明 |
|------|------|------|
| 框架 | Vue 3 | Composition API |
| 语言 | TypeScript | 类型安全 |
| 状态管理 | Pinia | 响应式状态存储 |
| 路由 | Vue Router 4 | SPA路由管理 |
| 构建工具 | Vite 6 | 快速构建 |

### 桌面客户端

| 组件 | 技术 | 说明 |
|------|------|------|
| 框架 | Tauri 2.x | 轻量级跨平台桌面应用 |
| 后端 | Rust | 高性能系统编程 |
| HTTP客户端 | reqwest | 异步HTTP请求 |
| 加密 | aes-gcm | 配置加密存储 |

### 数据库支持

| 数据库 | 同步驱动 | 异步驱动 |
|--------|----------|----------|
| SQLite | 内置 | aiosqlite |
| PostgreSQL | pg8000 / psycopg2 | asyncpg |
| MySQL | pymysql | aiomysql |

## 核心功能

### 仓库管理
- 仓库创建、克隆、Fork
- 分支管理与合并
- 提交历史浏览
- 文件树浏览与代码查看
- Diff 可视化对比

### 协作功能
- Issue 问题跟踪
- Pull Request 代码审查
- Webhook 事件通知
- 仓库成员权限管理

### Git HTTP 协议
- 支持 Git Smart HTTP 协议
- 兼容标准 Git 客户端
- 支持 `git clone`、`git push`、`git pull` 等操作

### 系统管理
- 多数据库迁移支持
- 实时日志推送 (WebSocket)
- 审计日志记录
- 请求速率限制
- Nginx 反向代理配置

## 项目结构

```
Perseus/
├── api/                    # API路由层
│   ├── api_v1.py          # RESTful API v1
│   ├── websocket/         # WebSocket处理
│   └── dependencies.py    # 依赖注入
├── controller/            # 控制器层
├── services/              # 业务逻辑层
├── models/                # 数据模型层
├── middleware/            # 中间件
│   ├── audit_logger.py    # 审计日志
│   ├── concurrency.py     # 并发控制
│   ├── request_stats.py   # 请求统计
│   ├── security_headers.py # 安全头
│   └── timeout.py         # 超时控制
├── utils/                 # 工具函数
│   ├── git_utils.py       # Git操作封装
│   ├── security_utils.py  # 安全工具
│   └── migration/         # 数据库迁移
├── frontend/              # Web前端
├── client/                # 桌面客户端
│   ├── src/               # Vue前端代码
│   └── src-tauri/         # Rust后端代码
├── tests/                 # 测试用例
├── config.py              # 配置管理
├── app.py                 # 应用入口
└── lifespan.py            # 生命周期管理
```

## 快速开始

### 环境要求

- Python 3.12+
- Node.js 20+
- Rust 1.77+ (桌面客户端)
- Git

### 后端启动

```bash
# 安装依赖
poetry install

# 配置环境变量 -推荐使用.env文件配置
- `DATABASE_URL`: 数据库连接URL
- `PERSEUS_SECURITY_SECRET_KEY`: JWT密钥
- `PERSEUS_APP_DEBUG`: 调试模式
- `PERSEUS_STRESS_TEST`: 压力测试模式


# 启动服务
python app.py
```

### Web前端启动

```bash
cd frontend
npm install
npm run dev
```

### 桌面客户端启动

```bash
cd client
npm install
npm run tauri dev
```

## 配置说明

配置通过 `config.toml` 文件和环境变量管理：

| 配置项 | 环境变量 | 说明 |
|--------|----------|------|
| 数据库连接 | `DATABASE_URL` | 数据库连接URL |
| JWT密钥 | `PERSEUS_SECURITY_SECRET_KEY` | 令牌加密密钥 |
| 调试模式 | `PERSEUS_APP_DEBUG` | 开启调试模式 |
| 压力测试 | `PERSEUS_STRESS_TEST` | 压力测试模式 |

## 安全特性

- JWT 令牌认证与刷新机制
- 密码 bcrypt 哈希存储
- 请求速率限制
- CORS 跨域保护
- 安全响应头 (CSP, HSTS, X-Frame-Options)
- 审计日志记录
- SQL 注入防护 (ORM)

## License

MIT License
