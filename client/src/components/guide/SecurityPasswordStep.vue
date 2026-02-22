<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import Button from '../Button.vue'
import ConfirmDialog from '../ConfirmDialog.vue'
import {
  setSecurityPassword,
  verifySecurityPassword,
  hasSecurityPassword,
  getDatabaseUrls,
  updateDatabaseUrl,
  getDatabaseType
} from '../../services/api'
import { useGuideEventBus } from '../../composables/useGuideEvents'

/**
 * 数据库类型
 */
type DatabaseType = 'sqlite' | 'postgresql' | 'mysql'

/**
 * 安全密码设置/验证步骤组件
 *
 * 功能：
 * - 首次使用：设置安全密码以保护敏感配置
 * - 重置后：验证已有密码，避免加密配置被覆盖
 * 状态管理：通过事件总线与Guide主组件通信
 */

const eventBus = useGuideEventBus()

// 从事件总线获取状态
const state = eventBus.state.value.securityPassword
const guideState = eventBus.state.value.guide

// 本地状态：是否已存在安全密码（需要验证而非设置）
const hasExistingPassword = ref(false)
// 本地状态：验证模式下的输入密码
const verifyPassword = ref('')
// 本地状态：验证错误次数
const verifyAttempts = ref(0)
const MAX_VERIFY_ATTEMPTS = 5

// 重置确认对话框状态
const showResetDialog = ref(false)
const resetDialogStep = ref<1 | 2>(1)

// 数据库配置状态
const databaseConfig = ref({
  urls: {} as Record<string, string>,
  selectedDbType: 'sqlite' as DatabaseType,
  tempUrl: '',
  isEditing: false,
  urlError: ''
})

/**
 * 初始化时检查是否已存在安全密码并加载数据库配置
 */
onMounted(async () => {
  try {
    const [hasPassword, databaseUrls, dbType] = await Promise.all([
      hasSecurityPassword(),
      getDatabaseUrls(),
      getDatabaseType()
    ])
    hasExistingPassword.value = hasPassword
    databaseConfig.value.urls = databaseUrls
    databaseConfig.value.selectedDbType = (dbType as DatabaseType) || 'sqlite'

    // 如果已存在密码且已验证过，自动标记为完成
    if (hasPassword && state.isSaved) {
      eventBus.emit('step:complete', { step: 1, data: null })
      setTimeout(() => {
        eventBus.emit('nav:next', undefined)
      }, 300)
    }
  } catch (e) {
    console.error('检查安全密码状态失败:', e)
  }
})

/**
 * 密码错误提示（设置模式）
 */
const passwordError = computed(() => {
  if (state.securityPassword && state.securityPassword.length < 6) {
    return '密码长度至少为6位'
  }
  return ''
})

/**
 * 确认密码错误提示（设置模式）
 */
const confirmPasswordError = computed(() => {
  const confirmPwd = state.confirmPassword || ''
  if (confirmPwd && confirmPwd !== state.securityPassword) {
    return '两次输入的密码不一致'
  }
  return ''
})

/**
 * 验证密码错误提示
 */
const verifyPasswordError = computed(() => {
  if (verifyAttempts.value > 0) {
    return `密码错误，还剩 ${MAX_VERIFY_ATTEMPTS - verifyAttempts.value} 次机会`
  }
  return ''
})

/**
 * 获取当前选中的数据库 URL
 */
const getCurrentDatabaseUrl = (): string => {
  return databaseConfig.value.urls[databaseConfig.value.selectedDbType] || ''
}

/**
 * 验证数据库 URL 格式
 */
const validateDatabaseUrl = (url: string, dbType: string): boolean => {
  const urlLower = url.toLowerCase().trim()

  switch (dbType) {
    case 'sqlite':
      return urlLower.startsWith('sqlite://')
    case 'postgresql':
      return urlLower.startsWith('postgresql://') || urlLower.startsWith('postgres://')
    case 'mysql':
      return urlLower.startsWith('mysql://')
    default:
      return false
  }
}

/**
 * 检查数据库 URL 是否已配置
 */
const isDatabaseUrlConfigured = computed(() => {
  const url = getCurrentDatabaseUrl()
  return url && url.trim().length > 0 && validateDatabaseUrl(url, databaseConfig.value.selectedDbType)
})

