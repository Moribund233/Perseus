/**
 * 全局日志管理 Store（简化版）
 *
 * 通过 Tauri 后端代理 WebSocket 连接
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  initLogWebSocket,
  connectLogWebSocket,
  disconnectLogWebSocket,
  subscribeLogs,
  unsubscribeLogs,
  onStateChange,
  onLog,
  onHistory,
  onError,
  cleanupListeners,
  type LogEntry,
  type LogFilters,
  ConnectionState
} from '../services/logService'
import { isServiceRunning } from '../services/api'

export const useLogStore = defineStore('logs', () => {
  // ============ State ============
  /** 连接状态 */
  const connectionState = ref<ConnectionState>(ConnectionState.Disconnected)
  /** 所有日志条目 */
  const allLogs = ref<LogEntry[]>([])
  /** 总日志计数器 */
  const totalLogCount = ref(0)
  /** 最近的日志条目 */
  const recentLogs = ref<LogEntry[]>([])
  /** 未读错误/警告数量 */
  const unreadErrorCount = ref(0)
  /** 连接错误信息 */
  const connectionError = ref<string | null>(null)
  /** 是否已初始化 */
  const isInitialized = ref(false)

  // 缓冲区配置
  const MAX_LOGS_IN_MEMORY = 20000
  const LOGS_KEEP_AFTER_TRUNCATE = 15000

  // ============ Getters ============
  /** 是否已连接 */
  const isConnected = computed(() => {
    return connectionState.value === ConnectionState.Connected ||
           connectionState.value === ConnectionState.Subscribed
  })

  /** 是否正在连接 */
  const isConnecting = computed(() => {
    return connectionState.value === ConnectionState.Connecting
  })

  /** 是否有未读错误 */
  const hasUnreadErrors = computed(() => unreadErrorCount.value > 0)

  /** 最新的错误日志 */
  const latestError = computed(() => {
    return recentLogs.value.find(log =>
      log.level === 'ERROR' || log.level === 'CRITICAL'
    )
  })

  // ============ Actions ============

  /**
   * 初始化并连接到 WebSocket 日志服务
   */
  async function connect(serviceRunning: boolean = true): Promise<void> {
    // 如果没有传入服务状态，先检查服务是否运行
    if (!serviceRunning) {
      serviceRunning = await isServiceRunning()
    }

    if (!serviceRunning) {
      connectionError.value = '服务未运行'
      return
    }

    if (isConnected.value || isConnecting.value) {
      return
    }

    try {
      connectionError.value = null

      // 初始化管理器
      if (!isInitialized.value) {
        await initLogWebSocket()
        isInitialized.value = true

        // 注册事件监听（只注册一次）
        await setupEventListeners()
      }

      // 连接（后端会自动检查服务健康状态）
      await connectLogWebSocket()

      // 订阅日志
      const filters: LogFilters = {
        levels: ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
      }

      await subscribeLogs({
        filters,
        historyCount: 100
      })

      console.log('WebSocket 日志连接已建立')
    } catch (err) {
      console.error('WebSocket 日志连接失败:', err)
      connectionError.value = '日志连接失败'
    }
  }

  /**
   * 设置事件监听器
   */
  async function setupEventListeners(): Promise<void> {
    // 状态变化监听
    await onStateChange((state) => {
      connectionState.value = state
    })

    // 新日志监听
    await onLog((entry) => {
      handleNewLog(entry)
    })

    // 历史日志监听
    await onHistory((logs) => {
      // 去重后添加到 allLogs
      const existingKeys = new Set(allLogs.value.map(l => `${l.timestamp}-${l.message}`))
      const newLogs = logs.filter(l => !existingKeys.has(`${l.timestamp}-${l.message}`))

      if (newLogs.length > 0) {
        allLogs.value.push(...newLogs)
        totalLogCount.value += newLogs.length

        // 限制内存中的日志数量
        if (allLogs.value.length > MAX_LOGS_IN_MEMORY) {
          allLogs.value = allLogs.value.slice(-LOGS_KEEP_AFTER_TRUNCATE)
        }
      }

      recentLogs.value = logs.slice(-20)
    })

    // 错误监听
    await onError((errMsg) => {
      connectionError.value = errMsg
      console.warn('WebSocket 日志连接错误:', errMsg)
    })
  }

  /**
   * 断开 WebSocket 连接
   */
  async function disconnect(): Promise<void> {
    await unsubscribeLogs()
    await disconnectLogWebSocket()
    connectionState.value = ConnectionState.Disconnected
  }

  /**
   * 处理新日志条目
   */
  function handleNewLog(entry: LogEntry): void {
    // 添加到所有日志
    allLogs.value.push(entry)
    totalLogCount.value++

    // 限制内存中的日志数量
    if (allLogs.value.length > MAX_LOGS_IN_MEMORY) {
      allLogs.value = allLogs.value.slice(-LOGS_KEEP_AFTER_TRUNCATE)
    }

    // 添加到最近日志
    recentLogs.value.push(entry)
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
   * 清除所有日志
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
    await disconnect()
    await connect(serviceRunning)
  }

  /**
   * 清理资源（应用退出时调用）
   */
  function cleanup(): void {
    cleanupListeners()
    disconnect()
  }

  return {
    // State
    connectionState,
    allLogs,
    totalLogCount,
    recentLogs,
    unreadErrorCount,
    connectionError,
    isInitialized,
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
    cleanup
  }
})
