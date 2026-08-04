package server

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"
)

// ErrLoginFailed 账密登录失败或服务器返回非 2xx。
var ErrLoginFailed = errors.New("login failed")

// ErrProbeFailed 连通性探测失败（服务器不可达或返回非 2xx）。
var ErrProbeFailed = errors.New("probe failed")

type Client struct {
	httpClient *http.Client
}

func NewClient() *Client {
	return &Client{httpClient: &http.Client{Timeout: 30 * time.Second}}
}

// Login 用账密调 {baseURL}/api/v1/auth/login 换取 access token。
func (c *Client) Login(baseURL, username, password string) (token string, err error) {
	var buf bytes.Buffer
	_ = json.NewEncoder(&buf).Encode(map[string]string{"username": username, "password": password})
	req, err := http.NewRequest(http.MethodPost, strings.TrimRight(baseURL, "/")+"/api/v1/auth/login", &buf)
	if err != nil {
		return "", err
	}
	req.Header.Set("Content-Type", "application/json")
	resp, err := c.httpClient.Do(req)
	if err != nil {
		return "", fmt.Errorf("%w: %v", ErrLoginFailed, err)
	}
	defer resp.Body.Close()
	body, _ := io.ReadAll(io.LimitReader(resp.Body, 1<<20))
	if resp.StatusCode != 200 {
		return "", fmt.Errorf("%w: server returned %d: %s", ErrLoginFailed, resp.StatusCode, strings.TrimSpace(string(body)))
	}
	var out struct {
		Token string `json:"token"`
	}
	if err := json.Unmarshal(body, &out); err != nil {
		return "", fmt.Errorf("%w: bad response: %v", ErrLoginFailed, err)
	}
	if out.Token == "" {
		return "", fmt.Errorf("%w: empty token", ErrLoginFailed)
	}
	return out.Token, nil
}

// Probe 用 token 请求 {baseURL}/api/v1/users/me 检查服务器连通与 token 有效性。
func (c *Client) Probe(baseURL, token string) error {
	if token == "" {
		return ErrProbeFailed
	}
	req, err := http.NewRequest(http.MethodGet, strings.TrimRight(baseURL, "/")+"/api/v1/users/me", nil)
	if err != nil {
		return err
	}
	req.Header.Set("Authorization", "Bearer "+token)
	resp, err := c.httpClient.Do(req)
	if err != nil {
		return fmt.Errorf("%w: %v", ErrProbeFailed, err)
	}
	defer resp.Body.Close()
	if resp.StatusCode >= 400 {
		return fmt.Errorf("%w: server returned %d", ErrProbeFailed, resp.StatusCode)
	}
	return nil
}