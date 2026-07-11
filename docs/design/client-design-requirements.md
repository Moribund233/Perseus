# Perseus 客户端设计需求文档

> **版本**: v1.0
> **更新日期**: 2026-07-11
> **定位**: 基于 Git 的本地化协作开发平台前端（Web 客户端）
> **适用范围**: 已完成后端 API 的页面层、组件层、状态层设计需求

---

## 1. 项目概述与目标

### 1.1 产品定位

Perseus 是一个**基于 Git 的本地化协作开发平台**，提供代码仓库托管、Pull Request、Issue 跟踪、代码审查、Release 管理等核心能力，并计划扩展实时协作、通知中心、CI/CD 状态展示等高级功能。

### 1.2 客户端目标

为 Perseus 平台提供一个**桌面端优先、功能完整、视觉统一**的 Web 客户端，使用户能够：

- 完成注册、登录、OAuth2 第三方登录。
- 浏览、创建、管理仓库及 Fork。
- 查看代码文件树、提交历史、Diff、README、代码符号。
- 发起 PR、Review、合并、行内评论。
- 创建 Issue、标签、指派、批量操作。
- 接收站内通知、查看实时日志、参与仓库实时协作。
- 管理员可查看系统状态、配置、日志、审计信息。

### 1.3 设计原则

1. **桌面端优先**: 以桌面浏览器为主要使用场景，不针对手机/平板做响应式断点，仅适配窗口最大化/最小化。
2. **模块内聚**: 页面、组件、Store 按业务域划分，避免跨模块耦合。
3. **实时优先**: 充分利用 WebSocket，减少轮询，关键业务事件实时推送。
4. **可扩展性**: 为 Phase 2/3 的实时协作、LFS、代码搜索、CI/CD、国际化预留扩展点。
5. **统一视觉**: 使用统一的组件库、颜色、间距、图标、徽章与状态标识。

---

## 2. 客户端现状

| 维度 | 现状 |
|------|------|
| 前端目录 | `client/web/` 尚未创建，无 `package.json` |
| 技术栈 | README 原规划为 Vue 3 + TypeScript + Pinia + Vue Router 4 + Vite 6 + Element Plus；**当前决定改为 React 技术栈** |
| 后端 API | 已完整实现 `/api/v1` 下所有 REST API |
| WebSocket | `/ws` 已就绪，支持认证、心跳、订阅、通知、仓库事件 |
| Git 协议 | 标准 Git HTTP Smart Protocol，通过 Nginx 代理，无需前端特殊处理 |
| HTML 原型 | 无 |

> **说明**: 前端技术栈已调整为 **React + TypeScript + Vite**。UI 组件库首选 **Ant Design**，兼顾组件完备性与企业级稳定性；若更偏好接近 Naive UI 的清爽风格，可选 **Arco Design**。

---

## 3. 目标用户与使用场景

### 3.1 用户角色

| 角色 | 能力 |
|------|------|
| 未登录用户 | 浏览公开仓库、查看公开仓库文件与提交历史 |
| 普通用户 | 创建仓库、管理个人仓库、Fork、PR、Issue、Review、设置 SSH Key |
| 仓库成员 | 按 `read/write/admin` 角色参与仓库协作 |
| 管理员 | 用户管理、系统配置、日志查看、调试接口、审计 |

### 3.2 核心使用场景

1. **开发者浏览代码**: 进入仓库 → 查看文件树 → 打开文件 → 阅读语法高亮代码 → 查看提交历史 → 对比 Diff。
2. **提交 PR 并 Review**: 创建 PR → 查看 Diff → 添加行内评论 → 提交 Review（通过/请求修改）→ 合并。
3. **跟踪 Issue**: 创建 Issue → 设置优先级/标签/指派人 → 评论 → 关闭/重开 → 批量管理。
4. **实时协作**: 仓库内聊天、接收 PR/Issue 变更通知、查看在线成员状态。

---

## 4. 技术栈选型建议

