<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import Alert from '../components/Alert.vue'
import {
  updateAppConfig,
  resetAppConfig,
  resetClientConfig,
  validateAppConfig,
  getClientConfig,
  saveClientConfig,
  updateServerUrl,
  setSecurityPassword,
  verifySecurityPassword,
  hasSecurityPassword,
  getDebugMode,
  updateDebugMode,
  resetAllTokens,
  isElevated,
  getJwtSecretKey,
  getLocalToken,
  type ConfigResponse,
  type ClientConfig
} from '../services/api'
import { useRouter } from 'vue-router'
import { useServiceStore, useThemeStore, presetColorThemes, layoutDensityPresets } from '../stores'

/**
 * 配置标签页类型
 */
type ConfigTab = 'theme' | 'server' | 'client' | 'advanced'

// 图标路径
const refreshIcon = new URL('../assets/icons/refresh.svg', import.meta.url).href
const infoIcon = new URL('../assets/icons/info.svg', import.meta.url).href
const loaderIcon = new URL('../assets/icons/loader.svg', import.meta.url).href

// 当前标签页
const activeTab = ref<ConfigTab>('theme')

// 加载状态
const isLoading = ref(false)
const isSaving = ref(false)
const error = ref<string | null>(null)
const successMessage = ref<string | null>(null)

// 使用Service Store
const serviceStore = useServiceStore()
const router = useRouter()

// 危险操作验证对话框状态
const dangerDialog = ref<{
  show: boolean
  title: string
  message: string
  confirmText: string
  expectedInput: string
  action: 'resetServer' | 'resetClient' | 'resetTokens' | null
}>({
  show: false,
  title: '',
  message: '',
  confirmText: '',
  expectedInput: '',
  action: null
})

const dangerInput = ref('')

// 敏感配置区域状态
const sensitiveConfig = ref({
  isExpanded: false,
  isAuthenticated: false,
  hasPassword: false,
  password: '',
  passwordError: '',
  debugMode: true,
  isElevated: false,
  jwtKey: '',
  localToken: '',
  showTokens: false
})

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
 * 打开危险操作验证对话框
 */
const openDangerDialog = (
  action: 'resetServer' | 'resetClient' | 'resetTokens',
  title: string,
  message: string,
  confirmText: string,
  expectedInput: string
): void => {
  dangerDialog.value = {
    show: true,
    title,
    message,
    confirmText,
    expectedInput,
    action
  }
  dangerInput.value = ''
}

/**
 * 关闭危险操作验证对话框
 */
const closeDangerDialog = (): void => {
  dangerDialog.value.show = false
  dangerInput.value = ''
}

/**
 * 确认危险操作
 */
const confirmDangerAction = async (): Promise<void> => {
  if (dangerInput.value !== dangerDialog.value.expectedInput) {
    error.value = '输入内容不匹配，操作已取消'
    closeDangerDialog()
    return
  }

  isSaving.value = true
  error.value = null

  try {
    if (dangerDialog.value.action === 'resetServer') {
      const result: ConfigResponse = await resetAppConfig()
      if (result.success) {
        await loadConfigs()
        successMessage.value = '服务端配置已重置为默认值'
      } else {
        error.value = result.errors?.[0] || '重置失败'
      }
    } else if (dangerDialog.value.action === 'resetClient') {
      await resetClientConfig()
      successMessage.value = '客户端配置已重置，即将重新进入引导流程'
      setTimeout(() => {
        router.replace('/guide')
      }, 2000)
    } else if (dangerDialog.value.action === 'resetTokens') {
      await resetAllTokens()
      successMessage.value = '安全令牌已重置'
      setTimeout(() => successMessage.value = null, 3000)
    }
  } catch (err) {
    console.error('危险操作失败:', err)
    error.value = '操作失败: ' + String(err)
  } finally {
    isSaving.value = false
    closeDangerDialog()
  }
}

/**
 * 重置服务端配置
 */
const handleResetServerConfig = (): void => {
  openDangerDialog(
    'resetServer',
    '重置服务端配置',
    '此操作将重置服务端配置为默认值。请输入 "RESET" 确认操作。',
    '重置服务端配置',
    'RESET'
  )
}

/**
 * 重置客户端配置
 */
