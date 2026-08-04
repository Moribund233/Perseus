package gateway

import (
	"bytes"
	"encoding/json"
	"net/http/httptest"
	"os"
	"os/exec"
	"path/filepath"
	"testing"

	"desktop/internal/git"
	"desktop/internal/server"
	"desktop/internal/store"
)

func newTestGateway(t *testing.T) (*Gateway, *store.Store) {
	t.Helper()
	st, _ := store.New("")
	g := New(Config{
		Store:   st,
		Git:     git.NewGit(&store.FakeKeychain{M: map[string]string{}}),
		Servers: server.NewRegistry(st, &store.FakeKeychain{M: map[string]string{}}),
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
