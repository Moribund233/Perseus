import { useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Alert, Button, Segmented } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import { adminApi, type ComponentInfo, type ComponentsResponse } from '../../../api/admin';
import ComponentRow from '../../../components/admin/ComponentRow';
import KeyValueLedger from '../../../components/admin/KeyValueLedger';
import {
  componentTone,
  formatDuration,
  groupOf,
  GROUP_ORDER,
  isProblem,
  type Tone,
} from '../../../components/admin/health';

const HISTORY_SIZE = 14;

function formatStartedAt(iso: string | null): string {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString();
}

interface HistoryMap {
  [service: string]: Tone[];
}

export default function ComponentsSection() {
  const { t } = useTranslation();
  const [data, setData] = useState<ComponentsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<HistoryMap>({});
  const [filter, setFilter] = useState<'all' | 'problems'>('all');
  const [selected, setSelected] = useState<string | null>(null);
  const [updatedAt, setUpdatedAt] = useState<string | null>(null);

  const load = () => {
    adminApi.getComponents()
      .then((res) => {
        setData(res);
        setError(null);
        setUpdatedAt(new Date().toLocaleTimeString());
        setHistory((prev) => {
          const next: HistoryMap = { ...prev };
          for (const c of res.components) {
            const tone = componentTone(c);
            next[c.service] = [...(next[c.service] ?? []).slice(-(HISTORY_SIZE - 1)), tone];
          }
          return next;
        });
      })
      .catch((err: unknown) => {
        setError(err instanceof Error && err.message ? err.message : '');
      });
  };

  useEffect(() => {
    let cancelled = false;
    const tick = () => {
      adminApi.getComponents()
        .then((res) => {
          if (cancelled) return;
          setData(res);
          setError(null);
          setUpdatedAt(new Date().toLocaleTimeString());
          setHistory((prev) => {
            const next: HistoryMap = { ...prev };
            for (const c of res.components) {
              const tone = componentTone(c);
              next[c.service] = [...(next[c.service] ?? []).slice(-(HISTORY_SIZE - 1)), tone];
            }
            return next;
          });
        })
        .catch((err: unknown) => {
          if (cancelled) return;
          setError(err instanceof Error && err.message ? err.message : '');
        });
    };
    tick();
    const timer = setInterval(tick, 10_000);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, []);

  const dataError = error === null ? null : (error || t('app.admin.components.loadFailed'));

  const visible = useMemo(() => {
    const list = data?.components ?? [];
    return filter === 'problems' ? list.filter(isProblem) : list;
  }, [data, filter]);

  const groups = useMemo(() => {
    const buckets = new Map<string, ComponentInfo[]>();
    for (const c of visible) {
      const group = groupOf(c.service);
      if (!buckets.has(group)) buckets.set(group, []);
      buckets.get(group)!.push(c);
    }
    const ordered = GROUP_ORDER.filter((g) => buckets.has(g));
    for (const [g] of buckets) {
      if (!ordered.includes(g)) ordered.push(g);
    }
    return ordered.map((g) => ({ key: g, items: buckets.get(g)! }));
  }, [visible]);

  const selectedInfo = data?.components.find((c) => c.service === selected) ?? null;
  const summary = data?.summary;

  return (
    <div>
      <div className="ac-page-head">
        <div>
          <h1 className="ac-h1">{t('app.admin.components.title')}</h1>
          <div className="ac-sub">{t('app.admin.components.subtitle')}</div>
        </div>
        <div className="ac-toolbar">
          <Segmented
            size="small"
            value={filter}
            onChange={(v) => setFilter(v as 'all' | 'problems')}
            options={[
              { label: t('app.admin.components.filterAll'), value: 'all' },
              { label: t('app.admin.components.filterProblems'), value: 'problems' },
            ]}
          />
          {updatedAt && <span className="ac-updated">{t('app.admin.components.updatedAt', { time: updatedAt })}</span>}
          <Button size="small" icon={<ReloadOutlined />} onClick={load}>
            {t('app.admin.components.refresh')}
          </Button>
        </div>
      </div>

      {dataError && (
        <Alert
          type="error"
          showIcon
          message={t('app.admin.components.loadFailed')}
          description={`${dataError} · ${t('app.admin.components.errorHint')}`}
          style={{ marginBottom: 18 }}
        />
      )}

      {data && !data.available && (
        <div className="ac-banner warn">
          <div>
            <div className="ac-banner-title">{t('app.admin.components.degraded.title')}</div>
            <div className="ac-banner-desc">
              {t('app.admin.components.degraded.desc')}
              {data.reason ? ` — ${data.reason}` : ''}
            </div>
          </div>
        </div>
      )}

      {data && summary && data.available && (
        <div className="ac-summary">
          <div className="ac-summary-cell">
            <div className="ac-summary-value">{summary.total}</div>
            <div className="ac-summary-label">{t('app.admin.components.summary.total')}</div>
          </div>
          <div className="ac-summary-cell">
            <div className="ac-summary-value" style={{ color: 'var(--ac-ok)' }}>{summary.running}</div>
            <div className="ac-summary-label">{t('app.admin.components.summary.running')}</div>
          </div>
          <div className="ac-summary-cell">
            <div className="ac-summary-value" style={{ color: 'var(--ac-danger)' }}>{summary.stopped}</div>
            <div className="ac-summary-label">{t('app.admin.components.summary.stopped')}</div>
          </div>
          <div className="ac-summary-cell">
            <div className="ac-summary-value" style={{ color: 'var(--ac-ok)' }}>{summary.healthy}</div>
            <div className="ac-summary-label">{t('app.admin.components.summary.healthy')}</div>
          </div>
          <div className="ac-summary-cell">
            <div className="ac-summary-value" style={{ color: 'var(--ac-danger)' }}>{summary.unhealthy}</div>
            <div className="ac-summary-label">{t('app.admin.components.summary.unhealthy')}</div>
          </div>
          <div className="ac-summary-cell">
            <div className="ac-summary-value" style={{ color: 'var(--ac-warn)' }}>{summary.starting}</div>
            <div className="ac-summary-label">{t('app.admin.components.summary.starting')}</div>
          </div>
        </div>
      )}

      {data && data.available && data.components.length === 0 && (
        <div className="ac-empty">{t('app.admin.components.empty')}</div>
      )}

      {data && data.available && data.components.length > 0 && (
        <div className="ac-components-layout">
          <div>
            {groups.map((group) => (
              <div className="ac-panel" key={group.key}>
                <div className="ac-group-cap">
                  {t(`app.admin.components.groups.${group.key}`)} · {group.items.length}
                </div>
                {group.items.map((c) => (
                  <ComponentRow
                    key={c.service}
                    component={c}
                    history={history[c.service] ?? []}
                    selected={selected === c.service}
                    onClick={() => setSelected(selected === c.service ? null : c.service)}
                  />
                ))}
              </div>
            ))}
          </div>

          <div className="ac-inspector">
            {selectedInfo ? (
              <div className="ac-panel">
                <div className="ac-panel-head">{t('app.admin.components.inspector.title')}</div>
                <div className="ac-panel-body">
                  <div className="ac-inspector-title">
                    {selectedInfo.label || selectedInfo.service}
                    <span className="ac-comp-service">{selectedInfo.service}</span>
                  </div>
                  <div className="ac-inspector-sub">{selectedInfo.image || selectedInfo.name}</div>
                  <KeyValueLedger
                    rows={[
                      { key: 'name', label: t('app.admin.components.inspector.name'), value: selectedInfo.name },
                      { key: 'state', label: t('app.admin.components.inspector.state'), value: selectedInfo.state },
                      { key: 'health', label: t('app.admin.components.inspector.health'), value: selectedInfo.health ?? '—' },
                      { key: 'running', label: t('app.admin.components.inspector.running'), value: selectedInfo.running ? 'true' : 'false' },
                      { key: 'startedAt', label: t('app.admin.components.inspector.startedAt'), value: formatStartedAt(selectedInfo.started_at) },
                      { key: 'uptime', label: t('app.admin.components.inspector.uptime'), value: formatDuration(selectedInfo.uptime_seconds) },
                      { key: 'restarts', label: t('app.admin.components.inspector.restarts'), value: selectedInfo.restart_count ?? '—' },
                      { key: 'exitCode', label: t('app.admin.components.inspector.exitCode'), value: selectedInfo.exit_code ?? '—' },
                      { key: 'statusText', label: t('app.admin.components.inspector.statusText'), value: selectedInfo.status_text ?? '—' },
                    ]}
                  />
                </div>
              </div>
            ) : (
              <div className="ac-panel">
                <div className="ac-panel-body ac-empty">{t('app.admin.components.inspector.hint')}</div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}