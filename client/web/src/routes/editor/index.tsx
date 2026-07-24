import { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { Layout, Avatar } from 'antd';
import {
  FolderOutlined,
  FileOutlined,
  FileTextOutlined,
  PlusOutlined,
  MessageOutlined,
  TeamOutlined,
  BranchesOutlined,
} from '@ant-design/icons';
import { EditorView, keymap, lineNumbers, highlightActiveLineGutter, highlightSpecialChars, drawSelection, dropCursor, rectangularSelection, crosshairCursor, highlightActiveLine } from '@codemirror/view';
import { EditorState } from '@codemirror/state';
import { indentOnInput, syntaxHighlighting, defaultHighlightStyle, bracketMatching } from '@codemirror/language';
import { history, historyKeymap, indentWithTab } from '@codemirror/commands';
import { searchKeymap } from '@codemirror/search';
import { lintKeymap } from '@codemirror/lint';
import { closeBrackets, autocompletion, closeBracketsKeymap, completionKeymap } from '@codemirror/autocomplete';
import { oneDark } from '@codemirror/theme-one-dark';
import { javascript } from '@codemirror/lang-javascript';
import { python } from '@codemirror/lang-python';
import { json } from '@codemirror/lang-json';
import { html } from '@codemirror/lang-html';
import { css } from '@codemirror/lang-css';
import { markdown } from '@codemirror/lang-markdown';
import { useTranslation } from 'react-i18next';
import { useParams } from 'react-router-dom';
import EditorSkeleton from '../../components/skeleton/EditorSkeleton';
import { useRepositoriesStore } from '../../stores/repositories';
import type { RepoFile, RepoMember } from '../../api/repositories';

const { Sider, Content } = Layout;

const borderColor = '#21262d';
const hoverBg = '#1c2333';
const activeBg = '#1a2332';
const textSecondary = '#8b949e';
const textPrimary = '#e6edf3';
const textTertiary = '#6e7681';
const blueLight = '#58a6ff';
const bluePrimary = '#1f6feb';
const blueDark = '#0d419d';
const bgPrimary = '#0d1117';
const bgSecondary = '#161b22';
const bgTertiary = '#1c2128';
const green = '#3fb950';

interface TreeNode {
  title: string;
  key: string;
  type: 'folder' | 'file';
  fileType?: 'ts' | 'json' | 'md' | 'css' | 'py' | 'html';
  children?: TreeNode[];
}

const avatarColors = ['#1f6feb', '#3fb950', '#58a6ff', '#bc8cff', '#d29922', '#f85149', '#f0883e', '#7956d9'];

function getInitials(name: string): string {
  return name.split(/[\s_-]/).map((n) => n[0]).join('').toUpperCase().slice(0, 2) || '?';
}

function getAvatarColor(initials: string): string {
  let hash = 0;
  for (let i = 0; i < initials.length; i++) {
    hash = initials.charCodeAt(i) + ((hash << 5) - hash);
  }
  return avatarColors[Math.abs(hash) % avatarColors.length];
}

function getFileType(filename: string): TreeNode['fileType'] | undefined {
  const ext = filename.split('.').pop()?.toLowerCase();
  if (ext === 'ts' || ext === 'tsx') return 'ts';
  if (ext === 'json') return 'json';
  if (ext === 'md' || ext === 'markdown') return 'md';
  if (ext === 'css' || ext === 'scss' || ext === 'less') return 'css';
  if (ext === 'py') return 'py';
  if (ext === 'html' || ext === 'htm') return 'html';
  return undefined;
}

function getLanguageExtension(path: string) {
  const ext = path.split('.').pop()?.toLowerCase();
  switch (ext) {
    case 'js':
    case 'jsx':
    case 'mjs':
      return javascript();
    case 'ts':
    case 'tsx':
      return javascript({ typescript: true });
    case 'py':
      return python();
    case 'json':
      return json();
    case 'html':
    case 'htm':
      return html();
    case 'css':
    case 'scss':
    case 'less':
      return css();
    case 'md':
    case 'markdown':
      return markdown();
    default:
      return undefined;
  }
}

function buildTree(files: RepoFile[]): TreeNode[] {
  const root: TreeNode = { title: 'root', key: 'root', type: 'folder', children: [] };
  for (const file of files) {
    const parts = file.path.split('/');
    let current = root;
    for (let i = 0; i < parts.length; i++) {
      const part = parts[i];
      const isLast = i === parts.length - 1;
      const key = parts.slice(0, i + 1).join('/');
      const existing = current.children?.find((c) => c.key === key);
      if (existing) {
        current = existing;
        continue;
      }
      const node: TreeNode = {
        title: part,
        key,
        type: isLast ? (file.type === 'directory' ? 'folder' : 'file') : 'folder',
        fileType: isLast ? getFileType(part) : undefined,
        children: isLast ? undefined : [],
      };
      current.children!.push(node);
      current = node;
    }
  }
  return root.children || [];
}

function findFirstFile(nodes: TreeNode[]): TreeNode | null {
  for (const node of nodes) {
    if (node.type === 'file') return node;
    if (node.children) {
      const found = findFirstFile(node.children);
      if (found) return found;
    }
  }
  return null;
}

function findFileByKey(nodes: TreeNode[], key: string): TreeNode | null {
  for (const node of nodes) {
    if (node.key === key) return node;
    if (node.children) {
      const found = findFileByKey(node.children, key);
      if (found) return found;
    }
  }
  return null;
}

const sampleCode = `// Select a file from the explorer to view repository contents.`;

const basicSetup = () => [
  lineNumbers(),
  highlightActiveLineGutter(),
  highlightSpecialChars(),
  history(),
  drawSelection(),
  dropCursor(),
  indentOnInput(),
  syntaxHighlighting(defaultHighlightStyle, { fallback: true }),
  bracketMatching(),
  closeBrackets(),
  autocompletion(),
  rectangularSelection(),
  crosshairCursor(),
  highlightActiveLine(),
  keymap.of([
    ...closeBracketsKeymap,
    ...historyKeymap,
    ...completionKeymap,
    ...searchKeymap,
    ...lintKeymap,
    indentWithTab,
  ]),
];

const discussions = [
  { id: 1, author: 'Li Wei', line: 'Line 11', code: 'handleMessage(msg)', text: 'Should we add error handling for malformed JSON messages? The current parse will throw.', replies: 2, time: '10m ago', icon: '💬' },
  { id: 2, author: 'Chen Mei', line: 'Line 15', code: 'startHeartbeat()', text: 'Should we make the heartbeat interval configurable instead of hardcoded?', replies: 1, time: '25m ago', icon: '💬' },
  { id: 3, author: 'Wang Jun', line: 'Line 34', code: 'getRetryDelay()', text: 'Fixed the jitter calculation — changed Math.random() to use crypto.getRandomValues per review feedback.', replies: 0, time: '1h ago', icon: '✅', resolved: true },
];

function FileIcon({ type, fileType }: { type: 'folder' | 'file'; fileType?: string }) {
  let color = blueLight;
  if (type === 'file') {
    switch (fileType) {
      case 'ts': color = '#3178c6'; break;
      case 'json': color = '#d29922'; break;
      case 'md': color = blueLight; break;
      case 'css': color = '#563d7c'; break;
      case 'py': color = '#3572A5'; break;
      case 'html': color = '#e34c26'; break;
      default: color = textSecondary;
    }
  }
  return (
    <span style={{ width: 14, height: 14, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, fontSize: 14, color }}>
      {type === 'folder' ? <FolderOutlined /> : <FileOutlined />}
    </span>
  );
}

function TreeNodeView({
  node,
  depth,
  selectedKey,
  onSelect,
}: {
  node: TreeNode;
  depth: number;
  selectedKey: string;
  onSelect: (key: string) => void;
}) {
  const isSelected = selectedKey === node.key;
  const hasChildren = node.children && node.children.length > 0;
  const [expanded, setExpanded] = useState(hasChildren);

  return (
    <div>
      <div
        onClick={() => {
          onSelect(node.key);
          if (hasChildren) setExpanded(!expanded);
        }}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          padding: '4px 12px',
          fontSize: 13,
          cursor: 'pointer',
          color: isSelected ? textPrimary : textSecondary,
          background: isSelected ? activeBg : 'transparent',
          transition: 'all 0.15s',
          fontFamily: "'JetBrains Mono', monospace",
        }}
        onMouseEnter={(e) => {
          if (!isSelected) {
            e.currentTarget.style.background = hoverBg;
            e.currentTarget.style.color = textPrimary;
          }
        }}
        onMouseLeave={(e) => {
          if (!isSelected) {
            e.currentTarget.style.background = 'transparent';
            e.currentTarget.style.color = textSecondary;
          }
        }}
      >
        {Array.from({ length: depth }).map((_, i) => (
          <span key={i} style={{ width: 16, flexShrink: 0 }} />
        ))}
        <FileIcon type={node.type} fileType={node.fileType} />
        <span>{node.title}</span>
      </div>
      {expanded && hasChildren && (
        <div>
          {node.children!.map((child) => (
            <TreeNodeView key={child.key} node={child} depth={depth + 1} selectedKey={selectedKey} onSelect={onSelect} />
          ))}
        </div>
      )}
    </div>
  );
}

