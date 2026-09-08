package git

import (
	"bufio"
	"strings"
)

type DiffHunk struct {
	Header string   `json:"header"`
	Lines  []string `json:"lines"`
}

// Show 读取 HEAD 中指定文件的内容（Monaco Diff 视图 original 侧）。
func (g *Git) Show(dir, path string) (string, error) {
	return g.run(dir, "show", "HEAD:"+path)
}

func (g *Git) Diff(dir, a, b string) ([]DiffHunk, error) {
	args := []string{"diff", "--no-color", "-U3"}
	if a != "" {
		args = append(args, a)
	}
	if b != "" {
		args = append(args, b)
	}
	out, err := g.run(dir, args...)
	if err != nil {
		return nil, err
	}
	return parseDiff(out), nil
}

func parseDiff(out string) []DiffHunk {
	var hunks []DiffHunk
	var cur *DiffHunk
	sc := bufio.NewScanner(strings.NewReader(out))
	for sc.Scan() {
		line := sc.Text()
		if strings.HasPrefix(line, "@@") {
			if cur != nil {
				hunks = append(hunks, *cur)
			}
			cur = &DiffHunk{Header: line}
			continue
		}
		if cur == nil {
			continue
		}
		cur.Lines = append(cur.Lines, line)
	}
	if cur != nil {
		hunks = append(hunks, *cur)
	}
	return hunks
}
