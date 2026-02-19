<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import {
  isServiceRunning
} from '../services/api'
import {
  getWebSocketLogClient,
  type LogEntry,
  type LogFilters,
  LogClientState
} from '../services/websocketLog'

/**
 * 日志级别类型
 */
type LogLevel = 'info' | 'warn' | 'error' | 'debug' | 'all'

// 日志数据
const logEntries = ref<LogEntry[]>([])
const selectedLevel = ref<LogLevel>('all')
const searchQuery = ref('')
const linesCount = ref(100)
const error = ref<string | null>(null)
const isServiceRunningStatus = ref<boolean>(false)
const wsState = ref<LogClientState>(LogClientState.DISCONNECTED)

// WebSocket 客户端
const wsClient = getWebSocketLogClient()

// 批量更新相关
const pendingLogs = ref<LogEntry[]>([])
let batchUpdateTimer: number | null = null
const BATCH_INTERVAL = 100 // 批量更新间隔（毫秒）

// 执行批量更新
const flushPendingLogs = () => {
  if (pendingLogs.value.length === 0) return
  
  const newEntries = pendingLogs.value
  pendingLogs.value = []
  
  // 使用 requestAnimationFrame 优化渲染
  requestAnimationFrame(() => {
    logEntries.value.push(...newEntries)
    // 限制内存中的日志数量
    if (logEntries.value.length > 5000) {
      logEntries.value = logEntries.value.slice(-3000)
    }
  })
}

// 添加日志到待处理队列
const queueLogEntry = (entry: LogEntry) => {
  pendingLogs.value.push(entry)
  
  // 如果队列太长，立即刷新
  if (pendingLogs.value.length >= 50) {
    flushPendingLogs()
  }
}

// 启动批量更新定时器
const startBatchTimer = () => {
  if (batchUpdateTimer) return
  batchUpdateTimer = window.setInterval(() => {
    flushPendingLogs()
  }, BATCH_INTERVAL)
}

// 停止批量更新定时器
const stopBatchTimer = () => {
  if (batchUpdateTimer) {
    clearInterval(batchUpdateTimer)
    batchUpdateTimer = null
  }
  // 刷新剩余日志
  flushPendingLogs()
}

// 日志级别配置
const logLevels: { value: LogLevel; label: string; class: string }[] = [
  { value: 'all', label: '全部', class: '' },
  { value: 'info', label: '信息', class: 'tag-info' },
  { value: 'warn', label: '警告', class: 'tag-warning' },
  { value: 'error', label: '错误', class: 'tag-error' },
  { value: 'debug', label: '调试', class: 'tag-secondary' }
]



/**
 * 日志级别匹配映射
 * 将前端选择的级别映射到服务端可能的级别值
 */
const levelMatchMap: Record<string, string[]> = {
  'info': ['info'],
  'warn': ['warn', 'warning'],
  'error': ['error'],
  'debug': ['debug']
}

// 过滤后的日志条目
const filteredLogEntries = computed(() => {
  let entries = logEntries.value

  // 级别过滤
  if (selectedLevel.value !== 'all') {
    const validLevels = levelMatchMap[selectedLevel.value] || [selectedLevel.value]
    entries = entries.filter(entry =>
      validLevels.includes(entry.level.toLowerCase())
    )
  }

  // 搜索过滤
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    entries = entries.filter(entry =>
      entry.message.toLowerCase().includes(query) ||
      entry.logger.toLowerCase().includes(query)
    )
  }

  // 限制行数
  if (entries.length > linesCount.value) {
    entries = entries.slice(-linesCount.value)
  }

  return entries
})

// WebSocket 状态文本
const wsStateText = computed(() => {
  switch (wsState.value) {
    case LogClientState.DISCONNECTED:
      return '未连接'
    case LogClientState.CONNECTING:
      return '连接中...'
    case LogClientState.CONNECTED:
      return '已连接'
    case LogClientState.SUBSCRIBED:
      return '实时接收中'
    case LogClientState.ERROR:
      return '连接错误'
    default:
      return '未知'
  }
})

// WebSocket 状态样式类
const wsStateClass = computed(() => {
  switch (wsState.value) {
    case LogClientState.DISCONNECTED:
      return 'status-disconnected'
    case LogClientState.CONNECTING:
      return 'status-connecting'
    case LogClientState.CONNECTED:
    case LogClientState.SUBSCRIBED:
      return 'status-connected'
    case LogClientState.ERROR:
      return 'status-error'
    default:
      return ''
  }
})

/**
 * 获取日志级别样式类
 */
