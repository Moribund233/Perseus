//go:build windows

// Package term 封装 Windows ConPTY：为网关终端 WS 桥提供本地 shell 会话。
package term

import (
	"fmt"
	"os/exec"

	"github.com/UserExistsError/conpty"
)

// Term 一个 ConPTY 终端会话。
type Term struct {
	pty *conpty.ConPty
}

// Start 在 dir 目录启动一个交互式 shell（优先 pwsh，回退 powershell/cmd）。
func Start(dir string, cols, rows int) (*Term, error) {
	shell := shellPath()
	pty, err := conpty.Start(
		shell,
		conpty.ConPtyWorkDir(dir),
		conpty.ConPtyDimensions(cols, rows),
	)
	if err != nil {
		return nil, fmt.Errorf("start %s: %w", shell, err)
	}
	return &Term{pty: pty}, nil
}

// shellPath 选择可用的交互式 shell。
func shellPath() string {
	for _, c := range []string{"pwsh.exe", "powershell.exe", "cmd.exe"} {
		if p, err := exec.LookPath(c); err == nil {
			return p
		}
	}
	return "cmd.exe"
}

// Write 把终端输入写入伪终端（进程 stdin）。
func (t *Term) Write(b []byte) (int, error) { return t.pty.Write(b) }

// Read 从伪终端读取输出（进程 stdout）。
func (t *Term) Read(b []byte) (int, error) { return t.pty.Read(b) }

// Resize 调整伪终端行列尺寸。
func (t *Term) Resize(cols, rows int) error { return t.pty.Resize(cols, rows) }

// Close 关闭伪终端并终止进程。
func (t *Term) Close() error { return t.pty.Close() }

// Pid 返回 shell 进程号。
func (t *Term) Pid() int { return t.pty.Pid() }