package gateway

import (
	"bytes"
	"testing"
)

func encodeAuthFrame(docName, token, version string, trailing []byte) []byte {
	var buf bytes.Buffer
	writeVarString(&buf, docName)
	writeVarUint(&buf, collabMessageTypeAuth)
	writeVarUint(&buf, collabAuthSubTypeToken)
	writeVarString(&buf, token)
	writeVarString(&buf, version)
	buf.Write(trailing)
	return buf.Bytes()
}

func parseAuthFrame(t *testing.T, frame []byte) (docName, token, version string, trailing []byte) {
	t.Helper()
	var ok bool
	docName, n1, ok := readVarString(frame, 0)
	if !ok {
		t.Fatal("readVarString docName failed")
	}
	msgType, n2, _ := readVarUint(frame, n1)
	if msgType != collabMessageTypeAuth {
		t.Fatalf("msgType = %d, want %d", msgType, collabMessageTypeAuth)
	}
	subType, n3, _ := readVarUint(frame, n2)
	if subType != collabAuthSubTypeToken {
		t.Fatalf("subType = %d, want %d", subType, collabAuthSubTypeToken)
	}
	token, n4, ok := readVarString(frame, n3)
	if !ok {
		t.Fatal("readVarString token failed")
	}
	version, n5, ok := readVarString(frame, n4)
	if !ok {
		t.Fatal("readVarString version failed")
	}
	trailing = frame[n5:]
	return docName, token, version, trailing
}

func TestLib0VarUintRoundTrip(t *testing.T) {
	values := []uint64{0, 1, 127, 128, 16383, 16384, 2097151, 2097152, 1<<31 - 1, 1 << 40}
	for _, v := range values {
		var buf bytes.Buffer
		writeVarUint(&buf, v)
		got, next, ok := readVarUint(buf.Bytes(), 0)
		if !ok || got != v || next != buf.Len() {
			t.Fatalf("varUint roundtrip %d: got %d, next %d, len %d, ok %v", v, got, next, buf.Len(), ok)
		}
	}
}

func TestLib0VarStringRoundTrip(t *testing.T) {
	for _, s := range []string{"", "repo:main:src/a.ts", "中文路径/a.py", string(make([]byte, 300))} {
		var buf bytes.Buffer
		writeVarString(&buf, s)
		got, next, ok := readVarString(buf.Bytes(), 0)
		if !ok || got != s || next != buf.Len() {
			t.Fatalf("varString roundtrip %q: got %q, ok %v", s, got, ok)
		}
	}
}

func TestRewriteCollabAuthFrameReplacesToken(t *testing.T) {
	old := encodeAuthFrame("repo-1:main:src/app.py", "old.jwt.token", "4.6.0", nil)
	rewritten, changed := rewriteCollabAuthFrame(old, "new.jwt.token")
	if !changed {
		t.Fatal("expected frame rewrite")
	}
	docName, token, version, trailing := parseAuthFrame(t, rewritten)
	if docName != "repo-1:main:src/app.py" {
		t.Fatalf("docName = %q", docName)
	}
	if token != "new.jwt.token" {
		t.Fatalf("token = %q, want new token", token)
	}
	if version != "4.6.0" {
		t.Fatalf("version = %q", version)
	}
	if len(trailing) != 0 {
		t.Fatalf("trailing = %v", trailing)
	}
}

func TestRewriteCollabAuthFrameTrailingBytes(t *testing.T) {
	trailing := []byte{0xde, 0xad, 0xbe, 0xef}
	old := encodeAuthFrame("doc", "old", "4.6.0", trailing)
	rewritten, changed := rewriteCollabAuthFrame(old, "new")
	if !changed {
		t.Fatal("expected frame rewrite")
	}
	_, _, _, got := parseAuthFrame(t, rewritten)
	if !bytes.Equal(got, trailing) {
		t.Fatalf("trailing = %v, want %v", got, trailing)
	}
}

func TestRewriteCollabAuthFrameNonAuthPassthrough(t *testing.T) {
	// MessageType.Sync = 0 非认证帧 → 原样透传
	var buf bytes.Buffer
	writeVarString(&buf, "doc")
	writeVarUint(&buf, 0)
	frame := buf.Bytes()
	rewritten, changed := rewriteCollabAuthFrame(frame, "new")
	if changed {
		t.Fatal("non-auth frame must not be rewritten")
	}
	if !bytes.Equal(frame, rewritten) {
		t.Fatal("frame mutated on passthrough")
	}

	// 错误子类型（PermissionDenied=1）→ 透传
	buf.Reset()
	writeVarString(&buf, "doc")
	writeVarUint(&buf, collabMessageTypeAuth)
	writeVarUint(&buf, 1)
	frame = buf.Bytes()
	if _, changed := rewriteCollabAuthFrame(frame, "new"); changed {
		t.Fatal("wrong sub-type must not be rewritten")
	}

	// 截断帧 → 透传
	if _, changed := rewriteCollabAuthFrame([]byte{0x05, 0x61}, "new"); changed {
		t.Fatal("truncated frame must not be rewritten")
	}
}

func TestCollabEndpoint(t *testing.T) {
	cases := map[string]string{
		"http://127.0.0.1:8000": "ws://127.0.0.1:8000/ws/collab",
		"https://perseus.local": "wss://perseus.local/ws/collab",
		"http://host/api":       "ws://host/ws/collab",
	}
	for base, want := range cases {
		if got := collabEndpoint(base); got != want {
			t.Fatalf("collabEndpoint(%q) = %q, want %q", base, got, want)
		}
	}
}
