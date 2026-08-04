package server

import (
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync"
	"testing"

	"desktop/internal/store"
)

func newFakeBackend(t *testing.T) (*httptest.Server, *string, *string) {
	t.Helper()
	var mu sync.Mutex
	var lastAuth, loginBody string
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		mu.Lock()
		defer mu.Unlock()
		lastAuth = r.Header.Get("Authorization")
		switch {
		case r.URL.Path == "/api/v1/auth/login":
			buf, _ := io.ReadAll(io.LimitReader(r.Body, 1<<20))
			loginBody = string(buf)
			if !strings.Contains(loginBody, `"password":"p@ss"`) {
				w.WriteHeader(401)
				_, _ = w.Write([]byte(`{"detail":"invalid credentials"}`))
				return
			}
			_, _ = w.Write([]byte(`{"token":"tok123","user":{"id":"u1"}}`))
		case r.URL.Path == "/api/v1/users/me":
			if lastAuth != "Bearer tok123" {
				w.WriteHeader(401)
				return
			}
			_, _ = w.Write([]byte(`{"id":"u1","username":"tester"}`))
		default:
			w.WriteHeader(404)
		}
	}))
	t.Cleanup(srv.Close)
	return srv, &lastAuth, &loginBody
}

func newTestRegistry(t *testing.T) *Registry {
	st, _ := store.New("")
	t.Cleanup(func() { st.Close() })
	return NewRegistry(st, &store.FakeKeychain{M: map[string]string{}})
}

func TestAddServerPasswordAndProbe(t *testing.T) {
	fake, lastAuth, _ := newFakeBackend(t)
	rg := newTestRegistry(t)

	srv, err := rg.AddServer(AddInput{
		Name: "dev", BaseURL: fake.URL, AuthMethod: "password",
		Username: "tester", Password: "p@ss",
	})
	if err != nil {
		t.Fatalf("AddServer: %v", err)
	}
	if srv.ID == "" || srv.Health != "online" || srv.LastSuccess == "" {
		t.Fatalf("unexpected server: %+v", srv)
	}
	if *lastAuth != "Bearer tok123" {
		t.Fatalf("probe auth = %q", *lastAuth)
	}

	tok, err := rg.Token(srv.ID)
	if err != nil || tok != "tok123" {
		t.Fatalf("Token = %q err %v", tok, err)
	}
}

func TestAddServerTokenPaste(t *testing.T) {
	_, _, _ = newFakeBackend(t)
	rg := newTestRegistry(t)
	srv, err := rg.AddServer(AddInput{
		Name: "paste", BaseURL: "http://127.0.0.1:1", AuthMethod: "token", Token: "abc",
	})
	if err != nil {
		t.Fatalf("AddServer: %v", err)
	}
	if srv.Health != "offline" {
		t.Fatalf("expected offline (unreachable), got %+v", srv)
	}
}

func TestAddServerLoginFailureRollsBack(t *testing.T) {
	_, _, _ = newFakeBackend(t)
	rg := newTestRegistry(t)
	if _, err := rg.AddServer(AddInput{
		Name: "bad", BaseURL: "http://127.0.0.1:1", AuthMethod: "password",
		Username: "x", Password: "wrong",
	}); err == nil {
		t.Fatal("expected login failure")
	}
	list, _ := rg.List()
	if len(list) != 0 {
		t.Fatalf("expected rollback, got %d servers", len(list))
	}
}

func TestProbeHealthTransition(t *testing.T) {
	_, _, _ = newFakeBackend(t)
	rg := newTestRegistry(t)
	srv, err := rg.AddServer(AddInput{
		Name: "dev", BaseURL: "http://127.0.0.1:1", AuthMethod: "token", Token: "x",
	})
	if err != nil {
		t.Fatal(err)
	}
	if srv.Health != "offline" {
		t.Fatalf("expected offline, got %+v", srv)
	}
	// 探测仍失败，保持 offline
	if err := rg.Probe(srv.ID); err == nil {
		t.Fatal("expected probe error")
	}
	got, _ := rg.Get(srv.ID)
	if got.Health != "offline" {
		t.Fatalf("health = %q", got.Health)
	}
}

func TestRefreshToken(t *testing.T) {
	fake, _, _ := newFakeBackend(t)
	rg := newTestRegistry(t)
	srv, err := rg.AddServer(AddInput{
		Name: "dev", BaseURL: fake.URL, AuthMethod: "password",
		Username: "tester", Password: "p@ss",
	})
	if err != nil {
		t.Fatal(err)
	}
	if _, err := rg.RefreshToken(srv.ID, "tester", "p@ss"); err != nil {
		t.Fatalf("RefreshToken: %v", err)
	}
	got, _ := rg.Get(srv.ID)
	if got.Username != "tester" {
		t.Fatalf("username = %q", got.Username)
	}
}

func TestDeleteRemovesToken(t *testing.T) {
	fake, _, _ := newFakeBackend(t)
	rg := newTestRegistry(t)
	srv, err := rg.AddServer(AddInput{
		Name: "dev", BaseURL: fake.URL, AuthMethod: "password",
		Username: "tester", Password: "p@ss",
	})
	if err != nil {
		t.Fatal(err)
	}
	if err := rg.Delete(srv.ID); err != nil {
		t.Fatalf("Delete: %v", err)
	}
	if _, err := rg.Token(srv.ID); err == nil {
		t.Fatal("expected token removed")
	}
}