| 层级 | 技术 | 说明 |
|------|------|------|
| 框架 | React 19 + TypeScript 5.6+ | 函数组件 + Hooks，严格类型与后端 DTO 对齐 |
| 构建工具 | Vite 6+ | 快速 HMR、按需加载 |
| 路由 | React Router 7（或 TanStack Router） | 嵌套路由、路由守卫、权限控制、数据加载 |
| 状态管理 | Zustand / Redux Toolkit | 模块化 Store，React 生态主流方案 |
| UI 组件库 | **Ant Design 5.x** | 首选；企业级组件丰富，适合代码托管类复杂后台 |
| UI 备选 | Arco Design / shadcn/ui | Arco 风格更接近 Naive UI；shadcn/ui 灵活度最高 |
| HTTP 客户端 | axios | 封装请求拦截、Token 刷新、错误统一处理 |
| WebSocket 客户端 | 原生 WebSocket | 封装重连、心跳、消息分发器 |
| Markdown 渲染 | react-markdown + remark-gfm + react-syntax-highlighter | README、Issue/PR 描述、评论 |
| Diff 展示 | diff2html / react-diff-viewer | 代码 Diff 可视化、行内评论锚定 |
| 代码高亮 | react-syntax-highlighter | 文件内容、Diff、代码块 |
| 图标 | @ant-design/icons 或 lucide-react | 统一图标库 |
| 表单与校验 | React Hook Form + zod | 性能与类型安全兼备 |
| 代码规范 | ESLint + Prettier | 与后端一致使用 Black/isort/flake8 的风格要求对应到前端 |

---

## 5. 信息架构与页面地图

```
/                          # Landing / 产品介绍（未登录）或 Dashboard（已登录）
/login                     # 登录
/register                  # 注册
/oauth/callback            # OAuth2 回调

/explore                   # 公开仓库广场
/explore/repositories      # 公开仓库列表

/:username                 # 用户主页
/:username/:repo           # 仓库详情首页（README / 文件树）
/:username/:repo/tree/:ref/:path*      # 文件树浏览
/:username/:repo/blob/:ref/:path*      # 文件内容查看
/:username/:repo/commits/:ref          # 提交历史
/:username/:repo/commit/:hash          # 提交详情
/:username/:repo/branches              # 分支列表
/:username/:repo/tags                  # 标签列表
/:username/:repo/releases              # Release 列表
/:username/:repo/releases/:id          # Release 详情

/:username/:repo/pulls                 # PR 列表
/:username/:repo/pull/:number          # PR 详情（Diff + 评论 + Review）
/:username/:repo/pull/:number/files    # PR 文件改动
/:username/:repo/pull/:number/commits  # PR 提交列表

/:username/:repo/issues                # Issue 列表
/:username/:repo/issues/:number        # Issue 详情

/:username/:repo/settings              # 仓库设置（成员、Webhook、分支保护、标签）
/:username/:repo/settings/members
/:username/:repo/settings/webhooks
/:username/:repo/settings/branches
/:username/:repo/settings/labels
/:username/:repo/chat                   # 仓库团队聊天（Phase 2）
/:username/:repo/chat/channels          # 聊天频道管理（仓库管理员）
/:username/:repo/collab/:path*          # 协作文本编辑（按文件路径，Phase 2）

/settings/profile          # 个人设置
/settings/keys             # SSH Key 管理
/settings/notifications    # 通知偏好
/settings/accounts         # 第三方账号绑定/解绑（OAuth，Phase 0）

/notifications             # 通知中心
/admin                     # 系统管理（管理员）
/admin/users
/admin/status
/admin/logs
/admin/config
```

---

## 6. 功能模块设计需求

### 6.1 认证与账号

#### 已完成后端能力
- 本地注册/登录（JWT access + refresh）
- Token 刷新
- 用户信息查询/更新/删除
- 管理员与普通用户权限区分

#### 前端需求
1. **登录页**
   - 用户名/邮箱 + 密码表单。
   - 表单校验、错误提示、登录限速提示（429）。
   - 登录成功后保存 Token（建议 `httpOnly` Cookie 或 secure localStorage）。
2. **注册页**
   - 用户名、邮箱、密码、确认密码。
   - 密码强度提示。
3. **OAuth2 登录（Phase 0 规划）**
   - GitHub / GitLab 登录按钮。
   - OAuth 回调页处理 `code` 并换取 Token。
   - 账号关联/解绑入口（用户中心）。
