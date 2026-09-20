import { useState, useEffect, useRef, useMemo, useCallback, type CSSProperties } from 'react';
import { Layout, Avatar, Button, Input, Modal, Tooltip, message as antdMessage } from 'antd';
import {
  FolderOutlined,
  FileOutlined,
  FileTextOutlined,
  PlusOutlined,
  MessageOutlined,
  TeamOutlined,
  BranchesOutlined,
  SaveOutlined,
  EyeOutlined,
  EditOutlined,
  DeleteOutlined,
  ShareAltOutlined,
  AimOutlined,
  StopOutlined,
  UsergroupAddOutlined,
} from '@ant-design/icons';
import { EditorView, keymap, lineNumbers, highlightActiveLineGutter, highlightSpecialChars, drawSelection, dropCursor, rectangularSelection, crosshairCursor, highlightActiveLine } from '@codemirror/view';
import { EditorState, Compartment } from '@codemirror/state';
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
import Markdown from '../../components/Markdown';
import { CollabController, type CollabParticipant, type FollowState } from '../../components/editor/collabController';
import { useRepositoriesStore } from '../../stores/repositories';
import { useAuthStore } from '../../stores/auth';
import { chatApi } from '../../api/chat';
import { chatSocket, type PresenceUser } from '../../api/chatSocket';
import { repositoriesApi, type RepoFile } from '../../api/repositories';
import { discussionsApi, type DiscussionComment } from '../../api/discussions';
import { FloatingTreePanel } from '../../components/FloatingTreePanel';

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
const yellow = '#d29922';

export interface TreeNode {
  title: string;
  key: string;
  type: 'folder' | 'file';
  fileType?: 'ts' | 'json' | 'md' | 'css' | 'py' | 'html';
  children?: TreeNode[];
}

interface FloatPanelPos {
  key: string;
  left: number;
  top: number;
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

// F-606 空闲自动落盘: 连续 IDLE_AUTOSAVE_MS 无编辑且存在未保存内容时,
// 经协作会话落到 collab/draft-{branch} 草稿分支 (不触碰工作分支)。
const IDLE_AUTOSAVE_MS = 5 * 60 * 1000;
const IDLE_AUTOSAVE_POLL_MS = 30 * 1000;

const basicSetup = (onSave: () => void) => [
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
    // Ctrl/Cmd+S 提交保存, 阻止浏览器默认行为
    { key: 'Mod-s', preventDefault: true, run: () => { onSave(); return true; } },
  ]),
];

