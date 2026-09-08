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
		//
		// 浏览器 WebSocket 无法携带自定义 header（X-Gateway-Token 受限），因此 WS 透传
		// 允许将网关 token 以查询参数 _token 传递。仅对 WS upgrade 请求生效，避免削弱 REST 鉴权。
		valid := g.validToken(r.Header.Get("X-Gateway-Token"))
		if !valid && isWebSocketUpgrade(r) {
			valid = g.validToken(r.URL.Query().Get("_token"))
		}
		if r.URL.Path != "/api/local/config" && !valid {
			http.Error(w, `{"error":{"code":"UNAUTHORIZED","message":"missing or invalid gateway token"}}`, http.StatusUnauthorized)
			return
		}
		next.ServeHTTP(w, r)
	})
}
