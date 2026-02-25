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
  // 所有日志条目（跨页面保持）
  const allLogs = ref<LogEntry[]>([])
  // 总日志计数器（不受截断影响）
  const totalLogCount = ref(0)
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
  // 监听器取消函数
  const unsubscribeHandlers = ref<(() => void)[]>([])

  // 缓冲区配置
  const MAX_LOGS_IN_MEMORY = 20000  // 内存中最大日志数
  const LOGS_KEEP_AFTER_TRUNCATE = 15000  // 截断后保留的日志数

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

      // 先取消之前的监听器（防止重复注册）
      unsubscribeHandlers.value.forEach(unsub => unsub())
      unsubscribeHandlers.value = []

      // 注册状态监听
      const unsubState = wsClient.onStateChange((state) => {
        connectionState.value = state
      })
      unsubscribeHandlers.value.push(unsubState)

      // 注册日志消息监听
      const unsubLog = wsClient.onLog((entry) => {
        handleNewLog(entry)
      })
      unsubscribeHandlers.value.push(unsubLog)

      // 注册历史日志监听
      const unsubHistory = wsClient.onHistory((logs) => {
        // 将历史日志添加到 allLogs（切换页面时能够显示历史日志）
        // 使用 message + timestamp 组合作为唯一标识去重
        const existingKeys = new Set(allLogs.value.map(l => `${l.timestamp}-${l.message}`))
        const newLogs = logs.filter(l => !existingKeys.has(`${l.timestamp}-${l.message}`))
        if (newLogs.length > 0) {
          allLogs.value.push(...newLogs)
          // 限制总数量
          if (allLogs.value.length > MAX_LOGS_IN_MEMORY) {
            allLogs.value = allLogs.value.slice(-LOGS_KEEP_AFTER_TRUNCATE)
          }
          // 更新计数器
          totalLogCount.value += newLogs.length
        }
        recentLogs.value = logs.slice(-20)
      })
      unsubscribeHandlers.value.push(unsubHistory)

      // 注册错误监听
      const unsubError = wsClient.onError((errMsg) => {
        connectionError.value = errMsg
        console.warn('WebSocket 日志连接错误:', errMsg)
      })
      unsubscribeHandlers.value.push(unsubError)

      // 连接
      await wsClient.connect()

      // 订阅日志（订阅所有级别，用于全局日志收集）
      const filters: LogFilters = {
        levels: ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
      }

      wsClient.subscribe({
        filters,
        historyCount: 100  // 获取最近100条历史日志
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
    // 取消所有监听器
    unsubscribeHandlers.value.forEach(unsub => unsub())
    unsubscribeHandlers.value = []

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
    // 添加到所有日志（跨页面保持）
    allLogs.value.push(entry)
    totalLogCount.value++

    // 限制内存中的日志数量
    if (allLogs.value.length > MAX_LOGS_IN_MEMORY) {
      allLogs.value = allLogs.value.slice(-LOGS_KEEP_AFTER_TRUNCATE)
    }

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
   * 清除所有日志（包括跨页面保持的日志）
   */
  function clearAllLogs(): void {
    allLogs.value = []
    totalLogCount.value = 0
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
    allLogs,
    totalLogCount,
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
    clearRecentLogs,
    clearAllLogs,
    handleNewLog
  }
})
