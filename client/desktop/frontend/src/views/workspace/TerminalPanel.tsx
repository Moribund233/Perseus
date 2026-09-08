import { useEffect, useRef, useState } from 'react';
import { Terminal } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import { useTranslation } from 'react-i18next';
import { terminalClient, type TerminalStatus } from '../../api/terminal';
import { logInfo, logErr } from '../../stores/logs';

interface Props {
  workspaceId: string;
  active: boolean;
}

const COLS = 100;
const ROWS = 30;

// TerminalPanel：xterm + 网关 ConPTY WS 桥的真实终端。
// 挂载即常驻（仅切换标签不销毁进程）；工作区切换时重建；首次显示才启动。
export default function TerminalPanel({ workspaceId, active }: Props) {
  const { t } = useTranslation();
  const containerRef = useRef<HTMLDivElement | null>(null);
  const disposeRef = useRef<(() => void) | null>(null);
  const startedFor = useRef<string>('');
  const [status, setStatus] = useState<TerminalStatus>('disconnected');

  useEffect(() => {
    if (!active) return;
    if (startedFor.current === workspaceId) return;
    disposeRef.current?.();
    disposeRef.current = null;
    startedFor.current = workspaceId;

    const container = containerRef.current;
    if (!container) return;
    container.replaceChildren();

    const term = new Terminal({
      fontFamily: "'JetBrains Mono', 'Fira Code', 'Consolas', monospace",
      fontSize: 12.5,
      cursorBlink: true,
      convertEol: true,
      scrollback: 4000,
      theme: {
        background: '#0d1117',
        foreground: '#c9d1d9',
        cursor: '#58a6ff',
        selectionBackground: 'rgba(88,166,255,0.3)',
        black: '#010409', red: '#f85149', green: '#3fb950', yellow: '#d29922',
        blue: '#58a6ff', magenta: '#bc8cff', cyan: '#39c5cf', white: '#c9d1d9',
        brightBlack: '#6e7681', brightRed: '#ff7b72', brightGreen: '#56d364',
        brightYellow: '#e3b341', brightBlue: '#79c0ff', brightMagenta: '#d2a8ff',
        brightCyan: '#56d4dd', brightWhite: '#ffffff',
      },
    });
    const fit = new FitAddon();
    term.loadAddon(fit);
    term.open(container);
    fit.fit();

    term.onData((data) => {
      terminalClient.write(new TextEncoder().encode(data));
    });

    terminalClient.setHandlers({
      onOutput: (data) => term.write(data),
      onExit: (code) => {
        logInfo(t('desktop.log.termExit', { code, defaultValue: '终端进程已退出 (code {{code}})' }));
      },
      onStatusChange: (s) => setStatus(s),
      onError: (msg) => logErr(msg),
    });

    terminalClient.connect(workspaceId, term.cols, term.rows);
    logInfo(t('desktop.log.termConnect', { defaultValue: '终端: 正在连接网关 ConPTY 会话…' }));

    const ro = new ResizeObserver(() => {
      try {
        fit.fit();
        terminalClient.resize(term.cols, term.rows);
      } catch {
        /* 容器隐藏时跳过 */
      }
    });
    ro.observe(container);

    disposeRef.current = () => {
      ro.disconnect();
      terminalClient.setHandlers({});
      term.dispose();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active, workspaceId]);

  // 切换工作区：无论当前是否显示终端，都释放旧会话，避免 conpty 泄漏。
  useEffect(() => {
    disposeRef.current?.();
    disposeRef.current = null;
    startedFor.current = '';
    terminalClient.close();
  }, [workspaceId]);

  useEffect(
    () => () => {
      disposeRef.current?.();
      disposeRef.current = null;
      terminalClient.close();
    },
    [],
  );

  const reconnect = () => {
    terminalClient.connect(workspaceId, COLS, ROWS);
    setStatus('connecting');
  };

  return (
    <div className={`bp-body${active ? ' on term-pane' : ''}`} data-pane="terminal">
      <div className="xterm-wrap" ref={containerRef} />
      {status !== 'connected' && (
        <div className="term-offline">
          <span>{t('desktop.terminal.offline', { status, defaultValue: '终端未连接（{{status}}）' })}</span>
          <button className="btn sm" onClick={reconnect}>
            {t('desktop.terminal.reconnect', { defaultValue: '重新连接' })}
          </button>
        </div>
      )}
    </div>
  );
}