<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, watch } from 'vue'
import { storeToRefs } from 'pinia'
import Alert from '../components/Alert.vue'
import Card from '../components/Card.vue'
import StatusBadge from '../components/StatusBadge.vue'
import { useServiceStore, type BasicSystemInfo } from '../stores'
import {
  startService,
  stopService,
  restartService,
  type ActionResponse
} from '../services/api'

/**
 * 服务状态类型
 */
type ServiceStatusType = 'running' | 'stopped' | 'starting' | 'stopping'

// 图标路径
const refreshIcon = new URL('../assets/icons/refresh.svg', import.meta.url).href
const playIcon = new URL('../assets/icons/play.svg', import.meta.url).href
const stopIcon = new URL('../assets/icons/stop.svg', import.meta.url).href

// 使用 Pinia store 管理服务状态
const serviceStore = useServiceStore()
const {
  isRunning: storeIsRunning,
  serviceStatus: storeServiceStatus,
  processInfo: storeProcessInfo,
  localSystemInfo: storeLocalSystemInfo,
  basicSystemInfo: storeBasicSystemInfo,
  isInitialized: storeIsInitialized
} = storeToRefs(serviceStore)

// 本地状态
const isLoading = ref(false)
const error = ref<string | null>(null)

// 计算属性：服务状态（兼容原有逻辑）
const serviceStatus = computed<ServiceStatusType | null>(() => {
  if (!storeIsInitialized.value) return null
  return storeIsRunning.value ? 'running' : 'stopped'
})

// 计算属性：服务端详细信息
const serverStatus = computed(() => storeServiceStatus.value)
const processInfo = computed(() => storeProcessInfo.value)
const localSystemInfo = computed(() => storeLocalSystemInfo.value)

// 基础系统信息（从 store 获取）
const basicSystemInfo = computed<BasicSystemInfo | null>(() => {
  return storeBasicSystemInfo.value
})

// 性能数据历史（用于图表）
const cpuHistory = ref<number[]>(new Array(20).fill(0))
const memoryHistory = ref<number[]>(new Array(20).fill(0))

// 网络吞吐量历史（用于图表）
const networkSentHistory = ref<number[]>(new Array(20).fill(0))
const networkReceivedHistory = ref<number[]>(new Array(20).fill(0))

// 上次网络字节数（用于计算速率）
let lastNetworkBytesSent = 0
let lastNetworkBytesReceived = 0
let lastNetworkUpdateTime = 0

// 监听本地系统信息变化，更新图表数据
watch(storeLocalSystemInfo, (sysInfo) => {
  if (sysInfo) {
    // 使用 requestAnimationFrame 批量更新，减少重绘
    requestAnimationFrame(() => {
      // 更新 CPU 历史
      cpuHistory.value.shift()
      cpuHistory.value.push(sysInfo.cpu_percent)

      // 更新内存历史
      memoryHistory.value.shift()
      memoryHistory.value.push(sysInfo.memory_percent)

      // 更新网络吞吐量历史
      const currentTime = Date.now()
      const network = sysInfo.network

      if (lastNetworkUpdateTime > 0 && network) {
        // 计算时间差（秒）
        const timeDiff = (currentTime - lastNetworkUpdateTime) / 1000

        if (timeDiff > 0) {
          // 计算速率 (KB/s)
          const sentRate = Math.max(0, (network.bytes_sent - lastNetworkBytesSent) / 1024 / timeDiff)
          const receivedRate = Math.max(0, (network.bytes_received - lastNetworkBytesReceived) / 1024 / timeDiff)

          networkSentHistory.value.shift()
          networkSentHistory.value.push(sentRate)

          networkReceivedHistory.value.shift()
          networkReceivedHistory.value.push(receivedRate)
        }
      }

      // 更新上次记录
      if (network) {
        lastNetworkBytesSent = network.bytes_sent
        lastNetworkBytesReceived = network.bytes_received
        lastNetworkUpdateTime = currentTime
      }
    })
  }
}, { immediate: true })

