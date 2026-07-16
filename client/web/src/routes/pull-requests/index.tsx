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
import { usePullRequestsStore } from '../../stores/pullRequests';
import { useAuthStore } from '../../stores/auth';
import { useRepositoriesStore } from '../../stores/repositories';

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
  id: string;
  title: string;
  author: string;
  time: string;
  status: 'open' | 'merged' | 'closed';
  labels: Label[];
  comments: number;
  reviews: number;
  avatars: string[];
}

const labelColorMap: Record<string, string> = {
  bug: '#f85149',
  feature: '#3fb950',
  enhancement: '#bc8cff',
  urgent: '#d29922',
};

const avatarColors = ['#1f6feb', '#3fb950', '#58a6ff', '#bc8cff', '#d29922', '#f85149', '#f0883e', '#7956d9'];

function relativeTime(dateStr: string): string {
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diff = now - then;
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);
  const weeks = Math.floor(days / 7);
  const months = Math.floor(days / 30);
  if (minutes < 1) return 'just now';
  if (minutes < 60) return `${minutes}m ago`;
  if (hours < 24) return `${hours}h ago`;
  if (days < 7) return `${days}d ago`;
  if (weeks < 5) return `${weeks}w ago`;
  return `${months}mo ago`;
}

function getInitials(name: string): string {
  return name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2) || '?';
}

function getAvatarColor(initials: string): string {
  let hash = 0;
  for (let i = 0; i < initials.length; i++) {
    hash = initials.charCodeAt(i) + ((hash << 5) - hash);
  }
  return avatarColors[Math.abs(hash) % avatarColors.length];
}

function resolveLabelColor(color: string): string {
  return color.startsWith('#') ? color : (labelColorMap[color] || '#8b949e');
}

const statusIcon = (status: string) => {
  if (status === 'open') return <PullRequestOutlined style={{ color: '#3fb950', fontSize: 20 }} />;
  if (status === 'merged') return <MergeOutlined style={{ color: '#bc8cff', fontSize: 20 }} />;
  return <CloseCircleOutlined style={{ color: '#f85149', fontSize: 20 }} />;
};

export default function PullRequestsPage() {
  const { user } = useAuthStore();
  const { repositories, fetchRepositoriesByUser, isLoading: repoLoading, error: repoError } = useRepositoriesStore();
  const { pullRequests, isLoading: prLoading, error: prError, fetchPullRequests } = usePullRequestsStore();

  const [selectedRepoId, setSelectedRepoId] = useState<string | null>(null);
  const [filter, setFilter] = useState<'open' | 'merged' | 'closed' | 'all'>('open');
  const [initialLoading, setInitialLoading] = useState(true);
  const { t } = useTranslation();

  const activeRepoId = selectedRepoId ?? repositories[0]?.id;
  const error = repoError || prError;

  useEffect(() => {
    if (user?.id) {
      fetchRepositoriesByUser(user.id);
    }
  }, [user?.id, fetchRepositoriesByUser]);

  useEffect(() => {
    if (activeRepoId) {
      fetchPullRequests(activeRepoId);
    }
  }, [activeRepoId, fetchPullRequests]);

  useEffect(() => {
    if (pullRequests.length > 0 || prError || (!prLoading && !repoLoading)) {
      setInitialLoading(false);
    }
  }, [pullRequests.length, prError, prLoading, repoLoading]);

  if (initialLoading) {
    return <PullRequestsSkeleton />;
  }

  const mappedPRs: PR[] = pullRequests.map((pr) => {
    const authorName = pr.author?.full_name || pr.author?.username || 'Unknown';
    const initials = getInitials(authorName);
    return {
      id: pr.pr_number,
      title: pr.title,
      author: authorName,
      time: relativeTime(pr.created_at),
      status: pr.status,
      labels: (pr.labels || []).map((l) => ({ name: l.name, color: l.color })),
      comments: pr.comment_count ?? 0,
      reviews: pr.review_count ?? 0,
      avatars: [initials],
    };
  });

  const filterCounts = {
    open: pullRequests.filter((p) => p.status === 'open').length,
    merged: pullRequests.filter((p) => p.status === 'merged').length,
    closed: pullRequests.filter((p) => p.status === 'closed').length,
    all: pullRequests.length,
  };

  const filterOrder: Array<'open' | 'merged' | 'closed' | 'all'> = ['open', 'merged', 'closed', 'all'];
  const filtered = mappedPRs.filter((p) => filter === 'all' || p.status === filter);

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
            {repositories.length > 1 && (
              <select
                value={activeRepoId ?? ''}
                onChange={(e) => setSelectedRepoId(e.target.value)}
                style={{
                  background: bgSecondary,
                  color: textPrimary,
                  border: `1px solid ${borderColor}`,
                  borderRadius: 6,
                  padding: '4px 8px',
                  fontSize: 13,
                  cursor: 'pointer',
                  outline: 'none',
                }}
              >
                {repositories.map((r) => (
                  <option key={r.id} value={r.id}>{r.name}</option>
                ))}
              </select>
            )}
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

        {error && (
          <div style={{ padding: '12px 24px', color: '#f85149', fontSize: 13, borderBottom: `1px solid ${borderColor}` }}>
            {error}
          </div>
        )}

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
                  {pr.labels.map((l) => {
                    const lc = resolveLabelColor(l.color);
                    return (
                      <Tag
                        key={l.name}
                        style={{
                          fontSize: 10,
                          fontWeight: 600,
                          borderRadius: 12,
                          background: `${lc}22`,
                          color: lc,
                          border: 'none',
                          margin: 0,
                          padding: '2px 8px',
                        }}
                      >
                        {l.name}
                      </Tag>
                    );
                  })}
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
                        background: getAvatarColor(a),
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
