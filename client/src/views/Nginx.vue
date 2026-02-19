<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import {
  getNginxStatus,
  loadNginx,
  startNginx,
  stopNginx,
  restartNginx,
  downloadAndExtractNginx,
  getNginxDownloadUrl,
  updateNginxDownloadUrl,
  getNginxProxyConfig,
  saveNginxProxyConfig,
  getNginxPlatformInfo,
  type NginxStatusResponse,
  type NginxProxyConfig,
  type NginxPlatformInfo
} from '../services/api'
import { useServiceStore } from '../stores/service'

/**
 * Nginx管理页面
 * 
 * 功能：
 * 1. 载入Nginx：选择Nginx可执行文件路径，验证并保存配置
 * 2. 下载Nginx：从指定URL下载并自动解压Nginx
 * 3. 控制Nginx：启动、停止、重启
 * 4. 代理配置：配置反向代理、安全头、CORS等
 */

// 状态
const status = ref<NginxStatusResponse | null>(null)
const isLoading = ref(false)
const isDownloading = ref(false)
const message = ref<string | null>(null)
const messageType = ref<'success' | 'error' | 'info'>('info')

// 平台信息
const platformInfo = ref<NginxPlatformInfo | null>(null)

// 下载配置
const downloadUrl = ref('')
const defaultDownloadUrl = 'https://nginx.org/download/nginx-1.24.0.zip'
const mirrorUrls = [
  { name: '官方源', url: 'https://nginx.org/download/nginx-1.24.0.zip' },
  { name: 'GitHub镜像', url: 'https://github.com/nginx/nginx/releases/download/release-1.24.0/nginx-1.24.0.zip' }
]

// 显示下载对话框
const showDownloadDialog = ref(false)

// 代理配置（默认值与服务端proxy.proxy=true保持一致）
const proxyConfig = ref<NginxProxyConfig>({
  enabled: true,
  listen_port: 80,
  backend_url: 'http://127.0.0.1:8000',
  add_security_headers: true,
  add_cors_headers: true,
  cors_origins: '*',
  cors_methods: 'GET, POST, PUT, DELETE, OPTIONS',
  cors_headers: 'Content-Type, Authorization',
  enable_hsts: false,
  hsts_max_age: 31536000,
  server_name: '_'
})
const isSavingConfig = ref(false)

// 获取Service Store
const serviceStore = useServiceStore()

// 安全头和CORS是否强制启用（当Nginx启用反向代理时强制启用）
const isSecurityHeadersForced = computed(() => proxyConfig.value.enabled)
const isCorsForced = computed(() => proxyConfig.value.enabled)

// 监听启用反向代理变化，自动同步安全头和CORS
watch(() => proxyConfig.value.enabled, (enabled) => {
  if (enabled) {
    // 启用反向代理时，自动启用安全头和CORS
    proxyConfig.value.add_security_headers = true
    proxyConfig.value.add_cors_headers = true
  }
}, { immediate: true })

/**
 * 获取状态文本
 */
const statusText = computed(() => {
  if (!status.value?.is_loaded) {
    return '未载入'
  }
  switch (status.value.status) {
    case 'running':
      return '运行中'
    case 'stopped':
      return '已停止'
    case 'error':
      return '错误'
    default:
      return '未知'
  }
})

/**
 * 获取状态样式类
 */
const statusClass = computed(() => {
  if (!status.value?.is_loaded) {
    return 'status-unloaded'
  }
  switch (status.value.status) {
    case 'running':
      return 'status-running'
    case 'stopped':
      return 'status-stopped'
    case 'error':
      return 'status-error'
    default:
      return 'status-unknown'
  }
})

/**
 * 是否可以启动
 */
const canStart = computed(() => {
  return status.value?.is_loaded && status.value?.status !== 'running'
})

/**
 * 是否可以停止
 */
const canStop = computed(() => {
  return status.value?.is_loaded && status.value?.status === 'running'
})

/**
 * 是否可以重启
 */
const canRestart = computed(() => {
  return status.value?.is_loaded
})

/**
 * 是否为自定义URL
 */
