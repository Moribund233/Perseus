<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import Alert from '../components/Alert.vue'
import {
  updateAppConfig,
  resetAppConfig,
  validateAppConfig,
  getClientConfig,
  saveClientConfig,
  updateServerUrl,
  type ConfigResponse,
  type ClientConfig
} from '../services/api'
import { useServiceStore, useThemeStore, presetThemes, adjustableCssVars } from '../stores'

/**
 * 配置标签页类型
 */
type ConfigTab = 'theme' | 'server' | 'client' | 'advanced'

// 当前标签页
const activeTab = ref<ConfigTab>('theme')

// 加载状态
const isLoading = ref(false)
const isSaving = ref(false)
const error = ref<string | null>(null)
const successMessage = ref<string | null>(null)

// 使用Service Store
const serviceStore = useServiceStore()

// 从store获取服务端配置和状态
const serverConfigFromStore = computed(() => serviceStore.serverConfig)
const isServiceRunning = computed(() => serviceStore.isRunning)
const isServiceInitialized = computed(() => serviceStore.isInitialized)

/**
 * 服务端配置类型
 * 仅包含服务端允许修改的配置项
 * 参考: services/app_service.py ALLOWED_CONFIG_SECTIONS
 */
interface ServerConfig {
  server: {
    host: string
    port: number
    workers: number
    log_level: string
  }
}

// 服务端配置（仅包含允许修改的字段）
const serverConfig = ref<ServerConfig>({
  server: {
    host: '0.0.0.0',
    port: 8000,
    workers: 1,
    log_level: 'info'
  }
})

// 客户端配置（使用新的结构）
const clientConfig = ref<ClientConfig>({
  server: {
    url: 'http://127.0.0.1:8000',
    auto_connect: true,
    auto_start: false,
    path: {
      exe_name: 'langit-server.exe',
      dir_name: 'langit-server',
      custom_path: undefined
    }
  },
  appearance: {
    theme: 'dark',
    language: 'zh',
    sidebar_collapsed: false
  },
  notification: {
    enabled: true,
    on_error: true,
    on_warning: false,
    on_start_stop: true
  },
  log: {
    level: 'info',
    retention_days: 7
  },
  advanced: {
    ws_reconnect_interval: 3000,
    connection_timeout: 30,
    request_timeout: 30
  }
})

// 日志级别选项（与服务端配置匹配，小写）
const logLevels = ['debug', 'info', 'warning', 'error', 'critical']

// 主题选项
const themes = [
  { value: 'dark', label: '深色主题' },
  { value: 'light', label: '浅色主题' },
  { value: 'auto', label: '跟随系统' }
]

/**
 * 从store同步服务端配置
 */
const syncServerConfigFromStore = (): void => {
  if (serverConfigFromStore.value?.server) {
    serverConfig.value.server = { ...serverConfig.value.server, ...serverConfigFromStore.value.server }
  }
}

/**
 * 加载配置
 */
const loadConfigs = async (): Promise<void> => {
  isLoading.value = true
  error.value = null

  try {
    // 加载客户端配置
    const clientCfg = await getClientConfig()
    clientConfig.value = { ...clientConfig.value, ...clientCfg }
  } catch (err) {
    console.error('加载客户端配置失败:', err)
  }

  // 等待store初始化完成
  if (!isServiceInitialized.value) {
    await serviceStore.refreshStatus()
  }

  // 如果服务运行中，从store同步服务端配置
  if (isServiceRunning.value) {
    syncServerConfigFromStore()
  }

  isLoading.value = false
}

/**
 * 保存服务端配置
 */
const saveServerConfig = async (): Promise<void> => {
  isSaving.value = true
  error.value = null
  successMessage.value = null
  
  try {
    // 先验证配置
    const isValid = await validateAppConfig(serverConfig.value)
    if (!isValid) {
      error.value = '配置验证失败'
      return
    }
    
    const result: ConfigResponse = await updateAppConfig(serverConfig.value)

    if (result.success) {
      successMessage.value = '服务端配置保存成功'
      // 保存成功后刷新 store 中的配置
      await serviceStore.refreshServerConfig()
      setTimeout(() => successMessage.value = null, 3000)
    } else {
      error.value = result.errors?.[0] || '保存失败'
    }
  } catch (err) {
    console.error('保存服务端配置失败:', err)
    error.value = '保存服务端配置失败: ' + String(err)
  } finally {
    isSaving.value = false
  }
}

/**
 * 保存客户端配置
 */
