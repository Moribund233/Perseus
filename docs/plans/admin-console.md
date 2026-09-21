# Admin 控制台开发规划

> 更新日期：2026-09-20
> 范围：应用管理层（admin/app）端点的前端控制台实现规划。
> 原型：`client/prototype/admin-console.html`（总控台）、`client/prototype/admin-components.html`（组件健康）。

> **2026-09-20（控制台顶栏 + 权限面板 + 调试开关）**：按原型补齐——新增 `AdminHeader`（品牌 logo/名称 + `// 应用控制台` + 运行状态 pulse + DEBUG/RELEASE chip + 版本 + API 端点 + 时钟 + 当前用户）；`AdminConsolePage` 改为「顶栏 + `.ac-shell`（左栏 + 主舞台）」列布局；左栏底部新增**权限面板** `PermissionPanel`：`is_admin` 只读展示，`app.debug` 可切换。新增后端 `POST /api/app/debug`（**仅管理员**）：以原始 TOML dict 读改写**仅** `app.debug`、保留文件其余键、不刷新运行态 → **重启服务后生效**（规避 `_write_config_file` 的部分写入缺陷）。前端切换后显示「已写入配置，重启服务后生效」。验证：后端 `test` 容器 1283 passed；前端 `pnpm lint` + `pnpm build` + `pnpm test`（41 用例）✅。

> **2026-09-20（日志查看器重构 + 日志流收紧 + 分片接续）**：① 日志查看器拆为**两个 tab**——「文件日志」（`/api/app/logs/content`，日期/文件/行数 + 服务端级别过滤，历史检索）与「实时日志流」（`/ws/logs`，级别/logger/关键字过滤 + 历史回填 + 实时推送 + 跟随）；`follow` 语义收归流 tab，`LogsSection` 降为 Tabs 容器，新增 `FileLogTab`/`StreamLogTab`、`api/logSocket.ts`、`components/admin/VirtualLogBody.tsx`（由 `lines` 泛化为 `rows`）。② `/ws/logs` 收紧为**仅管理员**（`authenticate_websocket` 必填 + `is_admin` 校验），并修补通用 `/ws/` 端点匿名 `subscribe_logs` 的旁路（`log_handler` 处理器层兜底校验 `metadata.is_admin`）。③ 文件端点**跨分片拼接**：`get_log_content` 将 `X.log` 与 `X.log.1..N` 按时间顺序拼为逻辑流，返回 `window_parts`/`segment_starts`/`truncated`；`get_log_info` 按基名聚合分片（`parts`/`total_size`/`truncated`）；级别过滤由子串匹配改为 ` - LEVEL - ` 边界匹配。前端按 `segment_starts` 插入分片分隔行、`truncated` 显示丢弃提示、文件项显示分片数/合计大小。后端 `test` 容器 1278 passed；前端 `pnpm lint` + `pnpm build` + `pnpm test`（40 用例）✅。

> **2026-09-20（文档修正 + 端点覆盖审计）**：修正与实现不符处——§5.1 `/admin` 已是**顶层路由**（不在 `ProtectedRoute`/`AppLayout` 内）；§3.3 日志取行上限已为 5000；§5.3 移除未落地的 `stores/admin.ts`（轮询/选择状态在各 section 内本地维护）；§5.4 更正 `getPlatformStats` 归属 `api/stats.ts`。新增 §3.7 覆盖对照：控制台强相关的 admin/app 与 debug 端点**全部已在前端落地**，无遗漏。

> **2026-09-20（独立入口 + 门禁）**：`/admin` 提升为**顶层路由**，不再挂在 `ProtectedRoute`/`AppLayout` 下——未认证访问不再回落到 landing，控制台也不再套主应用外壳（全屏 `.admin-console`）。新增进入前**来源预检**：`AdminRoute` 先探测 `GET /api/app/status`，`403`→「此终端未授权」拒绝页（网关 `PERSEUS_ADMIN_ALLOWED_SOURCES` 白名单），`401`→独立登录门禁 `AdminGate`（`app.admin.gate.*`），放行后已登录非管理员→「无管理员权限」拒绝页（`app.admin.denied.*`）。新增 `components/admin/{AdminGate.tsx,AdminDenied.tsx,gate.ts}` 与 `gate.test.ts`（预检归类单测）；i18n zh/en 各 731 键对齐。同时修复网关镜像构建的**同源**问题：`docker/gateway/Dockerfile` 构建时置 `VITE_API_URL=`（空=走网关同源，避免产物指向 `127.0.0.1:8002` 造成跨域）。验证：`pnpm lint` + `pnpm build` + `pnpm test`（23 用例）✅。

