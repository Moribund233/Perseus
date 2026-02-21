<script setup lang="ts">
import { onMounted } from 'vue'
import Button from '../Button.vue'
import {
  checkServerPath,
  validateAndSaveServerPath
} from '../../services/api'
import { useGuideEventBus } from '../../composables/useGuideEvents'

/**
 * 服务端检查步骤组件
 *
 * 功能：检测或手动指定服务端可执行文件路径
 * 状态管理：通过事件总线与Guide主组件通信
 */

const eventBus = useGuideEventBus()

// 从事件总线获取状态
const state = eventBus.state.value.serverCheck

/**
 * 检查服务端路径
 * 自动检测默认路径下是否存在服务端可执行文件
 */
async function checkServer(): Promise<void> {
  eventBus.updateServerCheck({ status: 'checking' })
  eventBus.clearError()

  try {
    const result = await checkServerPath()
    if (result.found) {
      eventBus.updateServerCheck({
        path: result.path || '',
        status: 'found'
      })
      // 触发步骤完成事件（步骤2）
      eventBus.emit('step:complete', { step: 2, data: result.path })
    } else {
      eventBus.updateServerCheck({ status: 'not_found' })
    }
  } catch (e) {
    eventBus.updateServerCheck({ status: 'not_found' })
    console.error('检查服务端失败:', e)
  }
}

/**
 * 手动选择服务端文件路径
 * 通过系统文件对话框让用户选择服务端可执行文件
 */
async function selectServerPath(): Promise<void> {
  try {
    const { open } = await import('@tauri-apps/plugin-dialog')
    const selected = await open({
      multiple: false
    })

    if (selected && typeof selected === 'string') {
      try {
        await validateAndSaveServerPath(selected)
        eventBus.updateServerCheck({
          path: selected,
          status: 'found'
        })
        // 触发步骤完成事件（步骤2）
        eventBus.emit('step:complete', { step: 2, data: selected })
      } catch (e) {
        eventBus.setError('验证服务端路径失败: ' + String(e))
        console.error('验证服务端路径失败:', e)
      }
    }
  } catch (e) {
    eventBus.setError('选择文件失败: ' + String(e))
    console.error('选择文件失败:', e)
  }
}

// 组件挂载时自动检查
onMounted(() => {
  if (state.status === 'idle') {
    checkServer()
  }
})
</script>

<template>
  <div class="step-content">
    <h2 class="step-heading">配置服务端</h2>
    <p class="step-text">需要指定LanGit服务端可执行文件的位置</p>

    <div v-if="state.status === 'checking'" class="status-box">
      <span class="loading-text">正在检查默认路径...</span>
    </div>

    <div v-else-if="state.status === 'found'" class="status-box success">
      <img src="../../assets/icons/success.svg" class="status-icon" alt="success" />
      <span>已找到服务端: {{ state.path }}</span>
    </div>

    <div v-else class="status-box warning">
      <img src="../../assets/icons/warning.svg" class="status-icon" alt="warning" />
      <span>未在默认路径找到服务端，请手动指定</span>
    </div>

    <div class="action-row">
      <Button
        type="primary"
        @click="selectServerPath"
      >
        选择服务端文件
      </Button>
      <Button
        v-if="state.status === 'not_found'"
        type="secondary"
        @click="checkServer"
      >
        重新检查
      </Button>
    </div>
  </div>
</template>

<style scoped>
@import '../../styles/guide-steps.css';
</style>
