import { useEffect, useState } from 'react';
import { Button, Empty, Input, List, Checkbox, Space } from 'antd';
import { useTranslation } from 'react-i18next';
import { gitStatus, gitAdd, gitCommit, GitStatus } from '../../api/workspaces';
import { useGitStore } from '../../stores/git';

export default function GitPanel({ workspaceId }: { workspaceId: string }) {
  const { t } = useTranslation();
  const status = useGitStore((s) => s.status);
  const setStatus = useGitStore((s) => s.setStatus);
  const [message, setMessage] = useState('');
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const refresh = async () => {
    const s = await gitStatus(workspaceId);
    setStatus(s);
    if (!s) return;
    const all = [...s.modified.map((m) => m.path), ...s.untracked];
    setSelected(new Set(all));
  };

  useEffect(() => { refresh().catch(console.error); }, [workspaceId]);

  const stage = async () => {
    await gitAdd(workspaceId, [...selected]);
    await refresh();
  };

  const commit = async () => {
    await gitCommit(workspaceId, message);
    setMessage('');
    await refresh();
  };

  if (!status) return <div>{t('desktop.git.loading')}</div>;

  const changes = [...status.modified.map((m) => m.path), ...status.untracked];

  return (
    <div className="git-panel">
      <div className="git-branch">{t('desktop.git.branch', { branch: status.branch, ahead: status.ahead, behind: status.behind })}</div>
      {changes.length === 0 ? (
        <Empty description={t('desktop.git.noChanges')} />
      ) : (
        <Checkbox.Group
          value={[...selected]}
          onChange={(vals) => setSelected(new Set(vals as string[]))}
        >
          <List
            size="small"
            dataSource={changes}
            renderItem={(p) => (
              <List.Item><Checkbox value={p}>{p}</Checkbox></List.Item>
            )}
          />
        </Checkbox.Group>
      )}
      <Input.TextArea rows={3} placeholder={t('desktop.git.commitMessage')} value={message} onChange={(e) => setMessage(e.target.value)} />
      <Space>
        <Button size="small" onClick={stage}>{t('desktop.git.stage')}</Button>
        <Button size="small" type="primary" disabled={!message.trim()} onClick={commit}>{t('desktop.git.commit')}</Button>
      </Space>
    </div>
  );
}
