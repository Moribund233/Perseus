<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import { useConfigSaver } from '../../composables/useConfigSaver'
import {
  updateAppConfig,
  validateAppConfig,
  type ConfigResponse,
  type RateLimitItem,
  type GunicornConfig
} from '../../services/api'
import { useServiceStore } from '../../stores'

/**
 * 服务端配置组件
 *
 * 提供服务端主机、端口、日志级别等配置（开发模式）
 * Gunicorn生产环境配置
 * 支持限流配置（分钟或小时二选一模式）
 */

// 图标路径
const loaderIcon = new URL('../../assets/icons/loader.svg', import.meta.url).href
const infoIcon = new URL('../../assets/icons/info.svg', import.meta.url).href

// 日志级别选项
const logLevels = ['debug', 'info', 'warning', 'error', 'critical']

// 限流模式选项
const rateLimitModes = [
  { value: 'default_limits', label: '默认限流', hint: '默认接口的访问限制' },
  { value: 'strict', label: '严格限流', hint: '登录等敏感接口的限制' },
  { value: 'standard', label: '标准限流', hint: '普通 API 接口的限制' },
  { value: 'generous', label: '宽松限流', hint: '静态资源等低敏感接口的限制' },
  { value: 'git_operations', label: 'Git 操作限流', hint: 'Git 相关操作的限制' },
  { value: 'download', label: '下载限流', hint: '文件下载接口的限制' }
] as const

type RateLimitMode = typeof rateLimitModes[number]['value']

// 使用 Service Store
const serviceStore = useServiceStore()

// 从 store 获取服务端配置
const serverConfigFromStore = computed(() => serviceStore.serverConfig)

// 当前选中的限流模式
const selectedRateLimitMode = ref<RateLimitMode>('default_limits')

// 当前模式的限流配置
const rateLimitMode = ref<'minute' | 'hour'>('minute')
const rateLimitValue = ref(200)



/**
 * 限流配置类型
 */
interface RateLimitConfig {
  default_limits: RateLimitItem
  strict: RateLimitItem
  standard: RateLimitItem
  generous: RateLimitItem
  git_operations: RateLimitItem
  download: RateLimitItem
}

/**
 * 服务端配置类型
 */
interface ServerConfig {
  server: {
    host: string
    port: number
    log_level: string
  }
  gunicorn: GunicornConfig
  rate_limit?: RateLimitConfig
}

// Gunicorn默认值
const defaultGunicornConfig: GunicornConfig = {
  workers: 4,
  worker_class: 'gunicorn_worker.LanGitUvicornWorker',
  threads: 1,
  worker_connections: 1000,
  backlog: 2048,
  timeout: 30,
  graceful_timeout: 30,
  keepalive: 2,
  max_requests: 10000,
  max_requests_jitter: 1000,
  preload_app: false,
  daemon: false,
  access_log: true,
  capture_output: true,
  enable_reuse_port: true
}

// 服务端配置（仅包含允许修改的字段）
const serverConfig = ref<ServerConfig>({
  server: {
    host: '0.0.0.0',
    port: 8000,
    log_level: 'info'
  },
  gunicorn: { ...defaultGunicornConfig },
  rate_limit: {
    default_limits: { mode: 'minute', value: 200 },
    strict: { mode: 'minute', value: 5 },
    standard: { mode: 'minute', value: 30 },
    generous: { mode: 'hour', value: 2000 },
    git_operations: { mode: 'minute', value: 10 },
    download: { mode: 'minute', value: 20 }
  }
})

// 当前激活的配置标签页
const activeTab = ref<'server' | 'gunicorn' | 'ratelimit'>('server')

/**
 * 获取指定模式的限流配置
 */
const getRateLimitConfig = (mode: RateLimitMode): RateLimitItem => {
  const defaults: Record<RateLimitMode, RateLimitItem> = {
    default_limits: { mode: 'minute', value: 200 },
    strict: { mode: 'minute', value: 5 },
    standard: { mode: 'minute', value: 30 },
    generous: { mode: 'hour', value: 2000 },
    git_operations: { mode: 'minute', value: 10 },
    download: { mode: 'minute', value: 20 }
  }
  return serverConfig.value.rate_limit?.[mode] ?? defaults[mode]
}

/**
 * 更新指定模式的限流配置
 */
const updateRateLimitConfig = (mode: RateLimitMode, config: RateLimitItem) => {
  if (serverConfig.value.rate_limit) {
    serverConfig.value.rate_limit[mode] = { ...config }
  }
}

