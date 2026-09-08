//fake_lsp 是测试用的最小语言服务器：走真实 LSP Content-Length 帧协议。
// 行为：
//   - initialize            → id 回显 + capabilities(positionEncoding=utf-8)
//   - textDocument/didOpen  → 推送 1 条 publishDiagnostics（1 个错误）
//   - shutdown              → result:null（随后收到 exit → 进程退出 0）
//   - initialized           → 无响应
//
// 崩溃注入（重启/永久失败测试）：
//   FAKE_LSP_CRASH_FILE=<path> 文件包含剩余崩溃次数 N：进程每次启动，
//   N>0 则 N-- 写回并 os.Exit(1)；N=0 正常运行。文件随会话保留，重启后继续计数。
package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"strconv"
	"strings"
)

func main() {
	crashFile := os.Getenv("FAKE_LSP_CRASH_FILE")
	// 进程启动即检查崩溃计数（模拟"服务器一启动就崩"），重启后基于文件继续计数。
	if crashFile != "" && crashArmed(crashFile) {
		os.Exit(1)
	}

	r := bufio.NewReader(os.Stdin)
	out := bufio.NewWriter(os.Stdout)
	shutdown := false

	for {
		payload, err := readFrame(r)
		if err != nil {
			return
		}
		var msg struct {
			ID     json.RawMessage `json:"id,omitempty"`
			Method string          `json:"method,omitempty"`
		}
		if err := json.Unmarshal(payload, &msg); err != nil {
			continue
		}
		switch msg.Method {
		case "initialize":
			sendResult(out, msg.ID, `{"capabilities":{"positionEncoding":"utf-8","textDocumentSync":{"openClose":true,"change":2}}}`)
		case "initialized":
			// 无响应
		case "textDocument/didOpen":
			var m struct {
				Params struct {
					TextDocument struct {
						URI string `json:"uri"`
					} `json:"textDocument"`
				} `json:"params"`
			}
			_ = json.Unmarshal(payload, &m)
			body := fmt.Sprintf(`{"jsonrpc":"2.0","method":"textDocument/publishDiagnostics","params":{"uri":%q,"diagnostics":[{"range":{"start":{"line":0,"character":0},"end":{"line":0,"character":5}},"severity":1,"message":"fake error","source":"fake-lsp"}]}}`, m.Params.TextDocument.URI)
			sendRaw(out, body)
		case "shutdown":
			shutdown = true
			sendResult(out, msg.ID, `null`)
		case "exit":
			_ = shutdown
			os.Exit(0)
		}
	}
}

// crashArmed 读取剩余崩溃次数；>0 时减一并返回 true（进程将崩溃）。
func crashArmed(path string) bool {
	b, err := os.ReadFile(path)
	if err != nil {
		return false
	}
	n, err := strconv.Atoi(strings.TrimSpace(string(b)))
	if err != nil || n <= 0 {
		return false
	}
	_ = os.WriteFile(path, []byte(strconv.Itoa(n-1)), 0o600)
	return true
}

// readFrame 读一条 LSP 帧正文。
func readFrame(r *bufio.Reader) ([]byte, error) {
	length := 0
	for {
		line, err := r.ReadString('\n')
		if err != nil {
			return nil, err
		}
		line = strings.TrimRight(line, "\r\n")
		if line == "" {
			break
		}
		name, value, found := strings.Cut(line, ":")
		if found && strings.EqualFold(strings.TrimSpace(name), "Content-Length") {
			if n, err := strconv.Atoi(strings.TrimSpace(value)); err == nil && n >= 0 {
				length = n
			}
		}
	}
	body := make([]byte, length)
	_, err := io.ReadFull(r, body)
	return body, err
}

// sendResult 发送一条带请求 id 的 result 响应帧。
func sendResult(w *bufio.Writer, id json.RawMessage, result string) {
	if len(id) == 0 {
		return
	}
	body := fmt.Sprintf(`{"jsonrpc":"2.0","id":%s,"result":%s}`, id, result)
	sendRaw(w, body)
}

// sendRaw 写入一条带 Content-Length 帧头的正文并 flush。
func sendRaw(w *bufio.Writer, body string) {
	fmt.Fprintf(w, "Content-Length: %d\r\n\r\n", len(body))
	w.WriteString(body)
	_ = w.Flush()
}