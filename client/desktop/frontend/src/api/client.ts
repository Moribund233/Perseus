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
  const isForm = typeof FormData !== 'undefined' && options.body instanceof FormData;
  const headers: Record<string, string> = {
    // FormData 交给浏览器生成含 boundary 的 Content-Type
    ...(isForm ? {} : { 'Content-Type': 'application/json' }),
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

// proxyRequestBlob 经网关代理拉取二进制内容（附件下载等场景）。
export async function proxyRequestBlob(serverId: string, path: string): Promise<Blob> {
  const { config } = useGatewayStore.getState();
  const res = await fetch(`${config?.baseURL ?? ''}/api/local/proxy/${serverId}${path}`, {
    headers: { 'X-Gateway-Token': config?.gatewayToken ?? '' },
  });
  if (!res.ok) {
    let message = res.statusText;
    try {
      const json = await res.json();
      message = json.error?.message || json.detail || message;
    } catch {
      /* keep statusText */
    }
    throw new ApiError(res.status, message, { offline: res.status === 503 });
  }
  return res.blob();
}
