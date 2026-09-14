import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Input, Button, Empty, Spin, Tag } from 'antd';
import {
  SearchOutlined,
  FileTextOutlined,
  RightOutlined,
  DatabaseOutlined,
  ExclamationCircleOutlined,
  PullRequestOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { searchApi, type GlobalSearchResponse, type GlobalAggregateResponse } from '../../api/search';

const borderColor = '#21262d';
const hoverBg = '#1c2333';
const textPrimary = '#e6edf3';
const textSecondary = '#8b949e';
const textTertiary = '#6e7681';
const blueLight = '#58a6ff';
const bluePrimary = '#1f6feb';
const bgSecondary = '#161b22';
const bgInput = '#0d1117';

const statusColor = (status: string) =>
  status === 'open' ? '#3fb950' : status === 'merged' ? '#a371f7' : '#8b949e';

export default function GlobalSearchPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { t } = useTranslation();
  const initialQuery = searchParams.get('q') || '';
  const [query, setQuery] = useState(initialQuery);
  const [input, setInput] = useState(initialQuery);
  const [results, setResults] = useState<GlobalSearchResponse | null>(null);
  const [aggregate, setAggregate] = useState<GlobalAggregateResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [failed, setFailed] = useState(false);
  const [searched, setSearched] = useState(false);

  const doSearch = async (q: string) => {
    const trimmed = q.trim();
    if (!trimmed) return;
    setQuery(trimmed);
    setLoading(true);
    setFailed(false);
    try {
      const [codeRes, aggRes] = await Promise.all([
        searchApi.searchCode(trimmed).catch(() => null),
        searchApi.searchGlobal(trimmed, { per_type: 10 }).catch(() => null),
      ]);
      setResults(codeRes);
      setAggregate(aggRes);
      setSearched(true);
      if (!codeRes && !aggRes) setFailed(true);
    } catch {
      setFailed(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let cancelled = false;
    Promise.resolve().then(() => {
      if (cancelled) return;
      const q = searchParams.get('q') || '';
      setQuery(q);
      setInput(q);
      if (q.trim()) {
        doSearch(q);
      } else {
        setResults(null);
        setAggregate(null);
        setSearched(false);
      }
    });
    return () => { cancelled = true; };
  }, [searchParams]);

  const openFile = (repoPath: string, file: string, line: number) => {
    navigate(`/editor/${repoPath}?file=${encodeURIComponent(file)}&line=${line}`);
  };

  const hasAggregate =
    !!aggregate &&
    (aggregate.repositories.length > 0 ||
      aggregate.issues.length > 0 ||
      aggregate.pull_requests.length > 0);

  const sectionTitle = (icon: React.ReactNode, label: string) => (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, margin: '20px 0 10px', fontSize: 13, fontWeight: 600, color: textPrimary }}>
      {icon}
      {label}
    </div>
  );

  return (
    <div style={{ height: '100%', overflowY: 'auto', padding: 24 }}>
      <div style={{ maxWidth: 860, margin: '0 auto' }}>
        <div style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
          <Input
            size="large"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onPressEnter={() => { if (input.trim()) { if (input.trim() !== query) navigate(`/search?q=${encodeURIComponent(input.trim())}`, { replace: true }); else doSearch(input); } }}
            placeholder={t('app.search.placeholder')}
            prefix={<SearchOutlined style={{ color: textTertiary }} />}
            style={{ background: bgInput, borderColor, color: textPrimary, fontSize: 14 }}
          />
          <Button
            type="primary"
            size="large"
            loading={loading}
            onClick={() => { if (input.trim() && input.trim() !== query) navigate(`/search?q=${encodeURIComponent(input.trim())}`); }}
            style={{ background: bluePrimary, borderColor: bluePrimary, height: 40 }}
          >
            {t('app.search.button')}
          </Button>
        </div>

        {searched && (
          <div style={{ fontSize: 13, color: textSecondary, marginBottom: 16 }}>
            {t('app.search.resultsFor', { query })}
            <span style={{ color: textTertiary }}>
              {' '}· {t('app.search.resultCount', { count: results?.total_count ?? 0 })}
            </span>
          </div>
        )}

        {loading ? (
          <div style={{ display: 'flex', justifyContent: 'center', padding: 60 }}>
            <Spin />
          </div>
        ) : failed ? (
          <Empty description={t('app.search.failed')} style={{ padding: 40 }} />
        ) : searched && results && results.repositories.length === 0 && !hasAggregate ? (
          <Empty description={t('app.search.noResults', { query })} style={{ padding: 40 }} />
        ) : searched ? (
          <>
            {aggregate && aggregate.repositories.length > 0 && (
              <>
                {sectionTitle(<DatabaseOutlined style={{ color: blueLight }} />, t('app.search.groupRepos'))}
                <div style={{ border: `1px solid ${borderColor}`, background: bgSecondary, borderRadius: 8, overflow: 'hidden' }}>
                  {aggregate.repositories.map((repo) => (
                    <div
                      key={repo.repository_id}
                      onClick={() => navigate(`/repositories/${repo.path}`)}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 10,
                        padding: '10px 16px',
                        cursor: 'pointer',
                        borderTop: `1px solid ${borderColor}`,
                      }}
                      onMouseEnter={(e) => { e.currentTarget.style.background = hoverBg; }}
                      onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
                    >
                      <span style={{ width: 8, height: 8, borderRadius: '50%', background: blueLight, flexShrink: 0 }} />
                      <span style={{ color: textPrimary, fontSize: 14, fontWeight: 600 }}>{repo.path}</span>
                      <span style={{ flex: 1, fontSize: 12, color: textSecondary, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {repo.description || ''}
                      </span>
                      <RightOutlined style={{ color: textTertiary, fontSize: 11 }} />
                    </div>
                  ))}
                </div>
              </>
            )}

            {aggregate && aggregate.issues.length > 0 && (
              <>
                {sectionTitle(<ExclamationCircleOutlined style={{ color: '#3fb950' }} />, t('app.search.groupIssues'))}
                <div style={{ border: `1px solid ${borderColor}`, background: bgSecondary, borderRadius: 8, overflow: 'hidden' }}>
                  {aggregate.issues.map((issue) => (
                    <div
                      key={`${issue.repository_path}#${issue.issue_number}`}
                      onClick={() => navigate(`/repositories/${issue.repository_path}/issues/${issue.issue_number}`)}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 10,
                        padding: '9px 16px',
                        cursor: 'pointer',
                        borderTop: `1px solid ${borderColor}`,
                      }}
                      onMouseEnter={(e) => { e.currentTarget.style.background = hoverBg; }}
                      onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
                    >
                      <ExclamationCircleOutlined style={{ color: statusColor(issue.status), fontSize: 14 }} />
                      <span style={{ color: textSecondary, fontSize: 12, flexShrink: 0 }}>{issue.repository_path}</span>
                      <span style={{ color: textPrimary, fontSize: 13, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        #{issue.issue_number} {issue.title}
                      </span>
                      <span style={{ flex: 1 }} />
                      <Tag color={statusColor(issue.status)} style={{ marginInlineEnd: 0 }}>
                        {t(`app.issues.filters.${issue.status}`, issue.status)}
                      </Tag>
                    </div>
                  ))}
                </div>
              </>
            )}

            {aggregate && aggregate.pull_requests.length > 0 && (
              <>
                {sectionTitle(<PullRequestOutlined style={{ color: '#a371f7' }} />, t('app.search.groupPullRequests'))}
                <div style={{ border: `1px solid ${borderColor}`, background: bgSecondary, borderRadius: 8, overflow: 'hidden' }}>
                  {aggregate.pull_requests.map((pr) => (
                    <div
                      key={`${pr.repository_path}#${pr.pr_number}`}
                      onClick={() => navigate(`/repositories/${pr.repository_path}/pulls/${pr.pr_number}`)}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 10,
                        padding: '9px 16px',
                        cursor: 'pointer',
                        borderTop: `1px solid ${borderColor}`,
                      }}
                      onMouseEnter={(e) => { e.currentTarget.style.background = hoverBg; }}
                      onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
                    >
                      <PullRequestOutlined style={{ color: statusColor(pr.status), fontSize: 14 }} />
                      <span style={{ color: textSecondary, fontSize: 12, flexShrink: 0 }}>{pr.repository_path}</span>
                      <span style={{ color: textPrimary, fontSize: 13, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        #{pr.pr_number} {pr.title}
                      </span>
                      <span style={{ flex: 1 }} />
                      <Tag color={statusColor(pr.status)} style={{ marginInlineEnd: 0 }}>
                        {t(`app.pullRequests.filters.${pr.status}`, pr.status)}
                      </Tag>
                    </div>
                  ))}
                </div>
              </>
            )}

            {results && results.repositories.length > 0 && (
              <>
                {sectionTitle(<FileTextOutlined style={{ color: blueLight }} />, t('app.search.groupCode'))}
                {results.repositories.map((repo) => (
                  <div
                    key={repo.repository_id}
                    style={{
                      border: `1px solid ${borderColor}`,
                      background: bgSecondary,
                      borderRadius: 8,
                      marginBottom: 16,
                      overflow: 'hidden',
                    }}
                  >
                    <div
                      onClick={() => navigate(`/repositories/${repo.repository_path}`)}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 8,
                        padding: '10px 16px',
                        background: '#0d1117',
                        cursor: 'pointer',
                      }}
                      onMouseEnter={(e) => { e.currentTarget.style.background = hoverBg; }}
                      onMouseLeave={(e) => { e.currentTarget.style.background = '#0d1117'; }}
                    >
                      <span style={{ width: 8, height: 8, borderRadius: '50%', background: blueLight, flexShrink: 0 }} />
                      <span style={{ color: textPrimary, fontSize: 14, fontWeight: 600 }}>{repo.repository_path}</span>
                      <span style={{ flex: 1 }} />
                      <span style={{ fontSize: 12, color: textTertiary }}>
                        {repo.total_count} {t('app.search.matches')}
                      </span>
                      <RightOutlined style={{ color: textTertiary, fontSize: 11 }} />
                    </div>

                    {repo.results.map((hit) => (
                      <div
                        key={`${hit.file}:${hit.line}`}
                        onClick={() => openFile(repo.repository_path, hit.file, hit.line)}
                        style={{
                          display: 'flex',
                          alignItems: 'flex-start',
                          gap: 10,
                          padding: '9px 16px',
                          borderTop: `1px solid ${borderColor}`,
                          cursor: 'pointer',
                        }}
                        onMouseEnter={(e) => { e.currentTarget.style.background = hoverBg; }}
                        onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
                      >
                        <FileTextOutlined style={{ color: textTertiary, marginTop: 3, fontSize: 13 }} />
                        <div style={{ minWidth: 0, flex: 1 }}>
                          <div style={{ fontSize: 13, color: textPrimary, fontFamily: 'monospace', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                            {hit.file}
                            <span style={{ color: textTertiary }}>:{hit.line}</span>
                          </div>
                          <div
                            style={{
                              fontSize: 13,
                              color: textSecondary,
                              marginTop: 2,
                              whiteSpace: 'pre-wrap',
                              wordBreak: 'break-word',
                              fontFamily: 'monospace',
                              background: 'rgba(0,0,0,0.2)',
                              padding: '6px 10px',
                              borderRadius: 4,
                              lineHeight: 1.5,
                            }}
                          >
                            {hit.content.trim() || '…'}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ))}
              </>
            )}
          </>
        ) : (
          <div style={{ textAlign: 'center', color: textTertiary, fontSize: 13, padding: 60 }}>
            {t('app.search.initialHint')}
          </div>
        )}
      </div>
    </div>
  );
}