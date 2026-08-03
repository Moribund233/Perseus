package git

import (
	"bufio"
	"fmt"
	"strings"
)

type Credential struct {
	Type       string `json:"type"` // "none" | "token" | "ssh"
	Token      string `json:"token,omitempty"`
	SSHKeyPath string `json:"ssh_key_path,omitempty"`
}

func (g *Git) Init(dir string) error {
	_, err := g.run(dir, "init")
	return err
}

func (g *Git) Add(dir string, paths ...string) error {
	args := append([]string{"add"}, paths...)
	_, err := g.run(dir, args...)
	return err
}

func (g *Git) Commit(dir, message string) error {
	_, err := g.run(dir, "commit", "-m", message)
	return err
}

type CommitInfo struct {
	Hash    string `json:"hash"`
	Short   string `json:"short"`
	Subject string `json:"subject"`
	Author  string `json:"author"`
	Date    string `json:"date"`
}

func (g *Git) Log(dir string, n int) ([]CommitInfo, error) {
	out, err := g.run(dir, "log", fmt.Sprintf("-n%d", n),
		`--format=%H%x09%h%x09%an%x09%ai%x09%s`)
	if err != nil {
		return nil, err
	}
	var commits []CommitInfo
	sc := bufio.NewScanner(strings.NewReader(out))
	for sc.Scan() {
		f := strings.SplitN(sc.Text(), "\t", 5)
		if len(f) != 5 {
			continue
		}
		commits = append(commits, CommitInfo{Hash: f[0], Short: f[1], Author: f[2], Date: f[3], Subject: f[4]})
	}
	return commits, sc.Err()
}

func (g *Git) CurrentBranch(dir string) (string, error) {
	out, err := g.run(dir, "symbolic-ref", "--short", "HEAD")
	if err != nil {
		return "", err
	}
	return strings.TrimSpace(out), nil
}
