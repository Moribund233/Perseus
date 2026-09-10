import { useEffect, useState } from 'react';
import { App as AntApp, Avatar, Badge, Button, Dropdown, Tag, Tooltip } from 'antd';
import { useTranslation } from 'react-i18next';
import {
  ArrowLeftOutlined,
  BellOutlined,
  CloudServerOutlined,
  ReloadOutlined,
  SearchOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import { useNavigationStore } from '../stores/navigation';
import { useServersStore } from '../stores/servers';
import { useIdentityStore } from '../stores/identity';
import { useNotificationsStore } from '../stores/notifications';
import { useRepositoriesStore } from '../stores/repositories';
import { useGatewayStore } from '../stores/gateway';
import { getAvatarColor, getInitials } from '../utils/avatar';
import Brand from '../components/Brand';
import WindowControls from '../components/WindowControls';
import Welcome from '../views/Welcome';
import ServerManager from '../views/servers/ServerManager';
import RepositoriesView from '../views/repositories/RepositoriesView';
import GlobalSearchView from '../views/GlobalSearchView';
import Settings from '../views/Settings';

const healthTag: Record<string, 'success' | 'error' | 'default'> = { online: 'success', offline: 'error', unknown: 'default' };

const CRUMB_KEYS: Record<string, string> = {
  welcome: 'desktop.portal.crumb.welcome',
  repositories: 'desktop.portal.crumb.repositories',
  servers: 'desktop.portal.crumb.servers',
  settings: 'desktop.portal.crumb.settings',
};

export default function PortalShell() {
  const { t } = useTranslation();
  const { message } = AntApp.useApp();
  const view = useNavigationStore((s) => s.view);
  const navigate = useNavigationStore((s) => s.navigate);
  const servers = useServersStore((s) => s.servers);
  const currentServerId = useServersStore((s) => s.currentServerId);
  const setCurrent = useServersStore((s) => s.setCurrent);
  const refreshHealth = useServersStore((s) => s.refreshHealth);
  const me = useIdentityStore((s) => s.me);
  const fetchIdentity = useIdentityStore((s) => s.fetchIdentity);
  const clearIdentity = useIdentityStore((s) => s.clear);
  const unreadCount = useNotificationsStore((s) => s.unreadCount);
  const fetchUnreadCount = useNotificationsStore((s) => s.fetchUnreadCount);
  const clearCurrentRepo = useRepositoriesStore((s) => s.clearCurrent);

  const current = servers.find((s) => s.id === currentServerId) ?? null;

  useEffect(() => {
    if (currentServerId) {
      fetchIdentity();
    } else {
      clearIdentity();
    }
  }, [currentServerId, fetchIdentity, clearIdentity]);

  useEffect(() => {
    if (view === 'repositories' && currentServerId) {
      void fetchUnreadCount();
    }
  }, [view, currentServerId, fetchUnreadCount]);

  // 切换服务器后清空仓库详情状态，避免串库。
  useEffect(() => {
    clearCurrentRepo();
  }, [currentServerId, clearCurrentRepo]);

  const identityName = me?.full_name || me?.username;
  const identityInitials = identityName ? getInitials(identityName) : '?';

  const onBack = () => navigate('welcome');

  const serverMenu = {
    items: [
      ...servers.map((s) => ({
        key: s.id,
        label: (
          <span className="dd-srv-item">
            <span className={`dot ${s.health}`} />
            <b>{s.name}</b>
            <Tag color={healthTag[s.health]}>{t(`desktop.servers.health.${s.health}`)}</Tag>
            {s.id === currentServerId && <span className="current-chip">{t('desktop.welcome.serverRowCurrent')}</span>}
          </span>
        ),
      })),
      { type: 'divider' as const },
      {
        key: 'manage',
        label: (
          <span className="dd-srv-item">
            <SettingOutlined />
            <span>{t('desktop.portal.manageServers')}</span>
          </span>
        ),
      },
    ],
    onClick: (info: { key: string }) => {
      if (info.key === 'manage') {
        navigate('servers');
      } else if (info.key !== currentServerId) {
        setCurrent(info.key);
      }
    },
  };

  const retry = async () => {
    if (!currentServerId) return;
    const updated = await refreshHealth(currentServerId);
    if (updated?.health === 'online') {
      message.success(`${updated.name}: ${t('desktop.servers.health.online')}`);
    }
  };

  const phase2 = () => message.info(t('desktop.portal.phase2'));

  const [searchOpen, setSearchOpen] = useState(false);

  // 双击标题栏空白/拖拽区 = 最大化/还原（交互控件上不触发）。
  const onTitlebarDblClick = (e: React.MouseEvent) => {
    if ((e.target as HTMLElement).closest('button, input, a, .win-controls, .avatar, .ant-avatar')) return;
    window.runtime?.WindowToggleMaximise();
  };

  const showOfflineBanner = view === 'repositories' && !!current && current.health === 'offline';

  let content: React.ReactNode;
  switch (view) {
    case 'repositories':
      content = current ? (
        <RepositoriesView key={currentServerId} />
      ) : (
        <div className="portal-empty">
          <CloudServerOutlined />
          <span>{t('desktop.serverShell.noServerSelected')}</span>
          <Button type="primary" onClick={() => navigate('servers')}>
            {t('desktop.serverShell.manageServers')}
          </Button>
        </div>
      );
      break;
    case 'servers':
      content = <ServerManager />;
      break;
    case 'settings':
      content = <Settings />;
      break;
    default:
      content = <Welcome />;
  }

  return (
    <div className="portal">
      <header className="titlebar" onDoubleClick={onTitlebarDblClick}>
        {view === 'welcome' ? (
          <>
            <span className="tb-brand">
              <Brand />
              <span className="tb-app">{t('desktop.app.name')}</span>
            </span>
            <span className="tb-sep" />
            <span className="tb-crumb">{t(CRUMB_KEYS.welcome)}</span>
            <div className="tb-right">
              <WindowControls />
            </div>
          </>
        ) : (
          <>
            <button className="tb-back" onClick={onBack}>
              <ArrowLeftOutlined />
              {t('desktop.serverShell.backWorkspace')}
            </button>
            <span className="tb-sep" />
            {view === 'repositories' && current && (
              <div className="tb-server">
                <Dropdown menu={serverMenu} trigger={['click']} placement="bottomLeft">
                  <button className="tb-server-btn">
                    <span className={`dot ${current.health}`} />
                    {current.name}
                    <span className="tb-chev">{'\u203A'}</span>
                  </button>
                </Dropdown>
              </div>
            )}
            <span className="tb-crumb">{t(CRUMB_KEYS[view])}</span>
            <div className="tb-right">
              {view === 'repositories' && current && (
                <Tooltip title={t('desktop.portal.searchPlaceholder')}>
                  <button className="tb-search" onClick={() => setSearchOpen(true)}>
                    <SearchOutlined />
                    {t('desktop.portal.searchPlaceholder')}
                    <kbd>{t('desktop.portal.searchKbd')}</kbd>
                  </button>
                </Tooltip>
              )}
              {view === 'repositories' && current && (
                <Tooltip title={t('desktop.portal.notifications')}>
                  <button className="tb-icon" onClick={phase2}>
                    <Badge count={unreadCount} size="small" offset={[2, -2]}>
                      <BellOutlined />
                    </Badge>
                  </button>
                </Tooltip>
              )}
              {view === 'repositories' && me && (
                <Avatar size={24} className="tb-avatar" style={{ background: getAvatarColor(identityInitials) }}>
                  {identityInitials}
                </Avatar>
              )}
              <WindowControls />
            </div>
          </>
        )}
      </header>

      {showOfflineBanner && current && (
        <div className="offline-banner">
          <ReloadOutlined />
          <span>
            <b>{t('desktop.portal.offlineBanner', { name: current.name })}</b>
          </span>
          <Button className="banner-action" size="small" ghost onClick={retry}>
            {t('desktop.portal.retry')}
          </Button>
        </div>
      )}

      <main className="portal-main">{content}</main>

      <GlobalSearchView open={searchOpen} onClose={() => setSearchOpen(false)} />
    </div>
  );
}