/**
 * WebSocket客户端核心模块
 *
 * 提供WebSocket连接管理和消息处理功能
 */

// WebSocket配置 - 从环境变量读取
const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL;

// 定时器类型定义
type TimerId = ReturnType<typeof setTimeout>;

// 兼容浏览器和Node.js环境的定时器函数
// 使用函数形式在运行时动态选择，以支持测试中的 vi.useFakeTimers()
const _setTimeout = (fn: (...args: any[]) => void, delay: number, ...args: any[]): TimerId => {
  return (typeof window !== 'undefined' ? window.setTimeout : setTimeout)(fn, delay, ...args);
};
const _setInterval = (fn: (...args: any[]) => void, delay: number, ...args: any[]): TimerId => {
  return (typeof window !== 'undefined' ? window.setInterval : setInterval)(fn, delay, ...args);
};
const _clearTimeout = (id: TimerId): void => {
  return (typeof window !== 'undefined' ? window.clearTimeout : clearTimeout)(id);
};
const _clearInterval = (id: TimerId): void => {
  return (typeof window !== 'undefined' ? window.clearInterval : clearInterval)(id);
};

// 消息类型定义
export interface WebSocketMessage {
  type: string;
  [key: string]: any;
}

export interface WebSocketConfig {
  url: string;
  autoReconnect?: boolean;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  heartbeatInterval?: number;
  onOpen?: () => void;
  onClose?: (event: CloseEvent) => void;
  onError?: (error: Event) => void;
  onMessage?: (message: WebSocketMessage) => void;
}

export type MessageHandler = (message: WebSocketMessage) => void;

/**
 * WebSocket客户端类
 */
export class WebSocketClient {
  private ws: WebSocket | null = null;
  private config: Required<WebSocketConfig>;
  private reconnectAttempts = 0;
  private reconnectTimer: TimerId | null = null;
  private heartbeatTimer: TimerId | null = null;
  private messageHandlers: Map<string, Set<MessageHandler>> = new Map();
  private isManualClose = false;
  private connectionId: string | null = null;
  private authenticated = false;

  constructor(config: WebSocketConfig) {
    this.config = {
      autoReconnect: true,
      reconnectInterval: 3000,
      maxReconnectAttempts: 5,
      heartbeatInterval: 30000,
      onOpen: () => {},
      onClose: () => {},
      onError: () => {},
      onMessage: () => {},
      ...config,
    };
  }

