import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Alert, Button } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import { adminApi, type AppStatus } from '../../../api/admin';
import { statsApi, type PlatformStats } from '../../../api/stats';
import KeyValueLedger from '../../../components/admin/KeyValueLedger';
import { formatBytesMb } from '../../../components/admin/health';

interface OverviewData {
  status: AppStatus;
  platform: PlatformStats;
}

function formatTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleTimeString();
}

async function fetchOverview(): Promise<OverviewData> {
  const [status, platform] = await Promise.all([adminApi.getStatus(), statsApi.getPlatformStats()]);
  return { status, platform };
}

export default function OverviewSection() {
  const { t } = useTranslation();
  const [data, setData] = useState<OverviewData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [updatedAt, setUpdatedAt] = useState<string | null>(null);

  const refresh = () => {
    fetchOverview()
      .then((d) => {
        setData(d);
        setError(null);
        setUpdatedAt(new Date().toLocaleTimeString());
      })
      .catch((err: unknown) => {
        setError(err instanceof Error && err.message ? err.message : '');
      });
  };

  useEffect(() => {
    let cancelled = false;
    const tick = () => {
      fetchOverview()
        .then((d) => {
          if (cancelled) return;
          setData(d);
          setError(null);
          setUpdatedAt(new Date().toLocaleTimeString());
        })
        .catch((err: unknown) => {
          if (cancelled) return;
          setError(err instanceof Error && err.message ? err.message : '');
        });
    };
    tick();
    const timer = setInterval(tick, 5_000);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, []);

  const status = data?.status;
  const errorMessage = error === null ? null : (error || t('app.admin.overview.loadFailed'));

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

      {status && (
        <>
          <div className="ac-vitals">
            <div className="ac-vital">
              <div className="ac-vital-label">{t('app.admin.overview.vitals.uptime')}</div>
              <div className="ac-vital-value">{status.uptime_formatted}</div>
            </div>
            <div className="ac-vital">
              <div className="ac-vital-label">{t('app.admin.overview.vitals.memory')}</div>
              <div className="ac-vital-value"><span className="ac-vital-unit">RAM</span> {formatBytesMb(status.process.memory_mb)}</div>
            </div>
            <div className="ac-vital">
              <div className="ac-vital-label">{t('app.admin.overview.vitals.cpu')}</div>
              <div className="ac-vital-value">{status.process.cpu_percent}<span className="ac-vital-unit">%</span></div>
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
                  <span className="ac-stat-value">{status.requests.total_requests.toLocaleString()}</span>
                </div>
                <div className="ac-stat">
                  <span className="ac-stat-label">{t('app.admin.overview.requests.active')}</span>
                  <span className="ac-stat-value">{status.requests.active_requests}</span>
                </div>
                <div className="ac-stat">
                  <span className="ac-stat-label">{t('app.admin.overview.requests.rate')}</span>
                  <span className="ac-stat-value">{status.requests.requests_per_second}<span className="ac-vital-unit">/s</span></span>
                </div>
                <div className="ac-stat">
                  <span className="ac-stat-label">{t('app.admin.overview.requests.avgTime')}</span>
                  <span className="ac-stat-value">{status.requests.average_response_time}<span className="ac-vital-unit">ms</span></span>
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
        </>
      )}
    </div>
  );
}