const isCustomUrl = computed(() => {
  return downloadUrl.value !== '' && !mirrorUrls.some(m => m.url === downloadUrl.value)
})

/**
 * 是否支持手动载入（Windows平台）
 */
const supportsManualLoad = computed(() => {
  return platformInfo.value?.supports_manual_load ?? true
})

/**
 * 是否支持下载（Windows平台）
 */
const supportsDownload = computed(() => {
  return platformInfo.value?.supports_download ?? true
})

/**
 * 平台显示文本
 */
const platformDisplayText = computed(() => {
  if (!platformInfo.value) return ''
  if (platformInfo.value.uses_package_manager) {
    const pm = platformInfo.value.package_manager || '包管理器'
    return `（通过${pm}管理）`
  }
  return ''
})

/**
 * 加载Nginx状态
 */
async function loadStatus() {
  try {
    status.value = await getNginxStatus()
  } catch (e) {
    showMessage('获取状态失败: ' + e, 'error')
  }
}

/**
 * 加载平台信息
 */
async function loadPlatformInfo() {
  try {
    platformInfo.value = await getNginxPlatformInfo()
  } catch (e) {
    console.error('获取平台信息失败:', e)
  }
}

/**
 * 加载代理配置
 */
async function loadProxyConfig() {
  try {
    const config = await getNginxProxyConfig()
    proxyConfig.value = config
  } catch (e) {
    showMessage('获取代理配置失败: ' + e, 'error')
  }
}

/**
 * 载入Nginx（选择文件）
 */
async function handleLoadNginx() {
  try {
    // 使用Tauri的文件选择对话框
    const { open: openDialog } = await import('@tauri-apps/plugin-dialog')
    const selected = await openDialog({
      multiple: false,
      directory: false,
      filters: [
        { name: 'Nginx可执行文件', extensions: ['exe'] },
        { name: '所有文件', extensions: ['*'] }
      ],
      title: '选择Nginx可执行文件'
    })

    if (!selected) {
      return
    }

    const exePath = Array.isArray(selected) ? selected[0] : selected

    isLoading.value = true
    showMessage('正在验证Nginx...', 'info')

    const result = await loadNginx(exePath)

    if (result.success) {
      showMessage(result.message, 'success')
      await loadStatus()
    } else {
      showMessage(result.message, 'error')
    }
  } catch (e) {
    showMessage('载入Nginx失败: ' + e, 'error')
  } finally {
    isLoading.value = false
  }
}

/**
 * 显示下载对话框
 */
async function showDownload() {
  try {
    const url = await getNginxDownloadUrl()
    downloadUrl.value = url || defaultDownloadUrl
    showDownloadDialog.value = true
  } catch (e) {
    downloadUrl.value = defaultDownloadUrl
    showDownloadDialog.value = true
  }
}

/**
 * 关闭下载对话框
 */
function closeDownloadDialog() {
  showDownloadDialog.value = false
}

/**
 * 下载并载入Nginx
 */
async function handleDownloadNginx() {
  if (!downloadUrl.value.trim()) {
    showMessage('请输入下载URL', 'error')
    return
  }

  isDownloading.value = true
  showMessage('正在下载Nginx，请稍候...', 'info')

  try {
    // 先保存下载URL
    await updateNginxDownloadUrl(downloadUrl.value)

    // 下载并解压
    const result = await downloadAndExtractNginx(downloadUrl.value)

    if (result.success) {
      showMessage(result.message, 'success')
      showDownloadDialog.value = false
      // 延迟一下再刷新状态，确保后端配置已保存
      setTimeout(async () => {
        await loadStatus()
        await loadProxyConfig()
      }, 500)
    } else {
      showMessage(result.message, 'error')
    }
  } catch (e) {
    showMessage('下载Nginx失败: ' + e, 'error')
  } finally {
    isDownloading.value = false
  }
}

/**
 * 选择镜像URL
 */
function selectMirror(url: string) {
  downloadUrl.value = url
}

/**
 * 选择自定义URL
 */
function selectCustom() {
  downloadUrl.value = ''
}

