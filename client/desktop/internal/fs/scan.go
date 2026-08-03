package fs

import (
	"os"
	"path/filepath"
	"strings"
)

var IgnoreDirs = []string{".git", "node_modules", "__pycache__", "dist", ".venv", "venv"}

type FileNode struct {
	Name     string      `json:"name"`
	Path     string      `json:"path"`
	IsDir    bool        `json:"is_dir"`
	Children []*FileNode `json:"children,omitempty"`
}

func ScanTree(root string, maxDepth int) (*FileNode, error) {
	return scan(root, root, 0, maxDepth)
}

func scan(root, cur string, depth, maxDepth int) (*FileNode, error) {
	entries, err := os.ReadDir(cur)
	if err != nil {
		return nil, err
	}
	rel, _ := filepath.Rel(root, cur)
	rel = filepath.ToSlash(rel)
	if rel == "." {
		rel = ""
	}
	node := &FileNode{Name: filepath.Base(cur), Path: rel, IsDir: true}
	for _, e := range entries {
		if e.IsDir() && contains(IgnoreDirs, e.Name()) {
			continue
		}
		childPath := filepath.Join(cur, e.Name())
		relChild := strings.TrimPrefix(filepath.ToSlash(childPath), filepath.ToSlash(root)+"/")
		child := &FileNode{Name: e.Name(), Path: relChild, IsDir: e.IsDir()}
		if e.IsDir() && depth < maxDepth {
			sub, err := scan(root, childPath, depth+1, maxDepth)
			if err != nil {
				continue
			}
			child.Children = sub.Children
		}
		node.Children = append(node.Children, child)
	}
	return node, nil
}

func contains(list []string, s string) bool {
	for _, v := range list {
		if v == s {
			return true
		}
	}
	return false
}
