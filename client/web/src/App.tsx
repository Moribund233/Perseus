import { useEffect } from 'react';
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
import PullRequestsPage from './routes/pull-requests';
import EditorPage from './routes/editor';
import ChatPage from './routes/chat';
import SettingsPage from './routes/settings';

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
              <PageTransition><LandingPage /></PageTransition>
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
        <Route path="/pulls" element={<PageTransition><PullRequestsPage /></PageTransition>} />
        <Route path="/editor" element={<PageTransition><EditorPage /></PageTransition>} />
        <Route path="/editor/:owner/:repo" element={<PageTransition><EditorPage /></PageTransition>} />
        <Route path="/chat" element={<PageTransition><ChatPage /></PageTransition>} />
        <Route path="/settings" element={<PageTransition><SettingsPage /></PageTransition>} />
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