/**
 * 启动Nginx
 */
async function handleStartNginx() {
  isLoading.value = true
  showMessage('正在启动Nginx...', 'info')

  try {
    const result = await startNginx()

    if (result.success) {
      showMessage(result.message, 'success')
    } else {
      showMessage(result.message, 'error')
    }

    await loadStatus()
  } catch (e) {
    showMessage('启动Nginx失败: ' + e, 'error')
  } finally {
    isLoading.value = false
  }
}

/**
 * 停止Nginx
 */
async function handleStopNginx() {
  isLoading.value = true
  showMessage('正在停止Nginx...', 'info')

  try {
    const result = await stopNginx()

    if (result.success) {
      showMessage(result.message, 'success')
    } else {
      showMessage(result.message, 'error')
    }

    await loadStatus()
  } catch (e) {
    showMessage('停止Nginx失败: ' + e, 'error')
  } finally {
    isLoading.value = false
  }
}

/**
 * 重启Nginx
 */
async function handleRestartNginx() {
  isLoading.value = true
  showMessage('正在重启Nginx...', 'info')

  try {
    const result = await restartNginx()

    if (result.success) {
      showMessage(result.message, 'success')
    } else {
      showMessage(result.message, 'error')
    }

    await loadStatus()
  } catch (e) {
    showMessage('重启Nginx失败: ' + e, 'error')
  } finally {
    isLoading.value = false
  }
}

/**
 * 显示消息
 */
function showMessage(msg: string, type: 'success' | 'error' | 'info' = 'info') {
  message.value = msg
  messageType.value = type

  // 3秒后清除消息
  setTimeout(() => {
    if (message.value === msg) {
      message.value = null
    }
  }, 5000)
}

/**
 * 保存代理配置
 */
async function handleSaveConfig() {
  isSavingConfig.value = true
  try {
    const result = await saveNginxProxyConfig(proxyConfig.value)
    if (result.success) {
      showMessage(result.message, 'success')
      // 保存成功后刷新 store 中的服务端配置（因为启用了反向代理会修改服务端配置）
      await serviceStore.refreshServerConfig()
    } else {
      showMessage(result.message, 'error')
    }
  } catch (e) {
    showMessage('保存配置失败: ' + e, 'error')
  } finally {
    isSavingConfig.value = false
  }
}

/**
 * 保存配置并重启
 */
async function handleSaveAndRestart() {
  isSavingConfig.value = true
  try {
    const result = await saveNginxProxyConfig(proxyConfig.value)
    if (result.success) {
      showMessage(result.message + '，正在重启Nginx...', 'success')
      // 保存成功后刷新 store 中的服务端配置
      await serviceStore.refreshServerConfig()
      // 重启Nginx
      const restartResult = await restartNginx()
      if (restartResult.success) {
        showMessage('Nginx已重启', 'success')
      } else {
        showMessage('重启失败: ' + restartResult.message, 'error')
      }
      await loadStatus()
    } else {
      showMessage(result.message, 'error')
    }
  } catch (e) {
    showMessage('保存配置失败: ' + e, 'error')
  } finally {
    isSavingConfig.value = false
  }
}

// 页面加载时获取状态
onMounted(() => {
  loadStatus()
  loadProxyConfig()
  loadPlatformInfo()
})
</script>