/**
 * 当切换模式时，加载对应模式的限流配置
 */
const loadRateLimitForMode = (mode: RateLimitMode) => {
  const config = getRateLimitConfig(mode)
  rateLimitMode.value = config.mode
  rateLimitValue.value = config.value
}

/**
 * 当修改限流配置时，更新到配置
 */
const handleRateLimitChange = () => {
  updateRateLimitConfig(selectedRateLimitMode.value, {
    mode: rateLimitMode.value,
    value: rateLimitValue.value
  })
}

// 同步服务端配置
const syncConfig = (newConfig: typeof serverConfigFromStore.value) => {
  if (!newConfig) return
  if (newConfig.server) {
    serverConfig.value.server = { ...serverConfig.value.server, ...newConfig.server }
  }
  if (newConfig.gunicorn) {
    serverConfig.value.gunicorn = { ...serverConfig.value.gunicorn, ...newConfig.gunicorn }
  }
  if (newConfig.rate_limit) {
    serverConfig.value.rate_limit = { ...serverConfig.value.rate_limit, ...newConfig.rate_limit }
  }
}

// 监听模式切换，自动加载对应模式的限流配置
watch(selectedRateLimitMode, (newMode) => {
  loadRateLimitForMode(newMode)
})

// 监听限流模式或值的变化，自动更新配置
watch([rateLimitMode, rateLimitValue], () => {
  handleRateLimitChange()
})

// 监听配置加载完成，初始化限流配置（使用 nextTick 避免 DOM 更新冲突）
watch(() => serverConfigFromStore.value, async (newConfig) => {
  if (newConfig) {
    await nextTick()
    syncConfig(newConfig)
    if (newConfig.rate_limit) {
      loadRateLimitForMode(selectedRateLimitMode.value)
    }
  }
}, { immediate: true })

/**
 * 当前限流模式的提示文本
 */
