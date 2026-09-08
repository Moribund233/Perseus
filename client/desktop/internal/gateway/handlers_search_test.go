package gateway

import (
	"encoding/json"
	"os"
	"path/filepath"
	"testing"

	"desktop/internal/store"
)

func TestWorkspaceSearch(t *testing.T) {
	g, st := newTestGateway(t)
	wsRoot := t.TempDir()

	// 写几个待搜索文件
	write := func(name, content string) {
		p := filepath.Join(wsRoot, name)
		if err := os.MkdirAll(filepath.Dir(p), 0o755); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(p, []byte(content), 0o644); err != nil {
			t.Fatal(err)
		}
	}
	write("main.go", "package main\n\nfunc runFrobnicate() {}\n")
	write("lib/helper.ts", "export const frobnicate = () => 1;\nconst other = 2;\n")
	write("notes.md", "remember the Frobnicate plan\n")

	ws, err := st.CreateWorkspace(store.Workspace{Name: "test", Path: wsRoot})
	if err != nil {
		t.Fatal(err)
	}

	rr := authedReq(t, g, "GET", "/api/local/workspaces/"+ws.ID+"/search?q=frobnicate", nil)
	if rr.Code != 200 {
		t.Fatalf("search status = %d body=%s", rr.Code, rr.Body.String())
	}
	var resp searchResponse
	if err := json.NewDecoder(rr.Body).Decode(&resp); err != nil {
		t.Fatal(err)
	}
	if resp.Total != 3 {
		t.Fatalf("total = %d, want 3 (case-insensitive across files)", resp.Total)
	}
	files := map[string]bool{}
	for _, h := range resp.Results {
		files[h.File] = true
	}
	if !files["main.go"] || !files["lib/helper.ts"] || !files["notes.md"] {
		t.Fatalf("expected hits in all 3 files, got %v", files)
	}

	// 限定 path 搜索
	rr = authedReq(t, g, "GET", "/api/local/workspaces/"+ws.ID+"/search?q=frobnicate&path=lib", nil)
	if rr.Code != 200 {
		t.Fatalf("scoped search status = %d body=%s", rr.Code, rr.Body.String())
	}
	if err := json.NewDecoder(rr.Body).Decode(&resp); err != nil {
		t.Fatal(err)
	}
	if resp.Total != 1 || len(resp.Results) == 0 || resp.Results[0].File != "lib/helper.ts" {
		t.Fatalf("scoped search total=%d first=%s, want 1 lib/helper.ts", resp.Total, resp.Results[0].File)
	}

	// 缺少 q → 400
	rr = authedReq(t, g, "GET", "/api/local/workspaces/"+ws.ID+"/search", nil)
	if rr.Code != 400 {
		t.Fatalf("missing q status = %d, want 400", rr.Code)
	}
}

func TestWorkspaceSearchNotFound(t *testing.T) {
	g, _ := newTestGateway(t)
	rr := authedReq(t, g, "GET", "/api/local/workspaces/missing/search?q=x", nil)
	if rr.Code != 404 {
		t.Fatalf("status = %d, want 404", rr.Code)
	}
}