const handleResetClientConfig = (): void => {
  openDangerDialog(
    'resetClient',
    '重置客户端配置',
    '此操作将删除所有客户端配置并重新进入引导流程。请输入 "RESET CLIENT" 确认操作。',
    '重置客户端配置',
    'RESET CLIENT'
  )
}

// ==================== 敏感配置相关 ====================

/**
 * 检查敏感配置状态
 */
const checkSensitiveConfigStatus = async (): Promise<void> => {
  try {
    sensitiveConfig.value.hasPassword = await hasSecurityPassword()
    sensitiveConfig.value.debugMode = await getDebugMode()
    sensitiveConfig.value.isElevated = await isElevated()
  } catch (err) {
    console.error('检查敏感配置状态失败:', err)
  }
}

/**
 * 切换敏感配置区域展开状态
 */
const toggleSensitiveConfig = async (): Promise<void> => {
  if (!sensitiveConfig.value.isExpanded) {
    // 展开前检查状态
    await checkSensitiveConfigStatus()
    sensitiveConfig.value.isExpanded = true
  } else {
    sensitiveConfig.value.isExpanded = false
    sensitiveConfig.value.isAuthenticated = false
    sensitiveConfig.value.password = ''
  }
}

/**
 * 验证安全密码
 */
const verifyPassword = async (): Promise<void> => {
  if (!sensitiveConfig.value.password) {
    sensitiveConfig.value.passwordError = '请输入安全密码'
    return
  }

  try {
    const isValid = await verifySecurityPassword(sensitiveConfig.value.password)
    if (isValid) {
      sensitiveConfig.value.isAuthenticated = true
      sensitiveConfig.value.passwordError = ''
      sensitiveConfig.value.password = ''
      // 验证成功后加载 Token
      await loadTokens()
    } else {
      sensitiveConfig.value.passwordError = '密码错误'
    }
  } catch (err) {
    console.error('验证密码失败:', err)
    sensitiveConfig.value.passwordError = '验证失败: ' + String(err)
  }
}

/**
 * 加载 Token 信息
 */
const loadTokens = async (): Promise<void> => {
  try {
    sensitiveConfig.value.jwtKey = await getJwtSecretKey()
    sensitiveConfig.value.localToken = await getLocalToken()
  } catch (err) {
    console.error('加载 Token 失败:', err)
  }
}

/**
 * 设置安全密码
 */
const handleSetSecurityPassword = async (): Promise<void> => {
  if (!sensitiveConfig.value.password || sensitiveConfig.value.password.length < 6) {
    error.value = '密码长度至少为6位'
    return
  }

  isSaving.value = true
  try {
    await setSecurityPassword(sensitiveConfig.value.password)
    sensitiveConfig.value.hasPassword = true
    sensitiveConfig.value.isAuthenticated = true
    successMessage.value = '安全密码设置成功'
    setTimeout(() => successMessage.value = null, 3000)
  } catch (err) {
    console.error('设置密码失败:', err)
    error.value = '设置密码失败: ' + String(err)
  } finally {
    isSaving.value = false
  }
}

/**
 * 更新调试模式
 */
const handleUpdateDebugMode = async (debug: boolean): Promise<void> => {
  isSaving.value = true
  try {
    await updateDebugMode(debug)
    sensitiveConfig.value.debugMode = debug
    successMessage.value = debug ? '调试模式已启用' : '调试模式已禁用'
    setTimeout(() => successMessage.value = null, 3000)
  } catch (err) {
    console.error('更新调试模式失败:', err)
    error.value = '更新失败: ' + String(err)
  } finally {
    isSaving.value = false
  }
}

/**
 * 打开重置令牌对话框
 */
