package server

import (
	"errors"
	"time"

	"desktop/internal/store"
)

const tokenService = "perseus"

type AddInput struct {
	Name       string
	BaseURL    string
	AuthMethod string // "password" | "token"
	Username   string
	Password   string
	Token      string
}

var ErrInvalidAuth = errors.New("invalid auth input")

// Registry 服务器注册表：包装 store 元数据 + 密钥库 token + 远端 client。
type Registry struct {
	store    *store.Store
	keychain store.Keychain
	client   *Client
}

func NewRegistry(st *store.Store, kc store.Keychain) *Registry {
	return &Registry{store: st, keychain: kc, client: NewClient()}
}

func tokenAccount(id string) string { return "server:" + id + ":token" }

func (rg *Registry) List() ([]store.Server, error) { return rg.store.ListServers() }
func (rg *Registry) Get(id string) (store.Server, error) {
	return rg.store.GetServer(id)
}

// AddServer 解析 token（账密登录或粘贴），存密钥库，探测初始 health，入库。
// 任一步骤失败都会清理已写入的 token/记录，保证一致性。
func (rg *Registry) AddServer(in AddInput) (store.Server, error) {
	var tok string
	switch in.AuthMethod {
	case "password":
		if in.Password == "" {
			return store.Server{}, ErrInvalidAuth
		}
		t, err := rg.client.Login(in.BaseURL, in.Username, in.Password)
		if err != nil {
			return store.Server{}, err
		}
		tok = t
	case "token":
		if in.Token == "" {
			return store.Server{}, ErrInvalidAuth
		}
		tok = in.Token
	default:
		return store.Server{}, ErrInvalidAuth
	}

	health := "unknown"
	now := time.Now().UTC().Format(time.RFC3339)
	lastSuccess := ""
	if err := rg.client.Probe(in.BaseURL, tok); err == nil {
		health = "online"
		lastSuccess = now
	} else {
		health = "offline"
	}

	srv, err := rg.store.CreateServer(store.Server{
		Name: in.Name, BaseURL: in.BaseURL, AuthMethod: in.AuthMethod,
		Username: in.Username, Health: health, LastChecked: now, LastSuccess: lastSuccess,
	})
	if err != nil {
		return store.Server{}, err
	}
	if err := rg.keychain.Set(tokenService, tokenAccount(srv.ID), tok); err != nil {
		_ = rg.store.DeleteServer(srv.ID)
		return store.Server{}, err
	}
	return srv, nil
}

func (rg *Registry) Update(srv store.Server) error { return rg.store.UpdateServer(srv) }

// Delete 删除注册表记录与密钥库 token（best-effort）。
func (rg *Registry) Delete(id string) error {
	_ = rg.keychain.Delete(tokenService, tokenAccount(id))
	return rg.store.DeleteServer(id)
}

func (rg *Registry) Token(id string) (string, error) {
	return rg.keychain.Get(tokenService, tokenAccount(id))
}

// RefreshToken 用新密码重新登录并更新密钥库 token，随后探测。
func (rg *Registry) RefreshToken(id, username, password string) (store.Server, error) {
	srv, err := rg.store.GetServer(id)
	if err != nil {
		return store.Server{}, err
	}
	if username == "" || password == "" {
		return srv, ErrInvalidAuth
	}
	tok, err := rg.client.Login(srv.BaseURL, username, password)
	if err != nil {
		return store.Server{}, err
	}
	if err := rg.keychain.Set(tokenService, tokenAccount(id), tok); err != nil {
		return srv, err
	}
	srv.Username = username
	if err := rg.store.UpdateServer(srv); err != nil {
		return srv, err
	}
	_ = rg.Probe(id)
	return srv, nil
}

// Probe 实测健康并落库。返回原始探测 error（供 handler 判断在线/离线）。
func (rg *Registry) Probe(id string) error {
	srv, err := rg.store.GetServer(id)
	if err != nil {
		return err
	}
	tok, err := rg.Token(id)
	if err != nil {
		return err
	}
	now := time.Now().UTC().Format(time.RFC3339)
	err = rg.client.Probe(srv.BaseURL, tok)
	if err == nil {
		_ = rg.store.SetServerHealth(id, "online", now, now)
	} else {
		_ = rg.store.SetServerHealth(id, "offline", now, srv.LastSuccess)
	}
	return err
}