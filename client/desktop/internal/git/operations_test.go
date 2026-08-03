package git

import (
	"path/filepath"
	"testing"

	"desktop/internal/store"
)

func TestCommitAndLog(t *testing.T) {
	dir := t.TempDir()
	runIn(t, dir, "init")
	runIn(t, dir, "config", "user.email", "t@t")
	runIn(t, dir, "config", "user.name", "T")
	mkFile(t, dir, "f.txt")

	g := NewGit(&store.FakeKeychain{})
	if err := g.Add(dir, "."); err != nil {
		t.Fatalf("Add: %v", err)
	}
	if err := g.Commit(dir, "feat: first"); err != nil {
		t.Fatalf("Commit: %v", err)
	}
	commits, err := g.Log(dir, 5)
	if err != nil {
		t.Fatalf("Log: %v", err)
	}
	if len(commits) != 1 || commits[0].Subject != "feat: first" {
		t.Fatalf("commits = %+v", commits)
	}
	br, err := g.CurrentBranch(dir)
	if err != nil || br == "" {
		t.Fatalf("CurrentBranch = %q, err %v", br, err)
	}
}

func TestCloneAndPushPull(t *testing.T) {
	src := t.TempDir()
	runIn(t, src, "init")
	runIn(t, src, "config", "user.email", "t@t")
	runIn(t, src, "config", "user.name", "T")
	runIn(t, src, "config", "receive.denyCurrentBranch", "ignore")
	mkFile(t, src, "x.txt")
	runIn(t, src, "add", ".")
	runIn(t, src, "commit", "-m", "seed")

	dest := filepath.Join(t.TempDir(), "clone")
	g := NewGit(&store.FakeKeychain{})
	if err := g.Clone(src, dest, Credential{Type: "none"}); err != nil {
		t.Fatalf("Clone: %v", err)
	}

	// 在 clone 中新增提交并 push 回 src
	mkFile(t, dest, "y.txt")
	runIn(t, dest, "config", "user.email", "t@t")
	runIn(t, dest, "config", "user.name", "T")
	if err := g.Add(dest, "."); err != nil {
		t.Fatalf("Add: %v", err)
	}
	if err := g.Commit(dest, "feat: second"); err != nil {
		t.Fatalf("Commit: %v", err)
	}
	br, err := g.CurrentBranch(dest)
	if err != nil {
		t.Fatalf("CurrentBranch: %v", err)
	}
	if err := g.Push(dest, "origin", br, Credential{Type: "none"}); err != nil {
		t.Fatalf("Push: %v", err)
	}
}
