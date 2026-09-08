import { useEffect } from 'react';
import { message } from 'antd';
import { PullRequestOutlined, WarningOutlined, RightOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { Workspace } from '../../api/workspaces';
import { useWorkspaceRepo } from '../../hooks/useWorkspaceRepo';
import { usePullRequestsStore } from '../../stores/pullRequests';
import { useIssuesStore } from '../../stores/issues';
import { timeAgo } from '../../utils/time';

type Kind = 'prs' | 'issues';

interface Props {
  kind: Kind;
  workspace: Workspace;
}

const PRIORITY_CLASS: Record<string, string> = {
  high: 'p-high',
  medium: 'p-medium',
  critical: 'p-critical',
  low: 'p-low',
};

// QuickListPanel：侧栏里基于真实服务器 API 的 PR / Issue 快速列表。
export default function QuickListPanel({ kind, workspace }: Props) {
  const { t } = useTranslation();
  const repo = useWorkspaceRepo(workspace);
  const { pullRequests = [], fetchPullRequests } = usePullRequestsStore();
  const { issues = [], fetchIssues } = useIssuesStore();

  const isPrs = kind === 'prs';
  const items = isPrs ? pullRequests : issues;

  // usePullRequestsStore / useIssuesStore 返回 state 对象，解构 action
  useEffect(() => {
    if (!repo.repoId) return;
    if (isPrs) {
      void fetchPullRequests(repo.repoId, 'open').catch(() => {});
    } else {
      void fetchIssues(repo.repoId, 'open').catch(() => {});
    }
  }, [repo.repoId, isPrs, fetchPullRequests, fetchIssues]);

  const head = isPrs
    ? t('desktop.quick.prTitle', { name: workspace.name.toUpperCase(), defaultValue: 'Pull Requests · {{name}}' })
    : t('desktop.quick.issuesTitle', { name: workspace.name.toUpperCase(), defaultValue: 'Issues · {{name}}' });

  const openFull = () => {
    message.info(t('desktop.portal.phase2', { defaultValue: 'Phase 2 提供' }));
  };

  const top = items.slice(0, 3);

  return (
    <div className="sb-pane on" data-pane={kind}>
      <div className="sb-head">
        {head}
        <span className="right">
          <button className="icon-btn sm" title={t('desktop.quick.openFull', { defaultValue: '打开完整视图' })} onClick={openFull}>
            <RightOutlined />
          </button>
        </span>
      </div>
      {(!repo.serverId || !repo.owner) && (
        <div className="git-hint">
          {t('desktop.quick.noRemote', { defaultValue: '工作区未关联远程仓库，无法获取 PR / Issue 列表。' })}
        </div>
      )}
      {repo.serverId && repo.owner && repo.loading && (
        <div className="git-hint">{t('desktop.quick.loading', { defaultValue: '正在解析仓库…' })}</div>
      )}
      {repo.serverId && repo.owner && !repo.loading && !repo.repoId && (
        <div className="git-hint">
          {t('desktop.quick.notFound', { defaultValue: `在服务器上找不到 ${repo.owner}/${repo.repo}，PR / Issue 列表不可用。` })}
        </div>
      )}
      {repo.repoId && top.map((it) => {
        const num = isPrs ? (it as { pr_number: number }).pr_number : (it as { issue_number: number }).issue_number;
        const priority = !isPrs ? (it as { priority?: string }).priority : undefined;
        const updated = it.updated_at ? timeAgo(it.updated_at, t) : '';
        return (
          <div key={it.id} className="lrow" onClick={openFull}>
            <span className="st-ic">
              {isPrs ? <PullRequestOutlined className="open" /> : <WarningOutlined className="open" />}
            </span>
            <div className="lr-main">
              <div className="lr-title">
                {it.title} <span className="num">#{num}</span>
                {priority && <span className={`tag ${PRIORITY_CLASS[priority] ?? 'p-low'}`}>{priority}</span>}
              </div>
              <div className="lr-meta">{updated}</div>
            </div>
          </div>
        );
      })}
      {repo.repoId && items.length === 0 && (
        <div className="git-hint">{t('desktop.quick.empty', { defaultValue: '暂无开放记录' })}</div>
      )}
    </div>
  );
}