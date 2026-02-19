/**
 * 服务状态管理 Store
 *
 * 使用 Pinia 管理全局服务状态，避免路由切换时重复检测
 * 自动启动服务状态检查，统一管理自动刷新逻辑
 */
import { defineStore } from 'pinia'
import { ref, computed, onMounted, onUnmounted } from 'vue'
import {
  isServiceRunning,
  getServiceStatus,
  getSystemResources,
  getServerProcessInfo,
  getLocalSystemInfo,
  getAppConfig,
  type ServiceStatus,
  type SystemResources,
  type ProcessInfo,
  type SystemInfo,
  type ServerAppConfig
} from '../services/api'

// 基础系统信息类型
export interface BasicSystemInfo {
  platform: string
  hostname: string
  cpuCount: number
  memoryTotalGB: number
  architecture: string
}

export const useServiceStore = defineStore('service', () => {
  // ============ State ============
  // 服务运行状态
  const isRunning = ref<boolean>(false)
  // 服务状态详情
  const serviceStatus = ref<ServiceStatus | null>(null)
  // 系统资源
  const systemResources = ref<SystemResources | null>(null)
  // 进程信息
  const processInfo = ref<ProcessInfo | null>(null)
  // 本地系统信息
  const localSystemInfo = ref<SystemInfo | null>(null)
  // 基础系统信息
  const basicSystemInfo = ref<BasicSystemInfo | null>(null)
  // 服务端配置
  const serverConfig = ref<ServerAppConfig | null>(null)
  // 是否正在刷新
  const isRefreshing = ref(false)
  // 是否已初始化
  const isInitialized = ref(false)
  // 错误信息
  const error = ref<string | null>(null)
  // 上次刷新时间
  const lastRefreshTime = ref<number>(0)
  // 是否已加载配置（仅启动时加载一次）
  const isConfigLoaded = ref<boolean>(false)

  // ============ Getters ============
  // 服务状态文本
  const statusText = computed(() => {
    if (!isInitialized.value) return '检测中...'
    return isRunning.value ? '运行中' : '已停止'
  })

  // 服务状态标签样式
  const statusClass = computed(() => {
    if (!isInitialized.value) return 'tag-secondary'
    return isRunning.value ? 'tag-success' : 'tag-error'
  })

  // 是否可以刷新（避免过于频繁的刷新）
  const canRefresh = computed(() => {
    const now = Date.now()
    return !isRefreshing.value && (now - lastRefreshTime.value > 1000)
  })

  // 服务端是否启用代理
  const isServerProxyEnabled = computed(() => {
    return serverConfig.value?.proxy?.proxy ?? false
  })

  // ============ Actions ============
  /**
   * 提取基础系统信息
   */
  function extractBasicSystemInfo(sysInfo: SystemInfo | null): BasicSystemInfo | null {
    if (!sysInfo) return null
    return {
      platform: sysInfo.platform || 'Unknown',
      hostname: sysInfo.hostname || 'Unknown',
      cpuCount: sysInfo.cpu_count || 0,
      memoryTotalGB: sysInfo.memory_total_gb || 0,
      architecture: sysInfo.architecture || 'Unknown'
    }
  }

  /**
   * 刷新服务状态
   * 使用防抖和超时控制，避免在压测环境下阻塞UI
   * @param force 是否强制刷新（忽略防抖限制）
   */
  async function refreshStatus(force: boolean = false): Promise<void> {
    // 如果正在刷新或刷新过于频繁，跳过（除非强制刷新）
    if (!force && !canRefresh.value) return

    isRefreshing.value = true
    error.value = null

    try {
      // 获取本地系统信息 - 设置2秒超时
      const sysInfoPromise = getLocalSystemInfo().catch(() => null)
      const sysInfo = await Promise.race([
        sysInfoPromise,
        new Promise<null>((_, reject) =>
          setTimeout(() => reject(new Error('Timeout')), 2000)
        ).catch(() => null)
      ])
      localSystemInfo.value = sysInfo

      // 更新基础系统信息
      const basicInfo = extractBasicSystemInfo(sysInfo)
      if (basicInfo) {
        basicSystemInfo.value = basicInfo
      }

      // 检查本地进程是否运行 - 设置1秒超时
      const runningPromise = isServiceRunning()
      const running = await Promise.race([
        runningPromise,
        new Promise<boolean>((_, reject) =>
          setTimeout(() => reject(new Error('Timeout')), 1000)
        ).catch(() => false)
      ])

      isRunning.value = running

      if (running) {
        // 获取服务端详细状态 - 设置3秒超时
        const statusPromise = getServiceStatus().catch(() => null)
        const resourcesPromise = getSystemResources().catch(() => null)
        const procInfoPromise = getServerProcessInfo().catch(() => null)

        const [status, resources, procInfo] = await Promise.all([
          Promise.race([statusPromise, new Promise<null>((_, reject) =>
            setTimeout(() => reject(new Error('Timeout')), 3000)
          ).catch(() => null)]),
          Promise.race([resourcesPromise, new Promise<null>((_, reject) =>
            setTimeout(() => reject(new Error('Timeout')), 3000)
          ).catch(() => null)]),
          Promise.race([procInfoPromise, new Promise<null>((_, reject) =>
            setTimeout(() => reject(new Error('Timeout')), 3000)
          ).catch(() => null)])
        ])

        serviceStatus.value = status
        systemResources.value = resources
        processInfo.value = procInfo

        // 只在启动时加载一次配置（避免频繁调用配置接口产生审计日志）
        if (!isConfigLoaded.value) {
          const configPromise = getAppConfig().catch(() => null)
          const config = await Promise.race([
            configPromise,
            new Promise<null>((_, reject) =>
              setTimeout(() => reject(new Error('Timeout')), 3000)
            ).catch(() => null)
          ])
          if (config?.success && config?.data) {
            serverConfig.value = config.data as ServerAppConfig
            isConfigLoaded.value = true
          }
        }
      } else {
        // 服务停止时清空服务端信息
        serviceStatus.value = null
        systemResources.value = null
        processInfo.value = null
        serverConfig.value = null
        isConfigLoaded.value = false
      }

      isInitialized.value = true
      lastRefreshTime.value = Date.now()
    } catch (err) {
      console.error('刷新服务状态失败:', err)
      // 静默处理错误，避免在压测环境下干扰用户
    } finally {
      isRefreshing.value = false
    }
  }

  /**
   * 启动自动刷新
   * @param interval 刷新间隔（毫秒），默认60000ms（1分钟）
   */
  let autoRefreshTimer: number | null = null

  function startAutoRefresh(interval: number = 60000): void {
    // 如果已经在自动刷新，不要重复启动
    if (autoRefreshTimer !== null) {
      return
    }
    // 立即执行一次
    refreshStatus()
    // 设置定时器
    autoRefreshTimer = window.setInterval(() => {
      refreshStatus()
    }, interval)
  }

  /**
   * 停止自动刷新
   */
  function stopAutoRefresh(): void {
    if (autoRefreshTimer) {
      clearInterval(autoRefreshTimer)
      autoRefreshTimer = null
    }
  }

  /**
   * 强制刷新服务端配置
   * 用于需要立即获取最新配置的场景（如设置页保存后）
   * 注意：此方法只在用户明确操作后调用，避免产生过多审计日志
   */
  async function refreshServerConfig(): Promise<void> {
    try {
      const config = await getAppConfig().catch(() => null)
      if (config?.success && config?.data) {
        serverConfig.value = config.data as ServerAppConfig
        isConfigLoaded.value = true
      }
    } catch (err) {
      console.error('刷新服务端配置失败:', err)
    }
  }

  /**
   * 重置状态（用于测试或重新初始化）
   */
  function reset(): void {
    stopAutoRefresh()
    isRunning.value = false
    serviceStatus.value = null
    systemResources.value = null
    processInfo.value = null
    localSystemInfo.value = null
    basicSystemInfo.value = null
    serverConfig.value = null
    isRefreshing.value = false
    isInitialized.value = false
    error.value = null
    lastRefreshTime.value = 0
    isConfigLoaded.value = false
  }

  // ============ 生命周期管理 ============
  // 在 store 创建时自动启动自动刷新
  onMounted(() => {
    // 默认 60 秒（1分钟）间隔自动刷新，减少审计日志产生
    startAutoRefresh(60000)
  })

  // 在 store 卸载时停止自动刷新
  onUnmounted(() => {
    stopAutoRefresh()
  })

  return {
    // State
    isRunning,
    serviceStatus,
    systemResources,
    processInfo,
    localSystemInfo,
    basicSystemInfo,
    serverConfig,
    isRefreshing,
    isInitialized,
    error,
    lastRefreshTime,
    // Getters
    statusText,
    statusClass,
    canRefresh,
    isServerProxyEnabled,
    // Actions
    refreshStatus,
    refreshServerConfig,
    startAutoRefresh,
    stopAutoRefresh,
    reset
  }
})
