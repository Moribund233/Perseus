<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import {
  getRedisStatus,
  loadRedis,
  startRedis,
  stopRedis,
  restartRedis,
  getRedisPlatformInfo,
  updateRedisConfig,
  installRedisService,
  uninstallRedisService,
  isRedisServiceInstalled,
  validateRedisDir,
  type RedisStatusResponse,
  type RedisPlatformInfo,
  type RedisConfigUpdateRequest
} from '../services/api'

/**
 * Redis管理页面
 *
 * 功能：
 * 1. 载入Redis：选择Redis目录，验证并保存配置
 * 2. Windows服务管理：安装/卸载Redis为Windows服务
 * 3. 控制Redis：启动、停止、重启
 * 4. 配置管理：端口、认证、数据目录等
 */

// 状态
const status = ref<RedisStatusResponse | null>(null)
const isLoading = ref(false)
const message = ref<string | null>(null)
const messageType = ref<'success' | 'error' | 'info'>('info')

// 平台信息
const platformInfo = ref<RedisPlatformInfo | null>(null)

// 服务安装状态
const isServiceInstalled = ref(false)

// 配置编辑
const isEditingConfig = ref(false)
const configForm = ref({
  port: 6379,
  require_pass: false,
  password: '',
  data_dir: ''
})

// 计算属性：状态文本
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

// 计算属性：状态样式类
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

// 计算属性：是否可以启动
const canStart = computed(() => {
  return status.value?.is_loaded && status.value?.status !== 'running'
})

// 计算属性：是否可以停止
const canStop = computed(() => {
  return status.value?.is_loaded && status.value?.status === 'running'
})

// 计算属性：是否可以重启
const canRestart = computed(() => {
  return status.value?.is_loaded
})

// 计算属性：是否支持手动载入（Windows平台）
const supportsManualLoad = computed(() => {
  return platformInfo.value?.supports_manual_load ?? false
})

// 计算属性：是否使用包管理器（Linux平台）
const usesPackageManager = computed(() => {
  return platformInfo.value?.uses_package_manager ?? false
})

// 计算属性：平台显示文本
const platformDisplayText = computed(() => {
  if (!platformInfo.value) return ''
  if (platformInfo.value.uses_package_manager) {
    const pm = platformInfo.value.package_manager || '包管理器'
    return `（通过${pm}管理）`
  }
  return ''
})

// 计算属性：是否显示Windows服务管理
const showWindowsService = computed(() => {
  return supportsManualLoad.value && status.value?.is_loaded
})

/**
 * 加载Redis状态
 */
async function loadStatus() {
  try {
    status.value = await getRedisStatus()
  } catch (e) {
    showMessage('获取状态失败: ' + e, 'error')
  }
}

/**
 * 加载平台信息
 */
async function loadPlatformInfo() {
  try {
    platformInfo.value = await getRedisPlatformInfo()
  } catch (e) {
    console.error('获取平台信息失败:', e)
  }
}

/**
 * 检查服务安装状态
 */
async function checkServiceStatus() {
  if (!supportsManualLoad.value) return
  try {
    isServiceInstalled.value = await isRedisServiceInstalled()
  } catch (e) {
    console.error('检查服务状态失败:', e)
  }
}

/**
 * 载入Redis目录
 */
async function handleLoadRedis() {
  try {
    const { open: openDialog } = await import('@tauri-apps/plugin-dialog')
    const selected = await openDialog({
      multiple: false,
      directory: true,
      title: '选择Redis目录'
    })

    if (!selected) {
      return
    }

    const exeDir = Array.isArray(selected) ? selected[0] : selected

    // 验证目录
    const isValid = await validateRedisDir(exeDir)
    if (!isValid) {
      showMessage('无效的Redis目录，请确保目录包含redis-server和redis-cli可执行文件', 'error')
      return
    }

    isLoading.value = true
    showMessage('正在载入Redis...', 'info')

    const result = await loadRedis(exeDir)

    if (result.success) {
      showMessage(result.message, 'success')
      await loadStatus()
      await checkServiceStatus()
    } else {
      showMessage(result.message, 'error')
    }
  } catch (e) {
    showMessage('载入Redis失败: ' + e, 'error')
  } finally {
    isLoading.value = false
  }
}

/**
 * 安装Redis为Windows服务
 */
async function handleInstallService() {
  if (!status.value?.exe_dir) {
    showMessage('Redis目录未设置', 'error')
    return
  }

  isLoading.value = true
  showMessage('正在安装Redis服务...', 'info')

  try {
    const result = await installRedisService(status.value.exe_dir)

    if (result.success) {
      showMessage(result.message, 'success')
      isServiceInstalled.value = result.is_installed
      await loadStatus()
    } else {
      showMessage(result.message, 'error')
    }
  } catch (e) {
    showMessage('安装服务失败: ' + e, 'error')
  } finally {
    isLoading.value = false
  }
}

