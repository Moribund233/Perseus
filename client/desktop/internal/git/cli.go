package git

import (
	"bytes"
	"fmt"
	"os"
	"os/exec"

	"desktop/internal/store"
)

type Git struct {
	keychain store.Keychain
}

func NewGit(kc store.Keychain) *Git {
	return &Git{keychain: kc}
}

func (g *Git) run(dir string, args ...string) (string, error) {
	cmd := exec.Command("git", args...)
	cmd.Dir = dir
	var out, errb bytes.Buffer
	cmd.Stdout = &out
	cmd.Stderr = &errb
	if err := cmd.Run(); err != nil {
		return out.String(), fmt.Errorf("git %v: %w: %s", args, err, errb.String())
	}
	return out.String(), nil
}

func (g *Git) runEnv(dir string, env []string, args ...string) (string, error) {
	cmd := exec.Command("git", args...)
	cmd.Dir = dir
	cmd.Env = append(os.Environ(), env...)
	var out, errb bytes.Buffer
	cmd.Stdout = &out
	cmd.Stderr = &errb
	if err := cmd.Run(); err != nil {
		return out.String(), fmt.Errorf("git %v: %w: %s", args, err, errb.String())
	}
	return out.String(), nil
}
