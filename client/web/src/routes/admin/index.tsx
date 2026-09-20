import { NavLink, Outlet } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import '../../components/admin/admin.css';

interface SectionDef {
  num: string;
  key: string;
  path: string;
  enabled: boolean;
}

export default function AdminConsolePage() {
  const { t } = useTranslation();

  const sections: SectionDef[] = [
    { num: '01', key: 'overview', path: '/admin', enabled: true },
    { num: '02', key: 'components', path: '/admin/components', enabled: true },
    { num: '03', key: 'config', path: '/admin/config', enabled: true },
    { num: '04', key: 'logs', path: '/admin/logs', enabled: true },
    { num: '05', key: 'operations', path: '/admin/operations', enabled: true },
    { num: '06', key: 'debug', path: '/admin/debug', enabled: true },
  ];

  return (
    <div className="admin-console">
      <aside className="ac-rail">
        <div className="ac-rail-cap">{t('app.admin.railTitle')}</div>
        <nav className="ac-idx">
          {sections.map((section) =>
            section.enabled ? (
              <NavLink
                key={section.key}
                to={section.path}
                end={section.path === '/admin'}
                className={({ isActive }) => `ac-idx-item${isActive ? ' active' : ''}`}
              >
                <span className="ac-idx-num">{section.num}</span>
                {t(`app.admin.sections.${section.key}`)}
              </NavLink>
            ) : (
              <span key={section.key} className="ac-idx-item disabled">
                <span className="ac-idx-num">{section.num}</span>
                {t(`app.admin.sections.${section.key}`)}
                <span className="ac-idx-soon">{t('app.admin.soon')}</span>
              </span>
            ),
          )}
        </nav>
      </aside>
      <main className="ac-stage">
        <Outlet />
      </main>
    </div>
  );
}