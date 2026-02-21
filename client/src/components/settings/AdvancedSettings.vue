<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useClientConfig } from '../../composables/useClientConfig'
import {
  setSecurityPassword,
  verifySecurityPassword,
  hasSecurityPassword
} from '../../services/api'

/**
 * 高级设置组件
 *
 * 提供客户端高级设置和开发者选项入口
 * 开发者选项需要通过安全密码验证后才能访问
 */

// 图标路径
const loaderIcon = new URL('../../assets/icons/loader.svg', import.meta.url).href

// Props
const props = defineProps<{
  isDeveloperEnabled: boolean
}>()

// 定义事件
const emit = defineEmits<{
  (e: 'error', message: string): void
  (e: 'success', message: string): void
  (e: 'developer-enabled'): void
  (e: 'developer-locked'): void
}>()

// 使用客户端配置组合式函数（禁用自动加载，手动控制）
const {
  clientConfig,
  isSaving,
  loadConfig,
  saveConfig: saveClientConfigHandler
} = useClientConfig(emit, {
  autoLoad: false,
  successMessage: '高级设置保存成功'
})

// 安全密码验证状态
const securityAuth = ref({
  hasPassword: false,
  password: '',
  passwordError: '',
  isLoading: false
})

/**
 * 监听开发者选项状态变化
 */
watch(() => props.isDeveloperEnabled, (newValue) => {
  if (!newValue) {
    // 当开发者选项被锁定时，重置本地状态
    securityAuth.value.password = ''
    securityAuth.value.passwordError = ''
  }
})

/**
 * 初始化
 */
onMounted(async () => {
  await loadConfig()
  await checkSecurityPasswordStatus()
})

/**
 * 检查安全密码状态
 */
const checkSecurityPasswordStatus = async (): Promise<void> => {
  try {
    securityAuth.value.hasPassword = await hasSecurityPassword()
  } catch (err) {
    console.error('检查安全密码状态失败:', err)
  }
}

/**
 * 验证安全密码
 */
const verifyPassword = async (): Promise<void> => {
  if (!securityAuth.value.password) {
    securityAuth.value.passwordError = '请输入安全密码'
    return
  }

  securityAuth.value.isLoading = true
  securityAuth.value.passwordError = ''

  try {
    const isValid = await verifySecurityPassword(securityAuth.value.password)
    if (isValid) {
      securityAuth.value.password = ''
      emit('success', '验证成功，开发者选项已启用')
      // 通知父组件启用开发者选项
      emit('developer-enabled')
    } else {
      securityAuth.value.passwordError = '密码错误'
    }
  } catch (err) {
    console.error('验证密码失败:', err)
    securityAuth.value.passwordError = '验证失败: ' + String(err)
  } finally {
    securityAuth.value.isLoading = false
  }
}

/**
 * 设置安全密码
 */
const handleSetSecurityPassword = async (): Promise<void> => {
  if (!securityAuth.value.password || securityAuth.value.password.length < 6) {
    securityAuth.value.passwordError = '密码长度至少为6位'
    return
  }

  securityAuth.value.isLoading = true
  try {
    await setSecurityPassword(securityAuth.value.password)
    securityAuth.value.hasPassword = true
    securityAuth.value.password = ''
    emit('success', '安全密码设置成功，开发者选项已启用')
    // 通知父组件启用开发者选项
    emit('developer-enabled')
  } catch (err) {
    console.error('设置密码失败:', err)
    securityAuth.value.passwordError = '设置密码失败: ' + String(err)
  } finally {
    securityAuth.value.isLoading = false
  }
}

/**
 * 锁定开发者选项
 */
const lockDeveloperOptions = (): void => {
  securityAuth.value.password = ''
  securityAuth.value.passwordError = ''
  emit('success', '开发者选项已锁定')
  // 通知父组件锁定开发者选项
  emit('developer-locked')
}
</script>

<template>
  <div class="config-section">
    <!-- 客户端高级设置 -->
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

    <!-- 开发者选项控制区域 -->
    <div class="card security-auth-card">
      <div class="card-header">
        <h2 class="card-title">开发者选项</h2>
      </div>

      <div v-if="!isDeveloperEnabled">
        <p class="security-description">
          开发者选项包含调试设置、压力测试、安全令牌管理和数据库配置等高级功能。
          <span v-if="!securityAuth.hasPassword">首次使用请设置安全密码。</span>
        </p>

        <div class="form-group">
          <label class="form-label">安全密码</label>
          <input
            v-model="securityAuth.password"
            type="password"
            class="input"
            :class="{ 'input-error': securityAuth.passwordError }"
            :placeholder="securityAuth.hasPassword ? '请输入安全密码' : '请设置安全密码（至少6位）'"
            @keyup.enter="securityAuth.hasPassword ? verifyPassword() : handleSetSecurityPassword()"
            :disabled="securityAuth.isLoading"
          />
          <span v-if="securityAuth.passwordError" class="input-error-text">{{ securityAuth.passwordError }}</span>
        </div>

        <div class="form-actions-inline">
          <button
            v-if="securityAuth.hasPassword"
            class="btn btn-primary"
            @click="verifyPassword"
            :disabled="securityAuth.isLoading"
          >
            <img
              v-if="securityAuth.isLoading"
              :src="loaderIcon"
              class="btn-icon spinning"
              alt="loading"
            />
            <span v-else>验证并启用开发者选项</span>
          </button>
          <button
            v-else
            class="btn btn-primary"
            @click="handleSetSecurityPassword"
            :disabled="securityAuth.isLoading"
          >
            <img
              v-if="securityAuth.isLoading"
              :src="loaderIcon"
              class="btn-icon spinning"
              alt="loading"
            />
            <span v-else>设置密码并启用</span>
          </button>
        </div>
      </div>

      <div v-else class="developer-enabled-state">
        <div class="success-message">
          <span class="success-icon">✓</span>
          <span>开发者选项已启用，您可以切换到"开发者选项"标签页进行配置</span>
        </div>
        <button class="btn btn-secondary" @click="lockDeveloperOptions">
          锁定开发者选项
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 安全密码验证卡片 */
.security-auth-card {
  border: 1px solid var(--border-color);
}

.security-description {
  color: var(--text-secondary);
  margin-bottom: var(--spacing-md);
  line-height: 1.5;
}

.security-description span {
  color: var(--warning-color);
}

/* 输入框错误样式 */
.input-error {
  border-color: var(--error-color);
}

.input-error:focus {
  border-color: var(--error-color);
  box-shadow: 0 0 0 2px rgba(239, 68, 68, 0.2);
}

.input-error-text {
  display: block;
  font-size: var(--font-size-xs);
  color: var(--error-color);
  margin-top: var(--spacing-xs);
}

/* 开发者已启用状态 */
.developer-enabled-state {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.success-message {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-md);
  background-color: rgba(34, 197, 94, 0.1);
  border: 1px solid var(--success-color);
  border-radius: var(--border-radius-md);
  color: var(--success-color);
}

.success-icon {
  font-size: var(--font-size-lg);
  font-weight: bold;
}

/* 表单操作按钮 */
.form-actions-inline {
  display: flex;
  gap: var(--spacing-sm);
  margin-top: var(--spacing-md);
}

/* 按钮图标 */
.btn-icon {
  width: 16px;
  height: 16px;
}

.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>