> **2026-09-20（四项待决落地）**：① `/api/app/status` 收紧为登录可见（匿名 401，`/health` 仍公开）；② 引入 vitest（`pnpm test`，19 用例覆盖 `api/client.ts` 错误映射/401 刷新重试 + `api/admin.ts` 请求构造）；③ 日志查看器接入 `@tanstack/react-virtual` 虚拟滚动（动态测量、兼容折行），后端取行上限 1000→5000；④ 组件健康历史维持前端本地 14 次，不后端持久化。后端验证：`test` 容器 181 passed；前端验证：`pnpm lint` + `pnpm build` + `pnpm test` ✅。

> **2026-09-20（F 批次打磨落地 · Admin 控制台收官）**：A–F 批次全部完成。新增 `AdminSkeleton`（ac 面板 + antd Skeleton）并在 Overview/Components/Config/Logs/Debug 首次加载时展示骨架屏；Overview 改为 status 主数据源 + platform 可选（平台统计失败时降级隐藏面板而非整页报错）；响应式补强（`ac-page-head`/`ac-op-row` 换行、`ac-env-wrap` 横向滚动、≤720px 操作按钮满宽/日志筛选换行）；无障碍键盘焦点可见（`.admin-console :focus-visible` 统一描边 + 组件行/筛选 chip 高亮）；i18n 全量复核 zh/en 各 712 键完全对齐，清理失效键 `app.admin.debug.loading`。验证：`pnpm lint` + `pnpm build` ✅。

> **2026-09-20（D/E 批次落地）**：日志查看器与运维/调试已完成——`LogsSection`（日期/文件/行数/级别筛选 + 实时跟随 + 清理确认 + 级别着色终端）、`OperationsSection`（restart/shutdown 危险确认，复用 `ConfirmDangerModal`）、`DebugSection`（`/api/v1/debug/status` 账本 + PERSEUS_* 环境变量脱敏表 + admin∧debug 门控卡片 + initdb/initconf 确认）；`api/admin.ts` 新增 `logsApi`/`operationsApi`/`debugApi`，`ConfirmDangerModal` 新增 `extra` 插槽（日志清理保留天数）；`/admin/logs`、`/admin/operations`、`/admin/debug` 路由与侧栏索引全部启用；i18n `app.admin.{logs,operations,debug}.*`。仅剩 F（打磨）批次。验证：`pnpm lint` + `pnpm build` ✅。

> **2026-09-20（A/B 批次落地）**：A. 控制台骨架 + 只读概览、B. 组件健康已按第六节实施并验收——`AdminRoute`、`/admin` 壳、`OverviewSection`、`ComponentsSection`（`ComponentRow`/`StatusDot`）、`api/admin.ts`、i18n `app.admin.*`；网关侧新增 `PERSEUS_ADMIN_ALLOWED_SOURCES` 来源白名单（生产 OpenResty Lua + dev `geo`，留空=拒绝 admin API），`docker-socket-proxy`（只读）已纳入 prod/dev 编排。验证：`pnpm lint` + `pnpm build` ✅；dev 栈实测 `/api/app/status`、`/api/app/components` 200（`available:true`），prod 网关实测 `/api/app/*` 403（白名单留空 → deny-by-default）。C–F 批次（配置/日志/运维/调试/打磨）后续落地（见 D/E 注）。

