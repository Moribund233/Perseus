package gateway

import (
	"encoding/json"
	"net/http"
	"time"

	"github.com/gorilla/websocket"
)

// handleLSP 语言服务器 WS 桥：GET /api/local/workspaces/{id}/lsp?lang=<language>
// 每个连接对应一个独立 LSP 进程（Phase 0 按连接会话）。网关注重流式透传：
// 一条 WS 消息 = 一条 LSP 帧正文（完整 JSON-RPC），进程侧负责 Content-Length 封帧。
// 协议握手（initialize/didOpen/...）由前端 Monaco providers 驱动（spec §8.1）。
func (g *Gateway) handleLSP(w http.ResponseWriter, r *http.Request) {
	ws, err := g.store.GetWorkspace(r.PathValue("id"))
	if err != nil {
		writeError(w, http.StatusNotFound, "STORE_NOT_FOUND", "workspace not found")
		return
	}
	lang := r.URL.Query().Get("lang")
	sess, err := g.lsp.Start(ws.Path, lang)
	if err != nil {
		writeError(w, http.StatusBadRequest, "LSP_LANG_UNSUPPORTED", err.Error())
		return
	}
	conn, err := wsUpgrader.Upgrade(w, r, nil)
	if err != nil {
		_ = sess.Close()
		return
	}
	defer conn.Close()
	defer sess.Close()

	// 进程 → 客户端
	go func() {
		for {
			select {
			case msg := <-sess.Out():
				_ = conn.SetWriteDeadline(time.Now().Add(30 * time.Second))
				if conn.WriteMessage(websocket.TextMessage, msg) != nil {
					return
				}
			case <-sess.Closed():
				if err := sess.Err(); err != nil {
					// 崩溃重试耗尽：以 LSP logMessage 形状通知前端。
					notify := map[string]any{
						"jsonrpc": "2.0",
						"method":  "window/logMessage",
						"params":  map[string]any{"type": 1, "message": err.Error()},
					}
					b, mErr := json.Marshal(notify)
					if mErr == nil {
						_ = conn.SetWriteDeadline(time.Now().Add(15 * time.Second))
						_ = conn.WriteMessage(websocket.TextMessage, b)
					}
				}
				return
			}
		}
	}()

	// 客户端 → 进程
	for {
		_, data, err := conn.ReadMessage()
		if err != nil {
			return
		}
		if len(data) == 0 || !json.Valid(data) {
			continue
		}
		if err := sess.Send(data); err != nil {
			return
		}
	}
}