4. **Token 管理**
   - 统一 HTTP 拦截器注入 `Authorization: Bearer <token>`。
   - 401 时尝试用 refresh_token 静默刷新，失败则跳转登录。
   - WebSocket 连接时通过 query `token` 传递 JWT。
5. **路由守卫**
   - 公开页面可匿名访问。
   - 私有页面要求登录，管理员页面要求 `is_admin=true`。

---

### 6.2 仓库管理

#### 已完成后端能力
- 仓库 CRUD、公开/私有、搜索、分页、统计、归档
- Fork 创建/列表/源追溯/同步
- 仓库成员管理（read/write/admin）
- Star（模型已存在）

#### 前端需求
1. **仓库列表页**
   - 当前用户仓库、公开仓库两个入口。
   - 搜索框、分页、排序（最近更新、创建时间、名称）。
   - 仓库卡片展示：名称、描述、语言、公开/私有徽章、Fork 数、Star 数、更新时间。
2. **创建仓库**
   - 表单：名称、描述、可见性（公开/私有）、默认分支。
   - 名称唯一性校验。
3. **仓库首页**
   - 顶部 Tab：Code、Issues、Pull Requests、Releases、Settings。
   - 默认展示 README 渲染 + 文件树。
   - 分支/标签选择器。
   - Clone URL 展示（HTTPS / SSH）。
4. **Fork 操作**
   - 一键 Fork 弹窗，支持自定义名称/描述/可见性。
   - Fork 列表页、源仓库链接、同步上游按钮。
5. **Star 功能**
   - 仓库标题旁 Star 按钮，显示 Star 数量，已 Star 高亮。

---

### 6.3 仓库浏览器（代码查看）

#### 已完成后端能力
- 文件树浏览
- 文件内容查看（含语法高亮原始内容）
- 提交历史、文件历史
- Diff 对比
- README 渲染
- 文件符号提取（当前仅 Python）
- 语言检测

#### 前端需求
1. **文件树**
   - 左侧目录树，右侧文件列表。
   - 面包屑导航，支持点击路径跳转。
   - 文件夹展开/收起，文件图标按语言/扩展名区分。
2. **文件内容查看**
   - 代码高亮，行号显示。
   - 原始内容查看切换。
   - 文件头部显示文件大小、行数、最近修改信息。
3. **提交历史**
   - 按时间线展示 commit 列表。
   - 支持按分支、文件路径过滤。
   - 点击 commit 进入详情。
4. **Diff 展示**
   - 文件级 Diff，行内新增/删除高亮。
   - 支持 side-by-side 与 unified 两种模式切换。
   - 文件过滤、展开/折叠。
5. **README 渲染**
   - Markdown 渲染，代码块高亮，TOC 锚点。
   - 未找到 README 时友好提示。
6. **代码符号（预留）**
   - 右侧符号大纲，支持 Python 函数/类跳转。
   - 后续扩展更多语言时符号组件可复用。

---

### 6.4 Pull Request

#### 已完成后端能力
- PR CRUD、关闭、合并（merge/squash/rebase）
- 行内评论、全局评论、回复
- Code Review（approved / changes_requested）
- Diff 对比、冲突检测

#### 前端需求
1. **PR 列表页**
   - 状态筛选：Open / Merged / Closed。
   - 作者筛选、搜索、分页。
   - 列表项展示：标题、编号、作者、状态徽章、评论数、更新时间。
2. **PR 详情页**
   - 顶部概览：标题、状态、源分支 → 目标分支、作者、创建时间。
   - Tab 切换：Overview / Files Changed / Commits。
   - **Overview**: 描述 Markdown、评论时间线、Review 状态汇总。
   - **Files Changed**: Diff 视图 + 行内评论（点击行号添加评论）。
   - **Commits**: PR 包含的提交列表。
3. **创建 PR**
   - 选择源分支与目标分支。
   - 自动展示分支间 Diff。
   - 标题、描述编辑器，支持 Markdown。
4. **Review 操作**
   - Review 按钮：Approve / Request Changes / Comment。
   - 行内评论 drafts，可批量提交 Review。
5. **合并操作**
   - 合并按钮，选择 merge_method。
   - 冲突检测提示，合并后刷新 PR 状态。

---

### 6.5 Issue 管理