const getLevelClass = (level: string): string => {
  const classMap: Record<string, string> = {
    info: 'log-info',
    warn: 'log-warn',
    warning: 'log-warn',
    error: 'log-error',
    debug: 'log-debug',
    critical: 'log-error'
  }
  return classMap[level.toLowerCase()] || 'log-info'
}

/**
 * 获取日志级别标签类
 */
const getLevelTagClass = (level: string): string => {
  const classMap: Record<string, string> = {
    info: 'tag-info',
    warn: 'tag-warning',
    warning: 'tag-warning',
    error: 'tag-error',
    debug: 'tag-secondary',
    critical: 'tag-error'
  }
  return classMap[level.toLowerCase()] || 'tag-info'
}

/**
 * 检查服务状态
 */
const checkServiceStatus = async (): Promise<void> => {
  isServiceRunningStatus.value = await isServiceRunning()
}

/**
 * 连接到 WebSocket 日志服务
 * @param loadHistory 是否加载历史日志，默认为 true
 */
const connectWebSocket = async (loadHistory: boolean = true) => {
  if (!isServiceRunningStatus.value) {
    return
  }

  try {
    // 注册状态监听
    wsClient.onStateChange((state) => {
      wsState.value = state
    })

    // 注册日志消息监听（使用批量更新）
    wsClient.onLog((entry) => {
      queueLogEntry(entry)
    })

    // 注册历史日志监听
    wsClient.onHistory((logs) => {
      if (loadHistory) {
        logEntries.value = logs
      }
    })

    // 注册错误监听
    wsClient.onError((errMsg) => {
      error.value = errMsg
    })

    // 连接
    await wsClient.connect()

    // 启动批量更新定时器
    startBatchTimer()

    // 订阅日志
    const filters: LogFilters = {
      levels: selectedLevel.value === 'all'
        ? ['DEBUG', 'INFO', 'WARNING', 'ERROR']
        : [selectedLevel.value.toUpperCase()]
    }

    wsClient.subscribe({
      filters,
      historyCount: loadHistory ? linesCount.value : 0
    })
  } catch (err) {
    console.error('WebSocket 连接失败:', err)
    error.value = '实时日志连接失败，请检查服务状态'
  }
}

/**
 * 断开 WebSocket 连接
 */
const disconnectWebSocket = () => {
  stopBatchTimer()
  wsClient.unsubscribe()
  wsClient.disconnect()
}

/**
 * 刷新日志
 * 清空当前日志并重新连接，不加载历史日志
 */
const refreshLogs = async (): Promise<void> => {
  await checkServiceStatus()

  if (isServiceRunningStatus.value) {
    // 清空当前日志显示
    logEntries.value = []

    // 重新连接 WebSocket，不加载历史日志
    disconnectWebSocket()
    await connectWebSocket(false)
  }
}

/**
 * 重新连接 WebSocket
 * 清空当前日志并重新连接，不加载历史日志
 */
const reconnectWebSocket = async () => {
  logEntries.value = []
  disconnectWebSocket()
  await connectWebSocket(false)
}

/**
 * 清空日志显示
 */
const clearDisplay = (): void => {
  logEntries.value = []
}

/**
 * 导出日志
 */
