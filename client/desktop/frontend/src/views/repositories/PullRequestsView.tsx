import { useEffect, useState } from 'react';
import { Button } from 'antd';
import { useTranslation } from 'react-i18next';
import { PullRequestOutlined, MergeOutlined, CloseCircleOutlined, MessageOutlined, EyeOutlined, PlusOutlined } from '@ant-design/icons';
import { usePullRequestsStore } from '../../stores/pullRequests';
import type { PR } from '../../api/pullRequests';

const borderColor = '#21262d';
const hoverBg = '#1c2333';
const activeBg = 'rgba(31,111,235,0.15)';
const textSecondary = '#8b949e';
const textPrimary = '#e6edf3';
const textTertiary = '#6e7681';
const blueLight = '#58a6ff';
const bluePrimary = '#1f6feb';
const bgSecondary = '#161b22';

function relativeTime(dateStr: string): string {
  const now = Date.now();
  const diff = now - new Date(dateStr).getTime();
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

const statusIcon = (status: string) => {
  if (status === 'open') return <PullRequestOutlined style={{ color: '#3fb950', fontSize: 20 }} />;
  if (status === 'merged') return <MergeOutlined style={{ color: '#bc8cff', fontSize: 20 }} />;
  return <CloseCircleOutlined style={{ color: '#f85149', fontSize: 20 }} />;
};

interface PullRequestsViewProps {
  repoId: string;
  onOpenPR: (pr: PR) => void;
}

export default function PullRequestsView({ repoId, onOpenPR }: PullRequestsViewProps) {
  const { t } = useTranslation();
  const { pullRequests, fetchPullRequests } = usePullRequestsStore();
  const [filter, setFilter] = useState<'open' | 'merged' | 'closed' | 'all'>('open');

  useEffect(() => {
    fetchPullRequests(repoId);
  }, [repoId, fetchPullRequests]);

  const filterCounts = {
    open: pullRequests.filter((p) => p.status === 'open').length,
    merged: pullRequests.filter((p) => p.status === 'merged').length,
    closed: pullRequests.filter((p) => p.status === 'closed').length,
    all: pullRequests.length,
  };
  const filterOrder: Array<'open' | 'merged' | 'closed' | 'all'> = ['open', 'merged', 'closed', 'all'];
  const filtered = pullRequests.filter((p) => filter === 'all' || p.status === filter);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '8px 0', gap: 16, flexShrink: 0 }}>
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
                  if (!isActive) { e.currentTarget.style.background = hoverBg; e.currentTarget.style.color = textPrimary; }
                }}
                onMouseLeave={(e) => {
                  if (!isActive) { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = textSecondary; }
                }}
              >
                {f === 'open' && <PullRequestOutlined style={{ fontSize: 12 }} />}
                {f === 'merged' && <MergeOutlined style={{ fontSize: 12 }} />}
                {f === 'closed' && <CloseCircleOutlined style={{ fontSize: 12 }} />}
                {t(`app.pullRequests.filters.${f}`)}
                <span style={{ background: isActive ? 'rgba(31,111,235,0.2)' : bgSecondary, color: isActive ? blueLight : textTertiary, padding: '1px 7px', borderRadius: 10, fontSize: 11 }}>{filterCounts[f]}</span>
              </button>
            );
          })}
        </div>
        <Button type="primary" icon={<PlusOutlined style={{ fontSize: 14 }} />} style={{ background: bluePrimary, borderColor: bluePrimary, borderRadius: 8 }}>
          {t('app.pullRequests.newPullRequest')}
        </Button>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', minHeight: 0 }}>
        {filtered.length === 0 ? (
          <div style={{ padding: 40, textAlign: 'center', color: textTertiary }}>{t('app.pullRequests.title')}</div>
        ) : (
          filtered.map((pr) => (
            <div
              key={pr.id}
              onClick={() => onOpenPR(pr)}
              style={{ display: 'flex', gap: 12, padding: '14px 4px', borderBottom: `1px solid ${borderColor}`, cursor: 'pointer', transition: 'background 0.15s', alignItems: 'flex-start' }}
              onMouseEnter={(e) => { e.currentTarget.style.background = hoverBg; }}
              onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
            >
              <div style={{ marginTop: 2, fontSize: 20, flexShrink: 0 }}>{statusIcon(pr.status)}</div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 4, color: textPrimary, display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                  {pr.title}
                  {(pr.labels || []).map((l) => (
                    <span key={l.id} style={{ fontSize: 10, fontWeight: 600, borderRadius: 12, background: `${l.color}22`, color: l.color, padding: '2px 8px' }}>{l.name}</span>
                  ))}
                </div>
                <div style={{ fontSize: 12, color: textTertiary }}>
                  {t('app.pullRequests.openedBy', { id: pr.pr_number, author: pr.author?.full_name || pr.author?.username || 'Unknown', time: relativeTime(pr.created_at) })}
                </div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexShrink: 0 }}>
                <span style={{ fontSize: 12, color: textTertiary, display: 'flex', alignItems: 'center', gap: 4 }}>
                  <EyeOutlined style={{ color: '#d29922', fontSize: 14 }} /> {pr.review_count ?? 0}
                </span>
                <span style={{ fontSize: 12, color: textTertiary, display: 'flex', alignItems: 'center', gap: 4 }}>
                  <MessageOutlined style={{ color: blueLight, fontSize: 14 }} /> {pr.comment_count ?? 0}
                </span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}