import { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import { Alert, Button, Segmented, Switch } from 'antd';
import { ArrowRightOutlined, ReloadOutlined } from '@ant-design/icons';
import { DualAxes, Line, Pie, Tiny } from '@ant-design/charts';
import {
  adminApi,
  logsApi,
  metricsApi,
  monitoringApi,
  redisApi,
  GRAFANA_ENTRY,
  type AppStatus,
  type ComponentsResponse,
  type MetricsPoint,
  type MetricsRange,
  type MetricsTimeseries,
  type MonitoringResponse,
  type RedisStatus,
} from '../../../api/admin';
import { statsApi, type PlatformStats } from '../../../api/stats';
import AdminSkeleton from '../../../components/admin/AdminSkeleton';
import { parseLogLines, splitLine } from '../../../components/admin/logLine';

const RANGES: MetricsRange[] = ['5m', '30m', '1h', '6h', '24h'];
const POLL_MS = 5_000;
const RECENT_ERROR_LINES = 6;

const C = {
  rpm: '#1f6feb',
  rpmLine: '#58a6ff',
  err: '#f85149',
  avg: '#bc8cff',
  p95: '#d29922',
  mem: '#3fb950',
  cpu: '#bc8cff',
  s2xx: '#3fb950',
  s3xx: '#58a6ff',
  s4xx: '#d29922',
  s5xx: '#f85149',
} as const;

const DARK_THEME = 'classicDark';

const Y_AXIS = {
  labelFill: '#6e7681',
  labelFontSize: 11,
  lineStroke: '#21262d',
  tickStroke: '#21262d',
  gridStroke: '#1c2333',
};

function fmtTime(t: number, range: MetricsRange): string {
  const d = new Date(t);
  if (range === '6h' || range === '24h') {
    const mm = String(d.getMonth() + 1).padStart(2, '0');
    const dd = String(d.getDate()).padStart(2, '0');
    const hh = String(d.getHours()).padStart(2, '0');
    const mi = String(d.getMinutes()).padStart(2, '0');
    return `${mm}/${dd} ${hh}:${mi}`;
  }
  return d.toLocaleTimeString();
}

interface DeltaInfo {
  text: string;
  cls: 'good' | 'bad' | 'flat';
}

/** 环比：goodWhenUp 表示「上升是好事」（如请求速率） */
function deltaOf(cur: number | null | undefined, before: number | null | undefined, goodWhenUp: boolean): DeltaInfo {
  if (cur === null || cur === undefined || before === null || before === undefined || before === 0) {
    return { text: '—', cls: 'flat' };
  }
  const d = ((cur - before) / before) * 100;
  if (Math.abs(d) < 0.5) return { text: '→ 0.0%', cls: 'flat' };
  const up = d > 0;
  const good = up ? goodWhenUp : !goodWhenUp;
  return { text: `${up ? '▲' : '▼'} ${Math.abs(d).toFixed(1)}%`, cls: good ? 'good' : 'bad' };
}

function Ring({ pct, color, label, sub, size = 86 }: { pct: number; color: string; label: string; sub: string; size?: number }) {
  const r = size / 2 - 7;
  const c = 2 * Math.PI * r;
  const len = Math.max(0, Math.min(1, pct)) * c;
  const mid = size / 2;
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} aria-hidden="true">
      <circle cx={mid} cy={mid} r={r} fill="none" stroke="#21262d" strokeWidth={7} />
      <circle
        cx={mid}
        cy={mid}
        r={r}
        fill="none"
        stroke={color}
        strokeWidth={7}
        strokeLinecap="round"
        strokeDasharray={`${len} ${c - len}`}
        transform={`rotate(-90 ${mid} ${mid})`}
      />
      <text x={mid} y={mid - 1} textAnchor="middle" className="ac-ring-txt">
        {label}
      </text>
      <text x={mid} y={mid + 13} textAnchor="middle" className="ac-ring-sub">
        {sub}
      </text>
    </svg>
  );
}

