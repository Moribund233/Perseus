<script setup lang="ts">
import { ref, onMounted } from 'vue'
import {
  getDebugMode,
  updateDebugMode,
  getStressTest,
  updateStressTest,
  getDatabaseUrls,
  updateDatabaseUrl,
  isElevated as checkIsElevated,
  getJwtSecretKey,
  getLocalToken,
  resetAllTokens,
  resetClientConfig
} from '../../services/api'
import { useRouter } from 'vue-router'
import ConfirmDialog from '../ConfirmDialog.vue'

/**
 * 数据库类型
 */
type DatabaseType = 'sqlite' | 'postgresql' | 'mysql'

/**
 * 开发者选项组件
 *
 * 提供调试设置、压力测试、安全令牌管理、数据库配置等高级功能
 * 需要在 AdvancedSettings 中通过安全密码验证后才能访问
 */

// 路由
const router = useRouter()

// 加载和保存状态
const isSaving = ref(false)

// 定义事件
const emit = defineEmits<{
  (e: 'error', message: string): void
  (e: 'success', message: string): void
}>()

// 调试与测试设置
const debugSettings = ref({
  debugMode: false,
  stressTest: false
})

// 管理员权限状态
const isElevated = ref(false)

// 安全令牌
const tokenConfig = ref({
  jwtKey: '',
  localToken: '',
  showTokens: false
})

