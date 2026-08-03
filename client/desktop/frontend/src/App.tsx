import { useEffect, useState } from 'react';
import { Button } from 'antd';
import { initGateway, useGatewayStore } from './stores/gateway';
import { useWorkspaceStore } from './stores/workspace';
import { listWorkspaces } from './api/workspaces';
import Welcome from './views/Welcome';
import IdeShell from './layouts/IdeShell';
import './styles/desktop.css';

export default function App() {
  const ready = useGatewayStore((s) => s.ready);
  const current = useWorkspaceStore((s) => s.current);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    initGateway()
      .then(() => listWorkspaces())
      .then((list) => useWorkspaceStore.getState().setWorkspaces(list))
      .catch((e) => setError(String(e)));
  }, []);

  if (error) {
    return (
      <div style={{ padding: 24 }}>
        <div>网关初始化失败：{error}</div>
        <Button onClick={() => window.location.reload()}>重试</Button>
      </div>
    );
  }

  if (!ready) return <div style={{ padding: 24 }}>正在连接本地网关…</div>;

  return current ? <IdeShell workspace={current} /> : <Welcome />;
}
