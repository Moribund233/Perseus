import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import Editor, { type OnMount } from '@monaco-editor/react';
import { App as AntApp, Modal } from 'antd';
import { DownOutlined, TeamOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import * as monaco from 'monaco-editor';
import { readFile, writeFile, type FileContent, type Workspace } from '../../api/workspaces';
import { CollabSession, type CollabParticipant, type CollabStatus } from '../../api/collabSocket';
import { useWorkspaceRepo } from '../../hooks/useWorkspaceRepo';
import { useProblemsStore } from '../../stores/problems';
import CollabMonaco from './CollabMonaco';
import { fileBadge } from './ExplorerPanel';
import {
  fileUri, langForPath, lspOpen, lspChange, lspSave, lspClose, applyModelDiagnostics,
} from './lspSession';

interface Tab {
  path: string;
  content: FileContent;
  savedContent: string;
}

interface Props {
  workspaceId: string;
  workspacePath: string;
  workspace: Workspace;
  openPath: string | null;
  openLine?: number | null;
  auxOpen?: boolean;
  onToggleAux?: () => void;
  onToggleBottom?: () => void;
  onCursor?: (path: string | null, lang: string | null, dirty: boolean, cursor?: { line: number; column: number }) => void;
}

export default function EditorTabs({ workspaceId, workspacePath, workspace, openPath, openLine, auxOpen, onToggleAux, onToggleBottom, onCursor }: Props) {
  const { t } = useTranslation();
  const { message } = AntApp.useApp();
  const repo = useWorkspaceRepo(workspace);
  const [tabs, setTabs] = useState<Tab[]>([]);
  const [active, setActive] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [cursor, setCursor] = useState<{ line: number; column: number }>({ line: 1, column: 1 });
  const editorRef = useRef<monaco.editor.IStandaloneCodeEditor | null>(null);
  const textRef = useRef<Map<string, string>>(new Map());
  const tabsRef = useRef<Tab[]>([]);
  tabsRef.current = tabs;

  // F-204 协作：按 tab path 管理会话；仅在 clone 工作区且远端仓库可解析时可用。
  const [collabEnabled, setCollabEnabled] = useState<Record<string, boolean>>({});
  const [collabStatus, setCollabStatus] = useState<CollabStatus>('disconnected');
  const [participants, setParticipants] = useState<CollabParticipant[]>([]);
  const [pending, setPending] = useState(false);
  const sessionsRef = useRef<Record<string, CollabSession>>({});

  const diagnostics = useProblemsStore((s) => s.diagnostics);

  const activePathRef = useRef<string | null>(null);
  activePathRef.current = active;

  const detachSession = useCallback((path: string) => {
    sessionsRef.current[path]?.detach();
    delete sessionsRef.current[path];
  }, []);

  const getText = useCallback((path: string) => textRef.current.get(path) ?? '', []);

  const findTab = (path: string | null) => (path ? tabs.find((tb) => tb.path === path) : undefined);

  const save = useCallback(
    async (path: string | null = active) => {
      const tab = path ? tabsRef.current.find((tb) => tb.path === path) : undefined;
      if (!tab || tab.content.binary) return;
      try {
        const res = await writeFile(workspaceId, tab.path, tab.content.content);
        setTabs((prev) =>
          prev.map((tb) => (tb.path === tab.path ? { ...tb, savedContent: tb.content.content } : tb)),
        );
        lspSave(tab.path);
        if (res && onCursor) onCursor(tab.path, langForPath(tab.path), false);
        // 协作模式：本地写盘保持镜像后，再触发网关侧 Git 提交（全员广播 collab-saved）。
        const session = sessionsRef.current[tab.path];
        if (session?.isActive()) {
          session.save(`collab: save ${tab.path}`);
        }
      } catch (e) {
        setError(String(e));
      }
    },
    [workspaceId, active, onCursor],
  );

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') {
        e.preventDefault();
        void save();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [save]);

  useEffect(() => {
    setTabs([]);
    setActive(null);
    setError(null);
    editorRef.current = null;
    textRef.current = new Map();
    for (const s of Object.values(sessionsRef.current)) s.detach();
    sessionsRef.current = {};
  }, [workspaceId]);

  useEffect(() => {
    if (!openPath) return;
    const existing = tabsRef.current.find((tb) => tb.path === openPath);
    if (existing) {
      setActive(openPath);
      return;
    }
    readFile(workspaceId, openPath)
      .then((fc) => {
        if (fc.binary) {
          setTabs((prev) =>
            prev.some((tb) => tb.path === openPath) ? prev : [...prev, { path: openPath, content: fc, savedContent: fc.content }],
          );
          setActive(openPath);
          return;
        }
        textRef.current.set(openPath, fc.content);
        setTabs((prev) =>
          prev.some((tb) => tb.path === openPath) ? prev : [...prev, { path: openPath, content: fc, savedContent: fc.content }],
        );
        setActive(openPath);
        lspOpen(workspaceId, workspacePath, openPath, () => getText(openPath));
      })
      .catch((e) => setError(String(e)));
  }, [workspaceId, workspacePath, openPath, getText]);

  // 问题面板 / 搜索结果跳转到指定行
  useEffect(() => {
    if (!openPath || !openLine) {
      if (openPath) setActive(openPath);
      return;
    }
    setActive(openPath);
    const editor = editorRef.current;
    if (editor && active === openPath) {
      editor.revealPositionInCenter({ lineNumber: openLine, column: 1 });
      editor.setPosition({ lineNumber: openLine, column: 1 });
    }
  }, [openPath, openLine, active]);

  // LSP → Monaco markers
  useEffect(() => {
    const editor = editorRef.current;
    if (editor) applyModelDiagnostics(editor.getModel());
  }, [diagnostics, active]);

  // 协作会话：为启用协作且可协作的 tab 建立会话（onSynced 后以 Git 权威内容绑定）。
  useEffect(() => {
    const path = active;
    const tab = path ? tabsRef.current.find((tb) => tb.path === path) : undefined;
    const eligible =
      !!path && !!repo.serverId && !!repo.repoId && !!collabEnabled[path] &&
      !!tab && !tab.content.binary && !tab.content.truncated && !!editorRef.current;
    if (!eligible || !path || !repo.serverId || !repo.repoId) return;
    let session = sessionsRef.current[path];
    if (session) return;
    const branch = workspace.branch || repo.defaultBranch || 'main';
    session = new CollabSession({
      serverId: repo.serverId,
      docKey: `${repo.repoId}:${branch}:${path}`,
      onStatus: (s) => { if (activePathRef.current === path) setCollabStatus(s); },
      onParticipants: (peers) => { if (activePathRef.current === path) setParticipants(peers); },
      onSaved: (msg) => message.success(t('desktop.collab.saved', { commit: (msg.commit_id || '').slice(0, 7) })),
      onError: (err) => message.error(`${t('desktop.collab.saveFailed')}: ${err}`),
    });
    sessionsRef.current[path] = session;
    session.attach(editorRef.current!);
  }, [active, collabEnabled, repo.serverId, repo.repoId, repo.defaultBranch, workspace.branch, message, t]);

  // 未同步（断线缓冲）指示轮询。
  useEffect(() => {
    if (!active || !sessionsRef.current[active]) {
      setPending(false);
      return;
    }
    const timer = setInterval(() => {
      setPending(sessionsRef.current[active!]?.hasPendingChanges() ?? false);
    }, 1000);
    return () => clearInterval(timer);
  }, [active, collabStatus]);

  const toggleCollab = () => {
    const path = active;
    if (!path) return;
    if (collabEnabled[path]) {
      detachSession(path);
      setCollabStatus('disconnected');
      setParticipants([]);
      setPending(false);
    }
    setCollabEnabled((prev) => ({ ...prev, [path]: !prev[path] }));
  };

  const close = (path: string) => {
    const tab = findTab(path);
    const doClose = () => {
      lspClose(path);
      detachSession(path);
      textRef.current.delete(path);
      setTabs((prev) => {
        const idx = prev.findIndex((tb) => tb.path === path);
        const next = prev.filter((tb) => tb.path !== path);
        setActive((cur) => {
          if (cur !== path) return cur;
          return next[Math.min(idx, next.length - 1)]?.path ?? null;
        });
        return next;
      });
    };
    if (tab && tab.content.content !== tab.savedContent) {
      Modal.confirm({
        title: t('desktop.editor.closeConfirmTitle', { defaultValue: '未保存的更改' }),
        content: t('desktop.editor.closeConfirm', { defaultValue: '“{{path}}” 有未保存的更改, 关闭将丢弃。', path }),
        okText: t('desktop.editor.closeDiscard', { defaultValue: '丢弃并关闭' }),
        okButtonProps: { danger: true },
        cancelText: t('desktop.editor.closeCancel', { defaultValue: '取消' }),
        onOk: doClose,
      });
    } else {
      doClose();
    }
  };

  const current = findTab(active);
  const language = useMemo(() => guessLang(active ?? ''), [active]);
  const dirty = current ? current.content.content !== current.savedContent : false;

  useEffect(() => {
    onCursor?.(active, active ? langForPath(active) : null, dirty, cursor);
  }, [active, dirty, cursor, onCursor]);

  const onMount: OnMount = (editor) => {
    editorRef.current = editor;
    editor.onDidChangeCursorPosition((e) => {
      const p = e.position;
      setCursor({ line: p.lineNumber, column: p.column });
    });
    applyModelDiagnostics(editor.getModel());
  };

  if (error) return <div className="error-text">{error}</div>;
  if (tabs.length === 0 || !current) return <div className="empty-editor">{t('desktop.editor.selectFile')}</div>;

  if (current.content.binary) {
    return (
      <div className="empty-editor">
        {t('desktop.editor.binary', { size: current.content.size, defaultValue: '二进制文件 ({{size}} 字节)，不支持编辑。' })}
      </div>
    );
  }

  return (
    <div className="editor-tab">
      <div className="tabbar" role="tablist">
        {tabs.map((tb) => {
          const tbDirty = tb.content.content !== tb.savedContent;
          const name = tb.path.split(/[\\/]/).pop() ?? tb.path;
          const badge = fileBadge(name);
          return (
            <span
              key={tb.path}
              role="tab"
              aria-selected={tb.path === active}
              className={`etab${tb.path === active ? ' on' : ''}${tb.content.binary ? ' bin' : ''}`}
              onClick={() => setActive(tb.path)}
            >
              <span className={badge.cls}>{badge.label}</span>
              <span className="tname">{name}</span>
              {tbDirty && <span className="dirty" />}
              <button
                className="x"
                aria-label={t('desktop.editor.closeTab', { defaultValue: '关闭' })}
                onClick={(e) => {
                  e.stopPropagation();
                  close(tb.path);
                }}
              >
                ×
              </button>
            </span>
          );
        })}
        <span className="tab-actions">
          {current.content.truncated && <span className="warn">{t('desktop.editor.truncated')}</span>}
          <button
            className={`icon-btn${auxOpen ? ' on' : ''}`}
            title={t('desktop.aux.toggle')}
            onClick={onToggleAux}
            style={auxOpen ? { color: '#58a6ff', background: 'var(--hover)' } : undefined}
          >
            <TeamOutlined />
          </button>
          <button className="icon-btn" title={t('desktop.editor.bottomPanel')} onClick={onToggleBottom}>
            <DownOutlined />
          </button>
          <button disabled={!dirty} onClick={() => void save()}>
            {t('desktop.editor.save')}
          </button>
        </span>
      </div>
      <div className="crumbs">
        <span className="crumb-path">
          {current.path.split(/[\\/]/).map((seg, i, arr) => (
            <span key={i}>
              {i > 0 && <span className="cru">/</span>}
              <span className={i === arr.length - 1 ? 'cru-leaf' : 'cru'}>{seg}</span>
            </span>
          ))}
        </span>
        <span className="right">
          {repo.repoId && !current.content.binary && !current.content.truncated && (
            <CollabMonaco
              enabled={!!collabEnabled[current.path]}
              status={collabStatus}
              participants={participants}
              pending={pending}
              onToggle={toggleCollab}
            />
          )}
          <span className="faint">{t('desktop.editor.saveHint', { size: (current.content.size / 1024).toFixed(1) })}</span>
          <span className="cursor-info">
            Ln {cursor.line}, Col {cursor.column}
          </span>
        </span>
      </div>
      <Editor
        height="100%"
        theme="vs-dark"
        path={fileUri(workspacePath, current.path)}
        language={language}
        value={current.content.content}
        onMount={onMount}
        onChange={(v) => {
          const next = v ?? '';
          textRef.current.set(current.path, next);
          setTabs((prev) =>
            prev.map((tb) => (tb.path === active ? { ...tb, content: { ...tb.content, content: next } } : tb)),
          );
          lspChange(current.path);
        }}
        options={{
          readOnly: current.content.truncated,
          automaticLayout: true,
          fontFamily: "'JetBrains Mono', 'Fira Code', 'Consolas', monospace",
          fontSize: 12.5,
          minimap: { enabled: false },
          scrollBeyondLastLine: false,
          tabSize: 2,
          cursorBlinking: 'smooth',
          renderLineHighlight: 'all',
          bracketPairColorization: { enabled: true },
          padding: { top: 8 },
          scrollbar: { verticalScrollbarSize: 10, horizontalScrollbarSize: 10 },
        }}
      />
    </div>
  );
}

function guessLang(path: string): string {
  const ext = path.split('.').pop()?.toLowerCase() ?? '';
  const map: Record<string, string> = {
    ts: 'typescript', tsx: 'typescript', js: 'javascript', jsx: 'javascript',
    py: 'python', pyi: 'python', json: 'json', jsonc: 'json', md: 'markdown',
    css: 'css', scss: 'scss', html: 'html', go: 'go', yaml: 'yaml', yml: 'yaml',
    toml: 'toml', xml: 'xml', sql: 'sql', sh: 'shell', bash: 'shell', txt: 'plaintext',
  };
  return map[ext] ?? 'plaintext';
}