import { useState, useEffect, useRef, useMemo, useCallback, Fragment } from 'react';
import { Layout, Input, Button, Avatar, Tooltip, Popover, Drawer, Dropdown, Switch, message as antdMessage } from 'antd';
import type { MenuProps } from 'antd';
import {
  NumberOutlined,
  LockOutlined,
  SendOutlined,
  PaperClipOutlined,
  SmileOutlined,
  BoldOutlined,
  ItalicOutlined,
  CodeOutlined,
  FileAddOutlined,
  SearchOutlined,
  EyeOutlined,
  MoreOutlined,
  DeleteOutlined,
  MessageOutlined,
  LoadingOutlined,
  BellOutlined,
  TeamOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import ChatSkeleton from '../../components/skeleton/ChatSkeleton';
import Markdown from '../../components/Markdown';
import RepoResourcePicker, { type RepoResourcePick } from '../../components/chat/RepoResourcePicker';
import { useRepositoriesStore } from '../../stores/repositories';
import { useAuthStore } from '../../stores/auth';
import {
  chatApi,
  dmApi,
  type ChatMessage,
  type RoomMember,
  type RealtimeRoom,
  type DMSession,
  type MessageSearchHit,
} from '../../api/chat';
import { chatSocket, type ChatSocketStatus } from '../../api/chatSocket';
import type { Repository } from '../../api/repositories';

const { Sider, Content } = Layout;

const borderColor = '#21262d';
const hoverBg = '#1c2333';
const activeBg = '#1a2332';
const textSecondary = '#8b949e';
const textPrimary = '#e6edf3';
const textTertiary = '#6e7681';
const bluePrimary = '#1f6feb';
const bgPrimary = '#0d1117';
const bgSecondary = '#161b22';
const bgTertiary = '#1c2128';
const green = '#3fb950';
const yellow = '#d29922';

const avatarColors = ['#1f6feb', '#3fb950', '#58a6ff', '#bc8cff', '#d29922', '#f85149', '#f0883e', '#7956d9'];

const emojiPalette = [
  '😀', '😂', '🤣', '😊', '😍', '🤔', '😎', '🥳',
  '😢', '😡', '👍', '👎', '👏', '🙌', '🤝', '💪',
  '🔥', '⭐', '🎉', '🚀', '✅', '❌', '⚠️', '💡',
  '🐛', '📌', '👀', '❤️', '🙏', '😅', '🫡', '🤖',
];

interface Channel {
  id: string;
  name: string;
  type: 'public' | 'private';
  unread: number;
}

interface Message {
  id: string;
  senderId: string;
  author: string;
  initials: string;
  color: string;
  time: string;
  createdAt?: string;
  text: string;
  reactions?: { emoji: string; count: number; active: boolean }[];
}

interface Member {
  name: string;
  role: string;
  status: 'online' | 'away' | 'offline';
  initials: string;
  color: string;
  user_id: string;
  is_muted: boolean;
}

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

function formatMessageTime(dateStr: string | null): string {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  if (Number.isNaN(d.getTime())) return '';
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function dayDiffFromToday(dateStr: string): number {
  const d = new Date(dateStr);
  if (Number.isNaN(d.getTime())) return NaN;
  const day = new Date(d);
  day.setHours(0, 0, 0, 0);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return Math.round((day.getTime() - today.getTime()) / 86400000);
}

function statusColor(status: string) {
  if (status === 'online') return green;
  if (status === 'away') return yellow;
  return '#6e7681';
}

function mapChatMessage(msg: ChatMessage): Message {
  const author = msg.sender_username || 'unknown';
  const initials = getInitials(author);
  return {
    id: msg.id,
    senderId: msg.sender_id,
    author,
    initials,
    color: getAvatarColor(initials),
    time: formatMessageTime(msg.created_at),
    createdAt: msg.created_at ?? undefined,
    text: msg.content,
    reactions: msg.reactions,
  };
}

function StatusDot({ status, size = 8 }: { status: string; size?: number }) {
  return (
    <span
      style={{
        width: size,
        height: size,
        borderRadius: '50%',
        background: statusColor(status),
        border: `2px solid ${bgSecondary}`,
        flexShrink: 0,
      }}
    />
  );
}

export default function ChatPage() {
  const [loading, setLoading] = useState(true);
  const [activeChannel, setActiveChannel] = useState<string | null>(null);
  const [activeDmId, setActiveDmId] = useState<string | null>(null);
  const [activeKind, setActiveKind] = useState<'channel' | 'dm' | null>(null);
  const [activeRepoId, setActiveRepoId] = useState<string | null>(null);
  const [resourcePicker, setResourcePicker] = useState<'file' | 'code' | null>(null);
  const [room, setRoom] = useState<RealtimeRoom | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [members, setMembers] = useState<Member[]>([]);
  const [dms, setDms] = useState<DMSession[]>([]);
  const [dmLoaded, setDmLoaded] = useState(false);
  const [searchQ, setSearchQ] = useState('');
  const [searchResults, setSearchResults] = useState<MessageSearchHit[]>([]);
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchScope, setSearchScope] = useState<'all' | 'room'>('all');
  const [error, setError] = useState<string | null>(null);
  const [input, setInput] = useState('');
  const [sendError, setSendError] = useState<string | null>(null);
  const [wsStatus, setWsStatus] = useState<ChatSocketStatus>('disconnected');
  const [channelsLoaded, setChannelsLoaded] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [emojiOpen, setEmojiOpen] = useState(false);
  const [onlineUserIds, setOnlineUserIds] = useState<Set<string>>(new Set());
  const [unreadByRepo, setUnreadByRepo] = useState<Record<string, number>>({});
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [myMuted, setMyMuted] = useState(false);
  const [membersOpen, setMembersOpen] = useState(true);
  const { t } = useTranslation();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const activeRoomIdRef = useRef<string | null>(null);
  const joinedRoomIdRef = useRef<string | null>(null);
  const textAreaRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const searchBoxWrapRef = useRef<HTMLDivElement>(null);
  const searchDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const { user } = useAuthStore();
  const { repositories, fetchRepositoriesByUser } = useRepositoriesStore();

  const channels: Channel[] = useMemo(() =>
    repositories.map((r: Repository) => ({
      id: r.id,
      name: r.name,
      type: r.is_public ? 'public' : 'private',
      unread: unreadByRepo[r.id] ?? 0,
    })),
    [repositories, unreadByRepo]
  );

  // 当前频道所属仓库（频道即仓库；私聊无仓库）
  const activeRepo = useMemo(
    () => repositories.find((r) => r.id === activeRepoId) ?? null,
    [repositories, activeRepoId],
  );

  const refreshUnread = useCallback(async () => {
    try {
      const list = await chatApi.getUnreadCounts();
      const map: Record<string, number> = {};
      for (const r of list) map[r.repository_id] = r.unread_count;
      setUnreadByRepo(map);
    } catch {
      // 未读刷新失败不影响主流程
    }
  }, []);

  // WebSocket: 连接、房间订阅与实时消息接收
  const applyReaction = useCallback((updated: ChatMessage) => {
    // 无论消息是否在当前频道, 都尝试定位更新 (ack 与广播最终一致)
    setMessages((prev) => prev.map((m) => m.id === updated.id ? mapChatMessage(updated) : m));
  }, []);

  useEffect(() => {
    chatSocket.setHandlers({
      onStatusChange: setWsStatus,
      onAck: (msg) => {
        if (msg.room_id === activeRoomIdRef.current) {
          setMessages((prev) => [...prev, mapChatMessage(msg)]);
          setSendError(null);
        }
      },
      onChatMessage: (msg) => {
        if (msg.room_id === activeRoomIdRef.current) {
          setMessages((prev) => [...prev, mapChatMessage(msg)]);
          // 正在观看的频道收到新消息立即保持已读水位
          chatApi.markRead(msg.room_id).catch(() => {});
        } else {
          refreshUnread();
          dmApi.listDms().then(setDms).catch(() => {});
        }
      },
      onReactionAck: (msg) => {
        if (msg.room_id === activeRoomIdRef.current) applyReaction(msg);
      },
      onReaction: (msg) => {
        if (msg.room_id === activeRoomIdRef.current) applyReaction(msg);
      },
      onPresence: (roomId, users) => {
        if (roomId === activeRoomIdRef.current) {
          setOnlineUserIds(new Set(users.map((u) => u.user_id)));
        }
      },
      onPresenceJoin: (roomId, user) => {
        if (roomId !== activeRoomIdRef.current) return;
        setOnlineUserIds((prev) => {
          if (prev.has(user.user_id)) return prev;
          const next = new Set(prev);
          next.add(user.user_id);
          return next;
        });
      },
      onPresenceLeave: (roomId, user) => {
        if (roomId !== activeRoomIdRef.current) return;
        setOnlineUserIds((prev) => {
          if (!prev.has(user.user_id)) return prev;
          const next = new Set(prev);
          next.delete(user.user_id);
          return next;
        });
      },
      onError: (err, originalType) => {
        if (originalType === 'chat_message') setSendError(err);
      },
    });
    chatSocket.start();
    Promise.resolve().then(() => refreshUnread());
    return () => chatSocket.stop();
  }, [refreshUnread, applyReaction]);

  // Fetch user repositories on mount
  useEffect(() => {
    if (user?.id) {
      fetchRepositoriesByUser(user.id).finally(() => setChannelsLoaded(true));
    } else {
      // 微任务延迟, 避免在 effect 同步体中触发级联渲染
      Promise.resolve().then(() => setChannelsLoaded(true));
    }
  }, [user?.id, fetchRepositoriesByUser]);

  // Fetch DM sessions on mount
  useEffect(() => {
    let disposed = false;
    dmApi.listDms()
      .then((items) => { if (!disposed) setDms(items); })
      .catch(() => {})
      .finally(() => { if (!disposed) setDmLoaded(true); });
    return () => { disposed = true; };
  }, []);

  // 绑定房间: 加入/离开 WS 房间、拉取在线成员、标记已读、加载消息与成员
  const bindRoom = useCallback(async (roomId: string) => {
    if (joinedRoomIdRef.current !== roomId) {
      if (joinedRoomIdRef.current) {
        chatSocket.leaveRoom(joinedRoomIdRef.current);
      }
      chatSocket.joinRoom(roomId);
      joinedRoomIdRef.current = roomId;
    }

    setOnlineUserIds(new Set());
    chatSocket.requestPresenceList(roomId);
    chatApi.markRead(roomId).catch(() => {});

    const [messagesRes, membersRes] = await Promise.all([
      chatApi.getRoomMessages(roomId, { limit: 50 }),
      chatApi.getRoomMembers(roomId),
    ]);

    setMessages(messagesRes.messages.map(mapChatMessage).reverse());
    setMembers(membersRes.map((m: RoomMember) => {
      const name = m.username || m.user_id;
      const initials = getInitials(name);
      return {
        user_id: m.user_id,
        name,
        role: m.role === 'admin' ? 'Admin' : 'Member',
        status: 'offline',
        initials,
        color: getAvatarColor(initials),
        is_muted: m.is_muted,
      };
    }));
    const self = membersRes.find((m) => m.user_id === user?.id);
    setMyMuted(!!self?.is_muted);
  }, [user]);

  // Load room, messages and members when channel changes
  const loadChannel = useCallback(async (repoId: string, options?: { selectOnSuccess?: boolean }) => {
    setLoading(true);
    setError(null);
    try {
      const roomData = await chatApi.getRepositoryRoom(repoId);
      setRoom(roomData);
      setActiveKind('channel');
      setActiveDmId(null);
      setActiveRepoId(repoId);
      activeRoomIdRef.current = roomData.id;
      setUnreadByRepo((prev) => ({ ...prev, [repoId]: 0 }));
      await bindRoom(roomData.id);
      if (options?.selectOnSuccess) {
        setActiveChannel(repoId);
      }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [bindRoom]);

  // Load a DM session (复用与频道相同的房间消息/成员接口)
  const loadDm = useCallback(async (session: DMSession) => {
    setLoading(true);
    setError(null);
    try {
      setRoom({
        id: session.room_id,
        repository_id: null,
        name: session.room_name,
        topic: null,
        room_type: session.room_type,
        is_active: true,
        created_at: session.created_at,
      });
      setActiveKind('dm');
      setActiveDmId(session.room_id);
      setActiveRepoId(null);
      setActiveChannel(null);
      activeRoomIdRef.current = session.room_id;
      setDms((prev) => prev.map((d) => d.room_id === session.room_id ? { ...d, unread_count: 0 } : d));
      await bindRoom(session.room_id);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [bindRoom]);

  // Auto-select first channel
  useEffect(() => {
    if (!activeChannel && !activeDmId && channels.length > 0) {
      const first = channels[0];
      // 通过微任务延迟加载，避免在 effect 同步体中触发状态更新
      Promise.resolve().then(() => {
        loadChannel(first.id, { selectOnSuccess: true });
      });
    }
  }, [channels, activeChannel, activeDmId, loadChannel]);

  const handleChannelClick = useCallback((channelId: string) => {
    if (channelId === activeChannel) return;
    setActiveChannel(channelId);
    setActiveDmId(null);
    loadChannel(channelId);
  }, [activeChannel, loadChannel]);

  const handleDmClick = useCallback((session: DMSession) => {
    if (activeDmId === session.room_id) return;
    loadDm(session);
  }, [activeDmId, loadDm]);

  const handleMemberClick = useCallback(async (m: Member) => {
    if (!user || m.user_id === user.id) return;
    const existing = dms.find((d) => d.peer_user_id === m.user_id);
    if (existing) {
      handleDmClick(existing);
      return;
    }
    try {
      const created = await dmApi.createDm(m.user_id);
      const session: DMSession = {
        room_id: created.id,
        room_name: created.name || m.name,
        room_type: created.room_type,
        peer_user_id: m.user_id,
        peer_username: m.name,
        created_at: created.created_at,
        unread_count: 0,
      };
      setDms((prev) => [session, ...prev.filter((d) => d.room_id !== session.room_id)]);
      loadDm(session);
      // 以服务端为准刷新列表顺序与名称
      dmApi.listDms().then(setDms).catch(() => {});
    } catch (e) {
      antdMessage.error((e as Error).message || t('app.teamChat.newDmFailed', { defaultValue: '发起私聊失败' }));
    }
  }, [user, dms, handleDmClick, loadDm, t]);

  // 静音/取消静音当前会话: 后端排除该会话未读累计
  const toggleMute = useCallback(async () => {
    if (!room) return;
    const next = !myMuted;
    try {
      const res = await chatApi.setMemberMuted(room.id, next);
      setMyMuted(res.is_muted);
      refreshUnread();
      if (res.is_muted) {
        antdMessage.success(t('app.teamChat.roomMuted', { defaultValue: '已静音该会话，不再累计未读' }));
      } else {
        antdMessage.success(t('app.teamChat.roomUnmuted', { defaultValue: '已取消静音' }));
      }
    } catch (e) {
      antdMessage.error((e as Error).message || t('app.teamChat.muteFailed', { defaultValue: '设置静音失败' }));
    }
  }, [room, myMuted, refreshUnread, t]);

  // 消息检索 (F-603): 跨会话 GET /api/v1/messages/search；本会话 GET /rooms/{id}/messages?q=
  const doSearch = useCallback((q: string, scopeOverride?: 'all' | 'room') => {
    if (searchDebounceRef.current) {
      clearTimeout(searchDebounceRef.current);
      searchDebounceRef.current = null;
    }
    const trimmed = q.trim();
    if (!trimmed) {
      setSearchResults([]);
      setSearchOpen(false);
      setSearchLoading(false);
      return;
    }
    const scope = scopeOverride ?? searchScope;
    searchDebounceRef.current = setTimeout(async () => {
      searchDebounceRef.current = null;
      setSearchLoading(true);
      try {
        if (scope === 'room' && room) {
          const res = await chatApi.searchRoomMessages(room.id, trimmed, 20);
          setSearchResults(res.messages.map((m) => ({
            id: m.id,
            room_id: m.room_id,
            room_name: room.name,
            room_type: room.room_type,
            repository_id: room.repository_id,
            sender_id: m.sender_id,
            sender_username: m.sender_username,
            message_type: m.message_type,
            content: m.content,
            reply_to: m.reply_to,
            created_at: m.created_at,
            reactions: m.reactions,
          })));
        } else {
          const res = await chatApi.searchMessages(trimmed, 20);
          setSearchResults(res.messages);
        }
        setSearchOpen(true);
      } catch {
        setSearchResults([]);
        setSearchOpen(true);
      } finally {
        setSearchLoading(false);
      }
    }, 300);
  }, [room, searchScope]);

  const handleSearchChange = useCallback((value: string) => {
    setSearchQ(value);
    doSearch(value);
  }, [doSearch]);

  const focusSearch = useCallback(() => {
    searchBoxWrapRef.current?.querySelector('input')?.focus();
  }, []);

  const openSearchHit = useCallback((hit: MessageSearchHit) => {
    setSearchOpen(false);
    setSearchQ('');
    setSearchResults([]);
    if (hit.room_type === 'repository' && hit.repository_id) {
      loadChannel(hit.repository_id, { selectOnSuccess: true });
    } else {
      loadDm({
        room_id: hit.room_id,
        room_name: hit.room_name,
        room_type: hit.room_type,
        peer_user_id: hit.sender_id,
        peer_username: hit.sender_username,
        created_at: hit.created_at,
        unread_count: 0,
      });
    }
  }, [loadChannel, loadDm]);

  useEffect(() => () => {
    if (searchDebounceRef.current) clearTimeout(searchDebounceRef.current);
  }, []);

  const handleSend = useCallback(() => {
    const content = input.trim();
    if (!content || !room) return;
    if (wsStatus !== 'connected') return;
    chatSocket.sendChatMessage(room.id, content);
    setInput('');
    setSendError(null);
  }, [input, room, wsStatus]);

  const handleDeleteMessage = useCallback(async (msg: Message) => {
    if (!room) return;
    if (msg.senderId && user && msg.senderId !== user.id) return;
    try {
      await chatApi.deleteMessage(room.id, msg.id);
      setMessages((prev) => prev.filter((m) => m.id !== msg.id));
    } catch (e) {
      antdMessage.error((e as Error).message || 'Failed to delete message');
    }
  }, [room, user]);

  const handleReaction = useCallback(async (msg: Message, emoji: string) => {
    if (!room) return;
    if (wsStatus !== 'connected') return;
    const existing = msg.reactions?.find((r) => r.emoji === emoji);
    const adding = !existing?.active;
    chatSocket.sendReaction(room.id, msg.id, emoji, adding);
  }, [room, wsStatus]);

  const handleReactionPicker = useCallback(async (msg: Message, emoji: string) => {
    if (!room) return;
    try {
      const updated = await chatApi.addReaction(room.id, msg.id, emoji);
      applyReaction(updated);
    } catch (e) {
      antdMessage.error((e as Error).message || 'Failed to add reaction');
    }
  }, [room, applyReaction]);

  const handleInputChange = (value: string) => {
    setInput(value);
    if (sendError) setSendError(null);
  };

  const getTextAreaEl = (): HTMLTextAreaElement | null =>
    textAreaRef.current?.querySelector('textarea') ?? null;

  const insertAtCursor = useCallback((text: string, wrap?: string) => {
    const el = getTextAreaEl();
    const start = el?.selectionStart ?? input.length;
    const end = el?.selectionEnd ?? input.length;
    const selected = input.slice(start, end);
    const inserted = wrap != null
      ? `${wrap}${selected || text}${wrap}`
      : text;
    const next = input.slice(0, start) + inserted + input.slice(end);
    setInput(next);
    // 焦点与光标复位到插入内容之后
    requestAnimationFrame(() => {
      if (!el) return;
      el.focus();
      const caret = start + inserted.length - (wrap != null && !selected ? wrap.length : 0);
      el.setSelectionRange(caret, caret);
    });
  }, [input]);

  // 仓库资源插入: 文件链接 / 代码片段引用 (频道即仓库)
  const handleResourceInsert = useCallback((pick: RepoResourcePick) => {
    const repoPath = activeRepo?.path;
    if (!repoPath) return;
    const base = `/editor/${repoPath}?file=${encodeURIComponent(pick.path)}`;
    let markdown: string;
    if (pick.startLine == null || pick.endLine == null || pick.snippet == null) {
      markdown = `[${pick.path}](${base})`;
    } else {
      // 片段始终以围栏代码块呈现内容预览 (含单行) + 可跳转并高亮区间的链接
      const ext = pick.path.split('.').pop()?.toLowerCase() ?? '';
      const langMap: Record<string, string> = {
        ts: 'ts', tsx: 'tsx', js: 'js', jsx: 'jsx', py: 'python', json: 'json',
        md: 'markdown', css: 'css', scss: 'scss', html: 'html', yml: 'yaml',
        yaml: 'yaml', sh: 'bash', go: 'go', rs: 'rust', java: 'java', sql: 'sql', toml: 'toml',
      };
      const fence = '```' + (langMap[ext] ?? '');
      const range = pick.startLine === pick.endLine ? `${pick.startLine}` : `${pick.startLine}-${pick.endLine}`;
      markdown = `${fence}\n${pick.snippet}\n\`\`\`\n[\`${pick.path}:${range}\`](${base}&line=${pick.startLine}&end=${pick.endLine})`;
    }
    insertAtCursor(markdown);
    setResourcePicker(null);
  }, [activeRepo?.path, insertAtCursor]);

  const handleFileSelected = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = '';
    if (!file || !room) return;
    if (wsStatus !== 'connected') {
      antdMessage.warning(t('app.teamChat.disconnected'));
      return;
    }
    setUploading(true);
    try {
      const att = await chatApi.uploadAttachment(room.id, file);
      const content = att.content_type.startsWith('image/')
        ? `![${att.name}](${att.url})`
        : `[${att.name}](${att.url})`;
      chatSocket.sendChatMessage(room.id, content);
    } catch (err) {
      antdMessage.error((err as Error).message || 'Upload failed');
    } finally {
      setUploading(false);
    }
  }, [room, wsStatus, t]);

  const activeChannelName = useMemo(() =>
    channels.find((c) => c.id === activeChannel)?.name || room?.name || '—',
    [channels, activeChannel, room]
  );

  const dayLabel = (dateStr: string | null): string => {
    if (!dateStr) return '';
    const diff = dayDiffFromToday(dateStr);
    if (Number.isNaN(diff)) return '';
    if (diff === 0) return t('app.teamChat.today');
    if (diff === -1) return t('app.teamChat.yesterday', { defaultValue: 'Yesterday' });
    return new Date(dateStr).toLocaleDateString([], { year: 'numeric', month: 'long', day: 'numeric' });
  };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  if (loading && !activeRepoId) {
    // 没有任何可用频道时不要永远停在骨架屏
    if (channelsLoaded && channels.length === 0) {
      return (
        <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: textSecondary, fontSize: 14 }}>
          {t('app.teamChat.noChannels')}
        </div>
      );
    }
    return <ChatSkeleton />;
  }

  if (error) {
    return (
      <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: textSecondary }}>
        {error}
      </div>
    );
  }

  const onlineMembers = members.filter((m) => onlineUserIds.has(m.user_id));
  const offlineMembers = members.filter((m) => !onlineUserIds.has(m.user_id));

  const moreMenu: MenuProps['items'] = [
    {
      key: 'details',
      icon: <InfoCircleOutlined />,
      label: t('app.teamChat.roomDetails', { defaultValue: '频道信息与成员' }),
      onClick: () => setDetailsOpen(true),
    },
    { type: 'divider' },
    {
      key: 'mute',
      icon: <BellOutlined style={{ color: myMuted ? textTertiary : undefined }} />,
      label: myMuted
        ? t('app.teamChat.unmuteRoom', { defaultValue: '取消静音会话' })
        : t('app.teamChat.muteRoom', { defaultValue: '静音会话' }),
      onClick: () => { void toggleMute(); },
    },
  ];

  return (
    <Layout style={{ height: '100%', background: 'transparent' }}>
      <style>{`
        .chat-msg:hover .chat-delete-btn {
          opacity: 1 !important;
        }
      `}</style>
      {/* Left Channels */}
      <Sider
        width={240}
        style={{
          background: bgSecondary,
          borderRight: `1px solid ${borderColor}`,
          display: 'flex',
          flexDirection: 'column',
          flexShrink: 0,
        }}
      >
        <div style={{ padding: 16, borderBottom: `1px solid ${borderColor}`, position: 'relative' }}>
          <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 10, color: textPrimary }}>Perseus Team</h3>
          <div ref={searchBoxWrapRef}>
            <Input
              value={searchQ}
              onChange={(e) => handleSearchChange(e.target.value)}
              onFocus={() => { if (searchQ.trim()) setSearchOpen(true); }}
              placeholder={t('app.topBar.searchPlaceholder')}
              prefix={<SearchOutlined style={{ color: textTertiary, fontSize: 14 }} />}
              suffix={searchLoading ? <LoadingOutlined style={{ color: textTertiary }} /> : undefined}
              style={{ background: bgPrimary, borderColor: '#30363d', color: textPrimary }}
              size="small"
            />
          </div>
          {searchQ.trim() && room && (
            <div style={{ display: 'flex', gap: 6, marginTop: 8 }}>
              {(['all', 'room'] as const).map((scope) => {
                const active = searchScope === scope;
                return (
                  <button
                    key={scope}
                    onClick={() => { setSearchScope(scope); doSearch(searchQ, scope); }}
                    style={{
                      flex: 1,
                      padding: '3px 8px',
                      fontSize: 11,
                      cursor: 'pointer',
                      borderRadius: 6,
                      border: `1px solid ${active ? bluePrimary : borderColor}`,
                      background: active ? 'rgba(31,111,235,0.15)' : 'transparent',
                      color: active ? bluePrimary : textSecondary,
                    }}
                  >
                    {scope === 'all'
                      ? t('app.teamChat.searchScopeAll', { defaultValue: '全部会话' })
                      : t('app.teamChat.searchScopeRoom', { defaultValue: '本会话' })}
                  </button>
                );
              })}
            </div>
          )}
          {searchOpen && (
            <div
              style={{
                position: 'absolute',
                top: 56,
                left: 8,
                right: 8,
                zIndex: 20,
                background: bgTertiary,
                border: `1px solid ${borderColor}`,
                borderRadius: 8,
                boxShadow: '0 8px 24px rgba(0,0,0,0.4)',
                maxHeight: 320,
                overflowY: 'auto',
              }}
            >
              {searchResults.length === 0 ? (
                <div style={{ padding: '12px 14px', fontSize: 12, color: textTertiary }}>
                  {t('app.teamChat.searchNoResults', { defaultValue: 'No matching messages' })}
                </div>
              ) : (
                searchResults.map((hit) => (
                  <div
                    key={hit.id}
                    onClick={() => openSearchHit(hit)}
                    style={{
                      display: 'flex',
                      flexDirection: 'column',
                      gap: 2,
                      padding: '8px 14px',
                      cursor: 'pointer',
                      borderBottom: `1px solid ${borderColor}`,
                    }}
                    onMouseEnter={(e) => { e.currentTarget.style.background = hoverBg; }}
                    onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11 }}>
                      <span style={{ color: bluePrimary, fontWeight: 600 }}>{hit.sender_username}</span>
                      <span style={{ color: textTertiary }}>
                        {hit.room_type === 'dm' ? '@' : '#'}{hit.room_name}
                      </span>
                      <span style={{ color: textTertiary, marginLeft: 'auto' }}>{formatMessageTime(hit.created_at)}</span>
                    </div>
                    <div style={{ fontSize: 12, color: textSecondary, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {hit.content}
                    </div>
                  </div>
                ))
              )}
            </div>
          )}
        </div>
        <div style={{ flex: 1, overflowY: 'auto', padding: '8px 0' }}>
          <div
            style={{
              padding: '4px 16px',
              fontSize: 11,
              textTransform: 'uppercase',
              letterSpacing: 0.5,
              color: textTertiary,
              fontWeight: 600,
            }}
          >
            {t('app.teamChat.channels')}
          </div>
          {channels.map((ch) => {
            const isActive = activeChannel === ch.id;
            return (
              <div
                key={ch.id}
                onClick={() => handleChannelClick(ch.id)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  padding: '6px 16px',
                  cursor: 'pointer',
                  color: isActive ? textPrimary : textSecondary,
                  background: isActive ? activeBg : 'transparent',
                  transition: 'all 0.15s',
                }}
                onMouseEnter={(e) => {
                  if (!isActive) {
                    e.currentTarget.style.background = hoverBg;
                    e.currentTarget.style.color = textPrimary;
                  }
                }}
                onMouseLeave={(e) => {
                  if (!isActive) {
                    e.currentTarget.style.background = 'transparent';
                    e.currentTarget.style.color = textSecondary;
                  }
                }}
              >
                {ch.type === 'public' ? (
                  <NumberOutlined style={{ opacity: 0.6, fontSize: 14 }} />
                ) : (
                  <LockOutlined style={{ opacity: 0.6, fontSize: 14 }} />
                )}
                <span style={{ flex: 1, fontSize: 13 }}>{ch.name}</span>
                {ch.unread > 0 && (
                  <span
                    style={{
                      background: '#f85149',
                      color: '#fff',
                      fontSize: 10,
                      fontWeight: 600,
                      padding: '1px 6px',
                      borderRadius: 10,
                    }}
                  >
                    {ch.unread}
                  </span>
                )}
              </div>
            );
          })}

          <div
            style={{
              padding: '12px 16px 4px',
              fontSize: 11,
              textTransform: 'uppercase',
              letterSpacing: 0.5,
              color: textTertiary,
              fontWeight: 600,
            }}
          >
            {t('app.teamChat.directMessages')}
          </div>
          {dms.length === 0 && dmLoaded && (
            <div style={{ padding: '4px 16px', fontSize: 12, color: textTertiary }}>
              {t('app.teamChat.noDMs', { defaultValue: 'No direct messages yet' })}
            </div>
          )}
          {dms.map((dm) => {
            const isActive = activeDmId === dm.room_id;
            const dmName = dm.peer_username || dm.room_name;
            const dmInitials = getInitials(dmName);
            const dmColor = getAvatarColor(dmInitials);
            return (
              <div
                key={dm.room_id}
                onClick={() => handleDmClick(dm)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  padding: '6px 16px',
                  cursor: 'pointer',
                  color: isActive ? textPrimary : textSecondary,
                  background: isActive ? activeBg : 'transparent',
                  transition: 'all 0.15s',
                }}
                onMouseEnter={(e) => {
                  if (!isActive) {
                    e.currentTarget.style.background = hoverBg;
                    e.currentTarget.style.color = textPrimary;
                  }
                }}
                onMouseLeave={(e) => {
                  if (!isActive) {
                    e.currentTarget.style.background = 'transparent';
                    e.currentTarget.style.color = textSecondary;
                  }
                }}
              >
                <div style={{ position: 'relative' }}>
                  <Avatar size={22} style={{ background: dmColor, fontSize: 9, fontWeight: 600 }}>
                    {dmInitials}
                  </Avatar>
                  <span
                    style={{
                      position: 'absolute',
                      bottom: -1,
                      right: -1,
                      width: 8,
                      height: 8,
                      borderRadius: '50%',
                      background: statusColor(onlineUserIds.has(dm.peer_user_id) ? 'online' : 'offline'),
                      border: `2px solid ${bgSecondary}`,
                    }}
                  />
                </div>
                <span style={{ flex: 1, fontSize: 13, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{dmName}</span>
                {dm.unread_count > 0 && (
                  <span
                    style={{
                      background: '#f85149',
                      color: '#fff',
                      fontSize: 10,
                      fontWeight: 600,
                      padding: '1px 6px',
                      borderRadius: 10,
                    }}
                  >
                    {dm.unread_count}
                  </span>
                )}
              </div>
            );
          })}
        </div>
      </Sider>

      {/* Main Chat */}
      <Layout style={{ background: 'transparent' }}>
        <div
          style={{
            padding: '12px 20px',
            borderBottom: `1px solid ${borderColor}`,
            display: 'flex',
            alignItems: 'center',
            gap: 12,
            flexShrink: 0,
            background: 'transparent',
          }}
        >
          <div style={{ flex: 1 }}>
            <h3
              style={{
                fontSize: 15,
                fontWeight: 700,
                margin: 0,
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                color: textPrimary,
              }}
            >
              {activeKind === 'dm' ? (
                <MessageOutlined style={{ color: textSecondary }} />
              ) : (
                <NumberOutlined style={{ color: textSecondary }} />
              )}{' '}
              {activeKind === 'dm' ? activeChannelName : `#${activeChannelName}`}
            </h3>
            <p style={{ fontSize: 12, color: textSecondary, margin: '2px 0 0' }}>{onlineMembers.length} members online</p>
          </div>
          <div style={{ display: 'flex', gap: 4 }}>
            <Tooltip title={t('app.teamChat.roomDetails', { defaultValue: 'View channel details' })}>
              <Button
                type="text"
                icon={<EyeOutlined style={{ color: membersOpen ? bluePrimary : textTertiary, fontSize: 16 }} />}
                style={{ width: 32, height: 32 }}
                onClick={() => setMembersOpen((v) => !v)}
              />
            </Tooltip>
            <Tooltip title={t('app.teamChat.searchMessages', { defaultValue: 'Search messages' })}>
              <Button type="text" icon={<SearchOutlined style={{ color: textTertiary, fontSize: 16 }} />} style={{ width: 32, height: 32 }} onClick={focusSearch} />
            </Tooltip>
            <Dropdown menu={{ items: moreMenu }} trigger={['click']} placement="bottomRight">
              <Tooltip title={t('app.teamChat.moreActions', { defaultValue: 'More' })}>
                <Button type="text" icon={<MoreOutlined style={{ color: textTertiary, fontSize: 16 }} />} style={{ width: 32, height: 32 }} />
              </Tooltip>
            </Dropdown>
          </div>
        </div>

        <Content style={{ overflowY: 'auto', padding: '16px 20px' }}>
          {messages.length === 0 && !loading && (
            <div style={{ textAlign: 'center', color: textTertiary, fontSize: 13, marginTop: 32 }}>
              {t('app.teamChat.noMessages', { defaultValue: '还没有消息，开始对话吧' })}
            </div>
          )}
          {messages.map((msg, idx) => {
            const curLabel = msg.createdAt ? dayLabel(msg.createdAt) : '';
            const prev = messages[idx - 1];
            const prevLabel = prev?.createdAt ? dayLabel(prev.createdAt) : '';
            const showHeader = curLabel !== '' && curLabel !== prevLabel;
            return (
              <Fragment key={msg.id}>
                {showHeader && (
                  <div style={{ textAlign: 'center', margin: '20px 0', position: 'relative' }}>
                    <div
                      style={{
                        position: 'absolute',
                        left: 0,
                        right: 0,
                        top: '50%',
                        height: 1,
                        background: borderColor,
                      }}
                    />
                    <span
                      style={{
                        background: bgPrimary,
                        padding: '0 12px',
                        fontSize: 11,
                        color: textTertiary,
                        position: 'relative',
                        fontWeight: 500,
                      }}
                    >
                      {curLabel}
                    </span>
                  </div>
                )}
                <div
                  style={{
                display: 'flex',
                gap: 12,
                padding: '6px 0',
                marginBottom: 4,
                borderRadius: 8,
                transition: 'background 0.15s',
              }}
              className="chat-msg"
              onMouseEnter={(e) => {
                e.currentTarget.style.background = hoverBg;
                e.currentTarget.style.margin = '0 -8px';
                e.currentTarget.style.padding = '6px 8px';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'transparent';
                e.currentTarget.style.margin = '0';
                e.currentTarget.style.padding = '6px 0';
              }}
            >
              <Avatar
                size={36}
                style={{
                  background: msg.color,
                  fontSize: 13,
                  fontWeight: 600,
                  marginTop: 2,
                  flexShrink: 0,
                }}
              >
                {msg.initials}
              </Avatar>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginBottom: 2 }}>
                  <span style={{ fontSize: 14, fontWeight: 600, color: textPrimary }}>{msg.author}</span>
                  <span style={{ fontSize: 11, color: textTertiary }}>{msg.time}</span>
                  {user && msg.senderId === user.id && (
                    <Tooltip title={t('app.teamChat.deleteMessage', { defaultValue: '删除' })}>
                      <button
                        onClick={() => handleDeleteMessage(msg)}
                        style={{
                          background: 'none',
                          border: 'none',
                          color: textTertiary,
                          cursor: 'pointer',
                          padding: 0,
                          fontSize: 12,
                          lineHeight: 1,
                          marginLeft: 'auto',
                          opacity: 0,
                          transition: 'opacity 0.15s',
                        }}
                        onMouseEnter={(e) => { e.currentTarget.style.color = '#f85149'; }}
                        onMouseLeave={(e) => { e.currentTarget.style.color = textTertiary; }}
                        className="chat-delete-btn"
                      >
                        <DeleteOutlined style={{ fontSize: 12 }} />
                      </button>
                    </Tooltip>
                  )}
                </div>
                <div
                  style={{
                    fontSize: 14,
                    lineHeight: 1.5,
                    color: textSecondary,
                    wordWrap: 'break-word',
                  }}
                >
                  <Markdown collapsibleCode>{msg.text}</Markdown>
                </div>
                <div style={{ display: 'flex', gap: 4, marginTop: 6 }}>
                    {msg.reactions && msg.reactions.map((r, idx) => (
                      <span
                        key={idx}
                        onClick={() => handleReaction(msg, r.emoji)}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: 4,
                          padding: '2px 8px',
                          borderRadius: 12,
                          background: r.active ? 'rgba(31,111,235,0.15)' : bgPrimary,
                          border: `1px solid ${r.active ? bluePrimary : '#30363d'}`,
                          fontSize: 12,
                          cursor: 'pointer',
                        }}
                      >
                        {r.emoji} <span style={{ fontSize: 11, color: textSecondary }}>{r.count}</span>
                      </span>
                    ))}
                    <Popover
                      trigger="click"
                      styles={{ root: { background: bgSecondary, border: `1px solid ${borderColor}` } }}
                      content={
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(8, 1fr)', gap: 2, width: 264 }}>
                          {emojiPalette.map((emoji) => (
                            <button
                              key={emoji}
                              onClick={() => { handleReactionPicker(msg, emoji); }}
                              style={{
                                background: 'transparent',
                                border: 'none',
                                fontSize: 16,
                                cursor: 'pointer',
                                padding: 4,
                                borderRadius: 6,
                                lineHeight: 1,
                              }}
                              onMouseEnter={(e) => { e.currentTarget.style.background = hoverBg; }}
                              onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
                            >
                              {emoji}
                            </button>
                          ))}
                        </div>
                      }
                    >
                      <button
                        style={{
                          background: 'transparent',
                          border: `1px dashed #30363d`,
                          borderRadius: 12,
                          color: textTertiary,
                          fontSize: 12,
                          padding: '0 8px',
                          cursor: 'pointer',
                        }}
                      >
                        +
                      </button>
                    </Popover>
                  </div>
                </div>
            </div>
              </Fragment>
            );
          })}
          <div ref={messagesEndRef} />
        </Content>

        <div style={{ padding: '12px 20px', borderTop: `1px solid ${borderColor}`, flexShrink: 0 }}>
          {sendError && (
            <div style={{ fontSize: 12, color: '#f85149', marginBottom: 6 }}>{sendError}</div>
          )}
          <div
            style={{
              background: bgTertiary,
              border: `1px solid #30363d`,
              borderRadius: 12,
              overflow: 'hidden',
            }}
          >
            <div ref={textAreaRef}>
              <Input.TextArea
                value={input}
                onChange={(e) => handleInputChange(e.target.value)}
                onPressEnter={(e) => {
                  if (!e.shiftKey) {
                    e.preventDefault();
                    handleSend();
                  }
                }}
                placeholder={t('app.teamChat.placeholder', { channel: activeChannelName })}
                autoSize={{ minRows: 1, maxRows: 4 }}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: textPrimary,
                  resize: 'none',
                  padding: '12px 14px',
                }}
              />
            </div>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                padding: '6px 10px',
                gap: 2,
                borderTop: `1px solid #30363d`,
              }}
            >
              <input
                ref={fileInputRef}
                type="file"
                style={{ display: 'none' }}
                onChange={handleFileSelected}
              />
              <Tooltip title={t('app.teamChat.attach', { defaultValue: '上传附件' })}>
                <Button
                  type="text"
                  icon={<PaperClipOutlined style={{ fontSize: 14, color: uploading ? bluePrimary : textTertiary }} />}
                  size="small"
                  loading={uploading}
                  onClick={() => fileInputRef.current?.click()}
                />
              </Tooltip>
              <Popover
                trigger="click"
                open={emojiOpen}
                onOpenChange={setEmojiOpen}
                styles={{ root: { background: bgSecondary, border: `1px solid ${borderColor}` } }}
                content={
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(8, 1fr)', gap: 2, width: 264 }}>
                    {emojiPalette.map((emoji) => (
                      <button
                        key={emoji}
                        onClick={() => { insertAtCursor(emoji); setEmojiOpen(false); }}
                        style={{
                          background: 'transparent',
                          border: 'none',
                          fontSize: 18,
                          cursor: 'pointer',
                          padding: 4,
                          borderRadius: 6,
                          lineHeight: 1,
                        }}
                        onMouseEnter={(e) => { e.currentTarget.style.background = hoverBg; }}
                        onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
                      >
                        {emoji}
                      </button>
                    ))}
                  </div>
                }
              >
                <Button type="text" icon={<SmileOutlined style={{ fontSize: 14, color: textTertiary }} />} size="small" />
              </Popover>
              <Tooltip title={t('app.teamChat.bold', { defaultValue: '粗体' })}>
                <Button
                  type="text"
                  size="small"
                  onMouseDown={(e) => e.preventDefault()}
                  onClick={() => insertAtCursor(t('app.teamChat.boldText', { defaultValue: '粗体' }), '**')}
                  icon={<BoldOutlined style={{ fontSize: 14, color: textTertiary }} />}
                />
              </Tooltip>
              <Tooltip title={t('app.teamChat.italic', { defaultValue: '斜体' })}>
                <Button
                  type="text"
                  size="small"
                  onMouseDown={(e) => e.preventDefault()}
                  onClick={() => insertAtCursor(t('app.teamChat.italicText', { defaultValue: '斜体' }), '*')}
                  icon={<ItalicOutlined style={{ fontSize: 14, color: textTertiary }} />}
                />
              </Tooltip>
              <Tooltip title={activeRepo ? t('app.teamChat.insertCode', { defaultValue: '插入仓库代码片段' }) : t('app.teamChat.repoOnly', { defaultValue: '仅仓库频道可用' })}>
                <Button
                  type="text"
                  size="small"
                  disabled={!activeRepo}
                  onClick={() => setResourcePicker('code')}
                  icon={<CodeOutlined style={{ fontSize: 14, color: textTertiary }} />}
                />
              </Tooltip>
              <Tooltip title={activeRepo ? t('app.teamChat.insertFile', { defaultValue: '插入仓库文件' }) : t('app.teamChat.repoOnly', { defaultValue: '仅仓库频道可用' })}>
                <Button
                  type="text"
                  size="small"
                  disabled={!activeRepo}
                  onClick={() => setResourcePicker('file')}
                  icon={<FileAddOutlined style={{ fontSize: 14, color: textTertiary }} />}
                />
              </Tooltip>
              <Tooltip title={wsStatus !== 'connected' ? t('app.teamChat.disconnected') : 'Enter'}>
                <Button
                  type="primary"
                  icon={<SendOutlined style={{ fontSize: 14 }} />}
                  size="small"
                  onClick={handleSend}
                  disabled={wsStatus !== 'connected' || !input.trim()}
                  style={{ marginLeft: 'auto', background: bluePrimary, borderColor: bluePrimary }}
                />
              </Tooltip>
            </div>
          </div>
        </div>
      </Layout>

      {/* Right Members (Eye 显隐) */}
      {membersOpen && (
      <Sider
        width={220}
        style={{
          background: bgSecondary,
          borderLeft: `1px solid ${borderColor}`,
          flexShrink: 0,
        }}
      >
        <div style={{ padding: 16, overflow: 'auto', height: '100%' }}>
          <div
            style={{
              fontSize: 11,
              textTransform: 'uppercase',
              letterSpacing: 0.5,
              color: textTertiary,
              fontWeight: 600,
              marginBottom: 8,
              display: 'flex',
              alignItems: 'center',
              gap: 6,
            }}
          >
            <StatusDot status="online" size={8} /> {t('app.teamChat.members')} — {onlineMembers.length}
          </div>
          {onlineMembers.map((m) => (
            <div
              key={m.user_id || m.name}
              onClick={() => handleMemberClick(m)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                padding: '6px 0',
                cursor: 'pointer',
                color: textSecondary,
                transition: 'all 0.15s',
              }}
              onMouseEnter={(e) => { e.currentTarget.style.background = hoverBg; e.currentTarget.style.color = textPrimary; }}
              onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = textSecondary; }}
            >
              <div style={{ position: 'relative' }}>
                <Avatar size={28} style={{ background: m.color, fontSize: 11, fontWeight: 600 }}>{m.initials}</Avatar>
                <span
                  style={{
                    position: 'absolute',
                    bottom: -1,
                    right: -1,
                    width: 8,
                    height: 8,
                    borderRadius: '50%',
                    background: statusColor(onlineUserIds.has(m.user_id) ? 'online' : 'offline'),
                    border: `2px solid ${bgSecondary}`,
                  }}
                />
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 13, color: 'inherit', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{m.name}</div>
                <div style={{ fontSize: 10, color: textTertiary }}>{m.role}</div>
              </div>
            </div>
          ))}

          <div
            style={{
              fontSize: 11,
              textTransform: 'uppercase',
              letterSpacing: 0.5,
              color: textTertiary,
              fontWeight: 600,
              marginTop: 16,
              marginBottom: 8,
              display: 'flex',
              alignItems: 'center',
              gap: 6,
            }}
          >
            <StatusDot status="offline" size={8} /> {t('app.teamChat.offlineMembers')} — {offlineMembers.length}
          </div>
          {offlineMembers.map((m) => (
            <div
              key={m.user_id || m.name}
              onClick={() => handleMemberClick(m)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                padding: '6px 0',
                cursor: 'pointer',
                color: textSecondary,
                transition: 'all 0.15s',
              }}
              onMouseEnter={(e) => { e.currentTarget.style.background = hoverBg; e.currentTarget.style.color = textPrimary; }}
              onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = textSecondary; }}
            >
              <div style={{ position: 'relative' }}>
                <Avatar size={28} style={{ background: m.color, fontSize: 11, fontWeight: 600 }}>{m.initials}</Avatar>
                <span
                  style={{
                    position: 'absolute',
                    bottom: -1,
                    right: -1,
                    width: 8,
                    height: 8,
                    borderRadius: '50%',
                    background: statusColor(onlineUserIds.has(m.user_id) ? 'online' : 'offline'),
                    border: `2px solid ${bgSecondary}`,
                  }}
                />
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 13, color: 'inherit', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{m.name}</div>
                <div style={{ fontSize: 10, color: textTertiary }}>{m.role}</div>
              </div>
            </div>
          ))}
        </div>
      </Sider>
      )}

      {/* 频道信息 Drawer (More → 频道信息与成员) */}
      <Drawer
        title={room ? (activeKind === 'dm' ? activeChannelName : `#${activeChannelName}`) : ''}
        placement="right"
        width={300}
        open={detailsOpen}
        onClose={() => setDetailsOpen(false)}
        styles={{
          content: { background: bgSecondary },
          header: { background: bgSecondary, borderColor, color: textPrimary },
          body: { padding: 16, color: textSecondary },
        }}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ fontSize: 12, textTransform: 'uppercase', letterSpacing: 0.5, color: textTertiary, fontWeight: 600 }}>
              {t('app.teamChat.roomInfo', { defaultValue: '频道信息' })}
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13 }}>
              <span style={{ color: textTertiary }}>{t('app.teamChat.roomType', { defaultValue: '类型' })}</span>
              <span style={{ color: textPrimary }}>{activeKind === 'dm' ? t('app.teamChat.dmType', { defaultValue: '私聊' }) : (room?.room_type === 'dm' ? t('app.teamChat.dmType', { defaultValue: '私聊' }) : t('app.teamChat.channelType', { defaultValue: '频道' }))}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13 }}>
              <span style={{ color: textTertiary }}>{t('app.teamChat.memberCount', { defaultValue: '成员' })}</span>
              <span style={{ color: textPrimary }}>{members.length}（{t('app.teamChat.onlineCount', { defaultValue: '在线 {{n}}', n: onlineMembers.length })}）</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13 }}>
              <span style={{ color: textTertiary }}>{t('app.teamChat.unread', { defaultValue: '未读' })}</span>
              <span style={{ color: textPrimary }}>{activeKind === 'channel' && activeRepoId ? (unreadByRepo[activeRepoId] ?? 0) : 0}</span>
            </div>
          </div>

          <div style={{ borderTop: `1px solid ${borderColor}` }} />

          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                <span style={{ fontSize: 13, color: textPrimary }}>
                  <BellOutlined style={{ marginRight: 6, color: textTertiary }} />
                  {myMuted
                    ? t('app.teamChat.roomMuted', { defaultValue: '已静音该会话' })
                    : t('app.teamChat.muteRoom', { defaultValue: '静音会话' })}
                </span>
                <span style={{ fontSize: 12, color: textTertiary }}>
                  {t('app.teamChat.muteDesc', { defaultValue: '静音后不再累计未读' })}
                </span>
              </div>
              <Switch
                size="small"
                checked={myMuted}
                onChange={() => { void toggleMute(); }}
                checkedChildren={t('app.teamChat.mutedShort', { defaultValue: '静音' })}
                unCheckedChildren={t('app.teamChat.unmutedShort', { defaultValue: '响铃' })}
              />
            </div>
          </div>

          <div style={{ borderTop: `1px solid ${borderColor}` }} />

          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <div style={{ fontSize: 12, textTransform: 'uppercase', letterSpacing: 0.5, color: textTertiary, fontWeight: 600 }}>
              <TeamOutlined style={{ marginRight: 6 }} />
              {t('app.teamChat.members')} — {members.length}
            </div>
            {members.map((m) => (
              <div
                key={m.user_id || m.name}
                onClick={() => { setDetailsOpen(false); void handleMemberClick(m); }}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  padding: '6px 4px',
                  borderRadius: 6,
                  cursor: 'pointer',
                  transition: 'all 0.15s',
                }}
                onMouseEnter={(e) => { e.currentTarget.style.background = hoverBg; }}
                onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
              >
                <Avatar size={28} style={{ background: m.color, fontSize: 11, fontWeight: 600 }}>{m.initials}</Avatar>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 13, color: textPrimary, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', display: 'flex', alignItems: 'center', gap: 6 }}>
                    <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{m.name}</span>
                    {m.is_muted && <BellOutlined style={{ fontSize: 11, color: textTertiary }} />}
                  </div>
                  <div style={{ fontSize: 10, color: textTertiary }}>{m.role}</div>
                </div>
                <span style={{ width: 8, height: 8, borderRadius: '50%', background: statusColor(onlineUserIds.has(m.user_id) ? 'online' : 'offline'), border: `2px solid ${bgSecondary}`, flexShrink: 0 }} />
              </div>
            ))}
          </div>
        </div>
      </Drawer>

      {/* 仓库资源选择器: 插入仓库文件 / 代码片段 (打开时挂载以重置状态) */}
      {resourcePicker !== null && (
        <RepoResourcePicker
          open
          mode={resourcePicker}
          repoId={activeRepoId}
          repoPath={activeRepo?.path ?? null}
          defaultBranch={activeRepo?.default_branch}
          onCancel={() => setResourcePicker(null)}
          onInsert={handleResourceInsert}
        />
      )}
    </Layout>
  );
}
