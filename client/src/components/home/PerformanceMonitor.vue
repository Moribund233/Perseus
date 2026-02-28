<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { storeToRefs } from 'pinia'
import { useServiceStore } from '../../stores'
import { useHomeEventBus } from '../../composables/useHomeEvents'
import { useDatabaseConnection } from '../../composables/useDatabaseConnection'
import { getRedisStatus, type RedisStatusResponse } from '../../services/api'

/**
 * 性能监控组件
 *
 * 功能：显示 CPU、内存、网络吞吐量的实时图表
 * 通信：通过事件总线与 Home 主组件交互
 */

// 使用 Pinia store
const serviceStore = useServiceStore()
const { localSystemInfo: storeLocalSystemInfo, isRunning: storeIsRunning, serviceStatus: storeServiceStatus } = storeToRefs(serviceStore)

// 使用事件总线
const eventBus = useHomeEventBus()
const performanceState = eventBus.state.value.performance

// 使用数据库连接 composable
const { state: dbConnectionState, badgeConfig: dbBadgeConfig, checkConnection: checkDbConnection } = useDatabaseConnection()

// Redis 状态
const redisStatus = ref<RedisStatusResponse | null>(null)
let redisCheckTimer: number | null = null

// 定时刷新数据库连接状态
let dbCheckTimer: number | null = null

// 数据库类型图标路径
const dbIcons: Record<string, string> = {
  sqlite: new URL('../../assets/icons/sqlite.svg', import.meta.url).href,
  postgresql: new URL('../../assets/icons/postgresql.svg', import.meta.url).href,
  mysql: new URL('../../assets/icons/mysql.svg', import.meta.url).href,
  default: new URL('../../assets/icons/database.svg', import.meta.url).href
}

// Redis 图标路径
const redisIcon = new URL('../../assets/icons/redis.svg', import.meta.url).href

/**
 * 获取当前数据库类型对应的图标
 */
const getDbIcon = (): string => {
  const dbType = dbConnectionState.value.dbType?.toLowerCase() || ''
  return dbIcons[dbType] || dbIcons.default
}

// 服务状态
const serviceStatus = computed(() => {
  return storeIsRunning.value ? 'running' : 'stopped'
})

// Redis 状态文本
const redisStatusText = computed(() => {
  if (!redisStatus.value?.is_loaded) {
    return '未载入'
  }
  switch (redisStatus.value.status) {
    case 'running':
      return '运行中'
    case 'stopped':
      return '已停止'
    case 'error':
      return '错误'
    default:
      return '未知'
  }
})

// Redis 状态样式类
const redisStatusClass = computed(() => {
  if (!redisStatus.value?.is_loaded) {
    return 'status-unloaded'
  }
  switch (redisStatus.value.status) {
    case 'running':
      return 'status-connected'
    case 'stopped':
      return 'status-disconnected'
    case 'error':
      return 'status-error'
    default:
      return 'status-unknown'
  }
})

// 上次网络字节数（用于计算速率）
let lastNetworkBytesSent = 0
let lastNetworkBytesReceived = 0
let lastNetworkUpdateTime = 0

// 监听本地系统信息变化，更新图表数据
watch(
  storeLocalSystemInfo,
  (sysInfo) => {
    if (sysInfo) {
      // 使用 requestAnimationFrame 批量更新，减少重绘
      requestAnimationFrame(() => {
        // 更新 CPU 和内存历史
        const cpu = sysInfo.cpu_percent
        const memory = sysInfo.memory_percent

        // 更新网络吞吐量历史
        const currentTime = Date.now()
        const network = sysInfo.network
        let sentRate = 0
        let receivedRate = 0

        if (lastNetworkUpdateTime > 0 && network) {
          // 计算时间差（秒）
          const timeDiff = (currentTime - lastNetworkUpdateTime) / 1000

          if (timeDiff > 0) {
            // 计算速率 (KB/s)
            sentRate = Math.max(0, (network.bytes_sent - lastNetworkBytesSent) / 1024 / timeDiff)
            receivedRate = Math.max(
              0,
              (network.bytes_received - lastNetworkBytesReceived) / 1024 / timeDiff
            )
          }
        }

        // 更新上次记录
        if (network) {
          lastNetworkBytesSent = network.bytes_sent
          lastNetworkBytesReceived = network.bytes_received
          lastNetworkUpdateTime = currentTime
        }

        // 更新事件总线中的性能数据
        eventBus.updatePerformanceHistory(cpu, memory, sentRate, receivedRate)
      })
    }
  },
  { immediate: true }
)

