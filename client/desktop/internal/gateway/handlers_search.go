package gateway

import (
	"bufio"
	"net/http"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"sync"
)

// searchHit 一条命中记录。
type searchHit struct {
	File    string `json:"file"`
	Line    int    `json:"line"`
	Content string `json:"content"`
}

// searchResponse 本地工作区搜索响应。
type searchResponse struct {
	Query     string      `json:"query"`
	Path      string      `json:"path"`
	Results   []searchHit `json:"results"`
	Total     int         `json:"total"`
	Truncated bool        `json:"truncated"`
}

// defaultIgnoreDirs 搜索时跳过的常见目录。
var defaultIgnoreDirs = map[string]bool{
	".git":         true,
	"node_modules": true,
	"vendor":       true,
	"dist":         true,
	"build":        true,
	"target":       true,
	"__pycache__":  true,
	".venv":        true,
}

// searchCtx 搜索上下文，map/reduce 线程安全。
type searchCtx struct {
	root    string
	pat     string
	max     int
	mu      sync.Mutex
	results []searchHit
	total   int
}

// handleSearch 本地工作区搜索：GET /api/local/workspaces/{id}/search?q=&path=&max_results=
func (g *Gateway) handleSearch(w http.ResponseWriter, r *http.Request) {
	ws, err := g.store.GetWorkspace(r.PathValue("id"))
	if err != nil {
		writeError(w, http.StatusNotFound, "STORE_NOT_FOUND", "workspace not found")
		return
	}
	q := strings.TrimSpace(r.URL.Query().Get("q"))
	if q == "" {
		writeError(w, http.StatusBadRequest, "BAD_REQUEST", "q query param required")
		return
	}
	max := 200
	if v := r.URL.Query().Get("max_results"); v != "" {
		if n, e := strconv.Atoi(v); e == nil && n > 0 {
			max = n
		}
	}
	root := ws.Path
	searchRoot := root
	if sub := strings.TrimPrefix(r.URL.Query().Get("path"), "/"); sub != "" {
		searchRoot = filepath.Join(root, filepath.FromSlash(sub))
	}

	ctx := &searchCtx{root: root, pat: strings.ToLower(q), max: max}
	ctx.run(searchRoot)

	results := ctx.results
	sort.Slice(results, func(i, j int) bool {
		if results[i].File == results[j].File {
			return results[i].Line < results[j].Line
		}
		return results[i].File < results[j].File
	})
	truncated := ctx.total > max
	if len(results) > max {
		results = results[:max]
	}
	writeJSON(w, http.StatusOK, searchResponse{
		Query: q, Path: searchRoot, Results: results,
		Total: ctx.total, Truncated: truncated,
	})
}

func (c *searchCtx) run(dir string) {
	_ = filepath.WalkDir(dir, func(path string, d os.DirEntry, err error) error {
		if err != nil {
			return nil
		}
		name := d.Name()
		if d.IsDir() {
			if path != c.root && (strings.HasPrefix(name, ".") || defaultIgnoreDirs[name]) {
				return filepath.SkipDir
			}
			return nil
		}
		if !isTextExt(name) {
			return nil
		}
		c.mu.Lock()
		done := c.total >= c.max
		c.mu.Unlock()
		if done {
			return filepath.SkipAll
		}
		c.scanFile(path)
		return nil
	})
}

// isTextExt 是否属于常见文本/源码扩展名（含无扩展名文件）。
func isTextExt(name string) bool {
	switch strings.ToLower(filepath.Ext(name)) {
	case ".go", ".ts", ".tsx", ".js", ".jsx", ".py", ".rs", ".java", ".kt", ".c", ".h",
		".cpp", ".hpp", ".cs", ".rb", ".php", ".sh", ".ps1", ".yml", ".yaml", ".json",
		".toml", ".md", ".txt", ".html", ".css", ".scss", ".sql", ".xml", ".conf", ".ini",
		".env", ".properties":
		return true
	case "":
		return true
	default:
		return false
	}
}

func (c *searchCtx) scanFile(path string) {
	f, err := os.Open(path)
	if err != nil {
		return
	}
	defer f.Close()
	rel, _ := filepath.Rel(c.root, path)
	rel = filepath.ToSlash(rel)
	sc := bufio.NewScanner(f)
	sc.Buffer(make([]byte, 1024*1024), 1024*1024)
	lineNo := 0
	for sc.Scan() {
		lineNo++
		if strings.Contains(strings.ToLower(sc.Text()), c.pat) {
			c.mu.Lock()
			c.total++
			if len(c.results) < c.max {
				c.results = append(c.results, searchHit{File: rel, Line: lineNo, Content: strings.TrimSpace(sc.Text())})
			}
			c.mu.Unlock()
		}
	}
}