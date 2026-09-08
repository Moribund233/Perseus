package lsp

import (
	"bytes"
	"io"
	"strings"
	"testing"
)

func TestFrameRoundTrip(t *testing.T) {
	var buf bytes.Buffer
	fw := NewFrameWriter(&buf)
	fr := NewFrameReader(&buf)

	for _, body := range []string{
		`{"jsonrpc":"2.0","id":1,"method":"initialize"}`,
		`{"jsonrpc":"2.0","method":"textDocument/didOpen","params":{"textDocument":{"uri":"file:///a.py","text":"print(1)"}}}`,
		`{"jsonrpc":"2.0","id":1,"result":{"capabilities":{}}}`,
	} {
		fw.WriteJSON([]byte(body))
		got, err := fr.Next()
		if err != nil {
			t.Fatalf("Next: %v", err)
		}
		if string(got) != body {
			t.Fatalf("round trip mismatch:\n got %s\nwant %s", got, body)
		}
	}
}

func TestFrameReaderChunkedWrites(t *testing.T) {
	// 逐字节写入，验证很小的读缓冲也能正确重组帧。
	raw := "Content-Length: 17\r\n\r\n{\"jsonrpc\":\"2.0\"}"
	pr, pw := io.Pipe()
	go func() {
		defer pw.Close()
		for i := 0; i < len(raw); i++ {
			_, _ = pw.Write([]byte{raw[i]})
		}
	}()
	got, err := NewFrameReader(pr).Next()
	if err != nil {
		t.Fatalf("Next: %v", err)
	}
	if string(got) != `{"jsonrpc":"2.0"}` {
		t.Fatalf("got %q", got)
	}
}

func TestFrameReaderHeaderWhitespace(t *testing.T) {
	raw := "Content-Length : 17    \r\nContent-Type: application/vscode-jsonrpc; charset=utf-8\r\n\r\n{\"jsonrpc\":\"2.0\"}"
	got, err := NewFrameReader(strings.NewReader(raw)).Next()
	if err != nil {
		t.Fatalf("Next: %v", err)
	}
	if string(got) != `{"jsonrpc":"2.0"}` {
		t.Fatalf("got %q", got)
	}
}

func TestFrameReaderEOF(t *testing.T) {
	_, err := NewFrameReader(strings.NewReader("Content-Length: 100\r\n\r\nshort")).Next()
	if err != io.EOF && err != io.ErrUnexpectedEOF {
		t.Fatalf("want EOF-ish error, got %v", err)
	}
}

func TestFrameReaderMalformed(t *testing.T) {
	_, err := NewFrameReader(strings.NewReader("nonsense\r\n\r\n")).Next()
	if err == nil {
		t.Fatal("want error for missing Content-Length")
	}
	_, err = NewFrameReader(strings.NewReader("Content-Length: -5\r\n\r\n")).Next()
	if err == nil {
		t.Fatal("want error for negative length")
	}
}