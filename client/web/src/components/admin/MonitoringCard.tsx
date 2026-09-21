import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button, Switch } from 'antd';
import { BarChartOutlined, ReloadOutlined } from '@ant-design/icons';
import { ApiError } from '../../api/client';
import { GRAFANA_ENTRY, monitoringApi, type MonitoringResponse } from '../../api/admin';

const COMPOSE_HINT = 'docker compose -f docker-compose.monitoring.yml up -d';

function msg(err: unknown): string {
  return err instanceof Error && err.message ? err.message : '';
}

export default function MonitoringCard() {
  const { t } = useTranslation();
  const [data, setData] = useState<MonitoringResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [ssoLoading, setSsoLoading] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setActionError(null);
    try {
      setData(await monitoringApi.getStatus());
    } catch (err) {
      setActionError(t('app.admin.monitoring.loadFailed', { msg: msg(err) }));
    }
  }, [t]);

  useEffect(() => {
    let cancelled = false;
    monitoringApi
      .getStatus()
      .then((d) => {
        if (!cancelled) setData(d);
      })
      .catch((err: unknown) => {
        if (!cancelled) setActionError(t('app.admin.monitoring.loadFailed', { msg: msg(err) }));
      });
    return () => {
      cancelled = true;
    };
  }, [t]);

  const grafana = data?.grafana;
  const running = grafana?.running === true;
  const deployed = Boolean(data?.grafana.container_id || data?.prometheus.container_id);
  const configured = grafana?.configured === true;
  const ready = grafana?.ready === true;
  const canToggle = data?.available === true && deployed;

  const toggle = useCallback(
    async (next: boolean) => {
      setActionError(null);
      setBusy(true);
      try {
        setData(await monitoringApi.setEnabled(next));
      } catch (err) {
        if (err instanceof ApiError && err.status === 409) {
          setActionError(t('app.admin.monitoring.notDeployedHint', { cmd: COMPOSE_HINT }));
        } else {
          setActionError(t('app.admin.monitoring.toggleFailed', { msg: msg(err) }));
        }
      } finally {
        setBusy(false);
      }
    },
    [t],
  );

  const openGrafana = useCallback(async () => {
    setActionError(null);
    setSsoLoading(true);
    try {
      const res = await monitoringApi.sso();
      window.location.assign(res.entry || GRAFANA_ENTRY);
    } catch (err) {
      setActionError(t('app.admin.monitoring.openFailed', { msg: msg(err) }));
    } finally {
      setSsoLoading(false);
    }
  }, [t]);

  const runningLabel = running ? t('app.admin.monitoring.running') : t('app.admin.monitoring.stopped');

  return (
    <div className="ac-panel">
      <div className="ac-panel-head">
        {t('app.admin.monitoring.title')}
        <span className="ac-panel-hint">{t('app.admin.monitoring.actionLabel')}</span>
        <span className={`ac-chip ${running ? 'ok' : 'warn'}`}>{runningLabel}</span>
        <div className="ac-panel-actions">
          {canToggle && (
            <Switch
              checked={running}
              loading={busy}
              onChange={toggle}
              checkedChildren={t('app.admin.monitoring.on')}
              unCheckedChildren={t('app.admin.monitoring.off')}
            />
          )}
          {ready && (
            <Button size="small" icon={<BarChartOutlined />} loading={ssoLoading} onClick={openGrafana}>
              {t('app.admin.monitoring.open')}
            </Button>
          )}
          <Button size="small" icon={<ReloadOutlined />} onClick={load} aria-label={t('app.admin.monitoring.refresh')} />
        </div>
      </div>
      <div className="ac-panel-body">
        {!data && !actionError && <div className="ac-empty">{t('app.admin.monitoring.loading')}</div>}

        {actionError && (
          <div className={`ac-empty ${actionError.startsWith(t('app.admin.monitoring.loadFailed')) ? 'lv-error' : 'lv-warn'}`}>
            {actionError}
          </div>
        )}

        {data && (
          <>
            {data.available === false ? (
              <div className="ac-empty lv-warn">
                {t('app.admin.monitoring.unavailable', { reason: data.reason ?? '-' })}
              </div>
            ) : !deployed ? (
              <div className="ac-empty lv-warn">
                {t('app.admin.monitoring.notDeployed')}
                <br />
                <code>{COMPOSE_HINT}</code>
              </div>
            ) : (
              <>
                <div className="ac-statline">
                  <div className="ac-stat">
                    <span className="ac-stat-label">Grafana</span>
                    <span className={`ac-chip ${grafana?.running ? 'ok' : 'warn'}`}>
                      {grafana?.running ? t('app.admin.monitoring.running') : t('app.admin.monitoring.stopped')}
                    </span>
                  </div>
                  <div className="ac-stat">
                    <span className="ac-stat-label">Prometheus</span>
                    <span className={`ac-chip ${data.prometheus.running ? 'ok' : 'warn'}`}>
                      {data.prometheus.running ? t('app.admin.monitoring.running') : t('app.admin.monitoring.stopped')}
                    </span>
                  </div>
                </div>
                {running && !configured && (
                  <div className="ac-empty lv-warn">{t('app.admin.monitoring.notConfigured')}</div>
                )}
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
}