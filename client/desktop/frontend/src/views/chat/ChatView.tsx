import { useEffect, useMemo, useState } from 'react';
import { Avatar, Input, Tag } from 'antd';
import {
  LockOutlined,
  NumberOutlined,
  SearchOutlined,
  TeamOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useRepositoriesStore } from '../../stores/repositories';
import { useChatStore } from '../../stores/chat';
import { useServersStore } from '../../stores/servers';
import { useIdentityStore } from '../../stores/identity';
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
const green = '#3fb950';

export default function ChatView() {
  const { t } = useTranslation();
  const server = useServersStore((s) => s.servers.find((x) => x.id === s.currentServerId));
  const me = useIdentityStore((s) => s.me);
  const repositories = useRepositoriesStore((s) => s.repositories);
  const fetchRepositories = useRepositoriesStore((s) => s.fetchRepositories);

  const rooms = useChatStore((s) => s.rooms);
  const messages = useChatStore((s) => s.messages);
  const members = useChatStore((s) => s.members);
  const onlineUsers = useChatStore((s) => s.onlineUsers);
  const unreadByRepo = useChatStore((s) => s.unreadByRepo);
  const activeRoomId = useChatStore((s) => s.activeRoomId);
  const status = useChatStore((s) => s.status);
  const start = useChatStore((s) => s.start);
  const openChannel = useChatStore((s) => s.openChannel);
  const setActiveRoom = useChatStore((s) => s.setActiveRoom);

  const [filter, setFilter] = useState('');
  const [showMembers, setShowMembers] = useState(true);

  // socket 常驻（对齐终端语义）：只 start 不 stop，切服务器时由 reset 统一清理。
  useEffect(() => {
    start();
  }, [start]);

  useEffect(() => {
    fetchRepositories();
  }, [fetchRepositories]);

  useEffect(() => {
    void useChatStore.getState().fetchChatRooms();
  }, []);

  // 自动选中第一个频道。
  useEffect(() => {
    if (!activeRoomId && repositories.length > 0) {
      void openChannel(repositories[0].id);
    }
  }, [activeRoomId, repositories, openChannel]);

  const activeRoom = useMemo(
    () => rooms.find((r) => r.id === activeRoomId) ?? null,
    [rooms, activeRoomId],
  );

  const filtered = useMemo(() => {
    const q = filter.trim().toLowerCase();
    if (!q) return repositories;
    return repositories.filter((r) => r.name.toLowerCase().includes(q));
  }, [repositories, filter]);

  const roomMembers = activeRoomId ? members[activeRoomId] ?? [] : [];
  const onlineIds = useMemo(
    () => new Set((activeRoomId ? onlineUsers[activeRoomId] ?? [] : []).map((u) => u.user_id)),
    [onlineUsers, activeRoomId],
  );
  const onlineMembers = roomMembers.filter((m) => onlineIds.has(m.user_id));
  const offlineMembers = roomMembers.filter((m) => !onlineIds.has(m.user_id));
  const onlineCount = new Set([...onlineIds, me?.id].filter(Boolean)).size;

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
    <div style={{ height: '100%', display: 'flex', background: '#0d1117' }}>
      {/* 左栏：频道 */}
      <aside style={{ width: 240, flexShrink: 0, background: bgSecondary, borderRight: `1px solid ${borderColor}`, display: 'flex', flexDirection: 'column' }}>
        <div style={{ padding: 14, borderBottom: `1px solid ${borderColor}` }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
            <b style={{ fontSize: 13, color: textPrimary }}>{t('desktop.chat.title')}</b>
            {statusPill}
          </div>
          <div style={{ fontSize: 11, color: textTertiary, marginBottom: 10 }}>{server.name} · {repositories.length} {t('desktop.chat.repoCount')}</div>
          <Input
            size="small"
            prefix={<SearchOutlined style={{ color: textTertiary, fontSize: 12 }} />}
            placeholder={t('desktop.chat.searchChannels')}
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            allowClear
          />
        </div>
        <div style={{ flex: 1, overflowY: 'auto', padding: '6px 0' }}>
          <div style={{ padding: '6px 16px', fontSize: 11, textTransform: 'uppercase', letterSpacing: 0.5, color: textTertiary, fontWeight: 600 }}>
            {t('desktop.chat.channels')}
          </div>
          {filtered.map((r) => {
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
          {filtered.length === 0 && (
            <div style={{ padding: 16, fontSize: 12, color: textTertiary, textAlign: 'center' }}>{t('desktop.chat.noChannels')}</div>
          )}
        </div>
      </aside>

      {/* 中栏：会话 */}
      <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column' }}>
        {activeRoom ? (
          <>
            <div style={{ padding: '10px 20px', borderBottom: `1px solid ${borderColor}`, display: 'flex', alignItems: 'center', gap: 10, flexShrink: 0 }}>
              <NumberOutlined style={{ color: textSecondary }} />
              <b style={{ fontSize: 14, color: textPrimary }}>{activeRoom.name}</b>
              <span style={{ fontSize: 12, color: textTertiary }}>{onlineCount} {t('desktop.chat.onlineCount')}</span>
              <div style={{ marginLeft: 'auto' }}>
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
          <MemberGroup label={`${t('desktop.chat.online')} · ${onlineMembers.length}`} members={onlineMembers} onlineIds={onlineIds} />
          <div style={{ marginTop: 12 }}>
            <MemberGroup label={`${t('desktop.chat.offline')} · ${offlineMembers.length}`} members={offlineMembers} onlineIds={onlineIds} />
          </div>
        </aside>
      )}
    </div>
  );
}

function MemberGroup({ label, members, onlineIds }: {
  label: string;
  members: Array<{ user_id: string; username: string; role: string }>;
  onlineIds: Set<string>;
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
          </div>
        );
      })}
    </div>
  );
}