// 数据库配置
const databaseConfig = ref({
  urls: {} as Record<string, string>,
  selectedDbType: 'sqlite' as DatabaseType,
  showDatabaseUrl: false,
  isEditingDatabaseUrl: false,
  tempDatabaseUrl: '',
  urlValidationError: ''
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

/**
 * 初始化加载配置
 */
onMounted(async () => {
  await loadAllConfigs()
})

/**
 * 加载所有配置
 */
const loadAllConfigs = async (): Promise<void> => {
  try {
    const [debugMode, stressTest, elevated, databaseUrls] = await Promise.all([
      getDebugMode(),
      getStressTest(),
      checkIsElevated(),
      getDatabaseUrls()
    ])

    debugSettings.value.debugMode = debugMode
    debugSettings.value.stressTest = stressTest
    isElevated.value = elevated
    databaseConfig.value.urls = databaseUrls

    // 加载 Token
    await loadTokens()
  } catch (err) {
    console.error('加载配置失败:', err)
    emit('error', '加载配置失败: ' + String(err))
  }
}

/**
 * 加载 Token 信息
 */
const loadTokens = async (): Promise<void> => {
  try {
    tokenConfig.value.jwtKey = await getJwtSecretKey()
    tokenConfig.value.localToken = await getLocalToken()
  } catch (err) {
    console.error('加载 Token 失败:', err)
  }
}

/**
 * 更新调试模式
 */
const handleUpdateDebugMode = async (debug: boolean): Promise<void> => {
  isSaving.value = true
  try {
    await updateDebugMode(debug)
    debugSettings.value.debugMode = debug
    emit('success', debug ? '调试模式已启用' : '调试模式已禁用')
  } catch (err) {
    console.error('更新调试模式失败:', err)
    emit('error', '更新失败: ' + String(err))
  } finally {
    isSaving.value = false
  }
}

/**
 * 更新压力测试模式
 */
const handleUpdateStressTest = async (stress: boolean): Promise<void> => {
  isSaving.value = true
  try {
    await updateStressTest(stress)
    debugSettings.value.stressTest = stress
    emit('success', stress ? '压力测试模式已启用' : '压力测试模式已禁用')
  } catch (err) {
    console.error('更新压力测试模式失败:', err)
    emit('error', '更新失败: ' + String(err))
  } finally {
    isSaving.value = false
  }
}

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
 * 开始编辑数据库 URL
 */
const startEditDatabaseUrl = (): void => {
  databaseConfig.value.tempDatabaseUrl = getCurrentDatabaseUrl()
  databaseConfig.value.isEditingDatabaseUrl = true
  databaseConfig.value.urlValidationError = ''
}

/**
 * 取消编辑数据库 URL
 */
const cancelEditDatabaseUrl = (): void => {
  databaseConfig.value.isEditingDatabaseUrl = false
  databaseConfig.value.tempDatabaseUrl = ''
  databaseConfig.value.urlValidationError = ''
}

/**
 * 保存数据库 URL
 */
const saveDatabaseUrl = async (): Promise<void> => {
  const url = databaseConfig.value.tempDatabaseUrl.trim()
  const dbType = databaseConfig.value.selectedDbType

  if (!url) {
    databaseConfig.value.urlValidationError = '数据库 URL 不能为空'
    return
  }

  // 验证 URL 格式
  if (!validateDatabaseUrl(url, dbType)) {
    const prefixMap: Record<string, string> = {
      sqlite: 'sqlite://',
      postgresql: 'postgresql://',
      mysql: 'mysql://'
    }
    databaseConfig.value.urlValidationError = `URL 格式不正确，${dbType} 类型必须以 ${prefixMap[dbType]} 开头`
    return
  }

  isSaving.value = true
  try {
    await updateDatabaseUrl(dbType, url)
    databaseConfig.value.urls[dbType] = url
    databaseConfig.value.isEditingDatabaseUrl = false
    databaseConfig.value.tempDatabaseUrl = ''
    databaseConfig.value.urlValidationError = ''
    emit('success', `${dbType.toUpperCase()} 数据库连接 URL 已更新`)
  } catch (err) {
    console.error('更新数据库 URL 失败:', err)
    emit('error', '更新数据库 URL 失败: ' + String(err))
  } finally {
    isSaving.value = false
  }
}

/**
 * 掩码显示数据库 URL
 * 隐藏敏感信息如密码
 */
const maskDatabaseUrl = (url: string): string => {
  if (!url) return ''
  try {
    // 尝试解析 URL
    if (url.startsWith('sqlite://')) {
      // SQLite URL 通常不包含密码，只显示文件名
      const parts = url.split('/')
      const fileName = parts[parts.length - 1] || 'database.db'
      return `sqlite://***${fileName.slice(-10)}`
    } else {
      // PostgreSQL 或 MySQL URL，隐藏用户名密码部分
      const match = url.match(/^(postgresql|postgres|mysql):\/\/([^@]+)@(.+)$/)
      if (match) {
        return `${match[1]}://***@***`
      }
      return url.replace(/:\/\/[^@]+@/, '://***@')
    }
  } catch {
    return '***'
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
      // 重新加载 Token
      await loadTokens()
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
  const elevated = await checkIsElevated()
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
</script>

<template>
  <div class="developer-options">
    <!-- 调试与测试设置 -->
    <div class="card">
      <div class="card-header">
        <h2 class="card-title">调试与测试设置</h2>
      </div>

      <div class="form-group checkbox-group">
        <label class="checkbox-label">
          <input
            type="checkbox"
            :checked="debugSettings.debugMode"
            @change="handleUpdateDebugMode(!debugSettings.debugMode)"
            :disabled="isSaving"
          />
          <span>启用调试模式</span>
        </label>
        <p class="help-text">启用后将显示详细的调试信息</p>
      </div>

      <div class="form-group checkbox-group">
        <label class="checkbox-label">
          <input
            type="checkbox"
            :checked="debugSettings.stressTest"
            @change="handleUpdateStressTest(!debugSettings.stressTest)"
            :disabled="isSaving"
          />
          <span>启用压力测试模式</span>
        </label>
        <p class="help-text">启用后服务端将加载压力测试数据，用于性能测试</p>
      </div>
    </div>

    <!-- 安全令牌与数据库配置（管理员权限控制） -->
    <div class="card admin-required-section" :class="{ disabled: !isElevated }">
      <div class="card-header">
        <h2 class="card-title">安全令牌与数据库配置</h2>
      </div>

      <p v-if="!isElevated" class="elevate-warning">
        ⚠️ 需要以管理员权限运行才能查看和修改以下配置
      </p>

      <div class="admin-required-content" :class="{ disabled: !isElevated }">
        <!-- 查看 Token -->
        <div class="subsection">
          <div class="subsection-header">
            <h4>安全令牌查看</h4>
            <button
              class="btn btn-sm"
              :class="tokenConfig.showTokens ? 'btn-secondary' : 'btn-primary'"
              @click="tokenConfig.showTokens = !tokenConfig.showTokens"
              :disabled="!isElevated"
            >
              {{ tokenConfig.showTokens ? '隐藏' : '显示' }}
            </button>
          </div>
          <div v-if="tokenConfig.showTokens" class="token-display-area">
            <div class="token-item">
              <label>JWT 密钥:</label>
              <div class="token-value no-select">{{ tokenConfig.jwtKey }}</div>
            </div>
            <div class="token-item">
              <label>本地 Token:</label>
              <div class="token-value no-select">{{ tokenConfig.localToken }}</div>
            </div>
            <p class="token-hint">⚠️ 仅用于开发调试，请勿泄露或复制这些值</p>
          </div>
        </div>

        <!-- Token重置 -->
        <div class="subsection token-reset-section">
          <div class="danger-item-inner">
            <div class="danger-info">
              <h4>重置安全令牌</h4>
              <p>重置 JWT 密钥和本地 Token</p>
            </div>
            <button
              class="btn btn-error"
              @click="handleResetTokens"
              :disabled="!isElevated || isSaving"
            >
              重置令牌
            </button>
          </div>
        </div>

        <!-- 数据库配置 -->
        <div class="subsection">
          <h4>数据库配置</h4>
          <div class="form-group">
            <div class="database-config-row">
              <!-- 左侧：URL 输入框 -->
              <div class="url-input-section">
                <label class="form-label">数据库连接 URL</label>
                <div v-if="!databaseConfig.isEditingDatabaseUrl" class="database-url-display">
                  <div class="url-value-wrapper">
                    <span class="url-value">
                      {{ databaseConfig.showDatabaseUrl ? getCurrentDatabaseUrl() : maskDatabaseUrl(getCurrentDatabaseUrl()) }}
                    </span>
                  </div>
                </div>
                <div v-else class="database-url-edit">
                  <input
                    v-model="databaseConfig.tempDatabaseUrl"
                    type="text"
                    class="input"
                    :class="{ 'input-error': databaseConfig.urlValidationError }"
                    :placeholder="`例如: ${databaseConfig.selectedDbType === 'sqlite' ? 'sqlite:///./langit.db' : databaseConfig.selectedDbType === 'postgresql' ? 'postgresql://user:pass@localhost/dbname' : 'mysql://user:pass@localhost/dbname'}`"
                  />
                  <span v-if="databaseConfig.urlValidationError" class="input-error-text">
                    {{ databaseConfig.urlValidationError }}
                  </span>
                </div>
              </div>

              <!-- 右侧：数据库类型下拉框 -->
              <div class="db-type-select-section">
                <label class="form-label">数据库类型</label>
                <select
                  v-model="databaseConfig.selectedDbType"
                  class="input"
                  :disabled="databaseConfig.isEditingDatabaseUrl || !isElevated"
                >
                  <option value="sqlite">SQLite</option>
                  <option value="postgresql">PostgreSQL</option>
                  <option value="mysql">MySQL</option>
                </select>
              </div>
            </div>

            <!-- 操作按钮 -->
            <div class="url-actions-row">
              <div v-if="!databaseConfig.isEditingDatabaseUrl" class="url-actions">
                <button
                  class="btn btn-sm btn-secondary"
                  @click="databaseConfig.showDatabaseUrl = !databaseConfig.showDatabaseUrl"
                  :disabled="!isElevated"
                >
                  {{ databaseConfig.showDatabaseUrl ? '隐藏' : '显示' }}
                </button>
                <button
                  class="btn btn-sm btn-primary"
                  @click="startEditDatabaseUrl"
                  :disabled="!isElevated"
                >
                  修改
                </button>
              </div>
              <div v-else class="url-edit-actions">
                <button
                  class="btn btn-sm btn-secondary"
                  @click="cancelEditDatabaseUrl"
                >
                  取消
                </button>
                <button
                  class="btn btn-sm btn-primary"
                  @click="saveDatabaseUrl"
                  :disabled="isSaving"
                >
                  保存
                </button>
              </div>
            </div>
            <p class="help-text">修改后需要重启服务端才能生效</p>
          </div>
        </div>
      </div>
    </div>

    <!-- 危险区域：重置客户端配置 -->
    <div class="card danger-zone">
      <div class="card-header">
        <h2 class="card-title">危险区域</h2>
      </div>

      <div class="danger-item">
        <div class="danger-info">
          <h3>重置客户端配置</h3>
          <p>删除所有客户端配置并重新进入引导流程</p>
        </div>
        <button class="btn btn-error" @click="handleResetClientConfig" :disabled="isSaving">
          重置客户端配置
        </button>
      </div>
    </div>

    <!-- 危险操作验证对话框 -->
    <ConfirmDialog
      v-model:visible="dangerDialog.show"
      :title="dangerDialog.title"
      type="danger"
      :message="dangerDialog.message"
      :hint="'请输入 \'' + dangerDialog.expectedInput + '\' 确认'"
      :confirm-text="dangerDialog.confirmText"
      :require-input="true"
      :expected-input="dangerDialog.expectedInput"
      :loading="isSaving"
      @update:input="dangerInput = $event"
      @confirm="confirmDangerAction"
      @cancel="closeDangerDialog"
    />
  </div>
</template>

<style scoped>
/* 开发者选项容器 */
.developer-options {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
}

/* 管理员权限控制区域样式 */
.admin-required-section {
  border: 1px solid var(--border-color);
}

.admin-required-section.disabled {
  opacity: 0.7;
  border-color: var(--border-color);
}

.admin-required-content {
  margin-top: var(--spacing-md);
}

.admin-required-content.disabled {
  pointer-events: none;
  opacity: 0.6;
}

.admin-required-section .elevate-warning {
  color: var(--warning-color);
  font-size: var(--font-size-sm);
  margin: var(--spacing-sm) 0 var(--spacing-md);
  padding: var(--spacing-sm);
  background-color: rgba(234, 179, 8, 0.1);
  border-radius: var(--border-radius-sm);
}

/* 子区域样式 */
.subsection {
  margin-bottom: var(--spacing-lg);
}

.subsection:last-child {
  margin-bottom: 0;
}

.subsection-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-sm);
}

.subsection-header h4,
.subsection h4 {
  margin: 0;
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}

/* Token 查看区域样式 */
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

/* Token 重置区域 */
.token-reset-section {
  padding-bottom: var(--spacing-lg);
  border-bottom: 1px solid var(--border-color);
}

.token-reset-section .danger-item-inner {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--spacing-md);
}

.token-reset-section .danger-info h4 {
  margin: 0 0 var(--spacing-xs) 0;
}

.token-reset-section .danger-info p {
  margin: 0;
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
}

/* 数据库配置行布局 */
.database-config-row {
  display: flex;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-md);
}

