package gateway

import (
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/gorilla/websocket"

	"desktop/internal/server"
	"desktop/internal/store"
)

// TestProxyWSPassthrough 验证帧经网关在客户端与假上游 WS 间往返。
func TestProxyWSPassthrough(t *testing.T) {
	st, _ := store.New("")
	t.Cleanup(func() { st.Close() })
	kc := &store.FakeKeychain{M: map[string]string{}}

	// 假上游 WS 端点：/ws/notifications，回显收到的文本。
	var gotToken string
	upstream := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/ws/notifications" {
			http.NotFound(w, r)
			return
		}
		gotToken = r.URL.Query().Get("token")
		conn, err := wsUpgrader.Upgrade(w, r, nil)
		if err != nil {
			return
		}
		defer conn.Close()
		for {
			mt, p, err := conn.ReadMessage()
			if err != nil {
				return
			}
			if err := conn.WriteMessage(mt, []byte("echo:"+string(p))); err != nil {
				return
			}
		}
	}))
	t.Cleanup(upstream.Close)

	g := New(Config{
		Store:         st,
		Servers:       server.NewRegistry(st, kc),
		AllowedOrigins: []string{"http://localhost:34115"},
	})
	reg := server.NewRegistry(st, kc)
	created, err := reg.AddServer(server.AddInput{
		Name: "up", BaseURL: upstream.URL, AuthMethod: "token", Token: "wstok",
	})
	if err != nil {
		t.Fatalf("AddServer: %v", err)
	}

	// 网关自身包一层 HTTP server，供客户端 dial。
	gatewaySrv := httptest.NewServer(g.Handler())
	t.Cleanup(gatewaySrv.Close)

	wsURL := "ws" + gatewaySrv.URL[4:] + "/api/local/proxy/" + created.ID + "/ws/notifications"
	header := http.Header{}
	header.Set("Origin", "http://localhost:34115")
	header.Set("X-Gateway-Token", g.Token())

	conn, resp, err := websocket.DefaultDialer.Dial(wsURL, header)
	if err != nil {
		t.Fatalf("dial gateway ws: %v (status=%d)", err, resp.StatusCode)
	}
	defer conn.Close()

	if err := conn.WriteMessage(websocket.TextMessage, []byte("hi")); err != nil {
		t.Fatal(err)
	}
	conn.SetReadDeadline(time.Now().Add(3 * time.Second))
	_, p, err := conn.ReadMessage()
	if err != nil {
		t.Fatalf("read echo: %v", err)
	}
	if string(p) != "echo:hi" {
		t.Fatalf("echo = %q", p)
	}
	// 回显成功说明上游已建立连接，此时 token 必已注入。
	if gotToken != "wstok" {
		t.Fatalf("upstream token = %q, want wstok", gotToken)
	}
}