> **2026-09-20（C 批次落地）**：配置管理已按第六节实施并验收——`ConfigSection` + `ConfigFieldEditor`（按类型推断 bool/int/list/enum 控件）+ `configField.ts`（可编辑节 / 受保护节 / 只读字段清单）、`ConfirmDangerModal`（危险操作确认词）、`api/admin.ts` 新增 `configApi`（get/update/validate/reset）、`/admin/config` 路由、i18n `app.admin.config.*`。受保护节渲染为只读账本，可编辑节中 `database.url`、`server.reload` 等只读字段标注「只读」。验证：`pnpm lint` + `pnpm build` ✅；dev 栈网关实测 `GET /api/app/config`、`validate`、`update`（no-op 返回重启 `hints`）、受保护节/只读字段负路径 ✅；Playwright 冒烟（经网关登录 → `/admin/config`：section 索引、只读标注、脏值计数「N 处修改」、校验横幅「配置校验通过」、reset 需输入 `RESET` 确认词方可继续）✅；只读挂载下的 reset 失败提示依赖后端错误透传（未在 dev 实测）。D–F 批次（日志/运维/调试/打磨）于 D/E 落地（见首注），仅剩 F（打磨）待办。

---

## 一、背景与目标

Perseus 后端已具备一组应用管理端点（配置、日志、运维、调试、平台统计），但 Web 前端尚无对应的管理界面。本规划：

1. 盘点现有 admin/app 端点及其就绪状态；
2. 给出前端控制台的信息架构、路由与分阶段实施计划；
3. 标注安全/权限模型与已知前置条件。

**非目标**：不在本期实现，仅做规划——本文件不产生前端代码；原型仅用于视觉/交互评审。

---

## 二、权限与安全模型

后端存在三档权限，前端需严格对齐：

| 档位 | 判定 | 可访问 |
|---|---|---|
| 公开 | 无需认证 | `/`、`/health`、`/api/v1/stats/platform` |
| 登录可见 | 任意已认证用户 | `/api/app/status`（状态/进程/请求/Git/schema；2026-09-20 由公开收紧） |
| 管理员 或 调试模式 | `current_user.is_admin` 或 `config.app.debug` | 配置读写/校验/重置、日志读取/清理、关机/重启 |
| 管理员 且 调试模式 | `is_admin && app.debug` | 调试工具：`/api/v1/debug/status`、`initdb`、`initconf` |
| 仅管理员 | `is_admin` | 编排组件状态 `/api/app/components` |

**原则**：
- 前端对无权限入口**显式置灰并说明原因**，而不是隐藏（避免用户困惑）。
- 危险操作（关机/重启/重置数据库/重置配置/清理日志）一律**二次确认 + 输入确认词**。
- `/api/app/components` 依赖只读 `docker-socket-proxy` 边车；未部署时端点返回 `available:false`，前端展示降级态而非报错。

---

## 三、后端端点清单与就绪状态

图例：✅ 后端就绪且已验证 · ⚠️ 就绪但有前置/语义注意 · ⛔ 存在缺口。

### 3.1 状态与统计（公开 / 登录可见）

| 端点 | 方法 | 权限 | 状态 | 备注 |
|---|---|---|---|---|
| `/` | GET | 公开 | ✅ | 欢迎信息（title/version/status） |
| `/health` | GET | 公开 | ✅ | 健康检查（网关/容器 healthcheck 亦用） |
| `/api/app/status` | GET | 登录可见 | ✅ | 进程/请求/Git/schema；**2026-09-20 收紧为登录可见**（`Depends(get_current_user)`，匿名 401），直连后端亦不可匿名读取；生产出口仍叠加网关 `PERSEUS_ADMIN_ALLOWED_SOURCES` 来源白名单（空=拒绝），白名单实现见 `docker/gateway/nginx.conf`（Lua）与 `docker/dev/nginx.dev.conf`（geo） |
| `/api/v1/stats/platform` | GET | 公开 | ✅ | 仓库/提交/用户数 + 运行时长 |

### 3.2 配置管理（admin 或 debug）

| 端点 | 方法 | 状态 | 备注 |
|---|---|---|---|
| `/api/app/config` | GET | ✅ | 支持 `?section=`；返回全量或单节 |
| `/api/app/config` | POST | ✅ | 仅允许 `server/gunicorn/proxy/cors/database`；受保护节 `storage/security/app/logging/system` 拒绝；返回重启提示 `hints` |
| `/api/app/config/validate` | POST | ✅ | 校验通过/失败均 200，看 `success` + `errors` |
| `/api/app/config/reset` | POST | ✅ | 恢复 `config.example.toml` 默认值；只读挂载下返回 `success:false`（不崩） |
| `/api/app/debug` | POST | ✅ | **仅管理员**；`{enabled}` 切换 `app.debug`，写 config.toml（保留其余键），重启服务后生效 |

