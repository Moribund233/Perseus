<script setup lang="ts">
import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import Card from '../Card.vue'
import { useServiceStore } from '../../stores'

/**
 * 进程信息卡片组件
 *
 * 功能：显示服务端进程详细信息
 */

// 使用 Pinia store
const serviceStore = useServiceStore()
const { serviceStatus: storeServiceStatus, isRunning: storeIsRunning } = storeToRefs(serviceStore)

// 是否有进程信息
const hasProcessInfo = computed(() => {
  return storeIsRunning.value && storeServiceStatus.value?.process
})

/**
 * 格式化内存大小
 * @param mb - 内存大小（MB）
 * @returns 格式化后的字符串
 */
const formatMemory = (mb?: number): string => {
  if (mb === undefined || mb === null) return '-'
  if (mb >= 1024) {
    return `${(mb / 1024).toFixed(2)} GB`
  }
  return `${mb.toFixed(1)} MB`
}
</script>

<template>
  <Card v-if="hasProcessInfo" title="进程信息" custom-class="info-card process-card">
    <div class="info-list">
      <div class="info-item">
        <span class="info-label">进程 ID</span>
        <span class="info-value">{{ storeServiceStatus?.process?.pid || '-' }}</span>
      </div>
      <div class="info-item">
        <span class="info-label">CPU 使用率</span>
        <span class="info-value">{{ storeServiceStatus?.process?.cpu_percent?.toFixed(1) || '0.0' }}%</span>
      </div>
      <div class="info-item">
        <span class="info-label">内存使用</span>
        <span class="info-value">{{ formatMemory(storeServiceStatus?.process?.memory_mb) }}</span>
      </div>
      <div class="info-item">
        <span class="info-label">连接数</span>
        <span class="info-value">{{ storeServiceStatus?.process?.connections || '-' }}</span>
      </div>
      <div class="info-item">
        <span class="info-label">线程数</span>
        <span class="info-value">{{ storeServiceStatus?.process?.threads || '-' }}</span>
      </div>
    </div>
  </Card>
</template>

<style scoped>
@import '../../styles/home-components.css';
</style>
