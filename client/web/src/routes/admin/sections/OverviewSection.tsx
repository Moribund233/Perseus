import { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import { Alert, Button, Empty } from 'antd';
import { ArrowRightOutlined, ReloadOutlined } from '@ant-design/icons';
import { Area, Column, Line, Tiny } from '@ant-design/charts';
import { adminApi, logsApi, type AppStatus } from '../../../api/admin';
import { statsApi, type PlatformStats } from '../../../api/stats';
import KeyValueLedger from '../../../components/admin/KeyValueLedger';
import AdminSkeleton from '../../../components/admin/AdminSkeleton';
import MonitoringCard from '../../../components/admin/MonitoringCard';
import { formatBytesMb } from '../../../components/admin/health';
import {
  pushSample,
  toSpark,
  toSeries,
  type MetricSample,
} from '../../../components/admin/metricsHistory';
import { parseLogLines, splitLine } from '../../../components/admin/logLine';

interface OverviewData {
  status: AppStatus;
  platform: PlatformStats | null;
}

const POLL_MS = 5_000;
const RECENT_LOG_LINES = 6;
const C = {
  mem: '#3fb950',
  cpu: '#d29922',
  rpm: '#1f6feb',
  avg: '#bc8cff',
  success: '#3fb950',
  failed: '#f85149',
} as const;

const DARK_THEME = 'classicDark';

const AXIS = {
  x: { labelFill: '#6e7681', labelFontSize: 11, lineStroke: '#21262d', tickStroke: '#21262d' },
  y: { labelFill: '#6e7681', labelFontSize: 11, lineStroke: '#21262d', tickStroke: '#21262d', gridStroke: '#1c2333' },
};

function formatTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleTimeString();
}

/** 状态为主数据源（失败即报错）；平台统计为可选，失败时降级为隐藏面板 */
async function fetchOverview(): Promise<OverviewData> {
  const [status, platform] = await Promise.all([
    adminApi.getStatus().catch(() => null),
    statsApi.getPlatformStats().catch(() => null),
  ]);
  if (!status) throw new Error('status-unavailable');
  return { status, platform };
}

function sampleOf(status: AppStatus): MetricSample {
  return {
    t: Date.now(),
    mem: status.process.memory_mb,
    cpu: status.process.cpu_percent,
    rpm: status.requests.requests_per_minute,
    avgMs: status.requests.avg_response_time_ms,
    success: status.requests.success,
    failed: status.requests.failed,
  };
}

