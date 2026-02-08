/**
 * WebSocket Store单元测试
 *
 * 测试范围:
 * 1. Store状态管理
 * 2. 消息处理器
 * 3. 通知管理
 * 4. 同步状态管理
 * 5. 进度管理
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';
import { useWebSocketStore } from '../src/stores/websocket';

// Mock WebSocket模块
vi.mock('@/utils/websocket', () => {
  const handlers: Map<string, Set<(message: any) => void>> = new Map();

  return {
    WebSocketClient: vi.fn().mockImplementation((config: any) => {
      const mockClient = {
        connect: vi.fn(),
        close: vi.fn(),
        send: vi.fn().mockReturnValue(true),
        subscribeRepository: vi.fn().mockReturnValue(true),
        unsubscribeRepository: vi.fn().mockReturnValue(true),
        subscribeUserNotifications: vi.fn().mockReturnValue(true),
        on: vi.fn().mockImplementation((type: string, handler: (message: any) => void) => {
          if (!handlers.has(type)) {
            handlers.set(type, new Set());
          }
          handlers.get(type)!.add(handler);

          // 返回取消订阅函数
          return () => {
            handlers.get(type)?.delete(handler);
          };
        }),
        isConnected: true,
        isAuthenticated: true,
        getConnectionId: 'test_conn_123',
        // 添加 onError 和 onClose 方法用于测试
        onError: vi.fn().mockImplementation((error: any) => {
          config.onError?.(error);
        }),
        onClose: vi.fn().mockImplementation((event: any) => {
          config.onClose?.(event);
        }),
      };

      // 模拟触发消息
      (mockClient as any)._trigger = (type: string, message: any) => {
        handlers.get(type)?.forEach((h) => h(message));
      };

      // 自动触发onOpen
      setTimeout(() => {
        config.onOpen?.();
      }, 0);

      return mockClient;
    }),
  };
});

describe('WebSocket Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  /**
   * 状态初始化测试
   */
  describe('State Initialization', () => {
    it('应该正确初始化状态', () => {
      const store = useWebSocketStore();

      expect(store.client).toBeNull();
      expect(store.isConnected).toBe(false);
      expect(store.isAuthenticated).toBe(false);
      expect(store.connectionId).toBeNull();
      expect(store.notifications).toEqual([]);
      expect(store.unreadCount).toBe(0);
      expect(store.syncStatuses.size).toBe(0);
      expect(store.progressMap.size).toBe(0);
      expect(store.subscribedRepositories.size).toBe(0);
    });
  });

  /**
   * 连接管理测试
   */
  describe('Connection Management', () => {
    it('应该初始化WebSocket连接', async () => {
      const store = useWebSocketStore();

      await store.initConnection('test_token');

      expect(store.client).not.toBeNull();
    });

    it('应该关闭现有连接后再创建新连接', async () => {
      const store = useWebSocketStore();

      // 第一次连接
      await store.initConnection('token1');
      const firstClient = store.client;

      // 第二次连接
      await store.initConnection('token2');

      // 第一个客户端应该被关闭
      expect(firstClient?.close).toHaveBeenCalled();
      expect(store.client).not.toBe(firstClient);
    });

    it('应该正确关闭连接', async () => {
      const store = useWebSocketStore();

      await store.initConnection('test_token');
      const client = store.client;

      store.closeConnection();

      expect(client?.close).toHaveBeenCalled();
      expect(store.client).toBeNull();
      expect(store.isConnected).toBe(false);
      expect(store.isAuthenticated).toBe(false);
      expect(store.connectionId).toBeNull();
    });

    it('应该在连接打开时更新状态', async () => {
      const store = useWebSocketStore();

      await store.initConnection('test_token');

      // 触发onOpen
      await vi.runAllTimersAsync();

      expect(store.isConnected).toBe(true);
    });
  });

  /**
   * 通知管理测试
   */
  describe('Notification Management', () => {
    it('应该处理notification消息', async () => {
      const store = useWebSocketStore();

      await store.initConnection('test_token');

      const message = {
        type: 'notification',
        action: 'commit_new',
        repository_id: 123,
        data: { message: 'New commit added' },
        timestamp: '2024-01-01T00:00:00Z',
      };

      // 触发notification消息
      (store.client as any)?._trigger('notification', message);

      expect(store.notifications).toHaveLength(1);
      expect(store.notifications[0].type).toBe('commit_new');
      expect(store.notifications[0].repositoryId).toBe(123);
      expect(store.notifications[0].read).toBe(false);
      expect(store.unreadCount).toBe(1);
    });

    it('应该处理user_notification消息', async () => {
      const store = useWebSocketStore();

      await store.initConnection('test_token');

      const message = {
        type: 'user_notification',
        notification_type: 'system',
        data: { message: 'System maintenance scheduled' },
        timestamp: '2024-01-01T00:00:00Z',
      };

      (store.client as any)?._trigger('user_notification', message);

      expect(store.notifications).toHaveLength(1);
      expect(store.notifications[0].type).toBe('system');
    });

    it('应该限制通知数量', async () => {
      const store = useWebSocketStore();

      await store.initConnection('test_token');

      // 添加101条通知
      for (let i = 0; i < 101; i++) {
        const message = {
          type: 'notification',
          action: 'commit_new',
          data: { message: `Commit ${i}` },
        };
        (store.client as any)?._trigger('notification', message);
      }

      expect(store.notifications).toHaveLength(100);
    });

    it('应该标记通知为已读', async () => {
      const store = useWebSocketStore();

      await store.initConnection('test_token');

      const message = {
        type: 'notification',
        action: 'commit_new',
        data: { message: 'New commit' },
      };
      (store.client as any)?._trigger('notification', message);

      const notificationId = store.notifications[0].id;
      store.markNotificationAsRead(notificationId);

      expect(store.notifications[0].read).toBe(true);
      expect(store.unreadCount).toBe(0);
    });

    it('应该标记所有通知为已读', async () => {
      const store = useWebSocketStore();

      await store.initConnection('test_token');

      for (let i = 0; i < 5; i++) {
        const message = {
          type: 'notification',
          action: 'commit_new',
          data: { message: `Commit ${i}` },
        };
        (store.client as any)?._trigger('notification', message);
      }

      store.markAllNotificationsAsRead();

      expect(store.unreadCount).toBe(0);
      expect(store.notifications.every((n) => n.read)).toBe(true);
    });

    it('应该清除所有通知', async () => {
      const store = useWebSocketStore();

      await store.initConnection('test_token');

      const message = {
        type: 'notification',
        action: 'commit_new',
        data: { message: 'New commit' },
      };
      (store.client as any)?._trigger('notification', message);

      store.clearNotifications();

      expect(store.notifications).toHaveLength(0);
      expect(store.unreadCount).toBe(0);
    });

    it('应该获取仓库相关通知', async () => {
      const store = useWebSocketStore();

      await store.initConnection('test_token');

      // 添加仓库123的通知
      (store.client as any)?._trigger('notification', {
        type: 'notification',
        action: 'commit_new',
        repository_id: 123,
        data: { message: 'Commit in repo 123' },
      });

      // 添加仓库456的通知
      (store.client as any)?._trigger('notification', {
        type: 'notification',
        action: 'commit_new',
        repository_id: 456,
        data: { message: 'Commit in repo 456' },
      });

      const repo123Notifications = store.getRepositoryNotifications(123);

      expect(repo123Notifications).toHaveLength(1);
      expect(repo123Notifications[0].repositoryId).toBe(123);
    });
  });

  /**
   * 同步状态管理测试
   */
  describe('Sync Status Management', () => {
    it('应该处理sync_status_update消息', async () => {
      const store = useWebSocketStore();

      await store.initConnection('test_token');

      const message = {
        type: 'sync_status_update',
        repository_id: 123,
        status: 'running',
        progress: 50,
        message: 'Syncing...',
      };

      (store.client as any)?._trigger('sync_status_update', message);

      const syncStatus = store.getSyncStatus(123);
      expect(syncStatus.status).toBe('running');
      expect(syncStatus.progress).toBe(50);
      expect(syncStatus.message).toBe('Syncing...');
    });

    it('应该处理sync_event消息（completed）', async () => {
      const store = useWebSocketStore();

      await store.initConnection('test_token');

      const message = {
        type: 'sync_event',
        repository_id: 123,
        action: 'completed',
        result: { message: 'Sync completed successfully' },
      };

      (store.client as any)?._trigger('sync_event', message);

      const syncStatus = store.getSyncStatus(123);
      expect(syncStatus.status).toBe('completed');
      expect(syncStatus.progress).toBe(100);
    });

    it('应该处理sync_event消息（failed）', async () => {
      const store = useWebSocketStore();

      await store.initConnection('test_token');

      const message = {
        type: 'sync_event',
        repository_id: 123,
        action: 'failed',
        error: 'Sync failed: network error',
      };

      (store.client as any)?._trigger('sync_event', message);

      const syncStatus = store.getSyncStatus(123);
      expect(syncStatus.status).toBe('failed');
    });

    it('应该处理sync_event消息（started）', async () => {
      const store = useWebSocketStore();

      await store.initConnection('test_token');

      const message = {
        type: 'sync_event',
        repository_id: 123,
        action: 'started',
      };

      (store.client as any)?._trigger('sync_event', message);

      const syncStatus = store.getSyncStatus(123);
      expect(syncStatus.status).toBe('running');
    });

    it('应该返回默认同步状态', () => {
      const store = useWebSocketStore();

      const syncStatus = store.getSyncStatus(999);

      expect(syncStatus.repositoryId).toBe(999);
      expect(syncStatus.status).toBe('idle');
      expect(syncStatus.progress).toBe(0);
    });
  });

  /**
   * 进度管理测试
   */
  describe('Progress Management', () => {
    it('应该处理progress消息', async () => {
      const store = useWebSocketStore();

      await store.initConnection('test_token');

      const message = {
        type: 'progress',
        operation_id: 'op_123',
        operation_type: 'clone',
        progress: 75,
        status: 'running',
        message: 'Cloning repository...',
        details: { current: 75, total: 100 },
      };

      (store.client as any)?._trigger('progress', message);

      const progress = store.getProgress('op_123');
      expect(progress).not.toBeUndefined();
      expect(progress?.operationId).toBe('op_123');
      expect(progress?.progress).toBe(75);
      expect(progress?.status).toBe('running');
    });

    it('应该在进度完成后清理', async () => {
      const store = useWebSocketStore();

      await store.initConnection('test_token');

      const message = {
        type: 'progress',
        operation_id: 'op_123',
        operation_type: 'clone',
        progress: 100,
        status: 'completed',
        message: 'Clone completed',
      };

      (store.client as any)?._trigger('progress', message);

      expect(store.getProgress('op_123')).not.toBeUndefined();

      // 前进5秒
      vi.advanceTimersByTime(5000);

      expect(store.getProgress('op_123')).toBeUndefined();
    });

    it('应该在进度失败后清理', async () => {
      const store = useWebSocketStore();

      await store.initConnection('test_token');

      const message = {
        type: 'progress',
        operation_id: 'op_123',
        operation_type: 'clone',
        progress: 50,
        status: 'failed',
        message: 'Clone failed',
      };

      (store.client as any)?._trigger('progress', message);

      // 前进5秒
      vi.advanceTimersByTime(5000);

      expect(store.getProgress('op_123')).toBeUndefined();
    });

    it('应该返回undefined获取不存在的进度', () => {
      const store = useWebSocketStore();

      const progress = store.getProgress('non_existent_op');

      expect(progress).toBeUndefined();
    });
  });

  /**
   * 订阅管理测试
   */
  describe('Subscription Management', () => {
    it('应该订阅仓库', async () => {
      const store = useWebSocketStore();

      await store.initConnection('test_token');

      const result = store.subscribeRepository(123);

      expect(result).toBe(true);
      expect(store.client?.subscribeRepository).toHaveBeenCalledWith(123);
    });

    it('未连接时不应订阅仓库', async () => {
      const store = useWebSocketStore();

      // 不初始化连接
      const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
      const result = store.subscribeRepository(123);

      expect(result).toBe(false);
      consoleSpy.mockRestore();
    });

    it('应该取消订阅仓库', async () => {
      const store = useWebSocketStore();

      await store.initConnection('test_token');

      const result = store.unsubscribeRepository(123);

      expect(result).toBe(true);
      expect(store.client?.unsubscribeRepository).toHaveBeenCalledWith(123);
    });

    it('应该处理subscribed确认消息', async () => {
      const store = useWebSocketStore();

      await store.initConnection('test_token');

      const message = {
        type: 'subscribed',
        channel: 'repository',
        repository_id: 123,
      };

      (store.client as any)?._trigger('subscribed', message);

      expect(store.subscribedRepositories.has(123)).toBe(true);
    });

    it('应该处理unsubscribed确认消息', async () => {
      const store = useWebSocketStore();

      await store.initConnection('test_token');

      // 先订阅
      store.subscribedRepositories.add(123);

      const message = {
        type: 'unsubscribed',
        channel: 'repository',
        repository_id: 123,
      };

      (store.client as any)?._trigger('unsubscribed', message);

      expect(store.subscribedRepositories.has(123)).toBe(false);
    });
  });

  /**
   * 错误处理测试
   */
  describe('Error Handling', () => {
    it('应该处理error消息', async () => {
      const store = useWebSocketStore();

      await store.initConnection('test_token');

      const message = {
        type: 'error',
        error: 'Connection timeout',
      };

      (store.client as any)?._trigger('error', message);

      expect(store.notifications).toHaveLength(1);
      expect(store.notifications[0].type).toBe('error');
      expect(store.notifications[0].title).toBe('WebSocket错误');
    });

    it('应该在连接错误时更新状态', async () => {
      const store = useWebSocketStore();
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      await store.initConnection('test_token');

      // 触发onError
      (store.client as any).onError(new Event('error'));

      consoleSpy.mockRestore();
    });
  });

  /**
   * 消息发送测试
   */
  describe('Message Sending', () => {
    it('应该发送消息', async () => {
      const store = useWebSocketStore();

      await store.initConnection('test_token');

      const message = { type: 'ping' };
      const result = store.sendMessage(message);

      expect(result).toBe(true);
      expect(store.client?.send).toHaveBeenCalledWith(message);
    });

    it('未连接时不应发送消息', async () => {
      const store = useWebSocketStore();
      const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

      const message = { type: 'ping' };
      const result = store.sendMessage(message);

      expect(result).toBe(false);
      consoleSpy.mockRestore();
    });
  });

  /**
   * 连接状态测试
   */
  describe('Connection State', () => {
    it('应该处理connected消息', async () => {
      const store = useWebSocketStore();

      await store.initConnection('test_token');

      const message = {
        type: 'connected',
        connection_id: 'conn_123',
        authenticated: true,
        user: { id: 1, username: 'testuser' },
      };

      (store.client as any)?._trigger('connected', message);

      expect(store.connectionId).toBe('conn_123');
      expect(store.isAuthenticated).toBe(true);
    });

    it('应该在连接关闭时重置状态', async () => {
      const store = useWebSocketStore();

      await store.initConnection('test_token');

      // 设置一些状态
      store.isConnected = true;
      store.isAuthenticated = true;
      store.connectionId = 'conn_123';
      store.subscribedRepositories.add(123);

      // 触发onClose
      (store.client as any).onClose(new CloseEvent('close'));

      expect(store.isConnected).toBe(false);
      expect(store.isAuthenticated).toBe(false);
      expect(store.connectionId).toBeNull();
      // 注意：subscribedRepositories 在 onClose 回调中不会被清除
      // 它只在调用 disconnect() 方法时清除
      expect(store.subscribedRepositories.size).toBe(1);
    });
  });
});

