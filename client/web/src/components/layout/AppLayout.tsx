import { useState } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { Layout, Menu, Input, Badge, Button, Avatar, Dropdown, Space, Breadcrumb, Tooltip } from 'antd';
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
  BgColorsOutlined,
  TranslationOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useAuthStore } from '../../stores/auth';
const { Header, Sider, Content } = Layout;

export default function AppLayout() {
  const [collapsed, setCollapsed] = useState(true);
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuthStore();
  const { t, i18n } = useTranslation();

  const selectedKey = '/' + location.pathname.split('/')[1];

  const navItems: MenuProps['items'] = [
    { key: '/dashboard', icon: <DashboardOutlined />, label: t('app.nav.dashboard') },
    { key: '/repositories', icon: <CodeOutlined />, label: t('app.nav.repositories') },
    { key: '/pulls', icon: <PullRequestOutlined />, label: t('app.nav.pullRequests') },
    { key: '/editor', icon: <EditOutlined />, label: t('app.nav.codeEditor') },
    { key: '/chat', icon: <MessageOutlined />, label: t('app.nav.teamChat') },
  ];

  const userMenu: MenuProps['items'] = [
    { key: 'profile', label: t('app.userMenu.profile') },
    { key: 'settings', label: t('app.userMenu.settings') },
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
          borderRight: '1px solid #21262d',
          height: '100vh',
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        <div
          onMouseEnter={() => setCollapsed(false)}
          onMouseLeave={() => setCollapsed(true)}
          style={{ height: '100%', display: 'flex', flexDirection: 'column', minHeight: 0 }}
        >
          {/* Logo */}
          <div
            style={{
              height: 48,
              display: 'flex',
              alignItems: 'center',
              justifyContent: collapsed ? 'center' : 'flex-start',
              padding: collapsed ? 0 : '0 16px',
              borderBottom: '1px solid #21262d',
              cursor: 'pointer',
              flexShrink: 0,
            }}
            onClick={() => navigate('/dashboard')}
          >
            <img src="/logo-orbit-compact.svg" width={28} height={28} alt="Perseus" />
            {!collapsed && (
              <span style={{ marginLeft: 12, fontSize: 16, fontWeight: 600, color: '#e6edf3' }}>
                Perseus
              </span>
            )}
          </div>

          {/* Main Nav */}
          <Menu
            mode="inline"
            selectedKeys={[selectedKey]}
            items={navItems}
            onClick={({ key }) => navigate(key)}
            style={{ flex: 1, minHeight: 0, borderInlineEnd: 'none', overflow: 'auto' }}
          />

          {/* Bottom section pinned to bottom */}
          <div
            style={{
              flexShrink: 0,
              borderTop: '1px solid #21262d',
              marginTop: 'auto',
            }}
          >
            {/* Quick actions */}
            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: collapsed ? 'center' : 'stretch',
                padding: collapsed ? '4px 0' : '4px 0',
              }}
            >
              <Tooltip title={t('app.nav.theme')} placement="right">
                <Button
                  type="text"
                  icon={<BgColorsOutlined />}
                  style={{
                    color: '#8b949e',
                    width: collapsed ? 48 : '100%',
                    height: 40,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: collapsed ? 'center' : 'flex-start',
                    padding: collapsed ? 0 : '0 24px',
                  }}
                >
                  {!collapsed && <span style={{ marginLeft: 10 }}>{t('app.nav.theme')}</span>}
                </Button>
              </Tooltip>
              <Tooltip title={t('app.nav.settings')} placement="right">
                <Button
                  type="text"
                  icon={<SettingOutlined />}
                  style={{
                    color: '#8b949e',
                    width: collapsed ? 48 : '100%',
                    height: 40,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: collapsed ? 'center' : 'flex-start',
                    padding: collapsed ? 0 : '0 24px',
                  }}
                  onClick={() => navigate('/settings')}
                >
                  {!collapsed && <span style={{ marginLeft: 10 }}>{t('app.nav.settings')}</span>}
                </Button>
              </Tooltip>
              <Tooltip title={t('common.language')} placement="right">
                <Button
                  type="text"
                  icon={<TranslationOutlined />}
                  style={{
                    color: '#8b949e',
                    width: collapsed ? 48 : '100%',
                    height: 40,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: collapsed ? 'center' : 'flex-start',
                    padding: collapsed ? 0 : '0 24px',
                  }}
                  onClick={toggleLanguage}
                >
                  {!collapsed && <span style={{ marginLeft: 10 }}>{i18n.language.startsWith('zh') ? t('common.english') : t('common.chinese')}</span>}
                </Button>
              </Tooltip>
            </div>

            {/* User avatar */}
            <div
              style={{
                padding: collapsed ? '8px 0' : '8px 16px',
                textAlign: collapsed ? 'center' : 'left',
                borderTop: '1px solid #21262d',
              }}
            >
              <Dropdown menu={{ items: userMenu }} placement="topRight" trigger={['click']}>
                <Space
                  style={{
                    cursor: 'pointer',
                    width: '100%',
                    justifyContent: collapsed ? 'center' : 'flex-start',
                  }}
                >
                  <Avatar
                    size={32}
                    icon={<UserOutlined />}
                    style={{ backgroundColor: '#1f6feb', flexShrink: 0 }}
                    src={user?.avatar_url}
                  />
                  {!collapsed && (
                    <span style={{ color: '#e6edf3', fontSize: 14 }}>
                      {user?.username || 'User'}
                    </span>
                  )}
                </Space>
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
            justifyContent: 'space-between',
            padding: '0 20px',
            borderBottom: '1px solid #21262d',
            height: 48,
          }}
        >
          <Breadcrumb
            items={[
              { title: 'Perseus' },
              { title: location.pathname.split('/').filter(Boolean).join(' / ') || t('app.nav.dashboard') },
            ]}
          />
          <Space size={12}>
            <Input
              prefix={<SearchOutlined style={{ color: '#6e7681' }} />}
              placeholder={t('app.topBar.searchPlaceholder')}
              style={{ width: 240, backgroundColor: '#0d1117', borderColor: '#30363d' }}
              size="small"
            />
            <Badge count={3} size="small">
              <BellOutlined style={{ color: '#8b949e', fontSize: 16, cursor: 'pointer' }} />
            </Badge>
            <Button type="primary" size="small" icon={<PlusOutlined />}>
              {t('app.topBar.new')}
            </Button>
          </Space>
        </Header>
        <Content style={{ padding: 24, overflow: 'auto' }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
