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
