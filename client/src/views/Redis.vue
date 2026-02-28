<script setup lang="ts">
import { ref, onMounted, computed, reactive } from 'vue'
import {
  getRedisStatus,
  loadRedis,
  startRedis,
  stopRedis,
  restartRedis,
  getPlatformInfo,
  installRedisService,
  uninstallRedisService,
  isRedisServiceInstalled,
  validateRedisDir,
  getRedisRuntimeConfigs,
  batchUpdateRedisRuntimeConfigs,
  rewriteRedisConfig,
  type RedisStatusResponse,
  type PlatformInfo,
  type RedisRuntimeConfig,
  type RedisRuntimeConfigUpdateRequest
} from '../services/api'

/**
 * Redis管理页面
 *
 * 功能：
 * 1. 载入Redis：选择Redis目录，验证并保存配置
 * 2. Windows服务管理：安装/卸载Redis为Windows服务
 * 3. 控制Redis：启动、停止、重启
 * 4. 运行时配置管理：可视化修改Redis配置
 */

// 状态
const status = ref<RedisStatusResponse | null>(null)
const isLoading = ref(false)
const message = ref<string | null>(null)
const messageType = ref<'success' | 'error' | 'info'>('info')

// 平台信息
const platformInfo = ref<PlatformInfo | null>(null)

// 服务安装状态
const isServiceInstalled = ref(false)

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

// ==================== 运行时配置管理 ====================

// 配置数据
const runtimeConfigs = ref<RedisRuntimeConfig[]>([])
const configLoading = ref(false)
const configError = ref<string | null>(null)
const hasConfigChanges = ref(false)

// 配置编辑状态
const editingConfigs = reactive<Record<string, string>>({})

// 配置分类
const configCategories = computed(() => {
  const categories: Record<string, RedisRuntimeConfig[]> = {
    network: [],
    security: [],
    performance: [],
    memory: [],
    persistence: [],
    monitoring: [],
    general: []
  }
  runtimeConfigs.value.forEach(config => {
    if (categories[config.config_type]) {
      categories[config.config_type].push(config)
    } else {
      categories.general.push(config)
    }
  })
  return categories
})

// 分类显示名称
const categoryNames: Record<string, string> = {
  network: '网络配置',
  security: '安全配置',
  performance: '性能配置',
  memory: '内存配置',
  persistence: '持久化配置',
  monitoring: '监控配置',
  general: '常规配置'
}

// 计算属性：是否显示配置管理（Redis运行中）
const showConfigManagement = computed(() => {
  return status.value?.is_loaded && status.value?.status === 'running'
})

// 配置项默认值映射
const configDefaults: Record<string, string> = {
  // 网络配置
  'port': '6379',
  'bind': '127.0.0.1',
  'protected-mode': 'yes',
  'tcp-backlog': '511',
  // 安全配置
  'requirepass': '',
  'masterauth': '',
  // 性能配置
  'maxclients': '10000',
  'timeout': '0',
  'tcp-keepalive': '300',
  'hz': '10',
  // 内存配置
  'maxmemory': '0',
  'maxmemory-policy': 'noeviction',
  'maxmemory-samples': '5',
  // 持久化配置
  'save': '3600 1 300 100 60 10000',
  'appendonly': 'no',
  'appendfsync': 'everysec',
  'auto-aof-rewrite-percentage': '100',
  'auto-aof-rewrite-min-size': '64mb',
  // 监控配置
  'slowlog-log-slower-than': '10000',
  'slowlog-max-len': '128',
  'latency-monitor-threshold': '0',
  // 常规配置
  'databases': '16',
  'loglevel': 'notice',
  'supervised': 'no'
}

/**
 * 加载Redis状态
 */
async function loadStatus() {
  try {
    const result = await getRedisStatus()
    console.log('[Redis] getRedisStatus 返回:', result)
    status.value = result
    console.log('[Redis] status.value 已更新:', status.value)
  } catch (e) {
    showMessage('获取状态失败: ' + e, 'error')
  }
}

/**
 * 加载平台信息
 */
