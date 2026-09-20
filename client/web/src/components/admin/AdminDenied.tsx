import { Button } from 'antd';
import { ApiOutlined, LockOutlined, StopOutlined } from '@ant-design/icons';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuthStore } from '../../stores/auth';

type DeniedKind = 'source' | 'network' | 'not-admin';

const KEY_BY_KIND: Record<DeniedKind, string> = {
  source: 'source',
  network: 'network',
  'not-admin': 'notAdmin',
};

const ICON_BY_KIND: Record<DeniedKind, React.ReactNode> = {
  source: <StopOutlined />,
  network: <ApiOutlined />,
  'not-admin': <LockOutlined />,
};

/** 控制台拒绝页：来源未授权 / 服务不可达 / 已登录但非管理员 */
export default function AdminDenied({ kind, onRetry }: { kind: DeniedKind; onRetry?: () => void }) {
  const { t } = useTranslation();
  const logout = useAuthStore((s) => s.logout);
  const key = KEY_BY_KIND[kind];

  return (
    <div className="admin-gate">
      <div className="admin-gate-card">
        <div className={`admin-denied-icon ${kind}`}>{ICON_BY_KIND[kind]}</div>
        <div className="admin-gate-title">{t(`app.admin.denied.${key}Title`)}</div>
        <div className="admin-gate-sub">{t(`app.admin.denied.${key}Desc`)}</div>
        <div className="admin-denied-actions">
          {onRetry && (
            <Button type="primary" onClick={onRetry}>{t('app.admin.denied.retry')}</Button>
          )}
          {kind === 'not-admin' ? (
            <Button onClick={() => logout()}>{t('app.admin.denied.logout')}</Button>
          ) : null}
          <Link to={kind === 'not-admin' ? '/dashboard' : '/'}>{t('app.admin.denied.backHome')}</Link>
        </div>
      </div>
    </div>
  );
}
