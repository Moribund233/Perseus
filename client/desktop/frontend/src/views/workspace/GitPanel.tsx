import { useEffect, useState } from 'react';
import { Button, Input, List, Checkbox, Space } from 'antd';
import { gitStatus, gitAdd, gitCommit, GitStatus } from '../../api/workspaces';
import { useGitStore } from '../../stores/git';

export default function GitPanel({ workspaceId }: { workspaceId: string }) {
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

  if (!status) return <div>加载状态…</div>;

  return (
    <div className="git-panel">
      <div className="git-branch">分支: {status.branch} ({status.ahead}↑ {status.behind}↓)</div>
      <Checkbox.Group
        value={[...selected]}
        onChange={(vals) => setSelected(new Set(vals as string[]))}
      >
        <List
          size="small"
          dataSource={[...status.modified.map((m) => m.path), ...status.untracked]}
          renderItem={(p) => (
            <List.Item><Checkbox value={p}>{p}</Checkbox></List.Item>
          )}
        />
      </Checkbox.Group>
      <Input.TextArea rows={3} placeholder="提交信息" value={message} onChange={(e) => setMessage(e.target.value)} />
      <Space>
        <Button size="small" onClick={stage}>暂存</Button>
        <Button size="small" type="primary" disabled={!message.trim()} onClick={commit}>提交</Button>
      </Space>
    </div>
  );
}
