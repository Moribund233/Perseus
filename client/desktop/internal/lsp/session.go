package lsp

import (
	"errors"
	"fmt"
	"io"
	"os"
	"os/exec"
	"sync"
	"time"
)

// MaxRestarts 进程崩溃后的最大重启次数（spec §8.2：指数退避，最多 3 次）。
const MaxRestarts = 3

// ErrClosed 会话已关闭。
var ErrClosed = errors.New("lsp: session closed")

// RestartNotification 进程重启后由网关注入的通知方法名（前端桥收到后重新初始化协议）。
const RestartNotification = "$/perseus/lspRestarted"

// Session 一个语言服务器子进程会话（spec §8.2 生命周期）。
// 网关桥接只关心帧输入输出；协议握手由前端 Monaco providers 驱动。
//
// 线程安全：Send/Out/Closed/Err 可并发调用。
// Out 通道在会话存活期间不关闭（配合 Closed 通道消费，避免并发发送 panic）。
type Session struct {
	srv  Server
	root string

	inMu   sync.Mutex
	inCond *sync.Cond
	in     io.WriteCloser
	inTok  int
	proc   *exec.Cmd

	out         chan []byte
	exitCh      chan error
	closed      chan struct{}
	done        chan struct{}
	once        sync.Once
	closedOnce  sync.Once

	finalMu sync.Mutex
	final   error
}

// NewSession 启动语言服务器进程并接管其生命周期。
func NewSession(root string, srv Server) (*Session, error) {
	s := &Session{
		srv:    srv,
		root:   root,
		out:    make(chan []byte, 256),
		exitCh: make(chan error, 1),
		closed: make(chan struct{}),
		done:   make(chan struct{}),
	}
	s.inCond = sync.NewCond(&s.inMu)
	if err := s.spawn(); err != nil {
		return nil, err
	}
	go s.run()
	return s, nil
}

// spawn 启动一代进程并接管 stdout 读取。线程安全（重启时替换进程）。
func (s *Session) spawn() error {
	select {
	case <-s.done:
		return ErrClosed
	default:
	}
	if len(s.srv.Command) == 0 {
		return errors.New("lsp: empty server command")
	}
	cmd := exec.Command(s.srv.Command[0], s.srv.Command[1:]...)
	cmd.Dir = s.root
	cmd.Env = append(os.Environ(), s.srv.Env...)
	stderr, err := cmd.StderrPipe()
	if err != nil {
		return err
	}
	stdin, err := cmd.StdinPipe()
	if err != nil {
		return err
	}
	stdout, err := cmd.StdoutPipe()
	if err != nil {
		return err
	}
	if err := cmd.Start(); err != nil {
		return fmt.Errorf("start %s: %w", s.srv.Command[0], err)
	}
	// stderr 仅用于崩溃诊断；丢弃正文，避免污染协议帧。
	go func() { _, _ = io.Copy(io.Discard, stderr) }()

	s.inMu.Lock()
	if s.in != nil {
		_ = s.in.Close()
	}
	tok := s.inTok + 1
	s.in = stdin
	s.inTok = tok
	s.proc = cmd
	s.inCond.Broadcast()
	s.inMu.Unlock()

	go s.readLoop(stdout, cmd, tok)
	return nil
}

// clearIn 解除一代进程的 stdin（进程死亡后调用），唤醒等待 Send 阻塞者。
func (s *Session) clearIn(tok int) {
	s.inMu.Lock()
	defer s.inMu.Unlock()
	if s.inTok == tok {
		if s.in != nil {
			_ = s.in.Close()
		}
		s.in = nil
		s.inCond.Broadcast()
	}
}