const handleResetTokens = async (): Promise<void> => {
  // 检查是否已提升权限
  const elevated = await isElevated()
  if (!elevated) {
    error.value = '需要以管理员权限运行才能执行此操作'
    return
  }

  openDangerDialog(
    'resetTokens',
    '重置安全令牌',
    '此操作将重置 JWT 密钥和本地 Token。请输入 "RESET TOKENS" 确认操作。',
    '重置令牌',
    'RESET TOKENS'
  )
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
 * 处理颜色主题切换
 */
const handleColorThemeChange = (themeId: string): void => {
  themeStore.switchColorTheme(themeId)
}

/**
 * 处理布局密度切换
 */
const handleLayoutDensityChange = (densityId: string): void => {
  themeStore.switchLayoutDensity(densityId)
}

/**
 * 选择服务端可执行文件路径
 */
const selectServerPath = async (): Promise<void> => {
  try {
    const { open } = await import('@tauri-apps/plugin-dialog')
    const selected = await open({
      multiple: false,
      filters: [{ name: 'Executable', extensions: ['exe'] }]
    })
    if (selected && typeof selected === 'string') {
      clientConfig.value.server.path.custom_path = selected
    }
  } catch (err) {
    console.error('选择文件失败:', err)
    error.value = '选择文件失败: ' + String(err)
  }
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
          :src="refreshIcon"
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
      <!-- 颜色主题选择 -->
      <div class="card">
        <div class="card-header">
          <h2 class="card-title">颜色主题</h2>
        </div>

        <div class="theme-grid">
          <div
            v-for="theme in presetColorThemes"
            :key="theme.id"
            class="theme-item"
            :class="{ active: themeStore.currentColorThemeId === theme.id }"
            @click="handleColorThemeChange(theme.id)"
          >
            <div
              class="theme-preview"
              :style="{ backgroundColor: theme.previewColor }"
            ></div>
            <span class="theme-name">{{ theme.name }}</span>
          </div>
        </div>
      </div>

      <!-- 布局密度选择 -->
      <div class="card">
        <div class="card-header">
          <h2 class="card-title">布局密度</h2>
        </div>

        <div class="density-grid">
          <div
            v-for="density in layoutDensityPresets"
            :key="density.id"
            class="density-item"
            :class="{ active: themeStore.currentLayoutDensityId === density.id }"
            @click="handleLayoutDensityChange(density.id)"
          >
            <div class="density-preview" :class="`density-preview-${density.id}`">
              <div class="preview-block"></div>
              <div class="preview-block"></div>
              <div class="preview-block"></div>
            </div>
            <span class="density-name">{{ density.name }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 服务端配置 -->
    <div v-show="activeTab === 'server'" class="config-section">
      <!-- 重启提示 -->
      <div class="card info-card">
        <p class="info-text">
          <img :src="infoIcon" class="info-icon icon-info" alt="info" />
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
            :src="loaderIcon"
            class="btn-icon spinning"
            alt="loading"
          />
          <span v-else>保存服务端配置</span>
        </button>

        <button class="btn btn-secondary" @click="handleResetServerConfig" :disabled="isSaving">
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

        <div class="form-group">
          <label class="form-label">服务端路径</label>
          <div class="input-group">
            <input
              v-model="clientConfig.server.path.custom_path"
              type="text"
              class="input"
              placeholder="默认路径"
            />
            <button class="btn btn-secondary" @click="selectServerPath">
              选择文件
            </button>
          </div>
          <p class="help-text">指定服务端可执行文件的完整路径，留空使用默认路径</p>
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
            <input v-model="clientConfig.notification.on_warning" type="checkbox" :disabled="!clientConfig.notification.enabled" />
            <span>警告时通知</span>
          </label>
        </div>

        <div class="form-group checkbox-group">
          <label class="checkbox-label">
            <input v-model="clientConfig.notification.on_start_stop" type="checkbox" :disabled="!clientConfig.notification.enabled" />
            <span>服务启动/停止时通知</span>
          </label>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <h2 class="card-title">日志设置</h2>
        </div>

        <div class="form-group">
          <label class="form-label">日志级别</label>
          <select v-model="clientConfig.log.level" class="input">
            <option value="debug">Debug - 调试信息</option>
            <option value="info">Info - 一般信息</option>
            <option value="warning">Warning - 警告信息</option>
            <option value="error">Error - 错误信息</option>
          </select>
        </div>

        <div class="form-group">
          <label class="form-label">日志保留天数</label>
          <input
            v-model.number="clientConfig.log.retention_days"
            type="number"
            class="input"
            min="1"
            max="365"
          />
          <p class="help-text">超过此天数的日志将被自动清理</p>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <h2 class="card-title">高级设置</h2>
        </div>

        <div class="form-group">
          <label class="form-label">WebSocket 重连间隔 (毫秒)</label>
          <input
            v-model.number="clientConfig.advanced.ws_reconnect_interval"
            type="number"
            class="input"
            min="1000"
            max="60000"
            step="100"
          />
        </div>
      </div>

      <div class="form-actions">
        <button class="btn btn-primary" @click="saveClientConfigHandler" :disabled="isSaving">
          <img
            v-if="isSaving"
            :src="loaderIcon"
            class="btn-icon spinning"
            alt="loading"
          />
          <span v-else>保存客户端配置</span>
        </button>
      </div>
    </div>

    <!-- 高级设置 -->
    <div v-show="activeTab === 'advanced'" class="config-section">
      <div class="card">
        <div class="card-header">
          <h2 class="card-title">客户端高级设置</h2>
        </div>

        <div class="form-group">
          <label class="form-label">WebSocket 重连间隔 (毫秒)</label>
          <input
            v-model.number="clientConfig.advanced.ws_reconnect_interval"
            type="number"
            class="input"
            min="1000"
            max="60000"
            step="100"
          />
          <p class="help-text">连接断开后的自动重连间隔</p>
        </div>

        <div class="form-group">
          <label class="form-label">连接超时 (秒)</label>
          <input
            v-model.number="clientConfig.advanced.connection_timeout"
            type="number"
            class="input"
            min="5"
            max="300"
          />
        </div>

        <div class="form-group">
          <label class="form-label">请求超时 (秒)</label>
          <input
            v-model.number="clientConfig.advanced.request_timeout"
            type="number"
            class="input"
            min="5"
            max="300"
          />
        </div>

        <div class="form-actions" style="margin-top: var(--spacing-lg);">
          <button class="btn btn-primary" @click="saveClientConfigHandler" :disabled="isSaving">
            <img
              v-if="isSaving"
              :src="loaderIcon"
              class="btn-icon spinning"
              alt="loading"
            />
            <span v-else>保存高级设置</span>
          </button>
        </div>
      </div>

      <div class="card danger-zone">
        <div class="card-header">
          <h2 class="card-title">危险区域</h2>
        </div>

        <div class="danger-actions">
          <!-- 敏感配置项 -->
          <div class="danger-item sensitive-danger-item" :class="{ expanded: sensitiveConfig.isExpanded }">
            <div class="danger-info" @click="toggleSensitiveConfig">
              <h3>敏感配置</h3>
              <p>管理调试模式和安全令牌</p>
              <span class="expand-hint">{{ sensitiveConfig.isExpanded ? '点击收起 ▲' : '点击展开 ▼' }}</span>
            </div>
          </div>

          <!-- 敏感配置展开内容 -->
          <div v-if="sensitiveConfig.isExpanded" class="sensitive-expanded-content">
            <!-- 第一层：密码验证 -->
            <div v-if="!sensitiveConfig.isAuthenticated" class="sensitive-verify-section">
              <p class="sensitive-description">
                此区域包含敏感配置，需要验证安全密码才能访问。
                <span v-if="!sensitiveConfig.hasPassword">（首次使用请设置密码）</span>
              </p>
              <div class="sensitive-form">
                <div class="form-group">
                  <label class="form-label">安全密码</label>
                  <input
                    v-model="sensitiveConfig.password"
                    type="password"
                    class="input"
                    :class="{ 'input-error': sensitiveConfig.passwordError }"
                    placeholder="请输入安全密码"
                    @keyup.enter="sensitiveConfig.hasPassword ? verifyPassword() : handleSetSecurityPassword()"
                  />
                  <span v-if="sensitiveConfig.passwordError" class="input-error-text">{{ sensitiveConfig.passwordError }}</span>
                </div>
                <div class="form-actions-inline">
                  <button
                    v-if="sensitiveConfig.hasPassword"
                    class="btn btn-primary"
                    @click="verifyPassword"
                    :disabled="isSaving"
                  >
                    验证密码
                  </button>
                  <button
                    v-else
                    class="btn btn-primary"
                    @click="handleSetSecurityPassword"
                    :disabled="isSaving"
                  >
                    设置密码
                  </button>
                </div>
              </div>
            </div>

            <!-- 第二层：已认证后的操作 -->
            <div v-else class="sensitive-authenticated-section">
              <!-- 查看 Token -->
              <div class="sensitive-subsection">
                <div class="token-view-header">
                  <h4>安全令牌查看</h4>
                  <button
                    class="btn btn-sm"
                    :class="sensitiveConfig.showTokens ? 'btn-secondary' : 'btn-primary'"
                    @click="sensitiveConfig.showTokens = !sensitiveConfig.showTokens"
                  >
                    {{ sensitiveConfig.showTokens ? '隐藏' : '显示' }}
                  </button>
                </div>
                <div v-if="sensitiveConfig.showTokens" class="token-display-area">
                  <div class="token-item">
                    <label>JWT 密钥:</label>
                    <div class="token-value no-select">{{ sensitiveConfig.jwtKey }}</div>
                  </div>
                  <div class="token-item">
                    <label>本地 Token:</label>
                    <div class="token-value no-select">{{ sensitiveConfig.localToken }}</div>
                  </div>
                  <p class="token-hint">⚠️ 仅用于开发调试，请勿泄露或复制这些值</p>
                </div>
              </div>

              <!-- Debug模式 -->
              <div class="sensitive-subsection">
                <h4>调试设置</h4>
                <div class="form-group checkbox-group">
                  <label class="checkbox-label">
                    <input
                      type="checkbox"
                      :checked="sensitiveConfig.debugMode"
                      @change="handleUpdateDebugMode(!sensitiveConfig.debugMode)"
                    />
                    <span>启用调试模式</span>
                  </label>
                  <p class="help-text">启用后将显示详细的调试信息</p>
                </div>
              </div>

              <!-- Token重置 -->
              <div class="sensitive-subsection token-reset-section">
                <h4>安全令牌管理</h4>
                <div class="danger-item-inner">
                  <div class="danger-info">
                    <h5>重置安全令牌</h5>
                    <p>重置 JWT 密钥和本地 Token</p>
                    <p v-if="!sensitiveConfig.isElevated" class="elevate-warning">
                      ⚠️ 需要以管理员权限运行才能执行此操作
                    </p>
                  </div>
                  <button
                    class="btn btn-error"
                    @click="handleResetTokens"
                    :disabled="!sensitiveConfig.isElevated"
                  >
                    重置令牌
                  </button>
                </div>
              </div>

              <div class="form-actions-inline">
                <button class="btn btn-secondary" @click="sensitiveConfig.isAuthenticated = false">
                  锁定配置
                </button>
              </div>
            </div>
          </div>

          <div class="danger-divider"></div>

          <div class="danger-item">
            <div class="danger-info">
              <h3>重置服务端配置</h3>
              <p>将服务端配置恢复为默认值</p>
            </div>
            <button class="btn btn-error" @click="handleResetServerConfig">
              重置服务端配置
            </button>
          </div>

          <div class="danger-item">
            <div class="danger-info">
              <h3>重置客户端配置</h3>
              <p>删除所有客户端配置并重新进入引导流程</p>
            </div>
            <button class="btn btn-error" @click="handleResetClientConfig">
              重置客户端配置
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 危险操作验证对话框 -->
    <div v-if="dangerDialog.show" class="danger-dialog-overlay" @click.self="closeDangerDialog">
      <div class="danger-dialog">
        <div class="danger-dialog-header">
          <h3 class="danger-dialog-title">{{ dangerDialog.title }}</h3>
        </div>
        <div class="danger-dialog-body">
          <p class="danger-dialog-message">{{ dangerDialog.message }}</p>
          <div class="form-group">
            <label class="form-label">请输入 "{{ dangerDialog.expectedInput }}" 确认</label>
            <input
              v-model="dangerInput"
              type="text"
              class="input danger-input"
              :placeholder="dangerDialog.expectedInput"
              @keyup.enter="confirmDangerAction"
            />
          </div>
        </div>
        <div class="danger-dialog-footer">
          <button class="btn btn-secondary" @click="closeDangerDialog">取消</button>
          <button
            class="btn btn-error"
            :disabled="dangerInput !== dangerDialog.expectedInput || isSaving"
            @click="confirmDangerAction"
          >
            {{ dangerDialog.confirmText }}
          </button>
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

/* 布局密度网格 */
.density-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
  gap: var(--spacing-md);
}

.density-item {
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

.density-item:hover {
  background-color: var(--bg-hover);
}

.density-item.active {
  border-color: var(--primary-color);
  background-color: var(--primary-light);
}

.density-preview {
  width: 60px;
  height: 60px;
  background-color: var(--bg-tertiary);
  border-radius: var(--border-radius-md);
  display: flex;
  flex-direction: column;
  padding: 4px;
  gap: 4px;
}

.density-preview-compact {
  padding: 2px;
  gap: 2px;
}

.density-preview-compact .preview-block {
  height: 14px;
  border-radius: 2px;
}

.density-preview-default {
  padding: 4px;
  gap: 4px;
}

.density-preview-default .preview-block {
  height: 14px;
  border-radius: 4px;
}

.density-preview-comfortable {
  padding: 6px;
  gap: 6px;
}

.density-preview-comfortable .preview-block {
  height: 12px;
  border-radius: 6px;
}

.density-preview-spacious {
  padding: 8px;
  gap: 8px;
}

.density-preview-spacious .preview-block {
  height: 10px;
  border-radius: 8px;
}

.preview-block {
  background-color: var(--primary-color);
  opacity: 0.6;
  flex: 1;
  min-height: 8px;
}

.density-name {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  text-align: center;
}

.density-item.active .density-name {
  color: var(--primary-color);
  font-weight: 600;
}

/* 危险操作对话框 */
.danger-dialog-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.danger-dialog {
  background-color: var(--bg-secondary);
  border-radius: var(--border-radius-lg);
  width: 90%;
  max-width: 500px;
  box-shadow: var(--shadow-lg);
  border: 1px solid var(--error-color);
}

.danger-dialog-header {
  padding: var(--spacing-lg);
  border-bottom: 1px solid var(--border-color);
}

.danger-dialog-title {
  color: var(--error-color);
  font-size: var(--font-size-lg);
  font-weight: 600;
  margin: 0;
}

.danger-dialog-body {
  padding: var(--spacing-lg);
}

.danger-dialog-message {
  color: var(--text-secondary);
  margin-bottom: var(--spacing-lg);
  line-height: 1.6;
}

.danger-input {
  border-color: var(--error-color);
}

.danger-input:focus {
  border-color: var(--error-color);
  box-shadow: 0 0 0 2px rgba(239, 68, 68, 0.2);
}

.danger-dialog-footer {
  padding: var(--spacing-lg);
  border-top: 1px solid var(--border-color);
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-md);
}

/* 敏感配置区域 */
.sensitive-zone {
  border: 1px solid var(--warning-color);
}

.sensitive-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  user-select: none;
}

.sensitive-header:hover {
  background-color: var(--bg-hover);
}

.expand-icon {
  font-size: 12px;
  transition: transform 0.3s ease;
  color: var(--text-secondary);
}

.expand-icon.expanded {
  transform: rotate(180deg);
}

.sensitive-content {
  padding: var(--spacing-lg);
  border-top: 1px solid var(--border-color);
}

.sensitive-description {
  color: var(--text-secondary);
  margin-bottom: var(--spacing-lg);
}

.password-verify {
  max-width: 400px;
}

.sensitive-section {
  margin-bottom: var(--spacing-xl);
  padding-bottom: var(--spacing-lg);
  border-bottom: 1px solid var(--border-color);
}

.sensitive-section:last-of-type {
  border-bottom: none;
}

.sensitive-section h3 {
  font-size: var(--font-size-md);
  color: var(--text-primary);
  margin-bottom: var(--spacing-md);
}

.danger-subsection {
  background-color: var(--bg-tertiary);
  padding: var(--spacing-lg);
  border-radius: var(--border-radius-md);
  border: 1px solid var(--error-color);
}

.danger-subsection h3 {
  color: var(--error-color);
}

.elevate-warning {
  color: var(--warning-color);
  font-size: var(--font-size-sm);
  margin-top: var(--spacing-sm);
}

.checkbox-group {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  cursor: pointer;
}

.checkbox-label input[type="checkbox"] {
  width: 18px;
  height: 18px;
  cursor: pointer;
}

/* 敏感配置在危险区域内的样式 */
.sensitive-danger-item {
  cursor: pointer;
  border: 1px solid transparent;
  border-radius: var(--border-radius-md);
  transition: all var(--transition-fast);
}

.sensitive-danger-item:hover {
  background-color: var(--bg-tertiary);
  border-color: var(--warning-color);
}

.sensitive-danger-item.expanded {
  background-color: var(--bg-tertiary);
  border-color: var(--warning-color);
}

.expand-hint {
  font-size: var(--font-size-xs);
  color: var(--text-secondary);
  margin-top: var(--spacing-xs);
}

.danger-divider {
  height: 1px;
  background-color: var(--border-color);
  margin: var(--spacing-md) 0;
}

.sensitive-expanded-content {
  background-color: var(--bg-tertiary);
  border-radius: var(--border-radius-md);
  padding: var(--spacing-lg);
  margin-top: var(--spacing-md);
}

.sensitive-verify-section {
  max-width: 400px;
}

.sensitive-description {
  color: var(--text-secondary);
  margin-bottom: var(--spacing-lg);
  font-size: var(--font-size-sm);
}

.sensitive-form .form-group {
  margin-bottom: var(--spacing-md);
}

.sensitive-form .form-label {
  display: block;
  margin-bottom: var(--spacing-xs);
  color: var(--text-secondary);
  font-size: var(--font-size-sm);
}

.sensitive-form .input {
  width: 100%;
  padding: var(--spacing-sm);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius-md);
  background-color: var(--bg-secondary);
  color: var(--text-primary);
  font-size: var(--font-size-sm);
}

