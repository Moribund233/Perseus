import { useGatewayStore } from '../stores/gateway';

export class ApiError extends Error {
  status: number;
  offline?: boolean;
  cached?: unknown;
  code?: string;
  constructor(status: number, message: string, opts?: { offline?: boolean; cached?: unknown; code?: string }) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.offline = opts?.offline;
    this.cached = opts?.cached;
    this.code = opts?.code;
  }
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
  _serverId?: string,
): Promise<T> {
  const { config } = useGatewayStore.getState();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'X-Gateway-Token': config?.gatewayToken ?? '',
    ...(options.headers as Record<string, string>),
  };
  const res = await fetch(`${config?.baseURL ?? ''}${path}`, { ...options, headers });

  if (!res.ok) {
    let message = res.statusText;
    let code: string | undefined;
    let offline: boolean | undefined;
    let cached: unknown;
    try {
      const json = await res.json();
      message = json.error?.message || json.detail || message;
      code = json.error?.code;
      offline = json.offline;
      cached = json.cached;
    } catch {
      /* keep statusText */
    }
    throw new ApiError(res.status, message, { offline, cached, code });
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

// proxyRequest 经本地网关代理访问服务器 API，token 在 Go 侧，前端不接触。
export async function proxyRequest<T>(
  serverId: string,
  path: string,
  options: RequestInit = {},
): Promise<T> {
  return apiRequest<T>(`/api/local/proxy/${serverId}${path}`, options);
}