async function loadPlatformInfo() {
  try {
    platformInfo.value = await getPlatformInfo()
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
    console.log('[Redis] loadRedis 返回:', result)

    if (result.success) {
      showMessage(result.message, 'success')
      console.log('[Redis] 准备调用 loadStatus 刷新状态')
      await loadStatus()
      console.log('[Redis] loadStatus 完成, 当前 status:', status.value)
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

// ==================== 运行时配置管理函数 ====================

/**
 * 加载Redis运行时配置
 */
async function loadRuntimeConfigs() {
  if (!showConfigManagement.value) return

  configLoading.value = true
  configError.value = null

  try {
    const response = await getRedisRuntimeConfigs()
    if (response.success) {
      runtimeConfigs.value = response.configs
      // 初始化编辑状态
      response.configs.forEach(config => {
        editingConfigs[config.name] = config.value
      })
      hasConfigChanges.value = false
    } else {
      configError.value = response.message
    }
  } catch (e) {
    configError.value = '加载配置失败: ' + e
  } finally {
    configLoading.value = false
  }
}

/**
 * 处理配置值变更
 */
function handleConfigChange(configName: string, value: string) {
  editingConfigs[configName] = value
  hasConfigChanges.value = true
}

/**
 * 保存配置变更
 */
async function saveRuntimeConfigs() {
  if (!hasConfigChanges.value) return

  configLoading.value = true

  try {
    // 构建变更列表
    const changedConfigs: RedisRuntimeConfigUpdateRequest[] = []
    runtimeConfigs.value.forEach(config => {
      if (editingConfigs[config.name] !== config.value) {
        changedConfigs.push({
          name: config.name,
          value: editingConfigs[config.name]
        })
      }
    })

    if (changedConfigs.length === 0) {
      configLoading.value = false
      return
    }

    // 批量更新配置
    const response = await batchUpdateRedisRuntimeConfigs({ configs: changedConfigs })

    if (response.success) {
      // 重写配置文件
      await rewriteRedisConfig()
      showMessage('配置已更新并保存到配置文件', 'success')
      hasConfigChanges.value = false
      // 重新加载配置
      await loadRuntimeConfigs()
    } else {
      showMessage(response.message, 'error')
    }
  } catch (e) {
    showMessage('保存配置失败: ' + e, 'error')
  } finally {
    configLoading.value = false
  }
}

/**
 * 重置配置变更
 */
function resetRuntimeConfigs() {
  runtimeConfigs.value.forEach(config => {
    editingConfigs[config.name] = config.value
  })
  hasConfigChanges.value = false
}

/**
 * 获取配置输入类型
 */
function getConfigInputType(configName: string): string {
  // 根据配置名判断输入类型
  const booleanConfigs = ['protected-mode', 'appendonly']
  const numberConfigs = ['port', 'maxclients', 'timeout', 'tcp-keepalive', 'hz', 'maxmemory', 'maxmemory-samples', 'slowlog-log-slower-than', 'slowlog-max-len', 'latency-monitor-threshold', 'databases']

  if (booleanConfigs.includes(configName)) {
    return 'select'
  }
  if (numberConfigs.includes(configName)) {
    return 'number'
  }
  return 'text'
}

/**
 * 获取配置选项（用于select类型）
 */
function getConfigOptions(configName: string): { label: string; value: string }[] {
  switch (configName) {
    case 'protected-mode':
    case 'appendonly':
      return [
        { label: '启用', value: 'yes' },
        { label: '禁用', value: 'no' }
      ]
    case 'maxmemory-policy':
      return [
        { label: '不淘汰', value: 'noeviction' },
        { label: '所有键LRU', value: 'allkeys-lru' },
        { label: '所有键随机', value: 'allkeys-random' },
        { label: '过期键LRU', value: 'volatile-lru' },
        { label: '过期键随机', value: 'volatile-random' },
        { label: '过期键TTL', value: 'volatile-ttl' }
      ]
    case 'appendfsync':
      return [
        { label: '总是同步', value: 'always' },
        { label: '每秒同步', value: 'everysec' },
        { label: '不同步', value: 'no' }
      ]
    case 'loglevel':
      return [
        { label: '调试', value: 'debug' },
        { label: '详细', value: 'verbose' },
        { label: '通知', value: 'notice' },
        { label: '警告', value: 'warning' }
      ]
    default:
      return []
  }
}

/**
 * 页面加载时获取状态
 */
onMounted(async () => {
  await loadPlatformInfo()
  await loadStatus()
  await checkServiceStatus()
  await loadRuntimeConfigs()
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

    <!-- Redis运行时配置管理卡片 -->
    <div class="config-card" v-if="showConfigManagement">
      <div class="config-header">
        <h2>运行时配置</h2>
        <span v-if="hasConfigChanges" class="unsaved-badge">有未保存的更改</span>
      </div>

      <!-- 加载状态 -->
      <div v-if="configLoading && runtimeConfigs.length === 0" class="status-box info">
        <span class="spinner"></span>
        <span class="loading-text">正在加载配置...</span>
      </div>

      <!-- 错误提示 -->
      <div v-if="configError" class="status-box error">
        <span class="status-icon">⚠️</span>
        <span>{{ configError }}</span>
      </div>

      <!-- 配置表单 -->
      <div v-if="runtimeConfigs.length > 0" class="runtime-config-form">
        <!-- 按分类渲染配置项 -->
        <div
          v-for="(configs, category) in configCategories"
          :key="category"
          class="preference-section"
        >
          <h3 v-if="configs.length > 0">{{ categoryNames[category] }}</h3>
          <div class="config-items">
            <div
              v-for="config in configs"
              :key="config.name"
              class="form-group"
            >
              <label class="form-label">
                {{ config.description }}
                <span class="config-name">({{ config.name }})</span>
              </label>

              <!-- select 类型输入 -->
              <select
                v-if="getConfigInputType(config.name) === 'select'"
                v-model="editingConfigs[config.name]"
                class="form-input"
                @change="handleConfigChange(config.name, editingConfigs[config.name])"
              >
                <option
                  v-for="option in getConfigOptions(config.name)"
                  :key="option.value"
                  :value="option.value"
                >
                  {{ option.label }}
                </option>
              </select>

              <!-- number 类型输入 -->
              <input
                v-else-if="getConfigInputType(config.name) === 'number'"
                v-model="editingConfigs[config.name]"
                type="number"
                class="form-input"
                @input="handleConfigChange(config.name, editingConfigs[config.name])"
              />

              <!-- text 类型输入 -->
              <input
                v-else
                v-model="editingConfigs[config.name]"
                type="text"
                class="form-input"
                @input="handleConfigChange(config.name, editingConfigs[config.name])"
              />

              <!-- 显示原始值（如果有变更） -->
              <div
                v-if="editingConfigs[config.name] !== config.value"
                class="config-original"
              >
                原始值: {{ config.value || '(空)' }}
              </div>

              <!-- 显示默认值提示 -->
              <div
                v-else-if="config.value === configDefaults[config.name] && configDefaults[config.name]"
                class="config-default"
              >
                默认值
              </div>
            </div>
          </div>
        </div>

        <!-- 操作按钮 -->
        <div class="config-actions">
          <button
            class="btn btn-secondary"
            @click="resetRuntimeConfigs"
            :disabled="!hasConfigChanges || configLoading"
          >
            重置
          </button>
          <button
            class="btn btn-primary"
            @click="saveRuntimeConfigs"
            :disabled="!hasConfigChanges || configLoading"
          >
            <span v-if="configLoading" class="spinner"></span>
            <span v-else>保存配置</span>
          </button>
        </div>

        <!-- 提示信息 -->
        <div class="status-box info mt-md">
          <span class="status-icon">ℹ️</span>
          <span>配置修改后会立即生效，并自动保存到Redis配置文件中。</span>
        </div>
      </div>
    </div>

    <!-- 配置管理提示（Redis未运行） -->
    <div class="config-card" v-else-if="status?.is_loaded && status?.status !== 'running'">
      <div class="config-header">
        <h2>运行时配置</h2>
      </div>
      <div class="status-box warning">
        <span class="status-icon">⚠️</span>
        <span>Redis未运行，请先启动Redis以管理运行时配置。</span>
      </div>
    </div>

  </div>
</template>

<style scoped>
@import '../styles/page-common.css';
@import '../styles/guide-steps.css';

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

/* 运行时配置管理样式 */
.runtime-config-form {
  margin-top: var(--spacing-lg);
}

.config-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--spacing-md);
}

.config-header h2 {
  margin: 0;
}

.unsaved-badge {
  padding: var(--spacing-xs) var(--spacing-sm);
  background-color: var(--warning-color);
  color: white;
  font-size: var(--font-size-xs);
  border-radius: var(--border-radius-sm);
  font-weight: 500;
}

.config-items {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: var(--spacing-md);
}

.config-name {
  color: var(--text-tertiary);
  font-size: var(--font-size-xs);
  font-weight: normal;
}

.config-original {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  margin-top: var(--spacing-xs);
}

.config-default {
  font-size: var(--font-size-xs);
  color: var(--success-color);
  margin-top: var(--spacing-xs);
}

.config-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-sm);
  margin-top: var(--spacing-lg);
  padding-top: var(--spacing-lg);
  border-top: 1px solid var(--border-color);
}

.mt-md {
  margin-top: var(--spacing-md);
}

/* 表单输入框样式增强 */
.form-input {
  width: 100%;
  padding: var(--spacing-sm);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius-md);
  background-color: var(--bg-secondary);
  color: var(--text-primary);
  font-size: var(--font-size-sm);
  transition: border-color var(--transition-fast);
}