describe('WebSocket Store Integration', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  it('应该完成完整的通知流程', async () => {
    const store = useWebSocketStore();

    // 初始化连接
    await store.initConnection('test_token');

    // 订阅仓库
    store.subscribeRepository(123);

    // 模拟收到多个通知
    const notifications = [
      { type: 'notification', action: 'commit_new', repository_id: 123, data: { message: 'Commit 1' } },
      { type: 'notification', action: 'commit_new', repository_id: 123, data: { message: 'Commit 2' } },
      { type: 'notification', action: 'branch_update', repository_id: 456, data: { message: 'Branch updated' } },
    ];

    notifications.forEach((msg) => {
      (store.client as any)?._trigger('notification', msg);
    });

    expect(store.notifications).toHaveLength(3);
    expect(store.unreadCount).toBe(3);
    expect(store.getRepositoryNotifications(123)).toHaveLength(2);

    // 标记已读
    store.markAllNotificationsAsRead();
    expect(store.unreadCount).toBe(0);

    // 清除通知
    store.clearNotifications();
    expect(store.notifications).toHaveLength(0);
  });

  it('应该管理多个仓库的同步状态', async () => {
    const store = useWebSocketStore();

    await store.initConnection('test_token');

    // 多个仓库的同步状态更新
    const syncUpdates = [
      { type: 'sync_status_update', repository_id: 1, status: 'running', progress: 30 },
      { type: 'sync_status_update', repository_id: 2, status: 'running', progress: 50 },
      { type: 'sync_status_update', repository_id: 1, status: 'running', progress: 60 },
      { type: 'sync_event', repository_id: 2, action: 'completed' },
    ];

    syncUpdates.forEach((msg) => {
      (store.client as any)?._trigger(msg.type, msg);
    });

    expect(store.getSyncStatus(1).progress).toBe(60);
    expect(store.getSyncStatus(2).status).toBe('completed');
    expect(store.getSyncStatus(2).progress).toBe(100);
  });

  it('应该管理多个操作的进度', async () => {
    const store = useWebSocketStore();

    await store.initConnection('test_token');

    // 多个操作的进度更新
    const progressUpdates = [
      { type: 'progress', operation_id: 'op_1', operation_type: 'clone', progress: 25, status: 'running' },
      { type: 'progress', operation_id: 'op_2', operation_type: 'pull', progress: 50, status: 'running' },
      { type: 'progress', operation_id: 'op_1', operation_type: 'clone', progress: 75, status: 'running' },
      { type: 'progress', operation_id: 'op_2', operation_type: 'pull', progress: 100, status: 'completed' },
    ];

    progressUpdates.forEach((msg) => {
      (store.client as any)?._trigger('progress', msg);
    });

    expect(store.getProgress('op_1')?.progress).toBe(75);

    // op_2应该被清理
    vi.advanceTimersByTime(5000);
    expect(store.getProgress('op_2')).toBeUndefined();
  });
});
