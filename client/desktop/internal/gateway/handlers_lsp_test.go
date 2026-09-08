package gateway

import (
	"encoding/base64"
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"os/exec"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/gorilla/websocket"

	"desktop/internal/lsp"
	"desktop/internal/server"
	"desktop/internal/store"
)

// gatewayEnv 组装网关 + httptest server + WS header。
type gatewayEnv struct {
	srv    *httptest.Server
	header http.Header
}

func newGatewayEnv(t *testing.T, st *store.Store, cfg Config) *gatewayEnv {
	t.Helper()
	if cfg.Servers == nil {
		cfg.Servers = server.NewRegistry(st, &store.FakeKeychain{M: map[string]string{}})
	}
	if len(cfg.AllowedOrigins) == 0 {
		cfg.AllowedOrigins = []string{"http://localhost:34115"}
	}
	g := New(cfg)
	srv := httptest.NewServer(g.Handler())
	t.Cleanup(srv.Close)
	hdr := http.Header{}
	hdr.Set("Origin", "http://localhost:34115")
	hdr.Set("X-Gateway-Token", g.Token())
	return &gatewayEnv{srv: srv, header: hdr}
}

// buildFakeLSP 编译 lsp/testdata/fake_lsp 并返回可执行路径。
func buildFakeLSP(t *testing.T) string {
	t.Helper()
	bin := t.TempDir() + "/fake_lsp.exe"
	out, err := exec.Command("go", "build", "-o", bin, "./../lsp/testdata/fake_lsp").CombinedOutput()
	if err != nil {
		t.Fatalf("build fake_lsp: %v: %s", err, out)
	}
	return bin
}

func (e *gatewayEnv) wsURL(path string) string {
	return "ws" + strings.TrimPrefix(e.srv.URL, "http") + path
}

func TestTerminalBridge(t *testing.T) {
	st, _ := store.New("")
	t.Cleanup(func() { st.Close() })
	ws, err := st.CreateWorkspace(store.Workspace{Name: "t", Path: t.TempDir()})
	if err != nil {
		t.Fatal(err)
	}

	termOut := make(chan []byte, 16)
	termIn := make(chan []byte, 16)
	termHandles := &fakeTermProto{outCh: termOut, inCh: termIn}
	var once sync.Once
	env := newGatewayEnv(t, st, Config{
		Store: st,
		TermFactory: func(_ string, _, _ int) (termSession, error) {
			once.Do(func() {
				termOut <- []byte("Hello-Term\n")
				termOut <- []byte("prompt> ")
			})
			return termHandles, nil
		},
	})

	conn, resp, err := websocket.DefaultDialer.Dial(env.wsURL("/api/local/workspaces/"+ws.ID+"/terminal"), env.header)
	if err != nil {
		t.Fatalf("dial terminal ws: %v (status=%d)", err, resp.StatusCode)
	}
	defer conn.Close()

	// 读取预置输出帧，验证 base64 透传
	conn.SetReadDeadline(time.Now().Add(5 * time.Second))
	_, data, err := conn.ReadMessage()
	if err != nil {
		t.Fatalf("read output: %v", err)
	}
	var m termMessage
	if err := json.Unmarshal(data, &m); err != nil {
		t.Fatalf("bad msg: %v", err)
	}
	dec, _ := base64.StdEncoding.DecodeString(m.Data)
	if string(dec) != "Hello-Term\n" {
		t.Fatalf("output = %q", dec)
	}

	// 发送输入帧 → fakeTerm 收到原始字节
	payload, _ := json.Marshal(termMessage{Type: "input", Data: base64.StdEncoding.EncodeToString([]byte("dir\r\n"))})
	if err := conn.WriteMessage(websocket.TextMessage, payload); err != nil {
		t.Fatal(err)
	}
	select {
	case got := <-termIn:
		if string(got) != "dir\r\n" {
			t.Fatalf("term input = %q", got)
		}
	case <-time.After(5 * time.Second):
		t.Fatal("fake term did not receive input")
	}
}

