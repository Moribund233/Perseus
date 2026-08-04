package gateway

import (
	"crypto/rand"
	"encoding/hex"
	"net"
	"net/http"
	"time"

	"desktop/internal/git"
	"desktop/internal/server"
	"desktop/internal/store"
)

type Config struct {
	Store          *store.Store
	Git            *git.Git
	Servers        *server.Registry
	AllowedOrigins []string
}

type Gateway struct {
	store    *store.Store
	git      *git.Git
	servers  *server.Registry
	origins  map[string]bool
	token    string
	addr     string
	listener net.Listener
	server   *http.Server
	handler  http.Handler
	cache    *proxyCache
	proxy    *http.Client
}

func New(cfg Config) *Gateway {
	if len(cfg.AllowedOrigins) == 0 {
		cfg.AllowedOrigins = []string{"http://localhost:34115", "wails://localhost"}
	}
	g := &Gateway{
		store:   cfg.Store,
		git:     cfg.Git,
		servers: cfg.Servers,
		origins: map[string]bool{},
		token:   newToken(),
		cache:   newProxyCache(200, 10<<20, 24*time.Hour),
		proxy:   &http.Client{Timeout: 30 * time.Second},
	}
	for _, o := range cfg.AllowedOrigins {
		g.origins[o] = true
	}
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
	return g.origins[origin]
}

func (g *Gateway) validToken(t string) bool {
	return t != "" && t == g.token
}
