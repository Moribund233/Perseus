<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { storeToRefs } from 'pinia'
import Alert from '../components/Alert.vue'
import { useServiceStore } from '../stores'
import {
  startService,
  stopService,
  restartService
} from '../services/api'

// 导入拆分后的组件
import ServiceControlCard from '../components/home/ServiceControlCard.vue'
import PerformanceMonitor from '../components/home/PerformanceMonitor.vue'
import ProcessInfoCard from '../components/home/ProcessInfoCard.vue'
import SystemInfoCard from '../components/home/SystemInfoCard.vue'
import RequestStatsCard from '../components/home/RequestStatsCard.vue'
import GitStatusCard from '../components/home/GitStatusCard.vue'
import HealthStatusCard from '../components/home/HealthStatusCard.vue'

// 导入事件总线
import { provideHomeEventBus } from '../composables/useHomeEvents'

/**
 * Home 控制台页面
 *
 * 功能模块：
 * 1. 服务控制 - 启动/停止/重启服务
 * 2. 性能监控 - CPU、内存、网络实时图表
 * 3. 系统信息 - 进程信息、系统信息、请求统计、Git状态、健康状态
 *
 * 架构：使用事件总线模式，各组件独立管理自己的状态和逻辑
 */

// 创建并提供事件总线
const eventBus = provideHomeEventBus()

// 使用 Pinia store
const serviceStore = useServiceStore()
const { isRunning: storeIsRunning } = storeToRefs(serviceStore)

// 状态引用
const state = eventBus.state.value.service

// ==================== 服务控制逻辑 ====================

/**
 * 刷新服务状态
 */
const handleRefreshStatus = async (): Promise<void> => {
  await serviceStore.refreshStatus()
}

/**
 * 启动服务
 */
const handleStartService = async (): Promise<void> => {
  if (state.isLoading || storeIsRunning.value) return

  eventBus.setLoading(true)
  eventBus.clearError()

  try {
    const result = await startService()

    if (result.success) {
      // 轮询检查服务状态，最多等待15秒
      let attempts = 0
      const maxAttempts = 30

      while (attempts < maxAttempts) {
        await new Promise((resolve) => setTimeout(resolve, 500))
        await serviceStore.refreshStatus(true)

        if (storeIsRunning.value) {
          break
        }
        attempts++
      }

      if (!storeIsRunning.value) {
        eventBus.setError('服务启动超时，请手动刷新状态')
      }
    } else {
      eventBus.setError(result.message)
    }
  } catch (err) {
    eventBus.setError('启动服务失败: ' + String(err))
  } finally {
    eventBus.setLoading(false)
  }
}

/**
 * 停止服务
 */
const handleStopService = async (): Promise<void> => {
  if (state.isLoading || !storeIsRunning.value) return

  eventBus.setLoading(true)
  eventBus.clearError()

  try {
    const result = await stopService()

    if (result.success) {
      // 轮询检查服务状态，最多等待10秒
      let attempts = 0
      const maxAttempts = 20

      while (attempts < maxAttempts) {
        await new Promise((resolve) => setTimeout(resolve, 500))
        await serviceStore.refreshStatus(true)

        if (!storeIsRunning.value) {
          // 服务已停止
          break
        }
        attempts++
      }

      if (storeIsRunning.value) {
        eventBus.setError('服务停止超时，请手动刷新状态')
      }
    } else {
      eventBus.setError(result.message)
    }
  } catch (err) {
    eventBus.setError('停止服务失败: ' + String(err))
  } finally {
    eventBus.setLoading(false)
  }
}

/**
 * 重启服务
 */
const handleRestartService = async (): Promise<void> => {
  if (state.isLoading) return

  eventBus.setLoading(true)
  eventBus.clearError()

  try {
    const result = await restartService()

    if (result.success) {
      // 等待服务重启
      await new Promise((resolve) => setTimeout(resolve, 5000))
      await serviceStore.refreshStatus()
    } else {
      eventBus.setError(result.message)
    }
  } catch (err) {
    eventBus.setError('重启服务失败: ' + String(err))
  } finally {
    eventBus.setLoading(false)
  }
}

/**
 * 开始定时刷新
 * 使用 Pinia store 的本地系统信息自动刷新方法（2秒间隔，不访问服务端）
 */
const startAutoRefresh = (): void => {
  serviceStore.startLocalSystemInfoRefresh(2000)
}

// ==================== 事件监听 ====================

onMounted(() => {
  // 注册事件监听
  eventBus.on('service:refresh', handleRefreshStatus)
  eventBus.on('service:start', handleStartService)
  eventBus.on('service:stop', handleStopService)
  eventBus.on('service:restart', handleRestartService)

  // 初始化服务状态
  if (!serviceStore.isRefreshing) {
    serviceStore.refreshStatus()
  }
  startAutoRefresh()
})

onUnmounted(() => {
  // 清理事件监听
  eventBus.off('service:refresh', handleRefreshStatus)
  eventBus.off('service:start', handleStartService)
  eventBus.off('service:stop', handleStopService)
  eventBus.off('service:restart', handleRestartService)
})
</script>

<template>
  <div class="home">
    <h1 class="page-title">控制台</h1>

    <!-- 错误提示 -->
    <Alert v-if="state.error" type="error" closable @close="eventBus.clearError()">
      {{ state.error }}
    </Alert>

    <!-- 成功提示 -->
    <Alert v-if="state.successMessage" type="success" closable @close="eventBus.clearSuccess()">
      {{ state.successMessage }}
    </Alert>

    <!-- 警告提示 -->
    <Alert v-if="state.warningMessage" type="warning" closable @close="eventBus.clearWarning()">
      {{ state.warningMessage }}
    </Alert>

    <!-- 服务控制卡片 -->
    <ServiceControlCard />

    <!-- 性能监控 -->
    <PerformanceMonitor />

    <!-- 详细信息网格（仅服务运行时显示） -->
    <div class="info-section">
      <div class="info-grid">
        <ProcessInfoCard />
        <SystemInfoCard />
        <RequestStatsCard />
        <GitStatusCard />
        <HealthStatusCard />
      </div>
    </div>
  </div>
</template>

<style scoped>
.home {
  padding: var(--spacing-lg);
  max-width: 1400px;
  margin: 0 auto;
}

.page-title {
  margin: 0 0 var(--spacing-lg);
  font-size: var(--font-size-2xl);
  font-weight: 600;
  color: var(--text-primary);
}
</style>
