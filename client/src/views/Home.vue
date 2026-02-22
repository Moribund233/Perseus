<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { storeToRefs } from 'pinia'
import Alert from '../components/Alert.vue'
import { useServiceStore, useDatabaseStore } from '../stores'
import {
  startService,
  stopService,
  restartService,
  getDatabaseUrl
} from '../services/api'

// 导入拆分后的组件
import ServiceControlCard from '../components/home/ServiceControlCard.vue'
import PerformanceMonitor from '../components/home/PerformanceMonitor.vue'
import ProcessInfoCard from '../components/home/ProcessInfoCard.vue'
import SystemInfoCard from '../components/home/SystemInfoCard.vue'
import RequestStatsCard from '../components/home/RequestStatsCard.vue'
import GitStatusCard from '../components/home/GitStatusCard.vue'
import HealthStatusCard from '../components/home/HealthStatusCard.vue'
import MigrationProgressModal from '../components/home/MigrationProgressModal.vue'

// 导入事件总线
import { provideHomeEventBus } from '../composables/useHomeEvents'

/**
 * Home 控制台页面
 *
 * 功能模块：
 * 1. 服务控制 - 启动/停止/重启服务
 * 2. 性能监控 - CPU、内存、网络实时图表
 * 3. 系统信息 - 进程信息、系统信息、请求统计、Git状态、健康状态
 * 4. 数据库迁移 - 通过事件总线触发迁移弹窗
 *
 * 架构：使用事件总线模式，各组件独立管理自己的状态和逻辑
 */

// 创建并提供事件总线
const eventBus = provideHomeEventBus()

// 使用 Pinia store
const serviceStore = useServiceStore()
const { isRunning: storeIsRunning } = storeToRefs(serviceStore)

// 数据库 store
const databaseStore = useDatabaseStore()

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
          // 服务已启动，检查是否需要迁移
          await checkMigrationAfterStart()
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
 * 服务启动后检查迁移状态
 * 处理迁移、回退等逻辑
 */
const checkMigrationAfterStart = async (): Promise<void> => {
  try {
    const status = await databaseStore.checkMigrationStatus()
    if (!status) return

    // 检查是否需要回退
    if (status.rollback_required && status.rollback_to_type) {
      await handleRollback(status)
      return
    }

    // 检查是否需要迁移
    if (status.migration_required) {
      await handleMigration(status)
      return
    }

    // 检查上次迁移是否失败
    if (status.last_migration_failed && status.failed_target_type) {
      eventBus.setWarning(`上次迁移到 ${status.failed_target_type.toUpperCase()} 失败，请检查配置后重试`)
    }
  } catch (err) {
    console.error('检查迁移状态失败:', err)
  }
}

/**
 * 处理回退逻辑
 */
const handleRollback = async (status: any): Promise<void> => {
  const rollbackType = status.rollback_to_type as 'sqlite' | 'postgresql' | 'mysql'
  const currentType = status.target_db_type as 'sqlite' | 'postgresql' | 'mysql'

  console.warn(`检测到未确认的迁移，建议回退到: ${rollbackType}`)

  // 显示回退确认弹窗
  const confirmed = confirm(
    `检测到数据库类型变更未确认：\n` +
    `当前环境变量: ${currentType.toUpperCase()}\n` +
    `服务端记录: ${rollbackType.toUpperCase()}\n\n` +
    `是否回退到 ${rollbackType.toUpperCase()}？\n` +
    `（选择"确定"回退，选择"取消"继续使用当前类型）`
  )

  if (confirmed) {
    // 用户确认回退
    try {
      eventBus.setLoading(true)

      // 停止服务
      const stopResult = await stopService()
      if (!stopResult.success) {
        eventBus.setError('停止服务失败: ' + stopResult.message)
        return
      }

      // 等待服务停止
      await new Promise(resolve => setTimeout(resolve, 2000))

      // 修改客户端配置为回退类型
      const { switchDatabaseType } = await import('../services/api')
      await switchDatabaseType(rollbackType)

      // 重新启动服务
      const startResult = await startService()
      if (startResult.success) {
        eventBus.setSuccess(`已回退到 ${rollbackType.toUpperCase()}`)
      } else {
        eventBus.setError('回退失败: ' + startResult.message)
      }
    } catch (err) {
      eventBus.setError('回退过程出错: ' + String(err))
    } finally {
      eventBus.setLoading(false)
    }
  } else {
    // 用户选择不回退，显示警告
    eventBus.setWarning(`继续使用 ${currentType.toUpperCase()}，但数据可能不一致。建议尽快确认迁移或回退。`)
  }
}

/**
 * 处理迁移逻辑
 */
const handleMigration = async (status: any): Promise<void> => {
  const sourceType = status.current_db_type as 'sqlite' | 'postgresql' | 'mysql'
  const targetType = status.target_db_type as 'sqlite' | 'postgresql' | 'mysql'

  // 检查上次是否迁移失败到相同类型
  if (status.last_migration_failed && status.failed_target_type === targetType) {
    const retry = confirm(
      `上次迁移到 ${targetType.toUpperCase()} 失败。\n` +
      `是否重新尝试迁移？\n` +
      `（建议先检查数据库配置）`
    )
    if (!retry) {
      eventBus.setWarning('已取消迁移，服务可能无法正常使用')
      return
    }
  }

  try {
    const [sourceUrl, targetUrl] = await Promise.all([
      getDatabaseUrl(sourceType),
      getDatabaseUrl(targetType)
    ])

    // 通过事件总线触发显示迁移弹窗
    eventBus.emit('migration:show', {
      sourceType,
      targetType,
      sourceUrl,
      targetUrl
    })
  } catch (err) {
    console.error('获取数据库 URL 失败:', err)
    eventBus.setError('获取数据库 URL 失败，无法执行迁移')
  }
}

/**
 * 迁移完成处理
 */
const handleMigrationComplete = async (payload: { success: boolean }): Promise<void> => {
  if (payload.success) {
    // 刷新数据库配置
    await databaseStore.loadConfig()
    // 显示成功消息
    eventBus.setSuccess('数据库迁移完成，服务已更新')
    setTimeout(() => {
      eventBus.clearSuccess()
    }, 5000)
  } else {
    // 迁移失败或取消
    console.log('数据库迁移未完成')
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
  eventBus.on('migration:complete', handleMigrationComplete)

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
  eventBus.off('migration:complete', handleMigrationComplete)
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

    <!-- 迁移进度弹窗 - 独立组件，通过事件总线控制 -->
    <MigrationProgressModal />
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

.info-section {
  margin-top: var(--spacing-lg);
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: var(--spacing-lg);
}

@media (max-width: 768px) {
  .home {
    padding: var(--spacing-md);
  }

  .info-grid {
    grid-template-columns: 1fr;
  }
}
</style>