/**
 * 获取 SVG 路径
 * @param data - 数据数组
 * @returns SVG 路径字符串
 */
const getSparklinePath = (data: number[]): string => {
  const max = Math.max(...data, 1)
  const min = Math.min(...data, 0)
  const range = max - min || 1
  const width = 200
  const height = 40

  return data
    .map((value, index) => {
      const x = (index / (data.length - 1)) * width
      const y = height - ((value - min) / range) * height
      return `${index === 0 ? 'M' : 'L'} ${x} ${y}`
    })
    .join(' ')
}

/**
 * 格式化内存大小
 * @param mb - 内存大小（MB）
 * @returns 格式化后的字符串
 */
const formatMemory = (mb: number): string => {
  if (mb >= 1024) {
    return `${(mb / 1024).toFixed(2)} GB`
  }
  return `${mb.toFixed(1)} MB`
}

/**
 * 获取网络速度显示
 * @returns 格式化后的网络速度字符串
 */
const getNetworkSpeedDisplay = (): string => {
  const received =
    performanceState.networkReceivedHistory[performanceState.networkReceivedHistory.length - 1] || 0
  const sent = performanceState.networkSentHistory[performanceState.networkSentHistory.length - 1] || 0
  const total = received + sent

  if (total >= 1024) {
    return `${(total / 1024).toFixed(2)} MB/s`
  }
  return `${total.toFixed(1)} KB/s`
}

/**
 * 检查 Redis 状态
 */
const checkRedisStatus = async () => {
  try {
    redisStatus.value = await getRedisStatus()
  } catch (e) {
    console.error('获取 Redis 状态失败:', e)
    redisStatus.value = null
  }
}

// 组件挂载时开始检查
onMounted(() => {
  // 立即检查一次
  checkDbConnection()
  checkRedisStatus()

  // 每 30 秒检查一次数据库连接
  dbCheckTimer = window.setInterval(() => {
    checkDbConnection()
  }, 30000)

  // 每 10 秒检查一次 Redis 状态
  redisCheckTimer = window.setInterval(() => {
    checkRedisStatus()
  }, 10000)
})

// 组件卸载时清理定时器
onUnmounted(() => {
  if (dbCheckTimer) {
    clearInterval(dbCheckTimer)
    dbCheckTimer = null
  }
  if (redisCheckTimer) {
    clearInterval(redisCheckTimer)
    redisCheckTimer = null
  }
})
</script>

