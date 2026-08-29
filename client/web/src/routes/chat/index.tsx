import { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { Layout, Input, Button, Avatar, Tooltip, Popover, message as antdMessage } from 'antd';
import {
  NumberOutlined,
  LockOutlined,
  SendOutlined,
  PaperClipOutlined,
  SmileOutlined,
  BoldOutlined,
  ItalicOutlined,
  CodeOutlined,
  LinkOutlined,
  SearchOutlined,
  EyeOutlined,
  MoreOutlined,
  DeleteOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import ChatSkeleton from '../../components/skeleton/ChatSkeleton';
import Markdown from '../../components/Markdown';
import { useRepositoriesStore } from '../../stores/repositories';
import { useAuthStore } from '../../stores/auth';
import { chatApi, type ChatMessage, type RoomMember, type RealtimeRoom } from '../../api/chat';
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

interface DM {
  id: string;
  name: string;
  status: 'online' | 'away' | 'offline';
  initials: string;
  color: string;
}

interface Message {
  id: string;
  senderId: string;
  author: string;
  initials: string;
  color: string;
  time: string;
  text: string;
  reactions?: { emoji: string; count: number; active: boolean }[];
}

interface Member {
  name: string;
  role: string;
  status: 'online' | 'away' | 'offline';
  initials: string;
  color: string;
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
    text: msg.content,
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
  const [activeRepoId, setActiveRepoId] = useState<string | null>(null);
  const [room, setRoom] = useState<RealtimeRoom | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [members, setMembers] = useState<Member[]>([]);
  const [dms, setDms] = useState<DM[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [input, setInput] = useState('');
  const [sendError, setSendError] = useState<string | null>(null);
  const [wsStatus, setWsStatus] = useState<ChatSocketStatus>('disconnected');
  const [channelsLoaded, setChannelsLoaded] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [emojiOpen, setEmojiOpen] = useState(false);
  const { t } = useTranslation();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const activeRoomIdRef = useRef<string | null>(null);
  const joinedRoomIdRef = useRef<string | null>(null);
  const textAreaRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { user } = useAuthStore();
  const { repositories, fetchRepositoriesByUser } = useRepositoriesStore();

  const channels: Channel[] = useMemo(() =>
    repositories.map((r: Repository) => ({
      id: r.id,
      name: r.name,
      type: r.is_public ? 'public' : 'private',
      unread: 0,
    })),
    [repositories]
  );

  // WebSocket: 连接、房间订阅与实时消息接收
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
        }
      },
      onError: (err, originalType) => {
        if (originalType === 'chat_message') setSendError(err);
      },
    });
    chatSocket.start();
    return () => chatSocket.stop();
  }, []);

  // Fetch user repositories on mount
  useEffect(() => {
    if (user?.id) {
      fetchRepositoriesByUser(user.id).finally(() => setChannelsLoaded(true));
    } else {
      // 微任务延迟, 避免在 effect 同步体中触发级联渲染
      Promise.resolve().then(() => setChannelsLoaded(true));
    }
  }, [user?.id, fetchRepositoriesByUser]);

  // Load room, messages and members when channel changes
  const loadChannel = useCallback(async (repoId: string, options?: { selectOnSuccess?: boolean }) => {
    setLoading(true);
    setError(null);
    try {
      const roomData = await chatApi.getRepositoryRoom(repoId);
      setRoom(roomData);
      setActiveRepoId(repoId);
      activeRoomIdRef.current = roomData.id;

      // 切换房间: 离开旧的, 加入新的以接收实时广播
      if (joinedRoomIdRef.current !== roomData.id) {
        if (joinedRoomIdRef.current) {
          chatSocket.leaveRoom(joinedRoomIdRef.current);
        }
        chatSocket.joinRoom(roomData.id);
        joinedRoomIdRef.current = roomData.id;
      }

      const [messagesRes, membersRes] = await Promise.all([
        chatApi.getRoomMessages(roomData.id, { limit: 50 }),
        chatApi.getRoomMembers(roomData.id),
      ]);

      const mappedMessages: Message[] = messagesRes.messages
        .map(mapChatMessage)
        .reverse();

      const mappedMembers: Member[] = membersRes.map((m: RoomMember) => {
        const name = m.username || m.user_id;
        const initials = getInitials(name);
        return {
          name,
          role: m.role === 'admin' ? 'Admin' : 'Member',
          status: 'online',
          initials,
          color: getAvatarColor(initials),
        };
      });

      const mappedDms: DM[] = membersRes.map((m: RoomMember) => {
        const name = m.username || m.user_id;
        const initials = getInitials(name);
        return {
          id: m.user_id,
          name,
          status: 'online',
          initials,
          color: getAvatarColor(initials),
        };
      });

      setMessages(mappedMessages);
      setMembers(mappedMembers);
      setDms(mappedDms);
      if (options?.selectOnSuccess) {
        setActiveChannel(repoId);
      }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  // Auto-select first channel
  useEffect(() => {
    if (!activeChannel && channels.length > 0) {
      const first = channels[0];
      // 通过微任务延迟加载，避免在 effect 同步体中触发状态更新
      Promise.resolve().then(() => {
        loadChannel(first.id, { selectOnSuccess: true });
      });
    }
  }, [channels, activeChannel, loadChannel]);

  const handleChannelClick = useCallback((channelId: string) => {
    if (channelId === activeChannel) return;
    setActiveChannel(channelId);
    loadChannel(channelId);
  }, [activeChannel, loadChannel]);

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

  const insertLink = useCallback(() => {
    const el = getTextAreaEl();
    const start = el?.selectionStart ?? input.length;
    const end = el?.selectionEnd ?? input.length;
    const selected = input.slice(start, end);
    // 选中内容形似 URL 时作为链接地址, 否则作为链接文本
    const isUrl = /^https?:\/\//.test(selected);
    const inserted = isUrl
      ? `[文本](${selected})`
      : `[${selected || '文本'}](https://)`;
    const next = input.slice(0, start) + inserted + input.slice(end);
    setInput(next);
    requestAnimationFrame(() => {
      if (!el) return;
      el.focus();
      const caret = isUrl
        ? start + inserted.length
        : start + inserted.length - 'https://)'.length - (selected ? 0 : 1);
      el.setSelectionRange(caret, caret);
    });
  }, [input]);

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

  const onlineMembers = members.filter((m) => m.status !== 'offline');
  const offlineMembers = members.filter((m) => m.status === 'offline');

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
        <div style={{ padding: 16, borderBottom: `1px solid ${borderColor}` }}>
          <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 10, color: textPrimary }}>Perseus Team</h3>
          <Input
            placeholder={t('app.topBar.searchPlaceholder')}
            prefix={<SearchOutlined style={{ color: textTertiary, fontSize: 14 }} />}
            style={{ background: bgPrimary, borderColor: '#30363d', color: textPrimary }}
            size="small"
          />
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
          {dms.map((dm) => (
            <div
              key={dm.id}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                padding: '6px 16px',
                cursor: 'pointer',
                color: textSecondary,
                transition: 'all 0.15s',
              }}
              onMouseEnter={(e) => { e.currentTarget.style.background = hoverBg; e.currentTarget.style.color = textPrimary; }}
              onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = textSecondary; }}
            >
              <div style={{ position: 'relative' }}>
                <Avatar size={22} style={{ background: dm.color, fontSize: 9, fontWeight: 600 }}>
                  {dm.initials}
                </Avatar>
                <span
                  style={{
                    position: 'absolute',
                    bottom: -1,
                    right: -1,
                    width: 8,
                    height: 8,
                    borderRadius: '50%',
                    background: statusColor(dm.status),
                    border: `2px solid ${bgSecondary}`,
                  }}
                />
              </div>
              <span style={{ fontSize: 13 }}>{dm.name}</span>
            </div>
          ))}
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
              <NumberOutlined style={{ color: textSecondary }} /> #{activeChannelName}
            </h3>
            <p style={{ fontSize: 12, color: textSecondary, margin: '2px 0 0' }}>{onlineMembers.length} members online</p>
          </div>
          <div style={{ display: 'flex', gap: 4 }}>
            <Tooltip title="View channel details">
              <Button type="text" icon={<EyeOutlined style={{ color: textTertiary, fontSize: 16 }} />} style={{ width: 32, height: 32 }} />
            </Tooltip>
            <Tooltip title="Search messages">
              <Button type="text" icon={<SearchOutlined style={{ color: textTertiary, fontSize: 16 }} />} style={{ width: 32, height: 32 }} />
            </Tooltip>
            <Tooltip title="More">
              <Button type="text" icon={<MoreOutlined style={{ color: textTertiary, fontSize: 16 }} />} style={{ width: 32, height: 32 }} />
            </Tooltip>
          </div>
        </div>

        <Content style={{ overflowY: 'auto', padding: '16px 20px' }}>
          <div style={{ textAlign: 'center', margin: '16px 0', position: 'relative' }}>
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
              {t('app.teamChat.today')}
            </span>
          </div>
          {messages.length === 0 && !loading && (
            <div style={{ textAlign: 'center', color: textTertiary, fontSize: 13, marginTop: 32 }}>
              No messages yet. Start the conversation!
            </div>
          )}
          {messages.map((msg) => (
            <div
              key={msg.id}
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
                  <Markdown>{msg.text}</Markdown>
                </div>
                {msg.reactions && (
                  <div style={{ display: 'flex', gap: 4, marginTop: 6 }}>
                    {msg.reactions.map((r, idx) => (
                      <span
                        key={idx}
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
                  </div>
                )}
              </div>
            </div>
          ))}
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
              <Tooltip title="**粗体**">
                <Button type="text" size="small" onClick={() => insertAtCursor('粗体', '**')} icon={<BoldOutlined style={{ fontSize: 14, color: textTertiary }} />} />
              </Tooltip>
              <Tooltip title="*斜体*">
                <Button type="text" size="small" onClick={() => insertAtCursor('斜体', '*')} icon={<ItalicOutlined style={{ fontSize: 14, color: textTertiary }} />} />
              </Tooltip>
              <Tooltip title="`行内代码`">
                <Button type="text" size="small" onClick={() => insertAtCursor('code', '`')} icon={<CodeOutlined style={{ fontSize: 14, color: textTertiary }} />} />
              </Tooltip>
              <Tooltip title="[文本](url)">
                <Button type="text" size="small" onClick={insertLink} icon={<LinkOutlined style={{ fontSize: 14, color: textTertiary }} />} />
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

      {/* Right Members */}
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
              key={m.name}
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
                    background: statusColor(m.status),
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
            <StatusDot status="offline" size={8} /> Offline — {offlineMembers.length}
          </div>
          {offlineMembers.map((m) => (
            <div
              key={m.name}
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
                    background: statusColor(m.status),
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
    </Layout>
  );
}
