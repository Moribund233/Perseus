import { useAuthStore } from '../stores/auth';

const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000';

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

// 并发的多个 401 共享同一次刷新, 避免重复请求 / 竞态导致的多重登出
let refreshPromise: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  const { refreshToken, logout } = useAuthStore.getState();
  if (!refreshToken) return null;

  if (!refreshPromise) {
    refreshPromise = (async () => {
      try {
        const res = await fetch(`${BASE_URL}/api/v1/auth/refresh`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });
        if (!res.ok) {
          logout();
          return null;
        }
        const data = await res.json();
        localStorage.setItem('access_token', data.access_token);
        localStorage.setItem('refresh_token', data.refresh_token);
        useAuthStore.setState({
          accessToken: data.access_token,
          refreshToken: data.refresh_token,
        });
        return data.access_token as string;
      } catch {
        return null;
      } finally {
        refreshPromise = null;
      }
    })();
  }
  return refreshPromise;
}

async function execute<T>(path: string, options: RequestInit, token: string | null): Promise<T> {
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };

  // FormData 由浏览器自动设置 multipart boundary, 不能手动指定 Content-Type
  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    const body = await res.text();
    let message: string;
    try {
      const json = JSON.parse(body);
      message = json.detail || json.error?.message || res.statusText;
    } catch {
      message = body || res.statusText;
    }
    throw new ApiError(res.status, message);
  }

  if (res.status === 204) {
    return undefined as T;
  }

  return res.json();
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = useAuthStore.getState().accessToken;

  try {
    return await execute<T>(path, options, token);
  } catch (err) {
    // access token 过期时自动刷新并重试一次;
    // 认证端点自身的 401 (密码错误等) 不应触发刷新
    const isAuthPath = path.startsWith('/api/v1/auth/');
    if (err instanceof ApiError && err.status === 401 && !isAuthPath) {
      const newToken = await refreshAccessToken();
      if (newToken) {
        return execute<T>(path, options, newToken);
      }
    }
    throw err;
  }
}
