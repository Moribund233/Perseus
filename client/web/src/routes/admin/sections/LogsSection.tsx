import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { App, Button, InputNumber, Tabs } from 'antd';
import { ClearOutlined } from '@ant-design/icons';
import { logsApi } from '../../../api/admin';
import ConfirmDangerModal from '../../../components/admin/ConfirmDangerModal';
import FileLogTab from './FileLogTab';
import StreamLogTab from './StreamLogTab';

const CLEANUP_CONFIRM_WORD = 'CLEANUP';

/** 日志查看器：文件日志（历史检索）与实时日志流（WS 订阅）两个 tab */
export default function LogsSection() {
  const { t } = useTranslation();
  const { message } = App.useApp();

  const [cleanupOpen, setCleanupOpen] = useState(false);
  const [keepDays, setKeepDays] = useState(30);
  const [cleanupBusy, setCleanupBusy] = useState(false);
  const [cleanupOut, setCleanupOut] = useState<{ success: boolean; text: string } | null>(null);

  const doCleanup = async () => {
    setCleanupBusy(true);
    try {
      const res = await logsApi.cleanup(keepDays);
      if (res.success) {
        const text = t('app.admin.logs.cleanup.done', { count: res.deleted_count, days: res.keep_days });
        message.success(text);
        setCleanupOut({ success: true, text });
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
          <Button danger size="small" icon={<ClearOutlined />} onClick={() => setCleanupOpen(true)}>
            {t('app.admin.logs.cleanup.button')}
          </Button>
        </div>
      </div>

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

      <Tabs
        defaultActiveKey="file"
        destroyOnHidden
        items={[
          { key: 'file', label: t('app.admin.logs.tabs.file'), children: <FileLogTab /> },
          { key: 'stream', label: t('app.admin.logs.tabs.stream'), children: <StreamLogTab /> },
        ]}
      />

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
