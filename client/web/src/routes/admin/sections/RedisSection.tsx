import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Alert, Button } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import { redisApi, type RedisConfig, type RedisStatus } from '../../../api/admin';
import KeyValueLedger from '../../../components/admin/KeyValueLedger';
import AdminSkeleton from '../../../components/admin/AdminSkeleton';

const POLL_MS = 10_000;

function fmtNum(n?: number | null): string {
  return n == null ? '—' : n.toLocaleString('en-US');
}

function fmtBytes(n?: number | null): string {
  if (n == null) return '—';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let v = n;
  let i = 0;
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024;
    i += 1;
  }
  return `${v.toFixed(i ? 1 : 0)} ${units[i]}`;
}

function fmtUptime(sec?: number | null): string {
  if (sec == null) return '—';
  const d = Math.floor(sec / 86400);
  const h = Math.floor((sec % 86400) / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const parts: string[] = [];
  if (d) parts.push(`${d}d`);
  if (h) parts.push(`${h}h`);
  if (m) parts.push(`${m}m`);
  if (!parts.length) parts.push(`${Math.floor(sec % 60)}s`);
  return parts.join(' ');
}

function chip(tone: 'ok' | 'warn' | 'danger' | 'info', text: string) {
  return <span className={`ac-chip ${tone}`}>{text}</span>;
}

export default function RedisSection() {
  const { t } = useTranslation();
  const [status, setStatus] = useState<RedisStatus | null>(null);
  const [config, setConfig] = useState<RedisConfig | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [updatedAt, setUpdatedAt] = useState<string | null>(null);

  const load = useCallback(() => {
    Promise.all([redisApi.getStatus(), redisApi.getConfig()])
      .then(([s, c]) => {
        setStatus(s);
        setConfig(c);
        setError(null);
        setUpdatedAt(new Date().toLocaleTimeString());
      })
      .catch((err: unknown) => {
        setError(err instanceof Error && err.message ? err.message : '');
      });
  }, []);

  useEffect(() => {
    load();
    const id = setInterval(load, POLL_MS);
    return () => clearInterval(id);
  }, [load]);

  const totalKeys = status?.keyspace.reduce((sum, k) => sum + k.keys, 0) ?? 0;
  const hitRate = status?.stats.hit_rate;
  const alive = status?.workers.alive ?? 0;
  const expected = status?.workers.expected ?? 0;

  return (
    <div>
      <div className="ac-page-head">
        <div>
          <h1 className="ac-h1">{t('app.admin.redis.title')}</h1>
          <div className="ac-sub">{t('app.admin.redis.subtitle')}</div>
        </div>
        <div className="ac-toolbar">
          {updatedAt && <span className="ac-updated">{t('app.admin.redis.updatedAt', { time: updatedAt })}</span>}
          <Button size="small" icon={<ReloadOutlined />} onClick={load}>
            {t('app.admin.redis.refresh')}
          </Button>
        </div>
      </div>

      {error && (
        <Alert
          type="error"
          showIcon
          message={t('app.admin.redis.loadFailed')}
          description={error}
          style={{ marginBottom: 18 }}
        />
      )}

      {!status && !error && <AdminSkeleton heading={t('app.admin.redis.title')} rows={6} />}

      {status && !status.configured && (
        <div className="ac-banner warn">
          <div>
            <div className="ac-banner-title">{t('app.admin.redis.notConfigured.title')}</div>
            <div className="ac-banner-desc">{t('app.admin.redis.notConfigured.desc')}</div>
          </div>
        </div>
      )}

      {status && status.configured && !status.reachable && (
        <div className="ac-banner danger">
          <div>
            <div className="ac-banner-title">{t('app.admin.redis.unreachable.title')}</div>
            <div className="ac-banner-desc">{t('app.admin.redis.unreachable.desc')}</div>
          </div>
        </div>
      )}

      {status && (
        <div className="ac-summary">
          <div className="ac-summary-cell">
            <div className="ac-summary-value">
              {status.reachable
                ? chip('ok', t('app.admin.redis.connected'))
                : chip(status.configured ? 'danger' : 'warn', t('app.admin.redis.disconnected'))}
            </div>
            <div className="ac-summary-label">{t('app.admin.redis.summary.connection')}</div>
          </div>
          <div className="ac-summary-cell">
            <div className="ac-summary-value" style={{ color: alive < expected ? 'var(--ac-warn)' : 'var(--ac-ok)' }}>
              {alive}/{expected}
            </div>
            <div className="ac-summary-label">{t('app.admin.redis.summary.workers')}</div>
          </div>
          <div className="ac-summary-cell">
            <div className="ac-summary-value" style={{ color: status.pubsub.mismatch ? 'var(--ac-danger)' : undefined }}>
              {fmtNum(status.pubsub.pattern_subscriptions)}
            </div>
            <div className="ac-summary-label">{t('app.admin.redis.summary.subscriptions')}</div>
          </div>
          <div className="ac-summary-cell">
            <div className="ac-summary-value">{fmtNum(totalKeys)}</div>
            <div className="ac-summary-label">{t('app.admin.redis.summary.keys')}</div>
          </div>
          <div className="ac-summary-cell">
            <div className="ac-summary-value" style={{ color: (status.stats.evicted_keys ?? 0) > 0 ? 'var(--ac-warn)' : undefined }}>
              {fmtNum(status.stats.evicted_keys)}
            </div>
            <div className="ac-summary-label">{t('app.admin.redis.summary.evicted')}</div>
          </div>
          <div className="ac-summary-cell">
            <div className="ac-summary-value">{hitRate == null ? '—' : `${(hitRate * 100).toFixed(1)}%`}</div>
            <div className="ac-summary-label">{t('app.admin.redis.summary.hitRate')}</div>
          </div>
        </div>
      )}

      {status && (
        <div className="ac-panel">
          <div className="ac-panel-head">
            {t('app.admin.redis.workers.title')}
            <span className="ac-panel-hint">{t('app.admin.redis.workers.hint')}</span>
            {status.pubsub.mismatch && chip('danger', t('app.admin.redis.workers.mismatch'))}
          </div>
          <div className="ac-panel-body">
            {status.workers.items.length === 0 ? (
              <div className="ac-empty">{t('app.admin.redis.workers.empty')}</div>
            ) : (
              <div className="ac-env-wrap">
                <table className="ac-env-table">
                  <thead>
                    <tr>
                      <th>worker</th>
                      <th>pid / host</th>
                      <th>{t('app.admin.redis.workers.age')}</th>
                      <th>{t('app.admin.redis.workers.bus')}</th>
                      <th>pub / recv</th>
                      <th>{t('app.admin.redis.workers.conns')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {status.workers.items.map((w, i) => (
                      <tr key={w.worker_id ?? `worker-${i}`}>
                        <td className="ac-mono">{w.worker_id?.slice(0, 12) ?? '—'}</td>
                        <td className="ac-mono">
                          {w.pid ?? '—'} · {w.host ?? '—'}
                        </td>
                        <td className="ac-mono">{w.age_seconds == null ? '—' : `${w.age_seconds}s`}</td>
                        <td>
                          {w.alive
                            ? w.bus_running
                              ? chip('ok', 'running')
                              : chip('warn', 'no-bus')
                            : chip('danger', 'stale')}
                        </td>
                        <td className="ac-mono">
                          {fmtNum(w.bus_published)} / {fmtNum(w.bus_received)}
                          {w.bus_publish_failures > 0 && (
                            <span style={{ color: 'var(--ac-warn)' }}> ({w.bus_publish_failures}✗)</span>
                          )}
                        </td>
                        <td className="ac-mono">
                          {w.local_connections} / {w.presence_rooms}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {status && (
        <div className="ac-panel">
          <div className="ac-panel-head">
            {t('app.admin.redis.pubsub.title')}
            <span className="ac-panel-hint">
              {t('app.admin.redis.pubsub.hint', {
                subs: fmtNum(status.pubsub.pattern_subscriptions),
                workers: status.pubsub.expected_workers,
              })}
            </span>
          </div>
          <div className="ac-panel-body">
            <KeyValueLedger
              rows={[
                {
                  key: 'numpat',
                  label: t('app.admin.redis.pubsub.numpat'),
                  value: `${fmtNum(status.pubsub.pattern_subscriptions)} / ${status.pubsub.expected_workers}`,
                },
                {
                  key: 'channels',
                  label: t('app.admin.redis.pubsub.channels'),
                  value:
                    status.pubsub.channels.length > 0 ? (
                      <span className="ac-mono">{status.pubsub.channels.join(', ')}</span>
                    ) : (
                      '—'
                    ),
                },
              ]}
            />
          </div>
        </div>
      )}

      {status && status.keyspace.length > 0 && (
        <div className="ac-panel">
          <div className="ac-panel-head">{t('app.admin.redis.keyspace.title')}</div>
          <div className="ac-panel-body">
            <div className="ac-env-wrap">
              <table className="ac-env-table">
                <thead>
                  <tr>
                    <th>namespace</th>
                    <th>{t('app.admin.redis.keyspace.use')}</th>
                    <th>ttl</th>
                    <th>{t('app.admin.redis.keyspace.policy')}</th>
                    <th>keys</th>
                  </tr>
                </thead>
                <tbody>
                  {status.keyspace.map((k) => (
                    <tr key={k.domain}>
                      <td className="ac-mono">{k.namespace}</td>
                      <td>{k.use}</td>
                      <td className="ac-mono">{k.ttl}</td>
                      <td>
                        {k.policy === 'persistent'
                          ? chip('info', t('app.admin.redis.keyspace.persistent'))
                          : chip('ok', t('app.admin.redis.keyspace.evictable'))}
                      </td>
                      <td className="ac-mono">{fmtNum(k.keys)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {status && status.reachable && (
        <div className="ac-panel">
          <div className="ac-panel-head">{t('app.admin.redis.metrics.title')}</div>
          <div className="ac-panel-body">
            <KeyValueLedger
              rows={[
                { key: 'version', label: t('app.admin.redis.metrics.version'), value: status.server.version ?? '—' },
                { key: 'mode', label: t('app.admin.redis.metrics.mode'), value: status.server.mode ?? '—' },
                { key: 'uptime', label: t('app.admin.redis.metrics.uptime'), value: fmtUptime(status.server.uptime_seconds) },
                { key: 'latency', label: t('app.admin.redis.metrics.latency'), value: status.latency_ms == null ? '—' : `${status.latency_ms} ms` },
                {
                  key: 'memory',
                  label: t('app.admin.redis.metrics.memory'),
                  value: `${fmtBytes(status.memory.used)} / ${fmtBytes(status.memory.maxmemory)} (${status.memory.maxmemory_policy ?? '—'})`,
                },
                {
                  key: 'frag',
                  label: t('app.admin.redis.metrics.fragmentation'),
                  value: status.memory.fragmentation_ratio ?? '—',
                },
                { key: 'clients', label: t('app.admin.redis.metrics.clients'), value: fmtNum(status.clients.connected) },
                { key: 'ops', label: t('app.admin.redis.metrics.ops'), value: `${status.stats.ops_per_sec ?? '—'} ops/s` },
                {
                  key: 'hits',
                  label: t('app.admin.redis.metrics.hits'),
                  value: `${fmtNum(status.stats.keyspace_hits)} / ${fmtNum(status.stats.keyspace_misses)}`,
                },
                {
                  key: 'expired',
                  label: t('app.admin.redis.metrics.expired'),
                  value: `${fmtNum(status.stats.expired_keys)} / ${fmtNum(status.stats.evicted_keys)}`,
                },
              ]}
            />
          </div>
        </div>
      )}

      {config && (
        <div className="ac-panel">
          <div className="ac-panel-head">
            {t('app.admin.redis.config.title')}
            <span className="ac-panel-hint">{t('app.admin.redis.config.hint')}</span>
          </div>
          <div className="ac-panel-body">
            <KeyValueLedger
              rows={[
                { key: 'url', label: 'url', value: <span className="ac-mono">{config.settings.url || '—'}</span> },
                { key: 'namespace', label: 'namespace', value: config.settings.namespace },
                { key: 'pubsub', label: 'pubsub_prefix', value: config.settings.pubsub_prefix },
                { key: 'cooldown', label: 'reconnect_cooldown', value: `${config.settings.reconnect_cooldown}s` },
                {
                  key: 'maxmemory',
                  label: 'maxmemory',
                  value: config.runtime.maxmemory ? fmtBytes(config.runtime.maxmemory) : '—',
                },
                { key: 'policy', label: 'maxmemory-policy', value: config.runtime.maxmemory_policy ?? '—' },
              ]}
            />
          </div>
        </div>
      )}

      {status && (
        <div className="ac-panel">
          <div className="ac-panel-head">{t('app.admin.redis.degradation.title')}</div>
          <div className="ac-panel-body">
            <KeyValueLedger
              rows={[
                { key: 'unavailable', label: 'unavailable_returns', value: fmtNum(status.degradation.unavailable_returns) },
                { key: 'connect', label: 'connect_failures', value: fmtNum(status.degradation.connect_failures) },
                { key: 'require', label: 'require_failures', value: fmtNum(status.degradation.require_failures) },
                {
                  key: 'bus',
                  label: 'bus_running',
                  value: status.degradation.bus_running ? chip('ok', 'true') : chip('warn', 'false'),
                },
                { key: 'pub', label: 'bus_published', value: fmtNum(status.degradation.bus_published) },
                { key: 'recv', label: 'bus_received', value: fmtNum(status.degradation.bus_received) },
                { key: 'pubfail', label: 'bus_publish_failures', value: fmtNum(status.degradation.bus_publish_failures) },
                { key: 'dispfail', label: 'bus_dispatch_failures', value: fmtNum(status.degradation.bus_dispatch_failures) },
                { key: 'lasterr', label: 'bus_last_error', value: status.degradation.bus_last_error ?? '—' },
              ]}
            />
          </div>
        </div>
      )}
    </div>
  );
}