.url-input-section {
  flex: 1;
  min-width: 0;
}

.db-type-select-section {
  width: 150px;
  flex-shrink: 0;
}

.db-type-select-section select {
  width: 100%;
}

.url-actions-row {
  display: flex;
  justify-content: flex-end;
}

.database-url-display {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.url-value-wrapper {
  background-color: var(--bg-tertiary);
  padding: var(--spacing-sm) var(--spacing-md);
  border-radius: var(--border-radius-sm);
  border: 1px solid var(--border-color);
  overflow: hidden;
}

.url-value {
  font-family: monospace;
  font-size: var(--font-size-sm);
  color: var(--text-primary);
  word-break: break-all;
}

.url-actions {
  display: flex;
  gap: var(--spacing-sm);
}

.database-url-edit {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.database-url-edit .input {
  font-family: monospace;
  font-size: var(--font-size-sm);
}

.url-edit-actions {
  display: flex;
  gap: var(--spacing-sm);
  justify-content: flex-end;
}

/* 危险区域样式 */
.danger-zone {
  border-color: var(--error-color);
}

.danger-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-md);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius-md);
  background-color: var(--bg-secondary);
}

.danger-info h3 {
  margin: 0 0 var(--spacing-xs) 0;
  font-size: var(--font-size-md);
  color: var(--text-primary);
}

.danger-info p {
  margin: 0;
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}
</style>