<template>
  <div class="performance-grid">
    <!-- CPU 使用率 -->
    <div class="card metric-card">
      <div class="metric-header">
        <div class="metric-icon cpu">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="4" y="4" width="16" height="16" rx="2" ry="2" />
            <rect x="9" y="9" width="6" height="6" />
            <line x1="9" y1="1" x2="9" y2="4" />
            <line x1="15" y1="1" x2="15" y2="4" />
            <line x1="9" y1="20" x2="9" y2="23" />
            <line x1="15" y1="20" x2="15" y2="23" />
            <line x1="20" y1="9" x2="23" y2="9" />
            <line x1="20" y1="14" x2="23" y2="14" />
            <line x1="1" y1="9" x2="4" y2="9" />
            <line x1="1" y1="14" x2="4" y2="14" />
          </svg>
        </div>
        <div class="metric-info">
          <span class="metric-label">系统 CPU</span>
          <span class="metric-value">{{ storeLocalSystemInfo?.cpu_percent.toFixed(1) || '0.0' }}%</span>
        </div>
      </div>
      <div class="sparkline">
        <svg viewBox="0 0 200 40" preserveAspectRatio="none">
          <path
            :d="getSparklinePath(performanceState.cpuHistory)"
            fill="none"
            stroke="var(--primary-color)"
            stroke-width="2"
          />
          <path
            :d="`${getSparklinePath(performanceState.cpuHistory)} L 200 40 L 0 40 Z`"
            fill="url(#cpuGradient)"
            opacity="0.3"
          />
          <defs>
            <linearGradient id="cpuGradient" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" style="stop-color: var(--primary-color); stop-opacity: 1" />
              <stop offset="100%" style="stop-color: var(--primary-color); stop-opacity: 0" />
            </linearGradient>
          </defs>
        </svg>
      </div>
    </div>

    <!-- 内存使用 -->
    <div class="card metric-card">
      <div class="metric-header">
        <div class="metric-icon memory">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="2" y="4" width="20" height="16" rx="2" ry="2" />
            <path
              d="M6 8h.01M6 16h.01M10 8h.01M10 16h.01M14 8h.01M14 16h.01M18 8h.01M18 16h.01"
            />
          </svg>
        </div>
        <div class="metric-info">
          <span class="metric-label">内存使用</span>
          <span class="metric-value">{{
            storeLocalSystemInfo ? formatMemory(storeLocalSystemInfo.memory_used_gb * 1024) : '0.0 MB'
          }}</span>
        </div>
      </div>
      <div class="sparkline">
        <svg viewBox="0 0 200 40" preserveAspectRatio="none">
          <path
            :d="getSparklinePath(performanceState.memoryHistory)"
            fill="none"
            stroke="var(--success-color)"
            stroke-width="2"
          />
          <path
            :d="`${getSparklinePath(performanceState.memoryHistory)} L 200 40 L 0 40 Z`"
            fill="url(#memoryGradient)"
            opacity="0.3"
          />
          <defs>
            <linearGradient id="memoryGradient" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" style="stop-color: var(--success-color); stop-opacity: 1" />
              <stop offset="100%" style="stop-color: var(--success-color); stop-opacity: 0" />
            </linearGradient>
          </defs>
        </svg>
      </div>
    </div>

    <!-- 网络吞吐量 -->
    <div class="card metric-card network-card">
      <div class="metric-header">
        <div class="metric-icon network">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="2" y="2" width="20" height="8" rx="2" ry="2" />
            <rect x="2" y="14" width="20" height="8" rx="2" ry="2" />
            <line x1="6" y1="6" x2="6.01" y2="6" />
            <line x1="6" y1="18" x2="6.01" y2="18" />
          </svg>
        </div>
        <div class="metric-info">
          <span class="metric-label">网络吞吐量</span>
          <span class="metric-value">{{ getNetworkSpeedDisplay() }}</span>
        </div>
        <div class="network-legend">
          <span class="legend-item received"><span class="dot"></span>接收</span>
          <span class="legend-item sent"><span class="dot"></span>发送</span>
        </div>
      </div>
      <div class="sparkline network-sparkline">
        <svg viewBox="0 0 200 40" preserveAspectRatio="none">
          <!-- 接收数据（下行） -->
          <path
            :d="getSparklinePath(performanceState.networkReceivedHistory)"
            fill="none"
            stroke="var(--success-color)"
            stroke-width="2"
          />
          <path
            :d="`${getSparklinePath(performanceState.networkReceivedHistory)} L 200 40 L 0 40 Z`"
            fill="url(#networkReceivedGradient)"
            opacity="0.3"
          />
          <!-- 发送数据（上行） -->
          <path
            :d="getSparklinePath(performanceState.networkSentHistory)"
            fill="none"
            stroke="var(--info-color)"
            stroke-width="2"
          />
          <path
            :d="`${getSparklinePath(performanceState.networkSentHistory)} L 200 40 L 0 40 Z`"
            fill="url(#networkSentGradient)"
            opacity="0.3"
          />
          <defs>
            <linearGradient id="networkReceivedGradient" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" style="stop-color: var(--success-color); stop-opacity: 1" />
              <stop offset="100%" style="stop-color: var(--success-color); stop-opacity: 0" />
            </linearGradient>
            <linearGradient id="networkSentGradient" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" style="stop-color: var(--info-color); stop-opacity: 1" />
              <stop offset="100%" style="stop-color: var(--info-color); stop-opacity: 0" />
            </linearGradient>
          </defs>
        </svg>
      </div>
    </div>

    <!-- 运行时间（仅服务运行时显示） -->
    <div v-if="serviceStatus === 'running'" class="card metric-card">
      <div class="metric-header">
        <div class="metric-icon uptime">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10" />
            <polyline points="12 6 12 12 16 14" />
          </svg>
        </div>
        <div class="metric-info">
          <span class="metric-label">运行时间</span>
          <span class="metric-value">{{ storeServiceStatus?.uptime_formatted || '00:00:00' }}</span>
        </div>
      </div>
    </div>

    <!-- 服务端版本（仅服务运行时显示） -->
    <div v-if="serviceStatus === 'running'" class="card metric-card">
      <div class="metric-header">
        <div class="metric-icon version">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
            <line x1="16" y1="13" x2="8" y2="13" />
            <line x1="16" y1="17" x2="8" y2="17" />
            <polyline points="10 9 9 9 8 9" />
          </svg>
        </div>
        <div class="metric-info">
          <span class="metric-label">服务端版本</span>
          <span class="metric-value">{{ storeServiceStatus?.version || '-' }}</span>
        </div>
      </div>
    </div>

    <!-- 数据库连接状态（客户端独立检测） -->
    <div class="card metric-card db-card">
      <div class="metric-header">
        <div class="metric-icon database" :class="`db-status-${dbConnectionState.status}`">
          <img :src="getDbIcon()" class="icon-database" :alt="dbConnectionState.dbType || 'database'" />
        </div>
        <div class="metric-info">
          <span class="metric-label">数据库连接</span>
          <span class="metric-value" :class="`db-status-text-${dbConnectionState.status}`">
            {{ dbBadgeConfig.text }}
          </span>
        </div>
      </div>
      <div v-if="dbConnectionState.dbType" class="db-details">
        <span class="db-type">{{ dbConnectionState.dbType.toUpperCase() }}</span>
        <span v-if="dbConnectionState.latency !== undefined" class="db-latency">
          {{ dbConnectionState.latency }}ms
        </span>
      </div>
    </div>

    <!-- Redis 连接状态 -->
    <div class="card metric-card redis-card">
      <div class="metric-header">
        <div class="metric-icon redis" :class="`redis-status-${redisStatusClass}`">
          <img :src="redisIcon" class="icon-redis" alt="redis" />
        </div>
        <div class="metric-info">
          <span class="metric-label">Redis</span>
          <span class="metric-value" :class="`redis-status-text-${redisStatusClass}`">
            {{ redisStatusText }}
          </span>
        </div>
      </div>
      <div v-if="redisStatus?.is_loaded" class="redis-details">
        <span class="redis-port">端口: {{ redisStatus.port }}</span>
        <span v-if="redisStatus.status === 'running'" class="redis-auth">
          {{ redisStatus.require_pass ? '有密码' : '无密码' }}
        </span>
      </div>
    </div>
  </div>
