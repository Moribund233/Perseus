import { useState, useEffect, useMemo } from 'react';
import { Card, Row, Col, List } from 'antd';
import {
  AppstoreOutlined,
  PullRequestOutlined,
  ExclamationCircleOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuthStore } from '../../stores/auth';
import { useRepositoriesStore } from '../../stores/repositories';
import { settingsApi, type DashboardData } from '../../api/settings';
import DashboardSkeleton from '../../components/skeleton/DashboardSkeleton';

interface Repo {
  id: string;
  name: string;
  path: string;
  isPublic: boolean;
}

interface ActivityItem {
  key: string;
  actor: string;
  text: string;
  time: string;
}

const avatarColors = ['#1f6feb', '#3fb950', '#58a6ff', '#bc8cff', '#d29922', '#f85149', '#f0883e', '#7956d9'];

function getInitials(name: string): string {
  return name.split(/[\s_-]/).map((n) => n[0]).join('').toUpperCase().slice(0, 2) || '?';
}

function getAvatarColor(name: string): string {
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  return avatarColors[Math.abs(hash) % avatarColors.length];
}

function relativeTime(dateStr: string | null | undefined, t: (key: string, opts?: Record<string, unknown>) => string): string {
  if (!dateStr) return '';
  const diff = Date.now() - new Date(dateStr).getTime();
  if (Number.isNaN(diff)) return '';
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return t('app.dashboard.timeJustNow');
  if (minutes < 60) return t('app.dashboard.timeMinutesAgo', { count: minutes });
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return t('app.dashboard.timeHoursAgo', { count: hours });
  const days = Math.floor(hours / 24);
  if (days < 30) return t('app.dashboard.timeDaysAgo', { count: days });
  return new Date(dateStr).toLocaleDateString();
}