const exportLogs = (): void => {
  if (logEntries.value.length === 0) return

  const content = logEntries.value
    .map(entry => `[${entry.timestamp}] [${entry.level}] ${entry.logger}: ${entry.message}`)
    .join('\n')

  const blob = new Blob([content], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `logs_${new Date().toISOString().slice(0, 10)}.log`
  a.click()
  URL.revokeObjectURL(url)
}



/**
 * 滚动到底部
 */
const scrollToBottom = (): void => {
  const container = document.querySelector('.log-container')
  if (container) {
    container.scrollTop = container.scrollHeight
  }
}

onMounted(() => {
  refreshLogs()
})

onUnmounted(() => {
  disconnectWebSocket()
})
</script>

<template>
  <div class="log-page">
    <h1 class="page-title">日志</h1>

    <!-- 服务未启动提示 -->
    <div v-if="!isServiceRunningStatus" class="info-alert">
      <svg class="info-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10"/>
        <line x1="12" y1="16" x2="12" y2="12"/>
        <line x1="12" y1="8" x2="12.01" y2="8"/>
      </svg>
      <span>服务未启动，请前往控制台启动服务以查看日志</span>
    </div>

    <!-- 错误提示 -->
    <div v-else-if="error" class="error-alert">
      <svg class="error-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10"/>
        <line x1="12" y1="8" x2="12" y2="12"/>
        <line x1="12" y1="16" x2="12.01" y2="16"/>
      </svg>
      <span>{{ error }}</span>
      <button class="close-btn" @click="error = null">×</button>
    </div>

    <!-- 工具栏 -->
    <div class="toolbar card">
      <!-- WebSocket 状态 -->
      <div class="toolbar-group">
        <label class="toolbar-label">连接状态</label>
        <div class="ws-status" :class="wsStateClass">
          <span class="status-dot"></span>
          <span>{{ wsStateText }}</span>
        </div>
      </div>

      <!-- 重新连接按钮 -->
      <div class="toolbar-group">
        <button class="btn btn-sm" @click="reconnectWebSocket" :disabled="wsState === LogClientState.CONNECTING">
          {{ wsState === LogClientState.CONNECTING ? '连接中...' : '重新连接' }}
        </button>
      </div>

      <!-- 级别过滤 -->
      <div class="toolbar-group">
        <label class="toolbar-label">级别</label>
        <div class="filter-group">
          <button
            v-for="level in logLevels"
            :key="level.value"
            class="filter-btn"
            :class="{ active: selectedLevel === level.value }"
            @click="selectedLevel = level.value"
          >
            {{ level.label }}
          </button>
        </div>
      </div>

      <!-- 搜索 -->
      <div class="toolbar-group search-group">
        <label class="toolbar-label">搜索</label>
        <div class="search-box">
          <svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="8"/>
            <path d="M21 21l-4.35-4.35"/>
          </svg>
          <input
            v-model="searchQuery"
            type="text"
            class="input input-sm"
            placeholder="搜索日志内容..."
          />
        </div>
      </div>

      <!-- 行数选择 -->
      <div class="toolbar-group">
        <label class="toolbar-label">显示行数</label>
        <select v-model="linesCount" class="input input-sm">
          <option :value="50">50</option>
          <option :value="100">100</option>
          <option :value="200">200</option>
          <option :value="500">500</option>
        </select>
      </div>

      <!-- 操作按钮 -->
      <div class="toolbar-group actions">
        <button class="btn btn-secondary btn-sm" @click="refreshLogs">
          <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="23 4 23 10 17 10"/>
            <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
          </svg>
          刷新
        </button>

        <button class="btn btn-secondary btn-sm" @click="scrollToBottom">
          <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="6 9 12 15 18 9"/>
          </svg>
          底部
        </button>

        <button class="btn btn-secondary btn-sm" @click="exportLogs" :disabled="logEntries.length === 0">
          <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="7 10 12 15 17 10"/>
            <line x1="12" y1="15" x2="12" y2="3"/>
          </svg>
          导出
        </button>

        <button class="btn btn-secondary btn-sm" @click="clearDisplay" :disabled="logEntries.length === 0">
          <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="3 6 5 6 21 6"/>
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
          </svg>
          清空
        </button>
      </div>
    </div>

    <!-- 日志统计 -->
    <div class="log-stats card">
      <span>总条目: {{ logEntries.length }}</span>
      <span>显示: {{ filteredLogEntries.length }}</span>
      <span v-if="wsState === LogClientState.SUBSCRIBED" class="tag tag-success">实时</span>
      <span v-else class="tag tag-warning">静态</span>
    </div>

    <!-- 日志列表 -->
    <div class="log-container card">
      <div v-if="filteredLogEntries.length === 0" class="empty-state">
        <svg class="empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
          <polyline points="14 2 14 8 20 8"/>
          <line x1="16" y1="13" x2="8" y2="13"/>
          <line x1="16" y1="17" x2="8" y2="17"/>
          <polyline points="10 9 9 9 8 9"/>
        </svg>
        <p>暂无日志</p>
      </div>

      <div
        v-for="(entry, index) in filteredLogEntries"
        :key="index"
        class="log-item"
        :class="getLevelClass(entry.level)"
      >
        <span class="log-time">{{ entry.timestamp }}</span>
        <span class="tag" :class="getLevelTagClass(entry.level)">
          {{ entry.level.toUpperCase() }}
        </span>
        <span class="log-logger">[{{ entry.logger }}]</span>
        <span class="log-message">{{ entry.message }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.log-page {
  max-width: 1400px;
  height: calc(100vh - var(--spacing-lg) * 2);
  display: flex;
  flex-direction: column;
}

.page-title {
  font-size: var(--font-size-2xl);
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: var(--spacing-lg);
  flex-shrink: 0;
}

.info-alert {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-md);
  background-color: rgba(59, 130, 246, 0.1);
  border: 1px solid var(--primary-color);
  border-radius: var(--border-radius-md);
  color: var(--primary-color);
  margin-bottom: var(--spacing-md);
  flex-shrink: 0;
}

.info-icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
}

