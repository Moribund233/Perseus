<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import Alert from '../components/Alert.vue'
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

// 图标路径
const searchIcon = new URL('../assets/icons/search.svg', import.meta.url).href
const refreshIcon = new URL('../assets/icons/refresh.svg', import.meta.url).href
const chevronDownIcon = new URL('../assets/icons/chevron-down.svg', import.meta.url).href
const downloadIcon = new URL('../assets/icons/download.svg', import.meta.url).href
const trashIcon = new URL('../assets/icons/trash.svg', import.meta.url).href
const logIcon = new URL('../assets/icons/log.svg', import.meta.url).href

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
    <Alert v-if="!isServiceRunningStatus" type="info">
      服务未启动，请前往控制台启动服务以查看日志
    </Alert>

    <!-- 错误提示 -->
    <Alert
      v-else-if="error"
      type="error"
      closable
      @close="error = null"
    >
      {{ error }}
    </Alert>

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
          <img :src="searchIcon" class="search-icon" alt="search" />
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
          <img :src="refreshIcon" class="btn-icon" alt="refresh" />
          刷新
        </button>

        <button class="btn btn-secondary btn-sm" @click="scrollToBottom">
          <img :src="chevronDownIcon" class="btn-icon" alt="bottom" />
          底部
        </button>

        <button class="btn btn-secondary btn-sm" @click="exportLogs" :disabled="logEntries.length === 0">
          <img :src="downloadIcon" class="btn-icon" alt="download" />
          导出
        </button>

        <button class="btn btn-secondary btn-sm" @click="clearDisplay" :disabled="logEntries.length === 0">
          <img :src="trashIcon" class="btn-icon" alt="clear" />
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
        <img :src="logIcon" class="empty-icon" alt="empty" />
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

/* 页面标题 */
.page-title {
  flex-shrink: 0;
}

/* 工具栏 */
.toolbar {
  margin-bottom: var(--spacing-md);
  flex-shrink: 0;
}

.input-sm {
  padding: var(--spacing-xs) var(--spacing-sm);
  font-size: var(--font-size-sm);
  min-width: 100px;
}

.search-group {
  flex: 1;
  min-width: 200px;
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

.btn-icon {
  width: 14px;
  height: 14px;
}

/* WebSocket 状态样式 */
.ws-status {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  font-size: var(--font-size-sm);
  font-weight: 500;
}

.status-disconnected .status-dot {
  background-color: var(--text-tertiary);
}

.status-connecting .status-dot {
  background-color: var(--warning-color);
  animation: pulse 1.5s ease-in-out infinite;
}

.status-connected .status-dot {
  background-color: var(--success-color);
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

/* 日志统计 */
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

/* 日志容器 */
.log-container {
  flex: 1;
  overflow-y: auto;
  padding: 0;
}

/* 加载状态 */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-xl);
  color: var(--text-tertiary);
}

.loading-state .spinner {
  width: 24px;
  height: 24px;
  margin-bottom: var(--spacing-sm);
}

/* 日志条目 */
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
  color: var(--text-tertiary);
  white-space: nowrap;
  min-width: 140px;
}

.log-logger {
  color: var(--text-secondary);
  white-space: nowrap;
}

.log-message {
  color: var(--text-primary);
  word-break: break-all;
  flex: 1;
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
</style>
