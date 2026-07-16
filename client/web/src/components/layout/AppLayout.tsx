import { useState } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { Layout, Input, Button, Avatar, Dropdown, Space, Tooltip } from 'antd';
import type { MenuProps } from 'antd';
import {
  DashboardOutlined,
  CodeOutlined,
  PullRequestOutlined,
  EditOutlined,
  MessageOutlined,
  SettingOutlined,
  SearchOutlined,
  BellOutlined,
  PlusOutlined,
  UserOutlined,
  TranslationOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useAuthStore } from '../../stores/auth';

const { Header, Sider, Content } = Layout;

const sidebarBg = '#010409';
const borderColor = '#21262d';
const hoverBg = '#1c2333';
const activeBg = '#1a2332';
const textSecondary = '#8b949e';
const textPrimary = '#e6edf3';
const blueLight = '#58a6ff';
const bluePrimary = '#1f6feb';
const red = '#f85149';

interface NavItemDef {
  key: string;
  path: string;
  icon: React.ReactNode;
  label: string;
  badge?: number;
}

export default function AppLayout() {
  const [collapsed, setCollapsed] = useState(true);
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuthStore();
  const { t, i18n } = useTranslation();

  const navItems: NavItemDef[] = [
    { key: 'dashboard', path: '/dashboard', icon: <DashboardOutlined />, label: t('app.nav.dashboard') },
    { key: 'repositories', path: '/repositories', icon: <CodeOutlined />, label: t('app.nav.repositories') },
    { key: 'pulls', path: '/pulls', icon: <PullRequestOutlined />, label: t('app.nav.pullRequests'), badge: 5 },
    { key: 'editor', path: '/editor', icon: <EditOutlined />, label: t('app.nav.codeEditor') },
    { key: 'chat', path: '/chat', icon: <MessageOutlined />, label: t('app.nav.teamChat'), badge: 3 },
  ];

  const activeKey = navItems.find((item) => location.pathname.startsWith(item.path))?.key || 'dashboard';
  const activeLabel = navItems.find((item) => item.key === activeKey)?.label || t('app.nav.dashboard');

  const userMenu: MenuProps['items'] = [
    { key: 'profile', label: t('app.userMenu.profile') },
    { key: 'settings', label: t('app.userMenu.settings'), onClick: () => navigate('/settings') },
    { type: 'divider' },
    { key: 'logout', label: t('app.userMenu.signOut'), onClick: () => { logout(); navigate('/'); } },
  ];

  const toggleLanguage = () => {
    const next = i18n.language.startsWith('zh') ? 'en' : 'zh';
    i18n.changeLanguage(next);
  };

  return (
    <Layout style={{ height: '100vh' }}>
      <Sider
        collapsible
        collapsed={collapsed}
        trigger={null}
        width={240}
        collapsedWidth={64}
        style={{
          background: sidebarBg,
          borderRight: `1px solid ${borderColor}`,
          height: '100vh',
          position: 'relative',
          overflow: 'hidden',
          zIndex: 100,
        }}
      >
        <div
          style={{
            height: '100%',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            padding: '12px 0',
            minHeight: 0,
          }}
        >
          {/* Logo */}
          <div
            style={{
              width: 40,
              height: 40,
              marginBottom: 20,
              cursor: 'pointer',
              flexShrink: 0,
            }}
            onClick={() => setCollapsed(!collapsed)}
            title="Perseus"
          >
            <img src="/logo-orbit-compact.svg" width="100%" height="100%" alt="Perseus" />
          </div>

          {/* Main Nav */}
          <nav
            style={{
              display: 'flex',
              flexDirection: 'column',
              gap: 4,
              width: '100%',
              padding: '0 8px',
              flex: 1,
              minHeight: 0,
              overflow: 'auto',
            }}
          >
            {navItems.map((item) => {
              const isActive = activeKey === item.key;
              return (
                <div
                  key={item.key}
                  onClick={() => navigate(item.path)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    padding: '10px 12px',
                    borderRadius: 8,
                    cursor: 'pointer',
                    color: isActive ? blueLight : textSecondary,
                    background: isActive ? activeBg : 'transparent',
                    transition: 'all 0.2s',
                    position: 'relative',
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    justifyContent: collapsed ? 'center' : 'flex-start',
                  }}
                  onMouseEnter={(e) => {
                    if (!isActive) {
                      e.currentTarget.style.background = hoverBg;
                      e.currentTarget.style.color = textPrimary;
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!isActive) {
                      e.currentTarget.style.background = 'transparent';
                      e.currentTarget.style.color = textSecondary;
                    }
                  }}
                >
                  {isActive && (
                    <span
                      style={{
                        position: 'absolute',
                        left: -8,
                        top: '50%',
                        transform: 'translateY(-50%)',
                        width: 3,
                        height: 20,
                        background: bluePrimary,
                        borderRadius: '0 3px 3px 0',
                      }}
                    />
                  )}
                  <span style={{ width: 20, height: 20, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, fontSize: 20 }}>
                    {item.icon}
                  </span>
                  {!collapsed && (
                    <span style={{ fontSize: 13, fontWeight: 500, marginLeft: 12, opacity: 1, transition: 'opacity 0.2s', flex: 1 }}>
                      {item.label}
                    </span>
                  )}
                  {!collapsed && item.badge ? (
                    <span
                      style={{
                        background: red,
                        color: '#fff',
                        fontSize: 10,
                        padding: '1px 6px',
                        borderRadius: 10,
                        fontWeight: 600,
                        marginLeft: 'auto',
                      }}
                    >
                      {item.badge}
                    </span>
                  ) : null}
                </div>
              );
            })}
          </nav>

          {/* Bottom section */}
          <div
            style={{
              width: '100%',
              padding: '0 8px',
              display: 'flex',
              flexDirection: 'column',
              gap: 4,
              flexShrink: 0,
            }}
          >
            <Tooltip title={t('app.nav.settings')} placement="right">
              <div
                onClick={() => navigate('/settings')}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  padding: '10px 12px',
                  borderRadius: 8,
                  cursor: 'pointer',
                  color: textSecondary,
                  transition: 'all 0.2s',
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  justifyContent: collapsed ? 'center' : 'flex-start',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = hoverBg;
                  e.currentTarget.style.color = textPrimary;
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = 'transparent';
                  e.currentTarget.style.color = textSecondary;
                }}
              >
                <span style={{ width: 20, height: 20, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, fontSize: 20 }}>
                  <SettingOutlined />
                </span>
                {!collapsed && (
                  <span style={{ fontSize: 13, fontWeight: 500, marginLeft: 12, opacity: 1, transition: 'opacity 0.2s' }}>
                    {t('app.nav.settings')}
                  </span>
                )}
              </div>
            </Tooltip>

            {/* User avatar */}
            <div
              style={{
                padding: collapsed ? '8px 0' : '8px 0',
                textAlign: 'center',
                borderTop: `1px solid ${borderColor}`,
                marginTop: 4,
              }}
            >
              <Dropdown menu={{ items: userMenu }} placement="topRight" trigger={['click']}>
                <Avatar
                  size={32}
                  icon={<UserOutlined />}
                  style={{
                    background: `linear-gradient(135deg, ${bluePrimary}, #bc8cff)`,
                    cursor: 'pointer',
                    flexShrink: 0,
                  }}
                  src={user?.avatar_url}
                >
                  {user?.username?.slice(0, 2).toUpperCase()}
                </Avatar>
              </Dropdown>
            </div>
          </div>
        </div>
      </Sider>

      <Layout>
        <Header
          style={{
            display: 'flex',
            alignItems: 'center',
            padding: '0 20px',
            borderBottom: `1px solid ${borderColor}`,
            height: 48,
            background: '#161b22',
            gap: 16,
            flexShrink: 0,
          }}
        >
          {/* Breadcrumb */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              fontSize: 13,
              color: textSecondary,
              flexShrink: 0,
            }}
          >
            {(() => {
              const repoMatch = location.pathname.match(/^\/repositories\/([^/]+)\/([^/]+)/);
              if (repoMatch) {
                const [, owner, repoName] = repoMatch;
                return (
                  <>
                    <span
                      onClick={() => navigate('/repositories')}
                      style={{ cursor: 'pointer', transition: 'color 0.15s' }}
                      onMouseEnter={(e) => { e.currentTarget.style.color = textPrimary; }}
                      onMouseLeave={(e) => { e.currentTarget.style.color = textSecondary; }}
                    >
                      {t('app.nav.repositories')}
                    </span>
                    <span style={{ color: '#6e7681' }}>/</span>
                    <span style={{ color: textSecondary }}>{owner}</span>
                    <span style={{ color: '#6e7681' }}>/</span>
                    <span style={{ color: textPrimary, fontWeight: 500 }}>{repoName}</span>
                  </>
                );
              }
              return <span style={{ color: textPrimary, fontWeight: 500 }}>{activeLabel}</span>;
            })()}
          </div>

          {/* Search */}
          <div style={{ flex: 1, maxWidth: 480, position: 'relative' }}>
            <SearchOutlined
              style={{
                position: 'absolute',
                left: 10,
                top: '50%',
                transform: 'translateY(-50%)',
                color: '#6e7681',
                fontSize: 16,
                zIndex: 1,
              }}
            />
            <Input
              placeholder={t('app.topBar.searchPlaceholder')}
              style={{
                width: '100%',
                backgroundColor: '#0d1117',
                borderColor: '#30363d',
                color: textPrimary,
                paddingLeft: 34,
                fontSize: 13,
              }}
            />
          </div>

          {/* Actions */}
          <Space size={8} style={{ marginLeft: 'auto' }}>
            <button
              style={{
                width: 32,
                height: 32,
                borderRadius: 8,
                border: 'none',
                background: 'transparent',
                color: textSecondary,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                transition: 'all 0.2s',
                position: 'relative',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = hoverBg;
                e.currentTarget.style.color = textPrimary;
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'transparent';
                e.currentTarget.style.color = textSecondary;
              }}
            >
              <BellOutlined style={{ fontSize: 18 }} />
              <span
                style={{
                  position: 'absolute',
                  top: 6,
                  right: 6,
                  width: 7,
                  height: 7,
                  background: blueLight,
                  borderRadius: '50%',
                  border: `1.5px solid #161b22`,
                }}
              />
            </button>

            <button
              onClick={toggleLanguage}
              style={{
                width: 32,
                height: 32,
                borderRadius: 8,
                border: 'none',
                background: 'transparent',
                color: textSecondary,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                transition: 'all 0.2s',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = hoverBg;
                e.currentTarget.style.color = textPrimary;
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'transparent';
                e.currentTarget.style.color = textSecondary;
              }}
            >
              <TranslationOutlined style={{ fontSize: 18 }} />
            </button>

            <Button
              type="primary"
              icon={<PlusOutlined style={{ fontSize: 14 }} />}
              style={{
                background: bluePrimary,
                borderColor: bluePrimary,
                color: '#fff',
                padding: '6px 14px',
                borderRadius: 8,
                fontSize: 13,
                fontWeight: 500,
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                height: 32,
                lineHeight: '20px',
              }}
            >
              {t('app.topBar.new')}
            </Button>
          </Space>
        </Header>
        <Content style={{ padding: 0, overflow: 'hidden' }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
