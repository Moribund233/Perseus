import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { SearchOutlined, FileTextOutlined, RightOutlined, LoadingOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { searchApi, type GlobalSearchResponse } from '../../api/search';

const borderColor = '#21262d';
const hoverBg = '#1c2333';
const textPrimary = '#e6edf3';
const textSecondary = '#8b949e';
const textTertiary = '#6e7681';
const blueLight = '#58a6ff';
const bgDropdown = '#161b22';
const bgInput = '#0d1117';

export default function GlobalSearch() {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<GlobalSearchResponse | null>(null);
  const [open, setOpen] = useState(false);
  const [searching, setSearching] = useState(false);
  const [failed, setFailed] = useState(false);
  const [searched, setSearched] = useState(false);
  const boxRef = useRef<HTMLDivElement>(null);
  const trimmed = query.trim();

  // 防抖搜索：输入停止 350ms 后请求全局搜索聚合端点
  useEffect(() => {
    let cancelled = false;
    Promise.resolve().then(() => {
      if (cancelled) return;
      if (trimmed.length < 2) {
        setResults(null);
        setSearched(false);
        setSearching(false);
        return;
      }
      setSearching(true);
      setFailed(false);
      setTimeout(async () => {
        if (cancelled) return;
        try {
          const res = await searchApi.searchCode(trimmed, { max_results: 60, per_repo_max: 8 });
          if (!cancelled) {
            setResults(res);
            setSearched(true);
          }
        } catch {
          if (!cancelled) setFailed(true);
        } finally {
          if (!cancelled) setSearching(false);
        }
      }, 350);
    });
    return () => { cancelled = true; };
  }, [trimmed]);

  // 点击外部关闭下拉
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (boxRef.current && !boxRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && trimmed) {
      setOpen(false);
      navigate(`/search?q=${encodeURIComponent(trimmed)}`);
    }
  };

  const openFile = (repoPath: string, file: string, line: number) => {
    setOpen(false);
    navigate(`/editor/${repoPath}?file=${encodeURIComponent(file)}&line=${line}`);
  };

  const openSearchPage = () => {
    if (!trimmed) return;
    setOpen(false);
    navigate(`/search?q=${encodeURIComponent(trimmed)}`);
  };

  const showDropdown = open && trimmed.length >= 2;

  return (
    <div ref={boxRef} style={{ flex: 1, maxWidth: 480, position: 'relative' }}>
      <SearchOutlined
        style={{
          position: 'absolute',
          left: 10,
          top: '50%',
          transform: 'translateY(-50%)',
          color: '#6e7681',
          fontSize: 16,
          zIndex: 1,
        }}
      />
      <InputBox
        value={query}
        onChange={(v) => { setQuery(v); setOpen(true); }}
        onFocus={() => setOpen(true)}
        onKeyDown={handleKeyDown}
        placeholder={t('app.topBar.searchPlaceholder')}
      />

      {showDropdown && (
        <div
          style={{
            position: 'absolute',
            top: 42,
            left: 0,
            right: 0,
            background: bgDropdown,
            border: `1px solid ${borderColor}`,
            borderRadius: 8,
            boxShadow: '0 8px 24px rgba(0,0,0,0.4)',
            zIndex: 1000,
            overflow: 'hidden',
          }}
        >
          <div style={{ maxHeight: 420, overflowY: 'auto' }}>
            {searching ? (
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: 14, color: textSecondary, fontSize: 13 }}>
                <LoadingOutlined style={{ color: blueLight }} /> {t('app.topBar.searching')}
              </div>
            ) : failed ? (
              <div style={{ padding: 14, color: textSecondary, fontSize: 13 }}>{t('app.topBar.searchFailed')}</div>
            ) : !searched || !results ? null : results.total_count === 0 && !searching ? (
              <div style={{ padding: 14, color: textSecondary, fontSize: 13 }}>
                {t('app.topBar.searchNoResults', { query: trimmed })}
              </div>
            ) : (
              results.repositories.map((repo) => (
                <div key={repo.repository_id} style={{ borderBottom: `1px solid ${borderColor}` }}>
                  <div
                    onClick={() => navigate(`/repositories/${repo.repository_path}`)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 8,
                      padding: '8px 12px',
                      color: textPrimary,
                      fontSize: 13,
                      fontWeight: 600,
                      cursor: 'pointer',
                      background: '#0d1117',
                    }}
                    onMouseEnter={(e) => { e.currentTarget.style.background = hoverBg; }}
                    onMouseLeave={(e) => { e.currentTarget.style.background = '#0d1117'; }}
                  >
                    <span style={{ width: 6, height: 6, borderRadius: '50%', background: blueLight, flexShrink: 0 }} />
                    {repo.repository_path}
                    <span style={{ flex: 1 }} />
                    <span style={{ fontSize: 11, color: textTertiary }}>{repo.total_count}</span>
                  </div>
                  {repo.results.slice(0, 5).map((hit) => {
                    const lineInfo = `${hit.file}:${hit.line}`;
                    return (
                      <div
                        key={lineInfo}
                        onClick={() => openFile(repo.repository_path, hit.file, hit.line)}
                        style={{ display: 'flex', alignItems: 'flex-start', gap: 8, padding: '7px 12px', cursor: 'pointer', paddingLeft: 26 }}
                        onMouseEnter={(e) => { e.currentTarget.style.background = hoverBg; }}
                        onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
                      >
                        <FileTextOutlined style={{ color: textTertiary, marginTop: 1, fontSize: 12 }} />
                        <div style={{ minWidth: 0 }}>
                          <div style={{ fontSize: 12, color: textPrimary, fontFamily: 'monospace', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                            {hit.file}
                            <span style={{ color: textTertiary }}>:{hit.line}</span>
                          </div>
                          <div style={{ fontSize: 12, color: textSecondary, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', marginTop: 1 }}>
                            {hit.content.trim() || '…'}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              ))
            )}
          </div>
          {!searching && !failed && results && results.total_count > 0 && (
            <div
              onClick={openSearchPage}
              style={{
                padding: '9px 12px',
                borderTop: `1px solid ${borderColor}`,
                color: blueLight,
                fontSize: 13,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: 4,
              }}
              onMouseEnter={(e) => { e.currentTarget.style.background = hoverBg; }}
              onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
            >
              {t('app.topBar.searchViewAll')}
              <RightOutlined style={{ fontSize: 10 }} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function InputBox({
  value,
  onChange,
  onFocus,
  onKeyDown,
  placeholder,
}: {
  value: string;
  onChange: (v: string) => void;
  onFocus: () => void;
  onKeyDown: (e: React.KeyboardEvent<HTMLInputElement>) => void;
  placeholder: string;
}) {
  return (
    <input
      value={value}
      onChange={(e) => onChange(e.target.value)}
      onFocus={onFocus}
      onKeyDown={onKeyDown}
      placeholder={placeholder}
      style={{
        width: '100%',
        background: bgInput,
        border: `1px solid #30363d`,
        borderRadius: 6,
        color: textPrimary,
        paddingLeft: 34,
        fontSize: 13,
        height: 32,
        outline: 'none',
      }}
    />
  );
}