/**
 * 设置模式下是否可以继续
 * 需要同时满足：密码有效、确认密码一致、数据库 URL 已配置
 */
const canProceedSet = computed(() => {
  const passwordValid = state.securityPassword.length >= 6 &&
    state.securityPassword === state.confirmPassword
  const dbUrlValid = isDatabaseUrlConfigured.value
  return state.isSaved || (passwordValid && dbUrlValid)
})

/**
 * 验证模式下是否可以继续
 */
const canProceedVerify = computed(() => {
  return verifyPassword.value.length >= 6 && verifyAttempts.value < MAX_VERIFY_ATTEMPTS
})

/**
 * 验证密码有效性（设置模式）
 */
function validatePassword(): boolean {
  if (!state.securityPassword || state.securityPassword.length < 6) {
    eventBus.setError('请设置有效的安全密码（至少6位）')
    return false
  }
  if (state.securityPassword !== state.confirmPassword) {
    eventBus.setError('两次输入的密码不一致')
    return false
  }
  return true
}

/**
 * 开始编辑数据库 URL
 */
function startEditDatabaseUrl(): void {
  databaseConfig.value.tempUrl = getCurrentDatabaseUrl()
  databaseConfig.value.isEditing = true
  databaseConfig.value.urlError = ''
}

/**
 * 取消编辑数据库 URL
 */
function cancelEditDatabaseUrl(): void {
  databaseConfig.value.isEditing = false
  databaseConfig.value.tempUrl = ''
  databaseConfig.value.urlError = ''
}

/**
 * 保存数据库 URL
 */
async function saveDatabaseUrl(): Promise<void> {
  const url = databaseConfig.value.tempUrl.trim()
  const dbType = databaseConfig.value.selectedDbType

  if (!url) {
    databaseConfig.value.urlError = '数据库 URL 不能为空'
    return
  }

  // 验证 URL 格式
  if (!validateDatabaseUrl(url, dbType)) {
    const prefixMap: Record<string, string> = {
      sqlite: 'sqlite://',
      postgresql: 'postgresql://',
      mysql: 'mysql://'
    }
    databaseConfig.value.urlError = `URL 格式不正确，${dbType} 类型必须以 ${prefixMap[dbType]} 开头`
    return
  }

  eventBus.setSaving(true)
  eventBus.clearError()

  try {
    await updateDatabaseUrl(dbType, url)
    databaseConfig.value.urls[dbType] = url
    databaseConfig.value.isEditing = false
    databaseConfig.value.tempUrl = ''
    databaseConfig.value.urlError = ''
  } catch (e) {
    eventBus.setError('保存数据库 URL 失败: ' + String(e))
    console.error('保存数据库 URL 失败:', e)
  } finally {
    eventBus.setSaving(false)
  }
}

/**
 * 保存安全密码（设置模式）
 */
async function savePassword(): Promise<void> {
  if (!validatePassword()) {
    return
  }

  eventBus.setSaving(true)
  eventBus.clearError()

  try {
    // 保存安全密码
    await setSecurityPassword(state.securityPassword)

    // 更新状态
    eventBus.updateSecurityPassword({
      isPasswordValid: true,
      isSaved: true
    })

    // 触发步骤完成事件
    eventBus.emit('step:complete', { step: 1, data: state.securityPassword })

    // 自动进入下一步
    setTimeout(() => {
      eventBus.emit('nav:next', undefined)
    }, 300)
  } catch (e) {
    eventBus.setError('保存安全密码失败: ' + String(e))
    console.error('保存安全密码失败:', e)
  } finally {
    eventBus.setSaving(false)
  }
}

/**
 * 验证安全密码（验证模式）
 */
