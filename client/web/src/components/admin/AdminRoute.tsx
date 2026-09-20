import { useCallback, useEffect, useState } from 'react';
import { Spin } from 'antd';
import { useAuthStore } from '../../stores/auth';
import { adminApi } from '../../api/admin';
import { classifyGateError, type GatePhase } from './gate';
import AdminGate from './AdminGate';
import AdminDenied from './AdminDenied';
import './admin.css';

/**
 * 控制台独立守卫（顶层路由，不经 ProtectedRoute/AppLayout）。
 *
 * 进入前先做来源预检 GET /api/app/status：
 * - 403 → 网关来源白名单拒绝，展示「未授权」拒绝页（不落到 landing）；
 * - 401 → 来源已放行，展示独立登录门禁；
 * - 放行后：已登录且 is_admin → 控制台；已登录非管理员 → 拒绝页。
 *
 * 后端仍有网关白名单 + is_admin 双重校验，此处仅为前端体验层。
 */
export default function AdminRoute({ children }: { children: React.ReactNode }) {
  const { user, isAuthenticated, isLoading } = useAuthStore();
  const [phase, setPhase] = useState<GatePhase | 'checking'>('checking');
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (isLoading) return;
    let cancelled = false;
    adminApi
      .getStatus()
      .then(() => {
        if (!cancelled) setPhase('allowed');
      })
      .catch((err: unknown) => {
        if (!cancelled) setPhase(classifyGateError(err));
      });
    return () => {
      cancelled = true;
    };
  }, [isLoading, attempt]);

  const retry = useCallback(() => {
    setPhase('checking');
    setAttempt((n) => n + 1);
  }, []);

  if (isLoading || phase === 'checking') {
    return (
      <div className="admin-gate" aria-busy="true">
        <Spin size="large" />
      </div>
    );
  }
  if (phase === 'source-denied') return <AdminDenied kind="source" onRetry={retry} />;
  if (phase === 'error') return <AdminDenied kind="network" onRetry={retry} />;
  if (!isAuthenticated) return <AdminGate />;
  if (!user?.is_admin) return <AdminDenied kind="not-admin" />;
  return <>{children}</>;
}
