import { useEffect, useState } from 'react';
import { Button, Empty, Input, List, Checkbox, Space, message as antdMessage } from 'antd';
import { useTranslation } from 'react-i18next';
import { DownloadOutlined, UploadOutlined } from '@ant-design/icons';
import { gitStatus, gitAdd, gitCommit, gitPush, gitPull, GitStatus } from '../../api/workspaces';
import { useGitStore } from '../../stores/git';

export default function GitPanel({ workspaceId }: { workspaceId: string }) {
  const { t } = useTranslation();
  const status = useGitStore((s) => s.status);
  const setStatus = useGitStore((s) => s.setStatus);
  const [message, setMessage] = useState('');
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [busy, setBusy] = useState<'push' | 'pull' | null>(null);

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

  // push/pull 的凭据由网关按 remote URL 自动匹配注册表服务器 token (credentials.go)
  const push = async () => {
    setBusy('push');
    try {
      await gitPush(workspaceId, { branch: status?.branch });
      antdMessage.success(t('desktop.git.pushOk', { defaultValue: 'Push 成功' }));
      await refresh();
    } catch (e) {
      antdMessage.error(t('desktop.git.pushFail', { defaultValue: 'Push 失败' }) + `: ${(e as Error).message}`);
    } finally {
      setBusy(null);
    }
  };

  const pull = async () => {
    setBusy('pull');
    try {
      await gitPull(workspaceId, { branch: status?.branch });
      antdMessage.success(t('desktop.git.pullOk', { defaultValue: 'Pull 成功' }));
      await refresh();
    } catch (e) {
      antdMessage.error(t('desktop.git.pullFail', { defaultValue: 'Pull 失败' }) + `: ${(e as Error).message}`);
    } finally {
      setBusy(null);
    }
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
      <Space wrap>
        <Button size="small" onClick={stage}>{t('desktop.git.stage')}</Button>
        <Button size="small" type="primary" disabled={!message.trim()} onClick={commit}>{t('desktop.git.commit')}</Button>
        <Button size="small" icon={<UploadOutlined />} loading={busy === 'push'} onClick={push}>
          {t('desktop.git.push', { defaultValue: 'Push' })}
          {status.ahead > 0 ? ` (${status.ahead})` : ''}
        </Button>
        <Button size="small" icon={<DownloadOutlined />} loading={busy === 'pull'} onClick={pull}>
          {t('desktop.git.pull', { defaultValue: 'Pull' })}
          {status.behind > 0 ? ` (${status.behind})` : ''}
        </Button>
      </Space>
    </div>
  );
}