#### 已完成后端能力
- Issue CRUD、关闭/重开
- 标签、优先级、指派
- 评论
- 高级筛选、批量操作

#### 前端需求
1. **Issue 列表页**
   - 看板/列表双视图（列表为 MVP）。
   - 状态、标签、优先级、指派人、作者筛选。
   - 搜索框、分页、排序。
   - 批量选择：关闭/重开/更新/添加标签/移除标签。
2. **Issue 详情页**
   - 标题、状态、优先级、标签、指派人、作者、时间线。
   - 描述 Markdown 渲染。
   - 评论列表 + 评论框。
   - 右侧边栏：编辑标签/优先级/指派人。
3. **创建/编辑 Issue**
   - 标题、描述、优先级、指派人、标签。
4. **标签管理**
   - 仓库设置内标签 CRUD，支持颜色选择器。

---

### 6.6 Release 管理

#### 已完成后端能力
- Release CRUD、标签关联、草稿/预发布、附件

#### 前端需求
1. **Release 列表页**
   - 按时间倒序，区分 Latest / Draft / Pre-release 徽章。
   - 入口在仓库 Tab 中。
2. **Release 详情页**
   - 标题、标签、发布说明 Markdown、附件下载列表。
3. **创建/编辑 Release**
   - 表单：标签名、名称、描述、commit_hash、草稿/预发布开关、是否自动创建 Git 标签。
   - 附件上传/管理。

---

### 6.7 Webhook 管理

#### 已完成后端能力
- Webhook CRUD、事件触发、HMAC 签名、自动重试、投递记录、测试投递

#### 前端需求
1. **Webhook 列表页**
   - URL、事件类型、激活状态、最近投递状态。
2. **创建/编辑 Webhook**
   - URL、Secret、事件多选、Content-Type、激活开关。
3. **测试与投递记录**
   - Ping 测试按钮。
   - 投递记录列表：状态码、响应时间、重试次数、请求/响应详情。

---

### 6.8 通知中心

#### 后端状态
- 模型、Service、Controller、迁移已实现。
- WebSocket 推送已规划。

#### 前端需求
1. **通知入口**
   - 顶部导航栏铃铛图标，显示未读数量徽章。
   - 下拉面板展示最近通知。
2. **通知中心页**
   - 全部 / 未读筛选。
   - 通知列表：标题、内容、关联仓库/PR/Issue、时间。
   - 单条已读、全部已读、删除。
   - 点击通知跳转对应页面。
3. **通知偏好（预留）**
   - 用户设置中配置接收类型、邮件通知开关等。

---

### 6.9 用户中心与 SSH Key

#### 已完成后端能力
- 用户信息查询/更新
- SSH Key CRUD、指纹计算

#### 前端需求
1. **个人资料页**
   - 用户名、邮箱、全名、头像（预留）。
2. **OAuth 账号管理页**
   - 页面地址：`/settings/accounts`。
   - 展示已绑定的 GitHub / GitLab / 其他 provider 账号列表。
   - 支持绑定新账号、解绑已绑定账号（至少保留一种登录方式，防止锁死）。
   - 绑定成功后更新用户信息，JWT 携带 provider 信息。
3. **SSH Key 管理页**
   - Key 列表：名称、指纹、添加时间。
   - 添加 Key：名称 + 公钥文本框，自动校验格式。
   - 删除 Key。

---

### 6.10 系统管理（管理员）

#### 已完成后端能力
- 系统状态、配置管理、日志查看、审计日志、调试接口

#### 前端需求
1. **Dashboard**
   - 系统运行状态卡片：运行时间、内存、CPU、请求统计、Git 操作统计。
2. **用户管理**
   - 用户列表、搜索、禁用/启用、删除。
3. **配置管理**
   - TOML 配置查看/编辑/验证/重置（高风险操作二次确认）。
4. **日志查看**
   - 按日期、级别、行数筛选。
   - 实时日志 WebSocket 接入。
5. **审计日志**
   - 请求审计列表，敏感操作高亮。

---

### 6.11 实时协作与团队聊天

#### 已完成后端能力

