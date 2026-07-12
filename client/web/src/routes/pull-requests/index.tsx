import { useState, useEffect } from 'react';
import { Layout, Avatar, Button, Tag } from 'antd';
import {
  PullRequestOutlined,
  MergeOutlined,
  CloseCircleOutlined,
  MessageOutlined,
  EyeOutlined,
  FilterOutlined,
  PlusOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import PullRequestsSkeleton from '../../components/skeleton/PullRequestsSkeleton';

const { Content } = Layout;

const borderColor = '#21262d';
const hoverBg = '#1c2333';
const activeBg = 'rgba(31,111,235,0.15)';
const textSecondary = '#8b949e';
const textPrimary = '#e6edf3';
const textTertiary = '#6e7681';
const blueLight = '#58a6ff';
const bluePrimary = '#1f6feb';
const bgSecondary = '#161b22';

interface Label {
  name: string;
  color: string;
}

interface PR {
  id: number;
  title: string;
  author: string;
  time: string;
  status: 'open' | 'merged' | 'closed';
  labels: Label[];
  comments: number;
  reviews: number;
  avatars: string[];
}

const prs: PR[] = [
  { id: 142, title: 'Add WebSocket support for real-time sync', author: 'Wang Jun', time: '1 hour ago', status: 'open', labels: [{ name: 'feature', color: 'green' }, { name: 'urgent', color: 'orange' }], comments: 4, reviews: 2, avatars: ['WJ', 'LW', 'CM'] },
  { id: 148, title: 'Refactor repository tree renderer', author: 'Li Wei', time: '3 hours ago', status: 'open', labels: [{ name: 'enhancement', color: 'purple' }], comments: 1, reviews: 0, avatars: ['LW'] },
  { id: 135, title: 'Fix memory leak in file watcher', author: 'Huang Yan', time: '2 days ago', status: 'merged', labels: [{ name: 'bug', color: 'red' }], comments: 7, reviews: 3, avatars: ['HY', 'ZL'] },
  { id: 128, title: 'Update CI pipeline to use new runner', author: 'Chen Mei', time: '3 days ago', status: 'closed', labels: [{ name: 'enhancement', color: 'purple' }], comments: 2, reviews: 1, avatars: ['CM'] },
];

const labelColorMap: Record<string, string> = {
  bug: '#f85149',
  feature: '#3fb950',
  enhancement: '#bc8cff',
  urgent: '#d29922',
};

const avatarColorMap: Record<string, string> = {
  ZL: '#1f6feb',
  LW: '#3fb950',
  CM: '#58a6ff',
  WJ: '#bc8cff',
  HY: '#d29922',
};

const statusIcon = (status: string) => {
  if (status === 'open') return <PullRequestOutlined style={{ color: '#3fb950', fontSize: 20 }} />;
  if (status === 'merged') return <MergeOutlined style={{ color: '#bc8cff', fontSize: 20 }} />;
  return <CloseCircleOutlined style={{ color: '#f85149', fontSize: 20 }} />;
};

export default function PullRequestsPage() {
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<'open' | 'merged' | 'closed' | 'all'>('open');
  const { t } = useTranslation();

  useEffect(() => {
    const timer = setTimeout(() => setLoading(false), 600);
    return () => clearTimeout(timer);
  }, []);

  if (loading) return <PullRequestsSkeleton />;

  const filtered = prs.filter((p) => filter === 'all' || p.status === filter);
  const filterCounts = { open: 5, merged: 128, closed: 14, all: 147 };
  const filterOrder: Array<'open' | 'merged' | 'closed' | 'all'> = ['open', 'merged', 'closed', 'all'];

  return (
    <Layout style={{ height: '100%', background: 'transparent' }}>
      <Content style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
        {/* Toolbar */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '16px 24px',
            borderBottom: `1px solid ${borderColor}`,
            flexShrink: 0,
            gap: 16,
          }}
        >
          <div style={{ display: 'flex', gap: 4 }}>
            {filterOrder.map((f) => {
              const isActive = filter === f;
              return (
                <button
                  key={f}
                  onClick={() => setFilter(f)}
                  style={{
                    padding: '6px 14px',
                    borderRadius: 8,
                    border: 'none',
                    background: isActive ? activeBg : 'transparent',
                    color: isActive ? blueLight : textSecondary,
                    cursor: 'pointer',
                    fontSize: 13,
                    fontWeight: 500,
                    display: 'flex',
                    alignItems: 'center',
                    gap: 6,
                    transition: 'all 0.15s',
                  }}
                  onMouseEnter={(e) => {
                    if (!isActive) {
                      e.currentTarget.style.background = hoverBg;
                      e.currentTarget.style.color = textPrimary;
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!isActive) {
                      e.currentTarget.style.background = 'transparent';
                      e.currentTarget.style.color = textSecondary;
                    }
                  }}
                >
                  {f === 'open' && <PullRequestOutlined style={{ fontSize: 12 }} />}
                  {f === 'merged' && <MergeOutlined style={{ fontSize: 12 }} />}
                  {f === 'closed' && <CloseCircleOutlined style={{ fontSize: 12 }} />}
                  {t(`app.pullRequests.filters.${f}`)}
                  <span
                    style={{
                      background: isActive ? 'rgba(31,111,235,0.2)' : bgSecondary,
                      color: isActive ? blueLight : textTertiary,
                      padding: '1px 7px',
                      borderRadius: 10,
                      fontSize: 11,
                    }}
                  >
                    {filterCounts[f]}
                  </span>
                </button>
              );
            })}
          </div>
          <div style={{ display: 'flex', gap: 8, flexShrink: 0 }}>
            <Button
              icon={<FilterOutlined style={{ fontSize: 14 }} />}
              style={{
                background: bgSecondary,
                color: textSecondary,
                border: `1px solid ${borderColor}`,
                borderRadius: 8,
                fontSize: 13,
                height: 32,
                display: 'flex',
                alignItems: 'center',
                gap: 6,
              }}
              onMouseEnter={(e) => { e.currentTarget.style.borderColor = textTertiary; e.currentTarget.style.color = textPrimary; }}
              onMouseLeave={(e) => { e.currentTarget.style.borderColor = borderColor; e.currentTarget.style.color = textSecondary; }}
            >
              {t('app.pullRequests.filter')}
            </Button>
            <Button
              type="primary"
              icon={<PlusOutlined style={{ fontSize: 14 }} />}
              style={{
                background: bluePrimary,
                borderColor: bluePrimary,
                borderRadius: 8,
                fontSize: 13,
                height: 32,
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                fontWeight: 500,
              }}
            >
              {t('app.pullRequests.newPullRequest')}
            </Button>
          </div>
        </div>

        {/* PR List */}
        <div style={{ flex: 1, overflow: 'auto', padding: '0 24px' }}>
          {filtered.map((pr) => (
            <div
              key={pr.id}
              style={{
                display: 'flex',
                gap: 12,
                padding: '16px 24px',
                margin: '0 -24px',
                borderBottom: `1px solid ${borderColor}`,
                cursor: 'pointer',
                transition: 'background 0.15s',
                alignItems: 'flex-start',
              }}
              onMouseEnter={(e) => { e.currentTarget.style.background = hoverBg; }}
              onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
            >
              <div style={{ marginTop: 2, fontSize: 20, flexShrink: 0 }}>{statusIcon(pr.status)}</div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div
                  style={{
                    fontSize: 14,
                    fontWeight: 600,
                    marginBottom: 4,
                    display: 'flex',
                    alignItems: 'center',
                    gap: 8,
                    color: textPrimary,
                    flexWrap: 'wrap',
                  }}
                >
                  {pr.title}
                  {pr.labels.map((l) => (
                    <Tag
                      key={l.name}
                      style={{
                        fontSize: 10,
                        fontWeight: 600,
                        borderRadius: 12,
                        background: `${labelColorMap[l.color]}22`,
                        color: labelColorMap[l.color],
                        border: 'none',
                        margin: 0,
                        padding: '2px 8px',
                      }}
                    >
                      {l.name}
                    </Tag>
                  ))}
                </div>
                <div style={{ fontSize: 12, color: textTertiary }}>
                  {t('app.pullRequests.openedBy', { id: pr.id, author: pr.author, time: pr.time })}
                </div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 16, flexShrink: 0 }}>
                <span style={{ fontSize: 12, color: textTertiary, display: 'flex', alignItems: 'center', gap: 4 }}>
                  <EyeOutlined style={{ color: '#d29922', fontSize: 14 }} /> {pr.reviews}
                </span>
                <span style={{ fontSize: 12, color: textTertiary, display: 'flex', alignItems: 'center', gap: 4 }}>
                  <MessageOutlined style={{ color: blueLight, fontSize: 14 }} /> {pr.comments}
                </span>
                <div style={{ display: 'flex', alignItems: 'center' }}>
                  {pr.avatars.map((a, i) => (
                    <Avatar
                      key={a}
                      size={24}
                      style={{
                        background: avatarColorMap[a] || bluePrimary,
                        fontSize: 9,
                        fontWeight: 600,
                        marginLeft: i > 0 ? -8 : 0,
                        border: `2px solid ${bgSecondary}`,
                      }}
                    >
                      {a}
                    </Avatar>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>
      </Content>
    </Layout>
  );
}
