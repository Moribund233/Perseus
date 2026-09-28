import { useEffect, useMemo, useState } from 'react';
import { Spin, Empty } from 'antd';
import { useTranslation } from 'react-i18next';
import { repositoriesApi } from '../../api/repositories';
import type { BlameResponse } from '../../api/repositories';

const borderColor = '#21262d';
const textPrimary = '#e6edf3';
const textSecondary = '#8b949e';
const textTertiary = '#6e7681';
const bgSecondary = '#161b22';

const avatarColors = ['#1f6feb', '#3fb950', '#58a6ff', '#bc8cff', '#d29922', '#f85149', '#f0883e', '#7956d9'];

function colorFor(sha: string): string {
  let hash = 0;
  for (let i = 0; i < sha.length; i += 1) hash = sha.charCodeAt(i) + ((hash << 5) - hash);
  return avatarColors[Math.abs(hash) % avatarColors.length];
}

export default function BlameView({ repoId, path, gitRef, content }: { repoId: string; path: string; gitRef: string; content: string }) {
  const { t } = useTranslation();
  const [blame, setBlame] = useState<BlameResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    repositoriesApi.getBlame(repoId, path, gitRef)
      .then((res) => { if (!cancelled) setBlame(res); })
      .catch(() => { if (!cancelled) setBlame(null); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [repoId, path, gitRef]);

  const lines = useMemo(() => content.split('\n'), [content]);

  const lineOwner = useMemo(() => {
    const owners: Array<BlameResponse['hunks'][number] | null> = new Array(lines.length).fill(null);
    if (!blame) return owners;
    for (const hunk of blame.hunks) {
      const start = hunk.final_start_line_number - 1;
      for (let i = start; i < start + hunk.lines_in_hunk && i < owners.length; i += 1) owners[i] = hunk;
    }
    return owners;
  }, [blame, lines.length]);

  if (loading) return <div style={{ textAlign: 'center', padding: 40 }}><Spin /></div>;
  if (!blame || blame.is_empty) {
    return (
      <div style={{ border: `1px solid ${borderColor}`, borderRadius: 12, background: bgSecondary }}>
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={<span style={{ color: textSecondary }}>{t('app.repositories.gitBrowser.noBlame')}</span>} style={{ padding: 40 }} />
      </div>
    );
  }

  return (
    <div style={{ flex: 1, minHeight: 0, border: `1px solid ${borderColor}`, borderRadius: '0 0 12px 12px', overflow: 'auto', background: '#0d1117' }}>
      {lines.map((line, i) => {
        const owner = lineOwner[i];
        const sha = owner?.final_commit_id ?? '';
        const color = sha ? colorFor(sha) : 'transparent';
        return (
          <div key={i} style={{ display: 'flex', fontSize: 12.5, lineHeight: '20px', fontFamily: "'JetBrains Mono','Fira Code','Consolas',monospace" }}>
            <span style={{ width: 44, flexShrink: 0, textAlign: 'right', paddingRight: 8, color: textTertiary, userSelect: 'none' }}>{i + 1}</span>
            <span
              title={owner ? `${owner.commit.summary} — ${owner.commit.author.name}` : ''}
              style={{ width: 200, flexShrink: 0, paddingLeft: 8, paddingRight: 8, color: owner ? color : textTertiary, borderLeft: `3px solid ${color}`, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', background: `${color}11` }}
            >
              {owner ? `${sha.slice(0, 7)} ${owner.commit.author.name}` : ''}
            </span>
            <span style={{ flex: 1, whiteSpace: 'pre-wrap', wordBreak: 'break-all', color: textPrimary, paddingLeft: 12, paddingRight: 12 }}>{line}</span>
          </div>
        );
      })}
    </div>
  );
}
