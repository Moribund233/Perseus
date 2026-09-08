package gateway

import (
	"crypto/rand"
	"encoding/hex"
	"net"
	"net/http"
	"net/url"
	"strings"
	"time"

	"desktop/internal/git"
	"desktop/internal/lsp"
	"desktop/internal/server"
	"desktop/internal/store"
)

type Config struct {
	Store          *store.Store
	Git            *git.Git
	Servers        *server.Registry
	LSP            *lsp.Manager
	TermFactory    termFactory
	AllowedOrigins []string
}

type Gateway struct {
	store    *store.Store
	git      *git.Git
	servers  *server.Registry
	lsp      *lsp.Manager
	origins  map[string]bool
	token    string
	addr     string
	listener net.Listener
	server   *http.Server
	handler  http.Handler
	cache    *proxyCache
	proxy    *http.Client
	termFactory termFactory
}

func New(cfg Config) *Gateway {
	if len(cfg.AllowedOrigins) == 0 {
		cfg.AllowedOrigins = []string{"http://localhost:34115", "wails://localhost"}
	}
	if cfg.LSP == nil {
		cfg.LSP = lsp.NewManager()
	}
	g := &Gateway{
		store:   cfg.Store,
		git:     cfg.Git,
		servers: cfg.Servers,
		lsp:     cfg.LSP,
		origins: map[string]bool{},
		token:   newToken(),
		cache:   newProxyCache(200, 10<<20, 24*time.Hour),
		proxy:   &http.Client{Timeout: 30 * time.Second},
	}
	for _, o := range cfg.AllowedOrigins {
		g.origins[o] = true
	}
	g.setupTermFactory(cfg)
	g.handler = g.buildRouter()
	return g
}

func newToken() string {
	b := make([]byte, 16)
	_, _ = rand.Read(b)
	return hex.EncodeToString(b)
}

func (g *Gateway) Start() error {
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		return err
	}
	g.listener = ln
	g.addr = ln.Addr().String()
	g.server = &http.Server{Handler: g.handler}
	go func() { _ = g.server.Serve(ln) }()
	return nil
}

func (g *Gateway) Addr() string  { return g.addr }
func (g *Gateway) Token() string { return g.token }

func (g *Gateway) Stop() error {
	if g.server != nil {
		return g.server.Close()
	}
	return nil
}

func (g *Gateway) Handler() http.Handler { return g.handler }

func (g *Gateway) originAllowed(origin string) bool {
	if g.origins[origin] {
		return true
	}
	// dev 模式: 前端由 Vite/Wails DevServer 提供, 端口不固定, 且 WebView2 中
	// Wails dev server 的 origin 是 http://wails.localhost:<port>。
	// 放行本机回环/保留域 (*.localhost, RFC 6761, 仅本机解析) 的 http(s) origin;
	// 数据安全边界仍是随机 gateway token (外部页面拿不到 token, 请求会 401),
	// CORS 只是第二道门。
	if u, err := url.Parse(origin); err == nil {
		host := u.Hostname()
		loopback := host == "localhost" || host == "127.0.0.1" || host == "::1" ||
			strings.HasSuffix(host, ".localhost")
		if (u.Scheme == "http" || u.Scheme == "https") && loopback {
			return true
		}
	}
	return false
}

func (g *Gateway) validToken(t string) bool {
	return t != "" && t == g.token
}
