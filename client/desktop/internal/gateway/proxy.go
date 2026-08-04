package gateway

import (
	"encoding/json"
	"io"
	"net/http"
	"strings"
)

// hop-by-hop 头，不透传到上游，也不从上游透回。
var hopHeaders = []string{
	"Connection", "Proxy-Connection", "Keep-Alive",
	"Proxy-Authenticate", "Proxy-Authorization", "Te",
	"Trailer", "Transfer-Encoding", "Upgrade",
}

// handleProxy 通用反向代理：/api/local/proxy/{serverId}/{path...} → {baseURL}/{path}
// 注入服务器 token；处理离线语义与 GET LRU 缓存。
func (g *Gateway) handleProxy(w http.ResponseWriter, r *http.Request) {
	serverID := r.PathValue("serverId")
	path := r.PathValue("path")
	srv, err := g.servers.Get(serverID)
	if err != nil {
		writeError(w, http.StatusNotFound, "SERVER_NOT_FOUND", "server not found")
		return
	}
	tok, err := g.servers.Token(serverID)
	if err != nil || tok == "" {
		writeError(w, http.StatusUnauthorized, "AUTH_TOKEN_MISSING", "server token missing")
		return
	}

	upstream := strings.TrimRight(srv.BaseURL, "/") + "/" + path
	if r.URL.RawQuery != "" {
		upstream += "?" + r.URL.RawQuery
	}

	if r.Method == http.MethodGet {
		if reachable := g.tryProxy(w, r, upstream, tok); reachable {
			return
		}
		// 离线：回退缓存。
		if hit, ok := g.cache.get(proxyCacheKey(r)); ok {
			writeOffline(w, &hit)
			return
		}
		writeOffline(w, nil)
		return
	}

	// 写操作：不缓存，直接转发；离线返回 503。
	if reachable := g.tryProxy(w, r, upstream, tok); !reachable {
		writeOffline(w, nil)
	}
}

// proxyCacheKey 缓存键：serverId + path + 原始 query。
func proxyCacheKey(r *http.Request) string {
	return r.PathValue("serverId") + "\x00" + r.PathValue("path") + "\x00" + r.URL.RawQuery
}

// tryProxy 转发上游请求并写响应。返回是否可达；仅缓存 2xx GET。
func (g *Gateway) tryProxy(w http.ResponseWriter, r *http.Request, upstream, token string) bool {
	body := r.Body
	if body == nil {
		body = http.NoBody
	}
	req, err := http.NewRequestWithContext(r.Context(), r.Method, upstream, body)
	if err != nil {
		return false
	}
	req.Header = r.Header.Clone()
	req.Header.Del("X-Gateway-Token")
	for _, h := range hopHeaders {
		req.Header.Del(h)
	}
	req.Header.Set("Authorization", "Bearer "+token)

	resp, err := g.proxy.Do(req)
	if err != nil {
		return false
	}
	defer resp.Body.Close()

	data, err := io.ReadAll(resp.Body)
	if err != nil {
		return false
	}

	if r.Method == http.MethodGet && resp.StatusCode >= 200 && resp.StatusCode < 300 {
		g.cache.put(proxyCacheKey(r), cachedResponse{
			Status:  resp.StatusCode,
			Body:    data,
			Content: resp.Header.Get("Content-Type"),
		})
	}

	// 剥离 CORS 响应头，交还网关中间件设置（避免与本地白名单冲突）。
	for _, h := range []string{"Access-Control-Allow-Origin", "Access-Control-Allow-Headers", "Access-Control-Allow-Methods"} {
		resp.Header.Del(h)
	}
	for key, vals := range resp.Header {
		for _, v := range vals {
			if isHopHeader(key) {
				continue
			}
			w.Header().Add(key, v)
		}
	}
	w.WriteHeader(resp.StatusCode)
	_, _ = w.Write(data)
	return true
}

func isHopHeader(name string) bool {
	for _, h := range hopHeaders {
		if strings.EqualFold(h, name) {
			return true
		}
	}
	return false
}

// writeOffline 离线响应：cached 命中时透出上游原始 JSON 结构，未命中为 null。
func writeOffline(w http.ResponseWriter, cached *cachedResponse) {
	var c any
	if cached != nil {
		var parsed any
		if err := json.Unmarshal(cached.Body, &parsed); err == nil {
			c = parsed
		} else {
			c = string(cached.Body)
		}
	}
	writeJSON(w, http.StatusServiceUnavailable, map[string]any{
		"error":   ErrorBody{Code: "SERVER_OFFLINE", Message: "server unreachable"},
		"offline": true,
		"cached":  c,
	})
}