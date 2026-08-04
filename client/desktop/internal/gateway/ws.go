package gateway

import (
	"net/http"
	"net/url"
	"strings"
	"sync"
	"time"

	"github.com/gorilla/websocket"
)

var wsUpgrader = websocket.Upgrader{
	CheckOrigin:    func(r *http.Request) bool { return true }, // 已被网关中间件鉴权
	ReadBufferSize: 4096,
	WriteBufferSize: 4096,
}

// handleProxyWS WS 透传：/api/local/proxy/{serverId}/ws/{path...} → ws(s)://{baseURL}/ws/{path}?token=...
// 服务器 WS 认证用 query token，透传时附加服务器 token；断线指数退避重连（上限 5 次）。
func (g *Gateway) handleProxyWS(w http.ResponseWriter, r *http.Request) {
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
	upstream := wsEndpoint(srv.BaseURL, path, tok)

	clientConn, err := wsUpgrader.Upgrade(w, r, nil)
	if err != nil {
		return
	}
	defer clientConn.Close()

	tunnel := &wsTunnel{alive: true}
	defer tunnel.close()

	// 先建立首个上游连接，再启动读方向，避免写方向在 conn 就绪前发送。
	conn, ok := dialWS(upstream)
	if !ok {
		return
	}
	tunnel.set(conn)

	// 客户端 → 上游。
	go func() {
		defer tunnel.close()
		for {
			mt, p, err := clientConn.ReadMessage()
			if err != nil {
				return
			}
			if !tunnel.send(mt, p) {
				return
			}
		}
	}()

	// 上游 → 客户端，断线重连（指数退避，上限 5 次）。
	for {
		for {
			mt, p, err := conn.ReadMessage()
			if err != nil {
				break
			}
			if err := clientConn.WriteMessage(mt, p); err != nil {
				return
			}
		}
		conn.Close()
		tunnel.set(nil)
		if !tunnel.alive {
			return
		}
		conn, ok = dialWS(upstream)
		if !ok {
			return
		}
		tunnel.set(conn)
	}
}

// dialWS 拨号上游，失败时指数退避重试（200ms 起翻倍，上限 5 次）。
func dialWS(upstream string) (*websocket.Conn, bool) {
	backoff := 200 * time.Millisecond
	for i := 0; i < 5; i++ {
		conn, _, err := websocket.DefaultDialer.Dial(upstream, nil)
		if err == nil {
			return conn, true
		}
		time.Sleep(backoff)
		backoff *= 2
		if backoff > 5*time.Second {
			backoff = 5 * time.Second
		}
	}
	return nil, false
}

// wsTunnel 当前上游连接，受 mutex 保护，写方向重连时并发安全。
type wsTunnel struct {
	mu    sync.Mutex
	conn  *websocket.Conn
	alive bool
}

func (t *wsTunnel) set(conn *websocket.Conn) {
	t.mu.Lock()
	t.conn = conn
	t.mu.Unlock()
}

func (t *wsTunnel) send(mt int, p []byte) bool {
	t.mu.Lock()
	defer t.mu.Unlock()
	if t.conn == nil {
		return false
	}
	if err := t.conn.WriteMessage(mt, p); err != nil {
		_ = t.conn.Close()
		t.conn = nil
		return false
	}
	return true
}

func (t *wsTunnel) close() {
	t.mu.Lock()
	t.alive = false
	if t.conn != nil {
		_ = t.conn.Close()
	}
	t.mu.Unlock()
}

// wsEndpoint 把 baseURL + path + token 拼成服务器 WS 端点。
func wsEndpoint(baseURL, path, token string) string {
	u, err := url.Parse(baseURL)
	if err != nil {
		return ""
	}
	switch u.Scheme {
	case "https":
		u.Scheme = "wss"
	default:
		u.Scheme = "ws"
	}
	u.Path = "/ws/" + strings.TrimPrefix(path, "/")
	u.RawQuery = "token=" + url.QueryEscape(token)
	return u.String()
}