import { useEffect } from 'react';
import { Empty, Spin, Tooltip } from 'antd';
import {
  BellOutlined,
  DeleteOutlined,
  ForkOutlined,
  IssuesCloseOutlined,
  MessageOutlined,
  PullRequestOutlined,
  StarOutlined,
  TagOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { notificationsApi, type Notification } from '../../api/notifications';
import { repositoriesApi } from '../../api/repositories';
import { useNotificationsStore } from '../../stores/notifications';
import { useRepositoriesStore } from '../../stores/repositories';
import { useNavigationStore } from '../../stores/navigation';
import { useServersStore } from '../../stores/servers';
import { timeAgo } from '../../utils/time';

const borderColor = '#21262d';
const hoverBg = '#1c2333';
const textPrimary = '#e6edf3';
const textSecondary = '#8b949e';
const textTertiary = '#6e7681';
const blueLight = '#58a6ff';
const bgSecondary = '#161b22';

function typeIcon(n: Notification) {
  const type = `${n.type} ${n.target_type ?? ''}`.toLowerCase();
  if (type.includes('pr') || type.includes('pull')) return <PullRequestOutlined />;
  if (type.includes('issue')) return <IssuesCloseOutlined />;
  if (type.includes('release')) return <TagOutlined />;
  if (type.includes('star')) return <StarOutlined />;
  if (type.includes('fork')) return <ForkOutlined />;
  if (type.includes('mention') || type.includes('comment')) return <MessageOutlined />;
  return <BellOutlined />;
}

export default function NotificationsPanel({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation();
  const serverId = useServersStore((s) => s.currentServerId);
  const notifications = useNotificationsStore((s) => s.notifications);
  const unreadCount = useNotificationsStore((s) => s.unreadCount);
  const isLoading = useNotificationsStore((s) => s.isLoading);
  const fetchNotifications = useNotificationsStore((s) => s.fetchNotifications);
  const fetchUnreadCount = useNotificationsStore((s) => s.fetchUnreadCount);
  const markAsRead = useNotificationsStore((s) => s.markAsRead);
  const markAllAsRead = useNotificationsStore((s) => s.markAllAsRead);
  const remove = useNotificationsStore((s) => s.remove);
  const setPendingOpen = useRepositoriesStore((s) => s.setPendingOpen);
  const navigate = useNavigationStore((s) => s.navigate);

  useEffect(() => {
    void fetchNotifications();
    void fetchUnreadCount();
  }, [fetchNotifications, fetchUnreadCount]);

  // 跳转语义对齐 web 端 AppLayout：target_type 含 pr/pull → PR Tab，issue → Issues Tab，其余 → 仓库。
  const go = async (n: Notification) => {
    onClose();
    if (!n.is_read) {
      await markAsRead(n.id).catch(() => {});
    }
    if (!n.repository_id || !serverId) return;
    let repoPath: string | null = null;
    try {
      const repo = await repositoriesApi.get(serverId, n.repository_id);
      repoPath = repo.path;
    } catch {
      return;
    }
    const type = (n.target_type ?? '').toLowerCase();
    if (type.includes('pr') || type.includes('pull')) {
      setPendingOpen({ repoPath, tab: 'pullRequests' });
    } else if (type.includes('issue')) {
      setPendingOpen({ repoPath, tab: 'issues' });
    } else {
      setPendingOpen({ repoPath });
    }
    navigate('repositories');
  };

  return (
    <div style={{ width: 380, maxHeight: 460, display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 14px', borderBottom: `1px solid ${borderColor}` }}>
        <b style={{ fontSize: 13, color: textPrimary }}>{t('desktop.notifications.title')}</b>
        {unreadCount > 0 && (
          <span style={{ background: '#f85149', color: '#fff', fontSize: 10, fontWeight: 600, padding: '1px 7px', borderRadius: 10 }}>
            {t('desktop.notifications.unreadCount', { count: unreadCount })}
          </span>
        )}
        <button
          className="chat-add-reaction"
          onClick={() => { void markAllAsRead(); }}
          style={{ marginLeft: 'auto', background: 'transparent', border: 'none', color: blueLight, fontSize: 12, cursor: 'pointer', opacity: 1 }}
        >
          {t('desktop.notifications.markAllRead')}
        </button>
      </div>

      <div style={{ overflowY: 'auto' }}>
        {isLoading && notifications.length === 0 ? (
          <div style={{ padding: '32px 0', textAlign: 'center' }}><Spin /></div>
        ) : notifications.length === 0 ? (
          <Empty style={{ padding: '28px 0' }} description={t('desktop.notifications.empty')} image={Empty.PRESENTED_IMAGE_SIMPLE} />
        ) : (
          notifications.map((n) => (
            <div
              key={n.id}
              className="chat-msg"
              onClick={() => { void go(n); }}
              style={{
                display: 'flex', gap: 10, padding: '9px 14px', borderBottom: `1px solid ${borderColor}`, cursor: 'pointer',
                background: n.is_read ? 'transparent' : 'rgba(31,111,235,0.08)',
              }}
              onMouseEnter={(e) => { e.currentTarget.style.background = hoverBg; }}
              onMouseLeave={(e) => { e.currentTarget.style.background = n.is_read ? 'transparent' : 'rgba(31,111,235,0.08)'; }}
            >
              <span style={{ color: n.is_read ? textTertiary : blueLight, fontSize: 14, flexShrink: 0, marginTop: 1 }}>
                {typeIcon(n)}
              </span>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 13, fontWeight: n.is_read ? 400 : 600, color: textPrimary, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {n.title}
                </div>
                <div style={{ fontSize: 12, color: textSecondary, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {n.message}
                </div>
                <div style={{ fontSize: 11, color: textTertiary, marginTop: 2 }}>{timeAgo(n.created_at, t)}</div>
              </div>
              <div className="chat-delete-btn" style={{ display: 'flex', alignItems: 'center', flexShrink: 0 }}>
                <Tooltip title={t('desktop.notifications.delete')}>
                  <button
                    onClick={(e) => { e.stopPropagation(); void remove(n.id); }}
                    style={{ background: 'none', border: 'none', color: textTertiary, cursor: 'pointer', padding: 2, lineHeight: 1 }}
                    onMouseEnter={(e) => { e.currentTarget.style.color = '#f85149'; }}
                    onMouseLeave={(e) => { e.currentTarget.style.color = textTertiary; }}
                  >
                    <DeleteOutlined style={{ fontSize: 12 }} />
                  </button>
                </Tooltip>
              </div>
              {!n.is_read && (
                <span style={{ width: 7, height: 7, borderRadius: '50%', background: blueLight, flexShrink: 0, alignSelf: 'center' }} />
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
