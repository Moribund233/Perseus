# Desktop Phase 1 — 骨架打通（本地优先）实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 打通 desktop 本地骨架：Go 本地网关（动态端口 + CORS 白名单 + 会话 token）、SQLite store、Wails 原生绑定、工作区（添加本地目录 / clone 单仓库）、文件树与文件读写、Monaco 编辑器、git 基础操作（status/diff/add/commit/push/pull）、IdeShell 前端布局。

**Architecture:** Wails v2 壳 + Go 本地网关（前端唯一通信入口，`127.0.0.1:0` 动态端口）。前端只与本地网关通信，经 `X-Gateway-Token` 会话校验与 Origin 白名单防护；敏感凭据走系统密钥库，Go 侧注入。Phase 1 不接入服务器注册表，clone 采用"手填 git URL + 一次性凭据"最小路径。

**Tech Stack:** Go 1.23+（本机 1.26）、Wails v2.12、React 19 + Vite 8 + TypeScript ~6（对齐 web）、antd 6、zustand 5、Monaco Editor（`@monaco-editor/react` + 本地打包）、modernc.org/sqlite（纯 Go，无 CGO）、github.com/zalando/go-keyring（Windows Credential Manager）。

## Global Constraints

- Go 模块名保持 `desktop`（不重命名，避免牵连现有 main.go/app.go）
- 网关只绑定 loopback；所有非白名单 Origin / 缺失 `X-Gateway-Token` 的请求返回 401（`GET /api/local/config` 除外）
- CORS 白名单默认仅 `http://localhost:34115` 与 `wails://localhost`，禁止 `*`
- 敏感数据（token、私钥）只进系统密钥库，SQLite store 只存引用/元数据
- 离线缓存为只读 GET 的 LRU 内存缓存（Phase 1 仅建骨架，随 Phase 2 代理一起启用）
- 前端 `api/client.ts` 拷贝自 web 但**必须移除** `Authorization: Bearer` 注入逻辑
- 目录树扫描忽略 `.git`、`node_modules`、`__pycache__`、`dist`、`.venv`、`venv`
- 文件读取 >2MB 标记 `truncated` 只读提示；写文件 UTF-8
- 模块路径：`desktop/internal/{store,gateway,fs,git}`
- 测试：Go 侧 `go test ./...`；git 模块用真实临时仓库；前端以 `npm run build`（tsc）作为类型检查 + 手工冒烟
- 每 Task 结束必须 `git commit`；commit message 前缀遵循仓库风格（`feat:`, `test:`, `refactor:`）

---

## 文件结构

```
client/desktop/
├── main.go                        # 修改：启动时装配 store/git/fs/gateway
├── app.go                         # 修改：App 原生绑定（GetGatewayConfig/对话框/密钥库）
├── go.mod                         # 修改：新增 modernc.org/sqlite、zalando/go-keyring、google/uuid
├── internal/
│   ├── store/
│   │   ├── db.go                  # SQLite：工作区/设置表 + CRUD
│   │   ├── keychain.go            # Keychain 接口 + Windows 实现（go-keyring）
│   │   └── keychain_fake.go       # 测试用内存实现（build tag 隔离或独立包）
│   ├── fs/
│   │   ├── scan.go                # 目录树扫描（忽略规则）
│   │   └── io.go                  # 读写文件、二进制识别、大小限制
│   ├── git/
│   │   ├── cli.go                 # exec 封装 + 凭据注入
│   │   ├── status.go              # status --porcelain=v2 解析
│   │   ├── diff.go                # diff 解析
│   │   ├── operations.go          # add/commit/log/branch/init
│   │   ├── clone.go               # clone（URL + 凭据）
│   │   └── remote.go              # push/pull
│   └── gateway/
│       ├── gateway.go             # 结构体、动态端口启动/停止、会话 token
│       ├── middleware.go          # CORS + X-Gateway-Token 校验
│       ├── router.go              # 路由注册（stdlib ServeMux）
│       ├── handlers_config.go     # GET /api/local/config
│       ├── handlers_workspace.go  # 工作区 CRUD + clone + git/{op}
│       ├── handlers_fs.go         # tree / file
│       └── json.go                # JSON 编解码 + 统一错误响应
└── frontend/src/
    ├── main.tsx                   # 修改：读取网关配置后渲染
    ├── App.tsx                    # 修改：Welcome / IdeShell 切换
    ├── api/client.ts              # 重写：BASE_URL=网关、X-Gateway-Token、serverId 作用域
    ├── api/workspaces.ts          # 新增：工作区/git/tree/file 客户端
    ├── stores/gateway.ts          # 新增：网关配置 + 会话 token
    ├── stores/workspace.ts        # 新增：工作区列表/当前工作区
    ├── stores/git.ts              # 新增：status/操作结果
    ├── layouts/IdeShell.tsx       # 新增：IDE 布局（活动栏/侧栏/标签页/状态栏）
    ├── views/Welcome.tsx          # 新增：打开本地目录 / clone / 最近工作区
    ├── views/workspace/ExplorerPanel.tsx   # 新增：文件树
    ├── views/workspace/EditorTabs.tsx      # 新增：Monaco 标签页 + 保存 + 只读
    ├── views/workspace/GitPanel.tsx        # 新增：变更/暂存/提交
    ├── views/Settings.tsx         # 新增：本地设置（占位 + 数据目录展示）
    └── styles/desktop.css         # 新增：IDE 布局样式
```

---

### Task 1: store 模块（SQLite：工作区 + 设置）

**Files:**
- Create: `client/desktop/internal/store/db.go`
- Create: `client/desktop/internal/store/db_test.go`
- Modify: `client/desktop/go.mod`

**Interfaces:**
- Consumes: 无（首个 Go 任务）
- Produces:
  ```go
  type Workspace struct {
      ID        string    `json:"id"`
      Name      string    `json:"name"`
      Path      string    `json:"path"`
      RemoteURL string    `json:"remote_url,omitempty"`
      ServerID  string    `json:"server_id,omitempty"`
      CreatedAt time.Time `json:"created_at"`
  }
  type Store struct { ... }
  func New(path string) (*Store, error)   // path="" → 内存库（测试）
  func (s *Store) Close() error
  func (s *Store) CreateWorkspace(ws Workspace) (Workspace, error)
  func (s *Store) ListWorkspaces() ([]Workspace, error)
  func (s *Store) GetWorkspace(id string) (Workspace, error)
  func (s *Store) DeleteWorkspace(id string) error
  func (s *Store) SetSetting(key, value string) error
  func (s *Store) GetSetting(key string) (string, error)
  ```

- [ ] **Step 1: 添加依赖**

  ```bash
  cd client/desktop
  go get modernc.org/sqlite@latest github.com/google/uuid@latest
  ```

- [ ] **Step 2: 写失败测试 `internal/store/db_test.go`**

  ```go
  package store

  import (
      "strings"
      "testing"
  )

  func TestStoreWorkspaceCRUD(t *testing.T) {
      s, err := New("")
      if err != nil {
          t.Fatalf("New: %v", err)
      }
      defer s.Close()

      ws, err := s.CreateWorkspace(Workspace{Name: "demo", Path: "C:/tmp/demo"})
      if err != nil {
          t.Fatalf("CreateWorkspace: %v", err)
      }
      if ws.ID == "" {
          t.Fatal("expected generated id")
      }
      if strings.Contains(ws.ID, "\x00") {
          t.Fatal("bad id")
      }

      got, err := s.GetWorkspace(ws.ID)
      if err != nil || got.Path != "C:/tmp/demo" {
          t.Fatalf("GetWorkspace = %+v, err %v", got, err)
      }

      list, err := s.ListWorkspaces()
      if err != nil || len(list) != 1 {
          t.Fatalf("ListWorkspaces = %+v, err %v", list, err)
      }

      if err := s.DeleteWorkspace(ws.ID); err != nil {
          t.Fatalf("DeleteWorkspace: %v", err)
      }
      if _, err := s.GetWorkspace(ws.ID); err == nil {
          t.Fatal("expected not found after delete")
      }
  }

  func TestStoreSettings(t *testing.T) {
      s, _ := New("")
      defer s.Close()
      if err := s.SetSetting("theme", "dark"); err != nil {
          t.Fatalf("SetSetting: %v", err)
      }
      v, err := s.GetSetting("theme")
      if err != nil || v != "dark" {
          t.Fatalf("GetSetting = %q, err %v", v, err)
      }
  }
  ```

- [ ] **Step 3: 运行确认失败**

  Run: `cd client/desktop && go test ./internal/store/ -v`
  Expected: FAIL（编译错误：store 包不存在）

- [ ] **Step 4: 实现 `internal/store/db.go`**

  ```go
  package store

  import (
      "database/sql"
      "time"

      "github.com/google/uuid"
      _ "modernc.org/sqlite"
  )

  type Workspace struct {
      ID        string    `json:"id"`
      Name      string    `json:"name"`
      Path      string    `json:"path"`
      RemoteURL string    `json:"remote_url,omitempty"`
      ServerID  string    `json:"server_id,omitempty"`
      CreatedAt time.Time `json:"created_at"`
  }

  type Store struct {
      db *sql.DB
  }

  func New(path string) (*Store, error) {
      if path == "" {
          path = "file::memory:?cache=shared"
      }
      db, err := sql.Open("sqlite", path)
      if err != nil {
          return nil, err
      }
      db.SetMaxOpenConns(1)
      if _, err := db.Exec(`
          CREATE TABLE IF NOT EXISTS workspaces (
              id TEXT PRIMARY KEY,
              name TEXT NOT NULL,
              path TEXT NOT NULL,
              remote_url TEXT NOT NULL DEFAULT '',
              server_id TEXT NOT NULL DEFAULT '',
              created_at TEXT NOT NULL
          );
          CREATE TABLE IF NOT EXISTS settings (
              key TEXT PRIMARY KEY,
              value TEXT NOT NULL
          );
      `); err != nil {
          db.Close()
          return nil, err
      }
      return &Store{db: db}, nil
  }

  func (s *Store) Close() error { return s.db.Close() }

  func (s *Store) CreateWorkspace(ws Workspace) (Workspace, error) {
      ws.ID = uuid.NewString()
      ws.CreatedAt = time.Now().UTC()
      _, err := s.db.Exec(
          `INSERT INTO workspaces (id, name, path, remote_url, server_id, created_at) VALUES (?,?,?,?,?,?)`,
          ws.ID, ws.Name, ws.Path, ws.RemoteURL, ws.ServerID,
          ws.CreatedAt.Format(time.RFC3339),
      )
      return ws, err
  }

  func (s *Store) ListWorkspaces() ([]Workspace, error) {
      rows, err := s.db.Query(`SELECT id, name, path, remote_url, server_id, created_at FROM workspaces ORDER BY created_at DESC`)
      if err != nil {
          return nil, err
      }
      defer rows.Close()
      var out []Workspace
      for rows.Next() {
          var ws Workspace
          var ts string
          if err := rows.Scan(&ws.ID, &ws.Name, &ws.Path, &ws.RemoteURL, &ws.ServerID, &ts); err != nil {
              return nil, err
          }
          if ws.CreatedAt, err = time.Parse(time.RFC3339, ts); err != nil {
              return nil, err
          }
          out = append(out, ws)
      }
      return out, rows.Err()
  }

  func (s *Store) GetWorkspace(id string) (Workspace, error) {
      var ws Workspace
      var ts string
      err := s.db.QueryRow(
          `SELECT id, name, path, remote_url, server_id, created_at FROM workspaces WHERE id = ?`, id,
      ).Scan(&ws.ID, &ws.Name, &ws.Path, &ws.RemoteURL, &ws.ServerID, &ts)
      if err != nil {
          return Workspace{}, err
      }
      ws.CreatedAt, err = time.Parse(time.RFC3339, ts)
      return ws, err
  }

  func (s *Store) DeleteWorkspace(id string) error {
      _, err := s.db.Exec(`DELETE FROM workspaces WHERE id = ?`, id)
      return err
  }

  func (s *Store) SetSetting(key, value string) error {
      _, err := s.db.Exec(`INSERT INTO settings (key, value) VALUES (?,?)
          ON CONFLICT(key) DO UPDATE SET value = excluded.value`, key, value)
      return err
  }

  func (s *Store) GetSetting(key string) (string, error) {
      var v string
      err := s.db.QueryRow(`SELECT value FROM settings WHERE key = ?`, key).Scan(&v)
      return v, err
  }
  ```

- [ ] **Step 5: 运行确认通过**

  Run: `cd client/desktop && go test ./internal/store/ -v`
  Expected: PASS (2 passed)

- [ ] **Step 6: Commit**

  ```bash
  git add client/desktop/go.mod client/desktop/go.sum client/desktop/internal/store/
  git commit -m "feat(desktop): add store module with SQLite workspaces and settings"
  ```

---

### Task 2: keychain 封装（Windows Credential Manager）

**Files:**
- Create: `client/desktop/internal/store/keychain.go`
- Create: `client/desktop/internal/store/keychain_test.go`

**Interfaces:**
- Consumes: 无
- Produces:
  ```go
  type Keychain interface {
      Get(service, account string) (string, error)
      Set(service, account, secret string) error
      Delete(service, account string) error
  }
  func NewKeychain() Keychain   // 生产：go-keyring 实现
  type FakeKeychain struct{ M map[string]string }
  func (f *FakeKeychain) Get(...) / Set(...) / Delete(...)  // 测试用
  ```

- [ ] **Step 1: 添加依赖**

  ```bash
  cd client/desktop
  go get github.com/zalando/go-keyring@latest
  ```

- [ ] **Step 2: 写失败测试（FakeKeychain 行为）**

  ```go
  package store

  import "testing"

  func TestFakeKeychain(t *testing.T) {
      k := &FakeKeychain{M: map[string]string{}}
      if err := k.Set("svc", "acct", "secret"); err != nil {
          t.Fatalf("Set: %v", err)
      }
      v, err := k.Get("svc", "acct")
      if err != nil || v != "secret" {
          t.Fatalf("Get = %q, err %v", v, err)
      }
      if err := k.Delete("svc", "acct"); err != nil {
          t.Fatalf("Delete: %v", err)
      }
      if _, err := k.Get("svc", "acct"); err == nil {
          t.Fatal("expected error after delete")
      }
  }
  ```