const currentRateLimitHint = computed(() => {
  const mode = rateLimitModes.find(m => m.value === selectedRateLimitMode.value)
  return mode?.hint || ''
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
 * 准备要保存的配置数据（过滤掉不允许修改的字段）
 */
const prepareConfigForSave = (config: ServerConfig): ServerConfig => {
  // 只提取允许修改的字段
  const prepared: ServerConfig = {
    server: {
      host: config.server.host,
      port: config.server.port,
      log_level: config.server.log_level
    },
    gunicorn: {
      workers: config.gunicorn.workers,
      worker_class: config.gunicorn.worker_class,
      threads: config.gunicorn.threads,
      worker_connections: config.gunicorn.worker_connections,
      backlog: config.gunicorn.backlog,
      timeout: config.gunicorn.timeout,
      graceful_timeout: config.gunicorn.graceful_timeout,
      keepalive: config.gunicorn.keepalive,
      max_requests: config.gunicorn.max_requests,
      max_requests_jitter: config.gunicorn.max_requests_jitter,
      preload_app: config.gunicorn.preload_app,
      daemon: config.gunicorn.daemon,
      access_log: config.gunicorn.access_log,
      capture_output: config.gunicorn.capture_output,
      enable_reuse_port: config.gunicorn.enable_reuse_port
    },
    rate_limit: config.rate_limit ? { ...config.rate_limit } : undefined
  }

  return prepared
}

/**
 * 保存服务端配置
 */
const saveServerConfig = async (): Promise<void> => {
  const configToSave = prepareConfigForSave(serverConfig.value)
  await save(configToSave, '服务端配置保存成功')
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
        修改服务器设置或Gunicorn配置后需要重启服务才能生效
      </p>
    </div>

    <!-- 标签页切换 -->
    <div class="tabs">
      <button
        class="tab-btn"
        :class="{ active: activeTab === 'server' }"
        @click="activeTab = 'server'"
      >
        开发服务器
      </button>
      <button
        class="tab-btn"
        :class="{ active: activeTab === 'gunicorn' }"
        @click="activeTab = 'gunicorn'"
      >
        Gunicorn生产环境
      </button>
      <button
        class="tab-btn"
        :class="{ active: activeTab === 'ratelimit' }"
        @click="activeTab = 'ratelimit'"
      >
        限流配置
      </button>
    </div>

    <!-- 开发服务器配置 -->
    <div v-show="activeTab === 'server'" class="card">
      <div class="card-header">
        <h2 class="card-title">开发服务器设置</h2>
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
          <label class="form-label">日志级别</label>
          <select v-model="serverConfig.server.log_level" class="input">
            <option v-for="level in logLevels" :key="level" :value="level">
              {{ level }}
            </option>
          </select>
        </div>
      </div>
    </div>

    <!-- Gunicorn生产环境配置 -->
    <div v-show="activeTab === 'gunicorn'" class="card">
      <div class="card-header">
        <h2 class="card-title">Gunicorn生产环境配置</h2>
        <span class="restart-badge">需重启</span>
      </div>

      <div class="form-grid">
        <!-- Worker配置 -->
        <div class="form-group">
          <label class="form-label">
            Worker进程数
            <span class="hint">建议: 2-4 x CPU核心数</span>
          </label>
          <input
            v-model.number="serverConfig.gunicorn.workers"
            type="number"
            class="input"
            min="1"
            max="32"
          />
        </div>

        <div class="form-group">
          <label class="form-label">Worker类</label>
          <input
            v-model="serverConfig.gunicorn.worker_class"
            type="text"
            class="input"
            readonly
          />
        </div>

        <div class="form-group">
          <label class="form-label">线程数</label>
          <input
            v-model.number="serverConfig.gunicorn.threads"
            type="number"
            class="input"
            min="1"
          />
        </div>

        <!-- 连接配置 -->
        <div class="form-group">
          <label class="form-label">最大并发连接数</label>
          <input
            v-model.number="serverConfig.gunicorn.worker_connections"
            type="number"
            class="input"
            min="100"
          />
        </div>

        <div class="form-group">
          <label class="form-label">连接队列长度</label>
          <input
            v-model.number="serverConfig.gunicorn.backlog"
            type="number"
            class="input"
            min="128"
          />
        </div>

        <!-- 超时配置 -->
        <div class="form-group">
          <label class="form-label">
            Worker超时时间
            <span class="hint">秒</span>
          </label>
          <input
            v-model.number="serverConfig.gunicorn.timeout"
            type="number"
            class="input"
            min="10"
            max="300"
          />
        </div>

        <div class="form-group">
          <label class="form-label">
            优雅关闭超时
            <span class="hint">秒</span>
          </label>
          <input
            v-model.number="serverConfig.gunicorn.graceful_timeout"
            type="number"
            class="input"
            min="5"
            max="120"
          />
        </div>

        <div class="form-group">
          <label class="form-label">
            Keep-alive超时
            <span class="hint">秒</span>
          </label>
          <input
            v-model.number="serverConfig.gunicorn.keepalive"
            type="number"
            class="input"
            min="1"
            max="60"
          />
        </div>

        <!-- 请求限制 -->
        <div class="form-group">
          <label class="form-label">
            最大请求数
            <span class="hint">Worker重启前处理的请求数</span>
          </label>
          <input
            v-model.number="serverConfig.gunicorn.max_requests"
            type="number"
            class="input"
            min="1000"
          />
        </div>

        <div class="form-group">
          <label class="form-label">
            请求数随机偏移
            <span class="hint">防止所有Worker同时重启</span>
          </label>
          <input
            v-model.number="serverConfig.gunicorn.max_requests_jitter"
            type="number"
            class="input"
            min="0"
          />
        </div>
      </div>

      <!-- 开关配置 -->
      <div class="switch-grid">
        <label class="switch-item">
          <input
            v-model="serverConfig.gunicorn.preload_app"
            type="checkbox"
          />
          <span class="switch-label">预加载应用</span>
          <span class="switch-hint">节省内存但影响热重载</span>
        </label>

        <label class="switch-item">
          <input
            v-model="serverConfig.gunicorn.daemon"
            type="checkbox"
          />
          <span class="switch-label">守护进程模式</span>
          <span class="switch-hint">后台运行</span>
        </label>

        <label class="switch-item">
          <input
            v-model="serverConfig.gunicorn.access_log"
            type="checkbox"
          />
          <span class="switch-label">访问日志</span>
          <span class="switch-hint">记录HTTP请求</span>
        </label>

        <label class="switch-item">
          <input
            v-model="serverConfig.gunicorn.capture_output"
            type="checkbox"
          />
          <span class="switch-label">捕获输出</span>
          <span class="switch-hint">捕获stdout/stderr</span>
        </label>

        <label class="switch-item">
          <input
            v-model="serverConfig.gunicorn.enable_reuse_port"
            type="checkbox"
          />
          <span class="switch-label">SO_REUSEPORT</span>
          <span class="switch-hint">Linux多核负载均衡优化</span>
        </label>
      </div>
    </div>

    <!-- 限流配置 -->
    <div v-show="activeTab === 'ratelimit'" class="card">
      <div class="card-header">
        <h2 class="card-title">限流配置</h2>
        <span class="restart-badge">需重启</span>
      </div>

      <div class="rate-limit-container">
        <!-- 左侧：限流模式选择和时间单位 -->
        <div class="rate-limit-left">
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

          <div class="form-group">
            <label class="form-label">时间单位</label>
            <div class="radio-group">
              <label class="radio-label">
                <input
                  v-model="rateLimitMode"
                  type="radio"
                  value="minute"
                />
                <span>每分钟</span>
              </label>
              <label class="radio-label">
                <input
                  v-model="rateLimitMode"
                  type="radio"
                  value="hour"
                />
                <span>每小时</span>
              </label>
            </div>
          </div>
        </div>

        <!-- 右侧：限流值输入 -->
        <div class="rate-limit-right">
          <div class="form-group">
            <label class="form-label">
              请求数限制
              <span class="limit-unit">({{ rateLimitMode === 'minute' ? '每分钟' : '每小时' }})</span>
            </label>
            <input
              v-model.number="rateLimitValue"
              type="number"
              class="input"
              min="1"
            />
            <span class="form-hint">
              每个 {{ rateLimitMode === 'minute' ? '分钟' : '小时' }} 内允许的最大请求数
            </span>
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
        <span v-else>保存配置</span>
      </button>

      <button class="btn btn-secondary" @click="handleResetServerConfig" :disabled="isSaving">
        重置为默认
      </button>
    </div>
  </div>
</template>

<style scoped>
/* 标签页样式 */
.tabs {
  display: flex;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-lg);
  border-bottom: 1px solid var(--border-color);
  padding-bottom: var(--spacing-sm);
}

.tab-btn {
  padding: var(--spacing-sm) var(--spacing-md);
  background: transparent;
  border: none;
  border-radius: var(--border-radius-sm);
  color: var(--text-secondary);
  font-size: var(--font-size-sm);
  cursor: pointer;
  transition: all 0.2s ease;
}

.tab-btn:hover {
  color: var(--text-primary);
  background: var(--bg-hover);
}

.tab-btn.active {
  color: var(--primary-color);
  background: var(--primary-light);
  font-weight: 500;
}

/* 限流配置容器 */
.rate-limit-container {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--spacing-lg);
  align-items: start;
}

/* 左侧区域 */
.rate-limit-left {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

/* 右侧区域 */
.rate-limit-right {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

/* 单选按钮组 */
.radio-group {
  display: flex;
  gap: var(--spacing-md);
  margin-top: var(--spacing-xs);
}

.radio-label {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  cursor: pointer;
  font-size: var(--font-size-sm);
  color: var(--text-primary);
}

.radio-label input[type="radio"] {
  width: 16px;
  height: 16px;
  cursor: pointer;
}

/* 限流单位标签 */
.limit-unit {
  font-size: var(--font-size-xs);
  color: var(--text-secondary);
  font-weight: normal;
  margin-left: var(--spacing-xs);
}

/* 表单提示 */
.form-hint {
  display: block;
  margin-top: var(--spacing-xs);
  font-size: var(--font-size-xs);
  color: var(--text-secondary);
}

/* 标签提示 */
.hint {
  font-size: var(--font-size-xs);
  color: var(--text-secondary);
  font-weight: normal;
  margin-left: var(--spacing-xs);
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

/* 开关网格 */
.switch-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: var(--spacing-md);
  margin-top: var(--spacing-lg);
  padding-top: var(--spacing-lg);
  border-top: 1px solid var(--border-color);
}

.switch-item {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
  cursor: pointer;
}

.switch-item input[type="checkbox"] {
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.switch-label {
  font-size: var(--font-size-sm);
  font-weight: 500;
  color: var(--text-primary);
}

.switch-hint {
  font-size: var(--font-size-xs);
  color: var(--text-secondary);
}

@media (max-width: 768px) {
  .tabs {
    flex-wrap: wrap;
  }

  .rate-limit-container {
    grid-template-columns: 1fr;
  }

  .radio-group {
    flex-direction: column;
    gap: var(--spacing-sm);
  }

  .switch-grid {
    grid-template-columns: 1fr;
  }
}
</style>
