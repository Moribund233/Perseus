import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { App, Alert, Button } from 'antd';
import { PoweroffOutlined, ReloadOutlined } from '@ant-design/icons';
import { operationsApi } from '../../../api/admin';
import ConfirmDangerModal from '../../../components/admin/ConfirmDangerModal';

type Pending = 'restart' | 'shutdown' | null;

export default function OperationsSection() {
  const { t } = useTranslation();
  const { message } = App.useApp();

  const [pending, setPending] = useState<Pending>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async (kind: Exclude<Pending, null>) => {
    setBusy(true);
    try {
      if (kind === 'restart') {
        const res = await operationsApi.restart();
        message.warning(res.message || t('app.admin.operations.restart.done'));
      } else {
        const res = await operationsApi.shutdown();
        message.warning(res.message || t('app.admin.operations.shutdown.done'));
      }
      setError(null);
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setError(msg);
      message.error(msg);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <div className="ac-page-head">
        <div>
          <h1 className="ac-h1">{t('app.admin.operations.title')}</h1>
          <div className="ac-sub">{t('app.admin.operations.subtitle')}</div>
        </div>
      </div>

      {error && (
        <Alert
          type="error"
          showIcon
          message={t('app.admin.operations.failed')}
          description={error}
          style={{ marginBottom: 18 }}
        />
      )}

      <div className="ac-panel ac-op-list">
        <div className="ac-op-row">
          <div>
            <h3 className="ac-op-h3">
              {t('app.admin.operations.restart.title')}
              <span className="ac-op-flag warn">{t('app.admin.operations.restart.flag')}</span>
            </h3>
            <p className="ac-op-desc">{t('app.admin.operations.restart.desc')}</p>
            <div className="ac-op-ep">{t('app.admin.operations.restart.endpoint')}</div>
          </div>
          <Button
            danger
            icon={<ReloadOutlined />}
            loading={pending === 'restart' && busy}
            onClick={() => setPending('restart')}
          >
            {t('app.admin.operations.restart.action')}
          </Button>
        </div>

        <div className="ac-op-row risky">
          <div>
            <h3 className="ac-op-h3">
              {t('app.admin.operations.shutdown.title')}
              <span className="ac-op-flag danger">{t('app.admin.operations.shutdown.flag')}</span>
            </h3>
            <p className="ac-op-desc">{t('app.admin.operations.shutdown.desc')}</p>
            <div className="ac-op-ep">{t('app.admin.operations.shutdown.endpoint')}</div>
          </div>
          <Button
            danger
            icon={<PoweroffOutlined />}
            loading={pending === 'shutdown' && busy}
            onClick={() => setPending('shutdown')}
          >
            {t('app.admin.operations.shutdown.action')}
          </Button>
        </div>
      </div>

      <ConfirmDangerModal
        open={pending === 'restart'}
        title={t('app.admin.operations.restart.title')}
        description={t('app.admin.operations.restart.desc')}
        confirmWord={t('app.admin.operations.restart.confirmWord')}
        actionLabel={t('app.admin.operations.restart.action')}
        busy={pending === 'restart' && busy}
        onAction={() => void run('restart')}
        onClose={() => setPending(null)}
      />
      <ConfirmDangerModal
        open={pending === 'shutdown'}
        title={t('app.admin.operations.shutdown.title')}
        description={t('app.admin.operations.shutdown.desc')}
        confirmWord={t('app.admin.operations.shutdown.confirmWord')}
        actionLabel={t('app.admin.operations.shutdown.action')}
        busy={pending === 'shutdown' && busy}
        onAction={() => void run('shutdown')}
        onClose={() => setPending(null)}
      />
    </div>
  );
}