async function verifyAndContinue(): Promise<void> {
  if (!verifyPassword.value || verifyPassword.value.length < 6) {
    eventBus.setError('请输入有效的安全密码（至少6位）')
    return
  }

  eventBus.setSaving(true)
  eventBus.clearError()

  try {
    const isValid = await verifySecurityPassword(verifyPassword.value)

    if (isValid) {
      // 验证成功，更新状态
      eventBus.updateSecurityPassword({
        isPasswordValid: true,
        isSaved: true
      })

      // 触发步骤完成事件
      eventBus.emit('step:complete', { step: 1, data: null })

      // 自动进入下一步
      setTimeout(() => {
        eventBus.emit('nav:next', undefined)
      }, 300)
    } else {
      // 验证失败
      verifyAttempts.value++
      if (verifyAttempts.value >= MAX_VERIFY_ATTEMPTS) {
        eventBus.setError('密码验证失败次数过多，请重启应用后重试')
      } else {
        eventBus.setError(`密码错误，还剩 ${MAX_VERIFY_ATTEMPTS - verifyAttempts.value} 次机会`)
      }
      verifyPassword.value = ''
    }
  } catch (e) {
    eventBus.setError('验证安全密码失败: ' + String(e))
    console.error('验证安全密码失败:', e)
  } finally {
    eventBus.setSaving(false)
  }
}

/**
 * 打开重置确认对话框
 */
function openResetDialog(): void {
  showResetDialog.value = true
  resetDialogStep.value = 1
}

/**
 * 关闭重置确认对话框
 */
function closeResetDialog(): void {
  showResetDialog.value = false
}

/**
 * 处理重置对话框确认
 */
function handleResetConfirm(): void {
  if (resetDialogStep.value === 1) {
    // 进入第二步
    resetDialogStep.value = 2
  } else {
    // 确认重置，切换到设置模式
    hasExistingPassword.value = false
    verifyPassword.value = ''
    verifyAttempts.value = 0
    eventBus.clearError()
    closeResetDialog()
  }
}

/**
 * 获取重置对话框消息
 */
const resetDialogMessage = computed(() => {
  if (resetDialogStep.value === 1) {
    return '重置加密配置将生成新的安全密钥和认证令牌'
  }
  return '此操作不可撤销，确定要重置加密配置吗？'
})

/**
 * 获取重置对话框提示
 */
const resetDialogHint = computed(() => {
  if (resetDialogStep.value === 1) {
    return '仅在加密配置文件被物理删除或您明确知道风险时使用。'
  }
  return '重置后将需要重新设置安全密码'
})

/**
 * 获取重置对话框确认按钮文本
 */
const resetDialogConfirmText = computed(() => {
  return resetDialogStep.value === 1 ? '继续' : '确认重置'
})
</script>

