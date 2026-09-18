import { useEffect, useMemo, useRef, useState } from 'react';
import { App as AntApp, Avatar, Input, Tag } from 'antd';
import {
  LoadingOutlined,
  LockOutlined,
  MessageOutlined,
  NumberOutlined,
  SearchOutlined,
  TeamOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useRepositoriesStore } from '../../stores/repositories';
import { useChatStore } from '../../stores/chat';
import { useServersStore } from '../../stores/servers';
import { useIdentityStore } from '../../stores/identity';
import type { DMSession, MessageSearchHit } from '../../api/chat';
import { getAvatarColor, getInitials } from '../../utils/avatar';
import ChatMessages from './ChatMessages';
import ChatComposer from './ChatComposer';

const borderColor = '#21262d';
const hoverBg = '#1c2333';
const activeBg = '#1a2332';
const textPrimary = '#e6edf3';
const textSecondary = '#8b949e';
const textTertiary = '#6e7681';
const blueLight = '#58a6ff';
const bgSecondary = '#161b22';
const bgTertiary = '#0d1117';
const green = '#3fb950';

function formatHitTime(dateStr: string | null): string {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  if (Number.isNaN(d.getTime())) return '';
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

export default function ChatView() {
  const { t } = useTranslation();
  const { message } = AntApp.useApp();
  const server = useServersStore((s) => s.servers.find((x) => x.id === s.currentServerId));
  const me = useIdentityStore((s) => s.me);
  const repositories = useRepositoriesStore((s) => s.repositories);
  const fetchRepositories = useRepositoriesStore((s) => s.fetchRepositories);

  const rooms = useChatStore((s) => s.rooms);
  const messages = useChatStore((s) => s.messages);
  const members = useChatStore((s) => s.members);
  const onlineUsers = useChatStore((s) => s.onlineUsers);
  const unreadByRepo = useChatStore((s) => s.unreadByRepo);
  const dms = useChatStore((s) => s.dms);
  const dmLoaded = useChatStore((s) => s.dmLoaded);
  const activeRoomId = useChatStore((s) => s.activeRoomId);
  const status = useChatStore((s) => s.status);
  const start = useChatStore((s) => s.start);
  const openChannel = useChatStore((s) => s.openChannel);
  const openDm = useChatStore((s) => s.openDm);
  const startDm = useChatStore((s) => s.startDm);
  const fetchDms = useChatStore((s) => s.fetchDms);
  const setActiveRoom = useChatStore((s) => s.setActiveRoom);

  const [showMembers, setShowMembers] = useState(true);
  const [searchQ, setSearchQ] = useState('');
  const [searchResults, setSearchResults] = useState<MessageSearchHit[]>([]);
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchLoading, setSearchLoading] = useState(false);
  const searchBoxWrapRef = useRef<HTMLDivElement>(null);
  const searchDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // socket 常驻（对齐终端语义）：只 start 不 stop，切服务器时由 reset 统一清理。
  useEffect(() => {
    start();
  }, [start]);

  useEffect(() => {
    fetchRepositories();
  }, [fetchRepositories]);

  useEffect(() => {
    void useChatStore.getState().fetchChatRooms();
    void fetchDms();
  }, [fetchDms]);

  // 自动选中第一个频道。
  useEffect(() => {
    if (!activeRoomId && repositories.length > 0) {
      void openChannel(repositories[0].id);
    }
  }, [activeRoomId, repositories, openChannel]);

  useEffect(() => () => {
    if (searchDebounceRef.current) clearTimeout(searchDebounceRef.current);
  }, []);

  const activeRoom = useMemo(
    () => rooms.find((r) => r.id === activeRoomId) ?? null,
    [rooms, activeRoomId],
  );

  const roomMembers = activeRoomId ? members[activeRoomId] ?? [] : [];
  const onlineIds = useMemo(
    () => new Set((activeRoomId ? onlineUsers[activeRoomId] ?? [] : []).map((u) => u.user_id)),
    [onlineUsers, activeRoomId],
  );
  const onlineMembers = roomMembers.filter((m) => onlineIds.has(m.user_id));
  const offlineMembers = roomMembers.filter((m) => !onlineIds.has(m.user_id));
  const onlineCount = new Set([...onlineIds, me?.id].filter(Boolean)).size;

  // 跨会话消息检索 (F-603): GET /api/v1/messages/search（300ms 防抖）。
  const doSearch = useMemo(() => (q: string) => {
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
    searchDebounceRef.current = setTimeout(async () => {
      searchDebounceRef.current = null;
      setSearchLoading(true);
      try {
        const res = await useChatStore.getState().searchMessages(trimmed, 20);
        setSearchResults(res.messages);
        setSearchOpen(true);
      } catch {
        setSearchResults([]);
        setSearchOpen(true);
      } finally {
        setSearchLoading(false);
      }
    }, 300);
  }, []);

  const handleSearchChange = (value: string) => {
    setSearchQ(value);
    doSearch(value);
  };

  const focusSearch = () => {
    searchBoxWrapRef.current?.querySelector('input')?.focus();
  };

  const openSearchHit = (hit: MessageSearchHit) => {
    setSearchOpen(false);
    setSearchQ('');
    setSearchResults([]);
    if (hit.room_type === 'repository' && hit.repository_id) {
      void openChannel(hit.repository_id);
    } else {
      void openDm({
        room_id: hit.room_id,
        room_name: hit.room_name,
        room_type: hit.room_type,
        peer_user_id: hit.sender_id,
        peer_username: hit.sender_username,
        created_at: hit.created_at,
        unread_count: 0,
      });
    }
  };

  const handleDmClick = (session: DMSession) => {
    if (activeRoomId === session.room_id) return;
    void openDm(session);
  };

  const handleStartDm = async (userId: string, username: string) => {
    if (!me || userId === me.id) return;
    try {
      await startDm(userId, username);
    } catch (e) {
      message.error(`${t('desktop.chat.newDmFailed')}: ${(e as Error).message}`);
    }
  };

  if (!server) {
    return (
      <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: textSecondary }}>
        {t('desktop.chat.noServer')}
      </div>
    );
  }

  const statusPill = status === 'connected'
    ? <span className="pill" style={{ color: green, borderColor: 'rgba(63,185,80,.5)' }}>{t('desktop.chat.connected')}</span>
    : <span style={{ fontSize: 11, color: textTertiary }}>{t(`desktop.chat.status.${status}`)}</span>;

  return (
    <div style={{ height: '100%', display: 'flex', background: bgTertiary }}>
      {/* 左栏：频道 + 私聊 */}
      <aside style={{ width: 240, flexShrink: 0, background: bgSecondary, borderRight: `1px solid ${borderColor}`, display: 'flex', flexDirection: 'column' }}>
        <div style={{ padding: 14, borderBottom: `1px solid ${borderColor}`, position: 'relative' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
            <b style={{ fontSize: 13, color: textPrimary }}>{t('desktop.chat.title')}</b>
            {statusPill}
          </div>
          <div style={{ fontSize: 11, color: textTertiary, marginBottom: 10 }}>{server.name} · {repositories.length} {t('desktop.chat.repoCount')}</div>
          <div ref={searchBoxWrapRef}>
            <Input
              size="small"
              prefix={<SearchOutlined style={{ color: textTertiary, fontSize: 12 }} />}
              suffix={searchLoading ? <LoadingOutlined style={{ color: textTertiary, fontSize: 12 }} /> : undefined}
              placeholder={t('desktop.chat.searchMessages')}
              value={searchQ}
              onChange={(e) => handleSearchChange(e.target.value)}
              onFocus={() => { if (searchQ.trim()) setSearchOpen(true); }}
              allowClear
            />
          </div>
          {searchOpen && (
            <div
              style={{
                position: 'absolute',
                top: 72,
                left: 8,
                right: 8,
                zIndex: 20,
                background: '#161b22',
                border: `1px solid ${borderColor}`,
                borderRadius: 8,
                boxShadow: '0 8px 24px rgba(0,0,0,0.4)',
                maxHeight: 320,
                overflowY: 'auto',
              }}
            >
              {searchResults.length === 0 ? (
                <div style={{ padding: '12px 14px', fontSize: 12, color: textTertiary }}>
                  {t('desktop.chat.searchNoResults')}
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
                      <span style={{ color: blueLight, fontWeight: 600 }}>{hit.sender_username}</span>
                      <span style={{ color: textTertiary }}>{hit.room_type === 'dm' ? '@' : '#'}{hit.room_name}</span>
                      <span style={{ color: textTertiary, marginLeft: 'auto' }}>{formatHitTime(hit.created_at)}</span>
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
        <div style={{ flex: 1, overflowY: 'auto', padding: '6px 0' }}>
          <div style={{ padding: '6px 16px', fontSize: 11, textTransform: 'uppercase', letterSpacing: 0.5, color: textTertiary, fontWeight: 600 }}>
            {t('desktop.chat.channels')}
          </div>
          {repositories.map((r) => {
            const isActive = activeRoom?.repository_id === r.id;
            const unread = unreadByRepo[r.id] ?? 0;
            return (
              <div
                key={r.id}
                onClick={() => { if (activeRoom?.repository_id !== r.id) void openChannel(r.id); }}
                style={{
                  display: 'flex', alignItems: 'center', gap: 8, padding: '6px 16px', cursor: 'pointer', fontSize: 13,
                  color: isActive ? textPrimary : textSecondary, background: isActive ? activeBg : 'transparent', transition: 'all 0.15s',
                }}
                onMouseEnter={(e) => { if (!isActive) e.currentTarget.style.background = hoverBg; }}
                onMouseLeave={(e) => { if (!isActive) e.currentTarget.style.background = 'transparent'; }}
              >
                {r.is_public ? <NumberOutlined style={{ opacity: 0.6, fontSize: 13 }} /> : <LockOutlined style={{ opacity: 0.6, fontSize: 13 }} />}
                <span style={{ flex: 1, minWidth: 0, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{r.name}</span>
                {unread > 0 && (
                  <span style={{ background: '#f85149', color: '#fff', fontSize: 10, fontWeight: 600, padding: '1px 6px', borderRadius: 10, flexShrink: 0 }}>
                    {unread}
                  </span>
                )}
              </div>
            );
          })}
          {repositories.length === 0 && (
            <div style={{ padding: 16, fontSize: 12, color: textTertiary, textAlign: 'center' }}>{t('desktop.chat.noChannels')}</div>
          )}

          <div style={{ padding: '12px 16px 4px', fontSize: 11, textTransform: 'uppercase', letterSpacing: 0.5, color: textTertiary, fontWeight: 600 }}>
            {t('desktop.chat.directMessages')}
          </div>
          {dms.length === 0 && dmLoaded && (
            <div style={{ padding: '4px 16px', fontSize: 12, color: textTertiary }}>{t('desktop.chat.noDMs')}</div>
          )}
          {dms.map((dm) => {
            const isActive = activeRoomId === dm.room_id;
            const dmName = dm.peer_username || dm.room_name;
            const dmInitials = getInitials(dmName);
            const dmColor = getAvatarColor(dmInitials);
            return (
              <div
                key={dm.room_id}
                onClick={() => handleDmClick(dm)}
                style={{
                  display: 'flex', alignItems: 'center', gap: 8, padding: '6px 16px', cursor: 'pointer',
                  color: isActive ? textPrimary : textSecondary, background: isActive ? activeBg : 'transparent', transition: 'all 0.15s',
                }}
                onMouseEnter={(e) => { if (!isActive) { e.currentTarget.style.background = hoverBg; e.currentTarget.style.color = textPrimary; } }}
                onMouseLeave={(e) => { if (!isActive) { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = textSecondary; } }}
              >
                <div style={{ position: 'relative' }}>
                  <Avatar size={22} style={{ background: dmColor, fontSize: 9, fontWeight: 600 }}>{dmInitials}</Avatar>
                  <span style={{
                    position: 'absolute', bottom: -1, right: -1, width: 8, height: 8, borderRadius: '50%',
                    background: onlineIds.has(dm.peer_user_id) ? green : '#6e7681', border: `2px solid ${bgSecondary}`,
                  }} />
                </div>
                <span style={{ flex: 1, fontSize: 13, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{dmName}</span>
                {dm.unread_count > 0 && (
                  <span style={{ background: '#f85149', color: '#fff', fontSize: 10, fontWeight: 600, padding: '1px 6px', borderRadius: 10, flexShrink: 0 }}>
                    {dm.unread_count}
                  </span>
                )}
              </div>
            );
          })}
        </div>
      </aside>

      {/* 中栏：会话 */}
      <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column' }}>
        {activeRoom ? (
          <>
            <div style={{ padding: '10px 20px', borderBottom: `1px solid ${borderColor}`, display: 'flex', alignItems: 'center', gap: 10, flexShrink: 0 }}>
              {activeRoom.repository_id ? <NumberOutlined style={{ color: textSecondary }} /> : <MessageOutlined style={{ color: textSecondary }} />}
              <b style={{ fontSize: 14, color: textPrimary }}>{activeRoom.name}</b>
              <span style={{ fontSize: 12, color: textTertiary }}>{onlineCount} {t('desktop.chat.onlineCount')}</span>
              <div style={{ marginLeft: 'auto', display: 'flex', gap: 6 }}>
                <button
                  className="icon-btn"
                  title={t('desktop.chat.searchMessages')}
                  onClick={focusSearch}
                  style={{ background: 'transparent', border: `1px solid ${borderColor}`, borderRadius: 6, color: textSecondary, cursor: 'pointer', padding: '3px 8px' }}
                >
                  <SearchOutlined />
                </button>
                <button
                  className={`icon-btn${showMembers ? ' on' : ''}`}
                  title={t('desktop.chat.members')}
                  onClick={() => setShowMembers((v) => !v)}
                  style={{ background: showMembers ? activeBg : 'transparent', border: `1px solid ${borderColor}`, borderRadius: 6, color: showMembers ? blueLight : textSecondary, cursor: 'pointer', padding: '3px 8px' }}
                >
                  <TeamOutlined />
                </button>
              </div>
            </div>
            <ChatMessages roomId={activeRoom.id} />
            <ChatComposer roomId={activeRoom.id} roomName={activeRoom.name} />
          </>
        ) : (
          <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: textTertiary, fontSize: 13 }}>
            {repositories.length === 0 ? t('desktop.chat.noChannels') : t('desktop.chat.selectChannel')}
          </div>
        )}
      </div>

      {/* 右栏：成员 */}
      {activeRoom && showMembers && (
        <aside style={{ width: 220, flexShrink: 0, background: bgSecondary, borderLeft: `1px solid ${borderColor}`, overflowY: 'auto', padding: 14 }}>
          <MemberGroup
            label={`${t('desktop.chat.online')} · ${onlineMembers.length}`}
            members={onlineMembers}
            onlineIds={onlineIds}
            meUserId={me?.id ?? null}
            onStartDm={(uid, uname) => void handleStartDm(uid, uname)}
          />
          <div style={{ marginTop: 12 }}>
            <MemberGroup
              label={`${t('desktop.chat.offline')} · ${offlineMembers.length}`}
              members={offlineMembers}
              onlineIds={onlineIds}
              meUserId={me?.id ?? null}
              onStartDm={(uid, uname) => void handleStartDm(uid, uname)}
            />
          </div>
        </aside>
      )}
    </div>
  );
}

function MemberGroup({ label, members, onlineIds, meUserId, onStartDm }: {
  label: string;
  members: Array<{ user_id: string; username: string; role: string }>;
  onlineIds: Set<string>;
  meUserId: string | null;
  onStartDm: (userId: string, username: string) => void;
}) {
  const { t } = useTranslation();
  return (
    <div>
      <div style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: 0.5, color: textTertiary, fontWeight: 600, marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
        <span style={{ width: 7, height: 7, borderRadius: '50%', background: label.startsWith(t('desktop.chat.online')) ? green : '#6e7681' }} />
        {label}
      </div>
      {members.length === 0 && <div style={{ fontSize: 12, color: textTertiary, padding: '2px 0' }}>—</div>}
      {members.map((m) => {
        const initials = getInitials(m.username || '?');
        const isSelf = meUserId != null && m.user_id === meUserId;
        return (
          <div key={m.user_id} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '5px 0', color: textSecondary }}>
            <div style={{ position: 'relative' }}>
              <Avatar size={26} style={{ background: getAvatarColor(initials), fontSize: 10, fontWeight: 600 }}>{initials}</Avatar>
              <span style={{
                position: 'absolute', bottom: -1, right: -1, width: 8, height: 8, borderRadius: '50%',
                background: onlineIds.has(m.user_id) ? green : '#6e7681', border: `2px solid ${bgSecondary}`,
              }} />
            </div>
            <span style={{ flex: 1, fontSize: 13, minWidth: 0, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              {m.username}
              {m.role === 'admin' && <Tag style={{ marginLeft: 6, fontSize: 10, lineHeight: '16px', padding: '0 6px' }}>{t('desktop.chat.roleAdmin')}</Tag>}
            </span>
            {!isSelf && (
              <button
                className="icon-btn"
                title={t('desktop.chat.newDm')}
                onClick={(e) => { e.stopPropagation(); onStartDm(m.user_id, m.username || m.user_id); }}
                style={{ background: 'transparent', border: `1px solid ${borderColor}`, borderRadius: 6, color: textTertiary, cursor: 'pointer', padding: '2px 7px', opacity: 0.7 }}
                onMouseEnter={(e) => { e.currentTarget.style.opacity = '1'; e.currentTarget.style.color = blueLight; }}
                onMouseLeave={(e) => { e.currentTarget.style.opacity = '0.7'; e.currentTarget.style.color = textTertiary; }}
              >
                <MessageOutlined style={{ fontSize: 12 }} />
              </button>
            )}
          </div>
        );
      })}
    </div>
  );
}