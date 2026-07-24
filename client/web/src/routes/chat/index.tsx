import { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { Layout, Input, Button, Avatar, Tooltip } from 'antd';
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
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import ChatSkeleton from '../../components/skeleton/ChatSkeleton';
import { useRepositoriesStore } from '../../stores/repositories';
import { useAuthStore } from '../../stores/auth';
import { chatApi, type ChatMessage, type RoomMember, type RealtimeRoom } from '../../api/chat';
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
  const { t } = useTranslation();
  const messagesEndRef = useRef<HTMLDivElement>(null);

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

  // Fetch user repositories on mount
  useEffect(() => {
    if (user?.id) {
      fetchRepositoriesByUser(user.id);
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
      const [messagesRes, membersRes] = await Promise.all([
        chatApi.getRoomMessages(roomData.id, { limit: 50 }),
        chatApi.getRoomMembers(roomData.id),
      ]);

      const mappedMessages: Message[] = messagesRes.messages.map((msg: ChatMessage) => {
        const author = msg.sender_username || 'unknown';
        const initials = getInitials(author);
        return {
          id: msg.id,
          author,
          initials,
          color: getAvatarColor(initials),
          time: formatMessageTime(msg.created_at),
          text: msg.content,
        };
      }).reverse();

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

  const activeChannelName = useMemo(() =>
    channels.find((c) => c.id === activeChannel)?.name || room?.name || '—',
    [channels, activeChannel, room]
  );

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  if (loading && !activeRepoId) return <ChatSkeleton />;

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
                </div>
                <div
                  style={{
                    fontSize: 14,
                    lineHeight: 1.5,
                    color: textSecondary,
                    wordWrap: 'break-word',
                  }}
                  dangerouslySetInnerHTML={{
                    __html: msg.text.replace(
                      /<code>(.*?)<\/code>/g,
                      '<code style="background:#1c2128;padding:1px 5px;border-radius:3px;font-family:\'JetBrains Mono\',monospace;font-size:12px;color:#58a6ff;">$1</code>'
                    ),
                  }}
                />
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
          <div
            style={{
              background: bgTertiary,
              border: `1px solid #30363d`,
              borderRadius: 12,
              overflow: 'hidden',
            }}
          >
            <Input.TextArea
              value={input}
              onChange={(e) => setInput(e.target.value)}
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
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                padding: '6px 10px',
                gap: 2,
                borderTop: `1px solid #30363d`,
              }}
            >
              <Button type="text" icon={<PaperClipOutlined style={{ fontSize: 14, color: textTertiary }} />} size="small" />
              <Button type="text" icon={<SmileOutlined style={{ fontSize: 14, color: textTertiary }} />} size="small" />
              <Button type="text" icon={<BoldOutlined style={{ fontSize: 14, color: textTertiary }} />} size="small" />
              <Button type="text" icon={<ItalicOutlined style={{ fontSize: 14, color: textTertiary }} />} size="small" />
              <Button type="text" icon={<CodeOutlined style={{ fontSize: 14, color: textTertiary }} />} size="small" />
              <Button type="text" icon={<LinkOutlined style={{ fontSize: 14, color: textTertiary }} />} size="small" />
              <Button
                type="primary"
                icon={<SendOutlined style={{ fontSize: 14 }} />}
                size="small"
                style={{ marginLeft: 'auto', background: bluePrimary, borderColor: bluePrimary }}
              />
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
