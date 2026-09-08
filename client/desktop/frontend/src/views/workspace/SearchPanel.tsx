import { useEffect, useMemo, useRef, useState } from 'react';
import { SearchOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useSearchStore } from '../../stores/search';
import { logInfo } from '../../stores/logs';

interface Props {
  workspaceName: string;
  onOpen: (path: string, line?: number) => void;
}

// SearchPanel 本地工作区搜索：命中分组到文件，点击行/文件在编辑器中打开。
export default function SearchPanel({ workspaceName, onOpen }: Props) {
  const { t } = useTranslation();
  const { query, results, total, truncated, searching, error, search, clear } = useSearchStore();
  const [path, setPath] = useState('');
  const [input, setInput] = useState('');
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // 输入防抖 300ms 触发搜索
  useEffect(() => {
    if (timer.current) clearTimeout(timer.current);
    setPath('');
    const q = input.trim();
    if (!q) {
      clear();
      return;
    }
    timer.current = setTimeout(() => {
      void search(q).then(() => logInfo(t('desktop.log.searchDone', { defaultValue: '本地搜索完成' })));
    }, 300);
    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
  }, [input, search, clear, t]);

  const grouped = useMemo(() => {
    const map = new Map<string, number[]>();
    for (const r of results) {
      const lines = map.get(r.file);
      if (lines) lines.push(r.line);
      else map.set(r.file, [r.line]);
    }
    return [...map.entries()];
  }, [results]);

  const matchesQuery = (s: string) => {
    if (!query) return s;
    const i = s.toLowerCase().indexOf(query.toLowerCase());
    if (i < 0) return s;
    return (
      <>
        {s.slice(0, i)}
        <span className="hl">{s.slice(i, i + query.length)}</span>
        {s.slice(i + query.length)}
      </>
    );
  };

  return (
    <div className="sb-pane on" data-pane="search">
      <div className="sb-head">{t('desktop.search.title', { defaultValue: '搜索' })}</div>
      <div style={{ padding: '0 12px 10px', display: 'flex', flexDirection: 'column', gap: 8 }}>
        <div className="input">
          <SearchOutlined />
          <input
            autoFocus
            placeholder={t('desktop.search.placeholder', { defaultValue: '在工作区中搜索…' })}
            value={input}
            onChange={(e) => setInput(e.target.value)}
          />
        </div>
        <div className="search-opts">
          {t('desktop.search.optsHint', { name: workspaceName, defaultValue: '{{name}} · 本地检索，忽略 .git / node_modules 等' })}
        </div>
      </div>
      {searching && <div className="srch-result">{t('desktop.search.searching', { defaultValue: '搜索中…' })}</div>}
      {error && <div className="srch-result" style={{ color: 'var(--red)' }}>{error}</div>}
      {!searching && !error && query && (
        <div className="search-summary">
          <span>
            {truncated
              ? t('desktop.search.truncated', { total, defaultValue: '超过 {{total}} 条，已截断' })
              : t('desktop.search.summary', { total, defaultValue: '共 {{total}} 条命中' })}
          </span>
          <span className="hsep"> · </span>
          <span>{t('desktop.search.groups', { count: grouped.length, defaultValue: '{{count}} 个文件' })}</span>
        </div>
      )}
      {query &&
        grouped.map(([file, lines]) => (
          <div key={file}>
            <div className="srch-file" onClick={() => onOpen(file, lines[0] ?? 1)}>
              <span className="fc def">{t('desktop.search.fileBadge', { defaultValue: 'FILE' })}</span>
              <span style={{ flex: '1', minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis' }}>{file}</span>
              <span className="cnt">{lines.length}</span>
            </div>
            {results
              .filter((r) => r.file === file)
              .map((r) => (
                <div key={`${r.file}:${r.line}`} className="srch-result" onClick={() => onOpen(r.file, r.line)}>
                  <span className="ln">{r.line}</span>
                  <span style={{ whiteSpace: 'pre' }}>
                    {r.content ? matchesQuery(r.content) : ''}
                  </span>
                </div>
              ))}
          </div>
        ))}
    </div>
  );
}