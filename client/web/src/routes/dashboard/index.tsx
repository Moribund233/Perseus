import { useState, useEffect } from 'react';
import { Card, Row, Col, List, Button } from 'antd';
import {
  AppstoreOutlined,
  PullRequestOutlined,
  TeamOutlined,
  ForkOutlined,
  ArrowUpOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../stores/auth';
import DashboardSkeleton from '../../components/skeleton/DashboardSkeleton';

const stats = [
  { label: 'Repositories', value: '24', change: '↑ 3 this week', icon: <AppstoreOutlined />, color: '#58a6ff', bg: 'rgba(31,111,235,0.15)' },
  { label: 'Open PRs', value: '12', change: '↑ 5 need review', icon: <PullRequestOutlined />, color: '#3fb950', bg: 'rgba(63,185,80,0.15)' },
  { label: 'Team Members', value: '8', change: '↑ 2 new', icon: <TeamOutlined />, color: '#bc8cff', bg: 'rgba(188,140,255,0.15)' },
  { label: 'Commits', value: '1,847', change: '↑ 142 this week', icon: <ForkOutlined />, color: '#d29922', bg: 'rgba(210,153,34,0.15)' },
];

const activities = [
  { name: 'Li Wei', initials: 'LW', gradient: 'linear-gradient(135deg,#3fb950,#238636)', action: 'merged PR <strong>#142</strong> in <strong>perseus-core</strong>', time: '12 minutes ago' },
  { name: 'Chen Mei', initials: 'CM', gradient: 'linear-gradient(135deg,#58a6ff,#1f6feb)', action: 'pushed 3 commits to <strong>feature/auth-module</strong>', time: '34 minutes ago' },
  { name: 'Wang Jun', initials: 'WJ', gradient: 'linear-gradient(135deg,#bc8cff,#8957e5)', action: 'opened PR <strong>#156</strong> — "Add WebSocket support for real-time sync"', time: '1 hour ago' },
  { name: 'You', initials: 'ZL', gradient: 'linear-gradient(135deg,#d29922,#9e6a03)', action: 'reviewed PR <strong>#148</strong> in <strong>perseus-editor</strong>', time: '2 hours ago' },
  { name: 'Huang Yan', initials: 'HY', gradient: 'linear-gradient(135deg,#f85149,#da3633)', action: 'created issue <strong>#89</strong> — "Memory leak in file watcher"', time: '3 hours ago' },
  { name: 'Chen Mei', initials: 'CM', gradient: 'linear-gradient(135deg,#58a6ff,#1f6feb)', action: 'commented on issue <strong>#85</strong> in <strong>perseus-api</strong>', time: '5 hours ago' },
];

const repos = [
  { name: 'perseus-core', lang: 'TypeScript', color: '#58a6ff' },
  { name: 'perseus-editor', lang: 'Rust', color: '#3fb950' },
  { name: 'perseus-api', lang: 'Go', color: '#bc8cff' },
  { name: 'perseus-web', lang: 'Vue', color: '#d29922' },
  { name: 'perseus-cli', lang: 'Rust', color: '#f85149' },
];

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
    const h = Math.random() * 100;
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

  useEffect(() => {
    const timer = setTimeout(() => setLoading(false), 600);
    return () => clearTimeout(timer);
  }, []);

  if (loading) {
    return <DashboardSkeleton />;
  }

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 4 }}>
          Welcome back,{' '}
          <span
            style={{
              background: 'linear-gradient(135deg,#58a6ff,#bc8cff)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
            }}
          >
            {user?.full_name || user?.username || 'Zhang Lei'}
          </span>
        </h1>
        <p style={{ color: '#8b949e', fontSize: 14 }}>Here&apos;s what&apos;s happening with your projects today.</p>
      </div>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
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
              <div style={{ fontSize: 28, fontWeight: 700, marginBottom: 2 }}>{s.value}</div>
              <div style={{ fontSize: 12, color: '#8b949e', textTransform: 'uppercase', letterSpacing: 0.5 }}>{s.label}</div>
              <div style={{ fontSize: 11, marginTop: 8, display: 'flex', alignItems: 'center', gap: 4, color: '#3fb950' }}>
                <ArrowUpOutlined /> {s.change}
              </div>
            </Card>
          </Col>
        ))}
      </Row>

      <Row gutter={[16, 16]}>
        <Col span={16}>
          <Card
            title={<span style={{ fontSize: 14, fontWeight: 600 }}>Recent Activity</span>}
            extra={<Button type="link" style={{ fontSize: 12, padding: 0 }}>View all →</Button>}
            styles={{ body: { padding: '0 20px 20px' } }}
            style={{ border: '1px solid #21262d', background: '#161b22' }}
          >
            <List
              dataSource={activities}
              renderItem={(item) => (
                <List.Item style={{ borderBottom: '1px solid #21262d', padding: '10px 0', gap: 12 }}>
                  <GradientAvatar initials={item.initials} gradient={item.gradient} size={32} />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <p
                      style={{ fontSize: 13, lineHeight: 1.5, margin: 0 }}
                      dangerouslySetInnerHTML={{ __html: `<strong>${item.name}</strong> ${item.action}` }}
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
        <Col span={8}>
          <Card
            title={<span style={{ fontSize: 14, fontWeight: 600 }}>Your Repositories</span>}
            extra={<Button type="link" style={{ fontSize: 12, padding: 0 }} onClick={() => navigate('/repositories')}>View all →</Button>}
            styles={{ body: { padding: '0 20px 20px' } }}
            style={{ border: '1px solid #21262d', background: '#161b22', marginBottom: 16 }}
          >
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {repos.map((repo) => (
                <div
                  key={repo.name}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 10,
                    padding: 10,
                    borderRadius: 8,
                    cursor: 'pointer',
                    transition: 'all 0.2s',
                  }}
                  className="repo-quick-item"
                  onClick={() => navigate('/repositories/perseus/' + repo.name)}
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
            title={<span style={{ fontSize: 14, fontWeight: 600 }}>Contribution Activity</span>}
            styles={{ body: { padding: '0 20px 20px' } }}
            style={{ border: '1px solid #21262d', background: '#161b22' }}
          >
            <p style={{ fontSize: 12, color: '#6e7681', marginBottom: 4 }}>142 contributions in the last 30 days</p>
            <ContribGraph />
          </Card>
        </Col>
      </Row>
    </div>
  );
}