.error-alert {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-md);
  background-color: rgba(239, 68, 68, 0.1);
  border: 1px solid var(--error-color);
  border-radius: var(--border-radius-md);
  color: var(--error-color);
  margin-bottom: var(--spacing-md);
  flex-shrink: 0;
}

.error-icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
}

.close-btn {
  margin-left: auto;
  background: none;
  border: none;
  color: var(--error-color);
  font-size: 20px;
  cursor: pointer;
  padding: 0;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.toolbar {
  display: flex;
  align-items: flex-end;
  gap: var(--spacing-md);
  padding: var(--spacing-md);
  margin-bottom: var(--spacing-md);
  flex-wrap: wrap;
  flex-shrink: 0;
}

.toolbar-group {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.toolbar-label {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}

.input-sm {
  padding: var(--spacing-xs) var(--spacing-sm);
  font-size: var(--font-size-sm);
  min-width: 100px;
}

.filter-group {
  display: flex;
  gap: var(--spacing-xs);
}

.filter-btn {
  padding: var(--spacing-xs) var(--spacing-sm);
  background-color: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius-sm);
  color: var(--text-secondary);
  font-size: var(--font-size-sm);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.filter-btn:hover {
  background-color: var(--bg-tertiary);
  color: var(--text-primary);
}

.filter-btn.active {
  background-color: var(--primary-color);
  border-color: var(--primary-color);
  color: white;
}

.search-group {
  flex: 1;
  min-width: 200px;
}

.search-box {
  position: relative;
}

.search-icon {
  position: absolute;
  left: var(--spacing-sm);
  top: 50%;
  transform: translateY(-50%);
  width: 16px;
  height: 16px;
  color: var(--text-muted);
}

.search-box .input {
  padding-left: 32px;
}

.actions {
  flex-direction: row;
  align-items: center;
  margin-left: auto;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  color: var(--text-secondary);
  font-size: var(--font-size-sm);
  cursor: pointer;
}

.checkbox-label input[type="checkbox"] {
  width: 14px;
  height: 14px;
  accent-color: var(--primary-color);
}

.btn-sm {
  padding: var(--spacing-xs) var(--spacing-sm);
  font-size: var(--font-size-sm);
}

.btn-icon {
  width: 14px;
  height: 14px;
}

.btn-icon.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* WebSocket 状态样式 */
.ws-status {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  font-size: var(--font-size-sm);
  font-weight: 500;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: currentColor;
}

.status-disconnected {
  color: var(--text-muted);
}

.status-disconnected .status-dot {
  background-color: var(--text-muted);
}

.status-connecting {
  color: var(--warning-color);
}

.status-connecting .status-dot {
  background-color: var(--warning-color);
  animation: pulse 1.5s ease-in-out infinite;
}

.status-connected {
  color: var(--success-color);
}

.status-connected .status-dot {
  background-color: var(--success-color);
}

.status-error {
  color: var(--error-color);
}

.status-error .status-dot {
  background-color: var(--error-color);
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

.log-stats {
  display: flex;
  align-items: center;
  gap: var(--spacing-lg);
  padding: var(--spacing-sm) var(--spacing-md);
  margin-bottom: var(--spacing-md);
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  flex-shrink: 0;
}

.log-container {
  flex: 1;
  overflow-y: auto;
  padding: 0;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: var(--font-size-sm);
}

.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-xl);
  color: var(--text-muted);
}

.spinner {
  width: 24px;
  height: 24px;
  border: 2px solid var(--border-color);
  border-top-color: var(--primary-color);
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: var(--spacing-sm);
}

.empty-icon {
  width: 48px;
  height: 48px;
  margin-bottom: var(--spacing-md);
  opacity: 0.5;
}

.log-item {
  display: flex;
  align-items: flex-start;
  gap: var(--spacing-sm);
  padding: var(--spacing-xs) var(--spacing-md);
  border-bottom: 1px solid var(--border-color);
  transition: background-color var(--transition-fast);
}

.log-item:hover {
  background-color: var(--bg-secondary);
}

.log-item:last-child {
  border-bottom: none;
}

.log-time {
  color: var(--text-muted);
  white-space: nowrap;
  min-width: 140px;
  font-size: var(--font-size-sm);
}

.log-logger {
  color: var(--text-secondary);
  white-space: nowrap;
  font-size: var(--font-size-sm);
}

.log-message {
  color: var(--text-primary);
  word-break: break-all;
  flex: 1;
  font-size: var(--font-size-sm);
}

.log-item.log-warn .log-message {
  color: var(--warning-color);
}

.log-item.log-error .log-message {
  color: var(--error-color);
}

.log-item.log-debug .log-message {
  color: var(--text-secondary);
}

button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
