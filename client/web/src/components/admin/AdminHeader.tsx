import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import type { AppStatus } from '../../api/admin';
import { useAuthStore } from '../../stores/auth';
import Logo from '../brand/Logo';

function apiEndpoint(): string {
  const base = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8002';
  // VITE_API_URL 为空字符串 = 与页面同源（走网关）
  if (base === '') {
    return typeof location !== 'undefined' ? `API /api/v1 · ${location.host}` : 'API /api/v1';
  }
  return `API /api/v1 · ${base.replace(/^https?:\/\//, '')}`;
}

/** 控制台顶栏：品牌 / 运行状态 / 环境端点 / 时钟 / 当前用户 */
export default function AdminHeader({ status }: { status: AppStatus | null }) {
  const { t } = useTranslation();
  const user = useAuthStore((s) => s.user);
  const [clock, setClock] = useState(() => new Date().toLocaleTimeString());

  useEffect(() => {
    const id = setInterval(() => setClock(new Date().toLocaleTimeString()), 1000);
    return () => clearInterval(id);
  }, []);

  const debug = status?.debug_mode ?? false;
  const healthy = status?.status === 'running' || status?.status === 'healthy';
  const initials = (user?.username ?? 'AD').slice(0, 2).toUpperCase();

  return (
    <header className="ac-header">
      <div className="ac-header-brand">
        <Logo size={24} />
        <span className="ac-brand-name">Perseus</span>
        <span className="ac-brand-sep">//</span>
        <span className="ac-brand-sub">{t('app.admin.header.console')}</span>
      </div>

      <div className="ac-header-status">
        <span className={`ac-pulse${healthy ? ' on' : ''}`} aria-hidden="true" />
        <span className="ac-status-word">{status?.status ?? t('app.admin.header.unknown')}</span>
        <span className={`ac-chip${debug ? ' debug' : ''}`}>{debug ? 'DEBUG' : 'RELEASE'}</span>
        {status && <span className="ac-version ac-mono">v{status.version}</span>}
      </div>

      <div className="ac-header-right">
        <span className="ac-endpoint ac-mono">{apiEndpoint()}</span>
        <span className="ac-clock ac-mono">{clock}</span>
        <div className="ac-who">
          <span className="ac-av">{initials}</span>
          <span className="ac-who-name ac-mono">{user?.username ?? 'admin'}</span>
        </div>
      </div>
    </header>
  );
}