function GradientAvatar({ initials, color, size = 32 }: { initials: string; color: string; size?: number }) {
  return (
    <div
      style={{
        width: size,
        height: size,
        borderRadius: '50%',
        background: color,
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

/** 近 30 天贡献柱状图，数据来自后端按日活动聚合 */
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
    <div style={{ display: 'flex', alignItems: 'end', gap: 2, height: 60, marginTop: 12 }}>
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

export default function DashboardPage() {
  const [loading, setLoading] = useState(true);
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const { t } = useTranslation();
  const { repositories, fetchRepositories } = useRepositoriesStore();
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);

  useEffect(() => {
    let cancelled = false;
    const loadData = async () => {
      try {
        const [data] = await Promise.all([
          settingsApi.getDashboard(),
          fetchRepositories(),
        ]);
        if (!cancelled) setDashboardData(data);
      } catch {
        // 统计加载失败时展示空态而非报错页
        if (!cancelled) setDashboardData(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    loadData();
    return () => { cancelled = true; };
  }, [fetchRepositories]);

  const stats = useMemo(
    () => [
      {
        label: t('app.dashboard.stats.repositories'),
        value: (dashboardData?.repo_count ?? 0).toLocaleString(),
        icon: <AppstoreOutlined />,
        color: '#58a6ff',
        bg: 'rgba(31,111,235,0.15)',
      },
      {
        label: t('app.dashboard.stats.openPRs'),
        value: (dashboardData?.open_prs ?? 0).toLocaleString(),
        icon: <PullRequestOutlined />,
        color: '#3fb950',
        bg: 'rgba(63,185,80,0.15)',
      },
      {
        label: t('app.dashboard.stats.openIssues'),
        value: (dashboardData?.open_issues ?? 0).toLocaleString(),
        icon: <ExclamationCircleOutlined />,
        color: '#bc8cff',
        bg: 'rgba(188,140,255,0.15)',
      },
    ],
    [dashboardData, t]
  );

  const activities: ActivityItem[] = useMemo(
    () => (dashboardData?.recent_activities ?? []).map((item) => {
      const entityType = String(item.entity_type ?? '');
      const action = String(item.action ?? '');
      const details = String(item.details ?? '');
      const key = `${entityType}_${action}`;
      const text = t(`app.dashboard.activityText.${key}`, {
        defaultValue: t('app.dashboard.activityText.fallback', {
          action,
          entityType: entityType === 'pull_request' ? 'PR' : entityType,
        }),
        details,
      });
      const actor = String(item.actor_username ?? 'unknown');
      return {
        key: String(item.id ?? `${actor}-${item.created_at}`),
        actor,
        text,
        time: relativeTime(item.created_at as string | undefined, t),
      };
    }),
    [dashboardData?.recent_activities, t]
  );

  const repos: Repo[] = useMemo(
    () => (repositories ?? []).map((repo) => ({
      id: repo.id,
      name: repo.name,
      path: repo.path,
      isPublic: repo.is_public,
    })),
    [repositories]
  );

  const contributions = useMemo(() => {
    const byDay = (dashboardData?.contributions_by_day ?? {}) as Record<string, number>;
    return Object.values(byDay).reduce((sum, n) => sum + n, 0);
  }, [dashboardData?.contributions_by_day]);

  if (loading) {
    return <DashboardSkeleton />;
  }

  return (
    <div style={{ height: '100%', overflow: 'hidden', display: 'flex', flexDirection: 'column', padding: 24 }}>
      <div style={{ marginBottom: 24, flexShrink: 0 }}>
        <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 4, color: '#e6edf3' }}>
          {t('app.dashboard.welcomeBack', { name: user?.full_name || user?.username || '' })}
        </h1>
        <p style={{ color: '#8b949e', fontSize: 14 }}>{t('app.dashboard.subtitle')}</p>
      </div>

      <div style={{ marginBottom: 24, flexShrink: 0 }}>
        <Row gutter={[16, 16]}>
          {stats.map((s) => (
            <Col span={8} key={s.label}>
              <Card
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
              styles={{ body: { padding: '0 20px 20px', flex: 1, overflowY: 'auto' } }}
              style={{ border: '1px solid #21262d', background: '#161b22', height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}
            >
              {activities.length === 0 ? (
                <div style={{ display: 'flex', flex: 1, alignItems: 'center', justifyContent: 'center', color: '#6e7681', fontSize: 13 }}>
                  {t('app.dashboard.emptyActivity')}
                </div>
              ) : (
                <List
                  dataSource={activities}
                  renderItem={(item) => (
                    <List.Item style={{ borderBottom: '1px solid #21262d', padding: '10px 0', gap: 12 }}>
                      <GradientAvatar initials={getInitials(item.actor)} color={getAvatarColor(item.actor)} size={32} />
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <p style={{ fontSize: 13, lineHeight: 1.5, margin: 0, color: '#8b949e' }}>
                          <strong style={{ color: '#e6edf3' }}>{item.actor}</strong> {item.text}
                        </p>
                        <div style={{ fontSize: 11, color: '#6e7681', marginTop: 2, display: 'flex', alignItems: 'center', gap: 4 }}>
                          <ClockCircleOutlined style={{ fontSize: 10 }} /> {item.time}
                        </div>
                      </div>
                    </List.Item>
                  )}
                />
              )}
            </Card>
          </Col>
          <Col span={8} style={{ height: '100%' }}>
            <div style={{ height: '100%', display: 'flex', flexDirection: 'column', gap: 16 }}>
              <Card
                title={<span style={{ fontSize: 14, fontWeight: 600, color: '#e6edf3' }}>{t('app.dashboard.yourRepositories')}</span>}
                extra={
                  <ButtonLink onClick={() => navigate('/repositories')} label={`${t('app.dashboard.viewAll')} →`} />
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
                      <div style={{ width: 8, height: 8, borderRadius: '50%', flexShrink: 0, background: repo.isPublic ? '#3fb950' : '#d29922' }} title={repo.isPublic ? 'Public' : 'Private'} />
                      <span style={{ fontSize: 13, fontWeight: 500, flex: 1, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {repo.name}
                      </span>
                      <span style={{ fontSize: 11, color: '#6e7681' }}>{repo.isPublic ? 'Public' : 'Private'}</span>
                    </div>
                  ))}
                </div>
              </Card>
              <Card
                title={<span style={{ fontSize: 14, fontWeight: 600, color: '#e6edf3' }}>{t('app.dashboard.contributionActivity')}</span>}
                styles={{ body: { padding: '0 20px 20px' } }}
                style={{ border: '1px solid #21262d', background: '#161b22', flexShrink: 0 }}
              >
                <p style={{ fontSize: 12, color: '#6e7681', marginBottom: 4 }}>
                  {contributions > 0
                    ? t('app.dashboard.contributionsCount', { count: contributions })
                    : t('app.dashboard.noContributions')}
                </p>
                <ContribGraph contributionsByDay={(dashboardData?.contributions_by_day ?? {}) as Record<string, number>} />
              </Card>
            </div>
          </Col>
        </Row>
      </div>
    </div>
  );
}

function ButtonLink({ onClick, label }: { onClick: () => void; label: string }) {
  const [hover, setHover] = useState(false);
  return (
    <button
      onClick={onClick}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        background: 'none',
        border: 'none',
        color: hover ? '#58a6ff' : '#8b949e',
        fontSize: 12,
        padding: 0,
        cursor: 'pointer',
      }}
    >
      {label}
    </button>
  );
}