export default function OverviewSection() {
  const { t } = useTranslation();
  const [data, setData] = useState<OverviewData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [updatedAt, setUpdatedAt] = useState<string | null>(null);
  const [history, setHistory] = useState<MetricSample[]>([]);
  const [recentLogs, setRecentLogs] = useState<string[]>([]);
  const [logsError, setLogsError] = useState<string | null>(null);

  const apply = useCallback((d: OverviewData) => {
    setData(d);
    setError(null);
    setUpdatedAt(new Date().toLocaleTimeString());
    setHistory((prev) => pushSample(prev, sampleOf(d.status)));
  }, []);

  const refresh = useCallback(() => {
    fetchOverview()
      .then(apply)
      .catch((err: unknown) => {
        setError(err instanceof Error && err.message ? err.message : '');
      });
  }, [apply]);

  const loadLogs = useCallback(() => {
    logsApi
      .getContent({ lines: RECENT_LOG_LINES })
      .then((res) => {
        setRecentLogs(parseLogLines(res.content).slice(-RECENT_LOG_LINES));
        setLogsError(null);
      })
      .catch((err: unknown) => {
        setLogsError(err instanceof Error && err.message ? err.message : '');
      });
  }, []);

  useEffect(() => {
    let cancelled = false;
    const tick = () => {
      fetchOverview()
        .then((d) => {
          if (!cancelled) apply(d);
        })
        .catch((err: unknown) => {
          if (!cancelled) setError(err instanceof Error && err.message ? err.message : '');
        });
    };
    tick();
    const timer = setInterval(tick, POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [apply]);

  useEffect(() => {
    loadLogs();
  }, [loadLogs]);

  const status = data?.status;
  const errorMessage = error === null ? null : (error || t('app.admin.overview.loadFailed'));

  const memSpark = useMemo(() => toSpark(history, (s) => s.mem), [history]);
  const cpuSpark = useMemo(() => toSpark(history, (s) => s.cpu), [history]);
  const rpmSpark = useMemo(() => toSpark(history, (s) => s.rpm), [history]);
  const rpmSeries = useMemo(() => toSeries(history, (s) => s.rpm), [history]);
  const avgSeries = useMemo(() => toSeries(history, (s) => s.avgMs), [history]);
  const outcome = useMemo(() => {
    const last = history[history.length - 1];
    if (!last) return [];
    return [
      { type: t('app.admin.overview.trends.success'), value: Math.max(last.success, 0) },
      { type: t('app.admin.overview.trends.failed'), value: Math.max(last.failed, 0) },
    ];
  }, [history, t]);

  const hasTrend = history.length >= 2;

  return (
    <div>
      <div className="ac-page-head">
        <div>
          <h1 className="ac-h1">{t('app.admin.overview.title')}</h1>
          <div className="ac-sub">{t('app.admin.overview.subtitle')}</div>
        </div>
        <div className="ac-toolbar">
          {status && (
            <span className={`ac-chip ${status.status === 'ok' ? 'ok' : 'warn'}`}>{status.status}</span>
          )}
          {status?.debug_mode && <span className="ac-chip warn">{t('app.admin.overview.debugMode')}</span>}
          {updatedAt && <span className="ac-updated">{t('app.admin.overview.updatedAt', { time: updatedAt })}</span>}
          <Button size="small" icon={<ReloadOutlined />} onClick={refresh}>
            {t('app.admin.overview.refresh')}
          </Button>
        </div>
      </div>

      {errorMessage && (
        <Alert
          type="error"
          showIcon
          message={t('app.admin.overview.loadFailed')}
          description={errorMessage}
          style={{ marginBottom: 18 }}
        />
      )}

      {!data && !errorMessage && <AdminSkeleton heading={t('app.admin.overview.process.title')} rows={5} />}

      {status && (
        <>
          <div className="ac-vitals">
            <div className="ac-vital">
              <div className="ac-vital-label">{t('app.admin.overview.vitals.uptime')}</div>
              <div className="ac-vital-value">{status.uptime_formatted}</div>
              <div className="ac-vital-foot">
                <Tiny.Line data={rpmSpark} height={28} autoFit xField="x" yField="y" theme={DARK_THEME} style={{ stroke: C.rpm, lineWidth: 1.5 }} />
                <span className="ac-vital-note">{t('app.admin.overview.vitals.requestRateNote')}</span>
              </div>
            </div>
            <div className="ac-vital">
              <div className="ac-vital-label">{t('app.admin.overview.vitals.memory')}</div>
              <div className="ac-vital-value">
                <span className="ac-vital-unit">RAM</span> {formatBytesMb(status.process.memory_mb)}
              </div>
              <div className="ac-vital-foot">
                <Tiny.Area data={memSpark} height={28} autoFit xField="x" yField="y" theme={DARK_THEME} style={{ fill: C.mem, fillOpacity: 0.22, stroke: C.mem, lineWidth: 1.5 }} />
                <span className="ac-vital-note">{t('app.admin.overview.vitals.windowNote')}</span>
              </div>
            </div>
            <div className="ac-vital">
              <div className="ac-vital-label">{t('app.admin.overview.vitals.cpu')}</div>
              <div className="ac-vital-value">{status.process.cpu_percent}<span className="ac-vital-unit">%</span></div>
              <div className="ac-vital-foot">
                <Tiny.Area data={cpuSpark} height={28} autoFit xField="x" yField="y" theme={DARK_THEME} style={{ fill: C.cpu, fillOpacity: 0.22, stroke: C.cpu, lineWidth: 1.5 }} />
                <span className="ac-vital-note">{t('app.admin.overview.vitals.windowNote')}</span>
              </div>
            </div>
            <div className="ac-vital">
              <div className="ac-vital-label">{t('app.admin.overview.vitals.threads')}</div>
              <div className="ac-vital-value">{status.process.threads}</div>
            </div>
            <div className="ac-vital">
              <div className="ac-vital-label">{t('app.admin.overview.vitals.connections')}</div>
              <div className="ac-vital-value">{status.process.connections}</div>
            </div>
          </div>

          <div className="ac-panel">
            <div className="ac-panel-head">
              {t('app.admin.overview.trends.title')}
              <span className="ac-panel-hint">{t('app.admin.overview.trends.window', { count: history.length })}</span>
            </div>
            <div className="ac-panel-body">
              {!hasTrend ? (
                <div className="ac-empty">{t('app.admin.overview.trends.collecting')}</div>
              ) : (
                <div className="ac-trends">
                  <div className="ac-trend-main">
                    <div className="ac-trend-title">{t('app.admin.overview.trends.requestRate')}<span className="ac-trend-unit">/min</span></div>
                    <Area
                      data={rpmSeries}
                      xField="time"
                      yField="value"
                      height={180}
                      autoFit
                     
                      theme={DARK_THEME}
                      style={{ fill: C.rpm, fillOpacity: 0.18, stroke: C.rpm, lineWidth: 2 }}
                      axis={AXIS}
                    />
                    <div className="ac-trend-title">{t('app.admin.overview.trends.avgResponse')}<span className="ac-trend-unit">ms</span></div>
                    <Line
                      data={avgSeries}
                      xField="time"
                      yField="value"
                      height={160}
                      autoFit
                     
                      theme={DARK_THEME}
                      style={{ stroke: C.avg, lineWidth: 2 }}
                      axis={AXIS}
                    />
                  </div>
                  <div className="ac-trend-side">
                    <div className="ac-trend-title">
                      {t('app.admin.overview.trends.outcome')}
                      <span className="ac-trend-unit">
                        {t('app.admin.overview.trends.windowMinutes', {
                          count: status.requests.window_minutes,
                        })}
                      </span>
                    </div>
                    {outcome.every((o) => o.value === 0) ? (
                      <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={t('app.admin.overview.trends.noOutcome')} />
                    ) : (
                      <Column
                        data={outcome}
                        xField="type"
                        yField="value"
                        height={200}
                        autoFit
                        theme={DARK_THEME}
                        scale={{ color: { range: [C.success, C.failed] } }}
                        legend={false}
                        axis={AXIS}
                        style={{ fillOpacity: 0.9 }}
                      />
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>

          <div className="ac-panel">
            <div className="ac-panel-head">{t('app.admin.overview.process.title')}</div>
            <div className="ac-panel-body">
              <KeyValueLedger
                rows={[
                  { key: 'pid', label: t('app.admin.overview.process.pid'), value: status.process.pid },
                  { key: 'mem', label: t('app.admin.overview.process.memory'), value: formatBytesMb(status.process.memory_mb) },
                  { key: 'cpu', label: t('app.admin.overview.process.cpu'), value: `${status.process.cpu_percent}%` },
                  { key: 'threads', label: t('app.admin.overview.process.threads'), value: status.process.threads },
                  { key: 'conns', label: t('app.admin.overview.process.connections'), value: status.process.connections },
                  { key: 'version', label: t('app.admin.overview.process.version'), value: status.version },
                  { key: 'serverTime', label: t('app.admin.overview.process.serverTime'), value: formatTime(status.server_time) },
                  { key: 'schema', label: t('app.admin.overview.process.schema'),
                    value: status.schema_state.head
                      ? `${status.schema_state.applied ?? '—'} / ${status.schema_state.head}`
                      : (status.schema_state.applied ?? '—') },
                ]}
              />
            </div>
          </div>

          <div className="ac-panel">
            <div className="ac-panel-head">{t('app.admin.overview.requests.title')}</div>
            <div className="ac-panel-body">
              <div className="ac-statline">
                <div className="ac-stat">
                  <span className="ac-stat-label">{t('app.admin.overview.requests.total')}</span>
                  <span className="ac-stat-value">{status.requests.total.toLocaleString()}</span>
                </div>
                <div className="ac-stat">
                  <span className="ac-stat-label">{t('app.admin.overview.requests.success')}</span>
                  <span className="ac-stat-value">{status.requests.success.toLocaleString()}</span>
                </div>
                <div className="ac-stat">
                  <span className="ac-stat-label">{t('app.admin.overview.requests.failed')}</span>
                  <span className="ac-stat-value">{status.requests.failed.toLocaleString()}</span>
                </div>
                <div className="ac-stat">
                  <span className="ac-stat-label">{t('app.admin.overview.requests.rate')}</span>
                  <span className="ac-stat-value">{status.requests.requests_per_minute}<span className="ac-vital-unit">/min</span></span>
                </div>
                <div className="ac-stat">
                  <span className="ac-stat-label">{t('app.admin.overview.requests.avgTime')}</span>
                  <span className="ac-stat-value">{status.requests.avg_response_time_ms}<span className="ac-vital-unit">ms</span></span>
                </div>
              </div>
            </div>
          </div>

          <div className="ac-panel">
            <div className="ac-panel-head">{t('app.admin.overview.git.title')}</div>
            <div className="ac-panel-body">
              <div className="ac-statline">
                <div className="ac-stat">
                  <span className="ac-stat-label">{t('app.admin.overview.git.activeClones')}</span>
                  <span className="ac-stat-value">{status.git_operations.active_clones}</span>
                </div>
                <div className="ac-stat">
                  <span className="ac-stat-label">{t('app.admin.overview.git.activePushes')}</span>
                  <span className="ac-stat-value">{status.git_operations.active_pushes}</span>
                </div>
                <div className="ac-stat">
                  <span className="ac-stat-label">{t('app.admin.overview.git.queue')}</span>
                  <span className="ac-stat-value">{status.git_operations.queue_size}</span>
                </div>
              </div>
            </div>
          </div>

          {data?.platform && (
            <div className="ac-panel">
              <div className="ac-panel-head">{t('app.admin.overview.platform.title')}</div>
              <div className="ac-panel-body">
                <div className="ac-statline">
                  <div className="ac-stat">
                    <span className="ac-stat-label">{t('app.admin.overview.platform.repositories')}</span>
                    <span className="ac-stat-value">{data.platform.repository_count.toLocaleString()}</span>
                  </div>
                  <div className="ac-stat">
                    <span className="ac-stat-label">{t('app.admin.overview.platform.commits')}</span>
                    <span className="ac-stat-value">{data.platform.commit_count.toLocaleString()}</span>
                  </div>
                  <div className="ac-stat">
                    <span className="ac-stat-label">{t('app.admin.overview.platform.users')}</span>
                    <span className="ac-stat-value">{data.platform.user_count.toLocaleString()}</span>
                  </div>
                  <div className="ac-stat">
                    <span className="ac-stat-label">{t('app.admin.overview.platform.uptime')}</span>
                    <span className="ac-stat-value">{status.uptime_formatted}</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          <MonitoringCard />

          <div className="ac-panel">
            <div className="ac-panel-head">
              {t('app.admin.overview.recentLogs.title')}
              <span className="ac-panel-hint">{t('app.admin.overview.recentLogs.hint', { count: RECENT_LOG_LINES })}</span>
              <Link className="ac-panel-link" to="/admin/logs">
                {t('app.admin.overview.recentLogs.open')} <ArrowRightOutlined />
              </Link>
            </div>
            <div className="ac-panel-body">
              {logsError ? (
                <div className="ac-empty">{logsError}</div>
              ) : recentLogs.length === 0 ? (
                <div className="ac-empty">{t('app.admin.overview.recentLogs.empty')}</div>
              ) : (
                <div className="ac-mini-term">
                  {recentLogs.map((line, i) => {
                    const { head, level: lv, tail } = splitLine(line);
                    return (
                      <div className={`ac-log-line${lv ? ` lv-${lv.toLowerCase()}` : ''}`} key={i}>
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
        </>
      )}
    </div>
  );
}
