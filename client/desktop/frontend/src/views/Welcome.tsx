import { useState } from 'react';
import { Button, Card, Empty, Input, List, Space } from 'antd';
import { FolderOpenOutlined } from '@ant-design/icons';
import { createWorkspace, listWorkspaces, Workspace } from '../api/workspaces';
import { useWorkspaceStore } from '../stores/workspace';

export default function Welcome() {
  const workspaces = useWorkspaceStore((s) => s.workspaces);
  const setWorkspaces = useWorkspaceStore((s) => s.setWorkspaces);
  const setCurrent = useWorkspaceStore((s) => s.setCurrent);
  const [url, setUrl] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const openFolder = async () => {
    const dir = await window.go?.main.App.OpenFolderDialog();
    if (!dir) return;
    setBusy(true);
    try {
      await createWorkspace({ name: dir.split(/[\\/]/).pop() ?? 'ws', path: dir });
      setWorkspaces(await listWorkspaces());
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };

  const clone = async () => {
    if (!url.trim()) return;
    setBusy(true);
    try {
      const name = url.split('/').pop()?.replace(/\.git$/, '') ?? 'repo';
      await createWorkspace({ name, path: '', url: url.trim(), clone: true });
      setWorkspaces(await listWorkspaces());
      setUrl('');
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="welcome">
      <h2>欢迎使用 Perseus Desktop</h2>
      <Space direction="vertical" size="middle" style={{ width: 520 }}>
        <Card title="打开本地目录">
          <Button icon={<FolderOpenOutlined />} loading={busy} onClick={openFolder}>
            选择文件夹
          </Button>
        </Card>
        <Card title="Clone 仓库（手动 URL）">
          <Space.Compact style={{ width: '100%' }}>
            <Input
              placeholder="https://server/owner/repo.git 或 git@host:owner/repo.git"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              onPressEnter={clone}
            />
            <Button type="primary" loading={busy} onClick={clone}>
              Clone
            </Button>
          </Space.Compact>
        </Card>
        {error && <div className="error-text">{error}</div>}
        <Card title="最近工作区">
          {workspaces.length === 0 ? (
            <Empty description="还没有工作区" />
          ) : (
            <List
              dataSource={workspaces}
              renderItem={(ws: Workspace) => (
                <List.Item actions={[<Button size="small" onClick={() => setCurrent(ws)}>打开</Button>]}>
                  {ws.name} <span className="muted">{ws.path}</span>
                </List.Item>
              )}
            />
          )}
        </Card>
      </Space>
    </div>
  );
}