<template>
  <div class="nginx-page">
    <h1 class="page-title">Nginx</h1>

    <!-- 消息提示 -->
    <div v-if="message" class="message" :class="messageType">
      {{ message }}
    </div>

    <!-- 状态卡片 -->
    <div class="status-card">
      <div class="status-header">
        <h2>Nginx状态 {{ platformDisplayText }}</h2>
        <span class="status-badge" :class="statusClass">
          {{ statusText }}
        </span>
      </div>

      <div class="status-details" v-if="status?.is_loaded">
        <div class="detail-item">
          <span class="detail-label">版本:</span>
          <span class="detail-value">{{ status.version || '未知' }}</span>
        </div>
        <div class="detail-item">
          <span class="detail-label">进程ID:</span>
          <span class="detail-value">{{ status.pid || '无' }}</span>
        </div>
        <div class="detail-item">
          <span class="detail-label">可执行文件:</span>
          <span class="detail-value path">{{ status.exe_path }}</span>
        </div>
        <div class="detail-item" v-if="status.config_dir">
          <span class="detail-label">配置目录:</span>
          <span class="detail-value path">{{ status.config_dir }}</span>
        </div>
      </div>

      <div class="status-actions">
        <button
          v-if="supportsManualLoad"
          class="btn btn-primary"
          @click="handleLoadNginx"
          :disabled="isLoading"
        >
          <span v-if="isLoading" class="loading-spinner"></span>
          <span v-else>载入Nginx</span>
        </button>

        <button
          v-if="supportsDownload"
          class="btn btn-secondary"
          @click="showDownload"
          :disabled="isDownloading"
        >
          <span v-if="isDownloading" class="loading-spinner"></span>
          <span v-else>下载Nginx</span>
        </button>

        <button
          class="btn btn-success"
          @click="handleStartNginx"
          :disabled="!canStart || isLoading"
        >
          启动
        </button>

        <button
          class="btn btn-danger"
          @click="handleStopNginx"
          :disabled="!canStop || isLoading"
        >
          停止
        </button>

        <button
          class="btn btn-warning"
          @click="handleRestartNginx"
          :disabled="!canRestart || isLoading"
        >
          重启
        </button>

      </div>
    </div>

    <!-- 代理配置卡片 -->
    <div class="config-card">
      <div class="config-header">
        <h2>代理配置</h2>
        <span class="config-hint">配置Nginx反向代理、安全头和CORS</span>
      </div>

      <div class="config-form">
        <!-- 基本配置 -->
        <div class="form-section">
          <h3>基本配置</h3>
          <div class="form-row">
            <div class="form-group">
              <label for="proxy-enabled">
                <input
                  id="proxy-enabled"
                  v-model="proxyConfig.enabled"
                  type="checkbox"
                />
                启用反向代理
              </label>
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label for="listen-port">监听端口:</label>
              <input
                id="listen-port"
                v-model.number="proxyConfig.listen_port"
                type="number"
                min="1"
                max="65535"
                class="form-input"
                :disabled="!proxyConfig.enabled"
              />
            </div>
            <div class="form-group">
              <label for="server-name">服务器名称:</label>
              <input
                id="server-name"
                v-model="proxyConfig.server_name"
                type="text"
                class="form-input"
                :disabled="!proxyConfig.enabled"
              />
            </div>
          </div>
          <div class="form-row">
            <div class="form-group form-group-full">
              <label for="backend-url">后端服务URL:</label>
              <input
                id="backend-url"
                v-model="proxyConfig.backend_url"
                type="text"
                placeholder="http://127.0.0.1:8000"
                class="form-input"
                :disabled="!proxyConfig.enabled"
              />
            </div>
          </div>
        </div>

        <!-- 安全头配置 -->
        <div class="form-section">
          <h3>
            安全头配置
            <span v-if="isSecurityHeadersForced" class="forced-badge">启用代理时强制</span>
          </h3>
          <div class="form-row">
            <div class="form-group">
              <label for="add-security-headers">
                <input
                  id="add-security-headers"
                  v-model="proxyConfig.add_security_headers"
                  type="checkbox"
                  :disabled="!proxyConfig.enabled || isSecurityHeadersForced"
                />
                添加安全头
              </label>
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label for="enable-hsts">
                <input
                  id="enable-hsts"
                  v-model="proxyConfig.enable_hsts"
                  type="checkbox"
                  :disabled="!proxyConfig.enabled || !proxyConfig.add_security_headers"
                />
                启用HSTS
              </label>
            </div>
            <div class="form-group">
              <label for="hsts-max-age">HSTS Max-Age:</label>
              <input
                id="hsts-max-age"
                v-model.number="proxyConfig.hsts_max_age"
                type="number"
                class="form-input"
                :disabled="!proxyConfig.enabled || !proxyConfig.add_security_headers || !proxyConfig.enable_hsts"
              />
            </div>
          </div>
        </div>

        <!-- CORS配置 -->
        <div class="form-section">
          <h3>
            CORS配置
            <span v-if="isCorsForced" class="forced-badge">启用代理时强制</span>
          </h3>
          <div class="form-row">
            <div class="form-group">
              <label for="add-cors-headers">
                <input
                  id="add-cors-headers"
                  v-model="proxyConfig.add_cors_headers"
                  type="checkbox"
                  :disabled="!proxyConfig.enabled || isCorsForced"
                />
                添加CORS头
              </label>
            </div>
          </div>
          <div class="form-row">
            <div class="form-group form-group-full">
              <label for="cors-origins">允许的源:</label>
              <input
                id="cors-origins"
                v-model="proxyConfig.cors_origins"
                type="text"
                placeholder="* 或特定域名"
                class="form-input"
                :disabled="!proxyConfig.enabled || !proxyConfig.add_cors_headers"
              />
            </div>
          </div>
          <div class="form-row">
            <div class="form-group form-group-full">
              <label for="cors-methods">允许的方法:</label>
              <input
                id="cors-methods"
                v-model="proxyConfig.cors_methods"
                type="text"
                placeholder="GET, POST, PUT, DELETE, OPTIONS"
                class="form-input"
                :disabled="!proxyConfig.enabled || !proxyConfig.add_cors_headers"
              />
            </div>
          </div>
          <div class="form-row">
            <div class="form-group form-group-full">
              <label for="cors-headers">允许的头:</label>
              <input
                id="cors-headers"
                v-model="proxyConfig.cors_headers"
                type="text"
                placeholder="Content-Type, Authorization"
                class="form-input"
                :disabled="!proxyConfig.enabled || !proxyConfig.add_cors_headers"
              />
            </div>
          </div>
        </div>
      </div>

      <div class="config-actions">
        <button
          class="btn btn-primary"
          @click="handleSaveConfig"
          :disabled="isSavingConfig"
        >
          <span v-if="isSavingConfig" class="loading-spinner"></span>
          <span v-else>保存配置</span>
        </button>
        <button
          v-if="status?.status === 'running'"
          class="btn btn-warning"
          @click="handleSaveAndRestart"
          :disabled="isSavingConfig"
        >
          <span v-if="isSavingConfig" class="loading-spinner"></span>
          <span v-else>保存并重启</span>
        </button>
      </div>
    </div>

    <!-- 下载对话框 -->
    <div v-if="showDownloadDialog" class="modal-overlay" @click.self="closeDownloadDialog">
      <div class="modal-content">
        <div class="modal-header">
          <h3>下载Nginx</h3>
          <button class="close-btn" @click="closeDownloadDialog">&times;</button>
        </div>

        <div class="modal-body">
          <div class="form-group">
            <label>下载源:</label>
            <div class="mirror-buttons">
              <button
                v-for="mirror in mirrorUrls"
                :key="mirror.name"
                class="btn btn-sm"
                :class="{ active: downloadUrl === mirror.url }"
                @click="selectMirror(mirror.url)"
              >
                {{ mirror.name }}
              </button>
              <button
                class="btn btn-sm"
                :class="{ active: isCustomUrl }"
                @click="selectCustom"
              >
                自定义
              </button>
            </div>
          </div>

          <div class="form-group">
            <label for="download-url">下载URL:</label>
            <input
              id="download-url"
              v-model="downloadUrl"
              type="text"
              placeholder="请输入Nginx下载URL"
              class="form-input"
            />
            <small class="form-hint">支持自定义镜像站URL</small>
          </div>

          <div class="form-info">
            <p>下载完成后将自动解压并载入Nginx。</p>
            <p>默认下载位置: 用户配置目录/nginx</p>
          </div>
        </div>

        <div class="modal-footer">
          <button
            class="btn btn-primary"
            @click="handleDownloadNginx"
            :disabled="isDownloading || !downloadUrl.trim()"
          >
            <span v-if="isDownloading" class="loading-spinner"></span>
            <span v-else>开始下载</span>
          </button>
          <button class="btn btn-secondary" @click="closeDownloadDialog">
            取消
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.nginx-page {
  padding: var(--spacing-lg);
  max-width: 1200px;
  margin: 0 auto;
}

