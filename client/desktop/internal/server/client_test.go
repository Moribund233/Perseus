package server

import (
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func loginBackend(t *testing.T, status int, body string) *httptest.Server {
	t.Helper()
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/v1/auth/login" {
			w.WriteHeader(404)
			return
		}
		if r.Method != http.MethodPost {
			w.WriteHeader(405)
			return
		}
		w.WriteHeader(status)
		_, _ = w.Write([]byte(body))
	}))
	t.Cleanup(srv.Close)
	return srv
}

func TestClientLoginSuccess(t *testing.T) {
	srv := loginBackend(t, 200, `{"token":"tok123"}`)
	tok, err := NewClient().Login(srv.URL, "tester", "p@ss")
	if err != nil {
		t.Fatalf("Login: %v", err)
	}
	if tok != "tok123" {
		t.Fatalf("token = %q", tok)
	}
}

func TestClientLoginNon2xx(t *testing.T) {
	srv := loginBackend(t, 401, `{"detail":"invalid credentials"}`)

	tok, err := NewClient().Login(srv.URL, "x", "y")
	if tok != "" || err == nil {
		t.Fatalf("expected failure, token=%q err=%v", tok, err)
	}
	if !errors.Is(err, ErrLoginFailed) {
		t.Fatalf("err = %v, want ErrLoginFailed", err)
	}
	if !strings.Contains(err.Error(), "401") {
		t.Fatalf("err should mention status: %v", err)
	}
}

func TestClientLoginEmptyToken(t *testing.T) {
	srv := loginBackend(t, 200, `{"detail":"ok"}`)
	tok, err := NewClient().Login(srv.URL, "a", "b")
	if tok != "" || err == nil {
		t.Fatalf("expected failure, token=%q err=%v", tok, err)
	}
	if !errors.Is(err, ErrLoginFailed) {
		t.Fatalf("err = %v, want ErrLoginFailed", err)
	}
}

func TestClientLoginMalformedBody(t *testing.T) {
	srv := loginBackend(t, 200, `not json`)
	tok, err := NewClient().Login(srv.URL, "a", "b")
	if tok != "" || err == nil {
		t.Fatalf("expected failure, token=%q err=%v", tok, err)
	}
	if !errors.Is(err, ErrLoginFailed) {
		t.Fatalf("err = %v, want ErrLoginFailed", err)
	}
}

func TestClientLoginUnreachable(t *testing.T) {
	tok, err := NewClient().Login("http://127.0.0.1:1", "a", "b")
	if tok != "" || err == nil {
		t.Fatalf("expected failure, token=%q err=%v", tok, err)
	}
	if !errors.Is(err, ErrLoginFailed) {
		t.Fatalf("err = %v, want ErrLoginFailed", err)
	}
}

// TestClientLoginRequestShape 验证登录请求体与响应头/解析的正确性。
func TestClientLoginRequestShape(t *testing.T) {
	var gotBody map[string]string
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if err := json.NewDecoder(r.Body).Decode(&gotBody); err != nil {
			w.WriteHeader(400)
			return
		}
		if r.Header.Get("Content-Type") != "application/json" {
			w.WriteHeader(415)
			return
		}
		_, _ = w.Write([]byte(`{"token":"t"}`))
	}))
	t.Cleanup(srv.Close)

	tok, err := NewClient().Login(srv.URL, "u", "p")
	if err != nil {
		t.Fatalf("Login: %v", err)
	}
	if tok != "t" {
		t.Fatalf("token = %q", tok)
	}
	if gotBody["username"] != "u" || gotBody["password"] != "p" {
		t.Fatalf("body = %v", gotBody)
	}
}

func TestClientProbeOK(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/v1/users/me" {
			w.WriteHeader(404)
			return
		}
		if r.Header.Get("Authorization") != "Bearer tok" {
			w.WriteHeader(401)
			return
		}
		_, _ = w.Write([]byte(`{"id":"u1"}`))
	}))
	t.Cleanup(srv.Close)

	if err := NewClient().Probe(srv.URL, "tok"); err != nil {
		t.Fatalf("Probe: %v", err)
	}
}

func TestClientProbeUnauthorized(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(401)
	}))
	t.Cleanup(srv.Close)

	err := NewClient().Probe(srv.URL, "bad")
	if err == nil {
		t.Fatal("expected probe failure")
	}
	if !errors.Is(err, ErrProbeFailed) {
		t.Fatalf("err = %v, want ErrProbeFailed", err)
	}
}

func TestClientProbeEmptyToken(t *testing.T) {
	if err := NewClient().Probe("http://127.0.0.1:1", ""); err == nil {
		t.Fatal("expected failure with empty token")
	}
}