- [ ] **Step 3: 运行确认失败**

  Run: `cd client/desktop && go test ./internal/store/ -run TestFakeKeychain -v`
  Expected: FAIL（FakeKeychain 未定义）

- [ ] **Step 4: 实现 `keychain.go`**

  ```go
  package store

  import "errors"

  type Keychain interface {
      Get(service, account string) (string, error)
      Set(service, account, secret string) error
      Delete(service, account string) error
  }

  // FakeKeychain 内存实现，仅用于测试。
  type FakeKeychain struct{ M map[string]string }

  func (f *FakeKeychain) Get(service, account string) (string, error) {
      v, ok := f.M[service+"\x00"+account]
      if !ok {
          return "", errors.New("not found")
      }
      return v, nil
  }

  func (f *FakeKeychain) Set(service, account, secret string) error {
      if f.M == nil {
          f.M = map[string]string{}
      }
      f.M[service+"\x00"+account] = secret
      return nil
  }

  func (f *FakeKeychain) Delete(service, account string) error {
      delete(f.M, service+"\x00"+account)
      return nil
  }

  // NewKeychain 返回生产实现（Windows Credential Manager）。
  // 非 Windows 平台运行时返回 nil，调用方需自行处理（Phase 1 仅 Windows）。
  func NewKeychain() Keychain {
      return &windowsKeychain{}
  }
  ```

- [ ] **Step 5: 实现 Windows 实现（同文件追加）**

  ```go
  package store

  import (
      "github.com/zalando/go-keyring"
  )

  type windowsKeychain struct{}

  func (w *windowsKeychain) Get(service, account string) (string, error) {
      return keyring.Get(service, account)
  }

  func (w *windowsKeychain) Set(service, account, secret string) error {
      return keyring.Set(service, account, secret)
  }

  func (w *windowsKeychain) Delete(service, account string) error {
      return keyring.Delete(service, account)
  }
  ```

- [ ] **Step 6: 运行确认通过**

  Run: `cd client/desktop && go test ./internal/store/ -v`
  Expected: PASS (3 passed)

- [ ] **Step 7: Commit**

  ```bash
  git add client/desktop/go.mod client/desktop/go.sum client/desktop/internal/store/
  git commit -m "feat(desktop): add keychain abstraction with Windows credential manager support"
  ```

---

### Task 3: fs 模块（目录扫描 + 文件读写）

**Files:**
- Create: `client/desktop/internal/fs/scan.go`
- Create: `client/desktop/internal/fs/io.go`
- Create: `client/desktop/internal/fs/fs_test.go`

**Interfaces:**
- Consumes: 无
- Produces:
  ```go
  type FileNode struct {
      Name     string      `json:"name"`
      Path     string      `json:"path"` // 相对根目录，路径分隔符统一 /
      IsDir    bool        `json:"is_dir"`
      Children []*FileNode `json:"children,omitempty"`
  }
  var IgnoreDirs = []string{".git", "node_modules", "__pycache__", "dist", ".venv", "venv"}
  func ScanTree(root string, maxDepth int) (*FileNode, error)
  type FileContent struct {
      Content   string `json:"content"`
      Binary    bool   `json:"binary"`
      Truncated bool   `json:"truncated"`
      Size      int64  `json:"size"`
  }
  type WriteResult struct { Lines int `json:"lines"`; Bytes int `json:"bytes"` }
  func ReadFile(path string) (*FileContent, error)
  func WriteFile(path string, content string) (WriteResult, error)
  ```
  常量：`MaxReadSize = 2 << 20`（2MB）。

- [ ] **Step 1: 写失败测试 `fs_test.go`**

  ```go
  package fs

  import (
      "os"
      "path/filepath"
      "strings"
      "testing"
  )

  func TestScanTreeSkipsIgnoredDirs(t *testing.T) {
      root := t.TempDir()
      mkDir(t, filepath.Join(root, "src"))
      mkFile(t, filepath.Join(root, "a.txt"))
      mkFile(t, filepath.Join(root, "src", "main.py"))
      mkDir(t, filepath.Join(root, ".git"))
      mkFile(t, filepath.Join(root, ".git", "HEAD"))
      mkDir(t, filepath.Join(root, "node_modules"))
      mkFile(t, filepath.Join(root, "node_modules", "x.js"))
      mkDir(t, filepath.Join(root, "__pycache__"))
      mkFile(t, filepath.Join(root, "__pycache__", "y.pyc"))

      tree, err := ScanTree(root, 4)
      if err != nil {
          t.Fatalf("ScanTree: %v", err)
      }
      flat := flatten(tree)
      if strings.Contains(flat, ".git") || strings.Contains(flat, "node_modules") ||
          strings.Contains(flat, "__pycache__") {
          t.Fatalf("ignored dirs leaked: %s", flat)
      }
      if !strings.Contains(flat, "src/main.py") || !strings.Contains(flat, "a.txt") {
          t.Fatalf("expected files missing: %s", flat)
      }
  }

  func TestReadWriteFile(t *testing.T) {
      p := filepath.Join(t.TempDir(), "demo.txt")
      wr, err := WriteFile(p, "line1\nline2\n")
      if err != nil {
          t.Fatalf("WriteFile: %v", err)
      }
      if wr.Lines != 2 || wr.Bytes != 12 {
          t.Fatalf("WriteResult = %+v", wr)
      }
      fc, err := ReadFile(p)
      if err != nil {
          t.Fatalf("ReadFile: %v", err)
      }
      if fc.Content != "line1\nline2\n" || fc.Binary || fc.Truncated {
          t.Fatalf("FileContent = %+v", fc)
      }
  }

  func TestReadFileDetectsBinary(t *testing.T) {
      p := filepath.Join(t.TempDir(), "bin")
      if err := os.WriteFile(p, []byte{0x00, 0x01, 0x02}, 0o644); err != nil {
          t.Fatal(err)
      }
      fc, err := ReadFile(p)
      if err != nil {
          t.Fatalf("ReadFile: %v", err)
      }
      if !fc.Binary {
          t.Fatal("expected binary=true")
      }
  }

  func mkDir(t *testing.T, p string) {
      t.Helper()
      if err := os.MkdirAll(p, 0o755); err != nil {
          t.Fatal(err)
      }
  }

  func mkFile(t *testing.T, p string) {
      t.Helper()
      if err := os.MkdirAll(filepath.Dir(p), 0o755); err != nil {
          t.Fatal(err)
      }
      if err := os.WriteFile(p, []byte("x"), 0o644); err != nil {
          t.Fatal(err)
      }
  }

  func flatten(n *FileNode) string {
      if n == nil {
          return ""
      }
      out := n.Path
      for _, c := range n.Children {
          out += " " + flatten(c)
      }
      return out
  }
  ```

- [ ] **Step 2: 运行确认失败**

  Run: `cd client/desktop && go test ./internal/fs/ -v`
  Expected: FAIL（fs 包不存在）

- [ ] **Step 3: 实现 `scan.go`**

  ```go
  package fs

  import (
      "os"
      "path/filepath"
      "strings"
  )

  var IgnoreDirs = []string{".git", "node_modules", "__pycache__", "dist", ".venv", "venv"}

  type FileNode struct {
      Name     string      `json:"name"`
      Path     string      `json:"path"`
      IsDir    bool        `json:"is_dir"`
      Children []*FileNode `json:"children,omitempty"`
  }

  func ScanTree(root string, maxDepth int) (*FileNode, error) {
      return scan(root, root, 0, maxDepth)
  }

  func scan(root, cur string, depth, maxDepth int) (*FileNode, error) {
      entries, err := os.ReadDir(cur)
      if err != nil {
          return nil, err
      }
      rel, _ := filepath.Rel(root, cur)
      rel = filepath.ToSlash(rel)
      if rel == "." {
          rel = ""
      }
      node := &FileNode{Name: filepath.Base(cur), Path: rel, IsDir: true}
      for _, e := range entries {
          if e.IsDir() && contains(IgnoreDirs, e.Name()) {
              continue
          }
          childPath := filepath.Join(cur, e.Name())
          relChild := strings.TrimPrefix(filepath.ToSlash(childPath), filepath.ToSlash(root)+"/")
          child := &FileNode{Name: e.Name(), Path: relChild, IsDir: e.IsDir()}
          if e.IsDir() && depth < maxDepth {
              sub, err := scan(root, childPath, depth+1, maxDepth)
              if err != nil {
                  continue
              }
              child.Children = sub.Children
          }
          node.Children = append(node.Children, child)
      }
      return node, nil
  }

  func contains(list []string, s string) bool {
      for _, v := range list {
          if v == s {
              return true
          }
      }
      return false
  }
  ```

- [ ] **Step 4: 实现 `io.go`**

  ```go
  package fs

  import (
      "bytes"
      "os"
      "path/filepath"
      "strings"
  )

  const MaxReadSize = 2 << 20

  type FileContent struct {
      Content   string `json:"content"`
      Binary    bool   `json:"binary"`
      Truncated bool   `json:"truncated"`
      Size      int64  `json:"size"`
  }

  type WriteResult struct {
      Lines int `json:"lines"`
      Bytes int `json:"bytes"`
  }

  func ReadFile(path string) (*FileContent, error) {
      info, err := os.Stat(path)
      if err != nil {
          return nil, err
      }
      data, err := os.ReadFile(path)
      if err != nil {
          return nil, err
      }
      fc := &FileContent{Size: info.Size(), Truncated: info.Size() > MaxReadSize}
      fc.Binary = isBinary(data)
      if !fc.Binary {
          fc.Content = string(data)
          if fc.Truncated {
              fc.Content = truncateTo(fc.Content, MaxReadSize)
          }
      }
      return fc, nil
  }

  func WriteFile(path string, content string) (WriteResult, error) {
      if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
          return WriteResult{}, err
      }
      b := []byte(content)
      if err := os.WriteFile(path, b, 0o644); err != nil {
          return WriteResult{}, err
      }
      return WriteResult{Lines: strings.Count(content, "\n"), Bytes: len(b)}, nil
  }

  func isBinary(data []byte) bool {
      sample := data
      if len(sample) > 512 {
          sample = sample[:512]
      }
      if bytes.IndexByte(sample, 0) >= 0 {
          return true
      }
      return false
  }

  func truncateTo(s string, n int) string {
      r := []rune(s)
      if len(r) <= n {
          return s
      }
      return string(r[:n])
  }
  ```

- [ ] **Step 5: 运行确认通过**

  Run: `cd client/desktop && go test ./internal/fs/ -v`
  Expected: PASS (3 passed)

  > 注意：`ScanTree` 对 `maxDepth` 的处理是"目录层级不超过 maxDepth 才递归展开子目录"，根目录为 depth 0。`TestScanTreeSkipsIgnoredDirs` 用 `maxDepth=4`，`src` 位于 depth 1 会展开，满足断言。

- [ ] **Step 6: Commit**

  ```bash
  git add client/desktop/internal/fs/
  git commit -m "feat(desktop): add fs module for directory scan and file read/write"
  ```

---

### Task 4: git CLI 基础（exec 封装 + status --porcelain=v2 解析）

**Files:**
- Create: `client/desktop/internal/git/cli.go`
- Create: `client/desktop/internal/git/status.go`
- Create: `client/desktop/internal/git/status_test.go`

**Interfaces:**
- Consumes: `store.Keychain`（Task 2）——本 Task 仅作为依赖声明注入，凭据注入逻辑在 Task 6 使用
- Produces:
  ```go
  type Git struct { keychain store.Keychain }
  func NewGit(kc store.Keychain) *Git
  func (g *Git) run(dir string, args ...string) (string, error)   // 内部
  type StatusEntry struct {
      X            string `json:"x"`
      Y            string `json:"y"`
      Path         string `json:"path"`
      OriginalPath string `json:"original_path,omitempty"`
  }
  type StatusResult struct {
      Branch     string        `json:"branch"`
      Ahead      int           `json:"ahead"`
      Behind     int           `json:"behind"`
      Staged     []StatusEntry `json:"staged"`
      Modified   []StatusEntry `json:"modified"`
      Untracked  []string      `json:"untracked"`
  }
  func (g *Git) Status(dir string) (*StatusResult, error)
  ```

- [ ] **Step 1: 写失败测试 `status_test.go`**

  ```go
  package git

  import (
      "os"
      "os/exec"
      "path/filepath"
      "testing"

      "desktop/internal/store"
  )

  func TestStatusPorcelain(t *testing.T) {
      dir := t.TempDir()
      runIn(t, dir, "init")
      runIn(t, dir, "config", "user.email", "t@t")
      runIn(t, dir, "config", "user.name", "T")
      mkFile(t, dir, "keep.txt")
      runIn(t, dir, "add", "keep.txt")
      runIn(t, dir, "commit", "-m", "init")

      mkFile(t, dir, "new.txt")          // untracked
      appendTo(t, filepath.Join(dir, "keep.txt"), "more\n") // modified

      g := NewGit(&store.FakeKeychain{})
      st, err := g.Status(dir)
      if err != nil {
          t.Fatalf("Status: %v", err)
      }
      if st.Branch != "master" && st.Branch != "main" {
          t.Fatalf("branch = %q", st.Branch)
      }
      if len(st.Untracked) != 1 || st.Untracked[0] != "new.txt" {
          t.Fatalf("untracked = %+v", st.Untracked)
      }
      if len(st.Modified) != 1 || st.Modified[0].Path != "keep.txt" {
          t.Fatalf("modified = %+v", st.Modified)
      }
  }

  func runIn(t *testing.T, dir string, args ...string) {
      t.Helper()
      cmd := exec.Command("git", args...)
      cmd.Dir = dir
      if out, err := cmd.CombinedOutput(); err != nil {
          t.Fatalf("git %v: %v\n%s", args, err, out)
      }
  }

  func mkFile(t *testing.T, dir, name string) {
      t.Helper()
      if err := os.WriteFile(filepath.Join(dir, name), []byte("x"), 0o644); err != nil {
          t.Fatal(err)
      }
  }

  func appendTo(t *testing.T, path, s string) {
      t.Helper()
      f, err := os.OpenFile(path, os.O_APPEND|os.O_WRONLY, 0o644)
      if err != nil {
          t.Fatal(err)
      }
      defer f.Close()
      if _, err := f.WriteString(s); err != nil {
          t.Fatal(err)
      }
  }
  ```