- WebSocket 连接管理器与 Token 鉴权（Phase 0）。
- 房间/频道管理：仓库↔聊天频道关联，成员加入/离开（Phase 2）。
- 团队聊天：消息持久化、历史记录、@提及（Phase 2）。
- 在线状态：仓库/项目内在线成员可见，心跳检测（Phase 2）。
- 业务事件广播：PR / Issue / Review / Release 变更实时推送到仓库频道（Phase 2）。
- 协作文本编辑：OT/CRDT 基础实现，支持多人同时编辑文本（Phase 2）。

#### 前端需求

1. **团队聊天**
   - 入口：仓库详情页右侧聊天抽屉或独立 `/:username/:repo/chat` 页面。
   - 消息列表：按时间倒序/正序展示，支持分页加载历史消息。
   - 消息类型：文本、代码块、@提及、引用回复。
   - 输入框：支持 Markdown 快捷输入、Enter 发送、Shift+Enter 换行。
   - 未读消息徽章：仓库导航 Tab 与聊天入口显示未读数。
   - 消息操作：删除（发送者/管理员）、复制、回复。

2. **频道/房间管理**
   - 频道列表：展示仓库下所有公开/私有频道，区分当前在线人数。
   - 创建频道：名称、描述、可见性（公开/仅成员）、关联仓库（默认当前仓库）。
   - 编辑/删除频道：仅仓库 `admin` 或频道创建者可操作，删除前二次确认。
   - 成员加入/离开：点击成员头像可查看在线状态，支持邀请成员加入频道。

3. **在线状态**
   - 仓库成员头像在线指示器：绿色在线、灰色离线、黄色离开。
   - 在线成员列表面板：显示当前仓库/频道内在线用户。
   - 心跳保活：与 WebSocket `ping/pong` 联动，30s 无响应标记为离开。

4. **协作文本编辑**
   - 入口：仓库文件右键「协作编辑」或访问 `/:username/:repo/collab/:path*`。
   - 编辑器：基于 OT/CRDT 的文本编辑器，支持语法高亮与行号。
   - 协作者光标：不同用户显示不同颜色光标与选区。
   - 版本冲突提示：当后端检测到冲突时给出合并/覆盖选择。
   - 保存策略：自动保存草稿，显式提交生成 Git commit（可选）。

5. **业务事件广播**
   - 事件 Feed：仓库详情页右侧或顶部展示最近仓库事件（push、PR、Issue、Release、member）。
   - Toast 提示：收到与自己相关的 PR/Issue/Review 变更时弹出提示。
   - 点击跳转：事件项可跳转至对应 PR/Issue/Commit 详情。

---

## 7. 实时协作需求（WebSocket）

### 7.1 通用连接

- 建立 `ws://host/ws?token=<jwt>` 连接。
- 接收 `connected` 消息，保存 `connection_id`。
- 定时发送 `ping`，处理 `pong` 保活（建议 30s）。
- 断线后指数退避重连，最大重试次数限制。

### 7.2 通知通道

- 连接 `ws://host/ws/notifications?token=<jwt>`。
- 自动订阅用户通知频道。
- 收到 `notification` 消息后更新通知 Store 并显示 Toast。

### 7.3 仓库实时事件

- 在仓库详情页连接 `ws://host/ws/repository/{id}?token=<jwt>`。
- 自动订阅当前仓库频道。
- 接收 `push` / `pull_request` / `issues` / `release` / `member` 事件。
- 事件触发页面局部刷新或 Toast 提示，并写入右侧事件 Feed。

### 7.4 团队聊天与在线状态通道

- 在仓库聊天页/抽屉连接 `ws://host/ws/repository/{id}/chat?token=<jwt>`。
- 加入指定频道后接收 `chat_message` / `user_joined` / `user_left` / `typing` 消息。
- 在线状态通过 `ws://host/ws/presence?token=<jwt>` 接收 `presence` 消息更新，心跳间隔 30s。
- @提及消息触发本地通知 Toast 并增加未读计数。

### 7.5 协作文本编辑通道

- 在协作文本编辑页连接 `ws://host/ws/collab/{session_id}?token=<jwt>`。
- 发送/接收 `operation` / `cursor` / `awareness` 消息。
- 断线后重连并请求最新操作历史以恢复状态。

---

## 8. 规划中功能预留

