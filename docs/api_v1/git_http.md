# Git HTTP API

> 本文档描述 Git Smart HTTP 协议端点，用于命令行 git 操作（clone/push/pull）。
> 
> **注意**：这些端点主要用于 Git 命令行客户端，不是给前端 Web 应用直接调用的 REST API。

## 基础 URL

```
http://localhost:8000/git/{username}/{repo-name}
```

**注意**：URL 不需要 `.git` 后缀。例如：`http://localhost:8000/git/johndoe/my-project`

## 支持的 Git 操作

| 操作 | 命令 | 所需权限 | 说明 |
|------|------|----------|------|
| Clone | `git clone` | 读取权限 | 克隆仓库到本地 |
| Pull | `git pull` | 读取权限 | 拉取远程更新 |
| Fetch | `git fetch` | 读取权限 | 获取远程分支 |
| Push | `git push` | 写入权限 | 推送本地提交 |

---

## 认证方式

Git HTTP API 支持以下认证方式：

### 1. HTTP Basic Auth（推荐）

在 URL 中嵌入用户名密码：

```bash
git clone http://username:password@localhost:8000/git/username/repo-name
```

或在命令行提示时输入：

```bash
git clone http://localhost:8000/git/username/repo-name
# 提示输入用户名和密码
```

### 2. 使用 Git Credential Helper

配置 Git 凭证助手避免重复输入：

```bash
# 缓存凭证（默认15分钟）
git config --global credential.helper cache

# 永久存储凭证（使用系统密钥库）
git config --global credential.helper store
```

---

## 使用示例

### 克隆仓库

**公开仓库**
```bash
git clone http://localhost:8000/git/johndoe/my-project
cd my-project
```

**私有仓库**
```bash
# 方式1：URL 中携带凭证
git clone http://johndoe:mypassword@localhost:8000/git/johndoe/private-project

# 方式2：交互式输入
git clone http://localhost:8000/git/johndoe/private-project
# Username: johndoe
# Password: ********
```

### 拉取更新

```bash
cd my-project
git pull origin main
```

### 推送提交

```bash
# 添加并提交更改
git add .
git commit -m "Update feature"

# 推送到远程
git push origin main
```

### 推送新分支

```bash
git checkout -b feature/new-feature
git push -u origin feature/new-feature
```

---

## 权限要求

| 操作 | 公开仓库 | 私有仓库 | 受保护分支 |
|------|----------|----------|------------|
| Clone/Fetch/Pull | ✅ 无需认证 | 🔐 需要读取权限 | - |
| Push | ✅ 无需认证 | 🔐 需要写入权限 | 🛡️ 需要管理员权限 |

### 受保护分支规则

以下分支默认受保护，需要特定权限才能推送：

- `main` / `master`
- `develop`

**保护规则**：
- 禁止强制推送 (`git push --force`)
- 可能需要代码审查
- 可能需要通过 CI 检查

---

## 技术端点

> 以下端点由 Git 客户端内部使用，**不需要手动调用**。

### 引用发现
```
GET /git/{repo_path}/info/refs?service=git-upload-pack
GET /git/{repo_path}/info/refs?service=git-receive-pack
```

### 上传包（Pull/Fetch）
```
POST /git/{repo_path}/git-upload-pack
```

### 接收包（Push）
```
POST /git/{repo_path}/git-receive-pack
```

---

## 错误处理

### 常见错误

| 错误信息 | 原因 | 解决方案 |
|----------|------|----------|
| `Authentication required` | 私有仓库未认证 | 提供正确的用户名密码 |
| `Permission denied` | 无权限推送 | 检查仓库成员权限 |
| `Repository not found` | 仓库不存在或路径错误 | 检查仓库路径 |
| `Cannot push to protected branch` | 推送到受保护分支 | 使用 PR 流程合并 |

### HTTP 状态码

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 401 | 未认证（缺少或错误的凭证） |
| 403 | 无权限（认证成功但无权操作） |
| 404 | 仓库不存在 |
| 429 | 请求过于频繁（速率限制） |

---

## 与 REST API 的区别

| 特性 | Git HTTP API | REST API |
|------|--------------|----------|
| **用途** | Git 命令行操作 | Web 应用/前端调用 |
| **协议** | Git Smart HTTP | HTTP REST |
| **认证** | HTTP Basic Auth | Bearer Token |
| **客户端** | Git 命令行 | 浏览器/HTTP 客户端 |
| **响应格式** | Git 二进制协议 | JSON |
| **基础路径** | `/git/` | `/api/` |

---

## 相关文档

- [repository_browser.md](./repository_browser.md) - 通过 REST API 浏览代码
- [branches.md](./branches.md) - 通过 REST API 管理分支
- [commits.md](./commits.md) - 通过 REST API 查看提交
- [pull_requests.md](./pull_requests.md) - 通过 REST API 创建合并请求

---

## 注意事项

1. **大文件推送**：建议使用 Git LFS 管理大文件
2. **速率限制**：频繁的 Git 操作可能触发速率限制
3. **凭证安全**：避免在脚本中硬编码密码，使用 Git 凭证助手
4. **SSH 替代**：如需更安全的连接，可配置 SSH 访问（如支持）
