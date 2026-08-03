package gateway

import (
	"encoding/json"
	"net/http"
	"os"
	"path/filepath"
	"strings"

	"desktop/internal/git"
	"desktop/internal/store"
)

type createWorkspaceReq struct {
	Name  string        `json:"name"`
	Path  string        `json:"path"`
	URL   string        `json:"url,omitempty"`
	Clone bool          `json:"clone,omitempty"`
	Cred  git.Credential `json:"credential,omitempty"`
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
		var err error
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
	base, err := os.UserConfigDir()
	if err != nil {
		base = os.TempDir()
	}
	return filepath.Join(base, "perseus", "workspaces", name)
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