### 3.3 日志（admin 或 debug）

| 端点 | 方法 | 状态 | 备注 |
|---|---|---|---|
| `/api/app/logs` | GET | ✅ | 日志目录、今日文件、可选日期；`today_files` 按基名聚合分片（`parts`/`total_size`/`truncated`） |
| `/api/app/logs/content` | GET | ✅ | `date/log_name/lines(1-5000)/level` 过滤，从末尾取；**跨 `X.log.1..N` 分片拼接为逻辑流**，返回 `window_parts`/`segment_starts`/`truncated`；级别按 ` - LEVEL - ` 边界匹配 |
| `/api/app/logs/cleanup` | POST | ✅ | `keep_days` 保留天数；实际删除日期目录 |
| `/ws/logs` | WS | ✅ | 实时日志流；**仅管理员**（非管理员/匿名 1008 拒绝）；`subscribe_logs` 支持 `levels/loggers/keywords` + `history_count`，通用 `/ws/` 上的同类型消息亦受处理器层管理员校验 |

### 3.4 运维操作（admin 或 debug）

| 端点 | 方法 | 状态 | 备注 |
|---|---|---|---|
| `/api/app/restart` | POST | ✅（已修复） | 已修 `sys.orig_argv` 重建启动命令 + 延迟拉起；Docker 下由 `restart: unless-stopped` 拉起 |
| `/api/app/shutdown` | POST | ⚠️ | 触发进程退出；`restart: unless-stopped` 策略会自动拉起（表现为"停不掉"），真正停机需 `docker stop`/改策略 |

### 3.5 调试工具（admin 且 debug）

| 端点 | 方法 | 状态 | 备注 |
|---|---|---|---|
| `/api/v1/debug/status` | GET | ✅ | debug 状态、配置路径、脱敏 DB URL、`PERSEUS_*` 环境变量、压力测试模式 |
| `/api/v1/debug/initdb` | POST | ✅ | 删除并重建全部表 + 重新引导管理员（破坏性） |
| `/api/v1/debug/initconf` | POST | ✅（已修复） | 原实现"只删不恢复"；已改为真正用模板落盘，并按 errno 处理只读挂载 |

### 3.6 编排组件状态（仅管理员）— 新增

| 端点 | 方法 | 状态 | 备注 |
|---|---|---|---|
| `/api/app/components` | GET | ✅ | 经只读 `docker-socket-proxy` 查询 compose 各容器状态；`available:false` 优雅降级 |

响应字段：`service, name, label, state, health, running, image, started_at, uptime_seconds, restart_count, exit_code, status_text` + `summary`。

**部署前置**：`docker-compose.yml` 中的 `docker-socket-proxy` 服务（`CONTAINERS=1`/`POST=0`）与 app 的 `PERSEUS_DOCKER_HOST`；dev overlay 需单独补。

### 3.7 前端控制台覆盖对照（2026-09-20 审计）

| 端点 | 前端封装 | 消费方 |
|---|---|---|
| `GET /api/app/status` | `adminApi.getStatus`（`api/admin.ts`） | `AdminRoute` 预检、`OverviewSection`、`DebugSection` |
| `GET /api/v1/stats/platform` | `statsApi.getPlatformStats`（`api/stats.ts`） | `OverviewSection`、landing |
| `GET/POST /api/app/config`、`/config/validate`、`/config/reset` | `configApi.*` | `ConfigSection` |
| `POST /api/app/debug` | `adminApi.setDebugMode` | `PermissionPanel`（左栏） |
| `GET /api/app/logs`、`/logs/content`、`POST /logs/cleanup` | `logsApi.*` | `FileLogTab`、`OverviewSection`（最近日志） |
| `WS /ws/logs`（`subscribe_logs`/`log`/`log_history`） | `logSocket`（`api/logSocket.ts`） | `StreamLogTab` |
| `POST /api/app/restart`、`/shutdown` | `operationsApi.*` | `OperationsSection` |
| `GET /api/v1/debug/status`、`POST /debug/initdb`、`/debug/initconf` | `debugApi.*` | `DebugSection` |
| `GET /api/app/components` | `adminApi.getComponents` | `ComponentsSection` |

