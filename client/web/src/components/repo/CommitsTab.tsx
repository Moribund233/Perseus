import { useCallback, useEffect, useMemo, useState } from 'react';
import { Select, Button, Spin, Empty, Segmented } from 'antd';
import { BranchesOutlined, HistoryOutlined, PartitionOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { repositoriesApi } from '../../api/repositories';
import type { RepoBranch, CommitGraphNode } from '../../api/repositories';

const borderColor = '#21262d';
const hoverBg = '#1c2333';
const textPrimary = '#e6edf3';
const textSecondary = '#8b949e';
const textTertiary = '#6e7681';
const bgSecondary = '#161b22';
const blue = '#58a6ff';
const green = '#3fb950';
const purple = '#bc8cff';
const amber = '#d29922';

const LANE_W = 14;
const ROW_H = 46;
const laneColors = ['#58a6ff', '#3fb950', '#bc8cff', '#d29922', '#f85149', '#f0883e', '#7956d9', '#39c5cf'];

function relativeTime(dateStr: string, t: (k: string, o?: Record<string, unknown>) => string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  if (Number.isNaN(diff)) return '';
  if (diff < 60_000) return t('app.repositories.gitBrowser.time.justNow');
  if (diff < 3_600_000) return t('app.repositories.gitBrowser.time.minutes', { n: Math.floor(diff / 60_000) });
  if (diff < 86_400_000) return t('app.repositories.gitBrowser.time.hours', { n: Math.floor(diff / 3_600_000) });
  if (diff < 7 * 86_400_000) return t('app.repositories.gitBrowser.time.days', { n: Math.floor(diff / 86_400_000) });
  if (diff < 30 * 86_400_000) return t('app.repositories.gitBrowser.time.months', { n: Math.floor(diff / (30 * 86_400_000)) });
  return t('app.repositories.gitBrowser.time.years', { n: Math.floor(diff / (365 * 86_400_000)) });
}

/** 计算每个提交所在泳道（简化版提交图布局） */
function computeLanes(commits: CommitGraphNode[]): { lane: number; width: number; active: (string | null)[] }[] {
  const lanes: (string | null)[] = [];
  return commits.map((c) => {
    let lane = lanes.indexOf(c.sha);
    if (lane === -1) {
      lane = lanes.length;
      lanes.push(c.sha);
    }
    if (c.parents.length === 0) {
      lanes[lane] = null;
    } else {
      lanes[lane] = c.parents[0];
    }
    for (let p = 1; p < c.parents.length; p += 1) {
      if (!lanes.includes(c.parents[p])) lanes.push(c.parents[p]);
    }
    return { lane, width: lanes.length, active: [...lanes] };
  });
}

function GraphRow({ node, layout }: { node: CommitGraphNode; layout: { lane: number; width: number; active: (string | null)[] } }) {
  const { t } = useTranslation();
  const width = Math.max(layout.width, 1) * LANE_W;
  return (
    <div style={{ display: 'flex', alignItems: 'center', borderBottom: `1px solid ${borderColor}` }}>
      <svg width={width + LANE_W} height={ROW_H} style={{ flexShrink: 0 }}>
        {layout.active.map((sha, i) => {
          if (!sha && i !== layout.lane) return null;
          const x = i * LANE_W + LANE_W / 2;
          return (
            <line key={i} x1={x} y1={0} x2={x} y2={ROW_H} stroke={laneColors[i % laneColors.length]} strokeWidth={1.5} opacity={0.55} />
          );
        })}
        <circle cx={layout.lane * LANE_W + LANE_W / 2} cy={ROW_H / 2} r={4.5} fill={laneColors[layout.lane % laneColors.length]} stroke={bgSecondary} strokeWidth={1.5} />
      </svg>
      <div style={{ flex: 1, minWidth: 0, padding: '6px 8px 6px 4px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          <span style={{ color: textPrimary, fontSize: 13, fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{node.summary || node.message.split('\n')[0]}</span>
          {node.labels.map((label) => {
            const isTag = label.startsWith('tag:');
            const isHead = label === 'HEAD';
            const color = isHead ? amber : isTag ? purple : green;
            return (
              <span key={label} style={{ fontSize: 10, fontWeight: 600, padding: '1px 7px', borderRadius: 10, border: `1px solid ${color}55`, color, flexShrink: 0 }}>
                {label}
              </span>
            );
          })}
        </div>
        <div style={{ fontSize: 11.5, color: textTertiary, marginTop: 2, display: 'flex', gap: 8 }}>
          <span style={{ fontFamily: 'monospace', color: blue }}>{node.sha.slice(0, 7)}</span>
          <span>{node.author.name}</span>
          <span>{relativeTime(node.author.date, t)}</span>
          {node.is_merge && <span style={{ color: purple }}>{t('app.repositories.gitBrowser.merge')}</span>}
        </div>
      </div>
    </div>
  );
}

export default function CommitsTab({ repoId, defaultBranch }: { repoId: string; defaultBranch: string }) {
  const { t } = useTranslation();
  const [branches, setBranches] = useState<RepoBranch[]>([]);
  const [ref, setRef] = useState(defaultBranch);
  const [mode, setMode] = useState<'list' | 'graph'>('list');
  const [commits, setCommits] = useState<CommitGraphNode[]>([]);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const perPage = 30;

  useEffect(() => {
    repositoriesApi.getBranches(repoId).then(setBranches).catch(() => setBranches([]));
  }, [repoId]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      if (mode === 'graph') {
        const res = await repositoriesApi.getGraph(repoId, { ref, limit: 100 });
        setCommits(res.commits ?? []);
      } else {
        const res = await repositoriesApi.getCommits(repoId, { branch: ref, page, per_page: perPage });
        setCommits((res.commits ?? []).map((c) => ({
          sha: c.sha,
          parents: c.parents ?? [],
          summary: c.message.split('\n')[0],
          message: c.message,
          author: c.author,
          committer: c.committer ?? c.author,
          date: c.author.date,
          labels: [],
          is_merge: (c.parents?.length ?? 0) > 1,
        })));
      }
    } catch {
      setCommits([]);
    } finally {
      setLoading(false);
    }
  }, [repoId, ref, mode, page]);

  useEffect(() => {
    Promise.resolve().then(load);
  }, [load]);

  const layouts = useMemo(() => (mode === 'graph' ? computeLanes(commits) : []), [mode, commits]);
  const hasNext = mode === 'list' && commits.length === perPage;

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
        <h3 style={{ fontSize: 16, fontWeight: 600, margin: 0, color: textPrimary, display: 'flex', alignItems: 'center', gap: 8 }}>
          <HistoryOutlined style={{ color: blue }} />
          {t('app.repositories.gitBrowser.commitsTitle')}
        </h3>
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 10 }}>
          <Select
            value={ref}
            onChange={(v) => { setRef(v); setPage(1); }}
            size="small"
            style={{ minWidth: 180 }}
            suffixIcon={<BranchesOutlined />}
            options={(branches.length ? branches : [{ name: defaultBranch } as RepoBranch]).map((b) => ({ value: b.name, label: b.name }))}
          />
          <Segmented
            size="small"
            value={mode}
            onChange={(v) => setMode(v as 'list' | 'graph')}
            options={[
              { value: 'list', label: t('app.repositories.gitBrowser.list') },
              { value: 'graph', icon: <PartitionOutlined />, label: t('app.repositories.gitBrowser.graph') },
            ]}
          />
        </div>
      </div>

      {loading && commits.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 48 }}><Spin /></div>
      ) : commits.length === 0 ? (
        <div style={{ border: `1px solid ${borderColor}`, borderRadius: 12, background: bgSecondary }}>
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={<span style={{ color: textSecondary }}>{t('app.repositories.gitBrowser.noCommits')}</span>} style={{ padding: 40 }} />
        </div>
      ) : mode === 'graph' ? (
        <div style={{ border: `1px solid ${borderColor}`, borderRadius: 12, overflow: 'hidden', background: bgSecondary }}>
          {commits.map((c, i) => <GraphRow key={c.sha} node={c} layout={layouts[i]} />)}
        </div>
      ) : (
        <>
          <div style={{ border: `1px solid ${borderColor}`, borderRadius: 12, overflow: 'hidden', background: bgSecondary }}>
            {commits.map((c, i) => (
              <div
                key={c.sha}
                style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '10px 16px', borderBottom: i === commits.length - 1 ? 'none' : `1px solid ${borderColor}`, fontSize: 13 }}
                onMouseEnter={(e) => { e.currentTarget.style.background = hoverBg; }}
                onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
              >
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ color: textPrimary, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{c.summary}</div>
                  <div style={{ fontSize: 12, color: textTertiary, marginTop: 2 }}>{c.author.name} · {relativeTime(c.author.date, t)}</div>
                </div>
                <span style={{ fontFamily: 'monospace', color: blue, flexShrink: 0 }}>{c.sha.slice(0, 7)}</span>
              </div>
            ))}
          </div>
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 16 }}>
            <Button size="small" disabled={page <= 1} onClick={() => setPage((p) => Math.max(1, p - 1))}>{t('app.repositories.gitBrowser.prev')}</Button>
            <Button size="small" disabled={!hasNext} onClick={() => setPage((p) => p + 1)}>{t('app.repositories.gitBrowser.next')}</Button>
          </div>
        </>
      )}
    </div>
  );
}
