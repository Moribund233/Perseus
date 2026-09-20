import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { App, Alert, Button } from 'antd';
import { DatabaseOutlined, FileTextOutlined } from '@ant-design/icons';
import { adminApi, debugApi, type DebugStatus } from '../../../api/admin';
import KeyValueLedger from '../../../components/admin/KeyValueLedger';
import ConfirmDangerModal from '../../../components/admin/ConfirmDangerModal';
import AdminSkeleton from '../../../components/admin/AdminSkeleton';

type Pending = 'initdb' | 'initconf' | null;

function isMasked(value: string): boolean {
  return value.includes('***masked***');
}

export default function DebugSection() {
  const { t } = useTranslation();
  const { message } = App.useApp();

  // 调试工具要求「管理员 且 调试模式」；管理员已由 AdminRoute 保证，此处探测 app.debug
  const [debugEnabled, setDebugEnabled] = useState<boolean | null>(null);
  const [data, setData] = useState<DebugStatus | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [pending, setPending] = useState<Pending>(null);
  const [busy, setBusy] = useState(false);
  const [actionOut, setActionOut] = useState<{ success: boolean; text: string } | null>(null);

  useEffect(() => {
    let cancelled = false;
    adminApi.getStatus()
      .then((res) => {
        if (cancelled) return;
        setDebugEnabled(res.debug_mode);
        if (!res.debug_mode) return;
        return debugApi.getStatus().then((d) => {
          if (cancelled) return;
          setData(d);
        });
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setLoadError(err instanceof Error && err.message ? err.message : '');
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const run = async (kind: Exclude<Pending, null>) => {
    setBusy(true);
    try {
      if (kind === 'initdb') {
        const res = await debugApi.initDb();
        if (res.success) {
          message.warning(res.message || t('app.admin.debug.initdb.done'));
          setActionOut({ success: true, text: res.message });
        } else {
          setActionOut({ success: false, text: res.message });
        }
      } else {
        const res = await debugApi.initConf();
        if (res.success) {
          message.warning(res.message || t('app.admin.debug.initconf.done'));
          setActionOut({ success: true, text: res.backup_path ? `${res.message} · ${res.backup_path}` : res.message });
        } else {
          setActionOut({ success: false, text: res.message });
        }
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      message.error(msg);
      setActionOut({ success: false, text: msg });
    } finally {
      setBusy(false);
    }
  };

  const gated = debugEnabled === false;

  return (
    <div>
      <div className="ac-page-head">
        <div>
          <h1 className="ac-h1">{t('app.admin.debug.title')}</h1>
          <div className="ac-sub">{t('app.admin.debug.subtitle')}</div>
        </div>
      </div>

      {loadError && (
        <Alert type="error" showIcon message={t('app.admin.debug.loadFailed')} description={loadError} style={{ marginBottom: 18 }} />
      )}

      {gated && (
        <div className="ac-banner danger">
          <div>
            <div className="ac-banner-title">{t('app.admin.debug.gate')}</div>
            <div className="ac-banner-desc">{t('app.admin.debug.gateDesc')}</div>
          </div>
        </div>
      )}

      {actionOut && (
        <div className={`ac-banner ${actionOut.success ? 'warn' : 'danger'}`}>
          <div>
            <div className="ac-banner-title">{actionOut.success ? t('app.admin.debug.done') : t('app.admin.debug.failed')}</div>
            <div className="ac-banner-desc">{actionOut.text}</div>
          </div>
        </div>
      )}

      {debugEnabled === null && !loadError && (
        <AdminSkeleton heading={t('app.admin.debug.status.title')} rows={5} />
      )}

      {!gated && data && (
        <>
          <div className="ac-panel">
            <div className="ac-panel-head">{t('app.admin.debug.status.title')}</div>
            <div className="ac-panel-body">
              <KeyValueLedger
                rows={[
                  {
                    key: 'debug',
                    label: t('app.admin.debug.status.debugMode'),
                    value: <span className={`ac-chip ${data.debug_mode ? 'warn' : ''}`}>{String(data.debug_mode)}</span>,
                  },
                  {
                    key: 'config',
                    label: t('app.admin.debug.status.configPath'),
                    value: (
                      <span>
                        <span className="ac-mono">{data.config_path}</span>{' '}
                        <span className="ac-text-dim">{data.config_exists ? t('app.admin.debug.status.yes') : t('app.admin.debug.status.no')}</span>
                      </span>
                    ),
                  },
                  { key: 'dbType', label: t('app.admin.debug.status.databaseType'), value: <span className="ac-mono">{data.database_type}</span> },
                  { key: 'dbUrl', label: t('app.admin.debug.status.databaseUrl'), value: <span className="ac-mono">{data.database_url}</span> },
                  { key: 'stress', label: t('app.admin.debug.status.stressTest'), value: <span className="ac-mono">{String(data.stress_test_mode)}</span> },
                ]}
              />
            </div>
          </div>

          <div className="ac-panel">
            <div className="ac-panel-head">
              {t('app.admin.debug.env.title')}
              <span className="ac-panel-hint">{t('app.admin.debug.env.hint')}</span>
            </div>
            <div className="ac-env-wrap">
              <table className="ac-env-table">
                <thead>
                  <tr>
                    <th>{t('app.admin.debug.env.key')}</th>
                    <th>{t('app.admin.debug.env.value')}</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(data.environment).map(([key, value]) => (
                    <tr key={key}>
                      <td className="ac-mono">{key}</td>
                      <td className={isMasked(value) ? 'ac-mono masked' : 'ac-mono'}>{value}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {Object.keys(data.environment).length === 0 && (
                <div className="ac-empty">{t('app.admin.debug.env.empty')}</div>
              )}
            </div>
          </div>

          <div className="ac-panel ac-op-list">
            <div className="ac-op-row risky">
              <div>
                <h3 className="ac-op-h3">
                  {t('app.admin.debug.initdb.title')}
                  <span className="ac-op-flag danger">{t('app.admin.debug.initdb.flag')}</span>
                </h3>
                <p className="ac-op-desc">{t('app.admin.debug.initdb.desc')}</p>
                <div className="ac-op-ep">{t('app.admin.debug.initdb.endpoint')}</div>
              </div>
              <Button
                danger
                icon={<DatabaseOutlined />}
                loading={pending === 'initdb' && busy}
                onClick={() => setPending('initdb')}
              >
                {t('app.admin.debug.initdb.action')}
              </Button>
            </div>

            <div className="ac-op-row risky">
              <div>
                <h3 className="ac-op-h3">
                  {t('app.admin.debug.initconf.title')}
                  <span className="ac-op-flag danger">{t('app.admin.debug.initconf.flag')}</span>
                </h3>
                <p className="ac-op-desc">{t('app.admin.debug.initconf.desc')}</p>
                <div className="ac-op-ep">{t('app.admin.debug.initconf.endpoint')}</div>
              </div>
              <Button
                danger
                icon={<FileTextOutlined />}
                loading={pending === 'initconf' && busy}
                onClick={() => setPending('initconf')}
              >
                {t('app.admin.debug.initconf.action')}
              </Button>
            </div>
          </div>

          <ConfirmDangerModal
            open={pending === 'initdb'}
            title={t('app.admin.debug.initdb.title')}
            description={t('app.admin.debug.initdb.desc')}
            confirmWord={t('app.admin.debug.initdb.confirmWord')}
            actionLabel={t('app.admin.debug.initdb.action')}
            busy={pending === 'initdb' && busy}
            onAction={() => void run('initdb')}
            onClose={() => setPending(null)}
          />
          <ConfirmDangerModal
            open={pending === 'initconf'}
            title={t('app.admin.debug.initconf.title')}
            description={t('app.admin.debug.initconf.desc')}
            confirmWord={t('app.admin.debug.initconf.confirmWord')}
            actionLabel={t('app.admin.debug.initconf.action')}
            busy={pending === 'initconf' && busy}
            onAction={() => void run('initconf')}
            onClose={() => setPending(null)}
          />
        </>
      )}
    </div>
  );
}