import { useState, useEffect, useRef } from 'react';
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
import { useTranslation } from 'react-i18next';
import EditorSkeleton from '../../components/skeleton/EditorSkeleton';

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
  fileType?: 'ts' | 'json' | 'md' | 'css';
  children?: TreeNode[];
}

const fileTree: TreeNode[] = [
  {
    title: 'PERSEUS-CORE',
    key: 'perseus-core',
    type: 'folder',
    children: [
      {
        title: 'src',
        key: 'src',
        type: 'folder',
        children: [
          {
            title: 'core',
            key: 'core',
            type: 'folder',
            children: [
              { title: 'engine.ts', key: 'engine.ts', type: 'file', fileType: 'ts' },
              { title: 'crdt.ts', key: 'crdt.ts', type: 'file', fileType: 'ts' },
            ],
          },
          {
            title: 'collab',
            key: 'collab',
            type: 'folder',
            children: [
              { title: 'websocket-client.ts', key: 'websocket-client.ts', type: 'file', fileType: 'ts' },
              { title: 'presence.ts', key: 'presence.ts', type: 'file', fileType: 'ts' },
            ],
          },
          {
            title: 'editor',
            key: 'editor',
            type: 'folder',
            children: [
              { title: 'renderer.ts', key: 'renderer.ts', type: 'file', fileType: 'ts' },
              { title: 'highlighter.ts', key: 'highlighter.ts', type: 'file', fileType: 'ts' },
            ],
          },
          { title: 'utils', key: 'utils', type: 'folder' },
        ],
      },
      { title: 'package.json', key: 'package.json', type: 'file', fileType: 'json' },
      { title: 'tsconfig.json', key: 'tsconfig.json', type: 'file', fileType: 'json' },
      { title: 'README.md', key: 'README.md', type: 'file', fileType: 'md' },
    ],
  },
];

const fileTabs = ['engine.ts', 'websocket-client.ts', 'presence.ts'];

const sampleCode = `import { EventEmitter } from 'events';
import { CRDTDocument, Operation } from './crdt';
import { PresenceManager, CursorState } from './presence';
import { MessageHandler, ConnectionState, WSMessage } from './types';

const MAX_RETRY_DELAY = 30000;
const BASE_RETRY_DELAY = 1000;
const HEARTBEAT_INTERVAL = 15000;

/**
 * WebSocket client for real-time collaboration.
 * Implements automatic reconnection with exponential
 * backoff and message queuing for offline support.
 */
export class WebSocketClient extends EventEmitter {
  private ws: WebSocket | null = null;
  private url: string;
  private retryCount = 0;
  private messageQueue: WSMessage[] = [];
  private presenceManager: PresenceManager;
  private heartbeatTimer: NodeJS.Timer | null = null;
  private state: ConnectionState = 'disconnected';

  constructor(url: string, private doc: CRDTDocument) {
    super();
    this.url = url;
    this.presenceManager = new PresenceManager();
    this.setupDocumentListeners();
  }

  /**
   * Establish WebSocket connection with retry logic.
   */
  async connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        this.ws = new WebSocket(this.url);
        this.state = 'connecting';
        this.emit('stateChange', this.state);

        this.ws.onopen = () => {
          this.state = 'connected';
          this.retryCount = 0;
          this.emit('stateChange', this.state);
          this.startHeartbeat();
          this.flushMessageQueue();
          resolve();
        };
      } catch (err) {
        reject(err);
      }
    });
  }

  private getRetryDelay(): number {
    const delay = Math.min(
      BASE_RETRY_DELAY * Math.pow(2, this.retryCount),
      MAX_RETRY_DELAY
    );
    return delay + Math.random() * 1000;
  }

  /**
   * Send an operation to all connected peers.
   */
  sendOperation(op: Operation): void {
    const msg: WSMessage = {
      type: 'operation',
      payload: op,
      timestamp: Date.now(),
      clientId: this.presenceManager.clientId
    };
    if (this.state === 'connected') {
      this.ws!.send(JSON.stringify(msg));
    } else {
      this.messageQueue.push(msg);
    }
  }
}
`;

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

const collaborators = [
  { initials: 'LW', color: '#3fb950', border: '#3fb950', title: 'Li Wei — editing engine.ts' },
  { initials: 'CM', color: '#58a6ff', border: '#58a6ff', title: 'Chen Mei — viewing websocket-client.ts' },
  { initials: 'WJ', color: '#bc8cff', border: '#bc8cff', title: 'Wang Jun — idle' },
  { initials: 'ZL', color: '#d29922', border: '#d29922', title: 'Zhang Lei (you) — editing' },
];

