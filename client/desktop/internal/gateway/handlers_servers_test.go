package gateway

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"desktop/internal/server"
	"desktop/internal/store"
)

func TestServerRoutes(t *testing.T) {
	st, _ := store.New("")
	t.Cleanup(func() { st.Close() })
	kc := &store.FakeKeychain{M: map[string]string{}}

	// 假上游：支持账密登录 + users/me。
	backend := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/api/v1/auth/login":
			_, _ = w.Write([]byte(`{"token":"tok9"}`))
		case "/api/v1/users/me":
			if r.Header.Get("Authorization") != "Bearer tok9" {
				w.WriteHeader(401)
				return
			}
			_, _ = w.Write([]byte(`{"id":"u1"}`))
		default:
			w.WriteHeader(404)
		}
	}))
	t.Cleanup(backend.Close)

	g := New(Config{
		Store:         st,
		Servers:       server.NewRegistry(st, kc),
		AllowedOrigins: []string{"http://localhost:34115"},
	})

	// 注册（账密）
	rr := authedReq(t, g, "POST", "/api/local/servers", map[string]string{
		"name": "dev", "base_url": backend.URL, "auth_method": "password",
		"username": "tester", "password": "p@ss",
	})
	if rr.Code != 200 {
		t.Fatalf("register = %d body=%s", rr.Code, rr.Body.String())
	}
	var srv struct {
		ID     string `json:"id"`
		Health string `json:"health"`
	}
	jsonUnmarshal(t, rr.Body.Bytes(), &srv)
	if srv.ID == "" || srv.Health != "online" {
		t.Fatalf("register result: %+v", srv)
	}

	// 列表
	rr = authedReq(t, g, "GET", "/api/local/servers", nil)
	if rr.Code != 200 || !strings.Contains(rr.Body.String(), srv.ID) {
		t.Fatalf("list = %d body=%s", rr.Code, rr.Body.String())
	}

	// health（关闭 upstream → offline）
	backend.Close()
	rr = authedReq(t, g, "GET", "/api/local/servers/"+srv.ID+"/health", nil)
	if rr.Code != 503 {
		t.Fatalf("health offline = %d body=%s", rr.Code, rr.Body.String())
	}
	rr = authedReq(t, g, "GET", "/api/local/servers", nil)
	if rr.Code != 200 || !strings.Contains(rr.Body.String(), `"health":"offline"`) {
		t.Fatalf("list after offline = %d body=%s", rr.Code, rr.Body.String())
	}

	// 删除
	rr = authedReq(t, g, "DELETE", "/api/local/servers/"+srv.ID, nil)
	if rr.Code != 200 {
		t.Fatalf("delete = %d body=%s", rr.Code, rr.Body.String())
	}
	if _, err := kc.Get("perseus", "server:"+srv.ID+":token"); err == nil {
		t.Fatal("token should be removed on delete")
	}
}

func TestServerRegisterBadAuth(t *testing.T) {
	st, _ := store.New("")
	t.Cleanup(func() { st.Close() })
	g := New(Config{
		Store:         st,
		Servers:       server.NewRegistry(st, &store.FakeKeychain{M: map[string]string{}}),
		AllowedOrigins: []string{"http://localhost:34115"},
	})
	// 不可达 + 密码路径 → LOGIN_FAILED(401)
	rr := authedReq(t, g, "POST", "/api/local/servers", map[string]string{
		"name": "x", "base_url": "http://127.0.0.1:1", "auth_method": "password",
		"username": "u", "password": "p",
	})
	if rr.Code != 401 {
		t.Fatalf("bad login = %d body=%s", rr.Code, rr.Body.String())
	}
	// 缺字段 → 400
	rr = authedReq(t, g, "POST", "/api/local/servers", map[string]string{"name": "x"})
	if rr.Code != 400 {
		t.Fatalf("bad req = %d body=%s", rr.Code, rr.Body.String())
	}
}

func jsonUnmarshal(t *testing.T, data []byte, v any) {
	t.Helper()
	if err := json.Unmarshal(data, v); err != nil {
		t.Fatalf("decode %s: %v", data, err)
	}
}