function formatCommentTime(dateStr: string | null): string {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  if (Number.isNaN(d.getTime())) return '';
  return d.toLocaleString([], { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

const linkButtonStyle: CSSProperties = {
  background: 'none',
  border: 'none',
  padding: 0,
  cursor: 'pointer',
  fontSize: 11,
  color: textSecondary,
  lineHeight: 1.4,
};

function DiscussionRow({
  comment,
  isReply,
  canResolve,
  canDelete,
  replying,
  replyValue,
  onReply,
  onReplyCancel,
  onReplyChange,
  onReplySubmit,
  onToggleResolve,
  onDelete,
  onJump,
}: {
  comment: DiscussionComment;
  isReply?: boolean;
  canResolve: boolean;
  canDelete: boolean;
  replying: boolean;
  replyValue: string;
  onReply: () => void;
  onReplyCancel: () => void;
  onReplyChange: (v: string) => void;
  onReplySubmit: () => void;
  onToggleResolve: () => void;
  onDelete: () => void;
  onJump: () => void;
}) {
  const { t } = useTranslation();
  const initials = getInitials(comment.author_username || comment.author_id);
  const color = getAvatarColor(initials);
  return (
    <div
      style={{
        display: 'flex',
        gap: 10,
        padding: '8px 16px',
        paddingLeft: isReply ? 40 : 16,
        borderBottom: `1px solid ${borderColor}`,
      }}
    >
      <Avatar size={24} style={{ background: color, fontSize: 9, fontWeight: 600, flexShrink: 0 }}>
        {initials}
      </Avatar>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 11, flexWrap: 'wrap' }}>
          <span style={{ fontWeight: 600, color: textPrimary }}>{comment.author_username}</span>
          <span style={{ color: blueLight, cursor: 'pointer' }} onClick={onJump}>
            {comment.file_path}{comment.line_number ? `:${comment.line_number}` : ''}
          </span>
          <span style={{ color: textTertiary }}>{formatCommentTime(comment.created_at)}</span>
          {comment.resolved && (
            <span style={{ color: green, fontSize: 10, background: 'rgba(63,185,80,0.12)', padding: '1px 6px', borderRadius: 8 }}>
              {t('app.codeEditor.resolved', { defaultValue: '已解决' })}
            </span>
          )}
        </div>
        <div
          style={{
            fontSize: 12,
            color: comment.resolved ? textTertiary : textSecondary,
            margin: '4px 0',
            textDecoration: comment.resolved ? 'line-through' : undefined,
            wordBreak: 'break-word',
            whiteSpace: 'pre-wrap',
            lineHeight: 1.5,
          }}
        >
          {comment.content}
        </div>
        <div style={{ display: 'flex', gap: 12, fontSize: 11 }}>
          {!comment.resolved && (
            <button style={linkButtonStyle} onClick={onReply}>
              {t('app.codeEditor.reply', { defaultValue: '回复' })}
            </button>
          )}
          {canResolve && (
            <button style={linkButtonStyle} onClick={onToggleResolve}>
              {comment.resolved
                ? t('app.codeEditor.reopen', { defaultValue: '重新打开' })
                : t('app.codeEditor.resolve', { defaultValue: '解决' })}
            </button>
          )}
          {canDelete && (
            <button style={{ ...linkButtonStyle, color: '#f85149' }} onClick={onDelete}>
              {t('app.codeEditor.deleteComment', { defaultValue: '删除' })}
            </button>
          )}
        </div>
        {replying && (
          <div style={{ display: 'flex', gap: 8, marginTop: 6 }}>
            <Input
              size="small"
              value={replyValue}
              onChange={(e) => onReplyChange(e.target.value)}
              placeholder={t('app.codeEditor.replyPlaceholder', { defaultValue: '回复该评论...' })}
              style={{ flex: 1, background: bgTertiary, borderColor: '#30363d', color: textPrimary }}
            />
            <Button
              size="small"
              type="primary"
              disabled={!replyValue.trim()}
              onClick={onReplySubmit}
              style={{ background: bluePrimary, borderColor: bluePrimary }}
            >
              {t('app.codeEditor.send', { defaultValue: '发送' })}
            </Button>
            <Button size="small" onClick={onReplyCancel}>
              {t('app.codeEditor.cancel', { defaultValue: '取消' })}
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}

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
  selectedKey,
  onSelect,
  onDelete,
  onMove,
  onDirPin,
}: {
  node: TreeNode;
  selectedKey: string;
  onSelect: (key: string) => void;
  onDelete?: (node: TreeNode) => void;
  onMove?: (node: TreeNode) => void;
  onDirPin?: (key: string, element: HTMLElement) => void;
}) {
  const isSelected = selectedKey === node.key;
  const hasChildren = node.children && node.children.length > 0;
  const { t } = useTranslation();

  return (
    <div>
      <div
        data-dir-path={node.type === 'folder' ? node.key : undefined}
        onClick={(e) => {
          if (node.type === 'folder') {
            if (hasChildren && onDirPin) onDirPin(node.key, e.currentTarget);
            return;
          }
          onSelect(node.key);
        }}
        className="cm-file-tree-row"
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
          position: 'relative',
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
        <FileIcon type={node.type} fileType={node.fileType} />
        <span>{node.title}</span>
        {(onDelete || onMove) && node.type === 'file' && (
          <div style={{ marginLeft: 'auto', display: 'flex', gap: 4, opacity: 0, transition: 'opacity 0.15s' }} className="cm-tree-delete-btn">
            {onMove && (
              <Tooltip title={t('app.codeEditor.moveFile', { defaultValue: '移动/重命名' })}>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onMove(node);
                  }}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: textTertiary,
                    cursor: 'pointer',
                    padding: '0 2px',
                    fontSize: 13,
                    display: 'flex',
                    alignItems: 'center',
                  }}
                  onMouseEnter={(e) => { e.currentTarget.style.color = blueLight; }}
                  onMouseLeave={(e) => { e.currentTarget.style.color = textTertiary; }}
                >
                  <EditOutlined />
                </button>
              </Tooltip>
            )}
            {onDelete && (
              <Tooltip title={t('app.codeEditor.deleteFile', { defaultValue: '删除文件' })}>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onDelete(node);
                  }}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: textTertiary,
                    cursor: 'pointer',
                    padding: '0 2px',
                    fontSize: 13,
                    display: 'flex',
                    alignItems: 'center',
                  }}
                  onMouseEnter={(e) => { e.currentTarget.style.color = '#f85149'; }}
                  onMouseLeave={(e) => { e.currentTarget.style.color = textTertiary; }}
                >
                  <DeleteOutlined />
                </button>
              </Tooltip>
            )}
          </div>
        )}
      </div>
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
  const [pinnedChain, setPinnedChain] = useState<FloatPanelPos[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isDirty, setIsDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveModalOpen, setSaveModalOpen] = useState(false);
  const [commitMessage, setCommitMessage] = useState('');
  // 预览绑定到具体文件: 切换文件自动退出预览, 无需 effect 复位
  const [previewTab, setPreviewTab] = useState<string | null>(null);
  const [previewContent, setPreviewContent] = useState('');
  const previewMode = previewTab != null && previewTab === activeTab;
  const [newFileModalOpen, setNewFileModalOpen] = useState(false);
  const [newFileName, setNewFileName] = useState('');
  const [newFileCreating, setNewFileCreating] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<TreeNode | null>(null);
  const [deleting, setDeleting] = useState(false);
  // 文件移动/重命名 (F-604)
  const [moveTarget, setMoveTarget] = useState<TreeNode | null>(null);
  const [moveToPath, setMoveToPath] = useState('');
  const [moveMessage, setMoveMessage] = useState('');
  const [moving, setMoving] = useState(false);
  const [cursor, setCursor] = useState({ line: 1, col: 1 });
  const [onlinePresence, setOnlinePresence] = useState<PresenceUser[]>([]);
  const [collabStatus, setCollabStatus] = useState<'connecting' | 'connected' | 'disconnected'>('disconnected');
  const [docParticipants, setDocParticipants] = useState<CollabParticipant[]>([]);
  // 跟随模式 (F-607): 跟随目标/跟随者/跟我来
  const [followState, setFollowState] = useState<FollowState>({
    following: null,
    followingName: null,
    followers: [],
    spotlightOn: false,
  });
  // 双态徽标: 会话同步状态(轮询 Yjs 未同步变更) + 最近一次保存产生的 Git 提交
  const [collabPending, setCollabPending] = useState(false);
  const [lastCommitSha, setLastCommitSha] = useState<string | null>(null);
  // 协作版本号 N (「会话已同步 · v{N}」): 由 collab-saved 广播的 version 填充
  const [collabVersion, setCollabVersion] = useState<number | null>(null);
  // 行内评论 (F-602): 当前文件评论 + 新建/回复/解决/删除
  const [discussions, setDiscussions] = useState<DiscussionComment[]>([]);
  const [discussionsLoading, setDiscussionsLoading] = useState(false);
  const [commentInput, setCommentInput] = useState('');
  const [replyingTo, setReplyingTo] = useState<string | null>(null);
  const [replyInput, setReplyInput] = useState('');
  const { t } = useTranslation();
  const editorRef = useRef<HTMLDivElement>(null);
  const viewRef = useRef<EditorView | null>(null);
  // 保存基线用 ref 承载, 避免闭包过期导致 dirty 判断失准
  const savedContentRef = useRef<string>('');
  const handleSaveRef = useRef<() => void>(() => {});
  // 全局搜索结果跳转携带 ?line= 时, 编辑器就绪后滚动到该行
  const pendingLineRef = useRef<number | null>(null);
  // F-606 空闲计时: 最近一次用户编辑时刻 (docChanged 时刷新);
  // 初始取极大值, 保证挂载后的首个周期不会误判为空闲
  const lastEditAtRef = useRef<number>(Number.MAX_SAFE_INTEGER);
  // F-204 协作编辑: collab 扩展经 Compartment 延迟装配 (init 后装配)
  const collabComp = useRef(new Compartment());
  const collabRef = useRef<CollabController | null>(null);

  const {
    currentRepo,
    files,
    currentBlob,
    members,
    fetchRepositoryByPath,
    fetchTree,
    fetchBlob,
    fetchMembers,
    commitFileContent,
    deleteFileContent,
    clearCurrent,
  } = useRepositoriesStore();

  const currentUserId = useAuthStore((s) => s.user?.id);
  // 邀请链接访客: ?invite=<token> 随连接透传给协作网关
  const inviteToken = useMemo(
    () => new URLSearchParams(window.location.search).get('invite') || undefined,
    [],
  );
  const isRepoMember =
    !!currentUserId &&
    !!currentRepo &&
    (currentRepo.owner_id === currentUserId || members.some((m) => m.user_id === currentUserId));
  // 协作写权限 (owner/admin/developer): 决定"跟我来"是否可发起
  const canWriteCollab =
    !!currentUserId &&
    !!currentRepo &&
    (currentRepo.owner_id === currentUserId ||
      members.some(
        (m) =>
          m.user_id === currentUserId &&
          ['owner', 'admin', 'developer'].includes(m.role),
      ));

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
        const loc = new URLSearchParams(window.location.search);
        const requestedFile = loc.get('file');
        const lineParam = loc.get('line');
        pendingLineRef.current = lineParam && Number(lineParam) > 0 ? Number(lineParam) : null;
        const requestedNode = requestedFile ? findFileByKey(built, requestedFile) : undefined;
        const readme = findFileByKey(built, 'README.md') || findFileByKey(built, 'readme.md');
        const defaultFile = requestedNode || readme || findFirstFile(built);
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

  // 实时在线协作者: 订阅仓库房间 presence
  useEffect(() => {
    const repoId = currentRepo?.id;
    if (!repoId) return;

    const joinedRoomRef = { current: '' };
    chatSocket.setHandlers({
      onPresence: (roomId, users) => {
        if (roomId === joinedRoomRef.current) setOnlinePresence(users);
      },
      onPresenceJoin: (roomId, user) => {
        if (roomId !== joinedRoomRef.current) return;
        setOnlinePresence((prev) =>
          prev.some((u) => u.user_id === user.user_id) ? prev : [...prev, user]
        );
      },
      onPresenceLeave: (roomId, user) => {
        if (roomId !== joinedRoomRef.current) return;
        setOnlinePresence((prev) => prev.filter((u) => u.user_id !== user.user_id));
      },
    });
    chatSocket.start();

    chatApi.getRepositoryRoom(repoId)
      .then((roomData) => {
        joinedRoomRef.current = roomData.id;
        chatSocket.joinRoom(roomData.id);
        chatSocket.requestPresenceList(roomData.id);
      })
      .catch(() => {});

    return () => {
      if (joinedRoomRef.current) chatSocket.leaveRoom(joinedRoomRef.current);
      chatSocket.setHandlers({});
      chatSocket.stop();
    };
  }, [currentRepo?.id]);

  // 双态徽标「会话已同步」: 轮询 Yjs 未同步变更 (断线缓冲时为 true)
  useEffect(() => {
    const timer = setInterval(() => {
      const c = collabRef.current;
      setCollabPending(!!c && c.isActive ? !!c.hasPendingChanges() : false);
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // M1 数据安全: 本地未提交或会话未同步时, 关闭/刷新页面前拦截提示
  useEffect(() => {
    const handler = (e: BeforeUnloadEvent) => {
      const pending = collabRef.current?.isActive ? collabRef.current.hasPendingChanges() : false;
      if (isDirty || pending) {
        e.preventDefault();
        e.returnValue = '';
      }
    };
    window.addEventListener('beforeunload', handler);
    return () => window.removeEventListener('beforeunload', handler);
  }, [isDirty]);

  const handleSelectFile = useCallback(async (key: string) => {
    setSelectedTreeKey(key);
    setPinnedChain([]);
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

const handleTreePin = useCallback((key: string, el: HTMLElement) => {
    const rect = el.getBoundingClientRect();
    setPinnedChain((prev) => {
      if (prev.length === 1 && prev[0].key === key) return [];
      return [{ key, left: rect.right + 4, top: rect.top }];
    });
  }, []);

  const handlePanelPin = useCallback((level: number, key: string, el: HTMLElement) => {
    const rect = el.getBoundingClientRect();
    setPinnedChain((prev) => {
      const base = prev.slice(0, level + 1);
      const reaching = prev.length === level + 2 && prev[level + 1]?.key === key;
      if (reaching) return base;
      return [...base, { key, left: rect.right + 4, top: rect.top }];
    });
  }, []);

  // 面包屑点击: 根段回到根文件树, 目录段加载该目录并钉出浮动面板
  const handleBreadcrumbRoot = useCallback(() => {
    setSelectedTreeKey('');
    setPinnedChain([]);
  }, []);

  const handleBreadcrumbDir = useCallback((level: number, path: string, el: HTMLElement) => {
    setSelectedTreeKey(path);
    const repoId = currentRepo?.id;
    const ref = currentRepo?.default_branch;
    if (repoId && ref) fetchTree(repoId, ref, path).catch(() => {});
    handlePanelPin(level, path, el);
  }, [currentRepo, fetchTree, handlePanelPin]);

  useEffect(() => {
    if (!pinnedChain.length) return;
    const handle = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      if (!target.closest('.cm-floating-panel') && !target.closest('[data-dir-path]')) {
        setPinnedChain([]);
      }
    };
    document.addEventListener('mousedown', handle);
    return () => document.removeEventListener('mousedown', handle);
  }, [pinnedChain.length]);

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

  // 保存: 优先走协作会话 (以服务端权威文本提交, 全员同步保存结果);
  // 会话不可用时回退 HTTP 直提编辑器当前内容
  const performSave = useCallback(async (message?: string) => {
    const repoId = currentRepo?.id;
    const path = activeTab;
    if (!repoId || !path || saving) return;
    const content = viewRef.current?.state.doc.toString() ?? currentBlob?.content ?? '';
    if (content === savedContentRef.current) {
      setIsDirty(false);
      return;
    }
    const controller = collabRef.current;
    if (controller?.isActive) {
      setSaving(true);
      controller.save(message || `Update ${path}`);
      return;
    }
    setSaving(true);
    try {
      const result = await commitFileContent(
        repoId,
        path,
        content,
        message || `Update ${path}`,
        currentRepo?.default_branch,
      );
      savedContentRef.current = content;
      setIsDirty(false);
      setLastCommitSha(result.commit_id.slice(0, 7));
      antdMessage.success(t('app.codeEditor.saved', { id: result.commit_id.slice(0, 7) }));
      // 后台刷新提交历史等派生数据
      fetchTree(repoId, currentRepo?.default_branch).catch(() => {});
    } catch (e) {
      antdMessage.error((e as Error).message || 'Save failed');
    } finally {
      setSaving(false);
    }
  }, [currentRepo, activeTab, currentBlob, saving, commitFileContent, fetchTree, t]);

  useEffect(() => {
    handleSaveRef.current = () => {
      if (isDirty && !saving) setSaveModalOpen(true);
    };
  }, [isDirty, saving, commitMessage]);

  // F-606 空闲自动落盘: 轮询检查 —— 连续 IDLE_AUTOSAVE_MS 无编辑且有未保存内容时,
  // 通过协作会话做一次草稿保存 (collab/draft-{branch})。无协作会话则不自动提交工作分支。
  useEffect(() => {
    if (!activeTab) return;
    const timer = setInterval(() => {
      if (saving || saveModalOpen || !isDirty) return;
      if (Date.now() - lastEditAtRef.current < IDLE_AUTOSAVE_MS) return;
      const controller = collabRef.current;
      if (!controller?.isActive) return;
      lastEditAtRef.current = Date.now();
      setSaving(true);
      controller.save(`Autosave ${activeTab}`, { draft: true });
    }, IDLE_AUTOSAVE_POLL_MS);
    return () => clearInterval(timer);
  }, [activeTab, isDirty, saving, saveModalOpen]);

  // 新建文件: 以空内容提交到默认分支, 随后刷新文件树并打开
  const handleCreateFile = useCallback(async () => {
    const repoId = currentRepo?.id;
    const name = newFileName.trim().replace(/^\/+|\/+$/g, '');
    if (!repoId || !name || newFileCreating) return;
    if (name.split('/').some((seg) => seg === '..' || seg === '.')) {
      antdMessage.error('Invalid file name');
      return;
    }
    setNewFileCreating(true);
    try {
      await commitFileContent(repoId, name, '', `Create ${name}`, currentRepo?.default_branch);
      await fetchTree(repoId, currentRepo?.default_branch);
      setOpenTabs((prev) => (prev.includes(name) ? prev : [...prev, name]));
      setActiveTab(name);
      setSelectedTreeKey(name);
      savedContentRef.current = '';
      setIsDirty(false);
      setNewFileModalOpen(false);
      setNewFileName('');
      antdMessage.success(t('app.codeEditor.fileCreated', { name }));
    } catch (e) {
      antdMessage.error((e as Error).message || 'Create file failed');
    } finally {
      setNewFileCreating(false);
    }
  }, [currentRepo, newFileName, newFileCreating, commitFileContent, fetchTree, t]);

  // 删除文件
  const handleDeleteFile = useCallback(async () => {
    const repoId = currentRepo?.id;
    if (!repoId || !deleteTarget || deleting) return;
    setDeleting(true);
    try {
      await deleteFileContent(repoId, deleteTarget.key, currentRepo?.default_branch);
      const delKey = deleteTarget.key;
      await fetchTree(repoId, currentRepo?.default_branch);
      setDeleteTarget(null);
      if (activeTab === delKey) {
        setActiveTab(null);
        setSelectedTreeKey('');
        setOpenTabs((prev) => prev.filter((k) => k !== delKey));
      }
      antdMessage.success(t('app.codeEditor.fileDeleted', { defaultValue: `已删除 ${delKey}` }));
    } catch (e) {
      antdMessage.error((e as Error).message || 'Delete failed');
    } finally {
      setDeleting(false);
    }
  }, [currentRepo, deleteTarget, deleting, deleteFileContent, fetchTree, activeTab, t]);

  // 移动/重命名文件: 请求弹窗预填 + 提交
  const handleMoveRequest = useCallback((node: TreeNode) => {
    if (node.type !== 'file') return;
    setMoveTarget(node);
    setMoveToPath(node.key);
    setMoveMessage(`Rename ${node.key}`);
  }, []);

  const handleMoveFile = useCallback(async () => {
    const repoId = currentRepo?.id;
    const to = moveToPath.trim();
    if (!repoId || !moveTarget || !to || moving) return;
    if (to === moveTarget.key) {
      setMoveTarget(null);
      return;
    }
    setMoving(true);
    try {
      const res = await repositoriesApi.moveFile(repoId, {
        from_path: moveTarget.key,
        to_path: to,
        message: moveMessage.trim() || `Rename ${moveTarget.key} to ${to}`,
        branch: currentRepo?.default_branch ?? undefined,
      });
      await fetchTree(repoId, currentRepo?.default_branch);
      const fromKey = moveTarget.key;
      setMoveTarget(null);
      setMoveToPath('');
      setMoveMessage('');
      if (activeTab === fromKey) {
        setActiveTab(res.to);
        setSelectedTreeKey(res.to);
        setOpenTabs((prev) => prev.map((k) => (k === fromKey ? res.to : k)));
      }
      antdMessage.success(t('app.codeEditor.fileMoved', { to: res.to, defaultValue: `已移动 ${res.to}` }));
    } catch (e) {
      antdMessage.error((e as Error).message || 'Move failed');
    } finally {
      setMoving(false);
    }
  }, [currentRepo, moveTarget, moveToPath, moveMessage, moving, fetchTree, activeTab, t]);

  // Initialize / update CodeMirror editor
  useEffect(() => {
    if (loading || !editorRef.current) return;
    if (viewRef.current) {
      viewRef.current.destroy();
      viewRef.current = null;
    }
    const content = currentBlob?.content ?? sampleCode;
    savedContentRef.current = content === sampleCode ? '\u0000-sample' : content;
    setIsDirty(false);
    setDocParticipants([]);
    setFollowState({ following: null, followingName: null, followers: [], spotlightOn: false });
    setLastCommitSha(null);
    setCollabVersion(null);
    const lang = activeTab ? getLanguageExtension(activeTab) : undefined;
    const extensions = [
      basicSetup(() => handleSaveRef.current()),
      oneDark,
      collabComp.current.of([]),
      EditorView.theme({ '&': { height: '100%' }, '.cm-scroller': { overflow: 'auto' } }),
      EditorView.updateListener.of((update) => {
        if (update.docChanged) {
          const dirty = update.state.doc.toString() !== savedContentRef.current;
          setIsDirty(dirty);
          // 内容再次偏离保存基线后, Git 已提交徽标失效
          if (dirty) setLastCommitSha(null);
          // 协作版本号同样只在当前快照有效
          if (dirty) setCollabVersion(null);
          // F-606 空闲计时基础: 最近一次用户编辑时刻
          lastEditAtRef.current = Date.now();
        }
        if (update.selectionSet || update.docChanged) {
          const head = update.state.selection.main.head;
          const line = update.state.doc.lineAt(head);
          setCursor({ line: line.number, col: head - line.from + 1 });
        }
      }),
    ];
    if (lang) extensions.push(lang);

    const state = EditorState.create({
      doc: content,
      extensions,
    });
    viewRef.current = new EditorView({ state, parent: editorRef.current });

    // F-204 协作: 打开文件即加入该文档的协作会话
    const repoId = currentRepo?.id;
    const branch = currentRepo?.default_branch || 'main';
    let controller: CollabController | null = null;
    if (repoId && activeTab && viewRef.current) {
      controller = new CollabController({
        docKey: `${repoId}:${branch}:${activeTab}`,
        repositoryId: repoId,
        branch,
        path: activeTab,
        inviteToken,
        onStatus: setCollabStatus,
        onParticipants: setDocParticipants,
        onFollowChange: setFollowState,
        onSaved: (msg) => {
          // 提交的是服务端权威文本快照: 本地仍有未确认变更时保持脏标记,
          // 待下次保存, 避免把未提交内容误标为已保存
          if (!controller?.hasPendingChanges()) {
            savedContentRef.current = viewRef.current?.state.doc.toString() ?? '';
            setIsDirty(false);
          }
          setSaving(false);
          setLastCommitSha(msg.commit_id.slice(0, 7));
          if (typeof msg.version === 'number') setCollabVersion(msg.version);
          antdMessage.success(
            t('app.codeEditor.collabSaved', { defaultValue: '协作编辑已提交' }) +
              ` ${msg.commit_id.slice(0, 7)}`
          );
        },
        onError: (err) => {
          setSaving(false);
          antdMessage.warning(err);
        },
      });
      controller.attach(viewRef.current, collabComp.current);
      collabRef.current = controller;
    }

    const pendingLine = pendingLineRef.current;
    if (pendingLine && pendingLine > 0) {
      pendingLineRef.current = null;
      const view = viewRef.current;
      const docLine = view?.state.doc.line(Math.min(pendingLine, view.state.doc.lines));
      if (docLine) {
        view.dispatch({ selection: { anchor: docLine.from }, scrollIntoView: true });
      }
    }
    return () => {
      controller?.detach();
      collabRef.current = null;
      viewRef.current?.destroy();
      viewRef.current = null;
    };
  }, [loading, activeTab, currentBlob, currentRepo, inviteToken, t]);

  const handleShareCollab = useCallback(async () => {
    const repoId = currentRepo?.id;
    if (!repoId || !activeTab) return;
    const branch = currentRepo?.default_branch || 'main';
    try {
      const res = await repositoriesApi.createCollabInvite(repoId, {
        doc_key: `${repoId}:${branch}:${activeTab}`,
        scope: 'write',
      });
      const link = `${window.location.origin}/editor/${currentRepo?.path}?file=${encodeURIComponent(activeTab)}&invite=${encodeURIComponent(res.token)}`;
      await navigator.clipboard.writeText(link);
      antdMessage.success(t('app.codeEditor.shareCollabCopied'));
    } catch {
      antdMessage.error(t('app.codeEditor.shareCollabFailed'));
    }
  }, [currentRepo, activeTab, t]);

  const collaborators = useMemo(() => {
    return (onlinePresence as PresenceUser[]).map((u) => {
      const name = u.username || u.user_id;
      const initials = getInitials(name);
      return {
        initials,
        color: getAvatarColor(initials),
        border: getAvatarColor(initials),
        title: name,
      };
    });
  }, [onlinePresence]);

  const editors = useMemo(() => {
    return (onlinePresence as PresenceUser[]).map((u) => {
      const name = u.username || u.user_id;
      const initials = getInitials(name);
      const peer = docParticipants.find((p) => p.user_id === u.user_id);
      return {
        initials,
        color: getAvatarColor(initials),
        name,
        file: activeTab || '—',
        status: 'viewing' as const,
        clientID: peer?.clientID ?? null,
        unsaved: peer?.unsaved ?? false,
        isSelf: u.user_id === currentUserId,
      };
    });
  }, [onlinePresence, activeTab, docParticipants, currentUserId]);

  // F-602 行内评论: 当前文件的线程分组/未读数与 CRUD
  const repoId = currentRepo?.id ?? null;
  const defaultBranch = currentRepo?.default_branch ?? null;
  const activeFileComments = useMemo(
    () => discussions.filter((d) => d.file_path === activeTab),
    [discussions, activeTab],
  );
  const discussionsThreads = useMemo(() => {
    const tops = activeFileComments.filter((c) => !c.parent_id);
    const children = activeFileComments.filter((c) => !!c.parent_id);
    return tops.map((top) => ({
      comment: top,
      replies: children.filter((r) => r.parent_id === top.id),
    }));
  }, [activeFileComments]);

  const unresolvedCount = useMemo(
    () => activeFileComments.filter((c) => !c.resolved).length,
    [activeFileComments],
  );

  // 当前文件切换时加载该文件的评论
  useEffect(() => {
    if (!repoId || !activeTab) return;
    const node = findFileByKey(fileTree, activeTab);
    if (!node || node.type !== 'file') return;
    let cancelled = false;
    Promise.resolve().then(() => {
      if (cancelled) return;
      setDiscussionsLoading(true);
      discussionsApi
        .list(repoId, { file_path: activeTab, branch: defaultBranch ?? undefined })
        .then((items) => { if (!cancelled) setDiscussions(items); })
        .catch(() => { if (!cancelled) setDiscussions([]); })
        .finally(() => { if (!cancelled) setDiscussionsLoading(false); });
    });
    return () => { cancelled = true; };
  }, [repoId, defaultBranch, activeTab, fileTree]);

  const submitComment = useCallback(async () => {
    const content = commentInput.trim();
    if (!content || !repoId || !activeTab) return;
    try {
      const created = await discussionsApi.create(repoId, {
        content,
        file_path: activeTab,
        line_number: cursor.line,
        branch: defaultBranch,
      });
      setDiscussions((prev) => [...prev, created]);
      setCommentInput('');
    } catch (e) {
      antdMessage.error((e as Error).message || t('app.codeEditor.commentFailed', { defaultValue: '评论失败' }));
    }
  }, [commentInput, repoId, activeTab, cursor.line, defaultBranch, t]);

  const submitReply = useCallback(async () => {
    const content = replyInput.trim();
    if (!content || !repoId || !activeTab || !replyingTo) return;
    try {
      const created = await discussionsApi.create(repoId, {
        content,
        file_path: activeTab,
        parent_id: replyingTo,
        branch: defaultBranch,
      });
      setDiscussions((prev) => [...prev, created]);
      setReplyingTo(null);
      setReplyInput('');
    } catch (e) {
      antdMessage.error((e as Error).message || t('app.codeEditor.commentFailed', { defaultValue: '评论失败' }));
    }
  }, [replyInput, repoId, activeTab, replyingTo, defaultBranch, t]);

  const toggleResolve = useCallback(async (c: DiscussionComment) => {
    if (!repoId) return;
    try {
      const updated = await discussionsApi.resolve(repoId, c.id, !c.resolved);
      setDiscussions((prev) => prev.map((x) => (x.id === updated.id ? updated : x)));
    } catch (e) {
      antdMessage.error((e as Error).message);
    }
  }, [repoId]);

  const handleDeleteDiscussion = useCallback(async (c: DiscussionComment) => {
    if (!repoId) return;
    try {
      await discussionsApi.remove(repoId, c.id);
      setDiscussions((prev) => prev.filter((x) => x.id !== c.id && x.parent_id !== c.id));
    } catch (e) {
      antdMessage.error((e as Error).message);
    }
  }, [repoId]);

  const jumpToCommentLine = useCallback((line: number | null) => {
    const view = viewRef.current;
    if (!view || !line) return;
    const docLine = view.state.doc.line(Math.min(line, view.state.doc.lines));
    view.dispatch({ selection: { anchor: docLine.from }, scrollIntoView: true });
    view.focus();
  }, []);

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

  // F-602 行内评论: 权限（作者或仓库负责人可解决/删除）
  const isCommentAdmin =
    !!currentUserId &&
    !!currentRepo &&
    (currentRepo.owner_id === currentUserId ||
      members.some((m) => m.user_id === currentUserId && m.role === 'admin'));
  const canManageComment = (c: DiscussionComment) =>
    isCommentAdmin || (!!currentUserId && c.author_id === currentUserId);

  return (
    <Layout style={{ height: '100%', background: 'transparent' }}>
      <style>{`
        .cm-file-tree-row:hover .cm-tree-delete-btn {
          opacity: 1 !important;
        }
      `}</style>
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
          <Tooltip title={t('app.codeEditor.newFile', { defaultValue: '新建文件' })}>
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
              onClick={() => setNewFileModalOpen(true)}
            >
              <PlusOutlined style={{ fontSize: 14 }} />
            </button>
          </Tooltip>
        </div>
        <div style={{ flex: 1, overflow: 'auto', padding: '4px 0', position: 'relative' }}>
          {fileTree.map((node) => (
            <TreeNodeView
              key={node.key}
              node={node}
              selectedKey={selectedTreeKey}
              onSelect={handleSelectFile}
              onDelete={setDeleteTarget}
              onMove={handleMoveRequest}
              onDirPin={handleTreePin}
            />
          ))}
        </div>
      </Sider>

      {(() => {
        const displayChain = pinnedChain;
        if (!displayChain.length) return null;
        const activeKeys = new Set(displayChain.slice(1).map((p) => p.key));
        return (
          <>
            {displayChain.map((pos, i) => {
              const node = findFileByKey(fileTree, pos.key);
              if (!node || node.type !== 'folder' || !node.children?.length) return null;
              return (
                <div
                  key={pos.key}
                  className="floating-tree-anchor"
                  style={{ position: 'fixed', top: pos.top, left: pos.left, zIndex: 200 }}
                >
                  <FloatingTreePanel
                    node={node}
                    level={i}
                    activeKeys={activeKeys}
                    onItemClick={handlePanelPin}
                    onSelectFile={handleSelectFile}
                    onDelete={setDeleteTarget}
                    onMove={handleMoveRequest}
                  />
                </div>
              );
            })}
          </>
        );
      })()}

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
          <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', padding: '0 8px', gap: 6, flexShrink: 0 }}>
            {isDirty && (
              <span
                title={t('app.codeEditor.unsaved', { defaultValue: '有未保存的更改' })}
                style={{ width: 8, height: 8, borderRadius: '50%', background: yellow, flexShrink: 0 }}
              />
            )}
            <Button
              size="small"
              type={isDirty ? 'primary' : 'default'}
              icon={<SaveOutlined style={{ fontSize: 12 }} />}
              loading={saving}
              disabled={!isDirty || saving}
              onClick={() => setSaveModalOpen(true)}
              style={{ fontSize: 12 }}
            >
              {t('app.codeEditor.commit', { defaultValue: 'Commit' })}
            </Button>
          </div>
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
          <span
            style={{ cursor: 'pointer' }}
            onClick={handleBreadcrumbRoot}
            title={currentRepo?.name || repo}
          >
            {currentRepo?.name || repo}
          </span>
          {breadcrumb.map((part, idx) => {
            const isFileSegment = idx === breadcrumb.length - 1;
            const partialKey = breadcrumb.slice(0, idx + 1).join('/');
            return (
              <span key={idx} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <span>/</span>
                <span
                  style={
                    isFileSegment
                      ? { color: textPrimary, maxWidth: 260, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }
                      : { cursor: 'pointer' }
                  }
                  onClick={
                    isFileSegment
                      ? undefined
                      : (e) => handleBreadcrumbDir(idx, partialKey, e.currentTarget)
                  }
                >
                  {part}
                </span>
              </span>
            );
          })}
          {activeNode?.fileType === 'md' && (
            <div style={{ marginLeft: 'auto', display: 'flex', gap: 4 }}>
              <Button
                size="small"
                type={previewMode ? 'text' : 'primary'}
                icon={<EditOutlined style={{ fontSize: 11 }} />}
                onClick={() => setPreviewTab(null)}
                style={{ fontSize: 11, height: 22, padding: '0 8px' }}
              >
                {t('app.codeEditor.edit', { defaultValue: 'Edit' })}
              </Button>
              <Button
                size="small"
                type={previewMode ? 'primary' : 'text'}
                icon={<EyeOutlined style={{ fontSize: 11 }} />}
                onClick={() => {
                  // 事件上下文中读取编辑器内容, 预览期间编辑器隐藏, 内容不会变化
                  setPreviewContent(viewRef.current?.state.doc.toString() ?? currentBlob?.content ?? '');
                  setPreviewTab(activeTab);
                }}
                style={{ fontSize: 11, height: 22, padding: '0 8px' }}
              >
                {t('app.codeEditor.preview', { defaultValue: 'Preview' })}
              </Button>
            </div>
          )}
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
                background: onlinePresence.length > 0 ? green : '#6e7681',
                boxShadow: onlinePresence.length > 0 ? `0 0 6px ${green}` : 'none',
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
            <strong style={{ color: textSecondary }}>{onlinePresence.length}</strong> {t('app.codeEditor.editorsOnline')}
          </div>
          <div style={{ color: textTertiary, fontSize: 11, display: 'flex', alignItems: 'center', gap: 5, marginLeft: 12 }}>
            <span
              style={{
                width: 7,
                height: 7,
                borderRadius: '50%',
                background: collabStatus === 'connected' ? green : collabStatus === 'connecting' ? yellow : '#6e7681',
                boxShadow: collabStatus === 'connected' ? `0 0 6px ${green}` : 'none',
              }}
            />
            {t('app.codeEditor.collab')}
            {docParticipants.length > 0 && (
              <span style={{ color: textSecondary }}>
                · {docParticipants.length} {t('app.codeEditor.peersInFile')}
              </span>
            )}
          </div>
          {canWriteCollab && activeTab && collabStatus === 'connected' && (
            <Button
              size="small"
              type="text"
              icon={<UsergroupAddOutlined style={{ fontSize: 12 }} />}
              onClick={() => collabRef.current?.setSpotlight(!followState.spotlightOn)}
              title={t('app.codeEditor.spotlightHint', { defaultValue: '邀请协作者跟随你的视口' })}
              style={{ color: followState.spotlightOn ? blueLight : textSecondary, fontSize: 11, marginLeft: 8, height: 22, padding: '0 6px' }}
            >
              {followState.spotlightOn ? t('app.codeEditor.spotlightStop') : t('app.codeEditor.spotlightStart')}
            </Button>
          )}
          {followState.following && (
            <Button
              size="small"
              type="text"
              icon={<StopOutlined style={{ fontSize: 12 }} />}
              onClick={() => collabRef.current?.follow(null)}
              style={{ color: blueLight, fontSize: 11, marginLeft: 4, height: 22, padding: '0 6px' }}
            >
              {t('app.codeEditor.following', { name: followState.followingName ?? '…' })}
            </Button>
          )}
          {isRepoMember && activeTab && (
            <Button
              size="small"
              type="text"
              icon={<ShareAltOutlined style={{ fontSize: 12 }} />}
              onClick={handleShareCollab}
              style={{ color: textSecondary, fontSize: 11, marginLeft: 8, height: 22, padding: '0 6px' }}
            >
              {t('app.codeEditor.shareCollab')}
            </Button>
          )}
        </div>

        {/* Code Editor */}
        <Content style={{ display: 'flex', overflow: 'hidden', background: bgPrimary, flex: 1 }}>
          {previewMode && activeNode?.fileType === 'md' && (
            <div style={{ flex: 1, overflow: 'auto', padding: '16px 24px' }}>
              <Markdown>{previewContent || (currentBlob?.content ?? '')}</Markdown>
            </div>
          )}
          {/* 预览时仅隐藏编辑器, 保持 CodeMirror DOM 挂载以免丢失文档状态 */}
          <div ref={editorRef} style={{ flex: 1, overflow: 'auto', display: previewMode ? 'none' : undefined }} />
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
              { key: 'discussions', icon: <MessageOutlined style={{ fontSize: 12 }} />, label: t('app.codeEditor.discussions'), count: unresolvedCount },
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
            {panelTab === 'discussions' && (
              <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                <div style={{ padding: '8px 16px', borderBottom: `1px solid ${borderColor}`, display: 'flex', gap: 8, alignItems: 'flex-end' }}>
                  <Input.TextArea
                    autoSize={{ minRows: 1, maxRows: 3 }}
                    value={commentInput}
                    onChange={(e) => setCommentInput(e.target.value)}
                    placeholder={
                      activeNode?.type === 'file'
                        ? t('app.codeEditor.commentPlaceholder', { line: cursor.line, defaultValue: `评论 L${cursor.line}...` })
                        : t('app.codeEditor.commentNoFile', { defaultValue: '请先打开文件再评论' })
                    }
                    disabled={activeNode?.type !== 'file'}
                    style={{ flex: 1, background: bgTertiary, borderColor: '#30363d', color: textPrimary }}
                  />
                  <Button
                    type="primary"
                    size="small"
                    icon={<MessageOutlined style={{ fontSize: 12 }} />}
                    disabled={activeNode?.type !== 'file' || !commentInput.trim()}
                    onClick={submitComment}
                    style={{ background: bluePrimary, borderColor: bluePrimary }}
                  >
                    {t('app.codeEditor.commentSend', { defaultValue: '评论' })}
                  </Button>
                </div>
                <div style={{ flex: 1, overflow: 'auto', padding: '6px 0' }}>
                  {discussionsLoading && (
                    <div style={{ padding: '12px 16px', fontSize: 12, color: textTertiary }}>
                      {t('app.codeEditor.commentsLoading', { defaultValue: '加载中...' })}
                    </div>
                  )}
                  {!discussionsLoading && discussionsThreads.length === 0 && (
                    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: textTertiary, fontSize: 12, gap: 6, padding: 16 }}>
                      <MessageOutlined style={{ fontSize: 22, opacity: 0.5 }} />
                      <span>{t('app.codeEditor.noDiscussions', { defaultValue: '暂无代码讨论' })}</span>
                      <span style={{ fontSize: 11 }}>{t('app.codeEditor.noDiscussionsHint', { defaultValue: '在下方输入框评论当前文件与行号' })}</span>
                    </div>
                  )}
                  {!discussionsLoading && discussionsThreads.map(({ comment, replies }) => (
                    <div key={comment.id}>
                      <DiscussionRow
                        comment={comment}
                        canResolve={canManageComment(comment)}
                        canDelete={canManageComment(comment)}
                        replying={replyingTo === comment.id}
                        replyValue={replyInput}
                        onReply={() => { setReplyingTo(replyingTo === comment.id ? null : comment.id); setReplyInput(''); }}
                        onReplyCancel={() => { setReplyingTo(null); setReplyInput(''); }}
                        onReplyChange={setReplyInput}
                        onReplySubmit={submitReply}
                        onToggleResolve={() => toggleResolve(comment)}
                        onDelete={() => handleDeleteDiscussion(comment)}
                        onJump={() => jumpToCommentLine(comment.line_number)}
                      />
                      {replies.map((r) => (
                        <DiscussionRow
                          key={r.id}
                          comment={r}
                          isReply
                          canResolve={canManageComment(r)}
                          canDelete={canManageComment(r)}
                          replying={replyingTo === r.id}
                          replyValue={replyInput}
                          onReply={() => { setReplyingTo(replyingTo === r.id ? null : r.id); setReplyInput(''); }}
                          onReplyCancel={() => { setReplyingTo(null); setReplyInput(''); }}
                          onReplyChange={setReplyInput}
                          onReplySubmit={submitReply}
                          onToggleResolve={() => toggleResolve(r)}
                          onDelete={() => handleDeleteDiscussion(r)}
                          onJump={() => jumpToCommentLine(r.line_number)}
                        />
                      ))}
                    </div>
                  ))}
                </div>
              </div>
            )}
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
                    {!ed.isSelf && ed.clientID && (
                      <Button
                        size="small"
                        type="text"
                        icon={followState.following === ed.clientID ? <StopOutlined style={{ fontSize: 12 }} /> : <AimOutlined style={{ fontSize: 12 }} />}
                        onClick={() =>
                          collabRef.current?.follow(
                            followState.following === ed.clientID ? null : ed.clientID,
                          )
                        }
                        style={{
                          color: followState.following === ed.clientID ? blueLight : textSecondary,
                          fontSize: 11,
                          height: 22,
                          padding: '0 6px',
                        }}
                      >
                        {followState.following === ed.clientID
                          ? t('app.codeEditor.followStop')
                          : t('app.codeEditor.follow')}
                      </Button>
                    )}
                    {ed.isSelf && followState.followers.length > 0 && (
                      <span style={{ fontSize: 10, color: blueLight, display: 'flex', alignItems: 'center', gap: 4 }}>
                        <AimOutlined style={{ fontSize: 11 }} />
                        {t('app.codeEditor.followerCount', { count: followState.followers.length })}
                      </span>
                    )}
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
                    {ed.clientID && (
                      <div style={{ fontSize: 10, display: 'flex', alignItems: 'center', gap: 4 }}>
                        <span
                          style={{
                            width: 6,
                            height: 6,
                            borderRadius: '50%',
                            background: ed.unsaved ? '#d29922' : green,
                          }}
                        />
                        {ed.unsaved
                          ? t('app.codeEditor.unsavedBadge', { defaultValue: '未保存' })
                          : t('app.codeEditor.savedBadge', { defaultValue: '已提交' })}
                      </div>
                    )}
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
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: onlinePresence.length > 0 ? green : '#6e7681', display: 'inline-block', marginRight: 2 }} />
            {t('app.codeEditor.online')}
          </div>
          <div style={{ marginLeft: 'auto', display: 'flex', gap: 16 }}>
            <span>{t('app.codeEditor.lnCol', { line: cursor.line, col: cursor.col })}</span>
            <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}><TeamOutlined style={{ fontSize: 12 }} /> {onlinePresence.length} online</span>
            {followState.following && (
              <span style={{ display: 'flex', alignItems: 'center', gap: 4, color: '#58a6ff' }}>
                <AimOutlined style={{ fontSize: 12 }} />
                {t('app.codeEditor.following', { name: followState.followingName ?? '…' })}
                <StopOutlined style={{ cursor: 'pointer' }} onClick={() => collabRef.current?.follow(null)} />
              </span>
            )}
            {collabStatus === 'connected' && !collabPending && (
              <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <span style={{ width: 6, height: 6, borderRadius: '50%', background: green, display: 'inline-block' }} />
                {t('app.codeEditor.collabSynced', { defaultValue: '会话已同步' })}
                {collabVersion != null && (
                  <span style={{ fontFamily: 'var(--mono)', fontSize: 10.5 }}>{`v${collabVersion}`}</span>
                )}
              </span>
            )}
            {collabStatus === 'connected' && collabPending && (
              <span style={{ color: '#e3b341' }}>{t('app.codeEditor.collabSyncing', { defaultValue: '会话同步中' })}</span>
            )}
            {lastCommitSha && (
              <span>{t('app.codeEditor.gitCommitted', { sha: lastCommitSha, defaultValue: `Git 已提交 ${lastCommitSha}` })}</span>
            )}
            {isDirty && <span style={{ color: '#e3b341' }}>{t('app.codeEditor.unsavedShort', { defaultValue: '● 未保存' })}</span>}
            <span>{activeNode?.fileType ? activeNode.fileType.toUpperCase() : 'Text'}</span>
            <span>UTF-8</span>
          </div>
        </div>
      </Layout>

      {/* 提交保存弹窗 */}
      <Modal
        title={t('app.codeEditor.commitTitle', { tab: activeTab || '' })}
        open={saveModalOpen}
        onCancel={() => setSaveModalOpen(false)}
        onOk={() => {
          performSave(commitMessage.trim() || undefined).then(() => {
            setSaveModalOpen(false);
            setCommitMessage('');
          });
        }}
        okText={t('app.codeEditor.commitOk', { branch: currentRepo?.default_branch || 'main' })}
        confirmLoading={saving}
        okButtonProps={{ style: { background: bluePrimary } }}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <span style={{ color: textSecondary, fontSize: 13 }}>
            {t('app.codeEditor.commitHint', { defaultValue: '更改将作为一次 Git 提交推送到默认分支' })}
          </span>
          <Input
            value={commitMessage}
            onChange={(e) => setCommitMessage(e.target.value)}
            placeholder={`Update ${activeTab || 'file'}`}
            onPressEnter={() => {
              performSave(commitMessage.trim() || undefined).then(() => {
                setSaveModalOpen(false);
                setCommitMessage('');
              });
            }}
          />
        </div>
      </Modal>

      {/* 删除文件弹窗 */}
      <Modal
        title={t('app.codeEditor.deleteFileTitle', { defaultValue: '删除文件' })}
        open={!!deleteTarget}
        onCancel={() => setDeleteTarget(null)}
        onOk={handleDeleteFile}
        okText={t('app.codeEditor.delete', { defaultValue: '删除' })}
        okButtonProps={{ danger: true, style: { background: '#f85149', borderColor: '#f85149' } }}
        confirmLoading={deleting}
      >
        <div style={{ color: textSecondary, fontSize: 13 }}>
          {deleteTarget && t('app.codeEditor.deleteFileConfirm', { defaultValue: `确定要删除 ${deleteTarget.key} 吗？此操作将创建一次删除该文件的 Git 提交。` })}
        </div>
      </Modal>

      {/* 移动/重命名文件弹窗 */}
      <Modal
        title={t('app.codeEditor.moveFileTitle', { defaultValue: '移动文件' })}
        open={!!moveTarget}
        onCancel={() => { setMoveTarget(null); setMoveToPath(''); setMoveMessage(''); }}
        onOk={handleMoveFile}
        okText={t('app.codeEditor.moveFile', { defaultValue: '移动' })}
        confirmLoading={moving}
        okButtonProps={{ style: { background: bluePrimary } }}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <Input
            value={moveTarget?.key ?? ''}
            disabled
            style={{ background: bgTertiary, borderColor: '#30363d', color: textTertiary }}
          />
          <div style={{ color: textSecondary, fontSize: 11 }}>⟶</div>
          <Input
            autoFocus
            value={moveToPath}
            onChange={(e) => setMoveToPath(e.target.value)}
            placeholder={t('app.codeEditor.movePathPlaceholder', { defaultValue: '目标路径（可含目录），如 src/utils.ts' })}
            onPressEnter={handleMoveFile}
          />
          <Input
            value={moveMessage}
            onChange={(e) => setMoveMessage(e.target.value)}
            placeholder={t('app.codeEditor.moveMessagePlaceholder', { defaultValue: '提交信息' })}
            onPressEnter={handleMoveFile}
          />
        </div>
      </Modal>

      {/* 新建文件弹窗 */}
      <Modal
        title={t('app.codeEditor.newFileTitle', { defaultValue: '新建文件' })}
        open={newFileModalOpen}
        onCancel={() => { setNewFileModalOpen(false); setNewFileName(''); }}
        onOk={handleCreateFile}
        okText={t('app.codeEditor.create', { defaultValue: '创建' })}
        confirmLoading={newFileCreating}
        okButtonProps={{ style: { background: bluePrimary } }}
      >
        <Input
          autoFocus
          value={newFileName}
          onChange={(e) => setNewFileName(e.target.value)}
          placeholder={t('app.codeEditor.newFilePlaceholder', { defaultValue: '例如 src/utils/helpers.ts 或 README.md' })}
          onPressEnter={handleCreateFile}
        />
      </Modal>
    </Layout>
  );
}
