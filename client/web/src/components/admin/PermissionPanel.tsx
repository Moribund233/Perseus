import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { App, Switch, Tooltip } from 'antd';
import { adminApi } from '../../api/admin';

interface PermissionPanelProps {
  runningDebug: boolean;
  onToggled: () => void;
}

/**
 * 权限面板：`is_admin` 只读展示真实管理员状态；`app.debug` 可切换，
 * 写入 config.toml 后需重启服务生效（切换后显示待重启提示）。
 */
export default function PermissionPanel({ runningDebug, onToggled }: PermissionPanelProps) {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const [pending, setPending] = useState<boolean | null>(null);
  const [busy, setBusy] = useState(false);

  // 运行态追上目标值（重启完成）即不再显示待重启标记，无需 effect 同步
  const pendingRestart = pending !== null && pending !== runningDebug;
  const target = pendingRestart ? (pending as boolean) : runningDebug;

  const toggle = async (next: boolean) => {
    setBusy(true);
    try {
      const res = await adminApi.setDebugMode(next);
      if (res.success) {
        setPending(res.debug ?? next);
        message.success(res.message);
        onToggled();
      } else {
        message.error(res.message);
      }
    } catch (err) {
      message.error(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="ac-perm">
      <div className="ac-perm-cap">{t('app.admin.permissions.title')}</div>
      <div className="ac-perm-row">
        <span className="ac-perm-label">
          {t('app.admin.permissions.admin')} <span className="ac-mono">is_admin</span>
        </span>
        <span className="ac-perm-on" title={t('app.admin.permissions.adminOn')}>
          {t('app.admin.permissions.on')}
        </span>
      </div>
      <div className="ac-perm-row">
        <span className="ac-perm-label">
          {t('app.admin.permissions.debug')} <span className="ac-mono">app.debug</span>
        </span>
        <Tooltip title={t('app.admin.permissions.debugHint')}>
          <Switch size="small" checked={target} loading={busy} onChange={(v) => void toggle(v)} />
        </Tooltip>
      </div>
      {pendingRestart && <div className="ac-perm-pending">{t('app.admin.permissions.pending')}</div>}
    </div>
  );
}
