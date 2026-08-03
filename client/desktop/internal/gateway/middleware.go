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
		if r.URL.Path != "/api/local/config" && !g.validToken(r.Header.Get("X-Gateway-Token")) {
			http.Error(w, `{"error":{"code":"UNAUTHORIZED","message":"missing or invalid gateway token"}}`, http.StatusUnauthorized)
			return
		}
		next.ServeHTTP(w, r)
	})
}
