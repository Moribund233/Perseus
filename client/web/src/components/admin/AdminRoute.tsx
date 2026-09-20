import { Navigate } from 'react-router-dom';
import { useAuthStore } from '../../stores/auth';

/**
 * 管理员守卫：非管理员重定向回控制台。
 * 后端另有网关来源白名单 + is_admin 鉴权，此处仅为前端体验层防线。
 */
export default function AdminRoute({ children }: { children: React.ReactNode }) {
  const user = useAuthStore((s) => s.user);
  if (!user?.is_admin) {
    return <Navigate to="/dashboard" replace />;
  }
  return <>{children}</>;
}