- [ ] **Step 2: 运行确认失败**

  Run: `cd client/desktop && go test ./internal/git/ -v`
  Expected: FAIL（git 包不存在）

- [ ] **Step 3: 实现 `cli.go`**

  ```go
  package git

  import (
      "bytes"
      "fmt"
      "os"
      "os/exec"

      "desktop/internal/store"
  )

  type Git struct {
      keychain store.Keychain
  }

  func NewGit(kc store.Keychain) *Git {
      return &Git{keychain: kc}
  }

  func (g *Git) run(dir string, args ...string) (string, error) {
      cmd := exec.Command("git", args...)
      cmd.Dir = dir
      var out, errb bytes.Buffer
      cmd.Stdout = &out
      cmd.Stderr = &errb
      if err := cmd.Run(); err != nil {
          return out.String(), fmt.Errorf("git %v: %w: %s", args, err, errb.String())
      }
      return out.String(), nil
  }

  func (g *Git) runEnv(dir string, env []string, args ...string) (string, error) {
      cmd := exec.Command("git", args...)
      cmd.Dir = dir
      cmd.Env = append(os.Environ(), env...)
      var out, errb bytes.Buffer
      cmd.Stdout = &out
      cmd.Stderr = &errb
      if err := cmd.Run(); err != nil {
          return out.String(), fmt.Errorf("git %v: %w: %s", args, err, errb.String())
      }
      return out.String(), nil
  }
  ```

- [ ] **Step 4: 实现 `status.go`**

  ```go
  package git

  import (
      "bufio"
      "strconv"
      "strings"
  )

  type StatusEntry struct {
      X            string `json:"x"`
      Y            string `json:"y"`
      Path         string `json:"path"`
      OriginalPath string `json:"original_path,omitempty"`
  }

  type StatusResult struct {
      Branch    string        `json:"branch"`
      Ahead     int           `json:"ahead"`
      Behind    int           `json:"behind"`
      Staged    []StatusEntry `json:"staged"`
      Modified  []StatusEntry `json:"modified"`
      Untracked []string      `json:"untracked"`
  }

  func (g *Git) Status(dir string) (*StatusResult, error) {
      out, err := g.run(dir, "status", "--porcelain=v2", "--branch")
      if err != nil {
          return nil, err
      }
      res := &StatusResult{}
      sc := bufio.NewScanner(strings.NewReader(out))
      for sc.Scan() {
          line := sc.Text()
          switch {
          case strings.HasPrefix(line, "# branch.head "):
              res.Branch = strings.TrimPrefix(line, "# branch.head ")
          case strings.HasPrefix(line, "# branch.ab "):
              ab := strings.TrimPrefix(line, "# branch.ab ")
              parseAb(ab, res)
          case strings.HasPrefix(line, "1 "):
              f := strings.Fields(line[2:])
              if len(f) >= 3 {
                  e := StatusEntry{X: f[0], Y: f[1], Path: f[2]}
                  res.Modified = append(res.Modified, e)
              }
          case strings.HasPrefix(line, "2 "):
              f := strings.Fields(line[2:])
              if len(f) >= 4 {
                  e := StatusEntry{X: f[0], Y: f[1], Path: f[3], OriginalPath: f[2]}
                  res.Modified = append(res.Modified, e)
              }
          case strings.HasPrefix(line, "?"):
              f := strings.Fields(line[1:])
              if len(f) >= 1 {
                  res.Untracked = append(res.Untracked, f[0])
              }
          }
      }
      // 拆分 staged/modified：X 非 '.' 或非 0 → staged
      var staged, modified []StatusEntry
      for _, e := range res.Modified {
          if e.X != "." && e.X != "?" && e.X != " " {
              staged = append(staged, e)
          } else {
              modified = append(modified, e)
          }
      }
      res.Staged, res.Modified = staged, modified
      return res, sc.Err()
  }

  func parseAb(ab string, res *StatusResult) {
      // 格式: +<ahead> -<behind>，可能只有一边
      fields := strings.Fields(ab)
      for _, f := range fields {
          if strings.HasPrefix(f, "+") {
              res.Ahead, _ = strconv.Atoi(strings.TrimPrefix(f, "+"))
          } else if strings.HasPrefix(f, "-") {
              res.Behind, _ = strconv.Atoi(strings.TrimPrefix(f, "-"))
          }
      }
  }
  ```

- [ ] **Step 5: 运行确认通过**

  Run: `cd client/desktop && go test ./internal/git/ -v`
  Expected: PASS（注意：Windows 上默认分支可能是 `main`，测试已兼容两者）

- [ ] **Step 6: Commit**

  ```bash
  git add client/desktop/internal/git/
  git commit -m "feat(desktop): add git cli wrapper and porcelain v2 status parsing"
  ```

---

### Task 5: git diff 解析

**Files:**
- Create: `client/desktop/internal/git/diff.go`
- Create: `client/desktop/internal/git/diff_test.go`

**Interfaces:**
- Consumes: `Git.run`（Task 4）
- Produces:
  ```go
  type DiffHunk struct {
      Header string   `json:"header"`
      Lines  []string `json:"lines"`
  }
  func (g *Git) Diff(dir, a, b string) ([]DiffHunk, error)
  // a,b 为 tree-ish 或 ""（空串表示工作区/HEAD）。示例：Diff(dir, "HEAD", ""), Diff(dir, "HEAD", "HEAD~1")
  ```

- [ ] **Step 1: 写失败测试 `diff_test.go`**

  ```go
  package git

  import (
      "os"
      "os/exec"
      "path/filepath"
      "testing"

      "desktop/internal/store"
  )

  func TestDiffParsesHunks(t *testing.T) {
      dir := t.TempDir()
      runIn(t, dir, "init")
      runIn(t, dir, "config", "user.email", "t@t")
      runIn(t, dir, "config", "user.name", "T")
      mkFile(t, dir, "a.txt")
      runIn(t, dir, "add", ".")
      runIn(t, dir, "commit", "-m", "one")

      appendTo(t, filepath.Join(dir, "a.txt"), "line2\n")
      runIn(t, dir, "add", "a.txt")
      runIn(t, dir, "commit", "-m", "two")

      g := NewGit(&store.FakeKeychain{})
      hunks, err := g.Diff(dir, "HEAD~1", "HEAD")
      if err != nil {
          t.Fatalf("Diff: %v", err)
      }
      if len(hunks) == 0 {
          t.Fatal("expected at least one hunk")
      }
      found := false
      for _, h := range hunks {
          if h.Header != "" && containsHunkLine(h, "+line2") {
              found = true
          }
      }
      if !found {
          t.Fatalf("expected +line2 in hunks: %+v", hunks)
      }
  }

  func containsHunkLine(h DiffHunk, want string) bool {
      for _, l := range h.Lines {
          if l == want {
              return true
          }
      }
      return false
  }
  ```

- [ ] **Step 2: 运行确认失败**

  Run: `cd client/desktop && go test ./internal/git/ -run TestDiffParsesHunks -v`
  Expected: FAIL（Diff 未定义）

- [ ] **Step 3: 实现 `diff.go`**

  ```go
  package git

  import (
      "bufio"
      "strings"
  )

  type DiffHunk struct {
      Header string   `json:"header"`
      Lines  []string `json:"lines"`
  }

  func (g *Git) Diff(dir, a, b string) ([]DiffHunk, error) {
      args := []string{"diff", "--no-color", "-U3"}
      if a != "" {
          args = append(args, a)
      }
      if b != "" {
          args = append(args, b)
      }
      out, err := g.run(dir, args...)
      if err != nil {
          return nil, err
      }
      return parseDiff(out), nil
  }

  func parseDiff(out string) []DiffHunk {
      var hunks []DiffHunk
      var cur *DiffHunk
      sc := bufio.NewScanner(strings.NewReader(out))
      for sc.Scan() {
          line := sc.Text()
          if strings.HasPrefix(line, "@@") {
              if cur != nil {
                  hunks = append(hunks, *cur)
              }
              cur = &DiffHunk{Header: line}
              continue
          }
          if cur == nil {
              continue
          }
          cur.Lines = append(cur.Lines, line)
      }
      if cur != nil {
          hunks = append(hunks, *cur)
      }
      return hunks
  }
  ```

- [ ] **Step 4: 运行确认通过**

  Run: `cd client/desktop && go test ./internal/git/ -v`
  Expected: PASS

- [ ] **Step 5: Commit**

  ```bash
  git add client/desktop/internal/git/diff.go client/desktop/internal/git/diff_test.go
  git commit -m "feat(desktop): add git diff parsing"
  ```

---

### Task 6: git 操作（add/commit/log/branch/init/clone/push/pull + 凭据注入）

**Files:**
- Create: `client/desktop/internal/git/operations.go`
- Create: `client/desktop/internal/git/clone.go`
- Create: `client/desktop/internal/git/remote.go`
- Create: `client/desktop/internal/git/operations_test.go`

**Interfaces:**
- Consumes: `Git.run` / `Git.runEnv`（Task 4）、`store.Keychain`（Task 2）
- Produces:
  ```go
  type Credential struct {
      Type       string `json:"type"` // "none" | "token" | "ssh"
      Token      string `json:"token,omitempty"`
      SSHKeyPath string `json:"ssh_key_path,omitempty"`
  }
  type CommitInfo struct {
      Hash    string `json:"hash"`
      Short   string `json:"short"`
      Subject string `json:"subject"`
      Author  string `json:"author"`
      Date    string `json:"date"`
  }
  func (g *Git) Add(dir string, paths ...string) error
  func (g *Git) Commit(dir, message string) error
  func (g *Git) Log(dir string, n int) ([]CommitInfo, error)
  func (g *Git) CurrentBranch(dir string) (string, error)
  func (g *Git) Init(dir string) error
  func (g *Git) Clone(url, dest string, cred Credential) error
  func (g *Git) Push(dir, remote, branch string, cred Credential) error
  func (g *Git) Pull(dir, remote, branch string, cred Credential) error
  ```

- [ ] **Step 1: 写失败测试 `operations_test.go`**

  ```go
  package git

  import (
      "path/filepath"
      "testing"

      "desktop/internal/store"
  )

  func TestCommitAndLog(t *testing.T) {
      dir := t.TempDir()
      runIn(t, dir, "init")
      runIn(t, dir, "config", "user.email", "t@t")
      runIn(t, dir, "config", "user.name", "T")
      mkFile(t, dir, "f.txt")

      g := NewGit(&store.FakeKeychain{})
      if err := g.Add(dir, "."); err != nil {
          t.Fatalf("Add: %v", err)
      }
      if err := g.Commit(dir, "feat: first"); err != nil {
          t.Fatalf("Commit: %v", err)
      }
      commits, err := g.Log(dir, 5)
      if err != nil {
          t.Fatalf("Log: %v", err)
      }
      if len(commits) != 1 || commits[0].Subject != "feat: first" {
          t.Fatalf("commits = %+v", commits)
      }
      br, err := g.CurrentBranch(dir)
      if err != nil || br == "" {
          t.Fatalf("CurrentBranch = %q, err %v", br, err)
      }
  }

  func TestCloneAndPushPull(t *testing.T) {
      src := t.TempDir()
      runIn(t, src, "init")
      runIn(t, src, "config", "user.email", "t@t")
      runIn(t, src, "config", "user.name", "T")
      runIn(t, src, "config", "receive.denyCurrentBranch", "ignore")
      mkFile(t, src, "x.txt")
      runIn(t, src, "add", ".")
      runIn(t, src, "commit", "-m", "seed")

      dest := filepath.Join(t.TempDir(), "clone")
      g := NewGit(&store.FakeKeychain{})
      if err := g.Clone(src, dest, Credential{Type: "none"}); err != nil {
          t.Fatalf("Clone: %v", err)
      }

      // 在 clone 中新增提交并 push 回 src
      mkFile(t, dest, "y.txt")
      runIn(t, dest, "config", "user.email", "t@t")
      runIn(t, dest, "config", "user.name", "T")
      if err := g.Add(dest, "."); err != nil {
          t.Fatalf("Add: %v", err)
      }
      if err := g.Commit(dest, "feat: second"); err != nil {
          t.Fatalf("Commit: %v", err)
      }
      if err := g.Push(dest, "origin", "HEAD", Credential{Type: "none"}); err != nil {
          t.Fatalf("Push: %v", err)
      }
  }
  ```

- [ ] **Step 2: 运行确认失败**

  Run: `cd client/desktop && go test ./internal/git/ -run "TestCommitAndLog|TestCloneAndPushPull" -v`
  Expected: FAIL（方法未定义）

- [ ] **Step 3: 实现 `operations.go`**

  ```go
  package git

  import (
      "bufio"
      "fmt"
      "strings"
  )

  func (g *Git) Init(dir string) error {
      _, err := g.run(dir, "init")
      return err
  }

  func (g *Git) Add(dir string, paths ...string) error {
      args := append([]string{"add"}, paths...)
      _, err := g.run(dir, args...)
      return err
  }

  func (g *Git) Commit(dir, message string) error {
      _, err := g.run(dir, "commit", "-m", message)
      return err
  }

  type CommitInfo struct {
      Hash    string `json:"hash"`
      Short   string `json:"short"`
      Subject string `json:"subject"`
      Author  string `json:"author"`
      Date    string `json:"date"`
  }

  func (g *Git) Log(dir string, n int) ([]CommitInfo, error) {
      out, err := g.run(dir, "log", fmt.Sprintf("-n%d", n),
          `--format=%H%x09%h%x09%an%x09%ai%x09%s`)
      if err != nil {
          return nil, err
      }
      var commits []CommitInfo
      sc := bufio.NewScanner(strings.NewReader(out))
      for sc.Scan() {
          f := strings.SplitN(sc.Text(), "\t", 5)
          if len(f) != 5 {
              continue
          }
          commits = append(commits, CommitInfo{Hash: f[0], Short: f[1], Author: f[2], Date: f[3], Subject: f[4]})
      }
      return commits, sc.Err()
  }

  func (g *Git) CurrentBranch(dir string) (string, error) {
      out, err := g.run(dir, "symbolic-ref", "--short", "HEAD")
      if err != nil {
          return "", err
      }
      return strings.TrimSpace(out), nil
  }
  ```