/**
 * 刷新服务状态
 * 使用 Pinia store 的方法，避免重复请求
 */
const refreshStatus = async (): Promise<void> => {
  await serviceStore.refreshStatus()
}

/**
 * 启动服务
 */
const handleStartService = async (): Promise<void> => {
  if (isLoading.value || storeIsRunning.value) return

  isLoading.value = true
  error.value = null

  try {
    const result: ActionResponse = await startService()

    if (result.success) {
      // 轮询检查服务状态，最多等待15秒
      let attempts = 0
      const maxAttempts = 30

      while (attempts < maxAttempts) {
        await new Promise(resolve => setTimeout(resolve, 500))
        // 使用强制刷新，忽略防抖限制
        await serviceStore.refreshStatus(true)

        if (storeIsRunning.value) {
          // 服务已启动
          break
        }
        attempts++
      }

      if (!storeIsRunning.value) {
        error.value = '服务启动超时，请手动刷新状态'
      }
    } else {
      error.value = result.message
    }
  } catch (err) {
    error.value = '启动服务失败: ' + String(err)
  } finally {
    isLoading.value = false
  }
}

/**
 * 停止服务
 */
const handleStopService = async (): Promise<void> => {
  if (isLoading.value || !storeIsRunning.value) return

  isLoading.value = true
  error.value = null

  try {
    const result: ActionResponse = await stopService()

    if (result.success) {
      // 轮询检查服务状态，最多等待10秒
      let attempts = 0
      const maxAttempts = 20

      while (attempts < maxAttempts) {
        await new Promise(resolve => setTimeout(resolve, 500))
        // 使用强制刷新，忽略防抖限制
        await serviceStore.refreshStatus(true)

        if (!storeIsRunning.value) {
          // 服务已停止
          break
        }
        attempts++
      }

      if (storeIsRunning.value) {
        error.value = '服务停止超时，请手动刷新状态'
      }
    } else {
      error.value = result.message
    }
  } catch (err) {
    error.value = '停止服务失败: ' + String(err)
  } finally {
    isLoading.value = false
  }
}

/**
 * 重启服务
 */
const handleRestartService = async (): Promise<void> => {
  if (isLoading.value) return

  isLoading.value = true
  error.value = null

  try {
    const result: ActionResponse = await restartService()

    if (result.success) {
      // 等待服务重启
      await new Promise(resolve => setTimeout(resolve, 5000))
      await serviceStore.refreshStatus()
    } else {
      error.value = result.message
    }
  } catch (err) {
    error.value = '重启服务失败: ' + String(err)
  } finally {
    isLoading.value = false
  }
}

/**
 * 开始定时刷新
 * 使用 Pinia store 的本地系统信息自动刷新方法（2秒间隔，不访问服务端）
 */
const startAutoRefresh = (): void => {
  serviceStore.startLocalSystemInfoRefresh(2000)
}

/**
 * 获取 SVG 路径
 */
const getSparklinePath = (data: number[]): string => {
  const max = Math.max(...data, 1)
  const min = Math.min(...data, 0)
  const range = max - min || 1
  const width = 200
  const height = 40

  return data.map((value, index) => {
    const x = (index / (data.length - 1)) * width
    const y = height - ((value - min) / range) * height
    return `${index === 0 ? 'M' : 'L'} ${x} ${y}`
  }).join(' ')
}

/**
 * 格式化内存大小
 * 根据大小自动选择 MB 或 GB 单位
 */
const formatMemory = (mb: number): string => {
  if (mb >= 1024) {
    return `${(mb / 1024).toFixed(2)} GB`
  }
  return `${mb.toFixed(1)} MB`
}

/**
 * 获取请求成功率
 */
const getSuccessRate = (): number => {
  if (!serverStatus.value?.requests) return 0
  const { total, success } = serverStatus.value.requests
  if (total === 0) return 100
  return (success / total) * 100
}

/**
 * 获取网络速度显示
 */
