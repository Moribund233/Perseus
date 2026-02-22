<script setup lang="ts">
import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import Card from '../Card.vue'
import { useServiceStore } from '../../stores'

/**
 * Git 状态卡片组件
 *
 * 功能：显示 Git 操作状态统计
 */

// 使用 Pinia store
const serviceStore = useServiceStore()
const { serviceStatus: storeServiceStatus, isRunning: storeIsRunning } = storeToRefs(serviceStore)

// 是否有 Git 状态
const hasGitStatus = computed(() => {
  return storeIsRunning.value && storeServiceStatus.value?.git_operations
})

// Git 状态数据
const gitStatus = computed(() => {
  return storeServiceStatus.value?.git_operations || { active_clones: 0, active_pushes: 0, queue_size: 0 }
})
</script>

<template>
  <Card v-if="hasGitStatus" title="Git 状态" custom-class="info-card git-card">
    <div class="git-grid">
      <div class="git-metric">
        <div class="git-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="3" />
            <path d="M12 1v6m0 6v6m4.22-10.22l4.24-4.24M6.34 6.34L2.1 2.1m17.8 17.8l-4.24-4.24M6.34 17.66l-4.24 4.24M23 12h-6m-6 0H1m20.24-4.24l-4.24 4.24M6.34 6.34l-4.24-4.24" />
          </svg>
        </div>
        <div class="git-info">
          <span class="git-value">{{ gitStatus.active_clones }}</span>
          <span class="git-label">克隆中</span>
        </div>
      </div>
      <div class="git-metric">
        <div class="git-icon push">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 19V5M5 12l7-7 7 7" />
          </svg>
        </div>
        <div class="git-info">
          <span class="git-value">{{ gitStatus.active_pushes }}</span>
          <span class="git-label">推送中</span>
        </div>
      </div>
      <div class="git-metric">
        <div class="git-icon queue">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 2v4m0 12v4M4.93 4.93l2.83 2.83m8.48 8.48l2.83 2.83M2 12h4m12 0h4M4.93 19.07l2.83-2.83m8.48-8.48l2.83-2.83" />
          </svg>
        </div>
        <div class="git-info">
          <span class="git-value">{{ gitStatus.queue_size }}</span>
          <span class="git-label">队列大小</span>
        </div>
      </div>
    </div>
  </Card>
</template>

<style scoped>
@import '../../styles/home-components.css';
</style>
