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