/**
 * 卸载Redis Windows服务
 */
async function handleUninstallService() {
  isLoading.value = true
  showMessage('正在卸载Redis服务...', 'info')

  try {
    const result = await uninstallRedisService()

    if (result.success) {
      showMessage(result.message, 'success')
      isServiceInstalled.value = result.is_installed
      await loadStatus()
    } else {
      showMessage(result.message, 'error')
    }
  } catch (e) {
    showMessage('卸载服务失败: ' + e, 'error')
  } finally {
    isLoading.value = false
  }
}

/**
 * 启动Redis
 */
async function handleStartRedis() {
  isLoading.value = true
  showMessage('正在启动Redis...', 'info')

  try {
    const result = await startRedis()

    if (result.success) {
      showMessage(result.message, 'success')
    } else {
      showMessage(result.message, 'error')
    }

    await loadStatus()
  } catch (e) {
    showMessage('启动Redis失败: ' + e, 'error')
  } finally {
    isLoading.value = false
  }
}

/**
 * 停止Redis
 */
async function handleStopRedis() {
  isLoading.value = true
  showMessage('正在停止Redis...', 'info')

  try {
    const result = await stopRedis()

    if (result.success) {
      showMessage(result.message, 'success')
    } else {
      showMessage(result.message, 'error')
    }

    await loadStatus()
  } catch (e) {
    showMessage('停止Redis失败: ' + e, 'error')
  } finally {
    isLoading.value = false
  }
}

/**
 * 重启Redis
 */
async function handleRestartRedis() {
  isLoading.value = true
  showMessage('正在重启Redis...', 'info')

  try {
    const result = await restartRedis()

    if (result.success) {
      showMessage(result.message, 'success')
    } else {
      showMessage(result.message, 'error')
    }

    await loadStatus()
  } catch (e) {
    showMessage('重启Redis失败: ' + e, 'error')
  } finally {
    isLoading.value = false
  }
}

/**
 * 打开配置编辑
 */
function openConfigEdit() {
  if (!status.value) return

  configForm.value = {
    port: status.value.port,
    require_pass: status.value.require_pass,
    password: '',
    data_dir: status.value.data_dir || ''
  }
  isEditingConfig.value = true
}

/**
 * 关闭配置编辑
 */
function closeConfigEdit() {
  isEditingConfig.value = false
}

/**
 * 保存配置
 */
