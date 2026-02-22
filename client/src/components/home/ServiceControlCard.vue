<script setup lang="ts">
import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import Card from '../Card.vue'
import StatusBadge from '../StatusBadge.vue'
import { useServiceStore } from '../../stores'
import { useHomeEventBus } from '../../composables/useHomeEvents'

/**
 * 服务控制卡片组件
 *
 * 功能：显示服务状态、控制服务启停
 * 通信：通过事件总线与 Home 主组件交互
 */

// 图标路径
const refreshIcon = new URL('../../assets/icons/refresh.svg', import.meta.url).href
const playIcon = new URL('../../assets/icons/play.svg', import.meta.url).href
const stopIcon = new URL('../../assets/icons/stop.svg', import.meta.url).href

// 使用 Pinia store 管理服务状态
const serviceStore = useServiceStore()
const { isRunning: storeIsRunning, isInitialized: storeIsInitialized } = storeToRefs(serviceStore)

// 使用事件总线
const eventBus = useHomeEventBus()
const state = eventBus.state.value.service

// 服务状态类型
type ServiceStatusType = 'running' | 'stopped' | 'starting' | 'stopping'

// 计算属性：服务状态
const serviceStatus = computed<ServiceStatusType | null>(() => {
  if (!storeIsInitialized.value) return null
  return storeIsRunning.value ? 'running' : 'stopped'
})

/**
 * 刷新服务状态
 */
const handleRefresh = async (): Promise<void> => {
  eventBus.emit('service:refresh')
}

/**
 * 启动服务
 */
const handleStart = async (): Promise<void> => {
  if (state.isLoading || storeIsRunning.value) return
  eventBus.emit('service:start')
}

/**
 * 停止服务
 */
const handleStop = async (): Promise<void> => {
  if (state.isLoading || !storeIsRunning.value) return
  eventBus.emit('service:stop')
}

/**
 * 重启服务
 */
const handleRestart = async (): Promise<void> => {
  if (state.isLoading) return
  eventBus.emit('service:restart')
}
</script>

<template>
  <Card title="服务状态" custom-class="service-card">
    <template #header>
      <div class="service-info">
        <StatusBadge :status="serviceStatus || 'default'" />
      </div>
    </template>
    <template #actions>
      <button class="btn btn-secondary btn-sm" @click="handleRefresh" :disabled="state.isLoading">
        <img :src="refreshIcon" class="btn-icon" :class="{ spinning: state.isLoading }" alt="refresh" />
        刷新
      </button>
    </template>

    <div class="service-controls">
      <button
        class="btn btn-success"
        @click="handleStart"
        :disabled="state.isLoading || serviceStatus === 'running' || serviceStatus === 'starting' || serviceStatus === null"
      >
        <img :src="playIcon" class="btn-icon icon-white" alt="play" />
        启动服务
      </button>

      <button
        class="btn btn-error"
        @click="handleStop"
        :disabled="state.isLoading || serviceStatus === 'stopped' || serviceStatus === 'stopping' || serviceStatus === null"
      >
        <img :src="stopIcon" class="btn-icon icon-white" alt="stop" />
        停止服务
      </button>

      <button
        class="btn btn-warning"
        @click="handleRestart"
        :disabled="state.isLoading || serviceStatus !== 'running'"
      >
        <img :src="refreshIcon" class="btn-icon icon-white" alt="restart" />
        重启服务
      </button>
    </div>

    <div v-if="state.isLoading" class="loading-indicator">
      <div class="spinner"></div>
      <span>正在处理...</span>
    </div>
  </Card>
</template>

<style scoped>
@import '../../styles/home-components.css';
</style>
