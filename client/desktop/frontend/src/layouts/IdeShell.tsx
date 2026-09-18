import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';
import { Dropdown, message } from 'antd';
import { useTranslation } from 'react-i18next';
import {
  AppstoreOutlined,
  SearchOutlined,
  BranchesOutlined,
  PullRequestOutlined,
  IssuesCloseOutlined,
  MessageOutlined,
  DatabaseOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import type { Workspace } from '../api/workspaces';
import { useWorkspaceStore } from '../stores/workspace';
import { useNavigationStore } from '../stores/navigation';
import { useIdentityStore } from '../stores/identity';
import { useProblemsStore } from '../stores/problems';
import { usePullRequestsStore } from '../stores/pullRequests';
import { useIssuesStore } from '../stores/issues';
import ExplorerPanel from '../views/workspace/ExplorerPanel';
import SearchPanel from '../views/workspace/SearchPanel';
import GitPanel from '../views/workspace/GitPanel';
import QuickListPanel from '../views/workspace/QuickListPanel';
import EditorTabs from '../views/workspace/EditorTabs';
import DiffView from '../views/workspace/DiffView';
import ProblemsPanel from '../views/workspace/ProblemsPanel';
import OutputPanel from '../views/workspace/OutputPanel';
import TerminalPanel from '../views/workspace/TerminalPanel';
import CollabAuxPanel from '../views/workspace/CollabAuxPanel';
import DiscussionsPanel from '../views/workspace/DiscussionsPanel';
import ActivityChatPanel from '../views/chat/ActivityChatPanel';
import StatusBar, { type BottomTab } from '../views/workspace/StatusBar';
import CommandPalette, { type PaneId } from '../views/workspace/CommandPalette';
import WindowControls from '../components/WindowControls';
import { lspShutdown } from '../views/workspace/lspSession';

export const PANES: Array<{ id: PaneId; icon: ReactNode; title: string }> = [
  { id: 'explorer', icon: <AppstoreOutlined />, title: '资源管理器' },
  { id: 'search', icon: <SearchOutlined />, title: '搜索' },
  { id: 'git', icon: <BranchesOutlined />, title: '源代码管理' },
  { id: 'prs', icon: <PullRequestOutlined />, title: 'Pull Requests' },
  { id: 'issues', icon: <IssuesCloseOutlined />, title: 'Issues' },
  { id: 'chat', icon: <MessageOutlined />, title: '聊天' },
];

const MENUS = {
  file: ['newFile', 'refresh', 'sep', 'exit'] as const,
  edit: ['undo', 'redo', 'sep', 'palette'] as const,
  view: ['explorer', 'search', 'git', 'prs', 'issues', 'sep', 'problems', 'output', 'terminal'] as const,
  terminal: ['terminal', 'sep', 'kill'] as const,
  help: ['about'] as const,
};

export default function IdeShell({ workspace }: { workspace: Workspace }) {
  const { t } = useTranslation();
  const setCurrent = useWorkspaceStore((s) => s.setCurrent);
  const navigate = useNavigationStore((s) => s.navigate);
  const me = useIdentityStore((s) => s.me);
  const fetchIdentity = useIdentityStore((s) => s.fetchIdentity);
  const problemCount = useProblemsStore((s) => s.diagnostics.length);
  const prCount = usePullRequestsStore((s) => (s.pullRequests ?? []).length);
  const issueCount = useIssuesStore((s) => (s.issues ?? []).length);

  const [pane, setPane] = useState<PaneId>('explorer');
  const [openPath, setOpenPath] = useState<string | null>(null);
  const [openLine, setOpenLine] = useState<number | null>(null);
  const [diffPath, setDiffPath] = useState<string | null>(null);
  const [bottom, setBottom] = useState<BottomTab>('problems');
  const [collapsed, setCollapsed] = useState(false);
  const [auxOpen, setAuxOpen] = useState(false);
  const [discussionsOpen, setDiscussionsOpen] = useState(false);
  const [palette, setPalette] = useState(false);
  const [file, setFile] = useState<string | null>(null);
  const [lang, setLang] = useState<string | null>(null);
  const [cursor, setCursor] = useState<{ line: number; column: number } | null>(null);

  useEffect(() => {
    lspShutdown();
    return () => lspShutdown();
  }, [workspace.id]);

  useEffect(() => {
    if (workspace.server_id) void fetchIdentity();
  }, [workspace.server_id, fetchIdentity]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setPalette((v) => !v);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  const openFileLine = useCallback((path: string, line?: number) => {
    setOpenPath(path);
    setOpenLine(line ?? null);
  }, []);

  const leaveTo = useCallback(
    (target: 'servers' | 'settings') => {
      lspShutdown();
      setCurrent(null);
      navigate(target);
    },
    [setCurrent, navigate],
  );

  const menuItems = useMemo(() => {
    const handler: Record<string, () => void> = {
      undo: () => document.dispatchEvent(new KeyboardEvent('keydown', { key: 'z', ctrlKey: true, bubbles: true })),
      redo: () => document.dispatchEvent(new KeyboardEvent('keydown', { key: 'y', ctrlKey: true, bubbles: true })),
      palette: () => setPalette(true),
      refresh: () => window.dispatchEvent(new Event('ide:refresh-tree')),
      exit: () => leaveTo('servers'),
      terminal: () => { setBottom('terminal'); setCollapsed(false); },
      problems: () => { setBottom('problems'); setCollapsed(false); },
      output: () => { setBottom('output'); setCollapsed(false); },
      explorer: () => setPane('explorer'),
      search: () => setPane('search'),
      git: () => setPane('git'),
      prs: () => setPane('prs'),
      issues: () => setPane('issues'),
      kill: () => message.info(t('desktop.menu.killHint')),
      newFile: () => message.info(t('desktop.portal.phase2')),
      about: () => message.info(makeAbout(workspace)),
    };
    const menuOf = (keys: string[]): Array<{ type: 'divider' | 'item'; key: string; label: string; danger?: boolean }> =>
      keys.map((k) =>
        k === 'sep'
          ? { type: 'divider' as const, key: 'sep-' + Math.random(), label: '' }
          : { type: 'item' as const, key: k, label: t(`desktop.menu.${k}`), danger: k === 'kill' },
      );
    return {
      file: menuOf([...MENUS.file]),
      edit: menuOf([...MENUS.edit]),
      view: menuOf([...MENUS.view]),
      terminal: menuOf([...MENUS.terminal]),
      help: menuOf([...MENUS.help]),
      onSelect: (e: { key: string }) => handler[e.key]?.(),
    };
  }, [t, leaveTo, workspace]);

  const badgeFor = (id: PaneId): ReactNode | null => {
    if (id === 'issues' && issueCount > 0) return <i className="badge gray">{issueCount}</i>;
    if (id === 'prs' && prCount > 0) return <i className="badge">{prCount}</i>;
    if (id === 'git' && problemCount > 0) return <i className="badge red">{problemCount}</i>;
    return null;
  };

  // 双击标题栏空白/拖拽区 = 最大化/还原（交互控件上不触发）。
  const onTitlebarDblClick = (e: React.MouseEvent) => {
    if ((e.target as HTMLElement).closest('button, input, a, .win-controls, .avatar, .ant-avatar')) return;
    window.runtime?.WindowToggleMaximise();
  };

  const paletteActions = useMemo(
    () => ({
      onOpenPane: (p: PaneId) => setPane(p),
      onOpenBottom: (b: BottomTab) => { setBottom(b); setCollapsed(false); },
      onExit: leaveTo,
      onRefreshTree: () => window.dispatchEvent(new Event('ide:refresh-tree')),
      workspaceName: workspace.name,
    }),
    [leaveTo, workspace.name],
  );

  return (
    <div className="ide">
      <header className="titlebar" onDoubleClick={onTitlebarDblClick}>
        <div className="tb-brand">
          <span className="brand-mark" style={{ width: 20, height: 20, borderRadius: 6 }}>
            <svg viewBox="0 0 24 24" width="12" height="12" fill="currentColor"><path d="M12 2 3 7v10l9 5 9-5V7l-9-5Z" opacity=".9" /></svg>
          </span>
          <span className="tb-app">PERSEUS</span>
        </div>
        <nav className="tb-menu">
          {(['file', 'edit', 'view', 'terminal', 'help'] as const).map((m) => (
            <Dropdown key={m} menu={{ items: menuItems[m], onClick: ({ key }) => menuItems.onSelect({ key }) }} trigger={['click']}>
              <button className="tb-menu-btn">{t(`desktop.menu.${m}`)}</button>
            </Dropdown>
          ))}
        </nav>
        <div className="tb-crumb mono">
          <b>{workspace.name}</b>
          <span className="tb-sep" />
          <span className="faint" title={workspace.path}>{workspace.name}/{workspace.path.split(/[\\/]/).pop()}</span>
        </div>
        <div className="tb-right">
          <button className="tb-search" onClick={() => setPalette(true)}>
            <SearchOutlined />
            <span>{t('desktop.ide.searchWorkspace')}</span>
            <kbd>⌘K</kbd>
          </button>
          <div className="avatar" style={{ background: hashColor(me?.username ?? 'perseus') }}>
            {(me?.username ?? 'P').slice(0, 2).toUpperCase()}
          </div>
          <WindowControls />
        </div>
      </header>

      <div className="ide-body">
        <nav className="activity">
          {PANES.map((p) => (
            <button key={p.id} className={`act${pane === p.id ? ' on' : ''}`} title={p.title} onClick={() => setPane(p.id)}>
              {p.icon}
              {badgeFor(p.id)}
            </button>
          ))}
          <span className="sp" />
          <button className={`act${pane === 'chat' ? ' on' : ''}`} title={t('desktop.menu.chat')} onClick={() => setPane('chat')}>
            <MessageOutlined />
          </button>
          <button className="act" title={t('desktop.menu.exit')} onClick={() => leaveTo('servers')}>
            <DatabaseOutlined />
          </button>
          <button className="act" title={t('desktop.menu.settings')} onClick={() => leaveTo('settings')}>
            <SettingOutlined />
          </button>
        </nav>

        <aside className="sidebar">
          {pane === 'explorer' && <ExplorerPanel workspaceId={workspace.id} workspaceName={workspace.name} onOpen={openFileLine} />}
          {pane === 'search' && <SearchPanel workspaceName={workspace.name} onOpen={openFileLine} />}
          {pane === 'git' && <GitPanel workspaceId={workspace.id} onOpenDiff={setDiffPath} />}
          {pane === 'prs' && <QuickListPanel kind="prs" workspace={workspace} />}
          {pane === 'issues' && <QuickListPanel kind="issues" workspace={workspace} />}
          {pane === 'chat' && <ActivityChatPanel workspace={workspace} />}
        </aside>

        <main className="editor-col">
          {diffPath ? (
            <DiffView workspaceId={workspace.id} workspacePath={workspace.path} path={diffPath} onClose={() => setDiffPath(null)} />
          ) : (
            <EditorTabs
              workspaceId={workspace.id}
              workspacePath={workspace.path}
              workspace={workspace}
              openPath={openPath}
              openLine={openLine}
              auxOpen={auxOpen}
              onToggleAux={() => setAuxOpen((v) => !v)}
              onToggleBottom={() => setCollapsed((v) => !v)}
              discussionsOn={discussionsOpen}
              onToggleDiscussions={() => setDiscussionsOpen((v) => !v)}
              onCursor={(p, l, _d, pos) => { setFile(p); setLang(l); setCursor(pos ?? null); }}
            />
          )}

          <div className={`bottom-panel${collapsed ? ' collapsed' : ''}`}>
            <div className="bp-tabs">
              <button className={`bpt${bottom === 'problems' ? ' on' : ''}`} onClick={() => setBottom('problems')}>
                {t('desktop.menu.problems')} {problemCount > 0 && <span className="cnt">({problemCount})</span>}
              </button>
              <button className={`bpt${bottom === 'output' ? ' on' : ''}`} onClick={() => setBottom('output')}>
                {t('desktop.menu.output')}
              </button>
              <button className={`bpt${bottom === 'terminal' ? ' on' : ''}`} onClick={() => setBottom('terminal')}>
                {t('desktop.menu.terminal')}
              </button>
              <div className="right">
                <button className="icon-btn sm" title={collapsed ? '展开面板' : '收起面板'} onClick={() => setCollapsed((v) => !v)}>
                  {collapsed ? '▲' : '▼'}
                </button>
              </div>
            </div>
            <ProblemsPanel rootPath={workspace.path} active={bottom === 'problems'} onOpen={openFileLine} />
            <OutputPanel active={bottom === 'output'} />
            <TerminalPanel workspaceId={workspace.id} active={bottom === 'terminal'} />
          </div>
        </main>

        {auxOpen && (
          <aside style={{ width: 264, flexShrink: 0 }}>
            <CollabAuxPanel workspace={workspace} />
          </aside>
        )}
        {discussionsOpen && (
          <aside style={{ width: 320, flexShrink: 0, borderLeft: '1px solid #21262d' }}>
            <DiscussionsPanel
              workspace={workspace}
              filePath={openPath}
              cursorLine={cursor?.line ?? null}
              onGoLine={(path, line) => openFileLine(path, line)}
            />
          </aside>
        )}
      </div>

      <StatusBar workspace={workspace} file={file} lang={lang} cursor={cursor} onOpenBottom={(b) => { setBottom(b); setCollapsed(false); }} />
      <CommandPalette open={palette} onClose={() => setPalette(false)} actions={paletteActions} />
    </div>
  );
}

function hashColor(name: string): string {
  const palette = ['#1f6feb', '#bc8cff', '#3fb950', '#ffa657', '#d29922', '#f85149', '#39c5cf'];
  let h = 0;
  for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) >>> 0;
  return palette[h % palette.length];
}

function makeAbout(ws: Workspace): string {
  return `PERSEUS 桌面版 — 工作区 ${ws.name} (${ws.path})`;
}