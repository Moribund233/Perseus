import { useEffect, useState } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { Layout, Input, Button, Avatar, Dropdown, Space, Tooltip, Popover, Empty, Modal, Form, Switch, message as antdMessage } from 'antd';
import type { MenuProps } from 'antd';
import {
  DashboardOutlined,
  CodeOutlined,
  PullRequestOutlined,
  EditOutlined,
  MessageOutlined,
  SettingOutlined,
  BellOutlined,
  PlusOutlined,
  UserOutlined,
  TranslationOutlined,
  DownOutlined,
  HistoryOutlined,
  BookOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useAuthStore } from '../../stores/auth';
import { useNotificationsStore } from '../../stores/notifications';
import { useEditorStateStore } from '../../stores/editorState';
import { notificationSocket } from '../../api/notificationSocket';
import { repositoriesApi, type Repository } from '../../api/repositories';
import { chatApi, dmApi, type DMSession } from '../../api/chat';
import type { Notification } from '../../api/notifications';
import Logo from '../brand/Logo';
import GlobalSearch from './GlobalSearch';
import { getRecentRepos, recordRecentRepo, type RecentRepo } from './recentRepos';

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

/** 顶栏上下文/最近项目下拉的触发器样式 */
const pillStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 6,
  height: 32,
  padding: '0 10px',
  background: '#0d1117',
  border: `1px solid #30363d`,
  borderRadius: 6,
  color: textPrimary,
  fontSize: 13,
  cursor: 'pointer',
  flexShrink: 0,
  whiteSpace: 'nowrap',
  transition: 'border-color 0.15s, background 0.15s',
};

function formatNotificationTime(iso: string, lang: string): string {
  const date = new Date(iso);
  const diffMs = Date.now() - date.getTime();
  const minutes = Math.floor(diffMs / 60000);
  if (minutes < 1) return lang.startsWith('zh') ? '刚刚' : 'just now';
  if (minutes < 60) return lang.startsWith('zh') ? `${minutes} 分钟前` : `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return lang.startsWith('zh') ? `${hours} 小时前` : `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 30) return lang.startsWith('zh') ? `${days} 天前` : `${days}d ago`;
  return date.toLocaleDateString(lang.startsWith('zh') ? 'zh-CN' : 'en-US');
}

interface NavItemDef {
  key: string;
  path: string;
  icon: React.ReactNode;
  label: string;
  badge?: number;
}

/** 按当前页面类型构造切换仓库后的目标路径：编辑器 / PR / Issue 保持同类页面。
 *  PR、Issue 详情页因编号与仓库绑定，切换到列表页。 */
function projectSwitchTarget(pathname: string, repoPath: string): string {
  if (pathname === '/editor' || pathname.startsWith('/editor/')) {
    return `/editor/${repoPath}`;
  }
  const section = pathname.match(/^\/repositories\/[^/]+\/[^/]+\/(issues|pulls)(?:\/|$)/);
  if (section) return `/repositories/${repoPath}/${section[1]}`;
  return `/repositories/${repoPath}`;
}

