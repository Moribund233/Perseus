<script setup lang="ts">
import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import Card from '../Card.vue'
import { useServiceStore } from '../../stores'

/**
 * 请求统计卡片组件
 *
 * 功能：显示服务端请求统计信息
 */

// 使用 Pinia store
const serviceStore = useServiceStore()
const { serviceStatus: storeServiceStatus, isRunning: storeIsRunning } = storeToRefs(serviceStore)

// 是否有请求统计
const hasRequestStats = computed(() => {
  return storeIsRunning.value && storeServiceStatus.value?.requests
})

// 请求统计数据
const requestStats = computed(() => {
  return storeServiceStatus.value?.requests || { total: 0, success: 0, failed: 0 }
})

/**
 * 获取请求成功率
 * @returns 成功率百分比
 */
const getSuccessRate = (): number => {
  const { total, success } = requestStats.value
  if (total === 0) return 100
  return (success / total) * 100
}
</script>

<template>
  <Card v-if="hasRequestStats" title="请求统计" custom-class="info-card requests-card">
    <div class="requests-grid">
      <div class="request-metric">
        <span class="request-value">{{ requestStats.total }}</span>
        <span class="request-label">总请求</span>
      </div>
      <div class="request-metric">
        <span class="request-value" style="color: var(--success-color)">{{ requestStats.success }}</span>
        <span class="request-label">成功</span>
      </div>
      <div class="request-metric">
        <span class="request-value" style="color: var(--error-color)">{{ requestStats.failed }}</span>
        <span class="request-label">失败</span>
      </div>
      <div class="request-metric">
        <span class="request-value">{{ getSuccessRate().toFixed(1) }}%</span>
        <span class="request-label">成功率</span>
      </div>
    </div>
  </Card>
</template>

<style scoped>
@import '../../styles/home-components.css';
</style>