<template>
  <div class="step-content">
    <!-- 验证模式：已存在安全密码 -->
    <template v-if="hasExistingPassword && !state.isSaved">
      <h2 class="step-heading">验证安全密码</h2>
      <p class="step-text">
        检测到已存在加密配置，请输入您的安全密码以继续。
      </p>

      <div class="password-form">
        <div class="form-group">
          <label class="form-label">
            安全密码 <span class="required">*</span>
          </label>
          <input
            v-model="verifyPassword"
            type="password"
            class="form-input"
            :class="{ 'input-error': verifyPasswordError }"
            placeholder="输入您的安全密码"
            :disabled="guideState.isSaving || verifyAttempts >= MAX_VERIFY_ATTEMPTS"
            @keyup.enter="verifyAndContinue"
          />
          <p v-if="verifyPasswordError" class="error-text">{{ verifyPasswordError }}</p>
        </div>
      </div>

      <div class="action-row">
        <Button
          type="primary"
          :loading="guideState.isSaving"
          :disabled="!canProceedVerify"
          @click="verifyAndContinue"
        >
          验证并继续
        </Button>
        <Button
          type="secondary"
          :disabled="guideState.isSaving"
          @click="openResetDialog"
        >
          重置加密配置
        </Button>
      </div>
    </template>

    <!-- 设置模式：首次设置或重置后 -->
    <template v-else>
      <h2 class="step-heading">设置安全密码</h2>
      <p class="step-text">
        为了保护您的敏感配置信息，请设置一个安全密码。此密码将用于加密存储配置文件。
      </p>

      <!-- 密码设置表单 -->
      <div class="password-form">
        <div class="form-group">
          <label class="form-label">
            安全密码 <span class="required">*</span>
          </label>
          <input
            v-model="state.securityPassword"
            type="password"
            class="form-input"
            :class="{ 'input-error': passwordError }"
            placeholder="设置安全密码（至少6位）"
            :disabled="state.isSaved"
          />
          <p v-if="passwordError" class="error-text">{{ passwordError }}</p>
        </div>

        <div class="form-group">
          <label class="form-label">
            确认密码 <span class="required">*</span>
          </label>
          <input
            v-model="state.confirmPassword"
            type="password"
            class="form-input"
            :class="{ 'input-error': confirmPasswordError }"
            placeholder="再次输入安全密码（至少6位）"
            :disabled="state.isSaved"
          />
          <p v-if="confirmPasswordError" class="error-text">{{ confirmPasswordError }}</p>
        </div>
      </div>

      <!-- 数据库配置 -->
      <div class="database-config-section">
        <h3 class="subsection-heading">数据库配置 <span class="required">*</span></h3>
        <p class="subsection-text">
          请配置数据库连接信息，用于存储应用数据。
        </p>

        <div class="database-config-row">
          <!-- 左侧：URL 输入框 -->
          <div class="url-input-section">
            <label class="form-label">数据库连接 URL</label>
            <div v-if="!databaseConfig.isEditing" class="database-url-display">
              <div class="url-value-wrapper">
                <span class="url-value" :class="{ 'url-empty': !getCurrentDatabaseUrl() }">
                  {{ getCurrentDatabaseUrl() || '未配置' }}
                </span>
              </div>
            </div>
            <div v-else class="database-url-edit">
              <input
                v-model="databaseConfig.tempUrl"
                type="text"
                class="form-input url-input"
                :class="{ 'input-error': databaseConfig.urlError }"
                :placeholder="databaseConfig.selectedDbType === 'sqlite'
                  ? 'sqlite:///path/to/database.db'
                  : databaseConfig.selectedDbType === 'postgresql'
                    ? 'postgresql://用户名:密码@主机:端口/数据库名'
                    : 'mysql://用户名:密码@主机:端口/数据库名'"
              />
              <p v-if="databaseConfig.urlError" class="error-text">{{ databaseConfig.urlError }}</p>
            </div>
          </div>

          <!-- 右侧：数据库类型下拉框 -->
          <div class="db-type-select-section">
            <label class="form-label">数据库类型</label>
            <select
              v-model="databaseConfig.selectedDbType"
              class="form-input"
              :disabled="databaseConfig.isEditing"
            >
              <option value="sqlite">SQLite</option>
              <option value="postgresql">PostgreSQL</option>
              <option value="mysql">MySQL</option>
            </select>
          </div>
        </div>

        <!-- 操作按钮 -->
        <div class="url-actions-row">
          <div v-if="!databaseConfig.isEditing" class="url-actions">
            <Button
              type="primary"
              size="sm"
              :disabled="state.isSaved"
              @click="startEditDatabaseUrl"
            >
              {{ getCurrentDatabaseUrl() ? '修改' : '配置' }}
            </Button>
          </div>
          <div v-else class="url-edit-actions">
            <Button
              type="secondary"
              size="sm"
              @click="cancelEditDatabaseUrl"
            >
              取消
            </Button>
            <Button
              type="primary"
              size="sm"
              :loading="guideState.isSaving"
              @click="saveDatabaseUrl"
            >
              保存
            </Button>
          </div>
        </div>
      </div>

      <!-- 保存按钮 -->
      <div class="action-row" v-if="!state.isSaved">
        <Button
          type="primary"
          :loading="guideState.isSaving"
          :disabled="!canProceedSet"
          @click="savePassword"
        >
          保存并继续
        </Button>
      </div>

      <!-- 已保存提示 -->
      <div v-else class="success-message">
        <span class="success-icon">✓</span>
        安全密码已设置
      </div>
    </template>

    <!-- 重置确认对话框 -->
    <ConfirmDialog
      v-model:visible="showResetDialog"
      :title="resetDialogStep === 1 ? '重置加密配置' : '确认重置'"
      type="danger"
      :two-step="true"
      :step="resetDialogStep"
      :message="resetDialogMessage"
      :hint="resetDialogHint"
      :confirm-text="resetDialogConfirmText"
      @confirm="handleResetConfirm"
      @cancel="closeResetDialog"
    />
  </div>
</template>

<style scoped>
@import '../../styles/guide-steps.css';
</style>
