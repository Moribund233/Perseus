<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import { useConfigSaver } from '../../composables/useConfigSaver'
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

/**
 * 限流模式选项
 */
const rateLimitModes = [
  { value: 'default_limits', label: '默认限流', hint: '默认接口的访问限制' },
  { value: 'strict', label: '严格限流', hint: '登录等敏感接口的限制' },
  { value: 'standard', label: '标准限流', hint: '普通 API 接口的限制' },
  { value: 'generous', label: '宽松限流', hint: '静态资源等低敏感接口的限制' },
  { value: 'git_operations', label: 'Git 操作限流', hint: 'Git 相关操作的限制' },
  { value: 'download', label: '下载限流', hint: '文件下载接口的限制' }
] as const

type RateLimitMode = typeof rateLimitModes[number]['value']

// 当前选中的限流模式
const selectedRateLimitMode = ref<RateLimitMode>('default_limits')

// 当前模式的限流值
const rateLimitMinute = ref(1000)
const rateLimitHour = ref(10000)

/**
 * 解析限流配置字符串，提取数值
 */
const parseRateLimit = (limits: string[] | undefined, defaultMinute: number, defaultHour: number): { minute: number, hour: number } => {
  if (!limits || limits.length < 2) {
    return { minute: defaultMinute, hour: defaultHour }
  }
  const minuteMatch = limits[0].match(/(\d+)\s*per\s*minute/)
  const hourMatch = limits[1].match(/(\d+)\s*per\s*hour/)
  return {
    minute: minuteMatch ? parseInt(minuteMatch[1]) : defaultMinute,
    hour: hourMatch ? parseInt(hourMatch[1]) : defaultHour
  }
}

/**
 * 获取指定模式的限流值
 */
const getRateLimitValues = (mode: RateLimitMode): { minute: number, hour: number } => {
  const defaults: Record<RateLimitMode, { minute: number, hour: number }> = {
    default_limits: { minute: 1000, hour: 10000 },
    strict: { minute: 50, hour: 500 },
    standard: { minute: 200, hour: 2000 },
    generous: { minute: 500, hour: 5000 },
    git_operations: { minute: 100, hour: 1000 },
    download: { minute: 100, hour: 1000 }
  }
  const limits = serverConfig.value.rate_limit?.[mode]
  return parseRateLimit(limits, defaults[mode].minute, defaults[mode].hour)
}

/**
 * 更新指定模式的限流值到配置
 */
const updateRateLimitConfig = (mode: RateLimitMode, minute: number, hour: number) => {
  if (serverConfig.value.rate_limit) {
    serverConfig.value.rate_limit[mode] = [`${minute} per minute`, `${hour} per hour`]
  }
}

/**
 * 当切换模式时，加载对应模式的限流值
 */
const loadRateLimitForMode = (mode: RateLimitMode) => {
  const values = getRateLimitValues(mode)
  rateLimitMinute.value = values.minute
  rateLimitHour.value = values.hour
}

/**
 * 当修改限流值时，更新到配置
 */
const handleRateLimitChange = () => {
  updateRateLimitConfig(selectedRateLimitMode.value, rateLimitMinute.value, rateLimitHour.value)
}

// 同步服务端配置
const syncConfig = (newConfig: typeof serverConfigFromStore.value) => {
  if (!newConfig) return
  if (newConfig.server) {
    serverConfig.value.server = { ...serverConfig.value.server, ...newConfig.server }
  }
  if (newConfig.rate_limit) {
    serverConfig.value.rate_limit = { ...serverConfig.value.rate_limit, ...newConfig.rate_limit }
  }
}

// 监听模式切换，自动加载对应模式的限流值
watch(selectedRateLimitMode, (newMode) => {
  loadRateLimitForMode(newMode)
})

// 监听配置加载完成，初始化限流值（使用 nextTick 避免 DOM 更新冲突）
watch(() => serverConfigFromStore.value, async (newConfig) => {
  if (newConfig) {
    await nextTick()
    syncConfig(newConfig)
    if (newConfig.rate_limit) {
      loadRateLimitForMode(selectedRateLimitMode.value)
    }
  }
})

/**
 * 当前限流模式的提示文本
 */
