<script setup lang="ts">
import { onMounted } from 'vue'
import Button from '../Button.vue'
import { checkGitInstallation } from '../../services/api'
import { useGuideEventBus } from '../../composables/useGuideEvents'

/**
 * Git检查步骤组件
 *
 * 功能：验证系统Git环境是否已安装
 * 状态管理：通过事件总线与Guide主组件通信
 */

const eventBus = useGuideEventBus()

// 从事件总线获取状态
const state = eventBus.state.value.gitCheck

/**
 * 检查Git安装状态
 * 检测系统中是否已安装Git并获取版本信息
 */
async function checkGit(): Promise<void> {
  eventBus.updateGitCheck({ status: 'checking' })

  try {
    const result = await checkGitInstallation()

    if (result.installed) {
      eventBus.updateGitCheck({
        status: 'installed',
        version: result.version || ''
      })
      // 触发步骤完成事件
      eventBus.emit('step:complete', { step: 3, data: result.version })
    } else {
      eventBus.updateGitCheck({ status: 'not_installed' })
    }
  } catch (e) {
    eventBus.updateGitCheck({ status: 'not_installed' })
    console.error('检查Git失败:', e)
  }
}

/**
 * 跳过Git检查
 */
function skipGit(): void {
  eventBus.emit('step:skip', { step: 3 })
  eventBus.emit('nav:next', undefined)
}

// 组件挂载时自动检查
onMounted(() => {
  if (state.status === 'idle') {
    checkGit()
  }
})
</script>

<template>
  <div class="step-content">
    <h2 class="step-heading">检查Git环境</h2>
    <p class="step-text">Git是服务端HTTP服务的必需依赖</p>

    <div v-if="state.status === 'checking'" class="status-box">
      <span class="loading-text">正在检查Git安装...</span>
    </div>

    <div v-else-if="state.status === 'installed'" class="status-box success">
      <img src="../../assets/icons/success.svg" class="status-icon" alt="success" />
      <span>Git已安装: {{ state.version }}</span>
    </div>

    <div v-else class="status-box error">
      <img src="../../assets/icons/error.svg" class="status-icon" alt="error" />
      <div>
        <div>未检测到Git安装</div>
        <div class="install-help">
          请访问 <a href="https://git-scm.com/downloads" target="_blank">git-scm.com</a> 下载安装
        </div>
      </div>
    </div>

    <div class="action-row">
      <Button
        type="secondary"
        @click="checkGit"
        :disabled="state.status === 'checking'"
      >
        重新检查
      </Button>
      <Button
        v-if="state.status === 'not_installed'"
        type="warning"
        @click="skipGit"
      >
        跳过（不推荐）
      </Button>
    </div>
  </div>
</template>

<style scoped>
@import '../../styles/guide-steps.css';
</style>