.page-title {
  font-size: var(--font-size-2xl);
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 var(--spacing-xl) 0;
}

/* 消息提示 */
.message {
  padding: var(--spacing-md) var(--spacing-lg);
  border-radius: var(--radius-md);
  margin-bottom: var(--spacing-lg);
  font-size: var(--font-size-sm);
}

.message.success {
  background-color: var(--success-color-bg, rgba(34, 197, 94, 0.1));
  color: var(--success-color, #22c55e);
  border: 1px solid var(--success-color, #22c55e);
}

.message.error {
  background-color: var(--error-color-bg, rgba(239, 68, 68, 0.1));
  color: var(--error-color, #ef4444);
  border: 1px solid var(--error-color, #ef4444);
}

.message.info {
  background-color: var(--info-color-bg, rgba(59, 130, 246, 0.1));
  color: var(--info-color, #3b82f6);
  border: 1px solid var(--info-color, #3b82f6);
}

/* 状态卡片 */
.status-card {
  background-color: var(--bg-secondary);
  border-radius: var(--border-radius-md);
  padding: var(--spacing-xl);
  border: 1px solid var(--border-color);
}

.status-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-lg);
  padding-bottom: var(--spacing-lg);
  border-bottom: 1px solid var(--border-color);
}

.status-header h2 {
  font-size: var(--font-size-lg);
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.status-badge {
  padding: var(--spacing-xs) var(--spacing-md);
  border-radius: var(--radius-full);
  font-size: var(--font-size-sm);
  font-weight: 500;
}

.status-badge.status-unloaded {
  background-color: var(--bg-tertiary);
  color: var(--text-secondary);
}

.status-badge.status-running {
  background-color: var(--success-color-bg, rgba(34, 197, 94, 0.2));
  color: var(--success-color, #22c55e);
}

.status-badge.status-stopped {
  background-color: var(--warning-color-bg, rgba(245, 158, 11, 0.2));
  color: var(--warning-color, #f59e0b);
}

.status-badge.status-error {
  background-color: var(--error-color-bg, rgba(239, 68, 68, 0.2));
  color: var(--error-color, #ef4444);
}

.status-badge.status-unknown {
  background-color: var(--bg-tertiary);
  color: var(--text-secondary);
}

/* 状态详情 */
.status-details {
  margin-bottom: var(--spacing-xl);
}

.detail-item {
  display: flex;
  margin-bottom: var(--spacing-sm);
  font-size: var(--font-size-sm);
}

.detail-label {
  width: 100px;
  color: var(--text-secondary);
  flex-shrink: 0;
}

.detail-value {
  color: var(--text-primary);
  word-break: break-all;
}

.detail-value.path {
  font-family: monospace;
  font-size: var(--font-size-xs);
  background-color: var(--bg-tertiary);
  padding: var(--spacing-xs) var(--spacing-sm);
  border-radius: var(--radius-sm);
}

/* 操作按钮 */
.status-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-md);
}

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-md);
  border-radius: var(--border-radius-md);
  font-size: var(--font-size-md);
  font-weight: 500;
  cursor: pointer;
  border: none;
  transition: all var(--transition-fast);
  white-space: nowrap;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary {
  background-color: var(--primary-color);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background-color: var(--primary-hover);
}

.btn-secondary {
  background-color: var(--bg-tertiary);
  color: var(--text-primary);
}

.btn-secondary:hover:not(:disabled) {
  background-color: #475569;
}

.btn-success {
  background-color: var(--success-color);
  color: white;
}

.btn-success:hover:not(:disabled) {
  background-color: #059669;
}

.btn-danger {
  background-color: var(--error-color);
  color: white;
}

.btn-danger:hover:not(:disabled) {
  background-color: #dc2626;
}

.btn-warning {
  background-color: var(--warning-color);
  color: white;
}

.btn-warning:hover:not(:disabled) {
  background-color: #d97706;
}

.btn-info {
  background-color: var(--info-color);
  color: white;
}

.btn-info:hover:not(:disabled) {
  background-color: #0891b2;
}

.btn-sm {
  padding: var(--spacing-xs) var(--spacing-sm);
  font-size: var(--font-size-sm);
}

.btn.active {
  background-color: var(--primary-color);
  color: white;
}

/* 加载动画 */
.loading-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid transparent;
  border-top-color: currentColor;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* 模态框 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background-color: var(--bg-secondary);
  border-radius: var(--radius-lg);
  width: 90%;
  max-width: 500px;
  max-height: 90vh;
  overflow-y: auto;
  border: 1px solid var(--border-color);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-lg);
  border-bottom: 1px solid var(--border-color);
}

.modal-header h3 {
  margin: 0;
  font-size: var(--font-size-lg);
  font-weight: 600;
  color: var(--text-primary);
}

.close-btn {
  background: none;
  border: none;
  font-size: var(--font-size-xl);
  color: var(--text-secondary);
  cursor: pointer;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-md);
}

.close-btn:hover {
  background-color: var(--bg-tertiary);
}

.modal-body {
  padding: var(--spacing-lg);
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-md);
  padding: var(--spacing-lg);
  border-top: 1px solid var(--border-color);
}

/* 表单 */
.form-group {
  margin-bottom: var(--spacing-lg);
}

.form-group label {
  display: block;
  font-size: var(--font-size-sm);
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: var(--spacing-sm);
}

.form-input {
  width: 100%;
  padding: var(--spacing-sm) var(--spacing-md);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background-color: var(--bg-primary);
  color: var(--text-primary);
  font-size: var(--font-size-sm);
  box-sizing: border-box;
}

.form-input:focus {
  outline: none;
  border-color: var(--primary-color);
}

.form-hint {
  display: block;
  margin-top: var(--spacing-xs);
  font-size: var(--font-size-xs);
  color: var(--text-secondary);
}

.form-info {
  background-color: var(--bg-tertiary);
  padding: var(--spacing-md);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}

.form-info p {
  margin: 0 0 var(--spacing-xs) 0;
}

.form-info p:last-child {
  margin-bottom: 0;
}

.mirror-buttons {
  display: flex;
  gap: var(--spacing-sm);
  flex-wrap: wrap;
}

/* 配置卡片 */
.config-card {
  background-color: var(--bg-secondary);
  border-radius: var(--border-radius-md);
  padding: var(--spacing-xl);
  border: 1px solid var(--border-color);
  margin-top: var(--spacing-lg);
}

.config-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-lg);
  padding-bottom: var(--spacing-lg);
  border-bottom: 1px solid var(--border-color);
}