| 阶段 | 功能 | 客户端预留点 |
|------|------|-------------|
| Phase 0 | OAuth2 登录与账号绑定 | 登录页第三方按钮、`/oauth/callback`、 `/settings/accounts` 账号绑定/解绑 |
| Phase 2 | 实时聊天与频道管理 | 仓库详情页右侧聊天抽屉、`/:username/:repo/chat`、频道管理页、消息 Store |
| Phase 2 | 在线状态 | 仓库成员头像在线指示器、在线成员列表面板 |
| Phase 2 | 协作文本编辑 | `/:username/:repo/collab/:path*` 独立编辑器页面 |
| Phase 2 | 业务事件广播 | 仓库事件 Feed、Toast 提示 |
| Phase 3 | CI/CD 构建状态 | PR / Commit 状态检查徽章、构建日志链接 |
| Phase 3 | 代码搜索 | 仓库内搜索框、搜索结果页、高亮匹配行 |
| Phase 3 | Git LFS | 大文件下载提示、LFS 指针文件友好展示 |
| Phase 3 | 国际化 | i18n 框架、语言切换、API 错误码映射 |

---

## 9. UI/UX 设计规范

### 9.1 布局

- **桌面端优先**: 最小设计宽度 1280px，不支持手机/平板响应式断点。
- **导航结构**: 顶部全局导航 + 左侧仓库菜单 + 右侧内容区。
- **内容区**: 最大宽度 1280px，居中或左对齐（代码查看可适当放宽）。

### 9.2 组件风格

- **组件库**: 推荐 Ant Design 5.x，图标使用 @ant-design/icons。
- **信息展示**: 优先使用**徽章（Badge / Tag）**展示状态、角色、语言、优先级等信息，提升视觉层次感。
- **状态颜色**:
  - Open: 绿色
  - Merged: 紫色
  - Closed: 红色
  - Draft: 灰色
  - Approved: 绿色
  - Changes Requested: 橙色
- **过渡动画**: 页面加载、数据提交使用**ASCII 进度条动画**或骨架屏，避免突兀的按钮闪烁。

### 9.3 交互细节

- **按钮加载态**: 提交操作显示加载动画，防止重复提交。
- **错误反馈**: 统一错误提示，403/404/500 页面按角色展示不同信息。
- **空状态**: 列表为空时提供创建入口或友好插画。
- **确认弹窗**: 删除仓库、移除成员、合并 PR、关闭应用等高风险操作二次确认。
- **代码查看**: 行号固定、支持复制、锚点分享。

### 9.4 主题

- 默认亮色主题，后续可扩展暗色模式（配置项预留）。

---

## 10. 非功能性需求

| 类别 | 需求 |
|------|------|
| 性能 | 首屏加载 < 2s；路由懒加载；大文件按需分页；Diff 大数据虚拟滚动 |
| 安全 | Token 不泄露；敏感表单 HTTPS；XSS 防护；CSRF 防护（由后端 CORS + Cookie 策略保障） |
| 可访问性 | 表单标签、键盘导航、焦点管理基础支持 |
| 兼容性 | 支持 Chrome / Edge / Firefox / Safari 最新两个主版本 |
| 错误处理 | 全局错误边界；API 错误统一拦截；前端错误上报 `/api/v1/errors/report` |
| 测试 | 单元测试（Vitest）、组件测试、E2E 测试（Playwright） |

---

## 11. 关键接口依赖清单

