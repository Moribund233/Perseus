import { useEffect, useState } from 'react';
import { ConfigProvider, App as AntApp, Spin } from 'antd';
import { initGateway, useGatewayStore } from './stores/gateway';
import { useWorkspaceStore } from './stores/workspace';
import { useServersStore } from './stores/servers';
import { useNavigationStore } from './stores/navigation';
import { listWorkspaces } from './api/workspaces';
import { perseusTheme } from './styles/theme';
import PortalShell from './layouts/PortalShell';
import IdeShell from './layouts/IdeShell';
import ErrorPage from './views/ErrorPage';
import './styles/desktop.css';

export default function App() {
  const ready = useGatewayStore((s) => s.ready);
  const current = useWorkspaceStore((s) => s.current);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    initGateway()
      .then(() => Promise.all([listWorkspaces(), useServersStore.getState().fetchServers()]))
      .then(([list]) => {
        useWorkspaceStore.getState().setWorkspaces(list);
        // 已有持久化服务器时直接进入仓库门户，否则停留在启动台。
        if (useServersStore.getState().currentServerId) {
          useNavigationStore.getState().navigate('repositories');
        }
      })
      .catch((e) => setError(String(e)));
  }, []);

  let body: React.ReactNode;
  if (error) {
    body = <ErrorPage error={error} />;
  } else if (!ready) {
    body = (
      <div className="app-boot">
        <Spin size="large" />
      </div>
    );
  } else if (current) {
    body = <IdeShell workspace={current} />;
  } else {
    body = <PortalShell />;
  }

  return (
    <ConfigProvider theme={perseusTheme}>
      <AntApp>{body}</AntApp>
    </ConfigProvider>
  );
}
