package git

import (
	"path/filepath"
	"testing"

	"desktop/internal/store"
)

func TestDiffParsesHunks(t *testing.T) {
	dir := t.TempDir()
	runIn(t, dir, "init")
	runIn(t, dir, "config", "user.email", "t@t")
	runIn(t, dir, "config", "user.name", "T")
	mkFile(t, dir, "a.txt")
	runIn(t, dir, "add", ".")
	runIn(t, dir, "commit", "-m", "one")

	appendTo(t, filepath.Join(dir, "a.txt"), "line2\n")
	runIn(t, dir, "add", "a.txt")
	runIn(t, dir, "commit", "-m", "two")

	g := NewGit(&store.FakeKeychain{})
	hunks, err := g.Diff(dir, "HEAD~1", "HEAD")
	if err != nil {
		t.Fatalf("Diff: %v", err)
	}
	if len(hunks) == 0 {
		t.Fatal("expected at least one hunk")
	}
	found := false
	for _, h := range hunks {
		if h.Header != "" && containsHunkLine(h, "+xline2") {
			found = true
		}
	}
	if !found {
		t.Fatalf("expected +line2 in hunks: %+v", hunks)
	}
}

func containsHunkLine(h DiffHunk, want string) bool {
	for _, l := range h.Lines {
		if l == want {
			return true
		}
	}
	return false
}