非控制台端点（不纳入）：`GET /`、`GET /health`——公开探活，供网关/容器 healthcheck 使用。另有若干**仅管理员**但属业务域（非应用运维）的端点，明确不在本控制台范围：`POST /api/v1/users/{id}/password`、`PUT /api/v1/users/{id}`（`user_controller.py`）、`DELETE /api/v1/rooms/{id}`（`room_controller.py`）——它们服务于主应用的用户/聊天管理，而非 app/debug 运维。

**结论**：所有与控制台强相关的 admin/app 与 debug 端点均已在前端落地，无遗漏；旧架构（桌面应用直管服务部署）遗留的部署控制已由 §3.4 运维 + §3.6 组件端点覆盖，现由 Docker 编排承担。

---

## 四、已知缺口与待决问题

| 项 | 说明 | 建议 | 决策（2026-09-20） |
|---|---|---|---|
| `/api/app/status` 公开 | 暴露 pid/内存/线程/连接数 | 评估收紧为登录可见；或保留但前端不展示敏感字段 | ✅ **收紧为登录可见**：后端加 `Depends(get_current_user)`（匿名 401），`/health` 仍公开探活；前端仅 admin 已登录场景调用，无影响 |
| shutdown 语义 | `unless-stopped` 下自动拉起 | UI 文案明确"重启/停止将触发编排重启"；真正停机引导到运维脚本 | — |
| config 只读节/字段 | ~~受保护节、`database.url`、`server.reload` 不可改~~ | ✅ 已落地（C）：受保护节只读账本；可编辑节内只读字段标注「只读」并禁用编辑 | ✅ C 批次已落地 |
| logs 无分页 | 仅按行数取末尾 | 大日志场景用虚拟滚动 + 级别过滤 | ✅ **已落地**：`@tanstack/react-virtual` 虚拟滚动（动态测量行高、兼容折行），后端取行上限 1000→5000，前端行数档位加 2000/5000 |
| 组件健康无历史 | 端点只给当前快照 | 前端本地维护最近 N 次检查做迷你历史条；如需持久化另开需求 | ✅ **维持前端本地**（14 次），不后端持久化 |
| debug 工具环境变量脱敏 | 敏感值 `***masked***` | 前端原样展示，不缓存 | — |
| 前端无单测框架 | 仅 `eslint` + `tsc -b` + 手动 | 本期靠类型/lint；后续可引入 vitest 覆盖 api 封装 | ✅ **引入 vitest**：覆盖 `api/client.ts` 错误映射/401 刷新重试 + `api/admin.ts` 请求构造（19 用例） |

---

## 五、前端信息架构与实现规划

### 5.1 路由与守卫

- `/admin` 为**顶层路由**（`App.tsx`，不挂 `ProtectedRoute`/`AppLayout`），下辖嵌套子路由：`/admin`（index=Overview）、`/admin/components`、`/admin/config`、`/admin/logs`、`/admin/operations`、`/admin/debug`。
- 守卫 `AdminRoute`：进入前先探测 `GET /api/app/status`——`403`→来源拒绝页（网关白名单）、`401`→`AdminGate` 独立登录门禁；放行后 `user.is_admin !== true`→`AdminDenied` 拒绝页（非重定向）。
- 主应用侧边栏（`AppLayout`）**不设** admin 入口：主应用面向普通用户，控制台仅经 `/admin` 独立入口访问。
- 调试 section 额外要求 `debug_mode`（来自 `/api/app/status` 的 `debug_mode`）：非 debug 时渲染置灰门控卡片，不请求 403 端点。

### 5.2 布局与 section

采用「左侧系统索引 + 全宽带状账本」的运维控制台布局（见原型），六个 section：

