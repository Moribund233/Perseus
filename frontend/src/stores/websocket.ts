/**
 * WebSocket状态管理 (Pinia Store)
 *
 * 集中管理WebSocket连接状态和消息
 */
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import type {
  WebSocketClient,
  WebSocketMessage,
} from '@/utils/websocket';

// 通知消息类型
export interface NotificationMessage {
  id: string;
  type: 'commit_new' | 'branch_update' | 'sync_event' | 'system' | 'error';
  title: string;
  message: string;
  repositoryId?: number;
  data?: any;
  timestamp: string;
  read: boolean;
}

// 同步状态类型
export interface SyncStatus {
  repositoryId: number;
  status: 'idle' | 'running' | 'completed' | 'failed';
  progress: number;
  message: string;
  details?: any;
}

// 进度信息类型
export interface ProgressInfo {
  operationId: string;
  operationType: string;
  progress: number;
  status: 'running' | 'completed' | 'failed';
  message: string;
  details?: any;
}

export const useWebSocketStore = defineStore('websocket', () => {
  // ==================== State ====================
  const client = ref<WebSocketClient | null>(null);
  const isConnected = ref(false);
  const isAuthenticated = ref(false);
  const connectionId = ref<string | null>(null);

  // 通知列表
  const notifications = ref<NotificationMessage[]>([]);
  const unreadCount = computed(
    () => notifications.value.filter((n) => !n.read).length
  );

  // 同步状态
  const syncStatuses = ref<Map<number, SyncStatus>>(new Map());

  // 进度信息
  const progressMap = ref<Map<string, ProgressInfo>>(new Map());

  // 订阅的仓库列表
  const subscribedRepositories = ref<Set<number>>(new Set());

  // ==================== Getters ====================
  const getSyncStatus = computed(
    () => (repositoryId: number) =>
      syncStatuses.value.get(repositoryId) ?? {
        repositoryId,
        status: 'idle',
        progress: 0,
        message: '',
      }
  );

  const getProgress = computed(
    () => (operationId: string) => progressMap.value.get(operationId)
  );

  const getRepositoryNotifications = computed(
    () => (repositoryId: number) =>
      notifications.value.filter((n) => n.repositoryId === repositoryId)
  );

  // ==================== Actions ====================

  /**
   * 初始化WebSocket连接
   */
  async function initConnection(token?: string) {
    // 如果已有连接，先关闭
    if (client.value) {
      client.value.close();
    }

    // 从环境变量获取 WebSocket 基础 URL
    const wsBaseUrl = import.meta.env.VITE_WS_BASE_URL;

    // 创建新连接，传入事件处理器
    const wsConfig = {
      url: token
        ? `${wsBaseUrl}/ws/?token=${encodeURIComponent(token)}`
        : `${wsBaseUrl}/ws/`,
      onOpen: () => {
        isConnected.value = true;
        console.log('[WebSocketStore] 连接已建立');
      },
      onClose: () => {
        isConnected.value = false;
        isAuthenticated.value = false;
        connectionId.value = null;
        console.log('[WebSocketStore] 连接已关闭');
      },
      onError: (error: Event) => {
        console.error('[WebSocketStore] 连接错误:', error);
      },
    };

    const { WebSocketClient } = await import('@/utils/websocket');
    client.value = new WebSocketClient(wsConfig);

    // 注册消息处理器
    setupMessageHandlers();

    // 建立连接
    client.value.connect();
  }

  /**
   * 设置消息处理器
   */
  function setupMessageHandlers() {
    if (!client.value) return;

    // 处理连接成功消息
    client.value.on('connected', (message: WebSocketMessage) => {
      connectionId.value = message.connection_id;
      isAuthenticated.value = message.authenticated || false;
      console.log('[WebSocketStore] 连接成功:', message.message);
    });

    // 处理通知消息
    client.value.on('notification', (message: WebSocketMessage) => {
      const notification: NotificationMessage = {
        id: `${Date.now()}-${Math.random()}`,
        type: message.action || 'system',
        title: getNotificationTitle(message.action),
        message: message.data?.message || JSON.stringify(message.data),
        repositoryId: message.repository_id,
        data: message.data,
        timestamp: message.timestamp || new Date().toISOString(),
        read: false,
      };
      notifications.value.unshift(notification);

      // 限制通知数量
      if (notifications.value.length > 100) {
        notifications.value = notifications.value.slice(0, 100);
      }
    });

    // 处理用户通知
    client.value.on('user_notification', (message: WebSocketMessage) => {
      const notification: NotificationMessage = {
        id: `${Date.now()}-${Math.random()}`,
        type: message.notification_type || 'system',
        title: getNotificationTitle(message.notification_type),
        message: message.data?.message || JSON.stringify(message.data),
        data: message.data,
        timestamp: message.timestamp || new Date().toISOString(),
        read: false,
      };
      notifications.value.unshift(notification);
    });

    // 处理同步状态更新
    client.value.on('sync_status_update', (message: WebSocketMessage) => {
      const status: SyncStatus = {
        repositoryId: message.repository_id,
        status: message.status,
        progress: message.progress || 0,
        message: message.message || '',
        details: message.details,
      };
      syncStatuses.value.set(message.repository_id, status);
    });

    // 处理同步事件
    client.value.on('sync_event', (message: WebSocketMessage) => {
      const status: SyncStatus = {
        repositoryId: message.repository_id,
        status:
          message.action === 'completed'
            ? 'completed'
            : message.action === 'failed'
            ? 'failed'
            : 'running',
        progress: message.action === 'completed' ? 100 : 0,
        message: message.result?.message || message.error || '',
        details: message.result,
      };
      syncStatuses.value.set(message.repository_id, status);
    });

    // 处理进度更新
    client.value.on('progress', (message: WebSocketMessage) => {
      const progress: ProgressInfo = {
        operationId: message.operation_id,
        operationType: message.operation_type,
        progress: message.progress,
        status: message.status,
        message: message.message || '',
        details: message.details,
      };
      progressMap.value.set(message.operation_id, progress);

      // 清理已完成的进度
      if (message.status === 'completed' || message.status === 'failed') {
        setTimeout(() => {
          progressMap.value.delete(message.operation_id);
        }, 5000);
      }
    });

    // 处理订阅确认
    client.value.on('subscribed', (message: WebSocketMessage) => {
      if (
        message.channel === 'repository' &&
        message.repository_id
      ) {
        subscribedRepositories.value.add(message.repository_id);
        console.log(
          `[WebSocketStore] 已订阅仓库 ${message.repository_id}`
        );
      }
    });

    // 处理取消订阅确认
    client.value.on('unsubscribed', (message: WebSocketMessage) => {
      if (
        message.channel === 'repository' &&
        message.repository_id
      ) {
        subscribedRepositories.value.delete(message.repository_id);
      }
    });

    // 处理错误
    client.value.on('error', (message: WebSocketMessage) => {
      console.error('[WebSocketStore] 收到错误:', message.error);
      const notification: NotificationMessage = {
        id: `${Date.now()}-${Math.random()}`,
        type: 'error',
        title: 'WebSocket错误',
        message: message.error || '未知错误',
        timestamp: new Date().toISOString(),
        read: false,
      };
      notifications.value.unshift(notification);
    });
  }

  /**
   * 获取通知标题
   */
  function getNotificationTitle(action: string): string {
    const titles: Record<string, string> = {
      commit_new: '新提交',
      branch_update: '分支更新',
      sync_started: '同步开始',
      sync_completed: '同步完成',
      sync_failed: '同步失败',
      system: '系统通知',
    };
    return titles[action] || '通知';
  }

  /**
   * 订阅仓库
   */
  function subscribeRepository(repositoryId: number): boolean {
    if (!client.value) {
      console.warn('[WebSocketStore] WebSocket未连接');
      return false;
    }
    return client.value.subscribeRepository(repositoryId);
  }

  /**
   * 取消订阅仓库
   */
  function unsubscribeRepository(repositoryId: number): boolean {
    if (!client.value) return false;
    return client.value.unsubscribeRepository(repositoryId);
  }

  /**
   * 标记通知为已读
   */
  function markNotificationAsRead(notificationId: string) {
    const notification = notifications.value.find(
      (n) => n.id === notificationId
    );
    if (notification) {
      notification.read = true;
    }
  }

  /**
   * 标记所有通知为已读
   */
  function markAllNotificationsAsRead() {
    notifications.value.forEach((n) => (n.read = true));
  }

  /**
   * 清除所有通知
   */
  function clearNotifications() {
    notifications.value = [];
  }

  /**
   * 关闭连接
   */
  function closeConnection() {
    if (client.value) {
      client.value.close();
      client.value = null;
    }
    isConnected.value = false;
    isAuthenticated.value = false;
    connectionId.value = null;
    subscribedRepositories.value.clear();
  }

  /**
   * 发送消息
   */
  function sendMessage(message: WebSocketMessage): boolean {
    if (!client.value) {
      console.warn('[WebSocketStore] WebSocket未连接');
      return false;
    }
    return client.value.send(message);
  }

  return {
    // State
    client,
    isConnected,
    isAuthenticated,
    connectionId,
    notifications,
    syncStatuses,
    progressMap,
    subscribedRepositories,

    // Getters
    unreadCount,
    getSyncStatus,
    getProgress,
    getRepositoryNotifications,

    // Actions
    initConnection,
    subscribeRepository,
    unsubscribeRepository,
    markNotificationAsRead,
    markAllNotificationsAsRead,
    clearNotifications,
    closeConnection,
    sendMessage,
  };
});
