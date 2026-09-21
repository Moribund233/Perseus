import { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Alert, Button, Select } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import { logsApi, type LogContent, type LogInfo } from '../../../api/admin';
import VirtualLogBody from '../../../components/admin/VirtualLogBody';
import { LEVELS, buildSegmentedRows, parseLogLines, type LogRow } from '../../../components/admin/logLine';

const LINE_CHOICES = [100, 200, 500, 1000, 2000, 5000];

function todayStr(): string {
  return new Date().toISOString().slice(0, 10);
}

/** "perseus.log" → "perseus"（content 端点按文件基名查询） */
function baseNameOf(fileName: string | undefined): string {
  return (fileName ?? '').replace(/\.log$/, '') || 'perseus';
}

/** 文件日志 tab：按日期/文件/行数检索磁盘日志（跨分片拼接），级别由服务端过滤 */
export default function FileLogTab() {
  const { t } = useTranslation();

  const [info, setInfo] = useState<LogInfo | null>(null);
  const [date, setDate] = useState<string | null>(null);
  const [file, setFile] = useState<string | null>(null);
  const [lines, setLines] = useState(200);
  const [level, setLevel] = useState<string>('');
  const [content, setContent] = useState<LogContent | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [updatedAt, setUpdatedAt] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    logsApi.getInfo()
      .then((res) => {
        if (cancelled) return;
        setInfo(res);
        setDate((prev) => prev ?? res.available_dates[0] ?? todayStr());
        setFile((prev) => prev ?? baseNameOf(res.today_files[0]?.name));
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(err instanceof Error && err.message ? err.message : '');
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const loadContent = useCallback(() => {
    if (!date || !file) return;
    setLoading(true);
    logsApi.getContent({ date, log_name: file, lines, level: level || undefined })
      .then((res) => {
        setContent(res);
        setError(null);
        setUpdatedAt(new Date().toLocaleTimeString());
      })
      .catch((err: unknown) => {
        setError(err instanceof Error && err.message ? err.message : '');
      })
      .finally(() => setLoading(false));
  }, [date, file, lines, level]);

  useEffect(() => {
    let cancelled = false;
    const id = window.setTimeout(() => {
      if (cancelled) return;
      loadContent();
    }, 0);
    return () => {
      cancelled = true;
      window.clearTimeout(id);
    };
  }, [loadContent]);

  const fileOptions = useMemo(
    () => (info?.today_files ?? []).map((f) => ({ label: baseNameOf(f.name), value: baseNameOf(f.name) })),
    [info],
  );
  const dateOptions = useMemo(
    () => (info?.available_dates ?? []).map((d) => ({ label: d, value: d })),
    [info],
  );
  const currentFile = useMemo(
    () => (info?.today_files ?? []).find((f) => baseNameOf(f.name) === file),
    [info, file],
  );

  const linesArr = useMemo(() => parseLogLines(content?.content), [content]);
  const rows = useMemo<LogRow[]>(
    () =>
      buildSegmentedRows(linesArr, content?.segment_starts ?? [], (name) =>
        t('app.admin.logs.segment', { name }),
      ),
    [linesArr, content, t],
  );

  const errorMessage = error === null ? null : (error || t('app.admin.logs.loadFailed'));

  return (
    <div>
      <div className="ac-log-toolbar">
        <span className="ac-log-lab">{t('app.admin.logs.date')}</span>
        <Select
          size="small"
          value={date ?? undefined}
          onChange={setDate}
          options={dateOptions}
          style={{ width: 132 }}
        />
        <span className="ac-log-lab">{t('app.admin.logs.file')}</span>
        <Select
          size="small"
          value={file ?? undefined}
          onChange={setFile}
          options={fileOptions}
          style={{ width: 120 }}
          disabled={fileOptions.length === 0}
        />
        <span className="ac-log-lab">{t('app.admin.logs.lines')}</span>
        <Select
          size="small"
          value={lines}
          onChange={setLines}
          options={LINE_CHOICES.map((n) => ({ label: String(n), value: n }))}
          style={{ width: 90 }}
        />
        {updatedAt && <span className="ac-updated">{t('app.admin.logs.updatedAt', { time: updatedAt })}</span>}
        <Button size="small" icon={<ReloadOutlined />} loading={loading} onClick={loadContent}>
          {t('app.admin.logs.refresh')}
        </Button>
        <div className="ac-log-filters">
          {[t('app.admin.logs.all'), ...LEVELS].map((label) => {
            const value = label === t('app.admin.logs.all') ? '' : label;
            return (
              <button
                key={value || 'all'}
                type="button"
                className={`ac-fchip${level === value ? ' on' : ''}`}
                data-level={value.toLowerCase() || 'all'}
                onClick={() => setLevel(value)}
              >
                {label}
              </button>
            );
          })}
        </div>
      </div>

      {errorMessage && (
        <Alert
          type="error"
          showIcon
          message={t('app.admin.logs.loadFailed')}
          description={errorMessage}
          style={{ marginBottom: 18 }}
        />
      )}

      {(content?.truncated || currentFile?.truncated) && (
        <div className="ac-log-note">{t('app.admin.logs.truncated')}</div>
      )}

      <div className="ac-log-term">
        <div className="ac-log-cap">
          <span className="ac-log-path">
            {info ? `${info.log_dir}/${date}/${file ?? ''}.log` : t('app.admin.logs.loading')}
          </span>
          {currentFile && (
            <span className="ac-log-meta">
              {t('app.admin.logs.segmentMeta', {
                parts: currentFile.parts,
                size: currentFile.total_size_formatted,
              })}
            </span>
          )}
          {content && (
            <span className="ac-log-count">
              {t('app.admin.logs.count', { shown: linesArr.length, total: content.total_lines })}
            </span>
          )}
          <span className="ac-log-state">{t('app.admin.logs.fileMode')}</span>
        </div>
        <VirtualLogBody
          rows={rows}
          loading={loading && !content}
          emptyText={t('app.admin.logs.empty')}
        />
      </div>
    </div>
  );
}
