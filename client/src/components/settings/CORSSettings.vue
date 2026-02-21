<script setup lang="ts">
import { ref, computed } from 'vue'
import { useConfigSaver } from '../../composables/useConfigSaver'
import { useServiceStore } from '../../stores'

/**
 * CORS 配置组件
 *
 * 提供跨域资源共享配置功能
 */

// 图标路径
const loaderIcon = new URL('../../assets/icons/loader.svg', import.meta.url).href
const infoIcon = new URL('../../assets/icons/info.svg', import.meta.url).href

// 使用 Service Store
const serviceStore = useServiceStore()

// 从 store 获取代理状态
const isServerProxyEnabled = computed(() => serviceStore.isServerProxyEnabled)

/**
 * CORS 配置类型
 */
interface CORSConfig {
  allow_origins: string[]
  allow_credentials: boolean
  allow_methods: string[]
  allow_headers: string[]
  max_age: number
}

// CORS 配置
const corsConfig = ref<CORSConfig>({
  allow_origins: ['http://localhost:3000', 'http://127.0.0.1:3000'],
  allow_credentials: true,
  allow_methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allow_headers: ['Content-Type', 'Authorization', 'X-Requested-With'],
  max_age: 600
})

// CORS 编辑状态
const corsOriginsInput = ref('')
const corsHeadersInput = ref('')

// 定义事件
const emit = defineEmits<{
  (e: 'error', message: string): void
  (e: 'success', message: string): void
}>()

// 使用配置保存组合式函数
const { isSaving, save } = useConfigSaver<Partial<CORSConfig>>(
  async (config) => {
    const result = await serviceStore.updateCORSConfig(config)

    if (!result.success) {
      throw new Error(result.errors?.[0] || '保存失败')
    }
  },
  emit
)

/**
 * 保存 CORS 配置
 */
const saveCORSConfig = async (): Promise<void> => {
  // 解析输入框内容
  const origins = corsOriginsInput.value
    .split('\n')
    .map(s => s.trim())
    .filter(s => s.length > 0)

  const headers = corsHeadersInput.value
    .split('\n')
    .map(s => s.trim())
    .filter(s => s.length > 0)

  // 验证至少有一个 origin
  if (origins.length === 0) {
    emit('error', '至少需要一个允许的源地址')
    return
  }

  const config: Partial<CORSConfig> = {
    allow_origins: origins,
    allow_credentials: corsConfig.value.allow_credentials,
    allow_methods: corsConfig.value.allow_methods,
    allow_headers: headers,
    max_age: corsConfig.value.max_age
  }

  await save(config, 'CORS 配置保存成功（需要重启服务才能生效）')
}

/**
 * 重置 CORS 配置为默认值
 */
const resetCORSConfig = (): void => {
  corsConfig.value = {
    allow_origins: ['http://localhost:3000', 'http://127.0.0.1:3000'],
    allow_credentials: true,
    allow_methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    allow_headers: ['Content-Type', 'Authorization', 'X-Requested-With'],
    max_age: 600
  }
  corsOriginsInput.value = corsConfig.value.allow_origins.join('\n')
  corsHeadersInput.value = corsConfig.value.allow_headers.join('\n')
}

// 初始化
const init = () => {
  corsOriginsInput.value = corsConfig.value.allow_origins.join('\n')
  corsHeadersInput.value = corsConfig.value.allow_headers.join('\n')
}
init()
</script>

<template>
  <div class="config-section">
    <!-- 代理模式提示 -->
    <div v-if="isServerProxyEnabled" class="card warning-card">
      <p class="warning-text">
        <img :src="infoIcon" class="info-icon icon-warning" alt="warning" />
        代理模式已启用，CORS 配置由代理服务器管理。如需修改 CORS 配置，请先禁用代理模式。
      </p>
    </div>

    <!-- 重启提示 -->
    <div v-else class="card info-card">
      <p class="info-text">
        <img :src="infoIcon" class="info-icon icon-info" alt="info" />
        修改 CORS 配置后需要重启服务才能生效
      </p>
    </div>

    <div class="card" :class="{ disabled: isServerProxyEnabled }">
      <div class="card-header">
        <h2 class="card-title">CORS 跨域配置</h2>
        <span v-if="!isServerProxyEnabled" class="restart-badge">需重启</span>
      </div>

      <div class="form-group">
        <label class="form-label">允许的源地址 (Allow Origins)</label>
        <p class="help-text">每行一个地址，例如: https://your-domain.com</p>
        <textarea
          v-model="corsOriginsInput"
          class="input textarea"
          rows="4"
          :disabled="isServerProxyEnabled"
          placeholder="http://localhost:3000&#10;http://127.0.0.1:3000"
        ></textarea>
      </div>

      <div class="form-group">
        <label class="form-label">允许的 HTTP 方法</label>
        <div class="checkbox-group checkbox-group-horizontal">
          <label
            v-for="method in ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'PATCH']"
            :key="method"
            class="checkbox-label"
          >
            <input
              v-model="corsConfig.allow_methods"
              type="checkbox"
              :value="method"
              :disabled="isServerProxyEnabled"
            />
            {{ method }}
          </label>
        </div>
      </div>

      <div class="form-group">
        <label class="form-label">允许的请求头 (Allow Headers)</label>
        <p class="help-text">每行一个请求头名称</p>
        <textarea
          v-model="corsHeadersInput"
          class="input textarea"
          rows="3"
          :disabled="isServerProxyEnabled"
          placeholder="Content-Type&#10;Authorization&#10;X-Requested-With"
        ></textarea>
      </div>

      <div class="form-group">
        <label class="form-label">
          <input
            v-model="corsConfig.allow_credentials"
            type="checkbox"
            :disabled="isServerProxyEnabled"
          />
          允许携带凭证 (Allow Credentials)
        </label>
        <p class="help-text">允许跨域请求携带 Cookie 和认证信息</p>
      </div>

      <div class="form-group">
        <label class="form-label">预检请求缓存时间 (Max Age)</label>
        <input
          v-model.number="corsConfig.max_age"
          type="number"
          class="input"
          min="0"
          max="86400"
          :disabled="isServerProxyEnabled"
        />
        <p class="help-text">预检请求 (OPTIONS) 的缓存时间（秒），0-86400</p>
      </div>
    </div>

    <div class="form-actions">
      <button
        class="btn btn-primary"
        @click="saveCORSConfig"
        :disabled="isSaving || isServerProxyEnabled"
      >
        <img
          v-if="isSaving"
          :src="loaderIcon"
          class="btn-icon spinning"
          alt="loading"
        />
        <span v-else>保存 CORS 配置</span>
      </button>

      <button
        class="btn btn-secondary"
        @click="resetCORSConfig"
        :disabled="isSaving || isServerProxyEnabled"
      >
        重置为默认
      </button>
    </div>
  </div>
</template>
