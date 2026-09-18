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
	mux.HandleFunc("POST /api/local/workspaces/{id}/rename", g.handleRenameFile)
	mux.HandleFunc("GET /api/local/workspaces/{id}/search", g.handleSearch)
	mux.HandleFunc("POST /api/local/workspaces/{id}/touch", g.handleTouchWorkspace)
	mux.HandleFunc("GET /api/local/workspaces/{id}/terminal", g.handleTerminal)
	mux.HandleFunc("GET /api/local/workspaces/{id}/lsp", g.handleLSP)
	// 服务器注册表
	mux.HandleFunc("GET /api/local/servers", g.handleListServers)
	mux.HandleFunc("POST /api/local/servers", g.handleRegisterServer)
	mux.HandleFunc("PUT /api/local/servers/{id}", g.handleUpdateServer)
	mux.HandleFunc("DELETE /api/local/servers/{id}", g.handleDeleteServer)
	mux.HandleFunc("GET /api/local/servers/{id}/health", g.handleServerHealth)
	mux.HandleFunc("POST /api/local/servers/{id}/refresh", g.handleRefreshServer)
	mux.HandleFunc("POST /api/local/servers/{id}/default", g.handleSetDefaultServer)
	// 通用反向代理（HTTP 与 WS 透传）
	mux.HandleFunc("GET /api/local/proxy/{serverId}/ws/{path...}", g.handleProxyWS)
	// 协作专用 WS 代理（Hocuspocus 首帧 token 注入，不能走通用 ?token= 透传）
	mux.HandleFunc("GET /api/local/proxy/{serverId}/collab", g.handleProxyCollab)
	for _, method := range []string{"GET", "POST", "PUT", "PATCH", "DELETE"} {
		mux.Handle(method+" /api/local/proxy/{serverId}/{path...}", http.HandlerFunc(g.handleProxy))
	}
	return g.withSecurity(mux)
}
