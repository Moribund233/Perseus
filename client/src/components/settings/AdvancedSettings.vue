<script setup lang="ts">
import { ref } from 'vue'
import {
  getClientConfig,
  saveClientConfig,
  resetClientConfig,
  setSecurityPassword,
  verifySecurityPassword,
  hasSecurityPassword,
  getDebugMode,
  updateDebugMode,
  resetAllTokens,
  isElevated,
  getJwtSecretKey,
  getLocalToken,
  type ClientConfig
} from '../../services/api'
import { useRouter } from 'vue-router'

/**
 * 高级设置组件
 *
 * 提供客户端高级设置和危险区域操作功能
 */

// 图标路径
const loaderIcon = new URL('../../assets/icons/loader.svg', import.meta.url).href

// 加载和保存状态
const isSaving = ref(false)

// 路由
const router = useRouter()

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

// 危险操作验证对话框状态
const dangerDialog = ref<{
  show: boolean
  title: string
  message: string
  confirmText: string
  expectedInput: string
  action: 'resetClient' | 'resetTokens' | null
}>({
  show: false,
  title: '',
  message: '',
  confirmText: '',
  expectedInput: '',
  action: null
})

const dangerInput = ref('')

// 定义事件
const emit = defineEmits<{
  (e: 'error', message: string): void
  (e: 'success', message: string): void
}>()

/**
 * 加载客户端配置
 */
const loadClientConfig = async (): Promise<void> => {
  try {
    const config = await getClientConfig()
    clientConfig.value = { ...clientConfig.value, ...config }
  } catch (err) {
    console.error('加载客户端配置失败:', err)
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
    emit('success', '高级设置保存成功')
  } catch (err) {
    console.error('保存客户端配置失败:', err)
    emit('error', '保存客户端配置失败: ' + String(err))
  } finally {
    isSaving.value = false
  }
}

// ==================== 敏感配置相关 ====================

/**
 * 检查敏感配置状态
 * 并行发起请求以减少延迟
 */
const checkSensitiveConfigStatus = async (): Promise<void> => {
  try {
    const [hasPassword, debugMode, elevated] = await Promise.all([
      hasSecurityPassword(),
      getDebugMode(),
      isElevated()
    ])
    sensitiveConfig.value.hasPassword = hasPassword
    sensitiveConfig.value.debugMode = debugMode
    sensitiveConfig.value.isElevated = elevated
  } catch (err) {
    console.error('检查敏感配置状态失败:', err)
  }
}

/**
 * 切换敏感配置区域展开状态
 * 立即切换 UI 状态，后台异步加载数据
 */
const toggleSensitiveConfig = (): void => {
  if (!sensitiveConfig.value.isExpanded) {
    // 立即展开 UI
    sensitiveConfig.value.isExpanded = true
    // 后台异步检查状态
    checkSensitiveConfigStatus()
  } else {
    sensitiveConfig.value.isExpanded = false
    sensitiveConfig.value.isAuthenticated = false
    sensitiveConfig.value.password = ''
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
 * 设置安全密码
 */
const handleSetSecurityPassword = async (): Promise<void> => {
  if (!sensitiveConfig.value.password || sensitiveConfig.value.password.length < 6) {
    emit('error', '密码长度至少为6位')
    return
  }

  isSaving.value = true
  try {
    await setSecurityPassword(sensitiveConfig.value.password)
    sensitiveConfig.value.hasPassword = true
    sensitiveConfig.value.isAuthenticated = true
    emit('success', '安全密码设置成功')
  } catch (err) {
    console.error('设置密码失败:', err)
    emit('error', '设置密码失败: ' + String(err))
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
    emit('success', debug ? '调试模式已启用' : '调试模式已禁用')
  } catch (err) {
    console.error('更新调试模式失败:', err)
    emit('error', '更新失败: ' + String(err))
  } finally {
    isSaving.value = false
  }
}

// ==================== 危险操作对话框 ====================

/**
 * 打开危险操作验证对话框
 */
const openDangerDialog = (
  action: 'resetClient' | 'resetTokens',
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
    emit('error', '输入内容不匹配，操作已取消')
    closeDangerDialog()
    return
  }

  isSaving.value = true
  emit('error', '')

  try {
    if (dangerDialog.value.action === 'resetClient') {
      await resetClientConfig()
      emit('success', '客户端配置已重置，即将重新进入引导流程')
      setTimeout(() => {
        router.replace('/guide')
      }, 2000)
    } else if (dangerDialog.value.action === 'resetTokens') {
      await resetAllTokens()
      emit('success', '安全令牌已重置')
    }
  } catch (err) {
    console.error('危险操作失败:', err)
    emit('error', '操作失败: ' + String(err))
  } finally {
    isSaving.value = false
    closeDangerDialog()
  }
}

/**
 * 打开重置令牌对话框
 */
const handleResetTokens = async (): Promise<void> => {
  // 检查是否已提升权限
  const elevated = await isElevated()
  if (!elevated) {
    emit('error', '需要以管理员权限运行才能执行此操作')
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

// 初始化加载配置
loadClientConfig()
</script>

<template>
  <div class="config-section">
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
            <h3>重置客户端配置</h3>
            <p>删除所有客户端配置并重新进入引导流程</p>
          </div>
          <button class="btn btn-error" @click="handleResetClientConfig">
            重置客户端配置
          </button>
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
/* 敏感配置在危险区域内的特定样式 */
.sensitive-danger-item {
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

.danger-divider {
  height: 1px;
  background-color: var(--border-color);
  margin: var(--spacing-md) 0;
}

/* 敏感配置表单特定样式 */
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

/* Token 查看区域特定样式 */
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