interface KpiProps {
  label: string;
  tag: string;
  value: string;
  unit?: string;
  tone?: '' | 'warn' | 'bad';
  spark: { x: number; y: number }[];
  sparkType: 'area' | 'line';
  sparkColor: string;
  delta: DeltaInfo;
  note?: string;
}

function Kpi({ label, tag, value, unit, tone, spark, sparkType, sparkColor, delta, note }: KpiProps) {
  return (
    <div className="ac-kpi">
      <div className="ac-kpi-top">
        <span className="ac-kpi-label">{label}</span>
        <span className="ac-kpi-tag">{tag}</span>
      </div>
      <div className={`ac-kpi-value${tone ? ` ${tone}` : ''}`}>
        {value}
        {unit && <span className="unit">{unit}</span>}
      </div>
      <div className="ac-kpi-foot">
        <div className="ac-kpi-spark">
          {sparkType === 'area' ? (
            <Tiny.Area
              data={spark}
              height={30}
              autoFit
              xField="x"
              yField="y"
              theme={DARK_THEME}
              style={{ fill: sparkColor, fillOpacity: 0.22, stroke: sparkColor, lineWidth: 1.5 }}
            />
          ) : (
            <Tiny.Line
              data={spark}
              height={30}
              autoFit
              xField="x"
              yField="y"
              theme={DARK_THEME}
              style={{ stroke: sparkColor, lineWidth: 1.5 }}
            />
          )}
        </div>
        <span className={`ac-delta ${delta.cls}`}>{delta.text}</span>
      </div>
      {note && <div className="ac-kpi-note">{note}</div>}
    </div>
  );
}

