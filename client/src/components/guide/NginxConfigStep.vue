<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import Button from '../Button.vue'
import {
  getNginxStatus,
  loadNginx,
  downloadAndExtractNginx,
  updateNginxDownloadUrl,
  getNginxPlatformInfo,
  type NginxPlatformInfo
} from '../../services/api'
import { useGuideEventBus } from '../../composables/useGuideEvents'

/**
 * Nginx配置步骤组件
 *
 * 功能：提供Nginx的手动载入或自动下载配置
 * 状态管理：通过事件总线与Guide主组件通信
 */

const eventBus = useGuideEventBus()

// 从事件总线获取状态
const state = eventBus.state.value.nginxConfig

// 本地状态
const nginxDownloadUrl = ref('https://nginx.org/download/nginx-1.24.0.zip')
const isLoading = ref(false)
const isNginxDownloading = ref(false)
const nginxPlatformInfo = ref<NginxPlatformInfo | null>(null)

// Nginx平台相关计算属性
const supportsNginxManualLoad = computed(() => {
  return nginxPlatformInfo.value?.supports_manual_load ?? false
})

const supportsNginxDownload = computed(() => {
  return nginxPlatformInfo.value?.supports_download ?? false
})

const nginxPlatformDisplayText = computed(() => {
  if (!nginxPlatformInfo.value) return ''
  if (nginxPlatformInfo.value.uses_package_manager) {
    const pm = nginxPlatformInfo.value.package_manager || '包管理器'
    return `（通过${pm}管理）`
  }
  return ''
})

/**
 * 检查Nginx状态
 */
async function checkNginx(): Promise<void> {
  try {
    const status = await getNginxStatus()
    if (status.is_loaded) {
      eventBus.updateNginxConfig({ status: 'loaded' })
      eventBus.emit('step:complete', { step: 2 })
    }
  } catch (e) {
    console.error('检查Nginx失败:', e)
  }
}

/**
 * 加载Nginx平台信息
 */
async function loadNginxPlatformInfo(): Promise<void> {
  try {
    nginxPlatformInfo.value = await getNginxPlatformInfo()
  } catch (e) {
    console.error('获取Nginx平台信息失败:', e)
  }
}

/**
 * 手动载入Nginx
 * 通过文件对话框选择Nginx可执行文件
 */
async function loadNginxManually(): Promise<void> {
  try {
    const { open } = await import('@tauri-apps/plugin-dialog')
    const selected = await open({
      multiple: false
    })

    if (selected && typeof selected === 'string') {
      isLoading.value = true
      eventBus.clearError()

      try {
        const result = await loadNginx(selected)
        if (result.success) {
          eventBus.updateNginxConfig({ status: 'loaded' })
          eventBus.emit('step:complete', { step: 2 })
        } else {
          eventBus.setError(result.message)
        }
      } catch (e) {
        eventBus.setError('载入Nginx失败: ' + String(e))
        console.error('载入Nginx失败:', e)
      } finally {
        isLoading.value = false
      }
    }
  } catch (e) {
    eventBus.setError('选择文件失败: ' + String(e))
    console.error('选择文件失败:', e)
  }
}

/**
 * 自动下载并配置Nginx
 */
async function downloadNginx(): Promise<void> {
  isNginxDownloading.value = true
  eventBus.clearError()

  try {
    await updateNginxDownloadUrl(nginxDownloadUrl.value)
    const result = await downloadAndExtractNginx(nginxDownloadUrl.value)

    if (result.success) {
      eventBus.updateNginxConfig({ status: 'loaded' })
      eventBus.emit('step:complete', { step: 2 })
    } else {
      eventBus.setError(result.message)
    }
  } catch (e) {
    eventBus.setError('下载Nginx失败: ' + String(e))
    console.error('下载Nginx失败:', e)
  } finally {
    isNginxDownloading.value = false
  }
}

/**
 * 跳过Nginx配置
 */
function skipNginx(): void {
  eventBus.updateNginxConfig({ status: 'skipped' })
  eventBus.emit('step:skip', { step: 2 })
  eventBus.emit('nav:next', undefined)
}

// 组件挂载时加载平台信息
onMounted(() => {
  checkNginx()
  loadNginxPlatformInfo()
})
</script>

<template>
  <div class="step-content">
    <h2 class="step-heading">配置Nginx（可选）</h2>
    <p class="step-text">Nginx可作为反向代理，提供更好的性能和安全性</p>

    <div v-if="state.status === 'loaded'" class="status-box success">
      <img src="../../assets/icons/success.svg" class="status-icon" alt="success" />
      <span>Nginx已载入</span>
    </div>

    <div v-else-if="state.status === 'skipped'" class="status-box info">
      <img src="../../assets/icons/info.svg" class="status-icon" alt="info" />
      <span>已跳过Nginx配置，稍后可在设置中配置</span>
    </div>

    <div v-else class="nginx-options">
      <!-- 手动载入选项 - 仅Windows支持 -->
      <div v-if="supportsNginxManualLoad" class="option-group">
        <h3>选项1: 手动载入</h3>
        <p class="option-desc">如果您已安装Nginx，请选择可执行文件</p>
        <Button type="secondary" :loading="isLoading" @click="loadNginxManually">
          选择Nginx文件
        </Button>
      </div>

      <div v-if="supportsNginxManualLoad && supportsNginxDownload" class="option-divider">或</div>

      <!-- 自动下载选项 - 仅Windows支持 -->
      <div v-if="supportsNginxDownload" class="option-group">
        <h3>选项2: 自动下载</h3>
        <p class="option-desc">自动下载并配置Nginx（推荐）</p>
        <input
          v-model="nginxDownloadUrl"
          type="text"
          class="url-input"
          placeholder="下载地址"
        />
        <Button
          type="primary"
          :loading="isNginxDownloading"
          @click="downloadNginx"
        >
          下载并配置
        </Button>
      </div>

      <!-- Linux平台提示 -->
      <div v-if="!supportsNginxManualLoad && !supportsNginxDownload" class="option-group">
        <h3>Nginx配置</h3>
        <p class="option-desc">
          在Linux系统上，Nginx通过包管理器安装和管理{{ nginxPlatformDisplayText }}
        </p>
        <p class="option-desc">
          请使用系统包管理器安装Nginx，系统将自动检测并使用系统Nginx。
        </p>
      </div>
    </div>

    <div v-if="state.status !== 'loaded'" class="action-row">
      <Button type="secondary" @click="skipNginx">
        跳过此步骤
      </Button>
    </div>
  </div>
</template>

<style scoped>
@import '../../styles/guide-steps.css';
</style>