.sensitive-form .input:focus {
  outline: none;
  border-color: var(--primary-color);
}

.sensitive-form .input-error {
  border-color: var(--error-color);
}

.sensitive-form .input-error:focus {
  border-color: var(--error-color);
  box-shadow: 0 0 0 2px rgba(239, 68, 68, 0.2);
}

.input-error-text {
  display: block;
  font-size: var(--font-size-xs);
  color: var(--error-color);
  margin-top: var(--spacing-xs);
}

.form-actions-inline {
  display: flex;
  gap: var(--spacing-sm);
}

.sensitive-authenticated-section {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
}

.sensitive-subsection {
  padding-bottom: var(--spacing-lg);
  border-bottom: 1px solid var(--border-color);
}

.sensitive-subsection:last-of-type {
  border-bottom: none;
  padding-bottom: 0;
}

.sensitive-subsection h4 {
  font-size: var(--font-size-sm);
  color: var(--text-primary);
  margin-bottom: var(--spacing-md);
  font-weight: 600;
}

.token-reset-section {
  background-color: var(--bg-secondary);
  padding: var(--spacing-md);
  border-radius: var(--border-radius-md);
  border: 1px solid var(--error-color);
}

.token-reset-section h4 {
  color: var(--error-color);
}

.danger-item-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-md);
}