const currentRateLimitHint = computed(() => {
  const mode = rateLimitModes.find(m => m.value === selectedRateLimitMode.value)
  return mode?.hint || ''
})

/**
 * 限流配置类型
 */
interface RateLimitConfig {
  default_limits: string[]
  strict: string[]
  standard: string[]
  generous: string[]
  git_operations: string[]
  download: string[]
}

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
  rate_limit?: RateLimitConfig
}

// 服务端配置（仅包含允许修改的字段）
const serverConfig = ref<ServerConfig>({
  server: {
    host: '0.0.0.0',
    port: 8000,
    workers: 1,
    log_level: 'info'
  },
  rate_limit: {
    default_limits: ['1000 per minute', '10000 per hour'],
    strict: ['50 per minute', '500 per hour'],
    standard: ['200 per minute', '2000 per hour'],
    generous: ['500 per minute', '5000 per hour'],
    git_operations: ['100 per minute', '1000 per hour'],
    download: ['100 per minute', '1000 per hour']
  }
})

// 定义事件
const emit = defineEmits<{
  (e: 'error', message: string): void
  (e: 'success', message: string): void
  (e: 'reset-server'): void
}>()

// 使用配置保存组合式函数
const { isSaving, save } = useConfigSaver<ServerConfig>(
  async (config) => {
    // 先验证配置
    const isValid = await validateAppConfig(config)
    if (!isValid) {
      throw new Error('配置验证失败')
    }

    const result: ConfigResponse = await updateAppConfig(config)

    if (!result.success) {
      throw new Error(result.errors?.[0] || '保存失败')
    }

    // 保存成功后刷新 store 中的配置
    await serviceStore.refreshServerConfig()
  },
  emit
)

/**
 * 保存服务端配置
 */
const saveServerConfig = async (): Promise<void> => {
  await save(serverConfig.value, '服务端配置保存成功')
}

/**
 * 重置服务端配置
 */
const handleResetServerConfig = async (): Promise<void> => {
  emit('reset-server')
}


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

    <!-- 限流配置 -->
    <div class="card">
      <div class="card-header">
        <h2 class="card-title">限流配置</h2>
        <span class="restart-badge">需重启</span>
      </div>

      <div class="rate-limit-container">
        <!-- 左侧：限流值输入 -->
        <div class="rate-limit-inputs">
          <div class="form-group">
            <label class="form-label">每分钟请求数</label>
            <input
              v-model.number="rateLimitMinute"
              type="number"
              class="input"
              min="1"
              @change="handleRateLimitChange"
            />
          </div>
          <div class="form-group">
            <label class="form-label">每小时请求数</label>
            <input
              v-model.number="rateLimitHour"
              type="number"
              class="input"
              min="1"
              @change="handleRateLimitChange"
            />
          </div>
        </div>

        <!-- 右侧：限流模式选择 -->
        <div class="rate-limit-selector">
          <div class="form-group">
            <label class="form-label">限流模式</label>
            <select v-model="selectedRateLimitMode" class="input">
              <option
                v-for="mode in rateLimitModes"
                :key="mode.value"
                :value="mode.value"
              >
                {{ mode.label }}
              </option>
            </select>
            <span class="form-hint">{{ currentRateLimitHint }}</span>
          </div>
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

<style scoped>
/* 限流配置容器 */
.rate-limit-container {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--spacing-lg);
  align-items: start;
}

/* 限流输入区域 */
.rate-limit-inputs {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

/* 限流选择区域 */
.rate-limit-selector {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

/* 表单提示 */
.form-hint {
  display: block;
  margin-top: var(--spacing-xs);
  font-size: var(--font-size-xs);
  color: var(--text-secondary);
}

/* 重启标签 */
.restart-badge {
  display: inline-block;
  padding: 2px 8px;
  background: var(--warning-color);
  color: white;
  border-radius: var(--border-radius-sm);
  font-size: var(--font-size-xs);
  font-weight: 500;
}

/* 卡片头部 */
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-md);
}

/* 卡片标题 */
.card-title {
  margin: 0;
  font-size: var(--font-size-lg);
  font-weight: 600;
}

@media (max-width: 768px) {
  .rate-limit-container {
    grid-template-columns: 1fr;
  }
}
</style>
