import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError, apiRequest } from './client';
import { useAuthStore } from '../stores/auth';

function jsonResponse(body: unknown, init: ResponseInit = {}): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
    ...init,
  });
}

describe('apiRequest 错误映射', () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    vi.stubGlobal('fetch', fetchMock);
    localStorage.clear();
    useAuthStore.setState({ accessToken: null, refreshToken: null, isAuthenticated: false });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    fetchMock.mockReset();
  });

  it('成功时返回解析后的 JSON', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse({ ok: true }));
    await expect(apiRequest('/api/app/status')).resolves.toEqual({ ok: true });
  });

  it('204 返回 undefined', async () => {
    fetchMock.mockResolvedValueOnce(new Response(null, { status: 204 }));
    await expect(apiRequest('/api/app/logs', { method: 'DELETE' })).resolves.toBeUndefined();
  });

  it('detail 字段映射为 ApiError.message', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse({ detail: '需要管理员权限' }, { status: 403 }));
    await expect(apiRequest('/api/app/status')).rejects.toMatchObject({
      status: 403,
      message: '需要管理员权限',
    });
  });

  it('error.message 嵌套结构映射', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse({ error: { message: 'boom' } }, { status: 500 }));
    const err = await apiRequest('/api/app/status').catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect((err as ApiError).status).toBe(500);
    expect((err as ApiError).message).toBe('boom');
  });

  it('非 JSON 响应体作为错误消息', async () => {
    fetchMock.mockResolvedValueOnce(new Response('Service Unavailable', { status: 503 }));
    await expect(apiRequest('/api/app/status')).rejects.toMatchObject({
      status: 503,
      message: 'Service Unavailable',
    });
  });

  it('携带 token 时附加 Authorization 与 JSON Content-Type', async () => {
    useAuthStore.setState({ accessToken: 'abc' });
    fetchMock.mockResolvedValueOnce(jsonResponse({}));
    await apiRequest('/api/app/config', { method: 'POST', body: JSON.stringify({ a: 1 }) });
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    const headers = init.headers as Record<string, string>;
    expect(headers.Authorization).toBe('Bearer abc');
    expect(headers['Content-Type']).toBe('application/json');
  });

  it('FormData 体不手动设置 Content-Type', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse({}));
    await apiRequest('/api/v1/repositories/1/attachments', {
      method: 'POST',
      body: new FormData(),
    });
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    const headers = init.headers as Record<string, string>;
    expect(headers['Content-Type']).toBeUndefined();
  });
});

describe('apiRequest 401 刷新重试', () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    vi.stubGlobal('fetch', fetchMock);
    localStorage.clear();
    useAuthStore.setState({ accessToken: 'old', refreshToken: null, isAuthenticated: false });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    fetchMock.mockReset();
  });

  it('认证端点自身 401 不触发刷新', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse({ detail: '凭据无效' }, { status: 401 }));
    await expect(
      apiRequest('/api/v1/auth/login', { method: 'POST', body: '{}' }),
    ).rejects.toMatchObject({ status: 401 });
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('无 refreshToken 时直接抛出 401', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse({ detail: 'expired' }, { status: 401 }));
    await expect(apiRequest('/api/app/status')).rejects.toMatchObject({ status: 401 });
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('刷新成功后带新 token 重试一次', async () => {
    useAuthStore.setState({ refreshToken: 'refresh-1' });
    fetchMock
      .mockResolvedValueOnce(jsonResponse({ detail: 'expired' }, { status: 401 }))
      .mockResolvedValueOnce(jsonResponse({ access_token: 'new-token', refresh_token: 'refresh-2' }))
      .mockResolvedValueOnce(jsonResponse({ status: 'ok' }));

    await expect(apiRequest('/api/app/status')).resolves.toEqual({ status: 'ok' });

    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(fetchMock.mock.calls[1][0]).toContain('/api/v1/auth/refresh');
    const [, retryInit] = fetchMock.mock.calls[2] as [string, RequestInit];
    expect((retryInit.headers as Record<string, string>).Authorization).toBe('Bearer new-token');
    expect(localStorage.getItem('access_token')).toBe('new-token');
    expect(useAuthStore.getState().refreshToken).toBe('refresh-2');
  });

  it('刷新失败（401）时登出并抛出原错误', async () => {
    useAuthStore.setState({ refreshToken: 'refresh-1', isAuthenticated: true });
    fetchMock
      .mockResolvedValueOnce(jsonResponse({ detail: 'expired' }, { status: 401 }))
      .mockResolvedValueOnce(new Response(null, { status: 401 }));

    await expect(apiRequest('/api/app/status')).rejects.toMatchObject({ status: 401 });
    expect(useAuthStore.getState().isAuthenticated).toBe(false);
  });
});
