import { useCallback, useEffect, useMemo, useState } from 'react';
import { Select, Button, Spin, Empty } from 'antd';
import { SwapOutlined, BranchesOutlined, TagOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { repositoriesApi } from '../../api/repositories';
import type { RepoBranch, RepoTag, CompareResponse } from '../../api/repositories';
import DiffView from './DiffView';

const borderColor = '#21262d';
const textPrimary = '#e6edf3';
const textSecondary = '#8b949e';
const textTertiary = '#6e7681';
const bgSecondary = '#161b22';
const bgTertiary = '#1c2128';
const blue = '#58a6ff';

export default function CompareTab({ repoId, defaultBranch }: { repoId: string; defaultBranch: string }) {
  const { t } = useTranslation();
  const [branches, setBranches] = useState<RepoBranch[]>([]);
  const [tags, setTags] = useState<RepoTag[]>([]);
  const [base, setBase] = useState(defaultBranch);
  const [head, setHead] = useState(defaultBranch);
  const [result, setResult] = useState<CompareResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      repositoriesApi.getBranches(repoId).catch(() => [] as RepoBranch[]),
      repositoriesApi.listTags(repoId).catch(() => [] as RepoTag[]),
    ]).then(([b, tg]) => { setBranches(b); setTags(tg); });
  }, [repoId]);

  const options = useMemo(() => {
    const groups: { label: string; options: { value: string; label: string }[] }[] = [];
    if (branches.length) groups.push({ label: t('app.repositories.gitBrowser.branchesGroup'), options: branches.map((b) => ({ value: b.name, label: b.name })) });
    if (tags.length) groups.push({ label: t('app.repositories.gitBrowser.tagsGroup'), options: tags.map((tg) => ({ value: tg.name, label: tg.name })) });
    if (!groups.length) groups.push({ label: t('app.repositories.gitBrowser.branchesGroup'), options: [{ value: defaultBranch, label: defaultBranch }] });
    return groups;
  }, [branches, tags, defaultBranch, t]);

  const runCompare = useCallback(async () => {
    if (!base || !head) return;
    setLoading(true);
    setError(null);
    try {
      setResult(await repositoriesApi.getCompare(repoId, base, head));
    } catch (e) {
      setResult(null);
      setError((e as Error).message || t('app.repositories.gitBrowser.compareFailed'));
    } finally {
      setLoading(false);
    }
  }, [repoId, base, head, t]);

  return (
    <div>
      <h3 style={{ fontSize: 16, fontWeight: 600, margin: '0 0 16px', color: textPrimary, display: 'flex', alignItems: 'center', gap: 8 }}>
        <SwapOutlined style={{ color: blue }} />
        {t('app.repositories.gitBrowser.compareTitle')}
      </h3>

      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16, flexWrap: 'wrap' }}>
        <span style={{ fontSize: 13, color: textSecondary }}>{t('app.repositories.gitBrowser.base')}</span>
        <Select
          value={base}
          onChange={setBase}
          style={{ minWidth: 200 }}
          size="small"
          suffixIcon={<BranchesOutlined />}
          options={options}
        />
        <SwapOutlined style={{ color: textTertiary }} />
        <span style={{ fontSize: 13, color: textSecondary }}>{t('app.repositories.gitBrowser.head')}</span>
        <Select
          value={head}
          onChange={setHead}
          style={{ minWidth: 200 }}
          size="small"
          suffixIcon={<TagOutlined />}
          options={options}
        />
        <Button type="primary" size="small" disabled={!base || !head || base === head} loading={loading} onClick={runCompare}>
          {t('app.repositories.gitBrowser.compare')}
        </Button>
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: 48 }}><Spin /></div>
      ) : error ? (
        <div style={{ border: '1px solid #f85149', borderRadius: 10, background: 'rgba(248,81,73,0.1)', color: '#f85149', padding: 12, fontSize: 13 }}>{error}</div>
      ) : !result ? (
        <div style={{ border: `1px solid ${borderColor}`, borderRadius: 12, background: bgSecondary }}>
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={<span style={{ color: textSecondary }}>{t('app.repositories.gitBrowser.compareHint')}</span>} style={{ padding: 40 }} />
        </div>
      ) : (
        <>
          <div style={{ border: `1px solid ${borderColor}`, borderRadius: 10, background: bgTertiary, padding: '10px 16px', marginBottom: 12, fontSize: 13, color: textSecondary, display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
            <span style={{ fontFamily: 'monospace', color: textPrimary }}>{result.base.slice(0, 7)}</span>
            <SwapOutlined style={{ color: textTertiary }} />
            <span style={{ fontFamily: 'monospace', color: textPrimary }}>{result.head.slice(0, 7)}</span>
            <span>· {t('app.repositories.gitBrowser.aheadBy', { count: result.ahead_by })}</span>
            <span>· {t('app.repositories.gitBrowser.filesChanged', { count: result.stats.files_changed })}</span>
            <span style={{ color: '#3fb950' }}>+{result.stats.additions}</span>
            <span style={{ color: '#f85149' }}>-{result.stats.deletions}</span>
          </div>

          {result.commits.length > 0 && (
            <div style={{ border: `1px solid ${borderColor}`, borderRadius: 10, overflow: 'hidden', background: bgSecondary, marginBottom: 16 }}>
              {result.commits.map((c, i) => (
                <div key={c.sha} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 16px', borderBottom: i === result.commits.length - 1 ? 'none' : `1px solid ${borderColor}`, fontSize: 13 }}>
                  <span style={{ flex: 1, minWidth: 0, color: textPrimary, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{c.summary}</span>
                  <span style={{ color: textTertiary, fontSize: 12, flexShrink: 0 }}>{c.author.name}</span>
                  <span style={{ fontFamily: 'monospace', color: blue, flexShrink: 0 }}>{c.sha.slice(0, 7)}</span>
                </div>
              ))}
            </div>
          )}

          <DiffView files={result.files} />
        </>
      )}
    </div>
  );
}
