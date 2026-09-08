//go:build windows

package gateway

import (
	"desktop/internal/term"
)

// setupTermFactory 默认以 ConPTY 启动 shell（工作目录=工作区路径）。
// 测试可注入 fake termFactory。
func (g *Gateway) setupTermFactory(cfg Config) {
	if cfg.TermFactory != nil {
		g.termFactory = cfg.TermFactory
		return
	}
	g.termFactory = func(path string, cols, rows int) (termSession, error) {
		t, err := term.Start(path, cols, rows)
		if err != nil {
			return nil, err
		}
		return t, nil
	}
}