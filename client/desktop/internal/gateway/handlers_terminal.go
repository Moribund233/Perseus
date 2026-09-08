package gateway

import (
	"encoding/base64"
	"encoding/json"
	"net/http"
	"time"

	"github.com/gorilla/websocket"
)

// termSession 终端会话的最小接口（生产为 ConPTY；测试可注入 fake）。
type termSession interface {
	Read([]byte) (int, error)
	Write([]byte) (int, error)
	Resize(int, int) error
	Close() error
}

// termFactory 按工作区路径创建终端会话。
type termFactory func(path string, cols, rows int) (termSession, error)

// termMessage 终端 WS 消息（base64 保证二进制安全）。
// 客户端→服务器: {"type":"input","data":"..."} | {"type":"resize","cols":N,"rows":N}
// 服务器→客户端: {"type":"output","data":"..."} | {"type":"exit","code":N}
type termMessage struct {
	Type string `json:"type"`
	Data string `json:"data,omitempty"`
	Cols int    `json:"cols,omitempty"`
	Rows int    `json:"rows,omitempty"`
	Code int    `json:"code,omitempty"`
}

// handleTerminal 终端 WS 桥：GET /api/local/workspaces/{id}/terminal
// 每个连接对应一个独立 shell 会话（目录=工作区路径）。
func (g *Gateway) handleTerminal(w http.ResponseWriter, r *http.Request) {
	ws, err := g.store.GetWorkspace(r.PathValue("id"))
	if err != nil {
		writeError(w, http.StatusNotFound, "STORE_NOT_FOUND", "workspace not found")
		return
	}
	conn, err := wsUpgrader.Upgrade(w, r, nil)
	if err != nil {
		return
	}
	defer conn.Close()

	t, err := g.termFactory(ws.Path, 120, 30)
	if err != nil {
		_ = g.writeTermStartError(conn, err)
		return
	}
	defer t.Close()

	// 进程 → 客户端
	go func() {
		buf := make([]byte, 8192)
		for {
			n, rerr := t.Read(buf)
			if n > 0 {
				msg := termMessage{Type: "output", Data: base64.StdEncoding.EncodeToString(buf[:n])}
				if !g.writeTerm(conn, msg) {
					return
				}
			}
			if rerr != nil {
				_ = g.writeTerm(conn, termMessage{Type: "exit", Code: -1})
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
		var m termMessage
		if err := json.Unmarshal(data, &m); err != nil {
			continue
		}
		switch m.Type {
		case "input":
			dec, derr := base64.StdEncoding.DecodeString(m.Data)
			if derr != nil {
				continue
			}
			if _, werr := t.Write(dec); werr != nil {
				return
			}
		case "resize":
			if m.Cols > 0 && m.Rows > 0 {
				if rerr := t.Resize(m.Cols, m.Rows); rerr != nil {
					return
				}
			}
		}
	}
}

func (g *Gateway) writeTerm(conn *websocket.Conn, m termMessage) bool {
	_ = conn.SetWriteDeadline(time.Now().Add(15 * time.Second))
	return conn.WriteJSON(m) == nil
}

func (g *Gateway) writeTermStartError(conn *websocket.Conn, err error) bool {
	enc := base64.StdEncoding.EncodeToString([]byte("终端启动失败: " + err.Error()))
	_ = g.writeTerm(conn, termMessage{Type: "output", Data: enc})
	return g.writeTerm(conn, termMessage{Type: "exit", Code: -1})
}