| 模块 | 依赖 API |
|------|---------|
| 认证 | `POST /api/v1/auth/login`, `POST /api/v1/auth/refresh` |
| OAuth 账号 | `GET /api/v1/users/me/oauth`, `POST /api/v1/users/me/oauth`, `DELETE /api/v1/users/me/oauth/{provider}` |
| 用户 | `GET /api/v1/users/me`, `PUT /api/v1/users/{id}` |
| SSH Key | `GET /api/v1/keys`, `POST /api/v1/keys`, `DELETE /api/v1/keys/{id}` |
| 仓库 | `GET/POST /api/v1/repositories`, `GET /api/v1/repositories/public` |
| Fork | `POST /api/v1/repositories/{id}/forks`, `POST /api/v1/repositories/{id}/forks/sync` |
| 成员 | `GET/POST/PUT/DELETE /api/v1/repositories/{id}/members` |
| 文件树 | `GET /api/v1/repositories/{id}/tree`, `GET .../blob`, `GET .../readme` |
| 提交 | `GET /api/v1/repositories/{id}/commits`, `GET .../commits/{hash}` |
| Diff | `GET /api/v1/repositories/{id}/diff` |
| 分支 | `GET /api/v1/repositories/{id}/branches`, `PUT .../protect` |
| PR | `GET/POST /api/v1/repositories/{id}/pull-requests`, `POST .../{n}/merge`, `POST .../{n}/reviews` |
| Issue | `GET/POST /api/v1/repositories/{id}/issues`, `POST .../batch/close` |
| 标签 | `GET/POST/PATCH/DELETE /api/v1/repositories/{id}/labels` |
| Release | `GET/POST/PATCH/DELETE /api/v1/repositories/{id}/releases` |
| Webhook | `GET/POST/PATCH/DELETE /api/v1/repositories/{id}/webhooks`, `POST .../test` |
| 通知 | `GET /api/v1/notifications`, `PATCH .../read`, `POST .../read-all` |
| 搜索 | `GET /api/v1/repositories/{id}/search` |
| 系统 | `GET /api/app/status`, `GET/POST /api/app/config`, `GET /api/app/logs` |
| 错误 | `POST /api/v1/errors/report` |
| 团队聊天 | `GET/POST /api/v1/repositories/{id}/chat/messages`, `GET /api/v1/repositories/{id}/chat/channels`, `POST/PATCH/DELETE /api/v1/repositories/{id}/chat/channels/{channel_id}` |
| 实时协作 | `WebSocket /ws/repository/{id}/chat`, `WebSocket /ws/collab/{session_id}`, `WebSocket /ws/presence` |
| WebSocket | `/ws`, `/ws/notifications`, `/ws/repository/{id}` |

---

## 12. 优先级与里程碑

### Milestone 1：基础框架与认证（1-2 周）

- 初始化 `client/web` React 19 + Vite + TypeScript + Ant Design 项目。
- 配置 ESLint、Prettier、TypeScript、axios 封装、路由守卫。
- 登录/注册页、OAuth 回调页、`/settings/accounts` 账号绑定/解绑页、全局导航、401 处理。

### Milestone 2：仓库浏览 MVP（2-3 周）

- 仓库列表、创建仓库、仓库首页、文件树、文件内容、README 渲染、提交历史。
- 分支选择器、Clone URL 展示。

### Milestone 3：PR 与 Issue（3-4 周）

- PR 列表/详情/创建/合并、Diff 视图、行内评论、Review。
- Issue 列表/详情/创建、标签管理、批量操作。

### Milestone 4：用户中心与通知（1-2 周）

- 个人资料、SSH Key、通知中心、WebSocket 通知接入。

### Milestone 5：系统管理与增强（2-3 周）

- 管理员 Dashboard、系统状态、日志、配置管理。
- Release、Webhook、搜索、LFS 等高级功能逐步补齐。

### Milestone 6：实时协作与国际化（Phase 2/3）

- 仓库聊天与频道管理、在线状态、协作文本编辑、业务事件广播、CI/CD 状态展示、国际化。

---

## 13. 待确认事项

1. UI 组件库最终选型：React 技术栈下首选 **Ant Design**，备选 **Arco Design** / **shadcn/ui**，需确认。
2. 是否保留 `client/web/` 目录结构，或采用 monorepo 其他组织方式。
3. 暗色模式是否在本次设计范围内。
4. 移动端是否需要最低限度的可读性适配（仅放大/滚动，不做响应式重构）。

---

## 14. 附录：参考文档

- [后端 API 总览](../api/README.md)
- [HTTP API 详细文档](../api/http/README.md)
- [WebSocket API 文档](../api/websocket/README.md)
- [产品路线图](../roadmap.md)
- [API 路线图](../api/roadmap.md)
- [通知系统设计](../superpowers/specs/2026-06-22-notification-system-design.md)
- [代码搜索设计](../superpowers/specs/2026-06-22-code-search-design.md)
- [Git LFS 设计](../superpowers/specs/2026-06-22-git-lfs-design.md)