const discussions = [
  { id: 1, author: 'Li Wei', line: 'Line 11', code: 'handleMessage(msg)', text: 'Should we add error handling for malformed JSON messages? The current parse will throw.', replies: 2, time: '10m ago', icon: '💬' },
  { id: 2, author: 'Chen Mei', line: 'Line 15', code: 'startHeartbeat()', text: 'Should we make the heartbeat interval configurable instead of hardcoded?', replies: 1, time: '25m ago', icon: '💬' },
  { id: 3, author: 'Wang Jun', line: 'Line 34', code: 'getRetryDelay()', text: 'Fixed the jitter calculation — changed Math.random() to use crypto.getRandomValues per review feedback.', replies: 0, time: '1h ago', icon: '✅', resolved: true },
];

const editors = [
  { initials: 'LW', color: '#3fb950', name: 'Li Wei', file: 'engine.ts', status: 'editing' },
  { initials: 'CM', color: '#58a6ff', name: 'Chen Mei', file: 'websocket-client.ts', status: 'viewing' },
  { initials: 'WJ', color: '#bc8cff', name: 'Wang Jun', file: 'crdt.ts', status: 'viewing' },
  { initials: 'ZL', color: '#d29922', name: 'Zhang Lei', file: 'websocket-client.ts (you)', status: 'editing' },
];

function FileIcon({ type, fileType }: { type: 'folder' | 'file'; fileType?: string }) {
  let color = blueLight;
  if (type === 'file') {
    switch (fileType) {
      case 'ts': color = '#3178c6'; break;
      case 'json': color = '#d29922'; break;
      case 'md': color = blueLight; break;
      case 'css': color = '#563d7c'; break;
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
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('websocket-client.ts');
  const [panelTab, setPanelTab] = useState('discussions');
  const [selectedTreeKey, setSelectedTreeKey] = useState('websocket-client.ts');
  const { t } = useTranslation();
  const editorRef = useRef<HTMLDivElement>(null);
  const viewRef = useRef<EditorView | null>(null);

  useEffect(() => {
    const timer = setTimeout(() => setLoading(false), 600);
    return () => clearTimeout(timer);
  }, []);

  useEffect(() => {
    if (loading || !editorRef.current || viewRef.current) return;
    const state = EditorState.create({
      doc: sampleCode,
      extensions: [basicSetup(), oneDark, javascript(), EditorView.theme({ '&': { height: '100%' }, '.cm-scroller': { overflow: 'auto' } })],
    });
    viewRef.current = new EditorView({ state, parent: editorRef.current });
    return () => {
      viewRef.current?.destroy();
      viewRef.current = null;
    };
  }, [loading]);

  if (loading) return <EditorSkeleton />;

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
            Explorer — perseus-core
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
              onSelect={setSelectedTreeKey}
            />
          ))}
        </div>
      </Sider>

      {/* Main Editor Area */}
      <Layout style={{ background: 'transparent' }}>
        {/* Tabs */}
        <div style={{ display: 'flex', background: bgSecondary, borderBottom: `1px solid ${borderColor}`, overflowX: 'auto', flexShrink: 0 }}>
          {fileTabs.map((tab) => {
            const isActive = activeTab === tab;
            return (
              <div
                key={tab}
                onClick={() => setActiveTab(tab)}
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
                {tab}
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
          <span style={{ cursor: 'pointer' }}>perseus-core</span>
          <span>/</span>
          <span style={{ cursor: 'pointer' }}>src</span>
          <span>/</span>
          <span style={{ cursor: 'pointer' }}>collab</span>
          <span>/</span>
          <span style={{ color: textPrimary }}>websocket-client.ts</span>
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
            {collaborators.map((c, i) => (
              <div
                key={c.initials}
                style={{
                  marginLeft: i > 0 ? -6 : 0,
                  transition: 'transform 0.15s, box-shadow 0.15s',
                  cursor: 'pointer',
                }}
                onMouseEnter={(e: React.MouseEvent<HTMLDivElement>) => { e.currentTarget.style.transform = 'translateY(-2px)'; e.currentTarget.style.zIndex = '5'; }}
                onMouseLeave={(e: React.MouseEvent<HTMLDivElement>) => { e.currentTarget.style.transform = 'translateY(0)'; e.currentTarget.style.zIndex = 'auto'; }}
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
            <strong style={{ color: textSecondary }}>2</strong> editors viewing this file
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
              { key: 'discussions', icon: <MessageOutlined style={{ fontSize: 12 }} />, label: t('app.codeEditor.discussions'), count: 3 },
              { key: 'editors', icon: <TeamOutlined style={{ fontSize: 12 }} />, label: t('app.codeEditor.activity'), count: 4 },
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
                          background: ed.status === 'editing' ? green : ed.status === 'viewing' ? blueLight : '#d29922',
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
            main
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: green, display: 'inline-block', marginRight: 2 }} />
            {t('app.codeEditor.online')}
          </div>
          <div style={{ marginLeft: 'auto', display: 'flex', gap: 16 }}>
            <span>Ln 24, Col 38</span>
            <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}><TeamOutlined style={{ fontSize: 12 }} /> 4 online</span>
            <span>TypeScript</span>
            <span>UTF-8</span>
          </div>
        </div>
      </Layout>
    </Layout>
  );
}