const saveClientConfigHandler = async (): Promise<void> => {
  isSaving.value = true
  error.value = null
  successMessage.value = null
  
  try {
    await saveClientConfig(clientConfig.value)
    successMessage.value = '客户端配置保存成功'
    setTimeout(() => successMessage.value = null, 3000)
  } catch (err) {
    console.error('保存客户端配置失败:', err)
    error.value = '保存客户端配置失败: ' + String(err)
  } finally {
    isSaving.value = false
  }
}

/**
 * 重置服务端配置
 */
const handleResetConfig = async (): Promise<void> => {
  if (!confirm('确定要重置服务端配置吗？此操作将恢复默认设置。')) return
  
  isSaving.value = true
  error.value = null
  
  try {
    const result: ConfigResponse = await resetAppConfig()
    
    if (result.success) {
      // 重新加载配置
      await loadConfigs()
      successMessage.value = '配置已重置为默认值'
      setTimeout(() => successMessage.value = null, 3000)
    } else {
      error.value = result.errors?.[0] || '重置失败'
    }
  } catch (err) {
    console.error('重置配置失败:', err)
    error.value = '重置配置失败: ' + String(err)
  } finally {
    isSaving.value = false
  }
}

/**
 * 检查服务器连接
 * 手动触发连接检测，使用store的状态
 */
const checkServerConnection = async (): Promise<void> => {
  await serviceStore.refreshStatus()
}

/**
 * 更新服务器地址
 */
const handleUpdateServerUrl = async (): Promise<void> => {
  try {
    await updateServerUrl(clientConfig.value.server.url)
    await checkServerConnection()
    successMessage.value = '服务器地址已更新'
    setTimeout(() => successMessage.value = null, 3000)
  } catch (err) {
    error.value = '更新服务器地址失败: ' + String(err)
  }
}

/**
 * 获取连接状态样式
 * 使用store中的服务状态
 */
const getConnectionStatusClass = (): string => {
  if (!isServiceInitialized.value) return ''
  return isServiceRunning.value ? 'status-online' : 'status-offline'
}

/**
 * 获取连接状态文本
 * 使用store中的服务状态
 */
const getConnectionStatusText = (): string => {
  if (!isServiceInitialized.value) return '检测中...'
  return isServiceRunning.value ? '已连接' : '未连接'
}

// ==================== 主题设置相关 ====================

// 使用 Theme Store
const themeStore = useThemeStore()

/**
 * 处理主题切换
 */
const handleThemeChange = (themeId: string): void => {
  themeStore.switchTheme(themeId)
}

/**
 * 处理CSS变量变化
 */
const handleCssVarChange = (name: string, value: string): void => {
  if (value) {
    themeStore.setCssVar(name, value)
  }
}

/**
 * 获取CSS变量占位符
 */
const getCssVarPlaceholder = (name: string): string => {
  // 从computed style获取当前值
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  return value || '默认'
}

/**
 * 重置CSS变量
 */
const handleResetCssVars = (): void => {
  themeStore.resetCustomCssVars()
}

onMounted(() => {
  loadConfigs()

  // 监听store中的服务端配置变化，自动同步到本地
  watch(serverConfigFromStore, (newConfig) => {
    if (newConfig && isServiceRunning.value) {
      syncServerConfigFromStore()
    }
  }, { deep: true })
})
</script>