- [ ] **Step 4: 实现 `clone.go` 与 `remote.go`**

  ```go
  package git

  import "os"

  func (g *Git) Clone(url, dest string, cred Credential) error {
      if err := os.MkdirAll(dest, 0o755); err != nil {
          return err
      }
      args := append(gitCredArgs(url, cred), "clone", url, dest)
      _, err := g.run("", args...)
      return err
  }

  func (g *Git) Push(dir, remote, branch string, cred Credential) error {
      var ref string
      if branch == "HEAD" {
          ref = "HEAD"
      } else {
          ref = branch
      }
      args := append(gitCredArgs(remoteURL(g, dir, remote), cred), "push", remote, ref)
      _, err := g.run(dir, args...)
      return err
  }

  func (g *Git) Pull(dir, remote, branch string, cred Credential) error {
      args := append(gitCredArgs(remoteURL(g, dir, remote), cred), "pull", remote, branch)
      _, err := g.run(dir, args...)
      return err
  }

  func remoteURL(g *Git, dir, remote string) string {
      out, err := g.run(dir, "config", "--get", "remote."+remote+".url")
      if err != nil {
          return ""
      }
      return trimSpace(out)
  }

  func gitCredArgs(url string, cred Credential) []string {
      switch cred.Type {
      case "token":
          if url != "" {
              return []string{"-c", "http.extraHeader=Authorization: Bearer " + cred.Token}
          }
      case "ssh":
          if cred.SSHKeyPath != "" {
              return []string{"-c", "core.sshCommand=ssh -i " + cred.SSHKeyPath + " -o IdentitiesOnly=yes -o BatchMode=yes"}
          }
      }
      return nil
  }
  ```

  ```go
  package git

  import "strings"

  func trimSpace(s string) string {
      return strings.TrimSpace(s)
  }
  ```

  > 注意：`gitCredArgs` 用 `-c` 注入 token/SSH 命令，避免明文落盘到 git 配置。生产实现后续（Phase 2+）用 `store.Keychain` 拉取凭据；Phase 1 由网关路由传入明文 token（内存态）。

- [ ] **Step 5: 修正测试中的分支名 push**

  说明：`TestCloneAndPushPull` 中 `Push(dest, "origin", "HEAD", ...)` 在无上游分支时 `git push origin HEAD` 需要 `-u` 才能建立跟踪，否则报错。将测试改为直接指定分支名：

  ```go
  br, _ := g.CurrentBranch(dest)
  if err := g.Push(dest, "origin", br, Credential{Type: "none"}); err != nil {
      t.Fatalf("Push: %v", err)
  }
  ```

  同时 `Clone` 使用 `git clone <url> <dest>` 时 dest 不应预先存在，将实现改为不 `MkdirAll`（git clone 会自建目标目录）：

  ```go
  func (g *Git) Clone(url, dest string, cred Credential) error {
      args := append(gitCredArgs(url, cred), "clone", url, dest)
      _, err := g.run("", args...)
      return err
  }
  ```

- [ ] **Step 6: 运行确认通过**

  Run: `cd client/desktop && go test ./internal/git/ -v`
  Expected: PASS（本地文件仓库 clone/push 用 `file://` 语义，`src` 作为 URL 时 git 视为本地路径，push 需 `receive.denyCurrentBranch=ignore`，测试已设置）

- [ ] **Step 7: Commit**

  ```bash
  git add client/desktop/internal/git/
  git commit -m "feat(desktop): add git operations clone push pull with credential injection"
  ```

---

### Task 7: 网关核心（动态端口 + CORS + 会话 token + config 路由）

**Files:**
- Create: `client/desktop/internal/gateway/gateway.go`
- Create: `client/desktop/internal/gateway/middleware.go`
- Create: `client/desktop/internal/gateway/router.go`
- Create: `client/desktop/internal/gateway/json.go`
- Create: `client/desktop/internal/gateway/handlers_config.go`
- Create: `client/desktop/internal/gateway/gateway_test.go`

**Interfaces:**
- Consumes: `store.Store`（Task 1）
- Produces:
  ```go
  type Config struct {
      Store           *store.Store
      AllowedOrigins  []string // 默认 ["http://localhost:34115","wails://localhost"]
  }
  type Gateway struct { ... }
  func New(cfg Config) *Gateway
  func (g *Gateway) Start() error      // 绑定 127.0.0.1:0 并后台 serve
  func (g *Gateway) Addr() string      // "127.0.0.1:PORT"
  func (g *Gateway) Token() string     // 随机会话 token
  func (g *Gateway) Stop() error
  func (g *Gateway) Handler() http.Handler  // 供 httptest 使用
  ```

- [ ] **Step 1: 写失败测试 `gateway_test.go`**

  ```go
  package gateway

  import (
      "net/http"
      "net/http/httptest"
      "testing"

      "desktop/internal/store"
  )

  func TestConfigRouteAndToken(t *testing.T) {
      st, _ := store.New("")
      defer st.Close()
      g := New(Config{Store: st, AllowedOrigins: []string{"http://localhost:34115"}})
      h := g.Handler()

      // 无 token 访问 config（放行）
      req := httptest.NewRequest("GET", "/api/local/config", nil)
      req.Header.Set("Origin", "http://localhost:34115")
      rr := httptest.NewRecorder()
      h.ServeHTTP(rr, req)
      if rr.Code != 200 {
          t.Fatalf("config status = %d body=%s", rr.Code, rr.Body.String())
      }

      // 无 token 访问其他路由 → 401
      req = httptest.NewRequest("GET", "/api/local/workspaces", nil)
      req.Header.Set("Origin", "http://localhost:34115")
      rr = httptest.NewRecorder()
      h.ServeHTTP(rr, req)
      if rr.Code != 401 {
          t.Fatalf("expected 401, got %d", rr.Code)
      }

      // 带 token → 200
      req = httptest.NewRequest("GET", "/api/local/workspaces", nil)
      req.Header.Set("Origin", "http://localhost:34115")
      req.Header.Set("X-Gateway-Token", g.Token())
      rr = httptest.NewRecorder()
      h.ServeHTTP(rr, req)
      if rr.Code != 200 {
          t.Fatalf("with token status = %d body=%s", rr.Code, rr.Body.String())
      }
  }

  func TestCORSDisallowedOrigin(t *testing.T) {
      st, _ := store.New("")
      defer st.Close()
      g := New(Config{Store: st, AllowedOrigins: []string{"http://localhost:34115"}})
      req := httptest.NewRequest("GET", "/api/local/config", nil)
      req.Header.Set("Origin", "https://evil.example.com")
      rr := httptest.NewRecorder()
      g.Handler().ServeHTTP(rr, req)
      if rr.Code != 403 {
          t.Fatalf("expected 403 for disallowed origin, got %d", rr.Code)
      }
  }
  ```

- [ ] **Step 2: 运行确认失败**

  Run: `cd client/desktop && go test ./internal/gateway/ -v`
  Expected: FAIL（gateway 包不存在）

- [ ] **Step 3: 实现 `gateway.go`**

  ```go
  package gateway

  import (
      "crypto/rand"
      "encoding/hex"
      "fmt"
      "net"
      "net/http"

      "desktop/internal/store"
  )

  type Config struct {
      Store          *store.Store
      AllowedOrigins []string
  }

  type Gateway struct {
      store     *store.Store
      origins   map[string]bool
      token     string
      addr      string
      listener  net.Listener
      server    *http.Server
      handler   http.Handler
  }

  func New(cfg Config) *Gateway {
      if len(cfg.AllowedOrigins) == 0 {
          cfg.AllowedOrigins = []string{"http://localhost:34115", "wails://localhost"}
      }
      g := &Gateway{
          store:   cfg.Store,
          origins: map[string]bool{},
          token:   newToken(),
      }
      for _, o := range cfg.AllowedOrigins {
          g.origins[o] = true
      }
      g.handler = g.buildRouter()
      return g
  }

  func newToken() string {
      b := make([]byte, 16)
      _, _ = rand.Read(b)
      return hex.EncodeToString(b)
  }

  func (g *Gateway) Start() error {
      ln, err := net.Listen("tcp", "127.0.0.1:0")
      if err != nil {
          return err
      }
      g.listener = ln
      g.addr = ln.Addr().String()
      g.server = &http.Server{Handler: g.handler}
      go func() { _ = g.server.Serve(ln) }()
      return nil
  }

  func (g *Gateway) Addr() string  { return g.addr }
  func (g *Gateway) Token() string { return g.token }

  func (g *Gateway) Stop() error {
      if g.server != nil {
          return g.server.Close()
      }
      return nil
  }

  func (g *Gateway) Handler() http.Handler { return g.handler }

  func (g *Gateway) originAllowed(origin string) bool {
      return g.origins[origin]
  }

  func (g *Gateway) validToken(t string) bool {
      return t != "" && t == g.token
  }
  ```

- [ ] **Step 4: 实现 `middleware.go`**

  ```go
  package gateway

  import (
      "net/http"
  )

  func (g *Gateway) withSecurity(next http.Handler) http.Handler {
      return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
          origin := r.Header.Get("Origin")
          if origin != "" && !g.originAllowed(origin) {
              http.Error(w, `{"error":{"code":"CORS_FORBIDDEN","message":"origin not allowed"}}`, http.StatusForbidden)
              return
          }
          if origin != "" {
              w.Header().Set("Access-Control-Allow-Origin", origin)
              w.Header().Set("Access-Control-Allow-Headers", "Content-Type, X-Gateway-Token, Authorization")
              w.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
              w.Header().Set("Vary", "Origin")
          }
          if r.Method == http.MethodOptions {
              w.WriteHeader(http.StatusNoContent)
              return
          }
          // 除 config 外需要会话 token
          if r.URL.Path != "/api/local/config" && !g.validToken(r.Header.Get("X-Gateway-Token")) {
              http.Error(w, `{"error":{"code":"UNAUTHORIZED","message":"missing or invalid gateway token"}}`, http.StatusUnauthorized)
              return
          }
          next.ServeHTTP(w, r)
      })
  }
  ```

- [ ] **Step 5: 实现 `json.go`、`handlers_config.go`、`router.go`**

  ```go
  package gateway

  import (
      "encoding/json"
      "net/http"
  )

  type ErrorBody struct {
      Code    string `json:"code"`
      Message string `json:"message"`
  }

  func writeJSON(w http.ResponseWriter, status int, v any) {
      w.Header().Set("Content-Type", "application/json")
      w.WriteHeader(status)
      _ = json.NewEncoder(w).Encode(v)
  }

  func writeError(w http.ResponseWriter, status int, code, msg string) {
      writeJSON(w, status, map[string]any{"error": ErrorBody{Code: code, Message: msg}})
  }
  ```

  ```go
  package gateway

  import "net/http"

  type ConfigResponse struct {
      BaseURL         string `json:"baseURL"`
      GatewayToken    string `json:"gatewayToken"`
      DefaultServerID string `json:"defaultServerId"`
  }

  func (g *Gateway) handleConfig(w http.ResponseWriter, r *http.Request) {
      baseURL := "http://" + g.Addr()
      writeJSON(w, http.StatusOK, ConfigResponse{BaseURL: baseURL, GatewayToken: g.token})
  }
  ```

  ```go
  package gateway

  import "net/http"

  func (g *Gateway) buildRouter() http.Handler {
      mux := http.NewServeMux()
      mux.HandleFunc("GET /api/local/config", g.handleConfig)
      // 工作区路由在 Task 8 注册
      mux.HandleFunc("GET /api/local/workspaces", g.handleListWorkspaces)
      mux.HandleFunc("POST /api/local/workspaces", g.handleCreateWorkspace)
      mux.HandleFunc("GET /api/local/workspaces/{id}", g.handleGetWorkspace)
      mux.HandleFunc("DELETE /api/local/workspaces/{id}", g.handleDeleteWorkspace)
      mux.HandleFunc("POST /api/local/workspaces/{id}/clone", g.handleCloneWorkspace)
      mux.HandleFunc("POST /api/local/workspaces/{id}/git/{op}", g.handleGitOp)
      mux.HandleFunc("GET /api/local/workspaces/{id}/tree", g.handleTree)
      mux.HandleFunc("GET /api/local/workspaces/{id}/file", g.handleReadFile)
      mux.HandleFunc("PUT /api/local/workspaces/{id}/file", g.handleWriteFile)
      return g.withSecurity(mux)
  }
  ```

  > 说明：Task 8 实现 handlers_workspace.go / handlers_fs.go 中的 8 个 handler，编译即通过（先以 stub 满足测试）。

