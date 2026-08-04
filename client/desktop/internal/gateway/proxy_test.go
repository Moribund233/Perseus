package gateway

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync"
	"testing"

	"desktop/internal/server"
	"desktop/internal/store"
)

type proxyFixture struct {
	g        *Gateway
	serverID string
	setMode  func(string) // "ok" | "error" | "off"
}

// newProxyFixture 构造带假上游 + 已注册 token 的网关。
func newProxyFixture(t *testing.T) *proxyFixture {
	t.Helper()
	st, _ := store.New("")
	t.Cleanup(func() { st.Close() })
	kc := &store.FakeKeychain{M: map[string]string{}}

	var mu sync.Mutex
	mode := "ok"
	backend := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		mu.Lock()
		auth := r.Header.Get("Authorization")
		m := mode
		mu.Unlock()
		if m == "off" {
			// 由 setMode("off") 直接 Close() 后端，这里不会走到。
			http.Error(w, "unreachable", http.StatusInternalServerError)
			return
		}
		if m == "error" && strings.HasPrefix(r.URL.Path, "/api/v1/repositories/err") {
			w.WriteHeader(500)
			_, _ = w.Write([]byte(`{"detail":"boom"}`))
			return
		}
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"path":"` + r.URL.Path + `","auth":"` + auth + `"}`))
	}))
	t.Cleanup(backend.Close)

	g := New(Config{
		Store:         st,
		Servers:       server.NewRegistry(st, kc),
		AllowedOrigins: []string{"http://localhost:34115"},
	})
	reg := server.NewRegistry(st, kc)
	created, err := reg.AddServer(server.AddInput{
		Name: "dev", BaseURL: backend.URL, AuthMethod: "token", Token: "tok123",
	})
	if err != nil {
		t.Fatalf("AddServer: %v", err)
	}

	return &proxyFixture{
		g:        g,
		serverID: created.ID,
		setMode: func(m string) {
			mu.Lock()
			mode = m
			mu.Unlock()
			if m == "off" {
				backend.Close()
			}
		},
	}
}

func (f *proxyFixture) proxy(suffix string) string {
	return "/api/local/proxy/" + f.serverID + suffix
}

func (f *proxyFixture) req(method, path string) *httptest.ResponseRecorder {
	req := httptest.NewRequest(method, path, strings.NewReader(`{"x":1}`))
	req.Header.Set("Origin", "http://localhost:34115")
	req.Header.Set("X-Gateway-Token", f.g.Token())
	req.Header.Set("Content-Type", "application/json")
	rr := httptest.NewRecorder()
	f.g.Handler().ServeHTTP(rr, req)
	return rr
}

func TestProxyInjectTokenAndPrefix(t *testing.T) {
	f := newProxyFixture(t)
	rr := f.req("GET", f.proxy("/api/v1/repositories?page=1"))
	if rr.Code != 200 {
		t.Fatalf("status=%d body=%s", rr.Code, rr.Body.String())
	}
	if !strings.Contains(rr.Body.String(), `"auth":"Bearer tok123"`) {
		t.Fatalf("token not injected: %s", rr.Body.String())
	}
	if !strings.Contains(rr.Body.String(), `/api/v1/repositories`) {
		t.Fatalf("path not forwarded: %s", rr.Body.String())
	}
}

func TestProxyOffline503WithCache(t *testing.T) {
	f := newProxyFixture(t)

	if rr := f.req("GET", f.proxy("/api/v1/repositories")); rr.Code != 200 {
		t.Fatalf("seed status=%d", rr.Code)
	}
	f.setMode("off")

	rr := f.req("GET", f.proxy("/api/v1/repositories"))
	if rr.Code != 503 {
		t.Fatalf("offline cached status=%d body=%s", rr.Code, rr.Body.String())
	}
	var body struct {
		Offline bool `json:"offline"`
		Cached  any  `json:"cached"`
		Error   struct{ Code string `json:"code"` } `json:"error"`
	}
	_ = json.Unmarshal(rr.Body.Bytes(), &body)
	if !body.Offline || body.Cached == nil || body.Error.Code != "SERVER_OFFLINE" {
		t.Fatalf("bad offline body: %s", rr.Body.String())
	}

	rr = f.req("GET", f.proxy("/api/v1/repositories/other"))
	if rr.Code != 503 || !strings.Contains(rr.Body.String(), `"cached":null`) {
		t.Fatalf("offline miss status=%d body=%s", rr.Code, rr.Body.String())
	}
}

func TestProxyWriteNotCached(t *testing.T) {
	f := newProxyFixture(t)
	f.setMode("off")
	rr := f.req("POST", f.proxy("/api/v1/repositories"))
	if rr.Code != 503 || !strings.Contains(rr.Body.String(), `"cached":null`) {
		t.Fatalf("offline write status=%d body=%s", rr.Code, rr.Body.String())
	}
}

func TestProxyUpstreamErrorPassthrough(t *testing.T) {
	f := newProxyFixture(t)
	f.setMode("error")
	rr := f.req("GET", f.proxy("/api/v1/repositories/err"))
	if rr.Code != 500 {
		t.Fatalf("upstream error status=%d body=%s", rr.Code, rr.Body.String())
	}
	if !strings.Contains(rr.Body.String(), "boom") {
		t.Fatalf("upstream body not passed: %s", rr.Body.String())
	}
}

func TestProxyUnknownServer(t *testing.T) {
	f := newProxyFixture(t)
	rr := f.req("GET", "/api/local/proxy/nope/api/v1/repositories")
	if rr.Code != 404 {
		t.Fatalf("status=%d body=%s", rr.Code, rr.Body.String())
	}
}