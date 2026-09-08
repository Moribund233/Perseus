import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import {
  FileOutlined,
  SyncOutlined,
  ConsoleSqlOutlined,
  BugOutlined,
  BellOutlined,
  SaveOutlined,
  DatabaseOutlined,
  SettingOutlined,
  SearchOutlined,
  BranchesOutlined,
  IssuesCloseOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import type { BottomTab } from './StatusBar';

export type PaneId = 'explorer' | 'search' | 'git' | 'prs' | 'issues' | 'chat';

export interface PaletteActions {
  onOpenPane: (pane: PaneId) => void;
  onOpenBottom: (tab: BottomTab) => void;
  onExit: (target: 'servers' | 'settings') => void;
  onRefreshTree: () => void;
  workspaceName: string;
}

interface Command {
  id: string;
  label: string;
  hint: string;
  group: string;
  icon: ReactNode;
  run: (a: PaletteActions) => void;
}

// CommandPalette：Ctrl+K 命令面板（VSCode 风格）。快捷键绑定见 IdeShell。
export default function CommandPalette({ open, onClose, actions }: { open: boolean; onClose: () => void; actions: PaletteActions }) {
  const [q, setQ] = useState('');
  const inputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (open) {
      setQ('');
      requestAnimationFrame(() => inputRef.current?.focus());
    }
  }, [open]);

  const commands: Command[] = useMemo<Command[]>(
    () => [
      { id: 'pane-explorer', label: '资源管理器', hint: 'View: Explorer', group: '视图', icon: <FileOutlined />, run: (a) => a.onOpenPane('explorer') },
      { id: 'pane-search', label: '搜索', hint: 'View: Search', group: '视图', icon: <SearchOutlined />, run: (a) => a.onOpenPane('search') },
      { id: 'pane-git', label: '源代码管理', hint: 'View: Git', group: '视图', icon: <BranchesOutlined />, run: (a) => a.onOpenPane('git') },
      { id: 'pane-prs', label: 'Pull Requests', hint: 'Sidebar: PRs', group: '视图', icon: <SyncOutlined />, run: (a) => a.onOpenPane('prs') },
      { id: 'pane-issues', label: 'Issues', hint: 'Sidebar: Issues', group: '视图', icon: <IssuesCloseOutlined />, run: (a) => a.onOpenPane('issues') },
      { id: 'bot-problems', label: '问题面板', hint: 'Panel: Problems', group: '面板', icon: <BugOutlined />, run: (a) => a.onOpenBottom('problems') },
      { id: 'bot-output', label: '输出', hint: 'Panel: Output', group: '面板', icon: <BellOutlined />, run: (a) => a.onOpenBottom('output') },
      { id: 'bot-terminal', label: '终端', hint: 'Panel: Terminal', group: '面板', icon: <ConsoleSqlOutlined />, run: (a) => a.onOpenBottom('terminal') },
      { id: 'refresh', label: '刷新文件树', hint: 'File: Refresh', group: '文件', icon: <ReloadOutlined />, run: (a) => a.onRefreshTree() },
      { id: 'save-all', label: '保存全部文件', hint: 'File: Save', group: '文件', icon: <SaveOutlined />, run: () => document.dispatchEvent(new KeyboardEvent('keydown', { key: 's', ctrlKey: true, bubbles: true })) },
      { id: 'exit-servers', label: '服务器', hint: 'Portal: Servers', group: '门户', icon: <DatabaseOutlined />, run: (a) => a.onExit('servers') },
      { id: 'exit-settings', label: '设置', hint: 'Portal: Settings', group: '门户', icon: <SettingOutlined />, run: (a) => a.onExit('settings') },
    ],
    [],
  );

  const list = commands
    .filter((c) => (c.label + c.hint).toLowerCase().includes(q.trim().toLowerCase()))
    .slice(0, 8);

  const run = (cmd: Command) => {
    cmd.run(actions);
    onClose();
  };

  if (!open) return null;

  return (
    <>
      <div className="palette-veil open" onClick={onClose} />
      <div className="palette" role="dialog" aria-modal="true">
        <div className="p-input">
          <SyncOutlined />
          <input
            ref={inputRef}
            placeholder="输入命令…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Escape') onClose();
            }}
          />
          <span style={{ fontSize: 11, color: 'var(--t3)' }}>{actions.workspaceName}</span>
        </div>
        <div className="p-list">
          {list.length === 0 && <div className="p-empty">无匹配命令</div>}
          {list.map((c, i) => (
            <div key={c.id} className={`p-row${q && i === 0 ? ' sel' : ''}`} onClick={() => run(c)}>
              {c.icon}
              <span>{c.label}</span>
              <span className="grp">{c.group}</span>
              <span className="grp">{c.hint}</span>
            </div>
          ))}
        </div>
        <div className="p-foot">
          <span>
            <kbd>↑</kbd>
            <kbd>↓</kbd> 导航
          </span>
          <span>
            <kbd>↵</kbd> 选择
          </span>
          <span>
            <kbd>esc</kbd> 关闭
          </span>
        </div>
      </div>
    </>
  );
}