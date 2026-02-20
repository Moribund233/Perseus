<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import Alert from '../components/Alert.vue'
import ThemeSettings from '../components/settings/ThemeSettings.vue'
import ServerSettings from '../components/settings/ServerSettings.vue'
import ClientSettings from '../components/settings/ClientSettings.vue'
import CORSSettings from '../components/settings/CORSSettings.vue'
import AdvancedSettings from '../components/settings/AdvancedSettings.vue'
import DeveloperOptions from '../components/settings/DeveloperOptions.vue'
import {
  resetAppConfig,
  getClientConfig,
  type ClientConfig,
  type ConfigResponse
} from '../services/api'
import { useServiceStore } from '../stores'

/**
 * 配置标签页类型
 */
type ConfigTab = 'theme' | 'server' | 'client' | 'cors' | 'advanced' | 'developer'

// 图标路径
const refreshIcon = new URL('../assets/icons/refresh.svg', import.meta.url).href

// 当前标签页
const activeTab = ref<ConfigTab>('theme')

// 开发者选项激活状态（通过高级设置中的安全密码验证）
const isDeveloperOptionsEnabled = ref(false)

// 加载状态
const isLoading = ref(false)
const error = ref<string | null>(null)
const successMessage = ref<string | null>(null)

// 使用Service Store
const serviceStore = useServiceStore()

// 从store获取服务端配置和状态
const isServiceRunning = computed(() => serviceStore.isRunning)
const isServiceInitialized = computed(() => serviceStore.isInitialized)

// 客户端配置
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

  isLoading.value = false
}

/**
 * 检查服务器连接
 * 手动触发连接检测，使用store的状态
 */
const checkServerConnection = async (): Promise<void> => {
  await serviceStore.refreshStatus()
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

/**
 * 处理错误消息
 * @param message - 错误消息
 */
const handleError = (message: string): void => {
  error.value = message
  successMessage.value = null
}

/**
 * 处理成功消息
 * @param message - 成功消息
 */
const handleSuccess = (message: string): void => {
  successMessage.value = message
  error.value = null
  setTimeout(() => successMessage.value = null, 3000)
}

/**
 * 处理开发者选项启用事件
 */
const handleDeveloperOptionsEnabled = (): void => {
  isDeveloperOptionsEnabled.value = true
  // 自动切换到开发者选项标签页
  activeTab.value = 'developer'
}

/**
 * 处理开发者选项锁定事件
 */
const handleDeveloperOptionsLocked = (): void => {
  isDeveloperOptionsEnabled.value = false
  // 如果当前在开发者选项标签页，切换回高级设置
  if (activeTab.value === 'developer') {
    activeTab.value = 'advanced'
  }
}

/**
 * 重置服务端配置
 */
const handleResetServerConfig = async (): Promise<void> => {
  try {
    const result: ConfigResponse = await resetAppConfig()
    if (result.success) {
      handleSuccess('服务端配置已重置为默认值')
      await loadConfigs()
    } else {
      handleError(result.errors?.[0] || '重置失败')
    }
  } catch (err) {
    console.error('重置服务端配置失败:', err)
    handleError('重置服务端配置失败: ' + String(err))
  }
}

onMounted(() => {
  loadConfigs()
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
        :class="{ active: activeTab === 'cors' }"
        @click="activeTab = 'cors'"
      >
        CORS 配置
      </button>
      <button
        class="tab-btn"
        :class="{ active: activeTab === 'advanced' }"
        @click="activeTab = 'advanced'"
      >
        高级设置
      </button>
      <button
        class="tab-btn"
        :class="{ 
          active: activeTab === 'developer',
          disabled: !isDeveloperOptionsEnabled 
        }"
        @click="isDeveloperOptionsEnabled && (activeTab = 'developer')"
        :disabled="!isDeveloperOptionsEnabled"
        :title="isDeveloperOptionsEnabled ? '开发者选项' : '请先在高级设置中验证安全密码'"
      >
        开发者选项
        <span v-if="!isDeveloperOptionsEnabled" class="tab-lock-icon">🔒</span>
      </button>
    </div>

    <!-- 主题配置 -->
    <ThemeSettings v-show="activeTab === 'theme'" />

    <!-- 服务端配置 -->
    <ServerSettings
      v-show="activeTab === 'server'"
      @error="handleError"
      @success="handleSuccess"
      @reset-server="handleResetServerConfig"
    />

    <!-- 客户端配置 -->
    <ClientSettings
      v-show="activeTab === 'client'"
      @error="handleError"
      @success="handleSuccess"
    />

    <!-- CORS 配置 -->
    <CORSSettings
      v-show="activeTab === 'cors'"
      @error="handleError"
      @success="handleSuccess"
    />

    <!-- 高级设置 -->
    <AdvancedSettings
      v-show="activeTab === 'advanced'"
      :is-developer-enabled="isDeveloperOptionsEnabled"
      @error="handleError"
      @success="handleSuccess"
      @developer-enabled="handleDeveloperOptionsEnabled"
      @developer-locked="handleDeveloperOptionsLocked"
    />

    <!-- 开发者选项 -->
    <DeveloperOptions
      v-show="activeTab === 'developer'"
      @error="handleError"
      @success="handleSuccess"
    />
  </div>
</template>

<style scoped>
.settings {
  max-width: 1000px;
}

/* 帮助文本 - Setting 页面特定的缩进 */
.help-text {
  margin-left: 26px;
}

/* 标签页锁定图标 */
.tab-lock-icon {
  margin-left: var(--spacing-xs);
  font-size: var(--font-size-sm);
}
</style>
