package fs

import (
	"bytes"
	"os"
	"path/filepath"
	"strings"
)

const MaxReadSize = 2 << 20

type FileContent struct {
	Content   string `json:"content"`
	Binary    bool   `json:"binary"`
	Truncated bool   `json:"truncated"`
	Size      int64  `json:"size"`
}

type WriteResult struct {
	Lines int `json:"lines"`
	Bytes int `json:"bytes"`
}

func ReadFile(path string) (*FileContent, error) {
	info, err := os.Stat(path)
	if err != nil {
		return nil, err
	}
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	fc := &FileContent{Size: info.Size(), Truncated: info.Size() > MaxReadSize}
	fc.Binary = isBinary(data)
	if !fc.Binary {
		fc.Content = string(data)
		if fc.Truncated {
			fc.Content = truncateTo(fc.Content, MaxReadSize)
		}
	}
	return fc, nil
}

func WriteFile(path string, content string) (WriteResult, error) {
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return WriteResult{}, err
	}
	b := []byte(content)
	if err := os.WriteFile(path, b, 0o644); err != nil {
		return WriteResult{}, err
	}
	return WriteResult{Lines: strings.Count(content, "\n"), Bytes: len(b)}, nil
}

func isBinary(data []byte) bool {
	sample := data
	if len(sample) > 512 {
		sample = sample[:512]
	}
	if bytes.IndexByte(sample, 0) >= 0 {
		return true
	}
	return false
}

func truncateTo(s string, n int) string {
	r := []rune(s)
	if len(r) <= n {
		return s
	}
	return string(r[:n])
}
