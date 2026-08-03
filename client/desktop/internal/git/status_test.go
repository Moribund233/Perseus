package git

import (
	"os"
	"os/exec"
	"path/filepath"
	"testing"

	"desktop/internal/store"
)

func TestStatusPorcelain(t *testing.T) {
	dir := t.TempDir()
	runIn(t, dir, "init")
	runIn(t, dir, "config", "user.email", "t@t")
	runIn(t, dir, "config", "user.name", "T")
	mkFile(t, dir, "keep.txt")
	runIn(t, dir, "add", "keep.txt")
	runIn(t, dir, "commit", "-m", "init")

	mkFile(t, dir, "new.txt")                                     // untracked
	appendTo(t, filepath.Join(dir, "keep.txt"), "more\n")         // modified

	g := NewGit(&store.FakeKeychain{})
	st, err := g.Status(dir)
	if err != nil {
		t.Fatalf("Status: %v", err)
	}
	if st.Branch != "master" && st.Branch != "main" {
		t.Fatalf("branch = %q", st.Branch)
	}
	if len(st.Untracked) != 1 || st.Untracked[0] != "new.txt" {
		t.Fatalf("untracked = %+v", st.Untracked)
	}
	if len(st.Modified) != 1 || st.Modified[0].Path != "keep.txt" {
		t.Fatalf("modified = %+v", st.Modified)
	}
}

func runIn(t *testing.T, dir string, args ...string) {
	t.Helper()
	cmd := exec.Command("git", args...)
	cmd.Dir = dir
	if out, err := cmd.CombinedOutput(); err != nil {
		t.Fatalf("git %v: %v\n%s", args, err, out)
	}
}

func mkFile(t *testing.T, dir, name string) {
	t.Helper()
	if err := os.WriteFile(filepath.Join(dir, name), []byte("x"), 0o644); err != nil {
		t.Fatal(err)
	}
}

func appendTo(t *testing.T, path, s string) {
	t.Helper()
	f, err := os.OpenFile(path, os.O_APPEND|os.O_WRONLY, 0o644)
	if err != nil {
		t.Fatal(err)
	}
	defer f.Close()
	if _, err := f.WriteString(s); err != nil {
		t.Fatal(err)
	}
}
