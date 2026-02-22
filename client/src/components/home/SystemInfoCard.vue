<script setup lang="ts">
import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import Card from '../Card.vue'
import { useServiceStore } from '../../stores'

/**
 * 系统信息卡片组件
 *
 * 功能：显示基础系统信息
 */

// 使用 Pinia store
const serviceStore = useServiceStore()
const { basicSystemInfo: storeBasicSystemInfo, isRunning: storeIsRunning } = storeToRefs(serviceStore)

// 是否有系统信息
const hasSystemInfo = computed(() => {
  return storeIsRunning.value && storeBasicSystemInfo.value
})

/**
 * 格式化内存大小
 * @param gb - 内存大小（GB）
 * @returns 格式化后的字符串
 */
const formatMemoryGB = (gb?: number): string => {
  if (gb === undefined || gb === null) return '-'
  return `${gb.toFixed(2)} GB`
}
</script>

<template>
  <Card v-if="hasSystemInfo" title="系统信息" custom-class="info-card system-card">
    <div class="info-list">
      <div class="info-item">
        <span class="info-label">操作系统</span>
        <span class="info-value">{{ storeBasicSystemInfo?.platform || '-' }}</span>
      </div>
      <div class="info-item">
        <span class="info-label">主机名</span>
        <span class="info-value">{{ storeBasicSystemInfo?.hostname || '-' }}</span>
      </div>
      <div class="info-item">
        <span class="info-label">CPU 核心数</span>
        <span class="info-value">{{ storeBasicSystemInfo?.cpuCount || '-' }}</span>
      </div>
      <div class="info-item">
        <span class="info-label">总内存</span>
        <span class="info-value">{{ formatMemoryGB(storeBasicSystemInfo?.memoryTotalGB) }}</span>
      </div>
      <div class="info-item">
        <span class="info-label">架构</span>
        <span class="info-value">{{ storeBasicSystemInfo?.architecture || '-' }}</span>
      </div>
    </div>
  </Card>
</template>

<style scoped>
@import '../../styles/home-components.css';
</style>
