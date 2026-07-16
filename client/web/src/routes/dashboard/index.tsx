import { useState, useEffect, useMemo } from 'react';
import { Card, Row, Col, List, Button, message } from 'antd';
import {
  AppstoreOutlined,
  PullRequestOutlined,
  TeamOutlined,
  ForkOutlined,
  ArrowUpOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuthStore } from '../../stores/auth';
import { useRepositoriesStore } from '../../stores/repositories';
import { settingsApi, type DashboardData } from '../../api/settings';
import DashboardSkeleton from '../../components/skeleton/DashboardSkeleton';

type ActivityType = 'mergedPR' | 'pushedCommits' | 'openedPR' | 'reviewedPR' | 'createdIssue' | 'commentedOnIssue';

interface Activity {
  name: string;
  initials: string;
  gradient: string;
  type: ActivityType;
  params: Record<string, string | number | undefined>;
  time: string;
}

interface Repo {
  id: string;
  name: string;
  path: string;
  lang: string;
  color: string;
}

function GradientAvatar({ initials, gradient, size = 32 }: { initials: string; gradient: string; size?: number }) {
  return (
    <div
      style={{
        width: size,
        height: size,
        borderRadius: '50%',
        background: gradient,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: size * 0.375,
        fontWeight: 600,
        color: '#fff',
        flexShrink: 0,
      }}
    >
      {initials}
    </div>
  );
}

function ContribGraph() {
  const bars = Array.from({ length: 30 }, (_, i) => {
    const h = Math.abs(Math.sin(i * 12.9898)) * 100;
    let bg = '#0d419d';
    if (h > 70) bg = '#1f6feb';
    else if (h > 40) bg = '#388bfd';
    return { key: i, height: Math.max(3, h), bg };
  });

  return (
    <div style={{ display: 'flex', alignItems: 'end', gap: 2, height: 60, marginTop: 12 }}>
      {bars.map((bar) => (
        <div
          key={bar.key}
          style={{
            flex: 1,
            background: bar.bg,
            borderRadius: 2,
            minHeight: 3,
            height: `${bar.height}%`,
            transition: 'all 0.3s',
          }}
        />
      ))}
    </div>
  );
}