.config-header h2 {
  font-size: var(--font-size-lg);
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.config-hint {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}

/* 配置表单 */
.config-form {
  margin-bottom: var(--spacing-lg);
}

.form-section {
  margin-bottom: var(--spacing-xl);
}

.form-section h3 {
  font-size: var(--font-size-md);
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 var(--spacing-md) 0;
  padding-bottom: var(--spacing-sm);
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.forced-badge {
  font-size: var(--font-size-xs);
  font-weight: 500;
  color: var(--warning-color);
  background-color: rgba(245, 158, 11, 0.1);
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--warning-color);
}

.form-row {
  display: flex;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-md);
  flex-wrap: wrap;
}

.form-row .form-group {
  flex: 1;
  min-width: 200px;
  margin-bottom: 0;
}

.form-row .form-group-full {
  flex: 1 1 100%;
}

.form-group label {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  font-size: var(--font-size-sm);
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: var(--spacing-sm);
}

.form-group input[type="checkbox"] {
  width: 16px;
  height: 16px;
  cursor: pointer;
}

.form-input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  background-color: var(--bg-tertiary);
}

.config-actions {
  display: flex;
  gap: var(--spacing-md);
  justify-content: flex-end;
  padding-top: var(--spacing-lg);
  border-top: 1px solid var(--border-color);
}
</style>
