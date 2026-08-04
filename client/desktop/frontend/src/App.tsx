import { useEffect, useState } from 'react';
import { ConfigProvider, App as AntApp, Button } from 'antd';
import { useTranslation } from 'react-i18next';
import { initGateway, useGatewayStore } from './stores/gateway';
import { useWorkspaceStore } from './stores/workspace';
import { useServersStore } from './stores/servers';
import { listWorkspaces } from './api/workspaces';
import { perseusTheme } from './styles/theme';
import Welcome from './views/Welcome';
import IdeShell from './layouts/IdeShell';
import ServerShell from './layouts/ServerShell';
import './styles/desktop.css';

export default function App() {
  const { t } = useTranslation();
  const ready = useGatewayStore((s) => s.ready);
  const current = useWorkspaceStore((s) => s.current);
  const currentServerId = useServersStore((s) => s.currentServerId);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    initGateway()
      .then(() => Promise.all([listWorkspaces(), useServersStore.getState().fetchServers()]))
      .then(([list]) => useWorkspaceStore.getState().setWorkspaces(list))
      .catch((e) => setError(String(e)));
  }, []);

  let body: React.ReactNode;
  if (error) {
    body = (
      <div style={{ padding: 24 }}>
        <div>{t('desktop.app.gatewayError', { error })}</div>
        <Button onClick={() => window.location.reload()}>{t('desktop.app.retry')}</Button>
      </div>
    );
  } else if (!ready) {
    body = <div style={{ padding: 24 }}>{t('desktop.app.connecting')}</div>;
  } else if (current) {
    body = <IdeShell workspace={current} />;
  } else if (currentServerId) {
    body = <ServerShell />;
  } else {
    body = <Welcome />;
  }

  return (
    <ConfigProvider theme={perseusTheme}>
      <AntApp>{body}</AntApp>
    </ConfigProvider>
  );
}
