import { useEffect, useMemo, useState } from 'react';
import { Card, Segmented, Tag } from 'antd';
import { PullRequestOutlined, ExclamationCircleOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { settingsApi, type MyPullRequest, type MyIssue } from '../../api/settings';

const borderColor = '#21262d';
const textPrimary = '#e6edf3';
const textSecondary = '#8b949e';
const textTertiary = '#6e7681';
const hoverBg = '#1c2333';
const green = '#3fb950';
const red = '#f85149';
const purple = '#bc8cff';

type MyWorkTab = 'pr' | 'issue';

function statusColor(status: string): string {
  if (status === 'open') return green;
  if (status === 'merged') return purple;
  return red;
}

function statusLabel(status: string): string {
  if (status === 'open') return 'Open';
  if (status === 'merged') return 'Merged';
  if (status === 'closed') return 'Closed';
  return status;
}

function relativeTime(dateStr: string): string {
  const diffMs = Date.now() - new Date(dateStr).getTime();
  if (Number.isNaN(diffMs)) return '';
  const minutes = Math.floor(diffMs / 60000);
  if (minutes < 1) return 'just now';
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d ago`;
  return new Date(dateStr).toLocaleDateString();
}

export default function MyWorkCard({
  repoPaths,
  repoNames,
}: {
  repoPaths: Map<string, string>;
  repoNames: Map<string, string>;
}) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [tab, setTab] = useState<MyWorkTab>('pr');
  const [prs, setPrs] = useState<MyPullRequest[]>([]);
  const [issues, setIssues] = useState<MyIssue[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      setLoading(true);
      try {
        if (tab === 'pr') {
          const res = await settingsApi.getUserPullRequests({ limit: 20 });
          if (!cancelled) setPrs(res.items);
        } else {
          const res = await settingsApi.getUserIssues({ limit: 20 });
          if (!cancelled) setIssues(res.items);
        }
      } catch {
        // 加载失败保持空态
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    Promise.resolve().then(() => load());
    return () => { cancelled = true; };
  }, [tab]);

  const items = useMemo(() => {
    if (tab === 'pr') {
      return prs.map((pr) => ({
        key: pr.id,
        numberLabel: `#${pr.pr_number}`,
        title: pr.title,
        status: pr.status,
        path: repoPaths.get(pr.repository_id),
        repoName: repoNames.get(pr.repository_id),
        navigateTo: repoPaths.get(pr.repository_id)
          ? `/repositories/${repoPaths.get(pr.repository_id)}/pulls/${pr.pr_number}`
          : null,
        time: relativeTime(pr.created_at),
      }));
    }
    return issues.map((issue) => ({
      key: issue.id,
      numberLabel: `#${issue.issue_number}`,
      title: issue.title,
      status: issue.status,
      path: repoPaths.get(issue.repository_id),
      repoName: repoNames.get(issue.repository_id),
      navigateTo: repoPaths.get(issue.repository_id)
        ? `/repositories/${repoPaths.get(issue.repository_id)}/issues/${issue.issue_number}`
        : null,
      time: relativeTime(issue.created_at),
    }));
  }, [tab, prs, issues, repoPaths, repoNames]);

  return (
    <Card
      title={
        <span style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 14, fontWeight: 600, color: textPrimary }}>
          {tab === 'pr' ? <PullRequestOutlined style={{ fontSize: 15, color: textSecondary }} /> : <ExclamationCircleOutlined style={{ fontSize: 15, color: textSecondary }} />}
          {tab === 'pr' ? t('app.dashboard.myPullRequests') : t('app.dashboard.myIssues')}
        </span>
      }
      extra={
        <Segmented
          size="small"
          value={tab}
          onChange={(val) => setTab(val as MyWorkTab)}
          options={[
            { label: 'PR', value: 'pr' },
            { label: t('app.dashboard.issues'), value: 'issue' },
          ]}
        />
      }
      styles={{ body: { padding: '0 20px 12px', flex: 1, overflowY: 'auto', minHeight: 0 } }}
      style={{ border: `1px solid ${borderColor}`, background: '#161b22', height: 320, display: 'flex', flexDirection: 'column', overflow: 'hidden', flexShrink: 0 }}
    >
      {loading ? (
        <div style={{ display: 'flex', flex: 1, alignItems: 'center', justifyContent: 'center', color: textTertiary, fontSize: 13 }}>
          {t('app.dashboard.loading')}
        </div>
      ) : items.length === 0 ? (
        <div style={{ display: 'flex', flex: 1, alignItems: 'center', justifyContent: 'center', color: textTertiary, fontSize: 13 }}>
          {t('app.dashboard.myWorkEmpty')}
        </div>
      ) : (
        items.map((item) => (
          <div
            key={item.key}
            onClick={() => item.navigateTo && navigate(item.navigateTo)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 10,
              padding: '10px 0',
              borderBottom: `1px solid ${borderColor}`,
              cursor: item.navigateTo ? 'pointer' : 'default',
            }}
            onMouseEnter={(e) => { e.currentTarget.style.background = hoverBg; }}
            onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
          >
            <Tag
              style={{
                margin: 0,
                borderRadius: 12,
                fontSize: 11,
                border: 'none',
                color: statusColor(item.status),
                background: `${statusColor(item.status)}1a`,
                flexShrink: 0,
              }}
            >
              {statusLabel(item.status)}
            </Tag>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 13, color: textPrimary, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                <span style={{ color: textTertiary, fontWeight: 400 }}>{item.repoName ? `${item.repoName} · ` : ''}</span>
                {item.title}
              </div>
              <div style={{ fontSize: 11, color: textTertiary, marginTop: 2 }}>{item.numberLabel}</div>
            </div>
            <span style={{ fontSize: 11, color: textTertiary, flexShrink: 0 }}>{item.time}</span>
          </div>
        ))
      )}
    </Card>
  );
}