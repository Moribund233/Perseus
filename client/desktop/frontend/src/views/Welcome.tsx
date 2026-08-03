import { useState } from 'react';
import { Button, Card, Empty, Input, List, Space } from 'antd';
import { FolderOpenOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { createWorkspace, listWorkspaces, Workspace } from '../api/workspaces';
import { useWorkspaceStore } from '../stores/workspace';

export default function Welcome() {
  const { t } = useTranslation();
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
      <h2>{t('desktop.app.welcomeTitle')}</h2>
      <Space direction="vertical" size="middle" style={{ width: 520 }}>
        <Card title={t('desktop.welcome.openLocal')}>
          <Button icon={<FolderOpenOutlined />} loading={busy} onClick={openFolder}>
            {t('desktop.welcome.chooseFolder')}
          </Button>
        </Card>
        <Card title={t('desktop.welcome.cloneTitle')}>
          <Space.Compact style={{ width: '100%' }}>
            <Input
              placeholder={t('desktop.welcome.clonePlaceholder')}
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              onPressEnter={clone}
            />
            <Button type="primary" loading={busy} onClick={clone}>
              {t('desktop.welcome.clone')}
            </Button>
          </Space.Compact>
        </Card>
        {error && <div className="error-text">{error}</div>}
        <Card title={t('desktop.welcome.recent')}>
          {workspaces.length === 0 ? (
            <Empty description={t('desktop.welcome.noWorkspaces')} />
          ) : (
            <List
              dataSource={workspaces}
              renderItem={(ws: Workspace) => (
                <List.Item actions={[<Button size="small" onClick={() => setCurrent(ws)}>{t('desktop.welcome.open')}</Button>]}>
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
