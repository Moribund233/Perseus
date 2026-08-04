package gateway

import "net/http"

func (g *Gateway) buildRouter() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /api/local/config", g.handleConfig)
	// 工作区路由
	mux.HandleFunc("GET /api/local/workspaces", g.handleListWorkspaces)
	mux.HandleFunc("POST /api/local/workspaces", g.handleCreateWorkspace)
	mux.HandleFunc("GET /api/local/workspaces/{id}", g.handleGetWorkspace)
	mux.HandleFunc("DELETE /api/local/workspaces/{id}", g.handleDeleteWorkspace)
	mux.HandleFunc("POST /api/local/workspaces/{id}/clone", g.handleCloneWorkspace)
	mux.HandleFunc("POST /api/local/workspaces/{id}/git/{op}", g.handleGitOp)
	mux.HandleFunc("GET /api/local/workspaces/{id}/tree", g.handleTree)
	mux.HandleFunc("GET /api/local/workspaces/{id}/file", g.handleReadFile)
	mux.HandleFunc("PUT /api/local/workspaces/{id}/file", g.handleWriteFile)
	// 服务器注册表
	mux.HandleFunc("GET /api/local/servers", g.handleListServers)
	mux.HandleFunc("POST /api/local/servers", g.handleRegisterServer)
	mux.HandleFunc("DELETE /api/local/servers/{id}", g.handleDeleteServer)
	mux.HandleFunc("GET /api/local/servers/{id}/health", g.handleServerHealth)
	mux.HandleFunc("POST /api/local/servers/{id}/refresh", g.handleRefreshServer)
	mux.HandleFunc("POST /api/local/servers/{id}/default", g.handleSetDefaultServer)
	// 通用反向代理（HTTP 与 WS 透传）
	mux.HandleFunc("GET /api/local/proxy/{serverId}/ws/{path...}", g.handleProxyWS)
	for _, method := range []string{"GET", "POST", "PUT", "PATCH", "DELETE"} {
		mux.Handle(method+" /api/local/proxy/{serverId}/{path...}", http.HandlerFunc(g.handleProxy))
	}
	return g.withSecurity(mux)
}
