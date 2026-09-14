import { useEffect, useMemo, useState } from 'react';
import { Empty, Radio, Spin } from 'antd';
import { IssuesCloseOutlined, PullRequestOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useMyWorkStore } from '../stores/myWork';
import { useRepositoriesStore } from '../stores/repositories';
import { useNavigationStore } from '../stores/navigation';
import { timeAgo } from '../utils/time';
import type { DashboardActivity } from '../api/myWork';

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

/** 近 30 天贡献柱状图（与 web 端 Dashboard ContribGraph 同源同款） */
function ContribGraph({ contributionsByDay }: { contributionsByDay: Record<string, number> }) {
  const days = useMemo(() => {
    const today = new Date();
    return Array.from({ length: 30 }, (_, i) => {
      const d = new Date(today);
      d.setDate(today.getDate() - (29 - i));
      const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
      return { key, count: contributionsByDay[key] ?? 0 };
    });
  }, [contributionsByDay]);

  const max = Math.max(1, ...days.map((d) => d.count));

  return (
    <div style={{ display: 'flex', alignItems: 'end', gap: 2, height: 56, marginTop: 10 }}>
      {days.map((day) => {
        const ratio = day.count / max;
        let bg = '#1c2128';
        if (day.count > 0) bg = ratio > 0.66 ? '#1f6feb' : ratio > 0.33 ? '#388bfd' : '#0d419d';
        return (
          <div
            key={day.key}
            title={`${day.key}: ${day.count}`}
            style={{
              flex: 1,
              background: bg,
              borderRadius: 2,
              minHeight: 3,
              height: `${Math.max(6, ratio * 100)}%`,
              transition: 'all 0.3s',
            }}
          />
        );
      })}
    </div>
  );
}

export default function MyWorkView() {
  const { t } = useTranslation();
  const navigate = useNavigationStore((s) => s.navigate);
  const repositories = useRepositoriesStore((s) => s.repositories);
  const fetchRepositories = useRepositoriesStore((s) => s.fetchRepositories);
  const setPendingOpen = useRepositoriesStore((s) => s.setPendingOpen);

  const pullRequests = useMyWorkStore((s) => s.pullRequests);
  const issues = useMyWorkStore((s) => s.issues);
  const dashboard = useMyWorkStore((s) => s.dashboard);
  const isLoading = useMyWorkStore((s) => s.isLoading);
  const error = useMyWorkStore((s) => s.error);
  const fetchMyPullRequests = useMyWorkStore((s) => s.fetchMyPullRequests);
  const fetchMyIssues = useMyWorkStore((s) => s.fetchMyIssues);
  const fetchDashboard = useMyWorkStore((s) => s.fetchDashboard);

  const [tab, setTab] = useState<TabKey>('prs');
  const [status, setStatus] = useState<string>('open');

  useEffect(() => {
    void fetchMyPullRequests(status === 'all' ? undefined : status);
    void fetchMyIssues(status === 'all' ? undefined : status);
  }, [status, fetchMyPullRequests, fetchMyIssues]);

  useEffect(() => {
    void fetchDashboard();
  }, [fetchDashboard]);

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

  const contributions = useMemo(
    () => Object.values(dashboard?.contributions_by_day ?? {}).reduce((s, n) => s + n, 0),
    [dashboard?.contributions_by_day],
  );

  // 活动流文案: 动态 i18n 键 {entity_type}_{action}, 无匹配时回退 fallback（与 web 端一致）
  const activities = useMemo(
    () => (dashboard?.recent_activities ?? []).map((item: DashboardActivity) => {
      const entityType = String(item.entity_type ?? '');
      const action = String(item.action ?? '');
      const details = String(item.details ?? '');
      const key = `${entityType}_${action}`;
      const text = t(`desktop.myWork.activityText.${key}`, {
        defaultValue: t('desktop.myWork.activityText.fallback', {
          action,
          entityType: entityType === 'pull_request' ? 'PR' : entityType,
        }),
        details,
      });
      return {
        key: String(item.id ?? `${item.actor_username}-${item.created_at}`),
        actor: String(item.actor_username ?? 'unknown'),
        text,
        time: timeAgo(item.created_at, t),
      };
    }),
    [dashboard?.recent_activities, t],
  );

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

      <div style={{ display: 'flex', gap: 12, marginBottom: 12 }}>
        <div style={{ flex: 1, border: `1px solid ${borderColor}`, borderRadius: 10, background: '#161b22', padding: '12px 16px' }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: textSecondary }}>{t('desktop.myWork.contributionActivity')}</div>
          <div style={{ display: 'flex', gap: 16, marginTop: 8, fontSize: 12, color: textTertiary }}>
            <span>{t('desktop.myWork.stats.repositories')}: <b style={{ color: blueLight }}>{dashboard?.repo_count ?? 0}</b></span>
            <span>{t('desktop.myWork.stats.openPRs')}: <b style={{ color: '#3fb950' }}>{dashboard?.open_prs ?? 0}</b></span>
            <span>{t('desktop.myWork.stats.openIssues')}: <b style={{ color: '#bc8cff' }}>{dashboard?.open_issues ?? 0}</b></span>
          </div>
          <ContribGraph contributionsByDay={dashboard?.contributions_by_day ?? {}} />
          <div style={{ marginTop: 8, fontSize: 12, color: textTertiary }}>
            {contributions > 0
              ? t('desktop.myWork.contributionsCount', { count: contributions })
              : t('desktop.myWork.noContributions')}
          </div>
        </div>
        <div style={{ flex: 1, border: `1px solid ${borderColor}`, borderRadius: 10, background: '#161b22', padding: '12px 16px', overflow: 'auto' }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: textSecondary, marginBottom: 4 }}>{t('desktop.myWork.recentActivity')}</div>
          {activities.length === 0 ? (
            <div style={{ padding: '18px 0', textAlign: 'center', fontSize: 12, color: textTertiary }}>
              {t('desktop.myWork.emptyActivity')}
            </div>
          ) : (
            activities.map((a) => (
              <div key={a.key} style={{ display: 'flex', gap: 8, padding: '6px 0', borderBottom: `1px dashed ${borderColor}`, fontSize: 12 }}>
                <span style={{ color: blueLight, flexShrink: 0 }}>{a.actor}</span>
                <span style={{ flex: 1, minWidth: 0, color: textSecondary }}>{a.text}</span>
                <span style={{ color: textTertiary, flexShrink: 0 }}>{a.time}</span>
              </div>
            ))
          )}
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