export default function AppLayout() {
  const [collapsed, setCollapsed] = useState(true);
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuthStore();
  const { t, i18n } = useTranslation();

  const notifications = useNotificationsStore((s) => s.notifications);
  const unreadCount = useNotificationsStore((s) => s.unreadCount);
  const fetchNotifications = useNotificationsStore((s) => s.fetchNotifications);
  const fetchUnreadCount = useNotificationsStore((s) => s.fetchUnreadCount);
  const markAsRead = useNotificationsStore((s) => s.markAsRead);
  const markAllAsRead = useNotificationsStore((s) => s.markAllAsRead);
  const [notifOpen, setNotifOpen] = useState(false);

  // 登录后拉取未读数并每 60s 轮询（WS 实时推送为主，轮询作对账兜底）
  useEffect(() => {
    if (!user) return;
    fetchUnreadCount();
    const timer = setInterval(() => fetchUnreadCount(), 60_000);
    return () => clearInterval(timer);
  }, [user, fetchUnreadCount]);

  // 团队聊天未读徽标：频道未读 + 私聊未读 聚合（恢复 P3 侧边栏未读徽标）
  const [chatUnread, setChatUnread] = useState(0);
  useEffect(() => {
    if (!user) return;
    const refreshChatUnread = () => {
      Promise.all([chatApi.getUnreadCounts(), dmApi.listDms()])
        .then(([channels, dms]) => {
          const channelsSum = channels.reduce((a, b) => a + b.unread_count, 0);
          const dmsSum = (dms as DMSession[]).reduce((a, b) => a + (b.unread_count || 0), 0);
          setChatUnread(channelsSum + dmsSum);
        })
        .catch(() => {});
    };
    refreshChatUnread();
    const timer = setInterval(refreshChatUnread, 60_000);
    return () => clearInterval(timer);
  }, [user, location.pathname]);

  // F-205: 订阅 /ws/notifications 实时推送
  useEffect(() => {
    if (!user) return;
    notificationSocket.setHandlers({
      onNotification: (payload) => {
        useNotificationsStore.getState().addLive(payload.data, payload.unread_count);
      },
    });
    notificationSocket.start();
    return () => notificationSocket.stop();
  }, [user]);

  const openNotificationPanel = (open: boolean) => {
    setNotifOpen(open);
    if (open) {
      fetchNotifications();
      fetchUnreadCount();
    }
  };

  const handleNotificationClick = async (n: Notification) => {
    setNotifOpen(false);
    if (!n.is_read) {
      try {
        await markAsRead(n.id);
      } catch {
        // 标记已读失败不阻塞跳转
      }
    }
    let repoPath: string | null = null;
    if (n.repository_id) {
      try {
        const repo = await repositoriesApi.get(n.repository_id);
        repoPath = repo.path;
      } catch {
        // 忽略解析失败, 仅打开通知面板所在的页面
      }
    }
    const type = (n.target_type || '').toLowerCase();
    if (!repoPath) return;
    if (type.includes('pr') || type.includes('pull')) {
      navigate(`/repositories/${repoPath}/pulls`);
    } else if (type.includes('issue')) {
      navigate(`/repositories/${repoPath}/issues`);
    } else {
      navigate(`/repositories/${repoPath}`);
    }
  };

  // 顶栏 New 按钮：新建仓库
  const [createRepoOpen, setCreateRepoOpen] = useState(false);
  const [creatingRepo, setCreatingRepo] = useState(false);
  const [repoForm] = Form.useForm();

  const handleCreateRepo = async () => {
    try {
      const values = await repoForm.validateFields();
      setCreatingRepo(true);
      const repo: Repository = await repositoriesApi.create({
        name: (values.name as string).trim(),
        description: (values.description as string | undefined)?.trim() || undefined,
        is_public: values.isPublic ?? true,
      });
      antdMessage.success(t('app.topBar.repoCreated', { name: repo.name }));
      setCreateRepoOpen(false);
      repoForm.resetFields();
      navigate(`/repositories/${repo.path}`);
    } catch (err) {
      if (err && typeof err === 'object' && 'errorFields' in err) return; // 表单校验错误
      antdMessage.error((err as Error).message || t('app.topBar.repoCreateFailed'));
    } finally {
      setCreatingRepo(false);
    }
  };

  const handleMarkAllRead = async () => {
    await markAllAsRead();
    await fetchNotifications();
  };

  const navItems: NavItemDef[] = [
    { key: 'dashboard', path: '/dashboard', icon: <DashboardOutlined />, label: t('app.nav.dashboard') },
    { key: 'repositories', path: '/repositories', icon: <CodeOutlined />, label: t('app.nav.repositories') },
    { key: 'pulls', path: '/pulls', icon: <PullRequestOutlined />, label: t('app.nav.pullRequests') },
    { key: 'editor', path: '/editor', icon: <EditOutlined />, label: t('app.nav.codeEditor') },
    { key: 'chat', path: '/chat', icon: <MessageOutlined />, label: t('app.nav.teamChat'), badge: chatUnread || undefined },
  ];

  const activeKey = navItems.find((item) => location.pathname.startsWith(item.path))?.key || 'dashboard';
  const activeLabel = navItems.find((item) => item.key === activeKey)?.label || t('app.nav.dashboard');

  // 当前仓库上下文（仓库 / PR / 编辑器页）
  const repoMatch = location.pathname.match(/^\/(?:repositories|editor)\/([^/]+)\/([^/]+)/);
  const currentRepo = repoMatch
    ? { owner: repoMatch[1], repo: repoMatch[2], path: `${repoMatch[1]}/${repoMatch[2]}` }
    : null;
  const repoOwner = currentRepo?.owner;
  const repoName = currentRepo?.repo;

  const [recentRepos, setRecentRepos] = useState<RecentRepo[]>([]);

  // 记录最近打开的项目（仅写 localStorage，不在 effect 内 setState）
  useEffect(() => {
    if (repoOwner && repoName) recordRecentRepo(repoOwner, repoName);
  }, [repoOwner, repoName]);

  // 编辑器未保存状态：离开编辑器前提示，避免切换项目时静默丢失编辑
  const editorDirty = useEditorStateStore((s) => s.dirty);
  const editorPending = useEditorStateStore((s) => s.pending);
  const [leaveConfirm, setLeaveConfirm] = useState<{ target: string; label: string } | null>(null);
  const onEditorRoute = location.pathname === '/editor' || location.pathname.startsWith('/editor/');

  const guardedNavigate = (target: string, label: string) => {
    if (target === location.pathname) return;
    if (onEditorRoute && (editorDirty || editorPending)) {
      setLeaveConfirm({ target, label });
      return;
    }
    navigate(target);
  };

  const contextItems: MenuProps['items'] = currentRepo
    ? [
        { key: 'path', label: currentRepo.path, disabled: true },
        { type: 'divider' },
        { key: 'repo-overview', label: t('app.topBar.contextOverview'), icon: <BookOutlined />, onClick: () => guardedNavigate(`/repositories/${currentRepo.path}`, currentRepo.path) },
        { key: 'repo-pulls', label: t('app.nav.pullRequests'), icon: <PullRequestOutlined />, onClick: () => guardedNavigate(`/repositories/${currentRepo.path}/pulls`, currentRepo.path) },
        { key: 'repo-issues', label: t('app.topBar.contextIssues'), icon: <ExclamationCircleOutlined />, onClick: () => guardedNavigate(`/repositories/${currentRepo.path}/issues`, currentRepo.path) },
        { key: 'repo-editor', label: t('app.nav.codeEditor'), icon: <EditOutlined />, onClick: () => guardedNavigate(`/editor/${currentRepo.path}`, currentRepo.path) },
      ]
    : navItems.map((item) => ({ key: item.key, label: item.label, icon: item.icon, onClick: () => guardedNavigate(item.path, item.label) }));

  const recentItems: MenuProps['items'] = recentRepos.length
    ? recentRepos.map((r) => ({
        key: r.path,
        label: (
          <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span>{r.path}</span>
            {r.path === currentRepo?.path && <span style={{ color: blueLight, fontSize: 11 }}>•</span>}
          </span>
        ),
        // 保持当前页面类型（仓库概览 / PR / Issue / 编辑器），不总是回到仓库详情页
        onClick: () => guardedNavigate(projectSwitchTarget(location.pathname, r.path), r.path),
      }))
    : [{ key: 'empty', label: t('app.topBar.recentEmpty'), disabled: true }];

  const pillHover = (e: React.MouseEvent<HTMLButtonElement>, on: boolean) => {
    e.currentTarget.style.borderColor = on ? blueLight : '#30363d';
    e.currentTarget.style.background = on ? hoverBg : '#0d1117';
  };

  const userMenu: MenuProps['items'] = [
    { key: 'profile', label: t('app.userMenu.profile'), onClick: () => navigate('/settings') },
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
          {/* Logo / 品牌 */}
          <div
            onClick={() => setCollapsed(!collapsed)}
            title="Perseus"
            style={{
              width: '100%',
              height: 40,
              marginBottom: 20,
              flexShrink: 0,
              display: 'flex',
              alignItems: 'center',
              justifyContent: collapsed ? 'center' : 'flex-start',
              gap: 10,
              padding: collapsed ? 0 : '0 20px',
              cursor: 'pointer',
              color: textPrimary,
            }}
          >
            <span style={{ width: 32, height: 32, flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Logo size="100%" />
            </span>
            {!collapsed && (
              <span style={{ fontSize: 16, fontWeight: 700, letterSpacing: '0.02em', whiteSpace: 'nowrap' }}>
                Perseus
              </span>
            )}
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
                  onClick={() => guardedNavigate(item.path, item.label)}
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

            {/* User */}
            <div
              style={{
                borderTop: `1px solid ${borderColor}`,
                marginTop: 4,
                paddingTop: 8,
              }}
            >
              <Dropdown menu={{ items: userMenu }} placement="topRight" trigger={['click']}>
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: collapsed ? 'center' : 'flex-start',
                    gap: 10,
                    padding: collapsed ? '4px 0' : '6px 12px',
                    borderRadius: 8,
                    cursor: 'pointer',
                    overflow: 'hidden',
                    transition: 'background 0.2s',
                  }}
                  onMouseEnter={(e) => { e.currentTarget.style.background = hoverBg; }}
                  onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
                >
                  <Avatar
                    size={32}
                    icon={<UserOutlined />}
                    style={{
                      background: `linear-gradient(135deg, ${bluePrimary}, #bc8cff)`,
                      flexShrink: 0,
                    }}
                    src={user?.avatar_url}
                  >
                    {user?.username?.slice(0, 2).toUpperCase()}
                  </Avatar>
                  {!collapsed && (
                    <div style={{ minWidth: 0, lineHeight: 1.25 }}>
                      <div style={{ fontSize: 13, fontWeight: 600, color: textPrimary, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {user?.username}
                      </div>
                      <div style={{ fontSize: 11, color: textSecondary, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {user?.email}
                      </div>
                    </div>
                  )}
                </div>
              </Dropdown>
            </div>
          </div>
        </div>
      </Sider>

      <Layout style={{ minWidth: 0, minHeight: 0, overflow: 'hidden' }}>
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
          {/* Search */}
          <GlobalSearch />

          {/* 上下文下拉（原面包屑） */}
          <Dropdown menu={{ items: contextItems }} trigger={['click']} placement="bottomLeft">
            <button
              type="button"
              style={pillStyle}
              onMouseEnter={(e) => pillHover(e, true)}
              onMouseLeave={(e) => pillHover(e, false)}
            >
              <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', width: 16, height: 16, fontSize: 14, color: textSecondary }}>
                {currentRepo ? <BookOutlined /> : navItems.find((i) => i.key === activeKey)?.icon}
              </span>
              <span style={{ maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {currentRepo ? currentRepo.path : activeLabel}
              </span>
              <DownOutlined style={{ fontSize: 10, color: textSecondary }} />
            </button>
          </Dropdown>

          {/* 最近项目下拉（仅仓库 / PR / 编辑器页） */}
          {currentRepo && (
            <Dropdown
              menu={{ items: recentItems }}
              trigger={['click']}
              placement="bottomLeft"
              onOpenChange={(open) => { if (open) setRecentRepos(getRecentRepos()); }}
            >
              <button
                type="button"
                style={pillStyle}
                title={t('app.topBar.recentProjects')}
                onMouseEnter={(e) => pillHover(e, true)}
                onMouseLeave={(e) => pillHover(e, false)}
              >
                <HistoryOutlined style={{ fontSize: 14, color: textSecondary }} />
                <DownOutlined style={{ fontSize: 10, color: textSecondary }} />
              </button>
            </Dropdown>
          )}

          {/* Actions */}
          <Space size={8} style={{ marginLeft: 'auto' }}>
            <Popover
              placement="bottomRight"
              trigger="click"
              open={notifOpen}
              onOpenChange={openNotificationPanel}
              styles={{ content: { padding: 0, width: 360 } }}
              content={
                <div style={{ display: 'flex', flexDirection: 'column', maxHeight: 420 }}>
                  <div
                    style={{
                      padding: '10px 14px',
                      borderBottom: `1px solid ${borderColor}`,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      flexShrink: 0,
                    }}
                  >
                    <span style={{ fontSize: 13, fontWeight: 600, color: textPrimary }}>
                      {t('app.notifications.title')}
                      {unreadCount > 0 && (
                        <span style={{ color: textSecondary, fontWeight: 400, marginLeft: 8, fontSize: 12 }}>
                          {t('app.notifications.unreadOnly', { count: unreadCount })}
                        </span>
                      )}
                    </span>
                    <a
                      onClick={handleMarkAllRead}
                      style={{ fontSize: 12, color: unreadCount > 0 ? blueLight : '#6e7681', cursor: unreadCount > 0 ? 'pointer' : 'default' }}
                    >
                      {t('app.notifications.markAllAsRead')}
                    </a>
                  </div>
                  <div style={{ overflow: 'auto', flex: 1, minHeight: 0 }}>
                    {notifications.length === 0 ? (
                      <Empty
                        description={t('app.notifications.empty')}
                        image={Empty.PRESENTED_IMAGE_SIMPLE}
                        style={{ margin: '32px 0' }}
                      />
                    ) : (
                      notifications.map((n) => (
                        <div
                          key={n.id}
                          onClick={() => handleNotificationClick(n)}
                          style={{
                            padding: '10px 14px',
                            borderBottom: `1px solid ${borderColor}`,
                            cursor: 'pointer',
                            display: 'flex',
                            gap: 8,
                            alignItems: 'flex-start',
                          }}
                          onMouseEnter={(e) => { e.currentTarget.style.background = hoverBg; }}
                          onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
                        >
                          <span
                            style={{
                              width: 7,
                              height: 7,
                              borderRadius: '50%',
                              marginTop: 6,
                              flexShrink: 0,
                              background: n.is_read ? 'transparent' : blueLight,
                              border: n.is_read ? `1.5px solid ${borderColor}` : 'none',
                            }}
                          />
                          <div style={{ flex: 1, minWidth: 0 }}>
                            <div style={{ fontSize: 13, color: n.is_read ? textSecondary : textPrimary, fontWeight: n.is_read ? 400 : 600 }}>
                              {n.title}
                            </div>
                            {n.message && (
                              <div style={{ fontSize: 12, color: textSecondary, marginTop: 2, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                {n.message}
                              </div>
                            )}
                            <div style={{ fontSize: 11, color: '#6e7681', marginTop: 4 }}>
                              {formatNotificationTime(n.created_at, i18n.language)}
                            </div>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              }
            >
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
                {unreadCount > 0 && (
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
                )}
              </button>
            </Popover>

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
              onClick={() => setCreateRepoOpen(true)}
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
        <Content style={{ padding: 0, overflow: 'hidden', minHeight: 0 }}>
          <Outlet />
        </Content>

        <Modal
          title={t('app.topBar.newRepoTitle')}
          open={createRepoOpen}
          onCancel={() => { setCreateRepoOpen(false); repoForm.resetFields(); }}
          onOk={handleCreateRepo}
          okText={t('app.topBar.repoCreate')}
          confirmLoading={creatingRepo}
          okButtonProps={{ style: { background: bluePrimary } }}
        >
          <Form form={repoForm} layout="vertical">
            <Form.Item
              name="name"
              label={t('app.topBar.repoName')}
              rules={[
                { required: true, message: t('app.topBar.repoNameRequired') },
                { pattern: /^[A-Za-z0-9._-]+$/, message: t('app.topBar.repoNamePattern') },
              ]}
            >
              <Input placeholder="my-project" />
            </Form.Item>
            <Form.Item name="description" label={t('app.topBar.repoDescription')}>
              <Input.TextArea rows={2} placeholder={t('app.topBar.repoDescriptionPlaceholder')} />
            </Form.Item>
            <Form.Item name="isPublic" label={t('app.topBar.repoVisibility')} initialValue={true} valuePropName="checked">
              <Switch checkedChildren="Public" unCheckedChildren="Private" />
            </Form.Item>
          </Form>
        </Modal>

        <Modal
          title={t('app.topBar.unsavedSwitchTitle')}
          open={!!leaveConfirm}
          onCancel={() => setLeaveConfirm(null)}
          footer={[
            <Button key="stay" onClick={() => setLeaveConfirm(null)}>
              {t('app.topBar.unsavedSwitchStay')}
            </Button>,
            <Button
              key="leave"
              danger
              type="primary"
              onClick={() => {
                const target = leaveConfirm?.target;
                setLeaveConfirm(null);
                if (target) navigate(target);
              }}
            >
              {t('app.topBar.unsavedSwitchDiscard')}
            </Button>,
          ]}
        >
          <div style={{ color: textSecondary, fontSize: 13 }}>
            {editorDirty
              ? t('app.topBar.unsavedSwitchMessage', { path: leaveConfirm?.label ?? '' })
              : t('app.topBar.unsavedSwitchPending')}
          </div>
        </Modal>
      </Layout>
    </Layout>
  );
}