type fakeTermProto struct {
	outCh chan []byte
	inCh  chan []byte
}

func (f *fakeTermProto) Read(b []byte) (int, error) {
	data, ok := <-f.outCh
	if !ok {
		return 0, io.EOF
	}
	return copy(b, data), nil
}

func (f *fakeTermProto) Write(b []byte) (int, error) {
	f.inCh <- append([]byte(nil), b...)
	return len(b), nil
}

func (f *fakeTermProto) Resize(cols, rows int) error { return nil }

func (f *fakeTermProto) Close() error {
	close(f.outCh)
	close(f.inCh)
	return nil
}

func TestLSPBridge(t *testing.T) {
	st, _ := store.New("")
	t.Cleanup(func() { st.Close() })
	ws, err := st.CreateWorkspace(store.Workspace{Name: "t", Path: t.TempDir()})
	if err != nil {
		t.Fatal(err)
	}

	bin := buildFakeLSP(t)
	reg := lsp.Registry{
		"fake": {Language: "fake", DisplayName: "Fake LSP", Command: []string{bin}, Extensions: []string{".py"}},
	}
	env := newGatewayEnv(t, st, Config{Store: st, LSP: lsp.NewManagerWithRegistry(reg)})

	conn, resp, err := websocket.DefaultDialer.Dial(env.wsURL("/api/local/workspaces/"+ws.ID+"/lsp?lang=fake"), env.header)
	if err != nil {
		t.Fatalf("dial lsp ws: %v (status=%d)", err, resp.StatusCode)
	}
	defer conn.Close()

	conn.SetReadDeadline(time.Now().Add(5 * time.Second))
	if err := conn.WriteMessage(websocket.TextMessage, []byte(`{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}`)); err != nil {
		t.Fatal(err)
	}
	_, data, err := conn.ReadMessage()
	if err != nil {
		t.Fatalf("read initialize response: %v", err)
	}
	var initResp struct {
		ID     int `json:"id"`
		Result struct {
			Capabilities map[string]any `json:"capabilities"`
		} `json:"result"`
	}
	if err := json.Unmarshal(data, &initResp); err != nil || initResp.ID != 1 {
		t.Fatalf("bad initialize response: %s", data)
	}
	if initResp.Result.Capabilities["positionEncoding"] != "utf-8" {
		t.Fatalf("unexpected capabilities: %s", data)
	}

	if err := conn.WriteMessage(websocket.TextMessage, []byte(`{"jsonrpc":"2.0","method":"textDocument/didOpen","params":{"textDocument":{"uri":"file:///fake.py"}}}`)); err != nil {
		t.Fatal(err)
	}
	_, diag, err := conn.ReadMessage()
	if err != nil {
		t.Fatalf("read diagnostics: %v", err)
	}
	if !strings.Contains(string(diag), "publishDiagnostics") || !strings.Contains(string(diag), "fake error") {
		t.Fatalf("diag = %s", diag)
	}
}

func TestLSPBridgeUnsupportedLang(t *testing.T) {
	st, _ := store.New("")
	t.Cleanup(func() { st.Close() })
	ws, err := st.CreateWorkspace(store.Workspace{Name: "t", Path: t.TempDir()})
	if err != nil {
		t.Fatal(err)
	}
	bin := buildFakeLSP(t)
	reg := lsp.Registry{"fake": {Language: "fake", Command: []string{bin}}}
	env := newGatewayEnv(t, st, Config{Store: st, LSP: lsp.NewManagerWithRegistry(reg)})

	_, resp, err := websocket.DefaultDialer.Dial(env.wsURL("/api/local/workspaces/"+ws.ID+"/lsp?lang=rust"), env.header)
	if err == nil {
		t.Fatal("expected dial error for unsupported lang")
	}
	if resp == nil || resp.StatusCode != http.StatusBadRequest {
		t.Fatalf("expected 400, got %v", resp)
	}
}