| section | 数据来源 | 核心交互 |
|---|---|---|
| 概览 `overview` | `/api/app/status`、`/api/v1/stats/platform` | 生命体征、进程账本、请求/Git 队列、平台统计；5s 轮询 |
| 组件 `components` | `/api/app/components` | 分组拓扑、状态/健康/运行时长/重启、异常过滤、详情面板；10s 轮询；`available:false` 降级 |
| 配置 `config` | `/api/app/config` | 分节表单、只读节、脏值计数、`validate`、`reset`、重启提示 |
| 日志 `logs` | `/api/app/logs*`、`WS /ws/logs` | **两个 tab**：文件日志（日期/文件/行数/级别、跨分片拼接与分隔、清理）与实时日志流（级别/logger/关键字、历史回填、实时推送、跟随） |
| 运维 `operations` | `/api/app/restart`、`/shutdown` | 二次确认 + 输入确认词 |
| 调试 `debug` | `/api/v1/debug/*` | 状态、环境变量、`initdb`/`initconf`（危险确认） |

### 5.3 目录与文件规划（web）

```
client/web/src/
  routes/admin/index.tsx            # 控制台壳（左侧索引 + <Outlet/> 切换，六个 section 全启用）
  routes/admin/sections/
    OverviewSection.tsx             # 状态 + 平台统计 + 趋势图 + 最近日志
    ComponentsSection.tsx
    ConfigSection.tsx
    LogsSection.tsx                 # 日志 Tabs 容器（文件日志 / 实时日志流）+ 清理
    FileLogTab.tsx                  # 文件日志：日期/文件/行数/级别 + 分片分隔
    StreamLogTab.tsx                # 实时日志流：/ws/logs 订阅 + 级别/logger/关键字
    OperationsSection.tsx
    DebugSection.tsx
  components/admin/
    AdminRoute.tsx                  # 来源预检 + 管理员守卫
    AdminHeader.tsx                 # 控制台顶栏（品牌/状态/端点/时钟/用户）
    PermissionPanel.tsx             # 权限面板（is_admin 只读 + app.debug 切换）
    AdminGate.tsx / AdminDenied.tsx # 独立登录门禁 / 拒绝页
    gate.ts                         # 预检归类（403/401/网络）
    AdminSkeleton.tsx               # 首屏骨架屏
    ComponentRow.tsx                # 组件行 + 迷你历史
    StatusDot.tsx / HealthChip.tsx / health.ts
    ConfirmDangerModal.tsx          # 输入确认词的危险操作弹窗
    KeyValueLedger.tsx
    ConfigFieldEditor.tsx           # 配置字段编辑器（类型推断：bool/int/list/enum）
    configField.ts                  # 可编辑节 / 受保护节 / 只读字段 / 控件类型映射
    VirtualLogBody.tsx              # 虚拟滚动日志正文（rows，含分片分隔行）
    metricsHistory.ts / logLine.ts  # 指标滚动缓冲 / 日志行解析 + 分片行构造
    admin.css
  api/admin.ts                      # 端点封装（类型化）
  api/logSocket.ts                  # /ws/logs 实时日志 WebSocket 客户端
  api/stats.ts                      # 平台统计（getPlatformStats）
  i18n/locales/{zh,en}.json         # app.admin.* 文案
```

### 5.4 API 客户端

- `api/admin.ts`：`adminApi`（`getStatus`/`getComponents`）、`configApi`（get/update/validate/reset）、`logsApi`（getInfo/getContent/cleanup）、`operationsApi`（restart/shutdown）、`debugApi`（getStatus/initDb/initConf）。
- `api/logSocket.ts`：`logSocket`（`/ws/logs` 订阅；`buildSubscribePayload`/`parseLogMessage`/`formatStreamLine` 纯函数，含重连与心跳）。
- `api/stats.ts`：`statsApi.getPlatformStats`（`/api/v1/stats/platform`，landing 亦复用）。

> 现状：全部封装已落地（A/B 基础、C `configApi`、D/E `logsApi`/`operationsApi`/`debugApi`、日志流 `logSocket`）。

约定：
- 复用 `api/client.ts` 的 `apiRequest`（带 Bearer）。
- 统一错误映射：401/403 → 权限态；`available:false` → 降级态。
- 危险操作返回值 `{success, message}`，成功/失败用 `message` 提示。

### 5.5 权限/可见性门控

