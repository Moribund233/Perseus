package git

import (
	"bufio"
	"strconv"
	"strings"
)

type StatusEntry struct {
	X            string `json:"x"`
	Y            string `json:"y"`
	Path         string `json:"path"`
	OriginalPath string `json:"original_path,omitempty"`
}

type StatusResult struct {
	Branch    string        `json:"branch"`
	Ahead     int           `json:"ahead"`
	Behind    int           `json:"behind"`
	Staged    []StatusEntry `json:"staged"`
	Modified  []StatusEntry `json:"modified"`
	Untracked []string      `json:"untracked"`
}

func (g *Git) Status(dir string) (*StatusResult, error) {
	out, err := g.run(dir, "status", "--porcelain=v2", "--branch")
	if err != nil {
		return nil, err
	}
	res := &StatusResult{}
	sc := bufio.NewScanner(strings.NewReader(out))
	for sc.Scan() {
		line := sc.Text()
		switch {
		case strings.HasPrefix(line, "# branch.head "):
			res.Branch = strings.TrimPrefix(line, "# branch.head ")
		case strings.HasPrefix(line, "# branch.ab "):
			ab := strings.TrimPrefix(line, "# branch.ab ")
			parseAb(ab, res)
		case strings.HasPrefix(line, "1 "):
			f := strings.Fields(line[2:])
			if len(f) >= 8 {
				e := StatusEntry{X: xy(f[0], 0), Y: xy(f[0], 1), Path: f[7]}
				res.Modified = append(res.Modified, e)
			}
		case strings.HasPrefix(line, "2 "):
			f := strings.Fields(line[2:])
			if len(f) >= 9 {
				e := StatusEntry{X: xy(f[0], 0), Y: xy(f[0], 1), Path: f[8]}
				if len(f) >= 10 {
					e.OriginalPath = f[9]
				}
				res.Modified = append(res.Modified, e)
			}
		case strings.HasPrefix(line, "?"):
			f := strings.Fields(line[1:])
			if len(f) >= 1 {
				res.Untracked = append(res.Untracked, f[0])
			}
		}
	}
	// 拆分 staged/modified：X 非 '.' 或非 0 → staged
	var staged, modified []StatusEntry
	for _, e := range res.Modified {
		if e.X != "." && e.X != "?" && e.X != " " {
			staged = append(staged, e)
		} else {
			modified = append(modified, e)
		}
	}
	res.Staged, res.Modified = staged, modified
	return res, sc.Err()
}

func xy(pair string, i int) string {
	if len(pair) > i {
		return string(pair[i])
	}
	return "."
}

func parseAb(ab string, res *StatusResult) {
	// 格式: +<ahead> -<behind>，可能只有一边
	fields := strings.Fields(ab)
	for _, f := range fields {
		if strings.HasPrefix(f, "+") {
			res.Ahead, _ = strconv.Atoi(strings.TrimPrefix(f, "+"))
		} else if strings.HasPrefix(f, "-") {
			res.Behind, _ = strconv.Atoi(strings.TrimPrefix(f, "-"))
		}
	}
}
