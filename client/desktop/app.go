package main

import (
	"context"
	"fmt"
	"os"
	"path/filepath"

	"desktop/internal/gateway"
	"desktop/internal/git"
	"desktop/internal/server"
	"desktop/internal/store"
)

// App struct
type App struct {
	ctx      context.Context
	store    *store.Store
	gateway  *gateway.Gateway
	keychain store.Keychain
}

// NewApp creates a new App application struct
func NewApp() *App {
	return &App{}
}

// startup is called when the app starts.
func (a *App) startup(ctx context.Context) {
	a.ctx = ctx
}

// Initialize 在 main 中调用：装配依赖并启动网关。
func (a *App) Initialize() error {
	dir, err := os.UserConfigDir()
	if err != nil {
		return err
	}
	dbPath := filepath.Join(dir, "perseus", "app.db")
	if err := os.MkdirAll(filepath.Dir(dbPath), 0o755); err != nil {
		return err
	}
	st, err := store.New(dbPath)
	if err != nil {
		return err
	}
	a.store = st
	a.keychain = store.NewKeychain()
	g := gateway.New(gateway.Config{
		Store:   st,
		Git:     git.NewGit(a.keychain),
		Servers: server.NewRegistry(st, a.keychain),
	})
	if err := g.Start(); err != nil {
		return err
	}
	a.gateway = g
	return nil
}

func (a *App) Shutdown() {
	if a.gateway != nil {
		_ = a.gateway.Stop()
	}
	if a.store != nil {
		_ = a.store.Close()
	}
}

type GatewayConfig struct {
	BaseURL      string `json:"baseURL"`
	GatewayToken string `json:"gatewayToken"`
}

func (a *App) GetGatewayConfig() (GatewayConfig, error) {
	if a.gateway == nil {
		return GatewayConfig{}, errNotReady
	}
	return GatewayConfig{
		BaseURL:      "http://" + a.gateway.Addr(),
		GatewayToken: a.gateway.Token(),
	}, nil
}

var errNotReady = fmt.Errorf("app not ready")

func (a *App) OpenFolderDialog() (string, error) {
	return a.dialogOpenDir()
}

func (a *App) OpenFileDialog() (string, error) {
	return a.dialogOpenFile()
}

func (a *App) SaveFileDialog(defaultName string) (string, error) {
	return a.dialogSaveFile(defaultName)
}

func (a *App) KeychainGet(service, account string) (string, error) {
	return a.keychain.Get(service, account)
}

func (a *App) KeychainSet(service, account, secret string) error {
	return a.keychain.Set(service, account, secret)
}

func (a *App) KeychainDelete(service, account string) error {
	return a.keychain.Delete(service, account)
}
