import { useCallback, useEffect, useState, type ReactNode } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Tooltip } from 'antd';
import {
  BugOutlined,
  ClusterOutlined,
  DashboardOutlined,
  FileTextOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  SettingOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import { adminApi, type AppStatus } from '../../api/admin';
import AdminHeader from '../../components/admin/AdminHeader';
import PermissionPanel from '../../components/admin/PermissionPanel';
import '../../components/admin/admin.css';

interface SectionDef {
  key: string;
  path: string;
  icon: ReactNode;
  enabled: boolean;
}

const COLLAPSE_KEY = 'perseus.admin.rail.collapsed';
const STATUS_INTERVAL_MS = 15_000;

export default function AdminConsolePage() {
  const { t } = useTranslation();
  const [collapsed, setCollapsed] = useState<boolean>(() => {
    try {
      return localStorage.getItem(COLLAPSE_KEY) === '1';
    } catch {
      return false;
    }
  });
  const [status, setStatus] = useState<AppStatus | null>(null);

  useEffect(() => {
    try {
      localStorage.setItem(COLLAPSE_KEY, collapsed ? '1' : '0');
    } catch {
      /* ignore storage failures (private mode / quota) */
    }
  }, [collapsed]);

  const refreshStatus = useCallback(() => {
    adminApi.getStatus().then(setStatus).catch(() => {});
  }, []);

  useEffect(() => {
    refreshStatus();
    const id = setInterval(refreshStatus, STATUS_INTERVAL_MS);
    return () => clearInterval(id);
  }, [refreshStatus]);

  const sections: SectionDef[] = [
    { key: 'overview', path: '/admin', icon: <DashboardOutlined />, enabled: true },
    { key: 'components', path: '/admin/components', icon: <ClusterOutlined />, enabled: true },
    { key: 'config', path: '/admin/config', icon: <SettingOutlined />, enabled: true },
    { key: 'logs', path: '/admin/logs', icon: <FileTextOutlined />, enabled: true },
    { key: 'operations', path: '/admin/operations', icon: <ThunderboltOutlined />, enabled: true },
    { key: 'debug', path: '/admin/debug', icon: <BugOutlined />, enabled: true },
  ];

  return (
    <div className="admin-console">
      <AdminHeader status={status} />

      <div className="ac-shell">
        <aside className={`ac-rail${collapsed ? ' collapsed' : ''}`}>
          <div className="ac-rail-head">
            <button
              type="button"
              className="ac-rail-toggle"
              onClick={() => setCollapsed((v) => !v)}
              title={collapsed ? t('app.admin.expand') : t('app.admin.collapse')}
              aria-label={collapsed ? t('app.admin.expand') : t('app.admin.collapse')}
              aria-expanded={!collapsed}
            >
              {collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            </button>
          </div>

          {!collapsed && <div className="ac-rail-cap">{t('app.admin.railTitle')}</div>}

          <nav className="ac-idx">
            {sections.map((section) => {
              const label = t(`app.admin.sections.${section.key}`);
              const item = section.enabled ? (
                <NavLink
                  key={section.key}
                  to={section.path}
                  end={section.path === '/admin'}
                  className={({ isActive }) => `ac-idx-item${isActive ? ' active' : ''}`}
                >
                  <span className="ac-idx-icon">{section.icon}</span>
                  {!collapsed && <span className="ac-idx-label">{label}</span>}
                </NavLink>
              ) : (
                <span key={section.key} className="ac-idx-item disabled">
                  <span className="ac-idx-icon">{section.icon}</span>
                  {!collapsed && <span className="ac-idx-label">{label}</span>}
                  {!collapsed && <span className="ac-idx-soon">{t('app.admin.soon')}</span>}
                </span>
              );
              return collapsed ? (
                <Tooltip key={section.key} title={label} placement="right">
                  {item}
                </Tooltip>
              ) : (
                item
              );
            })}
          </nav>

          {!collapsed && (
            <PermissionPanel
              runningDebug={status?.debug_mode ?? false}
              onToggled={refreshStatus}
            />
          )}
        </aside>

        <main className="ac-stage">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