export default function OverviewSection() {
  const { t } = useTranslation();
  const [range, setRange] = useState<MetricsRange>('1h');
  const [auto, setAuto] = useState(true);
  const [series, setSeries] = useState<MetricsTimeseries | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [updatedAt, setUpdatedAt] = useState<string | null>(null);

  const [status, setStatus] = useState<AppStatus | null>(null);
  const [platform, setPlatform] = useState<PlatformStats | null>(null);
  const [components, setComponents] = useState<ComponentsResponse | null>(null);
  const [redis, setRedis] = useState<RedisStatus | null>(null);
  const [monitoring, setMonitoring] = useState<MonitoringResponse | null>(null);
  const [recentErrors, setRecentErrors] = useState<string[]>([]);
  const [monBusy, setMonBusy] = useState(false);
  const [monError, setMonError] = useState<string | null>(null);

  const loadSeries = useCallback(() => {
    metricsApi
      .getTimeseries(range)
      .then((data) => {
        setSeries(data);
        setError(null);
        setUpdatedAt(new Date().toLocaleTimeString());
      })
      .catch((err: unknown) => {
        setError(err instanceof Error && err.message ? err.message : '');
      });
  }, [range]);

  const loadSide = useCallback(() => {
    Promise.all([
      adminApi.getStatus().catch(() => null),
      statsApi.getPlatformStats().catch(() => null),
      adminApi.getComponents().catch(() => null),
      redisApi.getStatus().catch(() => null),
      monitoringApi.getStatus().catch(() => null),
      logsApi.getContent({ level: 'error', lines: RECENT_ERROR_LINES }).catch(() => null),
    ]).then(([st, pf, comp, rd, mon, logs]) => {
      setStatus(st);
      setPlatform(pf);
      setComponents(comp);
      setRedis(rd);
      setMonitoring(mon);
      setRecentErrors(logs ? parseLogLines(logs.content).slice(-RECENT_ERROR_LINES) : []);
    });
  }, []);

  useEffect(() => {
    loadSeries();
  }, [loadSeries]);

  useEffect(() => {
    if (!auto) return undefined;
    const id = setInterval(loadSeries, POLL_MS);
    return () => clearInterval(id);
  }, [auto, loadSeries]);

  useEffect(() => {
    loadSide();
  }, [loadSide]);

  const refresh = useCallback(() => {
    loadSeries();
    loadSide();
  }, [loadSeries, loadSide]);

  const toggleMonitoring = useCallback(async (next: boolean) => {
    setMonBusy(true);
    setMonError(null);
    try {
      setMonitoring(await monitoringApi.setEnabled(next));
    } catch (err: unknown) {
      setMonError(err instanceof Error && err.message ? err.message : '');
    } finally {
      setMonBusy(false);
    }
  }, []);

  const openGrafana = useCallback(async () => {
    setMonError(null);
    try {
      const res = await monitoringApi.sso();
      window.location.assign(res.entry || GRAFANA_ENTRY);
    } catch (err: unknown) {
      setMonError(err instanceof Error && err.message ? err.message : '');
    }
  }, []);

  const points = useMemo(() => series?.points ?? [], [series]);
  const last = points[points.length - 1];
  const prev = points[points.length - 2] ?? last;

  /** 图表用降采样（<=24 点），避免 x 轴标签拥挤；KPI 仍用完整序列 */
  const chartPoints = useMemo(() => {
    const n = points.length;
    if (n <= 24) return points;
    const step = Math.ceil(n / 24);
    return points.filter((_, i) => i % step === 0 || i === n - 1);
  }, [points]);

  const trendData = useMemo(
    () => chartPoints.map((p) => ({ time: fmtTime(p.t, range), rpm: p.rpm, err_rate: p.err_rate })),
    [chartPoints, range],
  );

  const latencyData = useMemo(() => {
    const avgLabel = t('app.admin.overview.trends.avg');
    const p95Label = t('app.admin.overview.trends.p95');
    return chartPoints.flatMap((p) => [
      { time: fmtTime(p.t, range), type: avgLabel, value: p.avg_ms },
      { time: fmtTime(p.t, range), type: p95Label, value: p.p95_ms },
    ]);
  }, [chartPoints, range, t]);

  const chartAxis = useMemo(
    () => ({
      x: {
        labelFill: '#6e7681',
        labelFontSize: 11,
        lineStroke: '#21262d',
        tickStroke: '#21262d',
        labelAutoHide: true,
        labelAutoRotate: false,
      },
      y: Y_AXIS,
    }),
    [],
  );

  const sparkOf = useCallback(
    (pick: (p: MetricsPoint) => number) => points.map((p, i) => ({ x: i, y: pick(p) })),
    [points],
  );

  const totals = useMemo(
    () =>
      points.reduce(
        (acc, p) => ({
          s2xx: acc.s2xx + p.s2xx,
          s3xx: acc.s3xx + p.s3xx,
          s4xx: acc.s4xx + p.s4xx,
          s5xx: acc.s5xx + p.s5xx,
        }),
        { s2xx: 0, s3xx: 0, s4xx: 0, s5xx: 0 },
      ),
    [points],
  );
  const totalReq = totals.s2xx + totals.s3xx + totals.s4xx + totals.s5xx;
  const okPct = totalReq ? (totals.s2xx / totalReq) * 100 : 0;

  const pieData = useMemo(
    () => [
      { type: t('app.admin.overview.distribution.s2xx'), value: totals.s2xx },
      { type: t('app.admin.overview.distribution.s3xx'), value: totals.s3xx },
      { type: t('app.admin.overview.distribution.s4xx'), value: totals.s4xx },
      { type: t('app.admin.overview.distribution.s5xx'), value: totals.s5xx },
    ],
    [totals, t],
  );

  const errorMessage = error === null ? null : error || t('app.admin.overview.loadFailed');
  const rangeLabel = t('app.admin.overview.trends.range', { range });

  const compSummary = components?.summary;
  const runningPct = compSummary && compSummary.total ? compSummary.running / compSummary.total : 0;
  const ringColor =
    compSummary && compSummary.unhealthy > 0
      ? C.err
      : compSummary && compSummary.running < compSummary.total
        ? C.p95
        : C.mem;

  return (
    <div className="ac-overview">
      <div className="ac-page-head">
        <div>
          <h1 className="ac-h1">{t('app.admin.overview.title')}</h1>
          <div className="ac-sub">{t('app.admin.overview.subtitle')}</div>
        </div>
        <div className="ac-toolbar">
          {status && <span className={`ac-chip ${status.status === 'ok' ? 'ok' : 'warn'}`}>{status.status}</span>}
          {status?.debug_mode && <span className="ac-chip warn">{t('app.admin.overview.debugMode')}</span>}
          <Segmented
            size="small"
            value={range}
            options={RANGES.map((r) => ({ label: r, value: r }))}
            onChange={(v) => setRange(v as MetricsRange)}
          />
          <Button size="small" onClick={() => setAuto((v) => !v)}>
            {auto ? t('app.admin.overview.autoOn') : t('app.admin.overview.autoOff')}
          </Button>
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

      {!series && !errorMessage && <AdminSkeleton heading={t('app.admin.overview.title')} rows={5} />}

      {series && (
        <>
          <div className="ac-kpis">
            <Kpi
              label={t('app.admin.overview.kpis.requestRate')}
              tag="Tiny.Area"
              value={last ? last.rpm.toFixed(1) : '—'}
              unit={t('app.admin.overview.kpis.perMin')}
              spark={sparkOf((p) => p.rpm)}
              sparkType="area"
              sparkColor={C.rpmLine}
              delta={deltaOf(last?.rpm, prev?.rpm, true)}
              note={rangeLabel}
            />
            <Kpi
              label={t('app.admin.overview.kpis.errorRate')}
              tag="Tiny.Line"
              value={last ? last.err_rate.toFixed(2) : '—'}
              unit="%"
              tone={last && last.err_rate > 1 ? 'bad' : last && last.err_rate > 0.5 ? 'warn' : ''}
              spark={sparkOf((p) => p.err_rate)}
              sparkType="line"
              sparkColor={C.err}
              delta={deltaOf(last?.err_rate, prev?.err_rate, false)}
              note={t('app.admin.overview.kpis.thresholdError')}
            />
            <Kpi
              label={t('app.admin.overview.kpis.p95')}
              tag="Tiny.Line"
              value={last ? String(Math.round(last.p95_ms)) : '—'}
              unit="ms"
              spark={sparkOf((p) => p.p95_ms)}
              sparkType="line"
              sparkColor={C.p95}
              delta={deltaOf(last?.p95_ms, prev?.p95_ms, false)}
              note={last ? t('app.admin.overview.kpis.avgLatency', { value: last.avg_ms.toFixed(1) }) : undefined}
            />
            <Kpi
              label={t('app.admin.overview.kpis.memory')}
              tag="Tiny.Area"
              value={last?.mem_mb != null ? String(Math.round(last.mem_mb)) : '—'}
              unit="MB"
              tone={last?.mem_mb != null && last.mem_mb > 800 ? 'warn' : ''}
              spark={sparkOf((p) => p.mem_mb ?? 0)}
              sparkType="area"
              sparkColor={C.mem}
              delta={deltaOf(last?.mem_mb, prev?.mem_mb, false)}
              note={status ? t('app.admin.overview.kpis.rssNote', { pid: status.process.pid }) : undefined}
            />
            <Kpi
              label={t('app.admin.overview.kpis.cpu')}
              tag="Tiny.Area"
              value={last?.cpu_pct != null ? last.cpu_pct.toFixed(1) : '—'}
              unit="%"
              tone={last?.cpu_pct != null && last.cpu_pct > 60 ? 'warn' : ''}
              spark={sparkOf((p) => p.cpu_pct ?? 0)}
              sparkType="area"
              sparkColor={C.cpu}
              delta={deltaOf(last?.cpu_pct, prev?.cpu_pct, false)}
              note={
                status
                  ? t('app.admin.overview.kpis.threadsConns', {
                      threads: status.process.threads,
                      conns: status.process.connections,
                    })
                  : undefined
              }
            />
          </div>

          <div className="ac-grid">
            <section className="ac-panel ac-span8">
              <div className="ac-panel-head">
                {t('app.admin.overview.trends.title')}
                <span className="ac-panel-hint">
                  Area+Line · /api/app/metrics/timeseries?range={range}
                  {series.source === 'memory' ? ' · memory' : ''}
                </span>
              </div>
              <div className="ac-panel-body">
                <div className="ac-chart-block">
                  <div className="ac-chart-title">
                    {t('app.admin.overview.trends.requestRate')} / {t('app.admin.overview.trends.errorRate')}
                  </div>
                  {points.length === 0 ? (
                    <div className="ac-empty">{t('app.admin.overview.trends.noData')}</div>
                  ) : (
                    <DualAxes
                      data={trendData}
                      xField="time"
                      height={230}
                      autoFit
                      theme={DARK_THEME}
                      legend={false}
                      children={[
                        {
                          type: 'interval',
                          yField: 'rpm',
                          style: { fill: C.rpm, fillOpacity: 0.5, maxWidth: 14, radiusTopLeft: 2, radiusTopRight: 2 },
                        },
                        {
                          type: 'line',
                          yField: 'err_rate',
                          style: { stroke: C.err, lineWidth: 2 },
                          axis: { y: { position: 'right' } },
                        },
                      ]}
                      axis={chartAxis}
                    />
                  )}
                  <div className="ac-chart-legend">
                    <span>
                      <i className="ac-legend-dot" style={{ background: C.rpm }} />
                      {t('app.admin.overview.trends.requestRate')}
                    </span>
                    <span>
                      <i className="ac-legend-dot" style={{ background: C.err }} />
                      {t('app.admin.overview.trends.errorRate')}
                    </span>
                  </div>
                </div>

                <div className="ac-chart-block">
                  <div className="ac-chart-title">{t('app.admin.overview.trends.latency')}</div>
                  {points.length === 0 ? (
                    <div className="ac-empty">{t('app.admin.overview.trends.noData')}</div>
                  ) : (
                    <Line
                      data={latencyData}
                      xField="time"
                      yField="value"
                      colorField="type"
                      height={150}
                      autoFit
                      theme={DARK_THEME}
                      legend={false}
                      scale={{ color: { range: [C.avg, C.p95] } }}
                      style={{ lineWidth: 1.8 }}
                      axis={chartAxis}
                    />
                  )}
                  <div className="ac-chart-legend">
                    <span>
                      <i className="ac-legend-dot" style={{ background: C.avg }} />
                      {t('app.admin.overview.trends.avg')}
                    </span>
                    <span>
                      <i className="ac-legend-dot" style={{ background: C.p95 }} />
                      {t('app.admin.overview.trends.p95')}
                    </span>
                  </div>
                </div>
              </div>
            </section>

            <section className="ac-panel ac-span4">
              <div className="ac-panel-head">
                {t('app.admin.overview.health.title')}
                <span className="ac-panel-hint">components · redis/status</span>
              </div>
              <div className="ac-panel-body">
                {compSummary ? (
                  <div className="ac-health-top">
                    <Ring
                      pct={runningPct}
                      color={ringColor}
                      label={`${compSummary.running}/${compSummary.total}`}
                      sub={t('app.admin.overview.health.running')}
                    />
                    <div className="ac-health-legend">
                      <div className="row">
                        <i className="ac-legend-dot" style={{ background: C.s2xx }} />
                        {t('app.admin.overview.health.healthy')}
                        <b>{compSummary.healthy}</b>
                      </div>
                      <div className="row">
                        <i className="ac-legend-dot" style={{ background: C.p95 }} />
                        {t('app.admin.overview.health.starting')}
                        <b>{compSummary.starting}</b>
                      </div>
                      <div className="row">
                        <i className="ac-legend-dot" style={{ background: C.err }} />
                        {t('app.admin.overview.health.unhealthy')}
                        <b>{compSummary.unhealthy}</b>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="ac-empty">{t('app.admin.overview.health.unavailable')}</div>
                )}

                <div className="ac-hrow">
                  <span className="k">{t('app.admin.overview.health.redis')}</span>
                  <span className="v">
                    {redis ? (
                      redis.reachable ? (
                        <>
                          <span className="ac-dot ok" /> {redis.latency_ms ?? '—'} ms
                        </>
                      ) : (
                        <>
                          <span className="ac-dot danger" /> {t('app.admin.overview.health.unavailable')}
                        </>
                      )
                    ) : (
                      '—'
                    )}
                  </span>
                </div>
                <div className="ac-hrow">
                  <span className="k">{t('app.admin.overview.health.workers')}</span>
                  <span className="v">
                    {redis
                      ? t('app.admin.overview.health.alive', {
                          alive: redis.workers.alive,
                          expected: redis.workers.expected,
                        })
                      : '—'}
                  </span>
                </div>
                <div className="ac-hrow">
                  <span className="k">{t('app.admin.overview.health.schema')}</span>
                  <span className="v">
                    {status?.schema_state.head
                      ? `${status.schema_state.applied ?? '—'} / ${status.schema_state.head}`
                      : status?.schema_state.applied ?? '—'}
                  </span>
                </div>
                <div className="ac-hrow">
                  <span className="k">{t('app.admin.overview.health.gitQueue')}</span>
                  <span className="v">
                    {status
                      ? `clone ${status.git_operations.active_clones} · push ${status.git_operations.active_pushes} · ${status.git_operations.queue_size}`
                      : '—'}
                  </span>
                </div>
                <div className="ac-hrow">
                  <span className="k">{t('app.admin.overview.health.uptime')}</span>
                  <span className="v">{status?.uptime_formatted ?? '—'}</span>
                </div>
              </div>
            </section>

            <section className="ac-panel ac-span4">
              <div className="ac-panel-head">
                {t('app.admin.overview.distribution.title')}
                <span className="ac-panel-hint">Pie</span>
              </div>
              <div className="ac-panel-body">
                <div className="ac-donut-wrap">
                  <div className="ac-donut">
                    <Pie
                      data={pieData}
                      angleField="value"
                      colorField="type"
                      height={150}
                      autoFit
                      theme={DARK_THEME}
                      innerRadius={0.62}
                      legend={false}
                      label={false}
                      scale={{ color: { range: [C.s2xx, C.s3xx, C.s4xx, C.s5xx] } }}
                    />
                    <div className="ac-donut-center">
                      <span className="n">{okPct.toFixed(1)}%</span>
                      <span className="l">{t('app.admin.overview.distribution.successRate')}</span>
                    </div>
                  </div>
                  <div className="ac-dlegend">
                    {pieData.map((d, i) => (
                      <div className="row" key={d.type}>
                        <i
                          className="ac-legend-dot"
                          style={{ background: [C.s2xx, C.s3xx, C.s4xx, C.s5xx][i] }}
                        />
                        {d.type}
                        <span className="n">{d.value.toLocaleString()}</span>
                        <span className="p">{totalReq ? `${((d.value / totalReq) * 100).toFixed(1)}%` : '0%'}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </section>

            <section className="ac-panel ac-span4">
              <div className="ac-panel-head">
                {t('app.admin.overview.platform.title')}
                <span className="ac-panel-hint">/api/v1/stats/platform</span>
              </div>
              <div className="ac-panel-body">
                <div className="ac-statline">
                  <div className="ac-stat">
                    <span className="ac-stat-label">{t('app.admin.overview.platform.repositories')}</span>
                    <span className="ac-stat-value">{(platform?.repository_count ?? 0).toLocaleString()}</span>
                  </div>
                  <div className="ac-stat">
                    <span className="ac-stat-label">{t('app.admin.overview.platform.commits')}</span>
                    <span className="ac-stat-value">{(platform?.commit_count ?? 0).toLocaleString()}</span>
                  </div>
                  <div className="ac-stat">
                    <span className="ac-stat-label">{t('app.admin.overview.platform.users')}</span>
                    <span className="ac-stat-value">{(platform?.user_count ?? 0).toLocaleString()}</span>
                  </div>
                  <div className="ac-stat">
                    <span className="ac-stat-label">{t('app.admin.overview.platform.uptime')}</span>
                    <span className="ac-stat-value">{status?.uptime_formatted ?? '—'}</span>
                  </div>
                </div>
              </div>
            </section>

            <section className="ac-panel ac-span4">
              <div className="ac-panel-head">
                {t('app.admin.overview.monitoring.title')}
                <span className="ac-panel-hint">/api/app/monitoring</span>
                <span className="right">
                  <span className={`ac-chip ${monitoring?.grafana.running ? 'ok' : ''}`}>
                    {monitoring?.grafana.running
                      ? t('app.admin.overview.monitoring.running')
                      : t('app.admin.overview.monitoring.stopped')}
                  </span>
                </span>
              </div>
              <div className="ac-panel-body">
                <div className="ac-mon-row">
                  <span className={`ac-dot ${monitoring?.grafana.running ? 'ok' : 'danger'}`} />
                  Grafana
                  <span className="v">
                    {monitoring?.grafana.ready
                      ? t('app.admin.overview.monitoring.ready')
                      : t('app.admin.overview.monitoring.notReady')}
                  </span>
                </div>
                <div className="ac-mon-row">
                  <span className={`ac-dot ${monitoring?.prometheus.running ? 'ok' : 'danger'}`} />
                  Prometheus
                  <span className="v">
                    {monitoring?.prometheus.running
                      ? t('app.admin.overview.monitoring.running')
                      : t('app.admin.overview.monitoring.stopped')}
                  </span>
                </div>
                {monError && <div className="ac-empty lv-warn">{monError}</div>}
                <div className="ac-mon-foot">
                  <Switch
                    size="small"
                    checked={monitoring?.grafana.running === true}
                    loading={monBusy}
                    disabled={monitoring?.available !== true}
                    onChange={toggleMonitoring}
                  />
                  <Button
                    size="small"
                    disabled={monitoring?.grafana.ready !== true}
                    onClick={openGrafana}
                    style={{ marginLeft: 'auto' }}
                  >
                    {t('app.admin.overview.monitoring.open')} <ArrowRightOutlined />
                  </Button>
                </div>
              </div>
            </section>

            <section className="ac-panel ac-span12">
              <div className="ac-panel-head">
                {t('app.admin.overview.recentErrors.title')}
                <span className="ac-panel-hint">/api/app/logs/content?level=error&lines={RECENT_ERROR_LINES}</span>
                <Link className="ac-panel-link" to="/admin/logs">
                  {t('app.admin.overview.recentErrors.open')} <ArrowRightOutlined />
                </Link>
              </div>
              <div className="ac-panel-body">
                {recentErrors.length === 0 ? (
                  <div className="ac-empty">{t('app.admin.overview.recentErrors.empty')}</div>
                ) : (
                  <div className="ac-mini-term">
                    {recentErrors.map((line, i) => {
                      const { head, level, tail } = splitLine(line);
                      return (
                        <div className={`ac-log-line${level ? ` lv-${level.toLowerCase()}` : ''}`} key={i}>
                          <span className="ac-log-text">
                            {head}
                            {level && <span className="ac-log-lvl">{level}</span>}
                            {tail}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </section>
          </div>
        </>
      )}
    </div>
  );
}