export default function DashboardPage() {
  const [loading, setLoading] = useState(true);
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const { t } = useTranslation();
  const { repositories, fetchRepositories } = useRepositoriesStore();
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);

  useEffect(() => {
    const loadData = async () => {
      try {
        const [data] = await Promise.all([
          settingsApi.getDashboard(),
          fetchRepositories(),
        ]);
        setDashboardData(data);
      } catch (err) {
        message.error((err as Error).message);
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, [fetchRepositories, t]);

  const stats = useMemo(
    () => [
      {
        label: t('app.dashboard.stats.repositories'),
        value: (dashboardData?.repo_count ?? 0).toLocaleString(),
        change: t('app.dashboard.stats.repositoriesChange'),
        icon: <AppstoreOutlined />,
        color: '#58a6ff',
        bg: 'rgba(31,111,235,0.15)',
      },
      {
        label: t('app.dashboard.stats.openPRs'),
        value: (dashboardData?.open_prs ?? 0).toLocaleString(),
        change: t('app.dashboard.stats.openPRsChange'),
        icon: <PullRequestOutlined />,
        color: '#3fb950',
        bg: 'rgba(63,185,80,0.15)',
      },
      {
        label: t('app.dashboard.stats.teamMembers'),
        value: (dashboardData?.open_issues ?? 0).toLocaleString(),
        change: t('app.dashboard.stats.teamMembersChange'),
        icon: <TeamOutlined />,
        color: '#bc8cff',
        bg: 'rgba(188,140,255,0.15)',
      },
      {
        label: t('app.dashboard.stats.commits'),
        value: (dashboardData?.open_issues ?? 0).toLocaleString(),
        change: t('app.dashboard.stats.commitsChange'),
        icon: <ForkOutlined />,
        color: '#d29922',
        bg: 'rgba(210,153,34,0.15)',
      },
    ],
    [dashboardData, t]
  );

  const activities: Activity[] = useMemo(
    () => (dashboardData?.recent_activities ?? []).map((item) => ({
      name: (item.name as string) ?? 'Unknown',
      initials: (item.initials as string) ?? '??',
      gradient: (item.gradient as string) ?? 'linear-gradient(135deg,#58a6ff,#1f6feb)',
      type: (item.type as ActivityType) ?? 'pushedCommits',
      params: (item.params as Record<string, string | number | undefined>) ?? {},
      time: (item.time as string) ?? '',
    })),
    [dashboardData?.recent_activities]
  );

  const repos: Repo[] = useMemo(
    () => (repositories ?? []).map((repo) => ({
      id: repo.id,
      name: repo.name,
      path: repo.path,
      lang: '',
      color: '#58a6ff',
    })),
    [repositories]
  );

  const renderActivityAction = (item: Activity) => {
    const template = t(`app.dashboard.activity.${item.type}`, item.params);
    const name = item.name.replace(/</g, '&lt;').replace(/>/g, '&gt;');
    return { __html: `<strong>${name}</strong> ${template}` };
  };

  if (loading) {
    return <DashboardSkeleton />;
  }

  return (
    <div style={{ height: '100%', overflow: 'hidden', display: 'flex', flexDirection: 'column', padding: 24 }}>
      <div style={{ marginBottom: 24, flexShrink: 0 }}>
        <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 4, color: '#e6edf3' }}>
          {t('app.dashboard.welcomeBack', { name: user?.full_name || user?.username || 'Zhang Lei' })}
        </h1>
        <p style={{ color: '#8b949e', fontSize: 14 }}>{t('app.dashboard.subtitle')}</p>
      </div>

      <div style={{ marginBottom: 24, flexShrink: 0 }}>
        <Row gutter={[16, 16]}>
          {stats.map((s) => (
            <Col span={6} key={s.label}>
              <Card
                hoverable
                styles={{ body: { padding: 20 } }}
                style={{ border: '1px solid #21262d', background: '#161b22' }}
              >
                <div
                  style={{
                    width: 36,
                    height: 36,
                    borderRadius: 8,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    marginBottom: 12,
                    background: s.bg,
                    color: s.color,
                    fontSize: 18,
                  }}
                >
                  {s.icon}
                </div>
                <div style={{ fontSize: 28, fontWeight: 700, marginBottom: 2, color: '#e6edf3' }}>{s.value}</div>
                <div style={{ fontSize: 12, color: '#8b949e', textTransform: 'uppercase', letterSpacing: 0.5 }}>{s.label}</div>
                <div style={{ fontSize: 11, marginTop: 8, display: 'flex', alignItems: 'center', gap: 4, color: '#3fb950' }}>
                  <ArrowUpOutlined /> {s.change}
                </div>
              </Card>
            </Col>
          ))}
        </Row>
      </div>

      <div style={{ flex: 1, overflow: 'hidden', minHeight: 0 }}>
        <Row gutter={[16, 16]} style={{ height: '100%' }}>
          <Col span={16} style={{ height: '100%' }}>
            <Card
              title={<span style={{ fontSize: 14, fontWeight: 600, color: '#e6edf3' }}>{t('app.dashboard.recentActivity')}</span>}
              extra={<Button type="link" style={{ fontSize: 12, padding: 0 }}>{t('app.dashboard.viewAll')} →</Button>}
              styles={{ body: { padding: '0 20px 20px', flex: 1, overflowY: 'auto' } }}
              style={{ border: '1px solid #21262d', background: '#161b22', height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}
            >
              <List
                dataSource={activities}
                renderItem={(item) => (
                  <List.Item style={{ borderBottom: '1px solid #21262d', padding: '10px 0', gap: 12 }}>
                    <GradientAvatar initials={item.initials} gradient={item.gradient} size={32} />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <p
                        style={{ fontSize: 13, lineHeight: 1.5, margin: 0, color: '#8b949e' }}
                        dangerouslySetInnerHTML={renderActivityAction(item)}
                      />
                      <div style={{ fontSize: 11, color: '#6e7681', marginTop: 2, display: 'flex', alignItems: 'center', gap: 4 }}>
                        <ClockCircleOutlined style={{ fontSize: 10 }} /> {item.time}
                      </div>
                    </div>
                  </List.Item>
                )}
              />
            </Card>
          </Col>
          <Col span={8} style={{ height: '100%' }}>
            <div style={{ height: '100%', display: 'flex', flexDirection: 'column', gap: 16 }}>
              <Card
                title={<span style={{ fontSize: 14, fontWeight: 600, color: '#e6edf3' }}>{t('app.dashboard.yourRepositories')}</span>}
                extra={
                  <Button type="link" style={{ fontSize: 12, padding: 0 }} onClick={() => navigate('/repositories')}>
                    {t('app.dashboard.viewAll')} →
                  </Button>
                }
                styles={{ body: { padding: '0 20px 20px', flex: 1, overflowY: 'auto' } }}
                style={{ border: '1px solid #21262d', background: '#161b22', flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}
              >
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {repos.map((repo) => (
                    <div
                      key={repo.id}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 10,
                        padding: 10,
                        borderRadius: 8,
                        cursor: 'pointer',
                        transition: 'all 0.2s',
                        color: '#e6edf3',
                      }}
                      className="repo-quick-item"
                      onClick={() => {
                        const repoOwner = repo.path.split('/')[0];
                        navigate(`/repositories/${repoOwner}/${repo.name}`);
                      }}
                      onMouseEnter={(e) => { e.currentTarget.style.background = '#1c2333'; }}
                      onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
                    >
                      <div style={{ width: 8, height: 8, borderRadius: '50%', flexShrink: 0, background: repo.color }} />
                      <span style={{ fontSize: 13, fontWeight: 500, flex: 1, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {repo.name}
                      </span>
                      <span style={{ fontSize: 11, color: '#6e7681' }}>{repo.lang}</span>
                    </div>
                  ))}
                </div>
              </Card>
              <Card
                title={<span style={{ fontSize: 14, fontWeight: 600, color: '#e6edf3' }}>{t('app.dashboard.contributionActivity')}</span>}
                styles={{ body: { padding: '0 20px 20px' } }}
                style={{ border: '1px solid #21262d', background: '#161b22', flexShrink: 0 }}
              >
                <p style={{ fontSize: 12, color: '#6e7681', marginBottom: 4 }}>{t('app.dashboard.contributionsCount', { count: 142 })}</p>
                <ContribGraph />
              </Card>
            </div>
          </Col>
        </Row>
      </div>
    </div>
  );
}
