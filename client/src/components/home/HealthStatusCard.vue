<script setup lang="ts">
import { computed, onMounted, onUnmounted } from 'vue'
import { storeToRefs } from 'pinia'
import Card from '../Card.vue'
import { useServiceStore } from '../../stores'

/**
 * 健康状态卡片组件
 *
 * 功能：显示系统健康状态
 * 数据来源：调用后端 /health 接口获取真实健康状态
 */

// 使用 Pinia store
const serviceStore = useServiceStore()
const { healthStatus: storeHealthStatus, isRunning: storeIsRunning } = storeToRefs(serviceStore)

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
})

onUnmounted(() => {
  if (healthCheckTimer) {
    clearInterval(healthCheckTimer)
    healthCheckTimer = null
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
    </div>
  </Card>
</template>

<style scoped>
@import '../../styles/home-components.css';
</style>