async function handleSaveConfig() {
  isLoading.value = true

  try {
    const request: RedisConfigUpdateRequest = {
      port: configForm.value.port,
      require_pass: configForm.value.require_pass,
      password: configForm.value.password || undefined,
      data_dir: configForm.value.data_dir || undefined
    }

    const result = await updateRedisConfig(request)

    if (result.success) {
      showMessage(result.message, 'success')
      isEditingConfig.value = false
      await loadStatus()
    } else {
      showMessage(result.message, 'error')
    }
  } catch (e) {
    showMessage('保存配置失败: ' + e, 'error')
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
  setTimeout(() => {
    if (message.value === msg) {
      message.value = null
    }
  }, 5000)
}

/**
 * 页面加载时获取状态
 */
onMounted(async () => {
  await loadPlatformInfo()
  await loadStatus()
  await checkServiceStatus()
})
</script>

<template>
  <div class="page-container redis-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="header-title">
        <img src="../assets/icons/database.svg" class="header-icon" alt="Redis" />
        <h1>Redis管理{{ platformDisplayText }}</h1>
      </div>
      <p class="header-description">
        管理Redis服务的启动、停止和配置
      </p>
    </div>

    <!-- 消息提示 -->
    <div v-if="message" class="message" :class="messageType">
      {{ message }}
    </div>

    <!-- 状态卡片 -->
    <div class="status-card">
      <div class="status-header">
        <h2>服务状态</h2>
        <span class="status-badge" :class="statusClass">
          {{ statusText }}
        </span>
      </div>

      <div class="status-details">
        <div class="detail-item">
          <span class="detail-label">载入状态:</span>
          <span class="detail-value">{{ status?.is_loaded ? '已载入' : '未载入' }}</span>
        </div>
        <div class="detail-item" v-if="status?.version">
          <span class="detail-label">版本:</span>
          <span class="detail-value">{{ status.version }}</span>
        </div>
        <div class="detail-item" v-if="status?.exe_dir">
          <span class="detail-label">目录:</span>
          <span class="detail-value path">{{ status.exe_dir }}</span>
        </div>
        <div class="detail-item" v-if="status?.is_loaded">
          <span class="detail-label">端口:</span>
          <span class="detail-value">{{ status.port }}</span>
        </div>
        <div class="detail-item" v-if="status?.is_loaded">
          <span class="detail-label">认证:</span>
          <span class="detail-value">{{ status.require_pass ? '已启用' : '未启用' }}</span>
        </div>
        <div class="detail-item" v-if="status?.is_windows_service">
          <span class="detail-label">Windows服务:</span>
          <span class="detail-value">已安装</span>
        </div>
      </div>

      <!-- 操作按钮 -->
      <div class="status-actions">
        <!-- Windows平台：载入Redis目录 -->
        <button
          v-if="supportsManualLoad && !status?.is_loaded"
          class="btn btn-primary"
          @click="handleLoadRedis"
          :disabled="isLoading"
        >
          <span v-if="isLoading" class="spinner"></span>
          <span v-else>载入Redis目录</span>
        </button>

        <!-- 服务控制按钮 -->
        <template v-if="status?.is_loaded || usesPackageManager">
          <button
            class="btn btn-success"
            @click="handleStartRedis"
            :disabled="!canStart || isLoading"
          >
            启动
          </button>
          <button
            class="btn btn-warning"
            @click="handleStopRedis"
            :disabled="!canStop || isLoading"
          >
            停止
          </button>
          <button
            class="btn btn-info"
            @click="handleRestartRedis"
            :disabled="!canRestart || isLoading"
          >
            重启
          </button>
          <button
            class="btn btn-secondary"
            @click="openConfigEdit"
            :disabled="isLoading"
          >
            配置
          </button>
        </template>
      </div>
    </div>

    <!-- Windows服务管理卡片 -->
    <div class="config-card" v-if="showWindowsService">
      <div class="config-header">
        <h2>Windows服务管理</h2>
      </div>

      <div class="config-hint mb-md">
        将Redis安装为Windows服务后，可以更方便地管理Redis的启动和停止，并支持开机自启。
      </div>

      <div class="status-actions">
        <button
          v-if="!isServiceInstalled"
          class="btn btn-primary"
          @click="handleInstallService"
          :disabled="isLoading"
        >
          安装为Windows服务
        </button>
        <button
          v-else
          class="btn btn-danger"
          @click="handleUninstallService"
          :disabled="isLoading"
        >
          卸载Windows服务
        </button>
      </div>
    </div>

    <!-- 配置编辑对话框 -->
    <div v-if="isEditingConfig" class="modal-overlay" @click.self="closeConfigEdit">
      <div class="modal-content">
        <div class="modal-header">
          <h3>Redis配置</h3>
          <button class="btn-close" @click="closeConfigEdit">&times;</button>
        </div>

        <div class="modal-body">
          <div class="form-group">
            <label>监听端口</label>
            <input
              v-model.number="configForm.port"
              type="number"
              class="form-input"
              min="1"
              max="65535"
            />
          </div>

          <div class="form-group">
            <label class="form-checkbox">
              <input
                v-model="configForm.require_pass"
                type="checkbox"
              />
              <span>启用密码认证</span>
            </label>
          </div>

          <div class="form-group" v-if="configForm.require_pass">
            <label>密码</label>
            <input
              v-model="configForm.password"
              type="password"
              class="form-input"
              placeholder="留空表示不修改密码"
            />
            <span class="form-hint">留空表示不修改当前密码</span>
          </div>

          <div class="form-group">
            <label>数据目录</label>
            <input
              v-model="configForm.data_dir"
              type="text"
              class="form-input"
              placeholder="数据文件存储目录"
            />
          </div>
        </div>

        <div class="modal-footer">
          <button class="btn btn-secondary" @click="closeConfigEdit">取消</button>
          <button
            class="btn btn-primary"
            @click="handleSaveConfig"
            :disabled="isLoading"
          >
            保存
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
@import '../styles/page-common.css';

/* 状态徽章 */
.status-badge {
  padding: var(--spacing-xs) var(--spacing-md);
  border-radius: var(--border-radius-sm);
  font-size: var(--font-size-sm);
  font-weight: 500;
}

.status-badge.status-unloaded {
  background-color: var(--bg-tertiary);
  color: var(--text-secondary);
}

.status-badge.status-running {
  background-color: rgba(34, 197, 94, 0.2);
  color: var(--success-color);
}

.status-badge.status-stopped {
  background-color: var(--bg-tertiary);
  color: var(--text-secondary);
}

.status-badge.status-error {
  background-color: rgba(239, 68, 68, 0.2);
  color: var(--error-color);
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
  border-radius: var(--border-radius-lg);
  width: 100%;
  max-width: 500px;
  max-height: 90vh;
  overflow: hidden;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
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
  color: var(--text-primary);
}

.btn-close {
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
  border-radius: var(--border-radius-sm);
}

.btn-close:hover {
  background-color: var(--bg-tertiary);
  color: var(--text-primary);
}

.modal-body {
  padding: var(--spacing-lg);
  overflow-y: auto;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-md);
  padding: var(--spacing-lg);
  border-top: 1px solid var(--border-color);
}

/* 加载动画 */
.spinner {
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 2px solid var(--border-color);
  border-top-color: var(--primary-color);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