// readLoop 从进程 stdout 读帧 → out；EOF 后收尾（cmd.Wait）把退出错误推给 exitCh。
func (s *Session) readLoop(stdout io.ReadCloser, cmd *exec.Cmd, tok int) {
	defer stdout.Close()
	fr := NewFrameReader(stdout)
	for {
		body, err := fr.Next()
		if err != nil {
			break
		}
		if !s.deliver(body) {
			_ = cmd.Process.Kill()
			s.clearIn(tok)
			select {
			case s.exitCh <- cmd.Wait():
			default:
			}
			return
		}
	}
	s.clearIn(tok)
	select {
	case s.exitCh <- cmd.Wait():
	default:
	}
}

// deliver 把一帧送达 out；会话关闭时返回 false（不再发送）。
func (s *Session) deliver(body []byte) bool {
	select {
	case s.out <- body:
		return true
	case <-s.done:
		return false
	}
}

// run 生命周期主循环：崩溃指数退避重启（最多 MaxRestarts 次）。
// 每一代只有一次 spawn；结束后才进入下一个迭代，因此 out 无并发写风险。
func (s *Session) run() {
	backoff := 200 * time.Millisecond
	for attempt := 0; ; attempt++ {
		select {
		case <-s.done:
			s.finish(nil)
			return
		default:
		}

		var err error
		select {
		case <-s.done:
			s.finish(nil)
			return
		case err = <-s.exitCh:
		}
		if err == nil {
			// 干净退出（客户端 shutdown/exit）
			s.finish(nil)
			return
		}
		if attempt >= MaxRestarts {
			s.finish(fmt.Errorf("lsp: server exited %d times: %w", MaxRestarts+1, err))
			return
		}

		// 崩溃 → 告知前端重新初始化协议，退避后重启。
		s.notifyRestarted()
		select {
		case <-s.done:
			s.finish(nil)
			return
		case <-time.After(backoff):
		}
		backoff *= 2
		if backoff > 5*time.Second {
			backoff = 5 * time.Second
		}
		if sErr := s.spawn(); sErr != nil {
			s.finish(sErr)
			return
		}
	}
}

// notifyRestarted 注入一条 LSP 形状的重启通知，前端桥收到后重新 initialize。
func (s *Session) notifyRestarted() {
	msg := []byte(fmt.Sprintf(`{"jsonrpc":"2.0","method":%q,"params":null}`, RestartNotification))
	_ = s.deliver(msg)
}

// Send 把一条 LSP JSON 消息写入进程 stdin（Content-Length 帧）。
// 若进程刚崩溃尚未重启（stdin 换代时），阻塞等待新一代就绪；会话关闭返回 ErrClosed。
func (s *Session) Send(msg []byte) error {
	s.inMu.Lock()
	for s.in == nil {
		select {
		case <-s.done:
			s.inMu.Unlock()
			return ErrClosed
		default:
			s.inCond.Wait()
		}
	}
	var err error
	_, err = NewFrameWriter(s.in).WriteJSON(msg)
	s.inMu.Unlock()
	if err != nil {
		return fmt.Errorf("lsp: send: %w", err)
	}
	return nil
}

// Out 返回进程输出的已解析帧通道（协议透传，含 publishDiagnostics）。
func (s *Session) Out() <-chan []byte { return s.out }

// Closed 在会话终止时关闭（正常退出或 Close）。
func (s *Session) Closed() <-chan struct{} { return s.closed }

// Err 返回会话终止错误；正常/被主动关闭为 nil。
func (s *Session) Err() error {
	s.finalMu.Lock()
	defer s.finalMu.Unlock()
	return s.final
}

func (s *Session) finish(err error) {
	s.finalMu.Lock()
	if s.final == nil {
		s.final = err
	}
	s.finalMu.Unlock()
	s.closedOnce.Do(func() { close(s.closed) })
}

// Close 终止进程并释放资源。幂等。
func (s *Session) Close() error {
	s.once.Do(func() { close(s.done) })
	s.inMu.Lock()
	if s.proc != nil {
		_ = s.proc.Process.Kill()
		s.proc = nil
	}
	if s.in != nil {
		_ = s.in.Close()
		s.in = nil
	}
	s.inCond.Broadcast()
	s.inMu.Unlock()
	s.finish(nil)
	return nil
}