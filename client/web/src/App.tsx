import { lazy, Suspense, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider, App as AntApp, Spin } from 'antd';
import { perseusTheme } from './styles/theme';
import { useAuthStore } from './stores/auth';
import { PageTransition } from './components/PageTransition';
import AppLayout from './components/layout/AppLayout';
import LandingLayout from './components/layout/LandingLayout';
import LandingPage from './routes/landing';
import DashboardPage from './routes/dashboard';
import RepositoriesPage from './routes/repositories';
import IssuesPage from './routes/issues';
import IssueDetailPage from './routes/issues/[issueNumber]';
import PullRequestsPage from './routes/pull-requests';
import PullRequestDetailPage from './routes/pull-requests/[prNumber]';
import EditorPage from './routes/editor';
import ChatPage from './routes/chat';
import SettingsPage from './routes/settings';
import GlobalSearchPage from './routes/search';
import AdminRoute from './components/admin/AdminRoute';
import AdminConsolePage from './routes/admin';

// Admin 控制台各分节按需加载：避免图表库（@ant-design/charts）进入主包，
// 仅访问 /admin 时才下载对应 chunk。
const OverviewSection = lazy(() => import('./routes/admin/sections/OverviewSection'));
const ComponentsSection = lazy(() => import('./routes/admin/sections/ComponentsSection'));
const ConfigSection = lazy(() => import('./routes/admin/sections/ConfigSection'));
const LogsSection = lazy(() => import('./routes/admin/sections/LogsSection'));
const OperationsSection = lazy(() => import('./routes/admin/sections/OperationsSection'));
const DebugSection = lazy(() => import('./routes/admin/sections/DebugSection'));
const RedisSection = lazy(() => import('./routes/admin/sections/RedisSection'));

function AdminFallback() {
  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%', padding: 48 }}>
      <Spin size="large" />
    </div>
  );
}

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuthStore();
  if (isLoading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <Spin size="large" />
      </div>
    );
  }
  if (!isAuthenticated) {
    return <Navigate to="/" replace />;
  }
  return <>{children}</>;
}

function PublicRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuthStore();
  if (isLoading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <Spin size="large" />
      </div>
    );
  }
  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }
  return <>{children}</>;
}

function AppRoutes() {
  const initialize = useAuthStore((s) => s.initialize);

  useEffect(() => {
    initialize();
  }, [initialize]);

  return (
    <Routes>
      <Route element={<LandingLayout />}>
        <Route
          path="/"
          element={
            <PublicRoute>
              <PageTransition fill={false}><LandingPage /></PageTransition>
            </PublicRoute>
          }
        />
      </Route>
      <Route
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route path="/dashboard" element={<PageTransition><DashboardPage /></PageTransition>} />
        <Route path="/repositories" element={<PageTransition><RepositoriesPage /></PageTransition>} />
        <Route path="/repositories/:owner/:repo" element={<PageTransition><RepositoriesPage /></PageTransition>} />
        <Route path="/repositories/:owner/:repo/issues" element={<PageTransition><IssuesPage /></PageTransition>} />
        <Route path="/repositories/:owner/:repo/issues/:issueNumber" element={<PageTransition><IssueDetailPage /></PageTransition>} />
        <Route path="/repositories/:owner/:repo/pulls" element={<PageTransition><PullRequestsPage /></PageTransition>} />
        <Route path="/repositories/:owner/:repo/pulls/:prNumber" element={<PageTransition><PullRequestDetailPage /></PageTransition>} />
        <Route path="/pulls" element={<PageTransition><PullRequestsPage /></PageTransition>} />
        <Route path="/editor" element={<PageTransition><EditorPage /></PageTransition>} />
        <Route path="/editor/:owner/:repo" element={<PageTransition><EditorPage /></PageTransition>} />
        <Route path="/chat" element={<PageTransition><ChatPage /></PageTransition>} />
        <Route path="/settings" element={<PageTransition><SettingsPage /></PageTransition>} />
        <Route path="/search" element={<PageTransition><GlobalSearchPage /></PageTransition>} />
      </Route>
      <Route
        path="/admin"
        element={
          <PageTransition fill={false}>
            <AdminRoute>
              <Suspense fallback={<AdminFallback />}>
                <AdminConsolePage />
              </Suspense>
            </AdminRoute>
          </PageTransition>
        }
      >
        <Route index element={<OverviewSection />} />
        <Route path="components" element={<ComponentsSection />} />
        <Route path="config" element={<ConfigSection />} />
        <Route path="logs" element={<LogsSection />} />
        <Route path="operations" element={<OperationsSection />} />
        <Route path="debug" element={<DebugSection />} />
        <Route path="redis" element={<RedisSection />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <ConfigProvider theme={perseusTheme}>
      <AntApp>
        <BrowserRouter>
          <AppRoutes />
        </BrowserRouter>
      </AntApp>
    </ConfigProvider>
  );
}
