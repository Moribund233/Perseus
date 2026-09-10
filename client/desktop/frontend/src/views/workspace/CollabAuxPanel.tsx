import { useEffect } from 'react';
import { Spin } from 'antd';
import { IssuesCloseOutlined, PullRequestOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { Workspace } from '../../api/workspaces';
import { useWorkspaceRepo } from '../../hooks/useWorkspaceRepo';
import { useWorkspaceChatRoom } from '../../hooks/useWorkspaceChatRoom';
import { usePullRequestsStore } from '../../stores/pullRequests';
import { useIssuesStore } from '../../stores/issues';
import { getAvatarColor, getInitials } from '../../utils/avatar';
import { timeAgo } from '../../utils/time';

const borderColor = '#21262d';
const textPrimary = '#e6edf3';
const textSecondary = '#8b949e';
const textTertiary = '#6e7681';
const blueLight = '#58a6ff';
const bgSecondary = '#161b22';
const green = '#3fb950';

const PRIORITY_COLOR: Record<string, string> = {
  critical: '#f85149',
  high: '#f0883e',
  medium: '#d29922',
  low: '#6e7681',
};

// IDE 右侧协作辅助栏（对齐原型 ide.html aux）：待处理 PR / 相关 Issue / 成员在线。
export default function CollabAuxPanel({ workspace }: { workspace: Workspace }) {
  const { t } = useTranslation();
  const repo = useWorkspaceRepo(workspace);
  const chat = useWorkspaceChatRoom(workspace);

  const pullRequests = usePullRequestsStore((s) => s.pullRequests);
  const issues = useIssuesStore((s) => s.issues);
  const fetchPullRequests = usePullRequestsStore((s) => s.fetchPullRequests);
  const fetchIssues = useIssuesStore((s) => s.fetchIssues);

  useEffect(() => {
    if (!repo.repoId) return;
    void fetchPullRequests(repo.repoId, 'open').catch(() => {});
    void fetchIssues(repo.repoId, 'open').catch(() => {});
  }, [repo.repoId, fetchPullRequests, fetchIssues]);

  const prs = (pullRequests ?? []).slice(0, 3);
  const issueList = (issues ?? []).slice(0, 3);

  const cardTitle: React.CSSProperties = {
    display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, fontWeight: 600,
    color: textPrimary, marginBottom: 8,
  };
  const card: React.CSSProperties = {
    border: `1px solid ${borderColor}`, borderRadius: 8, background: bgSecondary, padding: 10, marginBottom: 10,
  };

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', background: bgSecondary, borderLeft: `1px solid ${borderColor}` }}>
      <div style={{ padding: '10px 12px', borderBottom: `1px solid ${borderColor}`, display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
        <b style={{ fontSize: 12, color: textPrimary }}>{t('desktop.aux.title')}</b>
        <span style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 5, fontSize: 11, color: textTertiary }}>
          <span style={{ width: 7, height: 7, borderRadius: '50%', background: chat.status === 'connected' ? green : '#6e7681' }} />
          {chat.roomMembers.length > 0 ? `${chat.onlineIds.size} ${t('desktop.chat.onlineCount')}` : t(`desktop.chat.status.${chat.status}`)}
        </span>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: 10 }}>
        <div style={card}>
          <div style={cardTitle}><PullRequestOutlined style={{ color: blueLight }} />{t('desktop.aux.pendingPRs')}</div>
          {!repo.repoId && <div style={{ fontSize: 11, color: textTertiary }}>{t('desktop.quick.noRemote', { defaultValue: '工作区未关联远程仓库。' })}</div>}
          {repo.loading && <Spin size="small" />}
          {repo.repoId && prs.length === 0 && <div style={{ fontSize: 11, color: textTertiary }}>{t('desktop.aux.empty')}</div>}
          {prs.map((pr) => (
            <div key={pr.id} style={{ padding: '4px 0', fontSize: 12 }}>
              <div style={{ color: textPrimary, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {pr.title} <span style={{ color: textTertiary }}>#{pr.pr_number}</span>
              </div>
              <div style={{ fontSize: 11, color: textTertiary }}>
                {pr.source_branch} → {pr.target_branch} · {timeAgo(pr.created_at, t)}
              </div>
            </div>
          ))}
        </div>

        <div style={card}>
          <div style={cardTitle}><IssuesCloseOutlined style={{ color: blueLight }} />{t('desktop.aux.relatedIssues')}</div>
          {!repo.repoId && <div style={{ fontSize: 11, color: textTertiary }}>{t('desktop.quick.noRemote', { defaultValue: '工作区未关联远程仓库。' })}</div>}
          {repo.repoId && issueList.length === 0 && <div style={{ fontSize: 11, color: textTertiary }}>{t('desktop.aux.empty')}</div>}
          {issueList.map((issue) => (
            <div key={issue.id} style={{ padding: '4px 0', fontSize: 12 }}>
              <div style={{ color: textPrimary, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {issue.title} <span style={{ color: textTertiary }}>#{issue.issue_number}</span>
              </div>
              <div style={{ fontSize: 11, color: textTertiary, display: 'flex', alignItems: 'center', gap: 6 }}>
                {issue.priority && (
                  <span style={{ color: PRIORITY_COLOR[issue.priority] ?? textTertiary }}>{issue.priority}</span>
                )}
                <span>{timeAgo(issue.created_at, t)}</span>
              </div>
            </div>
          ))}
        </div>

        <div style={card}>
          <div style={cardTitle}>{t('desktop.chat.members')}</div>
          {chat.roomMembers.length === 0 && (
            <div style={{ fontSize: 11, color: textTertiary }}>{t('desktop.chat.noChannelsHint')}</div>
          )}
          {chat.roomMembers.map((m) => {
            const initials = getInitials(m.username || '?');
            const online = chat.onlineIds.has(m.user_id);
            return (
              <div key={m.user_id} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '4px 0', fontSize: 12, color: textSecondary }}>
                <div style={{ position: 'relative' }}>
                  <span style={{
                    width: 22, height: 22, borderRadius: '50%', display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                    background: getAvatarColor(initials), color: '#fff', fontSize: 9, fontWeight: 600,
                  }}>
                    {initials}
                  </span>
                  <span style={{ position: 'absolute', bottom: -1, right: -1, width: 7, height: 7, borderRadius: '50%', background: online ? green : '#6e7681', border: `2px solid ${bgSecondary}` }} />
                </div>
                <span style={{ flex: 1, minWidth: 0, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{m.username}</span>
                <span style={{ fontSize: 10, color: textTertiary }}>{online ? t('desktop.chat.online') : t('desktop.chat.offline')}</span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
