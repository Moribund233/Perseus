import { useEffect, useMemo, useState } from 'react';
import { Empty, Radio, Spin } from 'antd';
import { IssuesCloseOutlined, PullRequestOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useMyWorkStore } from '../stores/myWork';
import { useRepositoriesStore } from '../stores/repositories';
import { useNavigationStore } from '../stores/navigation';
import { timeAgo } from '../utils/time';

const borderColor = '#21262d';
const hoverBg = '#1c2333';
const textPrimary = '#e6edf3';
const textSecondary = '#8b949e';
const textTertiary = '#6e7681';
const blueLight = '#58a6ff';

const statusColor: Record<string, string> = {
  open: 'blue',
  closed: 'default',
  merged: 'purple',
};

type TabKey = 'prs' | 'issues';

export default function MyWorkView() {
  const { t } = useTranslation();
  const navigate = useNavigationStore((s) => s.navigate);
  const repositories = useRepositoriesStore((s) => s.repositories);
  const fetchRepositories = useRepositoriesStore((s) => s.fetchRepositories);
  const setPendingOpen = useRepositoriesStore((s) => s.setPendingOpen);

  const pullRequests = useMyWorkStore((s) => s.pullRequests);
  const issues = useMyWorkStore((s) => s.issues);
  const isLoading = useMyWorkStore((s) => s.isLoading);
  const error = useMyWorkStore((s) => s.error);
  const fetchMyPullRequests = useMyWorkStore((s) => s.fetchMyPullRequests);
  const fetchMyIssues = useMyWorkStore((s) => s.fetchMyIssues);

  const [tab, setTab] = useState<TabKey>('prs');
  const [status, setStatus] = useState<string>('open');

  useEffect(() => {
    void fetchMyPullRequests(status === 'all' ? undefined : status);
    void fetchMyIssues(status === 'all' ? undefined : status);
  }, [status, fetchMyPullRequests, fetchMyIssues]);

  useEffect(() => {
    if (repositories.length === 0) void fetchRepositories();
  }, [repositories.length, fetchRepositories]);

  const repoNameById = useMemo(() => {
    const map: Record<string, string> = {};
    for (const r of repositories) map[r.id] = r.name;
    return map;
  }, [repositories]);

  const openTarget = (repoId: string, kind: TabKey, number: number) => {
    const repo = repositories.find((r) => r.id === repoId);
    if (!repo) return;
    setPendingOpen({
      repoPath: repo.path,
      tab: kind === 'prs' ? 'pullRequests' : 'issues',
      prNumber: kind === 'prs' ? number : undefined,
      issueNumber: kind === 'issues' ? number : undefined,
    });
    navigate('repositories');
  };

  const rowStyle: React.CSSProperties = {
    display: 'flex', alignItems: 'center', gap: 10, padding: '9px 14px',
    borderBottom: `1px solid ${borderColor}`, cursor: 'pointer', fontSize: 13,
  };

  return (
    <div className="page">
      <div className="page-head">
        <h2>{t('desktop.myWork.title')}</h2>
        <span className="sub">{t('desktop.myWork.sub')}</span>
        <div className="right">
          <Radio.Group value={status} onChange={(e) => setStatus(e.target.value)} size="small" buttonStyle="solid">
            <Radio.Button value="open">{t('desktop.myWork.statusOpen')}</Radio.Button>
            <Radio.Button value="closed">{t('desktop.myWork.statusClosed')}</Radio.Button>
            <Radio.Button value="all">{t('desktop.myWork.statusAll')}</Radio.Button>
          </Radio.Group>
        </div>
      </div>

      <div style={{ display: 'flex', gap: 0, marginBottom: 12 }}>
        {([['prs', t('desktop.myWork.myPRs')], ['issues', t('desktop.myWork.myIssues')]] as const).map(([key, label]) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            style={{
              background: 'transparent', border: 'none', borderBottom: `2px solid ${tab === key ? blueLight : 'transparent'}`,
              color: tab === key ? textPrimary : textSecondary, fontSize: 13, fontWeight: 600, padding: '8px 14px', cursor: 'pointer',
            }}
          >
            {label}
          </button>
        ))}
      </div>

      {error && <div style={{ color: '#f85149', fontSize: 13, marginBottom: 10 }}>{error}</div>}

      <div style={{ border: `1px solid ${borderColor}`, borderRadius: 10, background: '#161b22', overflow: 'hidden' }}>
        {isLoading ? (
          <div style={{ padding: '36px 0', textAlign: 'center' }}><Spin /></div>
        ) : (
          <>
            {tab === 'prs' && pullRequests.length === 0 && (
              <Empty style={{ padding: '32px 0' }} description={t('desktop.myWork.emptyPRs')} image={Empty.PRESENTED_IMAGE_SIMPLE} />
            )}
            {tab === 'prs' && pullRequests.map((pr) => (
              <div key={pr.id} style={rowStyle}
                onMouseEnter={(e) => { e.currentTarget.style.background = hoverBg; }}
                onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
                onClick={() => openTarget(pr.repository_id, 'prs', pr.pr_number)}
              >
                <PullRequestOutlined style={{ color: textTertiary, flexShrink: 0 }} />
                <span style={{ color: textTertiary, flexShrink: 0 }}>{repoNameById[pr.repository_id] ?? ''} #{pr.pr_number}</span>
                <span style={{ flex: 1, minWidth: 0, color: textPrimary, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{pr.title}</span>
                <span style={{ color: statusColor[pr.status] === 'purple' ? '#bc8cff' : undefined, flexShrink: 0 }}>
                  <em style={{ fontStyle: 'normal', fontSize: 11, color: textSecondary, border: `1px solid ${borderColor}`, borderRadius: 10, padding: '1px 8px' }}>
                    {t(`desktop.myWork.prStatus.${pr.status}`) || pr.status}
                  </em>
                </span>
                <span style={{ color: textTertiary, fontSize: 12, flexShrink: 0 }}>{timeAgo(pr.created_at, t)}</span>
              </div>
            ))}
            {tab === 'issues' && issues.length === 0 && (
              <Empty style={{ padding: '32px 0' }} description={t('desktop.myWork.emptyIssues')} image={Empty.PRESENTED_IMAGE_SIMPLE} />
            )}
            {tab === 'issues' && issues.map((issue) => (
              <div key={issue.id} style={rowStyle}
                onMouseEnter={(e) => { e.currentTarget.style.background = hoverBg; }}
                onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
                onClick={() => openTarget(issue.repository_id, 'issues', issue.issue_number)}
              >
                <IssuesCloseOutlined style={{ color: textTertiary, flexShrink: 0 }} />
                <span style={{ color: textTertiary, flexShrink: 0 }}>{repoNameById[issue.repository_id] ?? ''} #{issue.issue_number}</span>
                <span style={{ flex: 1, minWidth: 0, color: textPrimary, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{issue.title}</span>
                <em style={{ fontStyle: 'normal', fontSize: 11, color: textSecondary, border: `1px solid ${borderColor}`, borderRadius: 10, padding: '1px 8px', flexShrink: 0 }}>
                  {t(`desktop.myWork.issueStatus.${issue.status}`) || issue.status}
                </em>
                <span style={{ color: textTertiary, fontSize: 12, flexShrink: 0 }}>{timeAgo(issue.created_at, t)}</span>
              </div>
            ))}
          </>
        )}
      </div>
    </div>
  );
}
