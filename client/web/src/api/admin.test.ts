import { beforeEach, describe, expect, it, vi } from 'vitest';
import { apiRequest } from './client';
import { adminApi, configApi, debugApi, logsApi, operationsApi } from './admin';

vi.mock('./client', () => ({ apiRequest: vi.fn() }));

const mockedRequest = vi.mocked(apiRequest);

describe('api/admin 请求构造', () => {
  beforeEach(() => {
    mockedRequest.mockReset();
    mockedRequest.mockImplementation(() => Promise.resolve({} as never));
  });

  it('adminApi 状态与组件路径', async () => {
    await adminApi.getStatus();
    await adminApi.getComponents();
    expect(mockedRequest).toHaveBeenNthCalledWith(1, '/api/app/status');
    expect(mockedRequest).toHaveBeenNthCalledWith(2, '/api/app/components');
  });

  it('adminApi.setDebugMode 为 POST 且携带 enabled', async () => {
    await adminApi.setDebugMode(true);
    expect(mockedRequest).toHaveBeenCalledWith('/api/app/debug', {
      method: 'POST',
      body: JSON.stringify({ enabled: true }),
    });
  });

  it('logsApi.getContent 组装全部查询参数', async () => {
    await logsApi.getContent({
      date: '2026-09-20',
      log_name: 'error',
      lines: 500,
      level: 'ERROR',
    });
    expect(mockedRequest).toHaveBeenCalledWith(
      '/api/app/logs/content?date=2026-09-20&log_name=error&lines=500&level=ERROR',
    );
  });

  it('logsApi.getContent 省略空参数', async () => {
    await logsApi.getContent({});
    expect(mockedRequest).toHaveBeenCalledWith('/api/app/logs/content');
  });

  it('logsApi.cleanup 携带 keep_days 且为 POST', async () => {
    await logsApi.cleanup(7);
    expect(mockedRequest).toHaveBeenCalledWith('/api/app/logs/cleanup?keep_days=7', {
      method: 'POST',
    });
  });

  it('configApi.getConfig 编码 section', async () => {
    await configApi.getConfig('server cors');
    expect(mockedRequest).toHaveBeenCalledWith('/api/app/config?section=server%20cors');
  });

  it('configApi.getConfig 无 section 时无查询串', async () => {
    await configApi.getConfig();
    expect(mockedRequest).toHaveBeenCalledWith('/api/app/config');
  });

  it('operationsApi 重启/停止均为 POST', async () => {
    await operationsApi.restart();
    await operationsApi.shutdown();
    expect(mockedRequest).toHaveBeenNthCalledWith(1, '/api/app/restart', { method: 'POST' });
    expect(mockedRequest).toHaveBeenNthCalledWith(2, '/api/app/shutdown', { method: 'POST' });
  });

  it('debugApi 路径与方法', async () => {
    await debugApi.getStatus();
    await debugApi.initDb();
    await debugApi.initConf();
    expect(mockedRequest).toHaveBeenNthCalledWith(1, '/api/v1/debug/status');
    expect(mockedRequest).toHaveBeenNthCalledWith(2, '/api/v1/debug/initdb', { method: 'POST' });
    expect(mockedRequest).toHaveBeenNthCalledWith(3, '/api/v1/debug/initconf', { method: 'POST' });
  });
});
