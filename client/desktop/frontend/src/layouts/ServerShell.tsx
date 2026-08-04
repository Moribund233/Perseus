import { useEffect, useState } from 'react';
import { Button, Dropdown, Space, Tag, App as AntApp } from 'antd';
import { useTranslation } from 'react-i18next';
import { ArrowLeftOutlined, CloudServerOutlined, ReloadOutlined, SettingOutlined } from '@ant-design/icons';
import { useServersStore } from '../stores/servers';
import ServerManager from '../views/servers/ServerManager';
import RepositoriesView from '../views/repositories/RepositoriesView';
import { useRepositoriesStore } from '../stores/repositories';

const healthColor: Record<string, string> = { online: 'success', offline: 'error', unknown: 'default' };

export default function ServerShell() {
  const { t } = useTranslation();
  const { message } = AntApp.useApp();
  const servers = useServersStore((s) => s.servers);
  const currentServerId = useServersStore((s) => s.currentServerId);
  const setCurrent = useServersStore((s) => s.setCurrent);
  const setServers = useServersStore((s) => s.setServers);
  const refreshHealth = useServersStore((s) => s.refreshHealth);
  const [view, setView] = useState<'repositories' | 'manager'>('repositories');

  const current = servers.find((s) => s.id === currentServerId) ?? null;
  // 无法解析的 currentServerId（如从 Welcome 直达管理页）→ 直接显示管理器。
  const showManager = view === 'manager' || (!!currentServerId && !current);

  useEffect(() => {
    useServersStore.getState().fetchServers();
  }, [setServers]);

  const refresh = async () => {
    if (!currentServerId) return;
    const updated = await refreshHealth(currentServerId);
    if (updated) message.success(`${updated.name}: ${t(`desktop.servers.health.${updated.health}`)}`);
  };

  const serverMenu = {
    items: [
      ...servers.map((s) => ({
        key: s.id,
        label: (
          <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Tag color={healthColor[s.health]} style={{ marginInlineEnd: 0 }}>{s.name}</Tag>
          </span>
        ),
      })),
      { type: 'divider' as const },
      { key: 'manage', label: t('desktop.serverShell.manageServers') },
    ],
    onClick: (info: { key: string }) => {
      if (info.key === 'manage') setView('manager');
      else if (info.key !== currentServerId) setCurrent(info.key);
    },
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <header style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '10px 16px', borderBottom: '1px solid #21262d', flexShrink: 0 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => setCurrent(null)}>
          {t('desktop.serverShell.backWorkspace')}
        </Button>
        <CloudServerOutlined style={{ color: '#58a6ff', fontSize: 16 }} />
        {current ? (
          <>
            <Dropdown menu={serverMenu}>
              <Button type="text" style={{ fontWeight: 600 }}>
                {current.name}
              </Button>
            </Dropdown>
            <Tag color={healthColor[current.health]}>{t(`desktop.servers.health.${current.health}`)}</Tag>
            <Button
              icon={<ReloadOutlined />}
              size="small"
              onClick={refresh}
              disabled={current.health === 'offline'}
            >
              {t('desktop.servers.refresh')}
            </Button>
          </>
        ) : (
          <span className="muted">{t('desktop.serverShell.noServerSelected')}</span>
        )}
        <Button
          style={{ marginLeft: 'auto' }}
          icon={<SettingOutlined />}
          onClick={() => setView(view === 'manager' ? 'repositories' : 'manager')}
        >
          {t('desktop.serverShell.manageServers')}
        </Button>
      </header>

      <main style={{ flex: 1, overflow: 'auto', minHeight: 0 }}>
        {showManager ? (
          <ServerManager />
        ) : current ? (
          <RepositoriesView />
        ) : (
          <div style={{ padding: 40, textAlign: 'center', color: '#8b949e' }}>
            {t('desktop.serverShell.noServerSelected')}
            <div style={{ marginTop: 12 }}>
              <Button type="primary" onClick={() => setView('manager')}>
                {t('desktop.serverShell.manageServers')}
              </Button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}