/**
 * 全局日志管理 Store
 *
 * 管理 WebSocket 日志连接，实现客户端启动后自动连接日志接口
 * 支持全局日志监听和通知
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  getWebSocketLogClient,
  type LogEntry,
  type LogFilters,
  LogClientState
} from '../services/websocketLog'

/**
 * 日志通知条目
 */
export interface LogNotification {
  id: string
  timestamp: string
  level: string
  message: string
  logger: string
}

export const useLogStore = defineStore('logs', () => {
  // ============ State ============
  // WebSocket 客户端
  const wsClient = getWebSocketLogClient()
  // 连接状态
  const connectionState = ref<LogClientState>(LogClientState.DISCONNECTED)
  // 最近的日志条目（用于全局通知）
  const recentLogs = ref<LogEntry[]>([])
  // 未读错误/警告数量
  const unreadErrorCount = ref(0)
  // 是否已初始化
  const isInitialized = ref(false)
  // 是否启用自动连接
  const autoConnectEnabled = ref(true)
  // 连接错误信息
  const connectionError = ref<string | null>(null)

  // ============ Getters ============
  // 是否已连接
  const isConnected = computed(() => {
    return connectionState.value === LogClientState.CONNECTED ||
           connectionState.value === LogClientState.SUBSCRIBED
  })

  // 是否正在连接
  const isConnecting = computed(() => {
    return connectionState.value === LogClientState.CONNECTING
  })

  // 是否有未读错误
  const hasUnreadErrors = computed(() => unreadErrorCount.value > 0)

  // 最新的错误日志
  const latestError = computed(() => {
    return recentLogs.value.find(log =>
      log.level === 'ERROR' || log.level === 'CRITICAL'
    )
  })

  // ============ Actions ============
  /**
   * 连接到 WebSocket 日志服务
   * @param serviceRunning 服务是否运行
   */
  async function connect(serviceRunning: boolean = true): Promise<void> {
    if (!serviceRunning) {
      connectionError.value = '服务未运行'
      return
    }

    if (isConnected.value || isConnecting.value) {
      return
    }

    try {
      connectionError.value = null

      // 注册状态监听
      wsClient.onStateChange((state) => {
        connectionState.value = state
      })

      // 注册日志消息监听
      wsClient.onLog((entry) => {
        handleNewLog(entry)
      })

      // 注册历史日志监听
      wsClient.onHistory((logs) => {
        // 只保留最近的日志用于通知
        recentLogs.value = logs.slice(-20)
      })

      // 注册错误监听
      wsClient.onError((errMsg) => {
        connectionError.value = errMsg
        console.warn('WebSocket 日志连接错误:', errMsg)
      })

      // 连接
      await wsClient.connect()

      // 订阅日志（只订阅 ERROR 和 WARNING，减少流量）
      const filters: LogFilters = {
        levels: ['ERROR', 'WARNING', 'CRITICAL']
      }

      wsClient.subscribe({
        filters,
        historyCount: 10  // 只获取最近10条
      })

      isInitialized.value = true
      console.log('WebSocket 日志连接已建立')
    } catch (err) {
      console.error('WebSocket 日志连接失败:', err)
      connectionError.value = '日志连接失败'
    }
  }

  /**
   * 断开 WebSocket 连接
   */
  function disconnect(): void {
    if (wsClient.isConnected()) {
      wsClient.unsubscribe()
      wsClient.disconnect()
    }
    connectionState.value = LogClientState.DISCONNECTED
    isInitialized.value = false
  }

  /**
   * 处理新日志条目
   */
  function handleNewLog(entry: LogEntry): void {
    // 添加到最近日志
    recentLogs.value.push(entry)
    // 限制数量
    if (recentLogs.value.length > 50) {
      recentLogs.value = recentLogs.value.slice(-30)
    }

    // 如果是错误或警告，增加未读计数
    if (entry.level === 'ERROR' || entry.level === 'CRITICAL' || entry.level === 'WARNING') {
      unreadErrorCount.value++
    }
  }

  /**
   * 清除未读错误计数
   */
  function clearUnreadErrors(): void {
    unreadErrorCount.value = 0
  }

  /**
   * 清除最近日志
   */
  function clearRecentLogs(): void {
    recentLogs.value = []
    unreadErrorCount.value = 0
  }

  /**
   * 重新连接
   */
  async function reconnect(serviceRunning: boolean = true): Promise<void> {
    disconnect()
    await connect(serviceRunning)
  }

  return {
    // State
    connectionState,
    recentLogs,
    unreadErrorCount,
    isInitialized,
    autoConnectEnabled,
    connectionError,
    // Getters
    isConnected,
    isConnecting,
    hasUnreadErrors,
    latestError,
    // Actions
    connect,
    disconnect,
    reconnect,
    clearUnreadErrors,
    clearRecentLogs
  }
})
