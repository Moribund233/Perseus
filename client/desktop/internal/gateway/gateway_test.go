package gateway

import (
	"net/http/httptest"
	"testing"

	"desktop/internal/server"
	"desktop/internal/store"
)

func TestConfigRouteAndToken(t *testing.T) {
	st, _ := store.New("")
	defer st.Close()
	g := New(Config{
		Store:         st,
		Servers:       server.NewRegistry(st, &store.FakeKeychain{M: map[string]string{}}),
		AllowedOrigins: []string{"http://localhost:34115"},
	})
	h := g.Handler()

	// 无 token 访问 config（放行）
	req := httptest.NewRequest("GET", "/api/local/config", nil)
	req.Header.Set("Origin", "http://localhost:34115")
	rr := httptest.NewRecorder()
	h.ServeHTTP(rr, req)
	if rr.Code != 200 {
		t.Fatalf("config status = %d body=%s", rr.Code, rr.Body.String())
	}

	// 无 token 访问其他路由 → 401
	req = httptest.NewRequest("GET", "/api/local/workspaces", nil)
	req.Header.Set("Origin", "http://localhost:34115")
	rr = httptest.NewRecorder()
	h.ServeHTTP(rr, req)
	if rr.Code != 401 {
		t.Fatalf("expected 401, got %d", rr.Code)
	}

	// 带 token → 200
	req = httptest.NewRequest("GET", "/api/local/workspaces", nil)
	req.Header.Set("Origin", "http://localhost:34115")
	req.Header.Set("X-Gateway-Token", g.Token())
	rr = httptest.NewRecorder()
	h.ServeHTTP(rr, req)
	if rr.Code != 200 {
		t.Fatalf("with token status = %d body=%s", rr.Code, rr.Body.String())
	}
}

func TestCORSDisallowedOrigin(t *testing.T) {
	st, _ := store.New("")
	defer st.Close()
	g := New(Config{
		Store:         st,
		Servers:       server.NewRegistry(st, &store.FakeKeychain{M: map[string]string{}}),
		AllowedOrigins: []string{"http://localhost:34115"},
	})
	req := httptest.NewRequest("GET", "/api/local/config", nil)
	req.Header.Set("Origin", "https://evil.example.com")
	rr := httptest.NewRecorder()
	g.Handler().ServeHTTP(rr, req)
	if rr.Code != 403 {
		t.Fatalf("expected 403 for disallowed origin, got %d", rr.Code)
	}
}

func TestWebSocketTokenViaQuery(t *testing.T) {
	st, _ := store.New("")
	defer st.Close()
	g := New(Config{
		Store:         st,
		Servers:       server.NewRegistry(st, &store.FakeKeychain{M: map[string]string{}}),
		AllowedOrigins: []string{"http://localhost:34115"},
	})
	h := g.Handler()

	// WS upgrade 无 token（header 与 query 都缺）→ 401
	req := httptest.NewRequest("GET", "/api/local/proxy/srv1/ws/chat", nil)
	req.Header.Set("Connection", "Upgrade")
	req.Header.Set("Upgrade", "websocket")
	rr := httptest.NewRecorder()
	h.ServeHTTP(rr, req)
	if rr.Code != 401 {
		t.Fatalf("expected 401 without token, got %d", rr.Code)
	}

	// WS upgrade 带 query _token → 放行（应进入处理器并尝试连接上游 server，此处 server 不存在→404）
	req = httptest.NewRequest("GET", "/api/local/proxy/srv1/ws/chat?_token="+g.Token(), nil)
	req.Header.Set("Connection", "Upgrade")
	req.Header.Set("Upgrade", "websocket")
	rr = httptest.NewRecorder()
	h.ServeHTTP(rr, req)
	if rr.Code != 404 {
		t.Fatalf("expected 404 (no server) after token auth, got %d body=%s", rr.Code, rr.Body.String())
	}
}