</template>

<style scoped>
@import '../../styles/home-components.css';

/* 数据库卡片样式 */
.db-card {
  display: flex;
  flex-direction: column;
}

.db-details {
  display: flex;
  gap: var(--spacing-sm);
  margin-top: var(--spacing-sm);
  padding-top: var(--spacing-sm);
  border-top: 1px solid var(--border-color);
}

.db-type {
  font-size: var(--font-size-xs);
  font-weight: 500;
  color: var(--text-secondary);
  text-transform: uppercase;
}

.db-latency {
  font-size: var(--font-size-xs);
  color: var(--text-secondary);
}

/* 数据库状态颜色 */
.db-status-connected {
  background-color: var(--success-color);
}

.db-status-disconnected {
  background-color: var(--error-color);
}

.db-status-checking {
  background-color: var(--warning-color);
}

.db-status-text-connected {
  color: var(--success-color);
}

.db-status-text-disconnected {
  color: var(--error-color);
}

.db-status-text-checking {
  color: var(--warning-color);
}

/* 数据库图标 */
.icon-database {
  width: 24px;
  height: 24px;
}

/* Redis 图标 */
.icon-redis {
  width: 24px;
  height: 24px;
}

/* 亮色模式：图标保持原色 */
:root:not([data-theme='dark']) .icon-database,
:root:not([data-theme='dark']) .icon-redis {
  filter: none;
}

/* 暗色模式：图标反转为白色 */
:root[data-theme='dark'] .icon-database,
:root[data-theme='dark'] .icon-redis,
.icon-database,
.icon-redis {
  filter: brightness(0) invert(1);
}

/* Redis 卡片样式 */
.redis-card {
  display: flex;
  flex-direction: column;
}

.redis-details {
  display: flex;
  gap: var(--spacing-sm);
  margin-top: var(--spacing-sm);
  padding-top: var(--spacing-sm);
  border-top: 1px solid var(--border-color);
}

.redis-port,
.redis-auth {
  font-size: var(--font-size-xs);
  color: var(--text-secondary);
}

/* Redis 状态颜色 - 图标背景 */
.redis-status-status-connected {
  background-color: var(--success-color);
}

.redis-status-status-disconnected {
  background-color: var(--error-color);
}

.redis-status-status-unloaded {
  background-color: var(--bg-tertiary);
}

.redis-status-status-error {
  background-color: var(--warning-color);
}

.redis-status-status-unknown {
  background-color: var(--text-secondary);
}

/* Redis 状态颜色 - 文字 */
.redis-status-text-status-connected {
  color: var(--success-color);
}

.redis-status-text-status-disconnected {
  color: var(--error-color);
}

.redis-status-text-status-unloaded {
  color: var(--text-secondary);
}

.redis-status-text-status-error {
  color: var(--warning-color);
}

.redis-status-text-status-unknown {
  color: var(--text-secondary);
}
</style>