- 未认证：`AdminGate` 独立登录门禁（不复用主应用会话入口）。
- 已登录非管理员：`AdminDenied`「无管理员权限」拒绝页；主应用不提供 admin 入口。
- 来源被网关白名单拒绝：`AdminDenied`「此终端未授权」页（`GET /api/app/status` 返回 403）。
- admin 但非 debug：调试 section 显示「需要调试模式」门控卡片（置灰 + 说明），与原型一致。
- 组件端点 `available:false`（proxy 缺失）展示降级态；因控制台仅管理员可入，组件 403 场景仅理论存在。

---

## 六、分阶段实施计划

| 批次 | 内容 | 依赖 | 验收 |
|---|---|---|---|
| **A. 控制台骨架 + 只读概览** ✅（2026-09-20） | `AdminRoute`、`/admin` 壳、`OverviewSection`（status+platform）、`api/admin.ts` 基础、i18n 骨架 | 无 | 管理员可进入；非管理员被挡；概览数据真实、5s 刷新 |
| **B. 组件健康** ✅（2026-09-20） | `ComponentsSection` + `ComponentRow`/`StatusDot`、10s 轮询、异常过滤、降级态 | 部署 `docker-socket-proxy` | 组件状态/健康/重启真实；proxy 停掉显示降级而非报错 |
| **C. 配置管理** ✅（2026-09-20） | `ConfigSection`：分节表单、只读节、脏值、validate、reset、重启提示 | 无 | 受保护节不可改；校验/重置正确；只读挂载提示 |
| **D. 日志查看器** ✅（2026-09-20） | `LogsSection` 双 tab：`FileLogTab`（日期/文件/行数/级别、**跨分片拼接 + 分片分隔 + 丢弃提示**、清理）与 `StreamLogTab`（`/ws/logs` 实时流，级别/logger/关键字、历史回填、跟随）；**虚拟滚动**（`@tanstack/react-virtual`，取行上限 5000） | 无 | 过滤正确；清理需确认；大日志不卡顿；分片接续可见 |
| **E. 运维 + 调试** ✅（2026-09-20） | `OperationsSection`、`DebugSection`（危险操作复用 C 批次 `ConfirmDangerModal`） | C（弹窗） | 危险操作需输入确认词；debug 门控正确 |
| **F. 打磨** ✅（2026-09-20） | 骨架屏、空/错/降级态、响应式、i18n 全量、lint/类型 | A–E | `pnpm lint` + `pnpm build` 通过；无障碍焦点可见 |

---

## 七、测试与验收

**后端**（已在 WSL `test` 容器验证）：
- `tests/test_app_admin_api.py`：门控负路径、配置重置/更新提示、关机/重启、日志清理、debug initdb/initconf、组件端点；`/ws/logs` 与通用 `/ws/` 的日志流管理员门控（匿名/非管理员拒绝、管理员可订阅）。
- `tests/test_orchestration_service.py`：MockTransport 模拟 Docker API（正常/不可用/项目探测/前缀回退）。
- `tests/test_app_service.py`：重启命令构建、日志清理删除；日志分片拼接（跨段顺序、窗口偏移、级别边界、`truncated`、`get_log_info` 分片聚合）。
- `tests/api/test_api_contract.py`：admin/debug 路由契约。

**前端**（已引入 vitest，见下）：
- `pnpm lint`、`pnpm build`（`tsc -b && vite build`）、`pnpm test`（`vitest run`）。
- 手动验收矩阵：管理员/非管理员 × debug 开/关 × proxy 可用/不可用。
- ✅ `src/api/client.test.ts`：错误映射（`detail`/`error.message`/纯文本）、204、请求头、401 刷新重试与认证端点豁免；`src/api/admin.test.ts`：各 api 封装的路径/方法/查询串构造；`src/api/logSocket.test.ts`：订阅载荷构造与 `log` 消息解析；`src/components/admin/logLine.test.ts`：分片分隔行构造。

---

## 八、原型引用

| 原型 | 说明 |
|---|---|
| `client/prototype/admin-console.html` | 总控台：状态概览 / 配置管理 / 日志查看器 / 运维操作 / 调试工具；含权限模拟器与危险操作确认弹窗 |
| `client/prototype/admin-components.html` | 组件健康单页：分组拓扑、健康历史条、详情面板；含「模拟异常」「模拟不可用」降级态 |

原型为独立静态 HTML（内联 CSS/JS + 模拟数据），仅用于视觉与交互评审，不接后端。
