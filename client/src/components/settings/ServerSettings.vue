<script setup lang="ts">
import { ref, computed } from 'vue'
import {
  updateAppConfig,
  validateAppConfig,
  type ConfigResponse
} from '../../services/api'
import { useServiceStore } from '../../stores'

/**
 * 服务端配置组件
 *
 * 提供服务端主机、端口、工作进程数、日志级别等配置
 */

// 图标路径
const loaderIcon = new URL('../../assets/icons/loader.svg', import.meta.url).href
const infoIcon = new URL('../../assets/icons/info.svg', import.meta.url).href

// 日志级别选项
const logLevels = ['debug', 'info', 'warning', 'error', 'critical']

// 使用 Service Store
const serviceStore = useServiceStore()

// 从 store 获取服务端配置
const serverConfigFromStore = computed(() => serviceStore.serverConfig)

// 加载和保存状态
const isSaving = ref(false)

/**
 * 服务端配置类型
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

// 定义事件
const emit = defineEmits<{
  (e: 'error', message: string): void
  (e: 'success', message: string): void
  (e: 'reset-server'): void
}>()

/**
 * 从 store 同步服务端配置
 */
const syncServerConfigFromStore = (): void => {
  if (serverConfigFromStore.value?.server) {
    serverConfig.value.server = { ...serverConfig.value.server, ...serverConfigFromStore.value.server }
  }
}

/**
 * 保存服务端配置
 */
const saveServerConfig = async (): Promise<void> => {
  isSaving.value = true
  emit('error', '')
  emit('success', '')

  try {
    // 先验证配置
    const isValid = await validateAppConfig(serverConfig.value)
    if (!isValid) {
      emit('error', '配置验证失败')
      return
    }

    const result: ConfigResponse = await updateAppConfig(serverConfig.value)

    if (result.success) {
      emit('success', '服务端配置保存成功')
      // 保存成功后刷新 store 中的配置
      await serviceStore.refreshServerConfig()
    } else {
      emit('error', result.errors?.[0] || '保存失败')
    }
  } catch (err) {
    console.error('保存服务端配置失败:', err)
    emit('error', '保存服务端配置失败: ' + String(err))
  } finally {
    isSaving.value = false
  }
}

/**
 * 重置服务端配置
 */
const handleResetServerConfig = async (): Promise<void> => {
  emit('reset-server')
}

// 初始化时同步配置
syncServerConfigFromStore()
</script>

<template>
  <div class="config-section">
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
</template>