- [ ] **Step 6: 实现 stub handler（本 Task 让测试通过的最小实现，Task 8 删除 stubs.go 并填完整逻辑）**

  新建 `internal/gateway/stubs.go`：

  ```go
  package gateway

  import "net/http"

  func (g *Gateway) handleListWorkspaces(w http.ResponseWriter, r *http.Request) {
      writeJSON(w, http.StatusOK, map[string]any{"items": []any{}})
  }
  func (g *Gateway) handleCreateWorkspace(w http.ResponseWriter, r *http.Request) {
      writeError(w, http.StatusNotImplemented, "NOT_IMPLEMENTED", "todo")
  }
  func (g *Gateway) handleGetWorkspace(w http.ResponseWriter, r *http.Request) {
      writeError(w, http.StatusNotImplemented, "NOT_IMPLEMENTED", "todo")
  }
  func (g *Gateway) handleDeleteWorkspace(w http.ResponseWriter, r *http.Request) {
      writeError(w, http.StatusNotImplemented, "NOT_IMPLEMENTED", "todo")
  }
  func (g *Gateway) handleCloneWorkspace(w http.ResponseWriter, r *http.Request) {
      writeError(w, http.StatusNotImplemented, "NOT_IMPLEMENTED", "todo")
  }
  func (g *Gateway) handleGitOp(w http.ResponseWriter, r *http.Request) {
      writeError(w, http.StatusNotImplemented, "NOT_IMPLEMENTED", "todo")
  }
  func (g *Gateway) handleTree(w http.ResponseWriter, r *http.Request) {
      writeError(w, http.StatusNotImplemented, "NOT_IMPLEMENTED", "todo")
  }
  func (g *Gateway) handleReadFile(w http.ResponseWriter, r *http.Request) {
      writeError(w, http.StatusNotImplemented, "NOT_IMPLEMENTED", "todo")
  }
  func (g *Gateway) handleWriteFile(w http.ResponseWriter, r *http.Request) {
      writeError(w, http.StatusNotImplemented, "NOT_IMPLEMENTED", "todo")
  }
  ```

  > Go 版本要求：`http.ServeMux` 的方法+通配符模式（`GET /.../{id}`）需 Go 1.22+。本机 1.26 满足；go.mod 已声明 go 1.23.0。
  > Task 8 会删除 `stubs.go` 并以真实实现替换这些方法。

- [ ] **Step 7: 运行确认通过**

  Run: `cd client/desktop && go test ./internal/gateway/ -v`
  Expected: PASS (2 passed)

- [ ] **Step 8: Commit**

  ```bash
  git add client/desktop/internal/gateway/
  git commit -m "feat(desktop): add local gateway with dynamic port CORS and session token"
  ```

---

### Task 8: 网关工作区路由（workspaces CRUD + clone + git/{op} + tree/file）

**Files:**
- Create: `client/desktop/internal/gateway/handlers_workspace.go`
- Create: `client/desktop/internal/gateway/handlers_fs.go`
- Create: `client/desktop/internal/gateway/handlers_workspace_test.go`

**Interfaces:**
- Consumes: `Gateway`（Task 7）、`store.Store`、`git.Git`、`fs` 包
- Produces: 完整工作区 API：
  - `GET /api/local/workspaces` → `{items: Workspace[]}`
  - `POST /api/local/workspaces` body `{name, path}` → Workspace
  - `GET /api/local/workspaces/{id}` → Workspace
  - `DELETE /api/local/workspaces/{id}` → `{ok: true}`
  - `POST /api/local/workspaces/{id}/clone` body `{url, name, credential}` → Workspace
  - `POST /api/local/workspaces/{id}/git/{op}` body 按 op 不同 → 见各 handler
  - `GET /api/local/workspaces/{id}/tree` → `fs.FileNode`
  - `GET /api/local/workspaces/{id}/file?path=` → `fs.FileContent`
  - `PUT /api/local/workspaces/{id}/file` body `{path, content}` → `fs.WriteResult`

  注意：`Git` 实例注入方式——Task 8 在 `Config` 上新增字段 `Git *git.Git`（Task 7 的 Config 同步修改，非破坏性）。

- [ ] **Step 1: 在 `Config` 增加 Git 依赖**

  修改 `gateway.go` 的 `Config`：

  ```go
  import "desktop/internal/git"
  type Config struct {
      Store          *store.Store
      Git            *git.Git
      AllowedOrigins []string
  }
  ```

  并在 `Gateway` 结构体与 `New` 中保存 `g.git = cfg.Git`。

- [ ] **Step 1b: 删除 `stubs.go`，用真实实现替换**

  Run: `git rm client/desktop/internal/gateway/stubs.go`
  后续 Step 4/5 创建的 `handlers_workspace.go` / `handlers_fs.go` 提供同名 handler，编译即通过。

- [ ] **Step 2: 写失败测试 `handlers_workspace_test.go`**

  ```go
  package gateway

  import (
      "bytes"
      "encoding/json"
      "net/http"
      "net/http/httptest"
      "os"
      "os/exec"
      "path/filepath"
      "testing"

      "desktop/internal/git"
      "desktop/internal/store"
  )

  func newTestGateway(t *testing.T) (*Gateway, *store.Store) {
      t.Helper()
      st, _ := store.New("")
      g := New(Config{
          Store: st,
          Git:   git.NewGit(&store.FakeKeychain{M: map[string]string{}}),
          AllowedOrigins: []string{"http://localhost:34115"},
      })
      return g, st
  }

  func authedReq(t *testing.T, g *Gateway, method, path string, body any) *httptest.ResponseRecorder {
      t.Helper()
      var buf bytes.Buffer
      if body != nil {
          _ = json.NewEncoder(&buf).Encode(body)
      }
      req := httptest.NewRequest(method, path, &buf)
      req.Header.Set("Origin", "http://localhost:34115")
      req.Header.Set("X-Gateway-Token", g.Token())
      req.Header.Set("Content-Type", "application/json")
      rr := httptest.NewRecorder()
      g.Handler().ServeHTTP(rr, req)
      return rr
  }

  func TestWorkspaceLifecycle(t *testing.T) {
      g, _ := newTestGateway(t)
      dir := t.TempDir()
      os.MkdirAll(filepath.Join(dir, "proj"), 0o755)

      rr := authedReq(t, g, "POST", "/api/local/workspaces",
          map[string]string{"name": "proj", "path": filepath.Join(dir, "proj")})
      if rr.Code != 200 {
          t.Fatalf("create = %d body=%s", rr.Code, rr.Body.String())
      }
      var ws struct{ ID string `json:"id"`; Path string `json:"path"` }
      if err := json.Unmarshal(rr.Body.Bytes(), &ws); err != nil {
          t.Fatal(err)
      }
      if ws.ID == "" {
          t.Fatal("expected id")
      }

      rr = authedReq(t, g, "GET", "/api/local/workspaces", nil)
      if rr.Code != 200 {
          t.Fatalf("list = %d", rr.Code)
      }
      rr = authedReq(t, g, "DELETE", "/api/local/workspaces/"+ws.ID, nil)
      if rr.Code != 200 {
          t.Fatalf("delete = %d body=%s", rr.Code, rr.Body.String())
      }
  }

  func TestWorkspaceCloneAndGit(t *testing.T) {
      g, _ := newTestGateway(t)
      src := t.TempDir()
      runIn(t, src, "init")
      runIn(t, src, "config", "user.email", "t@t")
      runIn(t, src, "config", "user.name", "T")
      runIn(t, src, "config", "receive.denyCurrentBranch", "ignore")
      mkTestFile(t, src, "x.txt")
      runIn(t, src, "add", ".")
      runIn(t, src, "commit", "-m", "seed")

      base := t.TempDir()
      dest := filepath.Join(base, "repo")

      rr := authedReq(t, g, "POST", "/api/local/workspaces",
          map[string]any{"name": "repo", "path": dest, "url": src, "clone": true})
      if rr.Code != 200 {
          t.Fatalf("clone = %d body=%s", rr.Code, rr.Body.String())
      }
      var ws struct{ ID string `json:"id"` }
      _ = json.Unmarshal(rr.Body.Bytes(), &ws)

      rr = authedReq(t, g, "GET", "/api/local/workspaces/"+ws.ID+"/tree", nil)
      if rr.Code != 200 {
          t.Fatalf("tree = %d body=%s", rr.Code, rr.Body.String())
      }

      rr = authedReq(t, g, "POST", "/api/local/workspaces/"+ws.ID+"/git/status", nil)
      if rr.Code != 200 {
          t.Fatalf("git status = %d body=%s", rr.Code, rr.Body.String())
      }
  }

  func runIn(t *testing.T, dir string, args ...string) {
      t.Helper()
      cmd := exec.Command("git", args...)
      cmd.Dir = dir
      if out, err := cmd.CombinedOutput(); err != nil {
          t.Fatalf("git %v: %v\n%s", args, err, out)
      }
  }

  func mkTestFile(t *testing.T, dir, name string) {
      t.Helper()
      if err := os.WriteFile(filepath.Join(dir, name), []byte("x"), 0o644); err != nil {
          t.Fatal(err)
      }
  }
  ```

- [ ] **Step 3: 运行确认失败**

  Run: `cd client/desktop && go test ./internal/gateway/ -run "TestWorkspace" -v`
  Expected: FAIL（stub 返回 501）

- [ ] **Step 4: 实现 `handlers_workspace.go`**

  ```go
  package gateway

  import (
      "encoding/json"
      "net/http"
      "os"
      "path/filepath"
      "strings"

      "desktop/internal/fs"
      "desktop/internal/git"
      "desktop/internal/store"
  )

  type createWorkspaceReq struct {
      Name   string `json:"name"`
      Path   string `json:"path"`
      URL    string `json:"url,omitempty"`
      Clone  bool   `json:"clone,omitempty"`
      Cred   git.Credential `json:"credential,omitempty"`
  }

  func (g *Gateway) handleListWorkspaces(w http.ResponseWriter, r *http.Request) {
      items, err := g.store.ListWorkspaces()
      if err != nil {
          writeError(w, http.StatusInternalServerError, "STORE_LIST", err.Error())
          return
      }
      writeJSON(w, http.StatusOK, map[string]any{"items": items})
  }

  func (g *Gateway) handleCreateWorkspace(w http.ResponseWriter, r *http.Request) {
      var req createWorkspaceReq
      if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
          writeError(w, http.StatusBadRequest, "BAD_REQUEST", err.Error())
          return
      }
      if req.Path == "" && !req.Clone {
          writeError(w, http.StatusBadRequest, "BAD_REQUEST", "path required when clone=false")
          return
      }
      var abs string
      if req.Path != "" {
          abs, err = filepath.Abs(req.Path)
          if err != nil {
              writeError(w, http.StatusBadRequest, "BAD_REQUEST", err.Error())
              return
          }
      }
      if req.Clone {
          if req.URL == "" {
              writeError(w, http.StatusBadRequest, "BAD_REQUEST", "url required when clone=true")
              return
          }
          if abs == "" {
              abs = defaultCloneDest(req.Name, req.URL)
          }
          if err := g.git.Clone(req.URL, abs, req.Cred); err != nil {
              writeError(w, http.StatusBadGateway, "GIT_CLONE", err.Error())
              return
          }
      } else if err := os.MkdirAll(abs, 0o755); err != nil {
          writeError(w, http.StatusInternalServerError, "FS_MKDIR", err.Error())
          return
      }
      name := req.Name
      if name == "" {
          name = filepath.Base(abs)
      }
      ws, err := g.store.CreateWorkspace(store.Workspace{
          Name: name, Path: abs, RemoteURL: req.URL,
      })
      if err != nil {
          writeError(w, http.StatusInternalServerError, "STORE_CREATE", err.Error())
          return
      }
      writeJSON(w, http.StatusOK, ws)
  }

  func (g *Gateway) handleGetWorkspace(w http.ResponseWriter, r *http.Request) {
      ws, err := g.store.GetWorkspace(r.PathValue("id"))
      if err != nil {
          writeError(w, http.StatusNotFound, "STORE_NOT_FOUND", "workspace not found")
          return
      }
      writeJSON(w, http.StatusOK, ws)
  }

  func (g *Gateway) handleCloneWorkspace(w http.ResponseWriter, r *http.Request) {
      ws, err := g.store.GetWorkspace(r.PathValue("id"))
      if err != nil {
          writeError(w, http.StatusNotFound, "STORE_NOT_FOUND", "workspace not found")
          return
      }
      var body struct {
          URL  string         `json:"url"`
          Cred git.Credential `json:"credential"`
      }
      if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
          writeError(w, http.StatusBadRequest, "BAD_REQUEST", err.Error())
          return
      }
      if body.URL == "" {
          writeError(w, http.StatusBadRequest, "BAD_REQUEST", "url required")
          return
      }
      if err := g.git.Clone(body.URL, ws.Path, body.Cred); err != nil {
          writeError(w, http.StatusBadGateway, "GIT_CLONE", err.Error())
          return
      }
      updated := ws
      updated.RemoteURL = body.URL
      // 重新写回：删除并重建以简化（Phase 2 引入 UpdateWorkspace）
      _ = g.store.DeleteWorkspace(ws.ID)
      created, err := g.store.CreateWorkspace(updated)
      if err != nil {
          writeError(w, http.StatusInternalServerError, "STORE_CREATE", err.Error())
          return
      }
      writeJSON(w, http.StatusOK, created)
  }

  func defaultCloneDest(name, url string) string {
      if name == "" {
          name = strings.TrimSuffix(filepath.Base(url), ".git")
          if name == "" || name == "." {
              name = "repo"
          }
      }
      return filepath.Join(os.UserConfigDir(), "perseus", "workspaces", name)
  }

  func (g *Gateway) handleDeleteWorkspace(w http.ResponseWriter, r *http.Request) {
      if err := g.store.DeleteWorkspace(r.PathValue("id")); err != nil {
          writeError(w, http.StatusNotFound, "STORE_NOT_FOUND", "workspace not found")
          return
      }
      writeJSON(w, http.StatusOK, map[string]bool{"ok": true})
  }

  func (g *Gateway) handleGitOp(w http.ResponseWriter, r *http.Request) {
      ws, err := g.store.GetWorkspace(r.PathValue("id"))
      if err != nil {
          writeError(w, http.StatusNotFound, "STORE_NOT_FOUND", "workspace not found")
          return
      }
      op := r.PathValue("op")
      var body struct {
          Paths   []string        `json:"paths"`
          Message string          `json:"message"`
          Branch  string          `json:"branch"`
          Remote  string          `json:"remote"`
          A       string          `json:"a"`
          B       string          `json:"b"`
          Cred    git.Credential  `json:"credential"`
      }
      _ = json.NewDecoder(r.Body).Decode(&body)
      if body.Remote == "" {
          body.Remote = "origin"
      }
      switch op {
      case "status":
          res, err := g.git.Status(ws.Path)
          if err != nil {
              writeError(w, http.StatusBadGateway, "GIT_STATUS", err.Error())
              return
          }
          writeJSON(w, http.StatusOK, res)
      case "diff":
          hunks, err := g.git.Diff(ws.Path, body.A, body.B)
          if err != nil {
              writeError(w, http.StatusBadGateway, "GIT_DIFF", err.Error())
              return
          }
          writeJSON(w, http.StatusOK, map[string]any{"hunks": hunks})
      case "add":
          if err := g.git.Add(ws.Path, body.Paths...); err != nil {
              writeError(w, http.StatusBadGateway, "GIT_ADD", err.Error())
              return
          }
          writeJSON(w, http.StatusOK, map[string]bool{"ok": true})
      case "commit":
          if err := g.git.Commit(ws.Path, body.Message); err != nil {
              writeError(w, http.StatusBadGateway, "GIT_COMMIT", err.Error())
              return
          }
          writeJSON(w, http.StatusOK, map[string]bool{"ok": true})
      case "push":
          if err := g.git.Push(ws.Path, body.Remote, body.Branch, body.Cred); err != nil {
              writeError(w, http.StatusBadGateway, "GIT_PUSH", err.Error())
              return
          }
          writeJSON(w, http.StatusOK, map[string]bool{"ok": true})
      case "pull":
          if err := g.git.Pull(ws.Path, body.Remote, body.Branch, body.Cred); err != nil {
              writeError(w, http.StatusBadGateway, "GIT_PULL", err.Error())
              return
          }
          writeJSON(w, http.StatusOK, map[string]bool{"ok": true})
      case "log":
          commits, err := g.git.Log(ws.Path, 50)
          if err != nil {
              writeError(w, http.StatusBadGateway, "GIT_LOG", err.Error())
              return
          }
          writeJSON(w, http.StatusOK, map[string]any{"commits": commits})
      case "branch":
          br, err := g.git.CurrentBranch(ws.Path)
          if err != nil {
              writeError(w, http.StatusBadGateway, "GIT_BRANCH", err.Error())
              return
          }
          writeJSON(w, http.StatusOK, map[string]string{"branch": br})
      default:
          writeError(w, http.StatusNotFound, "GIT_OP_UNKNOWN", "unknown git op: "+op)
      }
  }
  ```

  > 需在 `handleCreateWorkspace` 顶部补 `import "desktop/internal/store"`（`store.Workspace`）。本 Task 统一把工作区 POST 语义扩展为支持 `{url, clone}`（覆盖 §7.2 的 clone 最小路径）。

