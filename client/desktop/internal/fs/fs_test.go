package fs

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestScanTreeSkipsIgnoredDirs(t *testing.T) {
	root := t.TempDir()
	mkDir(t, filepath.Join(root, "src"))
	mkFile(t, filepath.Join(root, "a.txt"))
	mkFile(t, filepath.Join(root, "src", "main.py"))
	mkDir(t, filepath.Join(root, ".git"))
	mkFile(t, filepath.Join(root, ".git", "HEAD"))
	mkDir(t, filepath.Join(root, "node_modules"))
	mkFile(t, filepath.Join(root, "node_modules", "x.js"))
	mkDir(t, filepath.Join(root, "__pycache__"))
	mkFile(t, filepath.Join(root, "__pycache__", "y.pyc"))

	tree, err := ScanTree(root, 4)
	if err != nil {
		t.Fatalf("ScanTree: %v", err)
	}
	flat := flatten(tree)
	if strings.Contains(flat, ".git") || strings.Contains(flat, "node_modules") ||
		strings.Contains(flat, "__pycache__") {
		t.Fatalf("ignored dirs leaked: %s", flat)
	}
	if !strings.Contains(flat, "src/main.py") || !strings.Contains(flat, "a.txt") {
		t.Fatalf("expected files missing: %s", flat)
	}
}

func TestReadWriteFile(t *testing.T) {
	p := filepath.Join(t.TempDir(), "demo.txt")
	wr, err := WriteFile(p, "line1\nline2\n")
	if err != nil {
		t.Fatalf("WriteFile: %v", err)
	}
	if wr.Lines != 2 || wr.Bytes != 12 {
		t.Fatalf("WriteResult = %+v", wr)
	}
	fc, err := ReadFile(p)
	if err != nil {
		t.Fatalf("ReadFile: %v", err)
	}
	if fc.Content != "line1\nline2\n" || fc.Binary || fc.Truncated {
		t.Fatalf("FileContent = %+v", fc)
	}
}

func TestReadFileDetectsBinary(t *testing.T) {
	p := filepath.Join(t.TempDir(), "bin")
	if err := os.WriteFile(p, []byte{0x00, 0x01, 0x02}, 0o644); err != nil {
		t.Fatal(err)
	}
	fc, err := ReadFile(p)
	if err != nil {
		t.Fatalf("ReadFile: %v", err)
	}
	if !fc.Binary {
		t.Fatal("expected binary=true")
	}
}

func mkDir(t *testing.T, p string) {
	t.Helper()
	if err := os.MkdirAll(p, 0o755); err != nil {
		t.Fatal(err)
	}
}

func mkFile(t *testing.T, p string) {
	t.Helper()
	if err := os.MkdirAll(filepath.Dir(p), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(p, []byte("x"), 0o644); err != nil {
		t.Fatal(err)
	}
}

func flatten(n *FileNode) string {
	if n == nil {
		return ""
	}
	out := n.Path
	for _, c := range n.Children {
		out += " " + flatten(c)
	}
	return out
}