export default function EditorPage() {
  const { owner, repo } = useParams<{ owner?: string; repo?: string }>();
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<string | null>(null);
  const [openTabs, setOpenTabs] = useState<string[]>([]);
  const [panelTab, setPanelTab] = useState('discussions');
  const [selectedTreeKey, setSelectedTreeKey] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const { t } = useTranslation();
  const editorRef = useRef<HTMLDivElement>(null);
  const viewRef = useRef<EditorView | null>(null);

  const {
    currentRepo,
    files,
    currentBlob,
    members,
    fetchRepositoryByPath,
    fetchTree,
    fetchBlob,
    fetchMembers,
    clearCurrent,
  } = useRepositoriesStore();

  const fileTree = useMemo(() => buildTree(files), [files]);

  // Load repository
  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      setLoading(true);
      setError(null);
      if (!owner || !repo) {
        setLoading(false);
        return;
      }
      try {
        await fetchRepositoryByPath(owner, repo);
        if (cancelled) return;
        const repoId = useRepositoriesStore.getState().currentRepo?.id;
        if (!repoId) {
          setError('Repository not found');
          setLoading(false);
          return;
        }
        await Promise.all([fetchTree(repoId), fetchMembers(repoId)]);
        if (cancelled) return;
        const tree = useRepositoriesStore.getState().files;
        const built = buildTree(tree);
        const readme = findFileByKey(built, 'README.md') || findFileByKey(built, 'readme.md');
        const defaultFile = readme || findFirstFile(built);
        if (defaultFile) {
          setActiveTab(defaultFile.key);
          setSelectedTreeKey(defaultFile.key);
          setOpenTabs([defaultFile.key]);
          await fetchBlob(repoId, defaultFile.key);
        }
      } catch (e) {
        if (!cancelled) setError((e as Error).message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    load();
    return () => {
      cancelled = true;
      clearCurrent();
    };
  }, [owner, repo, fetchRepositoryByPath, fetchTree, fetchBlob, fetchMembers, clearCurrent]);

  const handleSelectFile = useCallback(async (key: string) => {
    setSelectedTreeKey(key);
    const node = findFileByKey(fileTree, key);
    if (!node || node.type !== 'file') return;
    setActiveTab(key);
    setOpenTabs((prev) => (prev.includes(key) ? prev : [...prev, key]));
    const repoId = currentRepo?.id;
    if (repoId) {
      try {
        await fetchBlob(repoId, key);
      } catch {
        // 错误已由 store 记录
      }
    }
  }, [fileTree, currentRepo?.id, fetchBlob]);

  const closeTab = useCallback((key: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setOpenTabs((prev) => {
      const idx = prev.indexOf(key);
      const next = prev.filter((k) => k !== key);
      if (activeTab === key) {
        const newActive = next[idx] ?? next[idx - 1] ?? null;
        setActiveTab(newActive);
        if (newActive) {
          setSelectedTreeKey(newActive);
          const repoId = currentRepo?.id;
          if (repoId) fetchBlob(repoId, newActive);
        }
      }
      return next;
    });
  }, [activeTab, currentRepo?.id, fetchBlob]);

  // Initialize / update CodeMirror editor
  useEffect(() => {
    if (loading || !editorRef.current) return;
    if (viewRef.current) {
      viewRef.current.destroy();
      viewRef.current = null;
    }
    const content = currentBlob?.content ?? sampleCode;
    const lang = activeTab ? getLanguageExtension(activeTab) : undefined;
    const extensions = [basicSetup(), oneDark, EditorView.theme({ '&': { height: '100%' }, '.cm-scroller': { overflow: 'auto' } })];
    if (lang) extensions.push(lang);

    const state = EditorState.create({
      doc: content,
      extensions,
    });
    viewRef.current = new EditorView({ state, parent: editorRef.current });
    return () => {
      viewRef.current?.destroy();
      viewRef.current = null;
    };
  }, [loading, activeTab, currentBlob]);

  const collaborators = useMemo(() => {
    return (members as RepoMember[]).map((m) => {
      const name = m.user?.username || m.user_id;
      const initials = getInitials(name);
      return {
        initials,
        color: getAvatarColor(initials),
        border: getAvatarColor(initials),
        title: `${name} — ${m.role}`,
      };
    });
  }, [members]);

  const editors = useMemo(() => {
    return (members as RepoMember[]).map((m) => {
      const name = m.user?.username || m.user_id;
      const initials = getInitials(name);
      return {
        initials,
        color: getAvatarColor(initials),
        name,
        file: activeTab || '—',
        status: 'viewing' as const,
      };
    });
  }, [members, activeTab]);

  if (loading) return <EditorSkeleton />;

  if (error || !owner || !repo) {
    return (
      <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: textSecondary }}>
        {error || t('app.codeEditor.selectRepository', { defaultValue: '请从仓库列表选择一个仓库以浏览代码' })}
      </div>
    );
  }

  const activeNode = activeTab ? findFileByKey(fileTree, activeTab) : null;
  const breadcrumb = activeNode ? activeNode.key.split('/') : [];

  return (
    <Layout style={{ height: '100%', background: 'transparent' }}>
      {/* Left Sidebar */}
      <Sider
        width={260}
        style={{
          background: bgSecondary,
          borderRight: `1px solid ${borderColor}`,
          display: 'flex',
          flexDirection: 'column',
          flexShrink: 0,
        }}
      >
        <div
          style={{
            padding: '10px 12px',
            borderBottom: `1px solid ${borderColor}`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <span
            style={{
              fontSize: 11,
              textTransform: 'uppercase',
              letterSpacing: 1,
              color: textTertiary,
              fontWeight: 600,
            }}
          >
            Explorer — {currentRepo?.name || `${owner}/${repo}`}
          </span>
          <button
            style={{
              background: 'none',
              border: 'none',
              color: textTertiary,
              cursor: 'pointer',
              padding: 2,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
            onMouseEnter={(e) => { e.currentTarget.style.color = textPrimary; }}
            onMouseLeave={(e) => { e.currentTarget.style.color = textTertiary; }}
          >
            <PlusOutlined style={{ fontSize: 14 }} />
          </button>
        </div>
        <div style={{ flex: 1, overflow: 'auto', padding: '4px 0' }}>
          {fileTree.map((node) => (
            <TreeNodeView
              key={node.key}
              node={node}
              depth={0}
              selectedKey={selectedTreeKey}
              onSelect={handleSelectFile}
            />
          ))}
        </div>
      </Sider>

      {/* Main Editor Area */}
      <Layout style={{ background: 'transparent' }}>
        {/* Tabs */}
        <div style={{ display: 'flex', background: bgSecondary, borderBottom: `1px solid ${borderColor}`, overflowX: 'auto', flexShrink: 0 }}>
          {openTabs.map((tab) => {
            const isActive = activeTab === tab;
            const tabNode = findFileByKey(fileTree, tab);
            return (
              <div
                key={tab}
                onClick={() => handleSelectFile(tab)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  padding: '8px 16px',
                  fontSize: 12,
                  color: isActive ? textPrimary : textSecondary,
                  borderRight: `1px solid ${borderColor}`,
                  cursor: 'pointer',
                  background: isActive ? bgPrimary : 'transparent',
                  position: 'relative',
                  whiteSpace: 'nowrap',
                  fontFamily: "'JetBrains Mono', monospace",
                  transition: 'all 0.15s',
                }}
              >
                <FileTextOutlined style={{ fontSize: 14, color: '#3178c6' }} />
                {tabNode?.title || tab}
                <span
                  style={{
                    width: 16,
                    height: 16,
                    borderRadius: 3,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    opacity: isActive ? 1 : 0,
                    transition: 'opacity 0.15s',
                    fontSize: 12,
                  }}
                  onMouseEnter={(e) => { e.currentTarget.style.background = borderColor; }}
                  onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
                  onClick={(e) => closeTab(tab, e)}
                >
                  ×
                </span>
                {isActive && (
                  <div
                    style={{
                      position: 'absolute',
                      top: 0,
                      left: 0,
                      right: 0,
                      height: 2,
                      background: bluePrimary,
                    }}
                  />
                )}
              </div>
            );
          })}
        </div>

        {/* Breadcrumb */}
        <div
          style={{
            padding: '4px 16px',
            fontSize: 11,
            color: textTertiary,
            fontFamily: "'JetBrains Mono', monospace",
            background: bgPrimary,
            borderBottom: `1px solid ${borderColor}`,
            display: 'flex',
            alignItems: 'center',
            gap: 4,
            flexShrink: 0,
          }}
        >
          <span style={{ cursor: 'pointer' }}>{currentRepo?.name || repo}</span>
          {breadcrumb.map((part, idx) => (
            <span key={idx} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <span>/</span>
              <span style={idx === breadcrumb.length - 1 ? { color: textPrimary } : { cursor: 'pointer' }}>{part}</span>
            </span>
          ))}
        </div>

        {/* Collab Bar */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            padding: '3px 16px',
            background: bgTertiary,
            borderBottom: `1px solid ${borderColor}`,
            gap: 12,
            fontSize: 12,
            flexShrink: 0,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 5, color: textSecondary }}>
            <span
              style={{
                width: 7,
                height: 7,
                borderRadius: '50%',
                background: green,
                boxShadow: `0 0 6px ${green}`,
              }}
            />
            {t('app.codeEditor.online')}
          </div>
          <div style={{ display: 'flex', alignItems: 'center' }}>
            {collaborators.slice(0, 6).map((c, i) => (
              <div
                key={`${c.initials}-${i}`}
                style={{
                  marginLeft: i > 0 ? -6 : 0,
                  transition: 'transform 0.15s, box-shadow 0.15s',
                  cursor: 'pointer',
                }}
                onMouseEnter={(e: React.MouseEvent<HTMLDivElement>) => { e.currentTarget.style.transform = 'translateY(-2px)'; e.currentTarget.style.zIndex = '5'; }}
                onMouseLeave={(e: React.MouseEvent<HTMLDivElement>) => { e.currentTarget.style.transform = 'translateY(0)'; e.currentTarget.style.zIndex = 'auto'; }}
                title={c.title}
              >
                <Avatar
                  size={24}
                  style={{
                    background: c.color,
                    fontSize: 9,
                    fontWeight: 600,
                    border: `2px solid ${c.border === '#d29922' ? bgTertiary : c.border}`,
                  }}
                >
                  {c.initials}
                </Avatar>
              </div>
            ))}
          </div>
          <div style={{ color: textTertiary, marginLeft: 'auto', fontSize: 11, display: 'flex', alignItems: 'center', gap: 6 }}>
            <TeamOutlined style={{ fontSize: 14 }} />
            <strong style={{ color: textSecondary }}>{Math.max(1, members.length)}</strong> editors viewing this file
          </div>
        </div>

        {/* Code Editor */}
        <Content style={{ display: 'flex', overflow: 'hidden', background: bgPrimary, flex: 1 }}>
          <div ref={editorRef} style={{ flex: 1, overflow: 'auto' }} />
        </Content>

        {/* Collab Panel */}
        <div
          style={{
            height: 160,
            background: bgPrimary,
            borderTop: `1px solid ${borderColor}`,
            display: 'flex',
            flexDirection: 'column',
            flexShrink: 0,
          }}
        >
          <div style={{ display: 'flex', background: bgSecondary, borderBottom: `1px solid ${borderColor}`, padding: '0 8px', flexShrink: 0 }}>
            {[
              { key: 'discussions', icon: <MessageOutlined style={{ fontSize: 12 }} />, label: t('app.codeEditor.discussions'), count: discussions.length },
              { key: 'editors', icon: <TeamOutlined style={{ fontSize: 12 }} />, label: t('app.codeEditor.activity'), count: editors.length },
            ].map((tab) => (
              <div
                key={tab.key}
                onClick={() => setPanelTab(tab.key)}
                style={{
                  padding: '6px 12px',
                  fontSize: 11,
                  color: panelTab === tab.key ? textPrimary : textSecondary,
                  cursor: 'pointer',
                  borderBottom: `2px solid ${panelTab === tab.key ? bluePrimary : 'transparent'}`,
                  textTransform: 'uppercase',
                  letterSpacing: 0.5,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                  fontFamily: "'Inter', system-ui, sans-serif",
                  transition: 'all 0.15s',
                }}
                onMouseEnter={(e) => { if (panelTab !== tab.key) e.currentTarget.style.color = textPrimary; }}
                onMouseLeave={(e) => { if (panelTab !== tab.key) e.currentTarget.style.color = textSecondary; }}
              >
                {tab.icon} {tab.label}
                <span
                  style={{
                    background: bgTertiary,
                    padding: '0 6px',
                    borderRadius: 8,
                    fontSize: 10,
                    color: textTertiary,
                  }}
                >
                  {tab.count}
                </span>
              </div>
            ))}
          </div>
          <div style={{ flex: 1, overflow: 'auto', padding: '6px 0' }}>
            {panelTab === 'discussions' &&
              discussions.map((d) => (
                <div
                  key={d.id}
                  style={{
                    display: 'flex',
                    gap: 10,
                    padding: '8px 16px',
                    cursor: 'pointer',
                    transition: 'all 0.15s',
                    borderLeft: '3px solid transparent',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = hoverBg;
                    e.currentTarget.style.borderLeftColor = bluePrimary;
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = 'transparent';
                    e.currentTarget.style.borderLeftColor = 'transparent';
                  }}
                >
                  <span style={{ flexShrink: 0, fontSize: 13, marginTop: 1 }}>{d.icon}</span>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 12, fontWeight: 600, color: textPrimary }}>{d.author}</div>
                    <div style={{ fontSize: 11, color: blueLight, fontFamily: "'JetBrains Mono', monospace", marginTop: 1 }}>
                      {d.line} — <span style={{ color: textTertiary }}>{d.code}</span>
                    </div>
                    <div style={{ fontSize: 12, color: textSecondary, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', marginTop: 2 }}>
                      {d.text}
                    </div>
                    <div style={{ fontSize: 11, color: textTertiary, display: 'flex', gap: 8, marginTop: 3 }}>
                      <span style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
                        <MessageOutlined style={{ fontSize: 10 }} /> {d.resolved ? 'Resolved' : `${d.replies} replies`}
                      </span>
                      <span>{d.time}</span>
                    </div>
                  </div>
                </div>
              ))}
            {panelTab === 'editors' && (
              <div style={{ padding: '6px 0' }}>
                {editors.map((ed) => (
                  <div
                    key={ed.initials}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 10,
                      padding: '8px 16px',
                      fontSize: 12,
                      color: textSecondary,
                    }}
                  >
                    <Avatar size={24} style={{ background: ed.color, fontSize: 9, fontWeight: 600, flexShrink: 0 }}>{ed.initials}</Avatar>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontWeight: 600, color: textPrimary }}>{ed.name}</div>
                      <div style={{ fontSize: 11, color: textTertiary, fontFamily: "'JetBrains Mono', monospace" }}>{ed.file}</div>
                    </div>
                    <div style={{ fontSize: 10, display: 'flex', alignItems: 'center', gap: 4 }}>
                      <span
                        style={{
                          width: 6,
                          height: 6,
                          borderRadius: '50%',
                          background: ed.status === 'viewing' ? blueLight : '#d29922',
                        }}
                      />
                      {ed.status}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Status Bar */}
        <div
          style={{
            height: 24,
            background: blueDark,
            display: 'flex',
            alignItems: 'center',
            padding: '0 12px',
            fontSize: 11,
            color: 'rgba(255,255,255,0.8)',
            gap: 16,
            flexShrink: 0,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <BranchesOutlined style={{ fontSize: 12 }} />
            {currentRepo?.default_branch || 'main'}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: green, display: 'inline-block', marginRight: 2 }} />
            {t('app.codeEditor.online')}
          </div>
          <div style={{ marginLeft: 'auto', display: 'flex', gap: 16 }}>
            <span>Ln 24, Col 38</span>
            <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}><TeamOutlined style={{ fontSize: 12 }} /> {members.length || 1} online</span>
            <span>{activeNode?.fileType ? activeNode.fileType.toUpperCase() : 'Text'}</span>
            <span>UTF-8</span>
          </div>
        </div>
      </Layout>
    </Layout>
  );
}