<template>
  <div class="settings">
    <h1 class="page-title">设置</h1>
    
    <!-- 消息提示 -->
    <Alert
      v-if="error"
      type="error"
      closable
      @close="error = null"
    >
      {{ error }}
    </Alert>

    <Alert
      v-if="successMessage"
      type="success"
      closable
      @close="successMessage = null"
    >
      {{ successMessage }}
    </Alert>
    
    <!-- 连接状态卡片 -->
    <div class="card connection-card">
      <div class="connection-status" :class="getConnectionStatusClass()">
        <div class="status-indicator"></div>
        <div class="status-info">
          <span class="status-text">{{ getConnectionStatusText() }}</span>
        </div>
      </div>
      <button
        class="btn btn-secondary btn-sm"
        @click="checkServerConnection"
        :disabled="serviceStore.isRefreshing"
      >
        <img
          src="@/assets/icons/refresh.svg"
          class="btn-icon"
          :class="{ spinning: serviceStore.isRefreshing }"
          alt="refresh"
        />
        检查连接
      </button>
    </div>
    
    <!-- 标签页 -->
    <div class="tabs">
      <button
        class="tab-btn"
        :class="{ active: activeTab === 'theme' }"
        @click="activeTab = 'theme'"
      >
        主题
      </button>
      <button
        class="tab-btn"
        :class="{ active: activeTab === 'server' }"
        @click="activeTab = 'server'"
      >
        服务端配置
      </button>
      <button
        class="tab-btn"
        :class="{ active: activeTab === 'client' }"
        @click="activeTab = 'client'"
      >
        客户端配置
      </button>
      <button
        class="tab-btn"
        :class="{ active: activeTab === 'advanced' }"
        @click="activeTab = 'advanced'"
      >
        高级设置
      </button>
    </div>
    
    <!-- 主题配置 -->
    <div v-show="activeTab === 'theme'" class="config-section">
      <div class="card">
        <div class="card-header">
          <h2 class="card-title">主题选择</h2>
        </div>

        <div class="theme-grid">
          <div
            v-for="theme in presetThemes"
            :key="theme.id"
            class="theme-item"
            :class="{ active: themeStore.currentThemeId === theme.id }"
            @click="handleThemeChange(theme.id)"
          >
            <div
              class="theme-preview"
              :style="{ backgroundColor: theme.previewColor }"
            ></div>
            <span class="theme-name">{{ theme.name }}</span>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <h2 class="card-title">外观设置</h2>
        </div>

        <div class="form-grid">
          <div
            v-for="cssVar in adjustableCssVars"
            :key="cssVar.name"
            class="form-group"
          >
            <label class="form-label">{{ cssVar.label }}</label>
            <input
              v-model="themeStore.customCssVars[cssVar.name]"
              type="text"
              class="form-input"
              :placeholder="getCssVarPlaceholder(cssVar.name)"
              @change="handleCssVarChange(cssVar.name, themeStore.customCssVars[cssVar.name])"
            />
          </div>
        </div>

        <div class="form-actions">
          <button class="btn btn-secondary" @click="handleResetCssVars">
            重置为默认
          </button>
        </div>
      </div>
    </div>

    <!-- 服务端配置 -->
    <div v-show="activeTab === 'server'" class="config-section">
      <!-- 重启提示 -->
      <div class="card info-card">
        <p class="info-text">
          <img src="@/assets/icons/info.svg" class="info-icon icon-info" alt="info" />
          修改主机地址、端口或工作进程数后需要重启服务才能生效
        </p>
      </div>

      <div class="card">
        <div class="card-header">
          <h2 class="card-title">服务器设置</h2>
          <span class="restart-badge">需重启</span>
        </div>
        
        <div class="form-grid">
          <div class="form-group">
            <label class="form-label">主机地址</label>
            <input 
              v-model="serverConfig.server.host" 
              type="text" 
              class="input"
              placeholder="0.0.0.0"
            />
          </div>
          
          <div class="form-group">
            <label class="form-label">端口</label>
            <input 
              v-model.number="serverConfig.server.port" 
              type="number" 
              class="input"
              min="1"
              max="65535"
            />
          </div>
          
          <div class="form-group">
            <label class="form-label">工作进程数</label>
            <input 
              v-model.number="serverConfig.server.workers" 
              type="number" 
              class="input"
              min="1"
              max="16"
            />
          </div>

          <div class="form-group">
            <label class="form-label">日志级别</label>
            <select v-model="serverConfig.server.log_level" class="input">
              <option v-for="level in logLevels" :key="level" :value="level">
                {{ level }}
              </option>
            </select>
          </div>
        </div>
      </div>
      
      <div class="form-actions">
        <button class="btn btn-primary" @click="saveServerConfig" :disabled="isSaving">
          <img
            v-if="isSaving"
            src="@/assets/icons/loader.svg"
            class="btn-icon spinning"
            alt="loading"
          />
          <span v-else>保存服务端配置</span>
        </button>

        <button class="btn btn-secondary" @click="handleResetConfig" :disabled="isSaving">
          重置为默认
        </button>
      </div>
    </div>
    
    <!-- 客户端配置 -->
    <div v-show="activeTab === 'client'" class="config-section">
      <div class="card">
        <div class="card-header">
          <h2 class="card-title">连接设置</h2>
        </div>
        
        <div class="form-group">
          <label class="form-label">服务器地址</label>
          <div class="input-group">
            <input 
              v-model="clientConfig.server.url" 
              type="text" 
              class="input"
              placeholder="http://127.0.0.1:8000"
            />
            <button class="btn btn-secondary" @click="handleUpdateServerUrl">
              更新
            </button>
          </div>
        </div>

        <div class="form-group checkbox-group">
          <label class="checkbox-label">
            <input v-model="clientConfig.server.auto_connect" type="checkbox" />
            <span>自动连接</span>
          </label>
        </div>

        <div class="form-group checkbox-group">
          <label class="checkbox-label">
            <input v-model="clientConfig.server.auto_start" type="checkbox" />
            <span>自动启动服务端</span>
          </label>
          <p class="help-text">启动客户端时自动启动服务端（仅桌面端有效）</p>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <h2 class="card-title">外观设置</h2>
        </div>

        <div class="form-group">
          <label class="form-label">主题</label>
          <select v-model="clientConfig.appearance.theme" class="input">
            <option v-for="theme in themes" :key="theme.value" :value="theme.value">
              {{ theme.label }}
            </option>
          </select>
        </div>

        <div class="form-group checkbox-group">
          <label class="checkbox-label">
            <input v-model="clientConfig.appearance.sidebar_collapsed" type="checkbox" />
            <span>侧边栏默认折叠</span>
          </label>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <h2 class="card-title">通知设置</h2>
        </div>

        <div class="form-group checkbox-group">
          <label class="checkbox-label">
            <input v-model="clientConfig.notification.enabled" type="checkbox" />
            <span>启用通知</span>
          </label>
        </div>

        <div class="form-group checkbox-group">
          <label class="checkbox-label">
            <input v-model="clientConfig.notification.on_error" type="checkbox" :disabled="!clientConfig.notification.enabled" />
            <span>错误时通知</span>
          </label>
        </div>

        <div class="form-group checkbox-group">
          <label class="checkbox-label">
            <input v-model="clientConfig.notification.on_start_stop" type="checkbox" :disabled="!clientConfig.notification.enabled" />
            <span>服务启动/停止时通知</span>
          </label>
        </div>
      </div>
      
      <div class="form-actions">
        <button class="btn btn-primary" @click="saveClientConfigHandler" :disabled="isSaving">
          <img
            v-if="isSaving"
            src="@/assets/icons/loader.svg"
            class="btn-icon spinning"
            alt="loading"
          />
          <span v-else>保存客户端配置</span>
        </button>
      </div>
    </div>

    <!-- 高级设置 -->
    <div v-show="activeTab === 'advanced'" class="config-section">
      <div class="card info-card">
        <p class="info-text">
          <img src="@/assets/icons/info.svg" class="info-icon icon-info" alt="info" />
          高级设置中的服务端配置项正在开发中，目前仅支持基础服务器设置
        </p>
      </div>

      <div class="card danger-zone">
        <div class="card-header">
          <h2 class="card-title">危险区域</h2>
        </div>
        
        <div class="danger-actions">
          <div class="danger-item">
            <div class="danger-info">
              <h3>重置所有配置</h3>
              <p>这将删除所有自定义配置并恢复默认设置</p>
            </div>
            <button class="btn btn-error" @click="handleResetConfig">
              重置配置
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.settings {
  max-width: 1000px;
}