- [ ] **Step 5: 实现 `handlers_fs.go`**

  ```go
  package gateway

  import (
      "encoding/json"
      "net/http"
      "path/filepath"

      "desktop/internal/fs"
  )

  func (g *Gateway) handleTree(w http.ResponseWriter, r *http.Request) {
      ws, err := g.store.GetWorkspace(r.PathValue("id"))
      if err != nil {
          writeError(w, http.StatusNotFound, "STORE_NOT_FOUND", "workspace not found")
          return
      }
      tree, err := fs.ScanTree(ws.Path, 6)
      if err != nil {
          writeError(w, http.StatusInternalServerError, "FS_SCAN", err.Error())
          return
      }
      writeJSON(w, http.StatusOK, tree)
  }

  func (g *Gateway) handleReadFile(w http.ResponseWriter, r *http.Request) {
      ws, err := g.store.GetWorkspace(r.PathValue("id"))
      if err != nil {
          writeError(w, http.StatusNotFound, "STORE_NOT_FOUND", "workspace not found")
          return
      }
      p := r.URL.Query().Get("path")
      if p == "" {
          writeError(w, http.StatusBadRequest, "BAD_REQUEST", "path query required")
          return
      }
      full := filepath.Join(ws.Path, filepath.FromSlash(p))
      fc, err := fs.ReadFile(full)
      if err != nil {
          writeError(w, http.StatusInternalServerError, "FS_READ", err.Error())
          return
      }
      writeJSON(w, http.StatusOK, fc)
  }

  func (g *Gateway) handleWriteFile(w http.ResponseWriter, r *http.Request) {
      ws, err := g.store.GetWorkspace(r.PathValue("id"))
      if err != nil {
          writeError(w, http.StatusNotFound, "STORE_NOT_FOUND", "workspace not found")
          return
      }
      var body struct {
          Path    string `json:"path"`
          Content string `json:"content"`
      }
      if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
          writeError(w, http.StatusBadRequest, "BAD_REQUEST", err.Error())
          return
      }
      full := filepath.Join(ws.Path, filepath.FromSlash(body.Path))
      res, err := fs.WriteFile(full, body.Content)
      if err != nil {
          writeError(w, http.StatusInternalServerError, "FS_WRITE", err.Error())
          return
      }
      writeJSON(w, http.StatusOK, res)
  }
  ```

- [ ] **Step 6: 运行确认通过**

  Run: `cd client/desktop && go test ./internal/gateway/ -v`
  Expected: PASS

  > 注意：`TestWorkspaceCloneAndGit` 中 `POST /api/local/workspaces` 传 `{"name","path","url","clone":true}` 会触发 `Clone(url, abs, Cred{})`。若 `abs` 已存在（临时目录 pre-create），先确保 `base` 目录存在但 `dest` 不存在（git clone 自建）。已在测试中保证。

- [ ] **Step 7: Commit**

  ```bash
  git add client/desktop/internal/gateway/
  git commit -m "feat(desktop): implement gateway workspace git and fs routes"
  ```

---

### Task 9: Wails 绑定（GetGatewayConfig / 对话框 / 密钥库）+ main.go 装配

**Files:**
- Modify: `client/desktop/app.go`
- Modify: `client/desktop/main.go`

**Interfaces:**
- Consumes: `store.New`、`store.NewKeychain`、`gateway.New`、`git.NewGit`
- Produces（Wails 绑定，前端经 `window.go.main.App.*` 调用）：
  ```go
  type GatewayConfig struct {
      BaseURL      string `json:"baseURL"`
      GatewayToken string `json:"gatewayToken"`
  }
  func (a *App) GetGatewayConfig() (GatewayConfig, error)
  func (a *App) OpenFolderDialog() (string, error)
  func (a *App) OpenFileDialog() (string, error)
  func (a *App) SaveFileDialog(defaultName string) (string, error)
  func (a *App) KeychainGet(service, account string) (string, error)
  func (a *App) KeychainSet(service, account, secret string) error
  func (a *App) KeychainDelete(service, account string) error
  ```

- [ ] **Step 1: 重写 `app.go`**

  ```go
  package main

  import (
      "context"
      "fmt"
      "os"
      "path/filepath"

      "desktop/internal/gateway"
      "desktop/internal/git"
      "desktop/internal/store"
  )

  // App struct
  type App struct {
      ctx     context.Context
      store   *store.Store
      gateway *gateway.Gateway
      keychain store.Keychain
  }

  // NewApp creates a new App application struct
  func NewApp() *App {
      return &App{}
  }

  // startup is called when the app starts.
  func (a *App) startup(ctx context.Context) {
      a.ctx = ctx
  }

  // Initialize 在 main 中调用：装配依赖并启动网关。
  func (a *App) Initialize() error {
      st, err := store.New("")
      if err != nil {
          return err
      }
      a.store = st
      a.keychain = store.NewKeychain()
      g := gateway.New(gateway.Config{
          Store: st,
          Git:   git.NewGit(a.keychain),
      })
      if err := g.Start(); err != nil {
          return err
      }
      a.gateway = g
      return nil
  }

  func (a *App) Shutdown() {
      if a.gateway != nil {
          _ = a.gateway.Stop()
      }
      if a.store != nil {
          _ = a.store.Close()
      }
  }

  type GatewayConfig struct {
      BaseURL      string `json:"baseURL"`
      GatewayToken string `json:"gatewayToken"`
  }

  func (a *App) GetGatewayConfig() (GatewayConfig, error) {
      if a.gateway == nil {
          return GatewayConfig{}, errNotReady
      }
      return GatewayConfig{
          BaseURL:      "http://" + a.gateway.Addr(),
          GatewayToken: a.gateway.Token(),
      }, nil
  }

  var errNotReady = fmt.Errorf("app not ready")

  func (a *App) OpenFolderDialog() (string, error) {
      return a.dialogOpenDir()
  }

  func (a *App) OpenFileDialog() (string, error) {
      return a.dialogOpenFile()
  }

  func (a *App) SaveFileDialog(defaultName string) (string, error) {
      return a.dialogSaveFile(defaultName)
  }

  func (a *App) KeychainGet(service, account string) (string, error) {
      return a.keychain.Get(service, account)
  }

  func (a *App) KeychainSet(service, account, secret string) error {
      return a.keychain.Set(service, account, secret)
  }

  func (a *App) KeychainDelete(service, account string) error {
      return a.keychain.Delete(service, account)
  }
  ```

- [ ] **Step 2: 实现对话框辅助 `dialogs.go`（新建）**

  ```go
  package main

  import (
      "github.com/wailsapp/wails/v2/pkg/runtime"
  )

  func (a *App) dialogOpenDir() (string, error) {
      return runtime.OpenDirectoryDialog(a.ctx, runtime.OpenDialogOptions{})
  }

  func (a *App) dialogOpenFile() (string, error) {
      return runtime.OpenFileDialog(a.ctx, runtime.OpenDialogOptions{})
  }

  func (a *App) dialogSaveFile(defaultName string) (string, error) {
      return runtime.SaveFileDialog(a.ctx, runtime.SaveDialogOptions{
          DefaultFilename: defaultName,
      })
  }
  ```

- [ ] **Step 3: 修改 `main.go` 装配**

  ```go
  package main

  import (
      "embed"

      "github.com/wailsapp/wails/v2"
      "github.com/wailsapp/wails/v2/pkg/options"
      "github.com/wailsapp/wails/v2/pkg/options/assetserver"
  )

  //go:embed all:frontend/dist
  var assets embed.FS

  func main() {
      app := NewApp()
      if err := app.Initialize(); err != nil {
          println("desktop init error:", err.Error())
          return
      }
      defer app.Shutdown()

      err := wails.Run(&options.App{
          Title:  "Perseus Desktop",
          Width:  1280,
          Height: 800,
          AssetServer: &assetserver.Options{
              Assets: assets,
          },
          BackgroundColour: &options.RGBA{R: 27, G: 38, B: 54, A: 1},
          OnStartup:        app.startup,
          Bind: []interface{}{
              app,
          },
      })
      if err != nil {
          println("Error:", err.Error())
      }
  }
  ```

- [ ] **Step 4: 重新生成前端绑定并编译验证**

  修改 App 绑定方法后需重新生成 `frontend/wailsjs`：

  Run: `cd client/desktop && wails generate module`
  Expected: `frontend/wailsjs/go/main/App.js` 出现 `GetGatewayConfig`、`OpenFolderDialog`、`KeychainGet` 等新方法（同时保留旧的 `Greet` 直至前端替换，见 Task 10/11）

  Run: `cd client/desktop && go build ./...`
  Expected: 编译通过

  > 注意：`store.New("")` 使用内存库——Phase 1 数据随进程退出丢失，符合"本地优先"最小闭环。数据目录路径（`%APPDATA%/perseus`）留待 Phase 4 设置模块持久化。若需持久化可在 Step 1 改为 `store.New(filepath.Join(os.UserConfigDir(), "perseus", "app.db"))`（需 `os.MkdirAll`）。**采用持久化版本**：

  ```go
  func (a *App) Initialize() error {
      dir, err := os.UserConfigDir()
      if err != nil {
          return err
      }
      dbPath := filepath.Join(dir, "perseus", "app.db")
      if err := os.MkdirAll(filepath.Dir(dbPath), 0o755); err != nil {
          return err
      }
      st, err := store.New(dbPath)
      ...
  }
  ```

  需要新增 imports：`"os"`、`"path/filepath"`。

- [ ] **Step 5: Commit**

  ```bash
  git add client/desktop/app.go client/desktop/dialogs.go client/desktop/main.go
  git commit -m "feat(desktop): wire app bindings gateway and dialogs in wails main"
  ```

---

### Task 10: 前端工程升级（对齐 web + Monaco 本地化）

**Files:**
- Modify: `client/desktop/frontend/package.json`
- Modify: `client/desktop/frontend/vite.config.ts`
- Modify: `client/desktop/frontend/tsconfig.json`
- Modify: `client/desktop/frontend/src/main.tsx`
- Modify: `client/desktop/frontend/src/App.tsx`
- Delete: `client/desktop/frontend/src/App.css`、`client/desktop/frontend/src/style.css`（替换为 desktop.css）

**Interfaces:**
- Consumes: web 端依赖版本（React 19/Vite 8/TS 6/antd 6/zustand 5）
- Produces: `npm run build` 通过；`src/stores/gateway.ts` 导出 `useGatewayStore`

- [ ] **Step 1: 更新 `package.json` 依赖**

  ```json
  {
    "name": "desktop-frontend",
    "private": true,
    "version": "0.0.0",
    "type": "module",
    "scripts": {
      "dev": "vite",
      "build": "tsc && vite build",
      "preview": "vite preview"
    },
    "dependencies": {
      "@ant-design/icons": "^6.3.2",
      "@monaco-editor/react": "^4.7.0",
      "antd": "^6.5.0",
      "monaco-editor": "^0.52.0",
      "react": "^19.2.7",
      "react-dom": "^19.2.7",
      "zustand": "^5.0.14"
    },
    "devDependencies": {
      "@types/react": "^19.2.17",
      "@types/react-dom": "^19.2.3",
      "@vitejs/plugin-react": "^6.0.3",
      "typescript": "~6.0.2",
      "vite": "^8.1.1"
    }
  }
  ```

  > 说明：Phase 1 前端不引入 react-router / react-hook-form / zod / CodeMirror（web 页面移植在 Phase 2+）。`vite.config.ts` 保持 Wails 兼容（`wails dev` 会自动代理到 `34115`）。

