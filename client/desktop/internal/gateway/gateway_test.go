package gateway

import (
	"net/http/httptest"
	"testing"

	"desktop/internal/store"
)

func TestConfigRouteAndToken(t *testing.T) {
	st, _ := store.New("")
	defer st.Close()
	g := New(Config{Store: st, AllowedOrigins: []string{"http://localhost:34115"}})
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
	g := New(Config{Store: st, AllowedOrigins: []string{"http://localhost:34115"}})
	req := httptest.NewRequest("GET", "/api/local/config", nil)
	req.Header.Set("Origin", "https://evil.example.com")
	rr := httptest.NewRecorder()
	g.Handler().ServeHTTP(rr, req)
	if rr.Code != 403 {
		t.Fatalf("expected 403 for disallowed origin, got %d", rr.Code)
	}
}
