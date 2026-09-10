package gateway

import (
	"bytes"
	"net/http"
	"net/url"
	"strings"
	"sync"

	"github.com/gorilla/websocket"
)

// Hocuspocus 消息类型常量（@hocuspocus/common）。
const (
	collabMessageTypeAuth  = 2 // MessageType.Authentication
	collabAuthSubTypeToken = 0 // AuthMessageType.Token
)

// collabEndpoint 把 baseURL 拼成 collab-gateway WS 端点（服务器 nginx 分流 /ws/collab → collab:4444）。
// 与 chat 的 ?token= 透传不同：Hocuspocus 鉴权在首帧内（lib0 二进制），URL token 无效。
func collabEndpoint(baseURL string) string {
	u, err := url.Parse(baseURL)
	if err != nil {
		return ""
	}
	if strings.EqualFold(u.Scheme, "https") {
		u.Scheme = "wss"
	} else {
		u.Scheme = "ws"
	}
	u.Path = "/ws/collab"
	u.RawQuery = ""
	return u.String()
}

// rewriteCollabAuthFrame 截获 Hocuspocus AuthenticationMessage 并把 token 字段替换为
// 密钥库 app access token。仅当帧形如 Auth/Token 时改写并重算全部 varint 长度前缀；
// 其余帧原样返回（changed=false，透明转发）。
func rewriteCollabAuthFrame(frame []byte, newToken string) ([]byte, bool) {
	docName, n1, ok := readVarString(frame, 0)
	if !ok {
		return frame, false
	}
	msgType, n2, ok := readVarUint(frame, n1)
	if !ok || msgType != collabMessageTypeAuth {
		return frame, false
	}
	subType, n3, ok := readVarUint(frame, n2)
	if !ok || subType != collabAuthSubTypeToken {
		return frame, false
	}
	// 旧 token：明文 JWT，仅定位，不使用。
	_, n4, ok := readVarString(frame, n3)
	if !ok {
		return frame, false
	}
	version, n5, ok := readVarString(frame, n4)
	if !ok {
		return frame, false
	}

	var buf bytes.Buffer
	writeVarString(&buf, docName)
	writeVarUint(&buf, collabMessageTypeAuth)
	writeVarUint(&buf, collabAuthSubTypeToken)
	writeVarString(&buf, newToken)
	writeVarString(&buf, version)
	buf.Write(frame[n5:]) // 保留未知尾部字节（前向兼容）
	return buf.Bytes(), true
}

// collabTunnel 上游连接写保护（读方向仅 main loop 使用）。
type collabTunnel struct {
	mu   sync.Mutex
	conn *websocket.Conn
}

func (t *collabTunnel) send(mt int, p []byte) bool {
	t.mu.Lock()
	defer t.mu.Unlock()
	if t.conn == nil {
		return false
	}
	return t.conn.WriteMessage(mt, p) == nil
}

// handleProxyCollab 协作 WS 代理：GET /api/local/proxy/{serverId}/collab → <baseURL>/ws/collab
//
// 首个二进制帧为 HocuspocusProvider.sendToken() 的 AuthenticationMessage：以密钥库
// app access token 重建帧后转发；其余帧透明双向转发。上游断开时同时关闭客户端连接，
// 由 HocuspocusProvider 自行重连并重发认证帧（本代理再次改写），保证重连后鉴权有效。
func (g *Gateway) handleProxyCollab(w http.ResponseWriter, r *http.Request) {
	serverID := r.PathValue("serverId")
	srv, err := g.servers.Get(serverID)
	if err != nil {
		writeError(w, http.StatusNotFound, "SERVER_NOT_FOUND", "server not found")
		return
	}
	appToken, err := g.servers.Token(serverID)
	if err != nil || appToken == "" {
		writeError(w, http.StatusUnauthorized, "AUTH_TOKEN_MISSING", "server token missing")
		return
	}
	upstream := collabEndpoint(srv.BaseURL)
	if upstream == "" {
		writeError(w, http.StatusBadRequest, "BAD_SERVER_URL", "invalid server base url")
		return
	}

	clientConn, err := wsUpgrader.Upgrade(w, r, nil)
	if err != nil {
		return
	}
	defer clientConn.Close()

	upstreamConn, ok := dialWS(upstream)
	if !ok {
		return // 已 Upgrade，无法回写错误；客户端侧 provider 将走 onclose 重连
	}

	tunnel := &collabTunnel{conn: upstreamConn}
	defer func() {
		tunnel.mu.Lock()
		if tunnel.conn != nil {
			_ = tunnel.conn.Close()
			tunnel.conn = nil
		}
		tunnel.mu.Unlock()
	}()

	// 客户端 → 上游：首帧改写 token 后转发，其余透明。
	go func() {
		authed := false
		for {
			mt, p, err := clientConn.ReadMessage()
			if err != nil {
				return
			}
			if !authed && mt == websocket.BinaryMessage && len(p) > 0 {
				if rewritten, changed := rewriteCollabAuthFrame(p, appToken); changed {
					p = rewritten
				}
				authed = true
			}
			if !tunnel.send(mt, p) {
				return
			}
		}
	}()

	// 上游 → 客户端：透明转发；上游断开则关闭客户端（provider 驱动重连）。
	for {
		mt, p, err := upstreamConn.ReadMessage()
		if err != nil {
			return
		}
		if err := clientConn.WriteMessage(mt, p); err != nil {
			return
		}
	}
}
