import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { webhooksApi } from './webhooks';
import { useAuthStore } from '../stores/auth';

function jsonResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  });
}

// 回归保护：后端 /webhooks 返回分页对象 {items,...}；消费方按数组遍历，
// 若未归一化会在仓库设置页触发 "webhooks.map is not a function" 崩溃。
describe('webhooksApi.list 响应归一化', () => {
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

  it('分页对象 {items} 归一化为数组', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse({ items: [{ id: '1' }], total: 1, page: 1, limit: 20 }));
    await expect(webhooksApi.list('repo')).resolves.toEqual([{ id: '1' }]);
  });

  it('裸数组保持不变', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse([{ id: '2' }]));
    await expect(webhooksApi.list('repo')).resolves.toEqual([{ id: '2' }]);
  });
});
