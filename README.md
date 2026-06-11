# Perseus

一个基于 Git 的本地化协作开发平台，提供完整的代码仓库管理、协作开发和部署能力。

## 技术架构

```
┌─────────────────────────────────────────────────────────────┐
│                      Perseus Platform                        │
├─────────────────────────────────┬───────────────────────────┤
│          Web Frontend           │       Backend API         │
│         (Vue 3 + TS)            │    (FastAPI + Python)     │
└─────────────────────────────────┴───────────────────────────┘
```

## 技术栈

### 后端服务

| 组件 | 技术 | 说明 |
|------|------|------|
| Web框架 | FastAPI | 高性能异步API框架 |
| ASGI服务器 | Uvicorn / Gunicorn | 开发/生产环境 |
| ORM | SQLAlchemy 2.0 | 异步数据库操作 |
| 数据库迁移 | Alembic | 数据库版本管理 |
| Git引擎 | pygit2 | libgit2的Python绑定 |
| 认证 | python-jose | JWT令牌认证 |
| 密码加密 | passlib + bcrypt | 安全密码哈希 |
| 包管理 | UV | 高性能Python包管理器 |

### 前端应用

| 组件 | 技术 | 说明 |
|------|------|------|
| 框架 | Vue 3 | Composition API |
| 语言 | TypeScript | 类型安全 |
| 状态管理 | Pinia | 响应式状态存储 |
| 路由 | Vue Router 4 | SPA路由管理 |
| 构建工具 | Vite 6 | 快速构建 |
| UI组件 | Element Plus | 企业级UI组件库 |

### 数据库支持

| 数据库 | 同步驱动 | 异步驱动 |
|--------|----------|----------|
| SQLite | 内置 | aiosqlite |
| PostgreSQL | psycopg2 | asyncpg |

### 基础设施

| 组件 | 技术 | 说明 |
|------|------|------|
| 容器化 | Docker | 应用容器化部署 |
| 编排 | Docker Compose | 多服务编排 |
| 反向代理 | Nginx | 负载均衡、静态资源 |
| Git HTTP | git-http-backend + fcgiwrap | Git Smart HTTP 协议 |

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
- 多数据库迁移支持 (SQLite/PostgreSQL)
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
├── client/                # Web前端
│   └── web/               # Vue前端代码
├── tests/                 # 测试用例
├── docker/                # Docker配置
│   ├── dev/               # 开发环境配置
│   ├── git-cgi/           # Git CGI服务
│   └── nginx/             # Nginx配置
├── docs/                  # 文档
├── config.py              # 配置管理
├── app.py                 # 应用入口
├── lifespan.py            # 生命周期管理
├── pyproject.toml         # 项目配置与依赖
└── README.md              # 项目说明
```

## 快速开始

### 环境要求

- Python 3.12+
- Node.js 20+
- Git
- Docker & Docker Compose (可选，用于容器化部署)

### 方式一：本地开发

#### 后端启动

```bash
# 安装 UV (如果未安装)
pip install uv

# 创建虚拟环境并安装依赖
uv venv
uv pip install -e ".[dev]"

# 配置环境变量
cp .env.dev .env
# 编辑 .env 设置 PERSEUS_SECURITY_SECRET_KEY

# 启动服务
uvicorn app:app --reload
```

#### Web前端启动

```bash
cd client/web
npm install
npm run dev
```

### 方式二：Docker 开发环境

```bash
# 1. 配置环境变量
cp .env.dev .env
# 编辑 .env 设置 PERSEUS_SECURITY_SECRET_KEY

# 2. 启动后端服务 (Docker)
docker compose -f docker-compose.dev.yml up -d

# 3. 启动前端开发服务器 (本地)
cd client/web
npm run dev
```

### 方式三：生产部署

```bash
# 1. 配置环境变量
cp .env.dev .env
# 编辑 .env 设置生产环境配置

# 2. 构建并启动
docker compose -f docker-compose.yml up -d

# 3. 查看状态
docker compose -f docker-compose.yml ps
```

## 配置说明

配置通过环境变量管理（支持 `.env` 文件）：

| 配置项 | 环境变量 | 说明 | 默认值 |
|--------|----------|------|--------|
| 数据库连接 | `DATABASE_URL` | 数据库连接URL | sqlite+aiosqlite:///./perseus.db |
| JWT密钥 | `PERSEUS_SECURITY_SECRET_KEY` | 令牌加密密钥 | **必需设置** |
| 调试模式 | `PERSEUS_APP_DEBUG` | 开启调试模式 | false |
| 压力测试 | `PERSEUS_STRESS_TEST` | 压力测试模式 | false |
| 日志级别 | `LOG_LEVEL` | 日志级别 | info |

## Docker 构建

### 开发镜像

```bash
# 构建开发镜像
docker build -f docker/dev/Dockerfile.backend -t perseus-backend:dev .

# 使用国内镜像源加速构建
# 已配置阿里云镜像源，无需额外设置
```

### 生产镜像

```bash
# 构建生产镜像
docker build -t perseus:latest .

# 多阶段构建，自动优化镜像体积
```

## 安全特性

- JWT 令牌认证与刷新机制
- 密码 bcrypt 哈希存储
- 请求速率限制
- CORS 跨域保护
- 安全响应头 (CSP, HSTS, X-Frame-Options)
- 审计日志记录
- SQL 注入防护 (ORM)
- 非 root 用户运行容器

## 开发指南

### 代码规范

- 使用 Black 进行代码格式化
- 使用 isort 管理导入排序
- 使用 flake8 进行代码检查

### 测试

```bash
# 运行测试
pytest

# 运行测试并生成覆盖率报告
pytest --cov=.
```

### 数据库迁移

```bash
# 创建迁移
alembic revision --autogenerate -m "描述"

# 应用迁移
alembic upgrade head

# 回滚迁移
alembic downgrade -1
```

## License

MIT License