- [ ] **Step 2: Monaco worker 本地化（`vite.config.ts` + `main.tsx`）**

  `vite.config.ts`：

  ```ts
  import { defineConfig } from 'vite'
  import react from '@vitejs/plugin-react'

  export default defineConfig({
    plugins: [react()],
    worker: { format: 'es' },
  })
  ```

  `src/main.tsx`：

  ```tsx
  import React from 'react'
  import { createRoot } from 'react-dom/client'
  import * as monaco from 'monaco-editor'
  import { loader } from '@monaco-editor/react'
  import App from './App'
  import './styles/desktop.css'

  self.MonacoEnvironment = {
    getWorker(_, label: string) {
      const esm = 'monaco-editor/esm/vs'
      const map: Record<string, string> = {
        json: `${esm}/language/json/json.worker?worker`,
        css: `${esm}/language/css/css.worker?worker`,
        html: `${esm}/language/html/html.worker?worker`,
        typescript: `${esm}/language/typescript/ts.worker?worker`,
        javascript: `${esm}/language/typescript/ts.worker?worker`,
        editorWorker: `${esm}/editor/editor.worker?worker`,
      }
      const mod = map[label] ?? map.editorWorker
      return new Worker(mod, { type: 'module' })
    },
  }

  loader.config({ monaco })

  const container = document.getElementById('root')
  const root = createRoot(container!)
  root.render(
    <React.StrictMode>
      <App />
    </React.StrictMode>,
  )
  ```

- [ ] **Step 3: 替换 `tsconfig.json`**

  ```json
  {
    "compilerOptions": {
      "target": "ESNext",
      "useDefineForClassFields": true,
      "lib": ["DOM", "DOM.Iterable", "ESNext"],
      "allowJs": false,
      "skipLibCheck": true,
      "esModuleInterop": true,
      "allowSyntheticDefaultImports": true,
      "strict": true,
      "forceConsistentCasingInFileNames": true,
      "module": "ESNext",
      "moduleResolution": "Bundler",
      "resolveJsonModule": true,
      "isolatedModules": true,
      "noEmit": true,
      "jsx": "react-jsx",
      "types": ["vite/client"]
    },
    "include": ["src", "wailsjs"]
  }
  ```

- [ ] **Step 4: 安装依赖并验证构建**

  Run: `cd client/desktop/frontend && npm install && npm run build`
  Expected: 构建通过（`tsc && vite build`）

- [ ] **Step 5: Commit**

  ```bash
  git add client/desktop/frontend/package.json client/desktop/frontend/package-lock.json client/desktop/frontend/vite.config.ts client/desktop/frontend/tsconfig.json client/desktop/frontend/src/main.tsx client/desktop/frontend/src/App.tsx
  git commit -m "feat(desktop): upgrade frontend to react19 monaco and align toolchain with web"
  ```

  > `App.tsx` 的替换在 Task 11 完成，本 Task 先保留最小可编译入口（render `<App/>`，App 暂时渲染空壳或 Welcome 占位）。

---

### Task 11: 前端 api/client + stores（gateway/workspace/git）

**Files:**
- Create: `client/desktop/frontend/src/api/client.ts`
- Create: `client/desktop/frontend/src/api/workspaces.ts`
- Create: `client/desktop/frontend/src/stores/gateway.ts`
- Create: `client/desktop/frontend/src/stores/workspace.ts`
- Create: `client/desktop/frontend/src/stores/git.ts`

**Interfaces:**
- Consumes: Wails 绑定 `window.go.main.App.GetGatewayConfig`（Task 9 生成后位于 `frontend/wailsjs/go/main/App`）
- Produces:
  ```ts
  // stores/gateway.ts
  export interface GatewayConfig { baseURL: string; gatewayToken: string }
  export const useGatewayStore = create<{...}>(...)
  export async function initGateway(): Promise<void>
  // api/client.ts
  export class ApiError extends Error { status: number; offline?: boolean; cached?: unknown }
  export async function apiRequest<T>(path, options?, serverId?): Promise<T>
  // api/workspaces.ts
  export interface Workspace { id: string; name: string; path: string; remote_url?: string }
  export async function listWorkspaces(): Promise<Workspace[]>
  export async function createWorkspace(input): Promise<Workspace>
  export async function getTree(wsId): Promise<FileNode>
  export async function readFile(wsId, path): Promise<FileContent>
  export async function writeFile(wsId, path, content): Promise<WriteResult>
  export async function gitStatus(wsId): Promise<GitStatus>
  export async function gitAdd(wsId, paths): Promise<void>
  export async function gitCommit(wsId, message): Promise<void>
  ```

- [ ] **Step 1: 写 `api/client.ts`（移除 web 的 Authorization 注入）**

  ```ts
  import { useGatewayStore } from '../stores/gateway';

  export class ApiError extends Error {
    status: number;
    offline?: boolean;
    cached?: unknown;
    code?: string;
    constructor(status: number, message: string, opts?: { offline?: boolean; cached?: unknown; code?: string }) {
      super(message);
      this.name = 'ApiError';
      this.status = status;
      this.offline = opts?.offline;
      this.cached = opts?.cached;
      this.code = opts?.code;
    }
  }

  export async function apiRequest<T>(
    path: string,
    options: RequestInit = {},
    _serverId?: string,
  ): Promise<T> {
    const { baseURL, gatewayToken } = useGatewayStore.getState();
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      'X-Gateway-Token': gatewayToken,
      ...(options.headers as Record<string, string>),
    };
    const res = await fetch(`${baseURL}${path}`, { ...options, headers });

    if (!res.ok) {
      let message = res.statusText;
      let code: string | undefined;
      let offline: boolean | undefined;
      let cached: unknown;
      try {
        const json = await res.json();
        message = json.error?.message || json.detail || message;
        code = json.error?.code;
        offline = json.error?.offline;
        cached = json.error?.cached;
      } catch {
        /* keep statusText */
      }
      throw new ApiError(res.status, message, { offline, cached, code });
    }

    if (res.status === 204) return undefined as T;
    return res.json() as Promise<T>;
  }
  ```

- [ ] **Step 2: 写 `stores/gateway.ts`**

  ```ts
  import { create } from 'zustand';

  export interface GatewayConfig {
    baseURL: string;
    gatewayToken: string;
  }

  interface GatewayState {
    config: GatewayConfig | null;
    ready: boolean;
    setConfig: (c: GatewayConfig) => void;
  }

  export const useGatewayStore = create<GatewayState>((set) => ({
    config: null,
    ready: false,
    setConfig: (c) => set({ config: c, ready: true }),
  }));

  export async function initGateway(): Promise<void> {
    // window.go.main.App 由 Wails 生成，Task 9 之后存在。
    const cfg = await window.go.main.App.GetGatewayConfig();
    useGatewayStore.getState().setConfig(cfg);
  }
  ```

- [ ] **Step 3: 写 `api/workspaces.ts` 与剩余 stores**

  ```ts
  import { apiRequest } from './client';

  export interface Workspace {
    id: string;
    name: string;
    path: string;
    remote_url?: string;
  }

  export interface FileNode {
    name: string;
    path: string;
    is_dir: boolean;
    children?: FileNode[];
  }

  export interface FileContent {
    content: string;
    binary: boolean;
    truncated: boolean;
    size: number;
  }

  export interface WriteResult { lines: number; bytes: number }

  export interface GitStatus {
    branch: string;
    ahead: number;
    behind: number;
    staged: Array<{ x: string; y: string; path: string }>;
    modified: Array<{ x: string; y: string; path: string }>;
    untracked: string[];
  }

  export const listWorkspaces = () =>
    apiRequest<{ items: Workspace[] }>('/api/local/workspaces').then((r) => r.items);

  export const createWorkspace = (input: { name: string; path: string; url?: string; clone?: boolean }) =>
    apiRequest<Workspace>('/api/local/workspaces', { method: 'POST', body: JSON.stringify(input) });

  export const getTree = (wsId: string) =>
    apiRequest<FileNode>(`/api/local/workspaces/${wsId}/tree`);

  export const readFile = (wsId: string, path: string) =>
    apiRequest<FileContent>(`/api/local/workspaces/${wsId}/file?path=${encodeURIComponent(path)}`);

  export const writeFile = (wsId: string, path: string, content: string) =>
    apiRequest<WriteResult>(`/api/local/workspaces/${wsId}/file`, {
      method: 'PUT',
      body: JSON.stringify({ path, content }),
    });

  export const gitStatus = (wsId: string) =>
    apiRequest<GitStatus>(`/api/local/workspaces/${wsId}/git/status`, { method: 'POST' });

  export const gitAdd = (wsId: string, paths: string[]) =>
    apiRequest<{ ok: boolean }>(`/api/local/workspaces/${wsId}/git/add`, {
      method: 'POST', body: JSON.stringify({ paths }),
    });

  export const gitCommit = (wsId: string, message: string) =>
    apiRequest<{ ok: boolean }>(`/api/local/workspaces/${wsId}/git/commit`, {
      method: 'POST', body: JSON.stringify({ message }),
    });
  ```

  ```ts
  // stores/workspace.ts
  import { create } from 'zustand';
  import type { Workspace } from '../api/workspaces';

  interface WorkspaceState {
    workspaces: Workspace[];
    current: Workspace | null;
    setWorkspaces: (list: Workspace[]) => void;
    setCurrent: (ws: Workspace | null) => void;
  }

  export const useWorkspaceStore = create<WorkspaceState>((set) => ({
    workspaces: [],
    current: null,
    setWorkspaces: (list) => set({ workspaces: list }),
    setCurrent: (ws) => set({ current: ws }),
  }));
  ```

  ```ts
  // stores/git.ts
  import { create } from 'zustand';
  import type { GitStatus } from '../api/workspaces';

  interface GitState {
    status: GitStatus | null;
    setStatus: (s: GitStatus | null) => void;
  }

  export const useGitStore = create<GitState>((set) => ({
    status: null,
    setStatus: (s) => set({ status: s }),
  }));
  ```

- [ ] **Step 4: 类型检查**

  Run: `cd client/desktop/frontend && npm run build`
  Expected: 通过（Task 9 后 `window.go.main.App.GetGatewayConfig` 已由 Wails 生成绑定，类型存在）

- [ ] **Step 5: Commit**

  ```bash
  git add client/desktop/frontend/src/api client/desktop/frontend/src/stores
  git commit -m "feat(desktop): add gateway api client and workspace git stores"
  ```

---

### Task 12: 前端 IdeShell + Welcome + Workspace 视图（Explorer/Monaco/GitPanel）+ Settings

**Files:**
- Create: `client/desktop/frontend/src/styles/desktop.css`
- Create: `client/desktop/frontend/src/layouts/IdeShell.tsx`
- Create: `client/desktop/frontend/src/views/Welcome.tsx`
- Create: `client/desktop/frontend/src/views/workspace/ExplorerPanel.tsx`
- Create: `client/desktop/frontend/src/views/workspace/EditorTabs.tsx`
- Create: `client/desktop/frontend/src/views/workspace/GitPanel.tsx`
- Create: `client/desktop/frontend/src/views/Settings.tsx`
- Modify: `client/desktop/frontend/src/App.tsx`

**Interfaces:**
- Consumes: `useGatewayStore`、`useWorkspaceStore`、`useGitStore`、`api/workspaces.ts`（Task 11）
- Produces: 可运行的 IDE 界面（Welcome → 打开目录/clone → IdeShell 编辑 → GitPanel 提交）

- [ ] **Step 1: 重写 `App.tsx`（Welcome/IdeShell 切换 + 网关初始化）**

  ```tsx
  import { useEffect, useState } from 'react';
  import { Button } from 'antd';
  import { initGateway, useGatewayStore } from './stores/gateway';
  import { useWorkspaceStore } from './stores/workspace';
  import { listWorkspaces } from './api/workspaces';
  import Welcome from './views/Welcome';
  import IdeShell from './layouts/IdeShell';
  import './styles/desktop.css';

  export default function App() {
    const ready = useGatewayStore((s) => s.ready);
    const current = useWorkspaceStore((s) => s.current);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
      initGateway()
        .then(() => listWorkspaces())
        .then((list) => useWorkspaceStore.getState().setWorkspaces(list))
        .catch((e) => setError(String(e)));
    }, []);

    if (error) {
      return (
        <div style={{ padding: 24 }}>
          <div>网关初始化失败：{error}</div>
          <Button onClick={() => window.location.reload()}>重试</Button>
        </div>
      );
    }

    if (!ready) return <div style={{ padding: 24 }}>正在连接本地网关…</div>;

    return current ? <IdeShell workspace={current} /> : <Welcome />;
  }
  ```

- [ ] **Step 2: 写 `views/Welcome.tsx`**

  ```tsx
  import { useState } from 'react';
  import { Button, Card, Empty, Input, List, Space } from 'antd';
  import { FolderOpenOutlined } from '@ant-design/icons';
  import { createWorkspace, listWorkspaces, Workspace } from '../api/workspaces';
  import { useWorkspaceStore } from '../stores/workspace';

  declare global {
    interface Window {
      go?: {
        main: { App: { OpenFolderDialog: () => Promise<string> } };
      };
    }
  }

  export default function Welcome() {
    const workspaces = useWorkspaceStore((s) => s.workspaces);
    const setWorkspaces = useWorkspaceStore((s) => s.setWorkspaces);
    const setCurrent = useWorkspaceStore((s) => s.setCurrent);
    const [url, setUrl] = useState('');
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const openFolder = async () => {
      const dir = await window.go?.main.App.OpenFolderDialog();
      if (!dir) return;
      setBusy(true);
      try {
        await createWorkspace({ name: dir.split(/[\\/]/).pop() ?? 'ws', path: dir });
        setWorkspaces(await listWorkspaces());
      } catch (e) {
        setError(String(e));
      } finally {
        setBusy(false);
      }
    };

    const clone = async () => {
      if (!url.trim()) return;
      setBusy(true);
      try {
        const name = url.split('/').pop()?.replace(/\.git$/, '') ?? 'repo';
        await createWorkspace({ name, path: '', url: url.trim(), clone: true });
        setWorkspaces(await listWorkspaces());
        setUrl('');
      } catch (e) {
        setError(String(e));
      } finally {
        setBusy(false);
      }
    };

    return (
      <div className="welcome">
        <h2>欢迎使用 Perseus Desktop</h2>
        <Space direction="vertical" size="middle" style={{ width: 520 }}>
          <Card title="打开本地目录">
            <Button icon={<FolderOpenOutlined />} loading={busy} onClick={openFolder}>
              选择文件夹
            </Button>
          </Card>
          <Card title="Clone 仓库（手动 URL）">
            <Space.Compact style={{ width: '100%' }}>
              <Input
                placeholder="https://server/owner/repo.git 或 git@host:owner/repo.git"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                onPressEnter={clone}
              />
              <Button type="primary" loading={busy} onClick={clone}>
                Clone
              </Button>
            </Space.Compact>
          </Card>
          {error && <div className="error-text">{error}</div>}
          <Card title="最近工作区">
            {workspaces.length === 0 ? (
              <Empty description="还没有工作区" />
            ) : (
              <List
                dataSource={workspaces}
                renderItem={(ws: Workspace) => (
                  <List.Item actions={[<Button size="small" onClick={() => setCurrent(ws)}>打开</Button>]}>
                    {ws.name} <span className="muted">{ws.path}</span>
                  </List.Item>
                )}
              />
            )}
          </Card>
        </Space>
      </div>
    );
  }
  ```

