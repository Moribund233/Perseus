<script setup lang="ts">
import { computed, ref, onMounted, watch } from 'vue'
import { storeToRefs } from 'pinia'
import Card from '../Card.vue'
import StatusBadge from '../StatusBadge.vue'
import { useServiceStore } from '../../stores'
import { useHomeEventBus } from '../../composables/useHomeEvents'
import { getDebugMode, getStressTest, getNginxStatus, type NginxStatusResponse } from '../../services/api'

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

// 功能状态
const featureStatus = ref({
  debugMode: false,
  stressTest: false,
  nginxStatus: null as NginxStatusResponse | null
})

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

/**
 * 加载功能状态
 */
const loadFeatureStatus = async (): Promise<void> => {
  if (!storeIsRunning.value) {
    featureStatus.value.debugMode = false
    featureStatus.value.stressTest = false
    featureStatus.value.nginxStatus = null
    return
  }
  try {
    const [debugMode, stressTest, nginxStatus] = await Promise.all([
      getDebugMode(),
      getStressTest(),
      getNginxStatus()
    ])
    featureStatus.value.debugMode = debugMode
    featureStatus.value.stressTest = stressTest
    featureStatus.value.nginxStatus = nginxStatus
  } catch (err) {
    console.error('加载功能状态失败:', err)
  }
}

// 监听服务状态变化，自动刷新功能状态
watch(storeIsRunning, (isRunning) => {
  if (isRunning) {
    loadFeatureStatus()
  } else {
    featureStatus.value.debugMode = false
    featureStatus.value.stressTest = false
    featureStatus.value.nginxStatus = null
  }
})

// 组件挂载时加载功能状态
onMounted(() => {
  loadFeatureStatus()
})
</script>

<template>
  <Card title="服务状态" custom-class="service-card">
    <template #header>
      <div class="service-info">
        <StatusBadge :status="serviceStatus || 'default'" />
        <!-- 功能状态标签 -->
        <div v-if="storeIsRunning" class="feature-tags">
          <span v-if="featureStatus.debugMode" class="feature-tag tag-debug">调试</span>
          <span v-if="featureStatus.stressTest" class="feature-tag tag-stress">压测</span>
          <span v-if="featureStatus.nginxStatus?.status === 'running'" class="feature-tag tag-nginx">Nginx</span>
        </div>
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

/* 功能状态标签 */
.feature-tags {
  display: flex;
  gap: var(--spacing-xs);
  margin-left: var(--spacing-sm);
}

.feature-tag {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: var(--border-radius-sm);
  font-size: var(--font-size-xs);
  font-weight: 500;
}

.tag-debug {
  background-color: var(--warning-color);
  color: white;
}

.tag-stress {
  background-color: var(--error-color);
  color: white;
}

.tag-nginx {
  background-color: var(--success-color);
  color: white;
}
</style>