const getNetworkSpeedDisplay = (): string => {
  const received = networkReceivedHistory.value[networkReceivedHistory.value.length - 1] || 0
  const sent = networkSentHistory.value[networkSentHistory.value.length - 1] || 0
  const total = received + sent
  
  if (total >= 1024) {
    return `${(total / 1024).toFixed(2)} MB/s`
  }
  return `${total.toFixed(1)} KB/s`
}

/**
 * 格式化服务器时间
 */
const formatServerTime = (timeStr: string): string => {
  try {
    const date = new Date(timeStr)
    return date.toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    })
  } catch {
    return timeStr
  }
}

onMounted(() => {
  // 使用 Pinia store 的自动刷新，避免重复请求
  // 如果 store 已经在刷新，不需要额外调用
  if (!serviceStore.isRefreshing) {
    serviceStore.refreshStatus()
  }
  startAutoRefresh()
})

onUnmounted(() => {
  // 注意：这里不停止自动刷新，让其他页面可以继续使用
  // 只有在应用关闭时才需要停止
})
</script>

<template>
  <div class="home">
    <h1 class="page-title">控制台</h1>

    <!-- 错误提示 -->
    <Alert
      v-if="error"
      type="error"
      closable
      @close="error = null"
    >
      {{ error }}
    </Alert>

    <!-- 服务控制卡片 -->
    <Card
      title="服务状态"
      custom-class="service-card"
    >
      <template #header>
        <div class="service-info">
          <StatusBadge :status="serviceStatus || 'default'" />
        </div>
      </template>
      <template #actions>
        <button class="btn btn-secondary btn-sm" @click="refreshStatus" :disabled="isLoading">
          <img
            :src="refreshIcon"
            class="btn-icon"
            :class="{ spinning: isLoading }"
            alt="refresh"
          />
          刷新
        </button>
      </template>

      <div class="service-controls">
        <button
          class="btn btn-success"
          @click="handleStartService"
          :disabled="isLoading || serviceStatus === 'running' || serviceStatus === 'starting' || serviceStatus === null"
        >
          <img :src="playIcon" class="btn-icon icon-white" alt="play" />
          启动服务
        </button>

        <button
          class="btn btn-error"
          @click="handleStopService"
          :disabled="isLoading || serviceStatus === 'stopped' || serviceStatus === 'stopping' || serviceStatus === null"
        >
          <img :src="stopIcon" class="btn-icon icon-white" alt="stop" />
          停止服务
        </button>

        <button
          class="btn btn-warning"
          @click="handleRestartService"
          :disabled="isLoading || serviceStatus !== 'running'"
        >
          <img :src="refreshIcon" class="btn-icon icon-white" alt="restart" />
          重启服务
        </button>
      </div>

      <div v-if="isLoading" class="loading-indicator">
        <div class="spinner"></div>
        <span>正在处理...</span>
      </div>
    </Card>
    
    <!-- 性能监控（始终显示，使用本地系统信息） -->
    <div class="performance-grid">
      <!-- CPU 使用率 -->
      <div class="card metric-card">
        <div class="metric-header">
          <div class="metric-icon cpu">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="4" y="4" width="16" height="16" rx="2" ry="2"/>
              <rect x="9" y="9" width="6" height="6"/>
              <line x1="9" y1="1" x2="9" y2="4"/>
              <line x1="15" y1="1" x2="15" y2="4"/>
              <line x1="9" y1="20" x2="9" y2="23"/>
              <line x1="15" y1="20" x2="15" y2="23"/>
              <line x1="20" y1="9" x2="23" y2="9"/>
              <line x1="20" y1="14" x2="23" y2="14"/>
              <line x1="1" y1="9" x2="4" y2="9"/>
              <line x1="1" y1="14" x2="4" y2="14"/>
            </svg>
          </div>
          <div class="metric-info">
            <span class="metric-label">系统 CPU</span>
            <span class="metric-value">{{ localSystemInfo?.cpu_percent.toFixed(1) || '0.0' }}%</span>
          </div>
        </div>
        <div class="sparkline">
          <svg viewBox="0 0 200 40" preserveAspectRatio="none">
            <path
              :d="getSparklinePath(cpuHistory)"
              fill="none"
              stroke="var(--primary-color)"
              stroke-width="2"
            />
            <path
              :d="`${getSparklinePath(cpuHistory)} L 200 40 L 0 40 Z`"
              fill="url(#cpuGradient)"
              opacity="0.3"
            />
            <defs>
              <linearGradient id="cpuGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" style="stop-color:var(--primary-color);stop-opacity:1" />
                <stop offset="100%" style="stop-color:var(--primary-color);stop-opacity:0" />
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
              <rect x="2" y="4" width="20" height="16" rx="2" ry="2"/>
              <path d="M6 8h.01M6 16h.01M10 8h.01M10 16h.01M14 8h.01M14 16h.01M18 8h.01M18 16h.01"/>
            </svg>
          </div>
          <div class="metric-info">
            <span class="metric-label">内存使用</span>
            <span class="metric-value">{{ localSystemInfo ? formatMemory(localSystemInfo.memory_used_gb * 1024) : '0.0 MB' }}</span>
          </div>
        </div>
        <div class="sparkline">
          <svg viewBox="0 0 200 40" preserveAspectRatio="none">
            <path
              :d="getSparklinePath(memoryHistory)"
              fill="none"
              stroke="var(--success-color)"
              stroke-width="2"
            />
            <path
              :d="`${getSparklinePath(memoryHistory)} L 200 40 L 0 40 Z`"
              fill="url(#memoryGradient)"
              opacity="0.3"
            />
            <defs>
              <linearGradient id="memoryGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" style="stop-color:var(--success-color);stop-opacity:1" />
                <stop offset="100%" style="stop-color:var(--success-color);stop-opacity:0" />
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
              <rect x="2" y="2" width="20" height="8" rx="2" ry="2"/>
              <rect x="2" y="14" width="20" height="8" rx="2" ry="2"/>
              <line x1="6" y1="6" x2="6.01" y2="6"/>
              <line x1="6" y1="18" x2="6.01" y2="18"/>
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
              :d="getSparklinePath(networkReceivedHistory)"
              fill="none"
              stroke="var(--success-color)"
              stroke-width="2"
            />
            <path
              :d="`${getSparklinePath(networkReceivedHistory)} L 200 40 L 0 40 Z`"
              fill="url(#networkReceivedGradient)"
              opacity="0.3"
            />
            <!-- 发送数据（上行） -->
            <path
              :d="getSparklinePath(networkSentHistory)"
              fill="none"
              stroke="var(--info-color)"
              stroke-width="2"
            />
            <path
              :d="`${getSparklinePath(networkSentHistory)} L 200 40 L 0 40 Z`"
              fill="url(#networkSentGradient)"
              opacity="0.3"
            />
            <defs>
              <linearGradient id="networkReceivedGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" style="stop-color:var(--success-color);stop-opacity:1" />
                <stop offset="100%" style="stop-color:var(--success-color);stop-opacity:0" />
              </linearGradient>
              <linearGradient id="networkSentGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" style="stop-color:var(--info-color);stop-opacity:1" />
                <stop offset="100%" style="stop-color:var(--info-color);stop-opacity:0" />
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
              <circle cx="12" cy="12" r="10"/>
              <polyline points="12 6 12 12 16 14"/>
            </svg>
          </div>
          <div class="metric-info">
            <span class="metric-label">运行时间</span>
            <span class="metric-value">{{ serverStatus?.uptime_formatted || '00:00:00' }}</span>
          </div>
        </div>
      </div>

      <!-- 服务端版本（仅服务运行时显示） -->
      <div v-if="serviceStatus === 'running'" class="card metric-card">
        <div class="metric-header">
          <div class="metric-icon version">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
              <line x1="16" y1="13" x2="8" y2="13"/>
              <line x1="16" y1="17" x2="8" y2="17"/>
              <polyline points="10 9 9 9 8 9"/>
            </svg>
          </div>
          <div class="metric-info">
            <span class="metric-label">服务端版本</span>
            <span class="metric-value">{{ serverStatus?.version || 'Unknown' }}</span>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 进程信息 -->
    <div v-if="processInfo && serviceStatus === 'running'" class="card process-card">
      <div class="card-header">
        <h2 class="card-title">进程信息</h2>
      </div>
      <div class="process-info">
        <div class="info-item">
          <span class="info-label">进程 ID</span>
          <span class="info-value">{{ processInfo.pid }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">进程名称</span>
          <span class="info-value">{{ processInfo.name }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">CPU 使用率</span>
          <span class="info-value">{{ processInfo.cpu_usage.toFixed(1) }}%</span>
        </div>
        <div class="info-item">
          <span class="info-label">内存占用</span>
          <span class="info-value">{{ processInfo.memory_mb.toFixed(1) }} MB</span>
        </div>
        <div class="info-item">
          <span class="info-label">进程状态</span>
          <span class="info-value">{{ processInfo.status }}</span>
        </div>
      </div>
    </div>
    
    <!-- 基础系统信息（服务未启动时也可显示） -->
    <div v-if="basicSystemInfo" class="card system-card">
      <div class="card-header">
        <h2 class="card-title">系统信息</h2>
      </div>
      <div class="system-info">
        <div class="info-item">
          <span class="info-label">主机名</span>
          <span class="info-value">{{ basicSystemInfo.hostname }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">操作系统</span>
          <span class="info-value">{{ basicSystemInfo.platform }} ({{ basicSystemInfo.architecture }})</span>
        </div>
        <div class="info-item">
          <span class="info-label">CPU 核心数</span>
          <span class="info-value">{{ basicSystemInfo.cpuCount }} 核</span>
        </div>
        <div class="info-item">
          <span class="info-label">总内存</span>
          <span class="info-value">{{ basicSystemInfo.memoryTotalGB.toFixed(2) }} GB</span>
        </div>
      </div>
    </div>

    <!-- 详细系统信息（仅服务运行时显示） -->
    <div v-if="localSystemInfo && serviceStatus === 'running'" class="card system-card">
      <div class="card-header">
        <h2 class="card-title">系统详细信息</h2>
      </div>
      <div class="system-info">
        <div class="info-item">
          <span class="info-label">平台版本</span>
          <span class="info-value">{{ localSystemInfo.platform_version }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">处理器</span>
          <span class="info-value">{{ localSystemInfo.processor }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">CPU 频率</span>
          <span class="info-value">{{ localSystemInfo.cpu_freq_mhz ? (localSystemInfo.cpu_freq_mhz / 1000).toFixed(2) + ' GHz' : 'N/A' }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">内存使用</span>
          <span class="info-value">{{ localSystemInfo.memory_used_gb.toFixed(2) }} / {{ localSystemInfo.memory_total_gb.toFixed(2) }} GB ({{ localSystemInfo.memory_percent.toFixed(1) }}%)</span>
        </div>
        <div class="info-item">
          <span class="info-label">磁盘使用</span>
          <span class="info-value">{{ localSystemInfo.disk_used_gb.toFixed(2) }} / {{ localSystemInfo.disk_total_gb.toFixed(2) }} GB ({{ localSystemInfo.disk_percent.toFixed(1) }}%)</span>
        </div>
        <div v-if="serverStatus" class="info-item">
          <span class="info-label">调试模式</span>
          <span class="info-value">
            <span class="tag" :class="serverStatus.debug_mode ? 'tag-warning' : 'tag-success'">
              {{ serverStatus.debug_mode ? '开启' : '关闭' }}
            </span>
          </span>
        </div>
      </div>
    </div>

    <!-- 请求统计（仅服务运行时显示） -->
    <div v-if="serverStatus && serviceStatus === 'running'" class="card requests-card">
      <div class="card-header">
        <h2 class="card-title">请求统计</h2>
      </div>
      <div class="requests-grid">
        <div class="request-metric">
          <div class="request-value">{{ serverStatus.requests.total }}</div>
          <div class="request-label">总请求数</div>
        </div>
        <div class="request-metric">
          <div class="request-value" :class="{ 'text-success': getSuccessRate() >= 99, 'text-warning': getSuccessRate() < 95 && getSuccessRate() > 0, 'text-error': getSuccessRate() === 0 && serverStatus.requests.total > 0 }">
            {{ getSuccessRate().toFixed(1) }}%
          </div>
          <div class="request-label">成功率</div>
        </div>
        <div class="request-metric">
          <div class="request-value">{{ serverStatus.requests.avg_response_time_ms.toFixed(1) }}ms</div>
          <div class="request-label">平均响应时间</div>
        </div>
        <div class="request-metric">
          <div class="request-value">{{ serverStatus.requests.requests_per_minute }}</div>
          <div class="request-label">每分钟请求</div>
        </div>
      </div>
    </div>

    <!-- Git操作状态（仅服务运行时显示） -->
    <div v-if="serverStatus && serviceStatus === 'running'" class="card git-card">
      <div class="card-header">
        <h2 class="card-title">Git 操作状态</h2>
      </div>
      <div class="git-grid">
        <div class="git-metric">
          <div class="git-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 2L2 7l10 5 10-5-10-5z"/>
              <path d="M2 17l10 5 10-5"/>
              <path d="M2 12l10 5 10-5"/>
            </svg>
          </div>
          <div class="git-info">
            <div class="git-value">{{ serverStatus.git_operations.active_clones }}</div>
            <div class="git-label">活跃克隆</div>
          </div>
        </div>
        <div class="git-metric">
          <div class="git-icon push">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 19l7-7 3 3-7 7-3-3z"/>
              <path d="M18 13l-1.5-7.5L2 2l3.5 14.5L13 18l5-5z"/>
              <path d="M2 2l7.586 7.586"/>
              <circle cx="11" cy="11" r="2"/>
            </svg>
          </div>
          <div class="git-info">
            <div class="git-value">{{ serverStatus.git_operations.active_pushes }}</div>
            <div class="git-label">活跃推送</div>
          </div>
        </div>
        <div class="git-metric">
          <div class="git-icon queue" :class="{ 'text-warning': serverStatus.git_operations.queue_size > 5, 'text-error': serverStatus.git_operations.queue_size > 10 }">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="8" y1="6" x2="21" y2="6"/>
              <line x1="8" y1="12" x2="21" y2="12"/>
              <line x1="8" y1="18" x2="21" y2="18"/>
              <line x1="3" y1="6" x2="3.01" y2="6"/>
              <line x1="3" y1="12" x2="3.01" y2="12"/>
              <line x1="3" y1="18" x2="3.01" y2="18"/>
            </svg>
          </div>
          <div class="git-info">
            <div class="git-value" :class="{ 'text-warning': serverStatus.git_operations.queue_size > 5, 'text-error': serverStatus.git_operations.queue_size > 10 }">
              {{ serverStatus.git_operations.queue_size }}
            </div>
            <div class="git-label">队列长度</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 服务端健康状态（仅服务运行时显示） -->
    <div v-if="serverStatus && serviceStatus === 'running'" class="card health-card">
      <div class="card-header">
        <h2 class="card-title">服务端健康状态</h2>
      </div>
      <div class="health-grid">
        <div class="health-item">
          <span class="health-label">进程 ID</span>
          <span class="health-value">{{ serverStatus.process.pid }}</span>
        </div>
        <div class="health-item">
          <span class="health-label">线程数</span>
          <span class="health-value">{{ serverStatus.process.threads }}</span>
        </div>
        <div class="health-item">
          <span class="health-label">活跃连接</span>
          <span class="health-value">{{ serverStatus.process.connections }}</span>
        </div>
        <div class="health-item">
          <span class="health-label">服务端内存</span>
          <span class="health-value">{{ serverStatus.process.memory_mb.toFixed(1) }} MB</span>
        </div>
        <div class="health-item">
          <span class="health-label">服务端 CPU</span>
          <span class="health-value">{{ serverStatus.process.cpu_percent.toFixed(1) }}%</span>
        </div>
        <div class="health-item">
          <span class="health-label">服务器时间</span>
          <span class="health-value">{{ formatServerTime(serverStatus.server_time) }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.home {
  max-width: 1200px;
}

/* 服务控制 */
.service-card {
  margin-bottom: var(--spacing-lg);
}

.service-info {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.service-controls {
  display: flex;
  gap: var(--spacing-md);
  flex-wrap: wrap;
}

/* 性能监控网格 */
.performance-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: var(--spacing-lg);
  margin-bottom: var(--spacing-lg);
}

/* 指标卡片 */
.metric-card {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
  transform: translateZ(0);
  will-change: transform;
}

.metric-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.metric-icon {
  width: 48px;
  height: 48px;
  border-radius: var(--border-radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
}

.metric-icon svg {
  width: 24px;
  height: 24px;
}

.metric-icon.cpu {
  background-color: rgba(59, 130, 246, 0.2);
  color: var(--primary-color);
}

.metric-icon.memory {
  background-color: rgba(16, 185, 129, 0.2);
  color: var(--success-color);
}

.metric-icon.uptime {
  background-color: rgba(245, 158, 11, 0.2);
  color: var(--warning-color);
}

.metric-icon.version {
  background-color: rgba(6, 182, 212, 0.2);
  color: var(--info-color);
}

.metric-icon.network {
  background-color: rgba(139, 92, 246, 0.2);
  color: #8b5cf6;
}

.metric-info {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.metric-label {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}

.metric-value {
  font-size: var(--font-size-xl);
  font-weight: 700;
  color: var(--text-primary);
}

/* 网络图 */
.sparkline {
  height: 40px;
  margin-top: auto;
  transform: translateZ(0);
  will-change: transform;
  backface-visibility: hidden;
}

.sparkline svg {
  width: 100%;
  height: 100%;
  shape-rendering: geometricPrecision;
}

.network-card .metric-header {
  position: relative;
  justify-content: flex-start;
}

.network-legend {
  display: flex;
  gap: var(--spacing-sm);
  font-size: var(--font-size-xs);
  margin-left: auto;
  padding-left: var(--spacing-sm);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  color: var(--text-secondary);
  white-space: nowrap;
}

.legend-item .dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.legend-item.received .dot {
  background-color: var(--success-color);
}

.legend-item.sent .dot {
  background-color: var(--info-color);
}

/* 卡片间距 */
.process-card,
.system-card,
.requests-card,
.git-card,
.health-card {
  margin-bottom: var(--spacing-lg);
}

/* 信息网格 */
.process-info,
.system-info {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: var(--spacing-md);
}

/* 请求统计 */
.requests-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: var(--spacing-md);
}

.request-metric {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: var(--spacing-md);
  background-color: var(--bg-secondary);
  border-radius: var(--border-radius-md);
}

.request-value {
  font-size: var(--font-size-2xl);
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: var(--spacing-xs);
}

.request-label {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}

/* Git 状态 */
.git-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: var(--spacing-md);
}

.git-metric {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-md);
  background-color: var(--bg-secondary);
  border-radius: var(--border-radius-md);
}

.git-icon {
  width: 40px;
  height: 40px;
  border-radius: var(--border-radius-md);
  background-color: rgba(139, 92, 246, 0.2);
  color: #8b5cf6;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.git-icon.push {
  background-color: rgba(16, 185, 129, 0.2);
  color: var(--success-color);
}

.git-icon.queue {
  background-color: rgba(245, 158, 11, 0.2);
  color: var(--warning-color);
}

.git-icon svg {
  width: 20px;
  height: 20px;
}

.git-info {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.git-value {
  font-size: var(--font-size-xl);
  font-weight: 700;
  color: var(--text-primary);
}

.git-label {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}

/* 健康状态 */
.health-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: var(--spacing-md);
}

.health-item {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
  padding: var(--spacing-sm);
  background-color: var(--bg-secondary);
  border-radius: var(--border-radius-md);
}

.health-label {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}

.health-value {
  font-size: var(--font-size-md);
  font-weight: 600;
  color: var(--text-primary);
}
</style>
