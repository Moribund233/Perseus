/**
 * WebSocket客户端单元测试
 *
 * 测试范围:
 * 1. WebSocketClient - 连接管理、消息处理
 * 2. 自动重连机制
 * 3. 心跳检测
 * 4. 消息处理器注册/注销
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { WebSocketClient, WebSocketConfig, WebSocketMessage } from '../src/utils/websocket';

// WebSocket readyState 常量
const WS_CONNECTING = 0;
const WS_OPEN = 1;
const WS_CLOSING = 2;
const WS_CLOSED = 3;

// Mock WebSocket
global.WebSocket = vi.fn() as any;
global.WebSocket.CONNECTING = WS_CONNECTING;
global.WebSocket.OPEN = WS_OPEN;
global.WebSocket.CLOSING = WS_CLOSING;
global.WebSocket.CLOSED = WS_CLOSED;

// Mock window 对象以支持 Node.js 测试环境
global.window = {
  setTimeout: (fn: any, delay: number) => setTimeout(fn, delay),
  clearTimeout: (id: any) => clearTimeout(id),
  setInterval: (fn: any, delay: number) => setInterval(fn, delay),
  clearInterval: (id: any) => clearInterval(id),
} as any;

// 模拟WebSocket实例
const createMockWebSocket = () => {
  const mockWS = {
    readyState: WS_CONNECTING,
    send: vi.fn(),
    close: vi.fn(),
    onopen: null as ((event: Event) => void) | null,
    onmessage: null as ((event: MessageEvent) => void) | null,
    onclose: null as ((event: CloseEvent) => void) | null,
    onerror: null as ((event: Event) => void) | null,
  };
  return mockWS;
};

describe('WebSocketClient', () => {
  let mockWS: ReturnType<typeof createMockWebSocket>;

  beforeEach(() => {
    vi.clearAllMocks();
    mockWS = createMockWebSocket();
    (global.WebSocket as any).mockImplementation(() => mockWS);
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  /**
   * 基础连接测试
   */
  describe('Connection', () => {
    it('应该正确创建WebSocket连接', () => {
      const config: WebSocketConfig = {
        url: 'ws://localhost:8080/ws/',
      };

      const client = new WebSocketClient(config);
      client.connect();

      expect(global.WebSocket).toHaveBeenCalledWith('ws://localhost:8080/ws/');
    });

    it('连接已存在时不应重复创建', () => {
      const config: WebSocketConfig = {
        url: 'ws://localhost:8080/ws/',
      };

      const client = new WebSocketClient(config);
      client.connect();

      mockWS.readyState = WS_OPEN;
      mockWS.onopen?.(new Event('open'));

      // 再次连接
      client.connect();

      expect(global.WebSocket).toHaveBeenCalledTimes(1);
    });

    it('应该正确关闭连接', () => {
      const config: WebSocketConfig = {
        url: 'ws://localhost:8080/ws/',
      };

      const client = new WebSocketClient(config);
      client.connect();
      client.close();

      expect(mockWS.close).toHaveBeenCalled();
    });

    it('应该触发onOpen回调', () => {
      const onOpen = vi.fn();
      const config: WebSocketConfig = {
        url: 'ws://localhost:8080/ws/',
        onOpen,
      };

      const client = new WebSocketClient(config);
      client.connect();

      mockWS.readyState = WS_OPEN;
      mockWS.onopen?.(new Event('open'));

      expect(onOpen).toHaveBeenCalled();
    });

    it('应该触发onClose回调', () => {
      const onClose = vi.fn();
      const config: WebSocketConfig = {
        url: 'ws://localhost:8080/ws/',
        onClose,
      };

      const client = new WebSocketClient(config);
      client.connect();

      mockWS.readyState = WS_OPEN;
      mockWS.onopen?.(new Event('open'));

      const closeEvent = new CloseEvent('close', { code: 1000 });
      mockWS.onclose?.(closeEvent);

      expect(onClose).toHaveBeenCalledWith(closeEvent);
    });

    it('应该触发onError回调', () => {
      const onError = vi.fn();
      const config: WebSocketConfig = {
        url: 'ws://localhost:8080/ws/',
        onError,
      };

      const client = new WebSocketClient(config);
      client.connect();

      const errorEvent = new Event('error');
      mockWS.onerror?.(errorEvent);

      expect(onError).toHaveBeenCalledWith(errorEvent);
    });

    it('应该正确获取连接状态', () => {
      const config: WebSocketConfig = {
        url: 'ws://localhost:8080/ws/',
      };

      const client = new WebSocketClient(config);

      expect(client.isConnected).toBe(false);

      client.connect();
      mockWS.readyState = WS_OPEN;
      mockWS.onopen?.(new Event('open'));

      expect(client.isConnected).toBe(true);
    });
  });

  /**
   * 消息发送测试
   */
  describe('Message Sending', () => {
    it('应该正确发送消息', () => {
      const config: WebSocketConfig = {
        url: 'ws://localhost:8080/ws/',
      };

      const client = new WebSocketClient(config);
      client.connect();

      mockWS.readyState = WS_OPEN;
      mockWS.onopen?.(new Event('open'));

      const message: WebSocketMessage = {
        type: 'test',
        data: 'hello',
      };

      const result = client.send(message);

      expect(result).toBe(true);
      expect(mockWS.send).toHaveBeenCalledWith(JSON.stringify(message));
    });

    it('连接未建立时发送消息应该失败', () => {
      const config: WebSocketConfig = {
        url: 'ws://localhost:8080/ws/',
      };

      const client = new WebSocketClient(config);

      const message: WebSocketMessage = {
        type: 'test',
        data: 'hello',
      };

      const result = client.send(message);

      expect(result).toBe(false);
    });

    it('应该正确订阅仓库', () => {
      const config: WebSocketConfig = {
        url: 'ws://localhost:8080/ws/',
      };

      const client = new WebSocketClient(config);
      client.connect();

      mockWS.readyState = WS_OPEN;
      mockWS.onopen?.(new Event('open'));

      client.subscribeRepository(123);

      expect(mockWS.send).toHaveBeenCalledWith(
        JSON.stringify({
          type: 'subscribe',
          channel: 'repository',
          repository_id: 123,
        })
      );
    });

    it('应该正确取消订阅仓库', () => {
      const config: WebSocketConfig = {
        url: 'ws://localhost:8080/ws/',
      };

      const client = new WebSocketClient(config);
      client.connect();

      mockWS.readyState = WS_OPEN;
      mockWS.onopen?.(new Event('open'));

      client.unsubscribeRepository(123);

      expect(mockWS.send).toHaveBeenCalledWith(
        JSON.stringify({
          type: 'unsubscribe',
          channel: 'repository',
          repository_id: 123,
        })
      );
    });

    it('应该正确订阅用户通知', () => {
      const config: WebSocketConfig = {
        url: 'ws://localhost:8080/ws/',
      };

      const client = new WebSocketClient(config);
      client.connect();

      mockWS.readyState = WS_OPEN;
      mockWS.onopen?.(new Event('open'));

      client.subscribeUserNotifications();

      expect(mockWS.send).toHaveBeenCalledWith(
        JSON.stringify({
          type: 'subscribe',
          channel: 'user_notifications',
        })
      );
    });
  });

  /**
   * 消息接收测试
   */
  describe('Message Receiving', () => {
    it('应该正确解析收到的消息', () => {
      const onMessage = vi.fn();
      const config: WebSocketConfig = {
        url: 'ws://localhost:8080/ws/',
        onMessage,
      };

      const client = new WebSocketClient(config);
      client.connect();

      const message: WebSocketMessage = {
        type: 'notification',
        data: { message: 'Hello' },
      };

      mockWS.onmessage?.(
        new MessageEvent('message', { data: JSON.stringify(message) })
      );

      expect(onMessage).toHaveBeenCalledWith(message);
    });

    it('应该处理消息解析错误', () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      const config: WebSocketConfig = {
        url: 'ws://localhost:8080/ws/',
      };

      const client = new WebSocketClient(config);
      client.connect();

      mockWS.onmessage?.(
        new MessageEvent('message', { data: 'invalid json' })
      );

      expect(consoleSpy).toHaveBeenCalledWith(
        '[WebSocket] 消息解析失败:',
        expect.any(Error)
      );

      consoleSpy.mockRestore();
    });

    it('应该处理connected消息', () => {
      const config: WebSocketConfig = {
        url: 'ws://localhost:8080/ws/',
      };

      const client = new WebSocketClient(config);
      client.connect();

      const message: WebSocketMessage = {
        type: 'connected',
        connection_id: 'conn_123',
        authenticated: true,
      };

      mockWS.onmessage?.(
        new MessageEvent('message', { data: JSON.stringify(message) })
      );

      expect(client.getConnectionId).toBe('conn_123');
      expect(client.isAuthenticated).toBe(true);
    });

    it('应该正确处理pong消息', () => {
      const onMessage = vi.fn();
      const config: WebSocketConfig = {
        url: 'ws://localhost:8080/ws/',
        onMessage,
      };

      const client = new WebSocketClient(config);
      client.connect();

      const message: WebSocketMessage = {
        type: 'pong',
        timestamp: '2024-01-01T00:00:00Z',
      };

      mockWS.onmessage?.(
        new MessageEvent('message', { data: JSON.stringify(message) })
      );

      // pong消息不应该触发onMessage回调
      expect(onMessage).not.toHaveBeenCalled();
    });
  });

  /**
   * 消息处理器测试
   */
  describe('Message Handlers', () => {
    it('应该正确注册消息处理器', () => {
      const config: WebSocketConfig = {
        url: 'ws://localhost:8080/ws/',
      };

      const client = new WebSocketClient(config);
      const handler = vi.fn();

      const unsubscribe = client.on('notification', handler);

      expect(typeof unsubscribe).toBe('function');
    });

    it('应该正确触发消息处理器', () => {
      const config: WebSocketConfig = {
        url: 'ws://localhost:8080/ws/',
      };

      const client = new WebSocketClient(config);
      client.connect();

      const handler = vi.fn();
      client.on('notification', handler);

      const message: WebSocketMessage = {
        type: 'notification',
        data: { message: 'Hello' },
      };

      mockWS.onmessage?.(
        new MessageEvent('message', { data: JSON.stringify(message) })
      );

      expect(handler).toHaveBeenCalledWith(message);
    });

    it('应该正确注销消息处理器', () => {
      const config: WebSocketConfig = {
        url: 'ws://localhost:8080/ws/',
      };

      const client = new WebSocketClient(config);
      client.connect();

      const handler = vi.fn();
      const unsubscribe = client.on('notification', handler);

      // 注销处理器
      unsubscribe();

      const message: WebSocketMessage = {
        type: 'notification',
        data: { message: 'Hello' },
      };

      mockWS.onmessage?.(
        new MessageEvent('message', { data: JSON.stringify(message) })
      );

      expect(handler).not.toHaveBeenCalled();
    });

    it('应该支持多个消息处理器', () => {
      const config: WebSocketConfig = {
        url: 'ws://localhost:8080/ws/',
      };

      const client = new WebSocketClient(config);
      client.connect();

      const handler1 = vi.fn();
      const handler2 = vi.fn();

      client.on('notification', handler1);
      client.on('notification', handler2);

      const message: WebSocketMessage = {
        type: 'notification',
        data: { message: 'Hello' },
      };

      mockWS.onmessage?.(
        new MessageEvent('message', { data: JSON.stringify(message) })
      );

      expect(handler1).toHaveBeenCalledWith(message);
      expect(handler2).toHaveBeenCalledWith(message);
    });

    it('应该处理处理器执行异常', () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      const config: WebSocketConfig = {
        url: 'ws://localhost:8080/ws/',
      };

      const client = new WebSocketClient(config);
      client.connect();

      const handler = vi.fn().mockImplementation(() => {
        throw new Error('Handler error');
      });

      client.on('notification', handler);

      const message: WebSocketMessage = {
        type: 'notification',
        data: { message: 'Hello' },
      };

      mockWS.onmessage?.(
        new MessageEvent('message', { data: JSON.stringify(message) })
      );

      expect(consoleSpy).toHaveBeenCalledWith(
        '[WebSocket] 消息处理器执行失败 [notification]:',
        expect.any(Error)
      );

      consoleSpy.mockRestore();
    });
  });

  /**
   * 自动重连测试
   */
  describe('Auto Reconnect', () => {
    it('应该在连接关闭后自动重连', () => {
      const config: WebSocketConfig = {
        url: 'ws://localhost:8080/ws/',
        autoReconnect: true,
        reconnectInterval: 3000,
      };

      const client = new WebSocketClient(config);
      client.connect();

      mockWS.readyState = WS_OPEN;
      mockWS.onopen?.(new Event('open'));

      // WebSocket应该只被创建一次
      expect(global.WebSocket).toHaveBeenCalledTimes(1);

      // 模拟连接关闭
      mockWS.readyState = WS_CLOSED;
      mockWS.onclose?.(new CloseEvent('close', { code: 1006 }));

      // 前进时间触发重连
      vi.advanceTimersByTime(3000);

      // WebSocket应该被重新创建
      expect(global.WebSocket).toHaveBeenCalledTimes(2);
    });

    it('手动关闭时不应自动重连', () => {
      const config: WebSocketConfig = {
        url: 'ws://localhost:8080/ws/',
        autoReconnect: true,
        reconnectInterval: 3000,
      };

      const client = new WebSocketClient(config);
      client.connect();

      mockWS.readyState = WS_OPEN;
      mockWS.onopen?.(new Event('open'));

      // 手动关闭
      client.close();

      // 前进时间
      vi.advanceTimersByTime(3000);

      // WebSocket不应该被重新创建
      expect(global.WebSocket).toHaveBeenCalledTimes(1);
    });

    it('应该限制最大重连次数', () => {
      const config: WebSocketConfig = {
        url: 'ws://localhost:8080/ws/',
        autoReconnect: true,
        reconnectInterval: 1000,
        maxReconnectAttempts: 3,
      };

      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      const client = new WebSocketClient(config);
      client.connect();

      // 模拟连接关闭触发重连
      mockWS.onclose?.(new CloseEvent('close', { code: 1006 }));

      // 每次重连都会创建新的 WebSocket
      // 初始连接 + 3次重连 = 4次
      for (let i = 0; i < 3; i++) {
        vi.advanceTimersByTime(1000);
        // 新创建的 mockWS 立即关闭，触发下一次重连
        const newMockWS = (global.WebSocket as any).mock.results[(global.WebSocket as any).mock.results.length - 1]?.value;
        if (newMockWS && newMockWS.onclose) {
          newMockWS.onclose(new CloseEvent('close', { code: 1006 }));
        }
      }

      // 应该只重连3次
      expect(global.WebSocket).toHaveBeenCalledTimes(4); // 初始 + 3次重连

      expect(consoleSpy).toHaveBeenCalledWith(
        '[WebSocket] 达到最大重连次数，放弃重连'
      );

      consoleSpy.mockRestore();
    });

    it('成功连接后应该重置重连计数', () => {
      const config: WebSocketConfig = {
        url: 'ws://localhost:8080/ws/',
        autoReconnect: true,
        reconnectInterval: 1000,
        maxReconnectAttempts: 3,
      };

      const client = new WebSocketClient(config);
      client.connect();

      // 模拟连接失败触发重连
      mockWS.readyState = WS_CLOSED;
      mockWS.onclose?.(new CloseEvent('close', { code: 1006 }));
      vi.advanceTimersByTime(1000);

      // 获取重连后的新 WebSocket 实例并模拟成功连接
      const newMockWS = (global.WebSocket as any).mock.results[1]?.value;
      if (newMockWS) {
        newMockWS.readyState = WS_OPEN;
        newMockWS.onopen?.(new Event('open'));
      }

      // 再次断开触发第二次重连
      if (newMockWS) {
        newMockWS.readyState = WS_CLOSED;
        newMockWS.onclose?.(new CloseEvent('close', { code: 1006 }));
      }
      vi.advanceTimersByTime(1000);

      // 应该再次重连 (初始 + 2次重连)
      expect(global.WebSocket).toHaveBeenCalledTimes(3);
    });
  });

  /**
   * 心跳检测测试
   */
  describe('Heartbeat', () => {
    it('应该定期发送ping消息', () => {
      const config: WebSocketConfig = {
        url: 'ws://localhost:8080/ws/',
        heartbeatInterval: 30000,
      };

      const client = new WebSocketClient(config);
      client.connect();

      mockWS.readyState = WS_OPEN;
      mockWS.onopen?.(new Event('open'));

      // 前进30秒
      vi.advanceTimersByTime(30000);

      expect(mockWS.send).toHaveBeenCalledWith(
        expect.stringContaining('"type":"ping"')
      );

      // 再前进30秒
      vi.advanceTimersByTime(30000);

      expect(mockWS.send).toHaveBeenCalledTimes(2);
    });

    it('连接关闭时应该停止心跳', () => {
      const config: WebSocketConfig = {
        url: 'ws://localhost:8080/ws/',
        heartbeatInterval: 30000,
      };

      const client = new WebSocketClient(config);
      client.connect();

      mockWS.readyState = WS_OPEN;
      mockWS.onopen?.(new Event('open'));

      // 关闭连接
      client.close();

      // 前进30秒
      vi.advanceTimersByTime(30000);

      // 不应该发送ping
      expect(mockWS.send).not.toHaveBeenCalledWith(
        expect.stringContaining('"type":"ping"')
      );
    });

    it('连接断开时应该停止心跳', () => {
      const config: WebSocketConfig = {
        url: 'ws://localhost:8080/ws/',
        heartbeatInterval: 30000,
      };

      const client = new WebSocketClient(config);
      client.connect();

      mockWS.readyState = WS_OPEN;
      mockWS.onopen?.(new Event('open'));

      // 模拟连接断开
      mockWS.onclose?.(new CloseEvent('close', { code: 1006 }));

      // 前进30秒
      vi.advanceTimersByTime(30000);

      // 不应该发送ping
      expect(mockWS.send).not.toHaveBeenCalledWith(
        expect.stringContaining('"type":"ping"')
      );
    });
  });

  /**
   * 配置测试
   */
  describe('Configuration', () => {
    it('应该使用默认配置', () => {
      const config: WebSocketConfig = {
        url: 'ws://localhost:8080/ws/',
      };

      const client = new WebSocketClient(config);
      client.connect();

      mockWS.readyState = WS_OPEN;
      mockWS.onopen?.(new Event('open'));

      // 默认心跳间隔30秒
      vi.advanceTimersByTime(30000);

      // 应该发送ping
      expect(mockWS.send).toHaveBeenCalled();
    });

    it('应该允许自定义配置', () => {
      const onOpen = vi.fn();
      const onClose = vi.fn();
      const onError = vi.fn();
      const onMessage = vi.fn();

      const config: WebSocketConfig = {
        url: 'ws://localhost:8080/ws/',
        autoReconnect: true,
        reconnectInterval: 5000,
        maxReconnectAttempts: 10,
        heartbeatInterval: 60000,
        onOpen,
        onClose,
        onError,
        onMessage,
      };

      const client = new WebSocketClient(config);
      client.connect();

      mockWS.readyState = WS_OPEN;
      mockWS.onopen?.(new Event('open'));

      expect(onOpen).toHaveBeenCalled();

      // 前进60秒（自定义心跳间隔）
      vi.advanceTimersByTime(60000);

      expect(mockWS.send).toHaveBeenCalled();
    });
  });
});

