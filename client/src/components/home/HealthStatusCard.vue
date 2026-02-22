<script setup lang="ts">
import { computed, onMounted, onUnmounted, watch } from 'vue'
import { storeToRefs } from 'pinia'
import Card from '../Card.vue'
import { useServiceStore } from '../../stores'
import { useDatabaseConnection } from '../../composables/useDatabaseConnection'

/**
 * 健康状态卡片组件
 *
 * 功能：显示系统健康状态和数据库连接状态
 * 数据来源：调用后端 /health 接口获取真实健康状态
 * 数据库连接：客户端本地测试
 */

// 使用 Pinia store
const serviceStore = useServiceStore()
const { healthStatus: storeHealthStatus, isRunning: storeIsRunning } = storeToRefs(serviceStore)

// 使用数据库连接 composable
const { state: dbConnectionState, badgeConfig: dbBadgeConfig, checkConnection: checkDbConnection } = useDatabaseConnection()

// 是否有健康状态
const hasHealthStatus = computed(() => {
  return storeIsRunning.value && storeHealthStatus.value !== null
})

// 健康状态数据
const healthStatus = computed(() => {
  return storeHealthStatus.value
})

// 定时刷新健康状态
let healthCheckTimer: number | null = null

onMounted(() => {
  // 立即刷新一次
  if (storeIsRunning.value) {
    serviceStore.refreshHealthStatus()
  }

  // 每 30 秒刷新一次健康状态
  healthCheckTimer = window.setInterval(() => {
    if (storeIsRunning.value) {
      serviceStore.refreshHealthStatus()
    }
  }, 30000)

  // 检查数据库连接
  checkDbConnection()
})

onUnmounted(() => {
  if (healthCheckTimer) {
    clearInterval(healthCheckTimer)
    healthCheckTimer = null
  }
})

// 监听服务状态变化，服务启动时刷新数据库连接
watch(storeIsRunning, (isRunning) => {
  if (isRunning) {
    checkDbConnection()
  }
})
</script>

<template>
  <Card v-if="hasHealthStatus" title="健康状态" custom-class="info-card health-card">
    <div class="health-grid">
      <div class="health-item">
        <span class="health-label">服务状态</span>
        <span class="health-value" :style="{ color: healthStatus?.status === 'healthy' ? 'var(--success-color)' : 'var(--error-color)' }">
          {{ healthStatus?.status === 'healthy' ? '健康' : '异常' }}
        </span>
      </div>
      <div class="health-item">
        <span class="health-label">服务名称</span>
        <span class="health-value">{{ healthStatus?.service || '-' }}</span>
      </div>
      <div class="health-item">
        <span class="health-label">检查时间</span>
        <span class="health-value" style="font-size: var(--font-size-xs);">
          {{ healthStatus?.timestamp ? new Date(healthStatus.timestamp).toLocaleTimeString('zh-CN') : '-' }}
        </span>
      </div>
      <!-- 数据库连接状态 -->
      <div class="health-item">
        <span class="health-label">数据库连接</span>
        <span
          class="health-value db-status-badge"
          :class="`db-status-${dbConnectionState.status}`"
        >
          {{ dbBadgeConfig.text }}
        </span>
      </div>
      <div v-if="dbConnectionState.dbType" class="health-item">
        <span class="health-label">数据库类型</span>
        <span class="health-value" style="text-transform: uppercase;">
          {{ dbConnectionState.dbType }}
        </span>
      </div>
      <div v-if="dbConnectionState.latency !== undefined" class="health-item">
        <span class="health-label">连接延迟</span>
        <span class="health-value">
          {{ dbConnectionState.latency }}ms
        </span>
      </div>
    </div>
  </Card>
</template>

<style scoped>
@import '../../styles/home-components.css';
</style>
