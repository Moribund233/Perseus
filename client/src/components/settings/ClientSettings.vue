<script setup lang="ts">
import { ref } from 'vue'
import {
  getClientConfig,
  saveClientConfig,
  updateServerUrl,
  type ClientConfig
} from '../../services/api'

/**
 * 客户端配置组件
 *
 * 提供客户端连接设置、通知设置、日志设置等配置
 */

// 图标路径
const loaderIcon = new URL('../../assets/icons/loader.svg', import.meta.url).href

// 加载和保存状态
const isSaving = ref(false)
const isLoading = ref(false)

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

// 定义事件
const emit = defineEmits<{
  (e: 'error', message: string): void
  (e: 'success', message: string): void
}>()

/**
 * 加载客户端配置
 */
const loadClientConfig = async (): Promise<void> => {
  isLoading.value = true
  try {
    const config = await getClientConfig()
    clientConfig.value = { ...clientConfig.value, ...config }
  } catch (err) {
    console.error('加载客户端配置失败:', err)
    emit('error', '加载客户端配置失败: ' + String(err))
  } finally {
    isLoading.value = false
  }
}

/**
 * 保存客户端配置
 */
const saveClientConfigHandler = async (): Promise<void> => {
  isSaving.value = true
  emit('error', '')
  emit('success', '')

  try {
    await saveClientConfig(clientConfig.value)
    emit('success', '客户端配置保存成功')
  } catch (err) {
    console.error('保存客户端配置失败:', err)
    emit('error', '保存客户端配置失败: ' + String(err))
  } finally {
    isSaving.value = false
  }
}

/**
 * 更新服务器地址
 */
const handleUpdateServerUrl = async (): Promise<void> => {
  try {
    await updateServerUrl(clientConfig.value.server.url)
    emit('success', '服务器地址已更新')
  } catch (err) {
    emit('error', '更新服务器地址失败: ' + String(err))
  }
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
    emit('error', '选择文件失败: ' + String(err))
  }
}

// 初始化加载配置
loadClientConfig()
</script>

<template>
  <div class="config-section">
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

      <div class="form-group checkbox-group checkbox-group-horizontal">
        <label class="checkbox-label">
          <input v-model="clientConfig.server.auto_connect" type="checkbox" />
          <span>自动连接</span>
        </label>
        <label class="checkbox-label">
          <input v-model="clientConfig.server.auto_start" type="checkbox" />
          <span>自动启动服务端</span>
        </label>
      </div>
      <p class="help-text">启动客户端时自动启动服务端（仅桌面端有效）</p>

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

      <div class="form-group checkbox-group checkbox-group-horizontal">
        <label class="checkbox-label">
          <input v-model="clientConfig.notification.enabled" type="checkbox" />
          <span>启用通知</span>
        </label>
        <label class="checkbox-label">
          <input v-model="clientConfig.notification.on_error" type="checkbox" :disabled="!clientConfig.notification.enabled" />
          <span>错误时通知</span>
        </label>
        <label class="checkbox-label">
          <input v-model="clientConfig.notification.on_warning" type="checkbox" :disabled="!clientConfig.notification.enabled" />
          <span>警告时通知</span>
        </label>
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

    <div class="form-actions">
      <button class="btn btn-primary" @click="saveClientConfigHandler" :disabled="isSaving || isLoading">
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
</template>