/**
 * 集成测试
 */
describe('WebSocketClient Integration', () => {
  let mockWS: ReturnType<typeof createMockWebSocket>;

  beforeEach(() => {
    vi.clearAllMocks();
    mockWS = createMockWebSocket();
    (global.WebSocket as any).mockImplementation(() => mockWS);
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('应该完成完整的连接流程', () => {
    const events: string[] = [];

    const config: WebSocketConfig = {
      url: 'ws://localhost:8080/ws/',
      onOpen: () => events.push('open'),
      onMessage: () => events.push('message'),
    };

    const client = new WebSocketClient(config);

    // 连接
    client.connect();
    events.push('connect');

    // 模拟连接成功
    mockWS.readyState = WS_OPEN;
    mockWS.onopen?.(new Event('open'));

    // 模拟收到connected消息
    mockWS.onmessage?.(
      new MessageEvent('message', {
        data: JSON.stringify({
          type: 'connected',
          connection_id: 'conn_123',
          authenticated: true,
        }),
      })
    );

    // 订阅仓库
    client.subscribeRepository(1);
    events.push('subscribe');

    // 模拟收到通知
    mockWS.onmessage?.(
      new MessageEvent('message', {
        data: JSON.stringify({
          type: 'notification',
          data: { message: 'New commit' },
        }),
      })
    );

    // 关闭连接
    client.close();
    events.push('close');

    expect(events).toEqual(['connect', 'open', 'message', 'subscribe', 'message', 'close']);
    expect(client.getConnectionId).toBe('conn_123');
    expect(client.isAuthenticated).toBe(true);
  });

  it('应该处理重连后的状态恢复', () => {
    const config: WebSocketConfig = {
      url: 'ws://localhost:8080/ws/',
      autoReconnect: true,
      reconnectInterval: 1000,
    };

    const client = new WebSocketClient(config);
    client.connect();

    // 第一次连接成功
    mockWS.readyState = WS_OPEN;
    mockWS.onopen?.(new Event('open'));

    mockWS.onmessage?.(
      new MessageEvent('message', {
        data: JSON.stringify({
          type: 'connected',
          connection_id: 'conn_1',
          authenticated: true,
        }),
      })
    );

    expect(client.getConnectionId).toBe('conn_1');

    // 模拟断开
    mockWS.onclose?.(new CloseEvent('close', { code: 1006 }));

    // 触发重连
    vi.advanceTimersByTime(1000);

    // 第二次连接成功
    mockWS.readyState = WS_OPEN;
    mockWS.onopen?.(new Event('open'));

    mockWS.onmessage?.(
      new MessageEvent('message', {
        data: JSON.stringify({
          type: 'connected',
          connection_id: 'conn_2',
          authenticated: true,
        }),
      })
    );

    expect(client.getConnectionId).toBe('conn_2');
  });
});
