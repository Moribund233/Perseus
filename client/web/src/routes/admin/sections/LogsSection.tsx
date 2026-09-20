import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { App, Alert, Button, InputNumber, Select, Skeleton } from 'antd';
import { ClearOutlined, ReloadOutlined } from '@ant-design/icons';
import { useVirtualizer } from '@tanstack/react-virtual';
import { logsApi, type LogContent, type LogInfo } from '../../../api/admin';
import ConfirmDangerModal from '../../../components/admin/ConfirmDangerModal';
import { LEVELS, parseLogLines, splitLine } from '../../../components/admin/logLine';

const CLEANUP_CONFIRM_WORD = 'CLEANUP';
const LINE_CHOICES = [100, 200, 500, 1000, 2000, 5000];
const FOLLOW_INTERVAL_MS = 5_000;

function todayStr(): string {
  return new Date().toISOString().slice(0, 10);
}

/** "perseus.log" → "perseus"（content 端点按文件基名查询） */
function baseNameOf(fileName: string | undefined): string {
  return (fileName ?? '').replace(/\.log$/, '') || 'perseus';
}

export default function LogsSection() {
  const { t } = useTranslation();
  const { message } = App.useApp();

  const [info, setInfo] = useState<LogInfo | null>(null);
  const [date, setDate] = useState<string | null>(null);
  const [file, setFile] = useState<string | null>(null);
  const [lines, setLines] = useState(200);
  const [level, setLevel] = useState<string>('');
  const [content, setContent] = useState<LogContent | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [follow, setFollow] = useState(false);
  const [updatedAt, setUpdatedAt] = useState<string | null>(null);

  const [cleanupOpen, setCleanupOpen] = useState(false);
  const [keepDays, setKeepDays] = useState(30);
  const [cleanupBusy, setCleanupBusy] = useState(false);
  const [cleanupOut, setCleanupOut] = useState<{ success: boolean; text: string } | null>(null);

  const termRef = useRef<HTMLDivElement | null>(null);

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

  useEffect(() => {
    if (!follow) return;
    const timer = setInterval(loadContent, FOLLOW_INTERVAL_MS);
    return () => clearInterval(timer);
  }, [follow, loadContent]);

  const fileOptions = useMemo(
    () => (info?.today_files ?? []).map((f) => ({ label: baseNameOf(f.name), value: baseNameOf(f.name) })),
    [info],
  );
  const dateOptions = useMemo(
    () => (info?.available_dates ?? []).map((d) => ({ label: d, value: d })),
    [info],
  );

  const linesArr = useMemo(() => parseLogLines(content?.content), [content]);

  // 大日志虚拟滚动：仅渲染视口内行（行高按实际内容动态测量，兼容折行）
  // eslint-disable-next-line react-hooks/incompatible-library -- TanStack Virtual 返回非纯函数，React Compiler 无法安全记忆化
  const virtualizer = useVirtualizer({
    count: linesArr.length,
    getScrollElement: () => termRef.current,
    estimateSize: () => 19,
    overscan: 16,
  });
  const totalSize = virtualizer.getTotalSize();

  useEffect(() => {
    if (!follow || linesArr.length === 0) return;
    virtualizer.scrollToIndex(linesArr.length - 1, { align: 'end' });
  }, [follow, linesArr.length, totalSize, virtualizer]);

  const errorMessage = error === null ? null : (error || t('app.admin.logs.loadFailed'));

  const doCleanup = async () => {
    setCleanupBusy(true);
    try {
      const res = await logsApi.cleanup(keepDays);
      if (res.success) {
        message.success(
          t('app.admin.logs.cleanup.done', { count: res.deleted_count, days: res.keep_days }),
        );
        setCleanupOut({ success: true, text: t('app.admin.logs.cleanup.done', { count: res.deleted_count, days: res.keep_days }) });
      } else {
        setCleanupOut({ success: false, text: t('app.admin.logs.cleanup.failed') });
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      message.error(msg);
      setCleanupOut({ success: false, text: msg });
    } finally {
      setCleanupBusy(false);
      setCleanupOpen(false);
    }
  };

  return (
    <div>
      <div className="ac-page-head">
        <div>
          <h1 className="ac-h1">{t('app.admin.logs.title')}</h1>
          <div className="ac-sub">{t('app.admin.logs.subtitle')}</div>
        </div>
        <div className="ac-toolbar">
          {updatedAt && <span className="ac-updated">{t('app.admin.logs.updatedAt', { time: updatedAt })}</span>}
          <Button danger size="small" icon={<ClearOutlined />} onClick={() => setCleanupOpen(true)}>
            {t('app.admin.logs.cleanup.button')}
          </Button>
          <Button size="small" icon={<ReloadOutlined />} loading={loading} onClick={loadContent}>
            {t('app.admin.logs.refresh')}
          </Button>
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

      {cleanupOut && (
        <div className={`ac-banner ${cleanupOut.success ? '' : 'danger'}`}>
          <div>
            <div className="ac-banner-title">
              {cleanupOut.success ? t('app.admin.logs.cleanup.done') : t('app.admin.logs.cleanup.failed')}
            </div>
            <div className="ac-banner-desc">{cleanupOut.text}</div>
          </div>
        </div>
      )}

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
        <button
          type="button"
          className={`ac-log-follow${follow ? ' on' : ''}`}
          onClick={() => setFollow((v) => !v)}
        >
          {follow ? t('app.admin.logs.followOn') : t('app.admin.logs.follow')}
        </button>
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

      <div className={`ac-log-term${follow ? ' live' : ''}`}>
        <div className="ac-log-cap">
          <span className="ac-log-path">
            {info ? `${info.log_dir}/${date}/${file ?? ''}.log` : t('app.admin.logs.loading')}
          </span>
          {content && (
            <span className="ac-log-count">{t('app.admin.logs.count', { shown: linesArr.length, total: content.total_lines })}</span>
          )}
          <span className={`ac-log-state ${follow ? 'on' : ''}`}>
            {follow ? t('app.admin.logs.following') : t('app.admin.logs.paused')}
          </span>
        </div>
        <div className="ac-log-body" ref={termRef}>
          {!content && !errorMessage ? (
            <div className="ac-log-skeleton">
              <Skeleton active title={false} paragraph={{ rows: 8 }} />
            </div>
          ) : linesArr.length === 0 ? (
            <div className="ac-empty">{t('app.admin.logs.empty')}</div>
          ) : (
            <div className="ac-log-vlist" style={{ height: totalSize }}>
              {virtualizer.getVirtualItems().map((vi) => {
                const { head, level: lv, tail } = splitLine(linesArr[vi.index]);
                return (
                  <div
                    className={`ac-log-line${lv ? ` lv-${lv.toLowerCase()}` : ''}`}
                    key={vi.key}
                    data-index={vi.index}
                    ref={virtualizer.measureElement}
                    style={{ transform: `translateY(${vi.start}px)` }}
                  >
                    <span className="ac-log-no">{vi.index + 1}</span>
                    <span className="ac-log-text">
                      {head}
                      {lv && <span className="ac-log-lvl">{lv}</span>}
                      {tail}
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      <ConfirmDangerModal
        open={cleanupOpen}
        title={t('app.admin.logs.cleanup.title')}
        description={t('app.admin.logs.cleanup.desc')}
        confirmWord={CLEANUP_CONFIRM_WORD}
        actionLabel={t('app.admin.logs.cleanup.confirmAction')}
        busy={cleanupBusy}
        onAction={() => void doCleanup()}
        onClose={() => setCleanupOpen(false)}
        extra={
          <div className="ac-danger-row">
            <span className="ac-danger-label">{t('app.admin.logs.cleanup.keepDays')}</span>
            <InputNumber
              size="middle"
              min={1}
              max={365}
              value={keepDays}
              onChange={(v) => setKeepDays(v ?? 30)}
              style={{ width: 120 }}
            />
          </div>
        }
      />
    </div>
  );
}