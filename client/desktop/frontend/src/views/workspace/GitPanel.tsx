import { useCallback, useEffect, useState } from 'react';
import { message } from 'antd';
import {
  BranchesOutlined,
  UpOutlined,
  DownOutlined,
  FileTextOutlined,
  UndoOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import {
  gitStatus, gitAdd, gitCommit, gitPush, gitPull, type GitStatus,
} from '../../api/workspaces';
import { useGitStore } from '../../stores/git';
import { logGit } from '../../stores/logs';

interface Props {
  workspaceId: string;
  onOpenDiff: (path: string) => void;
}

function statusChip(status: GitStatus): Array<{ x: string; path: string }> {
  const seen = new Set<string>();
  const out: Array<{ x: string; path: string }> = [];
  for (const s of status.modified) {
    if (seen.has(s.path)) continue;
    seen.add(s.path);
    out.push({ x: status.staged.some((st) => st.path === s.path) ? 'A' : 'M', path: s.path });
  }
  for (const p of status.untracked) {
    if (seen.has(p)) continue;
    seen.add(p);
    out.push({ x: 'U', path: p });
  }
  return out;
}

export default function GitPanel({ workspaceId, onOpenDiff }: Props) {
  const { t } = useTranslation();
  const status = useGitStore((s) => s.status);
  const setStatus = useGitStore((s) => s.setStatus);
  const [msg, setMsg] = useState('');
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [busy, setBusy] = useState<'none' | 'push' | 'pull' | 'commit' | 'stage'>('none');

  const refresh = useCallback(async () => {
    const s = await gitStatus(workspaceId);
    setStatus(s);
    if (!s) return;
  }, [workspaceId, setStatus]);

  useEffect(() => {
    refresh().catch(() => logGit(t('desktop.log.gitFail', { defaultValue: 'git status 失败' })));
  }, [workspaceId, refresh, t]);

  const run = async (act: () => Promise<unknown>, flag: Exclude<typeof busy, 'none'>, okText: string) => {
    setBusy(flag);
    try {
      await act();
      message.success(okText);
      await refresh();
    } catch (e) {
      message.error(`${okText} 失败: ${(e as Error).message}`);
    } finally {
      setBusy('none');
    }
  };

  const stageAll = () => {
    const all = status ? [...status.modified.map((m) => m.path), ...status.untracked] : [];
    setSelected(new Set(all));
    void run(() => gitAdd(workspaceId, all), 'stage', t('desktop.git.stagedAll', { defaultValue: '已暂存全部更改' }));
  };

  const commit = () => {
    const targets = selected.size ? [...selected] : [];
    if (!msg.trim() || targets.length === 0) return;
    void run(async () => {
      await gitAdd(workspaceId, targets);
      await gitCommit(workspaceId, msg.trim());
      setMsg('');
    }, 'commit', t('desktop.git.commitOk', { defaultValue: '提交成功' }));
  };

  const push = () => {
    void run(
      () => gitPush(workspaceId, { branch: status?.branch }),
      'push',
      t('desktop.git.pushOk', { defaultValue: 'Push 成功' }),
    );
  };

  const pull = () => {
    void run(
      () => gitPull(workspaceId, { branch: status?.branch }),
      'pull',
      t('desktop.git.pullOk', { defaultValue: 'Pull 成功' }),
    );
  };

  if (!status) {
    return (
      <div className="sb-pane on gitpane" data-pane="git">
        <div className="git-hint">{t('desktop.git.loading')}</div>
      </div>
    );
  }

  const changes = statusChip(status);

  const toggle = (path: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
  };

  return (
    <div className="sb-pane on gitpane" data-pane="git">
      <div className="sb-head">
        {t('desktop.git.title', { defaultValue: '源代码管理' })}
        <span className="right">
          <button className="icon-btn sm" title={t('desktop.git.stageAllTitle', { defaultValue: '暂存全部' })} onClick={stageAll}>
            <FileTextOutlined />
          </button>
          <button className="icon-btn sm" title={t('desktop.git.refreshTitle', { defaultValue: '刷新' })} onClick={() => void refresh()}>
            <UndoOutlined />
          </button>
        </span>
      </div>

      <div className="git-branch-row">
        <BranchesOutlined />
        {status.branch || 'HEAD'}
        <span className="ab">
          <span className="up">↑{status.ahead}</span>
          <span className="down">↓{status.behind}</span>
        </span>
      </div>

      <div className="git-commit-area">
        <textarea
          rows={2}
          placeholder={t('desktop.git.commitMessage')}
          value={msg}
          onChange={(e) => setMsg(e.target.value)}
          onKeyDown={(e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') commit();
          }}
        />
        <div className="row">
          <button className="btn primary" style={{ flex: 1 }} disabled={!msg.trim() || busy === 'commit'} onClick={commit}>
            {t('desktop.git.commit')}
          </button>
          {selected.size > 0 && (
            <button className="icon-btn" style={{ border: '1px solid var(--line2)', borderRadius: 7 }} title={t('desktop.git.unstage', { defaultValue: '取消全部选择' })} onClick={() => setSelected(new Set())}>
              <UndoOutlined />
            </button>
          )}
        </div>
      </div>

      <div className="git-changes">
        <div className="git-group">
          {t('desktop.git.changes', { defaultValue: '更改' })} <span className="cnt">({changes.length})</span>
        </div>
        {changes.length === 0 && <div className="git-hint">{t('desktop.git.noChanges')}</div>}
        {changes.map((c) => (
          <div
            key={c.path}
            className={`git-file${selected.has(c.path) ? ' sel' : ''}`}
            onClick={() => toggle(c.path)}
          >
            <span className={`st ${c.x}`}>{c.x === 'U' ? 'U' : c.x}</span>
            <span className="path">{c.path}</span>
            <button
              className="icon-btn sm"
              title={t('desktop.git.openDiff', { defaultValue: '打开 diff' })}
              onClick={(e) => {
                e.stopPropagation();
                onOpenDiff(c.path);
              }}
            >
              <FileTextOutlined />
            </button>
          </div>
        ))}
        <div className="git-hint">
          {t('desktop.git.offlineHint', { defaultValue: '本地 Git 操作完全离线可用。Push / Pull 凭据由网关按 remote 自动注入密钥库 token。' })}
        </div>
      </div>

      <div className="git-bar">
        <button className="btn ghost sm" style={{ flex: 1 }} disabled={busy === 'push'} onClick={push}>
          <UpOutlined /> {t('desktop.git.push')}{status.ahead > 0 ? ` · ${status.ahead}` : ''}
        </button>
        <button className="btn ghost sm" style={{ flex: 1 }} disabled={busy === 'pull'} onClick={pull}>
          <DownOutlined /> {t('desktop.git.pull')}{status.behind > 0 ? ` · ${status.behind}` : ''}
        </button>
      </div>
    </div>
  );
}