  /**
   * 建立WebSocket连接
   */
  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      console.log('[WebSocket] 连接已存在');
      return;
    }

    this.isManualClose = false;

    try {
      this.ws = new WebSocket(this.config.url);
      this.setupEventHandlers();
    } catch (error) {
      console.error('[WebSocket] 连接创建失败:', error);
      this.handleReconnect();
    }
  }

  /**
   * 设置事件处理器
   */
  private setupEventHandlers(): void {
    if (!this.ws) return;

    this.ws.onopen = () => {
      console.log('[WebSocket] 连接已建立');
      this.reconnectAttempts = 0;
      this.startHeartbeat();
      this.config.onOpen();
    };

    this.ws.onmessage = (event) => {
      try {
        const message: WebSocketMessage = JSON.parse(event.data);
        this.handleMessage(message);
        // 只有非pong消息才触发onMessage回调
        if (message.type !== 'pong') {
          this.config.onMessage(message);
        }
      } catch (error) {
        console.error('[WebSocket] 消息解析失败:', error);
      }
    };

    this.ws.onclose = (event) => {
      console.log('[WebSocket] 连接已关闭:', event.code, event.reason);
      this.stopHeartbeat();
      this.config.onClose(event);

      if (!this.isManualClose && this.config.autoReconnect) {
        this.handleReconnect();
      }
    };

    this.ws.onerror = (error) => {
      console.error('[WebSocket] 连接错误:', error);
      this.config.onError(error);
    };
  }

  /**
   * 处理收到的消息
   */
  private handleMessage(message: WebSocketMessage): void {
    const { type } = message;

    // 处理连接成功消息
    if (type === 'connected') {
      this.connectionId = message.connection_id;
      this.authenticated = message.authenticated || false;
      console.log('[WebSocket] 连接成功:', message.message);
    }

    // 处理心跳响应
    if (type === 'pong') {
      return;
    }

    // 调用注册的消息处理器
    const handlers = this.messageHandlers.get(type);
    if (handlers) {
      handlers.forEach((handler) => {
        try {
          handler(message);
        } catch (error) {
          console.error(`[WebSocket] 消息处理器执行失败 [${type}]:`, error);
        }
      });
    }
  }

  /**
   * 处理重连
   */
  private handleReconnect(): void {
    if (this.reconnectAttempts >= this.config.maxReconnectAttempts) {
      console.error('[WebSocket] 达到最大重连次数，放弃重连');
      return;
    }

    this.reconnectAttempts++;
    console.log(
      `[WebSocket] ${this.config.reconnectInterval}ms后尝试第${this.reconnectAttempts}次重连...`
    );

    this.reconnectTimer = _setTimeout(() => {
      this.connect();
    }, this.config.reconnectInterval);
  }

  /**
   * 启动心跳
   */
  private startHeartbeat(): void {
    this.heartbeatTimer = _setInterval(() => {
      this.send({
        type: 'ping',
        timestamp: new Date().toISOString(),
      });
    }, this.config.heartbeatInterval);
  }

  /**
   * 停止心跳
   */
  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      _clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  /**
   * 发送消息
   */
  send(message: WebSocketMessage): boolean {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
      return true;
    }
    console.warn('[WebSocket] 连接未建立，无法发送消息');
    return false;
  }

  /**
   * 注册消息处理器
   */
  on(messageType: string, handler: MessageHandler): () => void {
    if (!this.messageHandlers.has(messageType)) {
      this.messageHandlers.set(messageType, new Set());
    }
    this.messageHandlers.get(messageType)!.add(handler);

    // 返回取消订阅函数
    return () => {
      this.off(messageType, handler);
    };
  }

  /**
   * 移除消息处理器
   */
  off(messageType: string, handler: MessageHandler): void {
    const handlers = this.messageHandlers.get(messageType);
    if (handlers) {
      handlers.delete(handler);
    }
  }

  /**
   * 订阅仓库消息
   */
  subscribeRepository(repositoryId: number): boolean {
    return this.send({
      type: 'subscribe',
      channel: 'repository',
      repository_id: repositoryId,
    });
  }

  /**
   * 取消订阅仓库消息
   */
  unsubscribeRepository(repositoryId: number): boolean {
    return this.send({
      type: 'unsubscribe',
      channel: 'repository',
      repository_id: repositoryId,
    });
  }

  /**
   * 订阅用户通知
   */
  subscribeUserNotifications(): boolean {
    return this.send({
      type: 'subscribe',
      channel: 'user_notifications',
    });
  }

  /**
   * 关闭连接
   */
  close(): void {
    this.isManualClose = true;
    this.stopHeartbeat();

    if (this.reconnectTimer) {
      _clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  /**
   * 获取连接状态
   */
  get readyState(): number {
    return this.ws?.readyState ?? WebSocket.CLOSED;
  }

  get isConnected(): boolean {
    return this.readyState === WebSocket.OPEN;
  }

  get isAuthenticated(): boolean {
    return this.authenticated;
  }

  get getConnectionId(): string | null {
    return this.connectionId;
  }
}

/**
 * 创建带认证的WebSocket客户端
 */
export function createAuthenticatedWebSocket(token: string): WebSocketClient {
  const url = `${WS_BASE_URL}/ws/?token=${encodeURIComponent(token)}`;
  return new WebSocketClient({ url });
}

/**
 * 创建匿名WebSocket客户端
 */
export function createAnonymousWebSocket(): WebSocketClient {
  return new WebSocketClient({ url: `${WS_BASE_URL}/ws/` });
}

/**
 * 创建仓库专用WebSocket客户端
 */
export function createRepositoryWebSocket(
  repositoryId: number,
  token?: string
): WebSocketClient {
  let url = `${WS_BASE_URL}/ws/repository/${repositoryId}`;
  if (token) {
    url += `?token=${encodeURIComponent(token)}`;
  }
  return new WebSocketClient({ url });
}

/**
 * 创建通知专用WebSocket客户端
 */
export function createNotificationWebSocket(token: string): WebSocketClient {
  const url = `${WS_BASE_URL}/ws/notifications?token=${encodeURIComponent(token)}`;
  return new WebSocketClient({ url });
}