.danger-item-inner .danger-info h5 {
  font-size: var(--font-size-sm);
  color: var(--text-primary);
  margin-bottom: var(--spacing-xs);
}

.danger-item-inner .danger-info p {
  font-size: var(--font-size-xs);
  color: var(--text-secondary);
}

.elevate-warning {
  color: var(--warning-color);
  font-size: var(--font-size-xs);
  margin-top: var(--spacing-xs);
}

/* Token 查看区域样式 */
.token-view-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-md);
}

.token-view-header h4 {
  margin: 0;
}

.token-display-area {
  background-color: var(--bg-secondary);
  padding: var(--spacing-md);
  border-radius: var(--border-radius-md);
  border: 1px solid var(--border-color);
}

.token-item {
  margin-bottom: var(--spacing-md);
}

.token-item:last-child {
  margin-bottom: 0;
}

.token-item label {
  display: block;
  font-size: var(--font-size-xs);
  color: var(--text-secondary);
  margin-bottom: var(--spacing-xs);
}

.token-value {
  font-family: monospace;
  font-size: var(--font-size-xs);
  color: var(--text-primary);
  background-color: var(--bg-tertiary);
  padding: var(--spacing-sm);
  border-radius: var(--border-radius-sm);
  word-break: break-all;
  line-height: 1.5;
}

.no-select {
  user-select: none;
  -webkit-user-select: none;
  -moz-user-select: none;
  -ms-user-select: none;
}

.token-hint {
  font-size: var(--font-size-xs);
  color: var(--warning-color);
  margin-top: var(--spacing-md);
  text-align: center;
}
</style>
