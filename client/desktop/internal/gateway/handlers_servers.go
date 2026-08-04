package gateway

import (
	"encoding/json"
	"errors"
	"net/http"

	"desktop/internal/server"
)

type registerServerReq struct {
	Name       string `json:"name"`
	BaseURL    string `json:"base_url"`
	AuthMethod string `json:"auth_method"` // "password" | "token"
	Username   string `json:"username,omitempty"`
	Password   string `json:"password,omitempty"`
	Token      string `json:"token,omitempty"`
}

func (g *Gateway) handleListServers(w http.ResponseWriter, r *http.Request) {
	items, err := g.servers.List()
	if err != nil {
		writeError(w, http.StatusInternalServerError, "STORE_LIST", err.Error())
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"items": items})
}

func (g *Gateway) handleRegisterServer(w http.ResponseWriter, r *http.Request) {
	var req registerServerReq
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "BAD_REQUEST", err.Error())
		return
	}
	if req.Name == "" || req.BaseURL == "" || (req.AuthMethod != "password" && req.AuthMethod != "token") {
		writeError(w, http.StatusBadRequest, "BAD_REQUEST", "name, base_url and auth_method( password|token ) required")
		return
	}
	srv, err := g.servers.AddServer(server.AddInput{
		Name: req.Name, BaseURL: req.BaseURL, AuthMethod: req.AuthMethod,
		Username: req.Username, Password: req.Password, Token: req.Token,
	})
	if err != nil {
		if errors.Is(err, server.ErrLoginFailed) {
			writeError(w, http.StatusUnauthorized, "LOGIN_FAILED", err.Error())
			return
		}
		if errors.Is(err, server.ErrInvalidAuth) {
			writeError(w, http.StatusBadRequest, "BAD_REQUEST", err.Error())
			return
		}
		writeError(w, http.StatusInternalServerError, "SERVER_REGISTER", err.Error())
		return
	}
	_ = g.store.SetSetting("default_server_id", srv.ID)
	writeJSON(w, http.StatusOK, srv)
}

func (g *Gateway) handleDeleteServer(w http.ResponseWriter, r *http.Request) {
	id := r.PathValue("id")
	if err := g.servers.Delete(id); err != nil {
		writeError(w, http.StatusNotFound, "SERVER_NOT_FOUND", "server not found")
		return
	}
	writeJSON(w, http.StatusOK, map[string]bool{"ok": true})
}

func (g *Gateway) handleServerHealth(w http.ResponseWriter, r *http.Request) {
	id := r.PathValue("id")
	if _, err := g.servers.Get(id); err != nil {
		writeError(w, http.StatusNotFound, "SERVER_NOT_FOUND", "server not found")
		return
	}
	err := g.servers.Probe(id)
	srv, _ := g.servers.Get(id)
	code := http.StatusOK
	if err != nil {
		code = http.StatusServiceUnavailable
	}
	writeJSON(w, code, srv)
}

func (g *Gateway) handleRefreshServer(w http.ResponseWriter, r *http.Request) {
	id := r.PathValue("id")
	var req struct {
		Username string `json:"username"`
		Password string `json:"password"`
	}
	_ = json.NewDecoder(r.Body).Decode(&req)
	srv, err := g.servers.RefreshToken(id, req.Username, req.Password)
	if err != nil {
		if errors.Is(err, server.ErrLoginFailed) {
			writeError(w, http.StatusUnauthorized, "LOGIN_FAILED", err.Error())
			return
		}
		writeError(w, http.StatusInternalServerError, "SERVER_REFRESH", err.Error())
		return
	}
	writeJSON(w, http.StatusOK, srv)
}

func (g *Gateway) handleSetDefaultServer(w http.ResponseWriter, r *http.Request) {
	id := r.PathValue("id")
	if _, err := g.servers.Get(id); err != nil {
		writeError(w, http.StatusNotFound, "SERVER_NOT_FOUND", "server not found")
		return
	}
	_ = g.store.SetSetting("default_server_id", id)
	writeJSON(w, http.StatusOK, map[string]bool{"ok": true})
}