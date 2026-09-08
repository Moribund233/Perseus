package lsp

import (
	"encoding/json"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"testing"
	"time"
)

var (
	buildOnce sync.Once
	binPath   string
	binErr    error
)

// fakeLspPath 编译并返回 fake_lsp 可执行文件路径（每轮测试一次）。
func fakeLspPath(t *testing.T) string {
	t.Helper()
	buildOnce.Do(func() {
		dir, err := os.MkdirTemp("", "fake_lsp_bin_")
		if err != nil {
			binErr = err
			return
		}
		binPath = filepath.Join(dir, "fake_lsp.exe")
		out, err := exec.Command("go", "build", "-o", binPath, "./testdata/fake_lsp").CombinedOutput()
		if err != nil {
			binErr = &buildError{out: string(out), err: err}
			return
		}
	})
	if binErr != nil {
		t.Fatalf("build fake_lsp: %v", binErr)
	}
	return binPath
}

type buildError struct {
	out string
	err error
}

func (e *buildError) Error() string { return e.err.Error() + ": " + e.out }

func fakeLspServer(t *testing.T, crashFile string) Server {
	srv := Server{
		Language: "fake",
		Command:  []string{fakeLspPath(t)},
	}
	if crashFile != "" {
		srv.Env = append(srv.Env, "FAKE_LSP_CRASH_FILE="+crashFile)
	}
	return srv
}

// waitOut 从会话 out 通道读取直到谓词命中（默认 8s 超时）。
func waitOut(t *testing.T, sess *Session, pred func([]byte) bool) []byte {
	t.Helper()
	deadline := time.After(8 * time.Second)
	for {
		select {
		case body := <-sess.Out():
			if pred(body) {
				return body
			}
		case <-deadline:
			t.Fatalf("timeout waiting for LSP message")
			return nil
		}
	}
}

func isResponseID(body []byte, id int) bool {
	var m struct {
		ID     json.RawMessage `json:"id"`
		Method string          `json:"method,omitempty"`
	}
	if json.Unmarshal(body, &m) != nil {
		return false
	}
	var got int
	return json.Unmarshal(m.ID, &got) == nil && got == id
}

func isMethod(body []byte, method string) bool {
	var m struct{ Method string `json:"method"` }
	return json.Unmarshal(body, &m) == nil && m.Method == method
}

func sendInit(sess *Session, id int) error {
	return sess.Send([]byte(`{"jsonrpc":"2.0","id":` + strconv.Itoa(id) + `,"method":"initialize","params":{"processId":1,"capabilities":{},"rootUri":null}}`))
}

func TestSessionInitializeAndDiagnostics(t *testing.T) {
	root := t.TempDir()
	sess, err := NewSession(root, fakeLspServer(t, ""))
	if err != nil {
		t.Fatalf("NewSession: %v", err)
	}
	defer sess.Close()

	if err := sendInit(sess, 1); err != nil {
		t.Fatalf("sendInit: %v", err)
	}
	resp := waitOut(t, sess, func(b []byte) bool { return isResponseID(b, 1) })
	var m struct {
		Result struct {
			Capabilities map[string]any `json:"capabilities"`
		} `json:"result"`
	}
	if err := json.Unmarshal(resp, &m); err != nil || m.Result.Capabilities["positionEncoding"] != "utf-8" {
		t.Fatalf("unexpected initialize result: %s", resp)
	}

	if err := sess.Send([]byte(`{"jsonrpc":"2.0","method":"textDocument/didOpen","params":{"textDocument":{"uri":"file:///fake.py","languageId":"python","version":1,"text":"print(1)"}}}`)); err != nil {
		t.Fatalf("didOpen: %v", err)
	}
	diag := waitOut(t, sess, func(b []byte) bool { return isMethod(b, "textDocument/publishDiagnostics") })
	if !strings.Contains(string(diag), "fake error") {
		t.Fatalf("diagnostics missing fake error: %s", diag)
	}
}

func TestSessionCrashRestart(t *testing.T) {
	crashFile := filepath.Join(t.TempDir(), "crashes.txt")
	if err := os.WriteFile(crashFile, []byte("1"), 0o600); err != nil {
		t.Fatal(err)
	}
	root := t.TempDir()
	sess, err := NewSession(root, fakeLspServer(t, crashFile))
	if err != nil {
		t.Fatalf("NewSession: %v", err)
	}
	defer sess.Close()

	// gen0 启动即崩溃 → 会话注入重启通知（新一代进程）
	_ = waitOut(t, sess, func(b []byte) bool { return isMethod(b, RestartNotification) })

	// 客户端按规范在收到通知后重新 initialize
	if err := sendInit(sess, 1); err != nil {
		t.Fatalf("sendInit: %v", err)
	}
	resp := waitOut(t, sess, func(b []byte) bool { return isResponseID(b, 1) })
	if !strings.Contains(string(resp), "positionEncoding") {
		t.Fatalf("unexpected restart response: %s", resp)
	}
}

func TestSessionPermanentFailure(t *testing.T) {
	crashFile := filepath.Join(t.TempDir(), "crashes.txt")
	if err := os.WriteFile(crashFile, []byte("4"), 0o600); err != nil {
		t.Fatal(err)
	}
	sess, err := NewSession(t.TempDir(), fakeLspServer(t, crashFile))
	if err != nil {
		t.Fatalf("NewSession: %v", err)
	}
	defer sess.Close()

	// 4 次启动即崩 > MaxRestarts(3)：最终失败，会话关闭
	select {
	case <-sess.Closed():
	case <-time.After(15 * time.Second):
		t.Fatal("session did not close after repeated crashes")
	}
	if sess.Err() == nil {
		t.Fatal("expected final error after repeated crashes")
	}
}