.form-input:focus {
  outline: none;
  border-color: var(--primary-color);
}

.form-input:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

select.form-input {
  cursor: pointer;
}

/* 偏好设置区域样式 */
.preference-section {
  margin-bottom: var(--spacing-xl);
}

.preference-section h3 {
  font-size: var(--font-size-md);
  margin-bottom: var(--spacing-md);
  color: var(--text-primary);
  padding-bottom: var(--spacing-xs);
  border-bottom: 1px solid var(--border-color);
}

/* 状态框样式微调 */
.status-box {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-md);
  border-radius: var(--border-radius-md);
  background-color: var(--bg-tertiary);
}

.status-box.success {
  background-color: rgba(16, 185, 129, 0.1);
  border: 1px solid var(--success-color);
}

.status-box.warning {
  background-color: rgba(245, 158, 11, 0.1);
  border: 1px solid var(--warning-color);
}

.status-box.error {
  background-color: rgba(239, 68, 68, 0.1);
  border: 1px solid var(--error-color);
}

.status-box.info {
  background-color: rgba(6, 182, 212, 0.1);
  border: 1px solid var(--info-color);
}

.status-icon {
  flex-shrink: 0;
  font-size: var(--font-size-md);
}

.loading-text {
  color: var(--text-secondary);
}
</style>