/* 连接卡片 */
.connection-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-md);
  margin-bottom: var(--spacing-lg);
}

.connection-status {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.status-detail {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}

/* 危险区域 */
.danger-zone .card-title {
  color: var(--error-color);
}

/* 重启标签 */
.restart-badge {
  display: inline-block;
  padding: 2px 8px;
  background-color: var(--warning-color);
  color: white;
  font-size: var(--font-size-xs);
  border-radius: var(--border-radius-sm);
  margin-left: var(--spacing-sm);
}

/* 帮助文本 */
.help-text {
  margin-left: 26px;
}

input:disabled {
  background-color: var(--bg-secondary);
}

/* 主题选择网格 */
.theme-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: var(--spacing-lg);
  padding: var(--spacing-md);
}

.theme-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-md);
  border-radius: var(--border-radius-md);
  cursor: pointer;
  transition: all var(--transition-fast);
  border: 2px solid transparent;
}

.theme-item:hover {
  background-color: var(--bg-hover);
}

.theme-item.active {
  border-color: var(--primary-color);
  background-color: var(--primary-light);
}

.theme-preview {
  width: 60px;
  height: 60px;
  border-radius: var(--border-radius-lg);
  box-shadow: var(--shadow-md);
}

.theme-name {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  text-align: center;
}

.theme-item.active .theme-name {
  color: var(--primary-color);
  font-weight: 600;
}
</style>