- [ ] **Step 3: 写 `layouts/IdeShell.tsx`（四段式布局 + 状态栏）**

  ```tsx
  import { useState } from 'react';
  import { Workspace } from '../api/workspaces';
  import ExplorerPanel from '../views/workspace/ExplorerPanel';
  import EditorTabs from '../views/workspace/EditorTabs';
  import GitPanel from '../views/workspace/GitPanel';
  import { useGatewayStore } from '../stores/gateway';

  export default function IdeShell({ workspace }: { workspace: Workspace }) {
    const baseURL = useGatewayStore((s) => s.config?.baseURL);
    const [view, setView] = useState<'explorer' | 'git'>('explorer');
    const [openPath, setOpenPath] = useState<string | null>(null);

    return (
      <div className="ide">
        <nav className="activity-bar">
          <button className={view === 'explorer' ? 'active' : ''} onClick={() => setView('explorer')}>📁</button>
          <button className={view === 'git' ? 'active' : ''} onClick={() => setView('git')}>⑂</button>
        </nav>
        <aside className="sidebar">
          {view === 'explorer' && <ExplorerPanel workspaceId={workspace.id} onOpen={setOpenPath} />}
          {view === 'git' && <GitPanel workspaceId={workspace.id} />}
        </aside>
        <main className="editor-area">
          <EditorTabs workspaceId={workspace.id} openPath={openPath} />
        </main>
        <footer className="status-bar">
          <span>网关: {baseURL ?? '…'}</span>
        </footer>
      </div>
    );
  }
  ```

- [ ] **Step 4: 写 `ExplorerPanel.tsx`**

  ```tsx
  import { useEffect, useState } from 'react';
  import { Tree } from 'antd';
  import type { TreeDataNode } from 'antd';
  import { getTree, FileNode } from '../../api/workspaces';

  function toTreeData(node: FileNode): TreeDataNode {
    return {
      key: node.path,
      title: node.name,
      isLeaf: !node.is_dir,
      children: node.is_dir ? (node.children ?? []).map(toTreeData) : undefined,
    };
  }

  export default function ExplorerPanel({ workspaceId, onOpen }: { workspaceId: string; onOpen: (p: string) => void }) {
    const [data, setData] = useState<TreeDataNode[]>([]);

    useEffect(() => {
      getTree(workspaceId)
        .then((root) => setData((root.children ?? []).map(toTreeData)))
        .catch(console.error);
    }, [workspaceId]);

    return <Tree treeData={data} onSelect={(_, info) => onOpen(String(info.node.key))} defaultExpandAll />;
  }
  ```

- [ ] **Step 5: 写 `EditorTabs.tsx`（Monaco 标签页 + 保存 + 只读）**

  ```tsx
  import { useEffect, useMemo, useState } from 'react';
  import Editor from '@monaco-editor/react';
  import { readFile, writeFile, FileContent } from '../../api/workspaces';

  export default function EditorTabs({ workspaceId, openPath }: { workspaceId: string; openPath: string | null }) {
    const [current, setCurrent] = useState<string | null>(null);
    const [content, setContent] = useState<FileContent | null>(null);
    const [dirty, setDirty] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
      if (!openPath) return;
      setCurrent(openPath);
      readFile(workspaceId, openPath)
        .then((fc) => {
          setContent(fc);
          setDirty(false);
        })
        .catch((e) => setError(String(e)));
    }, [workspaceId, openPath]);

    const language = useMemo(() => guessLang(current ?? ''), [current]);

    const save = async () => {
      if (!current || !content || content.binary) return;
      try {
        await writeFile(workspaceId, current, content.content);
        setDirty(false);
      } catch (e) {
        setError(String(e));
      }
    };

    if (error) return <div className="error-text">{error}</div>;
    if (!current || !content) return <div className="empty-editor">选择左侧文件开始编辑</div>;

    if (content.binary) {
      return <div className="empty-editor">二进制文件（{content.size} bytes）不可编辑</div>;
    }

    return (
      <div className="editor-tab">
        <div className="tab-bar">
          <span className="tab-title">{current}{dirty ? ' ●' : ''}</span>
          <span className="tab-actions">
            {content.truncated && <span className="warn">文件过大，仅读入前 2MB</span>}
            <button disabled={!dirty} onClick={save}>保存</button>
          </span>
        </div>
        <Editor
          height="100%"
          language={language}
          value={content.content}
          onChange={(v) => {
            setContent((c) => (c ? { ...c, content: v ?? '' } : c));
            setDirty(true);
          }}
          options={{ readOnly: content.truncated, automaticLayout: true }}
        />
      </div>
    );
  }

  function guessLang(path: string): string {
    const ext = path.split('.').pop()?.toLowerCase() ?? '';
    const map: Record<string, string> = {
      ts: 'typescript', tsx: 'typescript', js: 'javascript', jsx: 'javascript',
      py: 'python', json: 'json', md: 'markdown', css: 'css', html: 'html',
    };
    return map[ext] ?? 'plaintext';
  }
  ```

- [ ] **Step 6: 写 `GitPanel.tsx`**

  ```tsx
  import { useEffect, useState } from 'react';
  import { Button, Input, List, Checkbox, Space } from 'antd';
  import { gitStatus, gitAdd, gitCommit, GitStatus } from '../../api/workspaces';
  import { useGitStore } from '../../stores/git';

  export default function GitPanel({ workspaceId }: { workspaceId: string }) {
    const status = useGitStore((s) => s.status);
    const setStatus = useGitStore((s) => s.setStatus);
    const [message, setMessage] = useState('');
    const [selected, setSelected] = useState<Set<string>>(new Set());

    const refresh = async () => {
      const s = await gitStatus(workspaceId);
      setStatus(s);
      if (!s) return;
      const all = [...s.modified.map((m) => m.path), ...s.untracked];
      setSelected(new Set(all));
    };

    useEffect(() => { refresh().catch(console.error); }, [workspaceId]);

    const stage = async () => {
      await gitAdd(workspaceId, [...selected]);
      await refresh();
    };

    const commit = async () => {
      await gitCommit(workspaceId, message);
      setMessage('');
      await refresh();
    };

    if (!status) return <div>加载状态…</div>;

    return (
      <div className="git-panel">
        <div className="git-branch">分支: {status.branch} ({status.ahead}↑ {status.behind}↓)</div>
        <Checkbox.Group
          value={[...selected]}
          onChange={(vals) => setSelected(new Set(vals as string[]))}
        >
          <List
            size="small"
            dataSource={[...status.modified.map((m) => m.path), ...status.untracked]}
            renderItem={(p) => (
              <List.Item><Checkbox value={p}>{p}</Checkbox></List.Item>
            )}
          />
        </Checkbox.Group>
        <Input.TextArea rows={3} placeholder="提交信息" value={message} onChange={(e) => setMessage(e.target.value)} />
        <Space>
          <Button size="small" onClick={stage}>暂存</Button>
          <Button size="small" type="primary" disabled={!message.trim()} onClick={commit}>提交</Button>
        </Space>
      </div>
    );
  }
  ```

  > antd v6 中 `Checkbox.Group` 的 `onChange` 值为数组。

- [ ] **Step 7: 写 `Settings.tsx`（占位）与 `desktop.css`**

  ```tsx
  import { Card } from 'antd';
  import { useGatewayStore } from '../stores/gateway';

  export default function Settings() {
    const config = useGatewayStore((s) => s.config);
    return (
      <Card title="设置" style={{ margin: 16 }}>
        <p>网关地址: {config?.baseURL}</p>
        <p>会话 token: {config?.gatewayToken ? '已生成（仅内存）' : '未生成'}</p>
        <p className="muted">Phase 1 占位。数据目录持久化、主题、SSH 密钥等在后续阶段实现。</p>
      </Card>
    );
  }
  ```

  ```css
  /* styles/desktop.css */
  * { box-sizing: border-box; }
  html, body, #root { height: 100%; margin: 0; }
  body {
    background: #0d1117;
    color: #c9d1d9;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  }
  .ide { display: flex; flex-direction: row; height: 100vh; }
  .activity-bar {
    display: flex; flex-direction: column; width: 48px;
    background: #010409; border-right: 1px solid #21262d; padding-top: 8px;
  }
  .activity-bar button {
    background: none; border: none; color: #8b949e; font-size: 20px;
    padding: 10px; cursor: pointer;
  }
  .activity-bar button.active { color: #58a6ff; }
  .sidebar {
    width: 280px; background: #0d1117; border-right: 1px solid #21262d;
    overflow: auto; padding: 8px;
  }
  .editor-area { flex: 1; display: flex; flex-direction: column; background: #010409; }
  .editor-tab { flex: 1; display: flex; flex-direction: column; }
  .tab-bar {
    display: flex; justify-content: space-between; align-items: center;
    background: #161b22; border-bottom: 1px solid #21262d; padding: 6px 10px;
  }
  .status-bar {
    background: #161b22; border-top: 1px solid #21262d; padding: 4px 12px;
    font-size: 12px; color: #8b949e;
  }
  .welcome { padding: 48px 24px; display: flex; flex-direction: column; align-items: center; gap: 16px; }
  .muted { color: #8b949e; font-size: 12px; margin-left: 8px; }
  .error-text { color: #f85149; padding: 8px; }
  .warn { color: #d29922; font-size: 12px; margin-right: 8px; }
  .empty-editor { padding: 32px; color: #8b949e; }
  .git-panel { padding: 8px; display: flex; flex-direction: column; gap: 8px; }
  .git-branch { font-size: 13px; font-weight: 600; }
  ```

- [ ] **Step 8: 构建验证**

  Run: `cd client/desktop/frontend && npm run build`
  Expected: 构建通过

- [ ] **Step 9: 冒烟测试（手工验收清单）**

  Run: `cd client/desktop && wails dev`
  验收：
  1. 应用启动后进入 Welcome 页，状态栏无错误
  2. "选择文件夹"打开本地 git 仓库目录 → 进入 IdeShell，Explorer 显示文件树（无 .git/node_modules）
  3. 点击文件 → Monaco 打开，修改后保存按钮可用，保存成功
  4. 左侧 Git 面板显示分支与变更；选中文件→暂存→填信息→提交成功
  5. 用任意公开仓库 URL 执行 Clone → 工作区出现，文件树加载

- [ ] **Step 10: Commit**

  ```bash
  git add client/desktop/frontend/src
  git commit -m "feat(desktop): add ide shell welcome explorer editor and git panel"
  ```

---

### Task 13: 端到端验证 + 计划收尾

**Files:**
- Modify: `client/desktop/frontend/wailsjs/...`（Task 9 之后 `wails dev` 自动重新生成绑定，提交生成结果）

- [ ] **Step 1: 全量 Go 测试**

  Run: `cd client/desktop && go vet ./... && go test ./... -v`
  Expected: 全部 PASS，`go vet` 无告警

- [ ] **Step 2: 前端类型与构建**

  Run: `cd client/desktop/frontend && npm run build`
  Expected: 通过

- [ ] **Step 3: 运行 `wails dev` 冒烟（Task 12 Step 9 清单逐项通过）**

- [ ] **Step 4: 更新桌面端 README**

  修改 `client/desktop/README.md`，记录：
  - 架构一页图（Go 网关 + React 前端 + SQLite/keychain）
  - 开发命令：`wails dev` / `wails build`
  - Phase 1 功能范围与已知边界（内存网关 token、持久化路径、Phase 2 待办）

- [ ] **Step 5: Commit**

  ```bash
  git add client/desktop/README.md client/desktop/frontend/wailsjs
  git commit -m "docs(desktop): document phase1 architecture and dev workflow"
  ```

---

## 自审记录

- **Spec 覆盖**：Phase 1 全部条目均有 Task——Go 骨架(T1/T2/T7/T9)、gateway 安全(A/T7)、工作区添加目录+clone(C/T8)、Explorer 文件树+文件读写(T3/T8/T12)、Monaco 标签页/保存/只读/diff(T12)、git 基础操作(T4/T5/T6/T8)、IdeShell+Welcome+Settings(T12)、前端移除 Authorization(B/T11)。
- **占位符扫描**：Task 8 的 stub handler 为 T7 通过测试的最小实现，T8 全部替换为真实逻辑，无遗留 TODO。
- **类型一致性**：`store.Workspace`、`git.Credential`、`fs.FileNode`、`GatewayConfig`、`FileContent` 在各 Task 间签名一致；前端 `apiRequest(path, options, serverId?)` 第三参 Phase 1 未使用（serverId 作用域留待 Phase 2 代理），保持一致。
- **已知取舍**：`GitPanel` 的暂存按钮语义简化为"add 选中文件"；`push/pull` 通过 git/{op} 路由暴露但 Phase 1 前端未接 UI（凭据注入最小路径）。这两项在 Phase 2 完善。
