# LanGit 项目文档

> 本文档目录包含 LanGit 项目的所有开发文档、API 文档和测试报告

---

## 📁 目录结构

```
docs/
├── README.md                    # 本文档（文档导航）
├── P1_TEST_REPORT.md           # P1 阶段测试报告
├── api_v1/                      # API v1 相关文档
│   ├── ROADMAP.md              # API v1 开发规划路线图
│   ├── README.md               # API v1 接口文档首页
│   ├── frontend-sdk.md         # 前端 SDK 指南
│   ├── git_http.md             # Git HTTP API 文档
│   ├── users.md                # 用户管理 API
│   ├── repositories.md         # 仓库管理 API
│   ├── repository_members.md   # 仓库成员 API
│   ├── repository_browser.md   # 代码浏览 API
│   ├── branches.md             # 分支管理 API
│   ├── commits.md              # 提交管理 API
│   ├── pull_requests.md        # 合并请求 API
│   └── issues.md               # 问题跟踪 API
├── api_v2/                      # API v2 相关文档
│   └── ROADMAP.md              # API v2 开发规划路线图
└── shared/                      # 共享文档（按版本分类）
    └── api_v1/                 # API v1 测试与审查报告
        ├── SECURITY_TEST_REPORT.md     # 安全测试报告
        ├── code_review_report.md       # 代码审查报告
        └── server_code_review_report.md # 服务端代码审查报告
```

---

## 🚀 快速导航

### 开发规划
- [API v1 开发规划](./api_v1/ROADMAP.md) - 基础功能开发历程（已完成）
- [API v2 开发规划](./api_v2/ROADMAP.md) - 实时功能扩展规划（进行中）

### API 文档
- [API v1 接口文档](./api_v1/README.md) - 完整的 REST API 文档
- [前端 SDK 指南](./api_v1/frontend-sdk.md) - TypeScript 类型和 Vue 3 示例

### 测试与质量
- [P1 测试报告](./P1_TEST_REPORT.md) - P1 阶段详细测试报告
- [安全测试报告](./shared/api_v1/SECURITY_TEST_REPORT.md) - 安全测试详细报告
- [代码审查报告](./shared/api_v1/code_review_report.md) - 代码质量审查报告

---

## 📊 项目状态

| 版本 | 状态 | 说明 |
|-----|------|------|
| API v1 | ✅ 已完成 | 基础功能完整，可用于生产环境 |
| API v2 | 🟡 规划中 | 扩展 WebSocket 实时功能和 Webhook 系统 |

---

## 📝 文档更新记录

| 日期 | 更新内容 |
|-----|---------|
| 2026-02-10 | 整理文档目录结构，区分 API v1 和 API v2 |
| 2026-02-10 | 创建 API v2 开发规划，加入 Webhook 系统 |
| 2026-02-10 | 补充 P0/P1 阶段测试报告到 API v1 文档 |
| 2026-02-09 | 完成 P2 阶段开发，安全测试 100% 通过 |

---

**提示**: 如需查找特定文档，请参考上方目录结构或使用 IDE 的文件搜索功能。
