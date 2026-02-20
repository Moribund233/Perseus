<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import Button from '../components/Button.vue'
import Card from '../components/Card.vue'
import Alert from '../components/Alert.vue'
import {
  getClientConfig,
  saveClientConfig,
  getNginxStatus,
  loadNginx,
  downloadAndExtractNginx,
  updateNginxDownloadUrl,
  checkServerPath,
  validateAndSaveServerPath,
  checkGitInstallation,
  markGuideCompleted,
  setSecurityPassword,
  getNginxPlatformInfo,
  type ClientConfig,
  type NginxPlatformInfo
} from '../services/api'
import { useThemeStore, presetColorThemes, layoutDensityPresets } from '../stores'

/**
 * 首次启动引导页面
 *
 * 功能流程：
 * 1. 服务端检查 - 检测/指定服务端路径
 * 2. Nginx载入 - 可选的Nginx预配置
 * 3. Git检查 - 验证Git环境
 * 4. 用户偏好 - 主题和布局设置
 */

const router = useRouter()
const themeStore = useThemeStore()

// 当前步骤 (1-4)
const currentStep = ref(1)
const isLoading = ref(false)
const error = ref('')

// 客户端配置
const clientConfig = ref<ClientConfig | null>(null)

// 步骤状态
const steps = [
  { id: 1, title: '服务端检查', description: '配置服务端路径' },
  { id: 2, title: 'Nginx载入', description: '可选的反向代理' },
  { id: 3, title: 'Git检查', description: '验证Git环境' },
  { id: 4, title: '用户偏好', description: '主题和布局设置' }
]

// ==================== 步骤1: 服务端检查 ====================
const serverPath = ref('')
const serverCheckStatus = ref<'idle' | 'checking' | 'found' | 'not_found'>('idle')

// ==================== 步骤2: Nginx ====================
const nginxStatus = ref<'not_loaded' | 'loaded' | 'skipped'>('not_loaded')
const nginxDownloadUrl = ref('https://nginx.org/download/nginx-1.24.0.zip')
const isNginxDownloading = ref(false)
const nginxPlatformInfo = ref<NginxPlatformInfo | null>(null)

// Nginx平台相关计算属性
const supportsNginxManualLoad = computed(() => {
  return nginxPlatformInfo.value?.supports_manual_load ?? false
})

const supportsNginxDownload = computed(() => {
  return nginxPlatformInfo.value?.supports_download ?? false
})

const nginxPlatformDisplayText = computed(() => {
  if (!nginxPlatformInfo.value) return ''
  if (nginxPlatformInfo.value.uses_package_manager) {
    const pm = nginxPlatformInfo.value.package_manager || '包管理器'
    return `（通过${pm}管理）`
  }
  return ''
})

// ==================== 步骤3: Git ====================
const gitStatus = ref<'idle' | 'checking' | 'installed' | 'not_installed'>('idle')
const gitVersion = ref('')

// ==================== 步骤4: 用户偏好 ====================
const selectedTheme = ref('dark')
const selectedLayout = ref('default')
const securityPassword = ref('')
const confirmPassword = ref('')

// 计算属性
const isFirstStep = computed(() => currentStep.value === 1)
const isLastStep = computed(() => currentStep.value === 4)
const canProceed = computed(() => {
  switch (currentStep.value) {
    case 1:
      return serverCheckStatus.value === 'found'
    case 2:
      return true // Nginx可选
    case 3:
      return gitStatus.value === 'installed' || gitStatus.value === 'not_installed' // 可跳过
    case 4:
      // 步骤4需要设置安全密码
      return securityPassword.value.length >= 6 && securityPassword.value === confirmPassword.value
    default:
      return false
  }
})

// 初始化
onMounted(async () => {
  try {
    clientConfig.value = await getClientConfig()
    selectedTheme.value = clientConfig.value?.appearance?.theme || 'dark'
    selectedLayout.value = clientConfig.value?.appearance?.layout_density || 'default'

    // 自动检查服务端
    await checkServer()
    // 自动检查Git
    await checkGit()
    // 检查Nginx状态
    await checkNginx()
    // 加载Nginx平台信息
    await loadNginxPlatformInfo()
  } catch (e) {
    console.error('初始化失败:', e)
  }
})

// ==================== 步骤1: 服务端检查 ====================
async function checkServer() {
  serverCheckStatus.value = 'checking'
  try {
    const result = await checkServerPath()
    if (result.found) {
      serverCheckStatus.value = 'found'
      serverPath.value = result.path || ''
    } else {
      serverCheckStatus.value = 'not_found'
    }
  } catch (e) {
    serverCheckStatus.value = 'not_found'
  }
}

async function selectServerPath() {
  try {
    const { open } = await import('@tauri-apps/plugin-dialog')
    const selected = await open({
      multiple: false
      // 不设置filters，允许选择任何文件
    })
    if (selected && typeof selected === 'string') {
      serverPath.value = selected
      await validateAndSaveServerPath(selected)
    }
  } catch (e) {
    error.value = '选择文件失败: ' + String(e)
  }
}



// ==================== 步骤2: Nginx ====================
async function checkNginx() {
  try {
    const status = await getNginxStatus()
    if (status.is_loaded) {
      nginxStatus.value = 'loaded'
    }
  } catch (e) {
    console.error('检查Nginx失败:', e)
  }
}

/**
 * 加载Nginx平台信息
 */
async function loadNginxPlatformInfo() {
  try {
    nginxPlatformInfo.value = await getNginxPlatformInfo()
  } catch (e) {
    console.error('获取Nginx平台信息失败:', e)
  }
}

async function loadNginxManually() {
  try {
    const { open } = await import('@tauri-apps/plugin-dialog')
    const selected = await open({
      multiple: false
      // 不设置filters，允许选择任何文件
    })
    if (selected && typeof selected === 'string') {
      isLoading.value = true
      const result = await loadNginx(selected)
      if (result.success) {
        nginxStatus.value = 'loaded'
      } else {
        error.value = result.message
      }
    }
  } catch (e) {
    error.value = '载入Nginx失败: ' + String(e)
  } finally {
    isLoading.value = false
  }
}

async function downloadNginx() {
  isNginxDownloading.value = true
  error.value = ''
  try {
    await updateNginxDownloadUrl(nginxDownloadUrl.value)
    const result = await downloadAndExtractNginx(nginxDownloadUrl.value)
    if (result.success) {
      nginxStatus.value = 'loaded'
    } else {
      error.value = result.message
    }
  } catch (e) {
    error.value = '下载Nginx失败: ' + String(e)
  } finally {
    isNginxDownloading.value = false
  }
}

function skipNginx() {
  nginxStatus.value = 'skipped'
  nextStep()
}

// ==================== 步骤3: Git检查 ====================
async function checkGit() {
  gitStatus.value = 'checking'
  try {
    const result = await checkGitInstallation()
    if (result.installed) {
      gitStatus.value = 'installed'
      gitVersion.value = result.version || ''
    } else {
      gitStatus.value = 'not_installed'
    }
  } catch (e) {
    gitStatus.value = 'not_installed'
  }
}

function skipGit() {
  nextStep()
}

// ==================== 步骤4: 用户偏好 ====================
/**
 * 选择主题并实时预览
 * @param themeId 主题ID
 */
function selectTheme(themeId: string) {
  selectedTheme.value = themeId
  themeStore.switchColorTheme(themeId)
}

/**
 * 选择布局密度并实时预览
 * @param layoutId 布局ID
 */
function selectLayout(layoutId: string) {
  selectedLayout.value = layoutId
  themeStore.switchLayoutDensity(layoutId)
}

async function savePreferences() {
  isLoading.value = true
  error.value = ''

  try {
    // 验证安全密码 - 必填项
    if (!securityPassword.value) {
      error.value = '请设置安全密码'
      isLoading.value = false
      return
    }
    if (securityPassword.value.length < 6) {
      error.value = '安全密码长度至少为6位'
      isLoading.value = false
      return
    }
    if (securityPassword.value !== confirmPassword.value) {
      error.value = '两次输入的密码不一致'
      isLoading.value = false
      return
    }
    // 保存安全密码
    await setSecurityPassword(securityPassword.value)

    // 构建最终配置对象
    const finalConfig: ClientConfig = {
      server: {
        url: clientConfig.value?.server?.url || 'http://127.0.0.1:8000',
        auto_connect: clientConfig.value?.server?.auto_connect ?? true,
        auto_start: clientConfig.value?.server?.auto_start ?? false,
        path: {
          exe_name: clientConfig.value?.server?.path?.exe_name || 'langit-server.exe',
          dir_name: clientConfig.value?.server?.path?.dir_name || 'langit-server',
          custom_path: serverPath.value || clientConfig.value?.server?.path?.custom_path
        }
      },
      appearance: {
        theme: selectedTheme.value,
        language: clientConfig.value?.appearance?.language || 'zh',
        sidebar_collapsed: clientConfig.value?.appearance?.sidebar_collapsed ?? false,
        layout_density: selectedLayout.value
      },
      notification: {
        enabled: clientConfig.value?.notification?.enabled ?? true,
        on_error: clientConfig.value?.notification?.on_error ?? true,
        on_warning: clientConfig.value?.notification?.on_warning ?? false,
        on_start_stop: clientConfig.value?.notification?.on_start_stop ?? true
      },
      log: {
        level: clientConfig.value?.log?.level || 'info',
        retention_days: clientConfig.value?.log?.retention_days ?? 7
      },
      advanced: {
        ws_reconnect_interval: clientConfig.value?.advanced?.ws_reconnect_interval ?? 3000,
        connection_timeout: clientConfig.value?.advanced?.connection_timeout ?? 30,
        request_timeout: clientConfig.value?.advanced?.request_timeout ?? 30
      }
    }

    // 保存配置（这会生成 client.toml 文件）
    await saveClientConfig(finalConfig)

    // 标记引导完成
    await markGuideCompleted()

    // 跳转到主页
    router.replace('/home')
  } catch (e) {
    error.value = '保存配置失败: ' + String(e)
    console.error('保存配置失败:', e)
  } finally {
    isLoading.value = false
  }
}

// ==================== 导航控制 ====================
function nextStep() {
  if (currentStep.value < 4) {
    currentStep.value++
    error.value = ''
  }
}

function prevStep() {
  if (currentStep.value > 1) {
    currentStep.value--
    error.value = ''
  }
}

// ==================== Tauri命令调用 ====================
// 所有Tauri命令调用已通过API服务导入
</script>

<template>
  <div class="guide-container">
    <!-- 步骤指示器 -->
    <div class="step-indicator">
      <div
        v-for="(step, index) in steps"
        :key="step.id"
        class="step-item"
        :class="{
          'step-active': currentStep === step.id,
          'step-completed': currentStep > step.id
        }"
      >
        <div class="step-number">{{ index + 1 }}</div>
        <div class="step-info">
          <div class="step-title">{{ step.title }}</div>
          <div class="step-desc">{{ step.description }}</div>
        </div>
        <div v-if="index < steps.length - 1" class="step-line" />
      </div>
    </div>

    <!-- 步骤内容 -->
    <Card class="guide-card">
      <!-- 错误提示 -->
      <Alert v-if="error" type="error" closable @close="error = ''">
        {{ error }}
      </Alert>

      <!-- 步骤1: 服务端检查 -->
      <div v-if="currentStep === 1" class="step-content">
        <h2 class="step-heading">配置服务端</h2>
        <p class="step-text">需要指定LanGit服务端可执行文件的位置</p>

        <div v-if="serverCheckStatus === 'checking'" class="status-box">
          <span class="loading-text">正在检查默认路径...</span>
        </div>

        <div v-else-if="serverCheckStatus === 'found'" class="status-box success">
          <img src="../assets/icons/success.svg" class="status-icon" alt="success" />
          <span>已找到服务端: {{ serverPath }}</span>
        </div>

        <div v-else class="status-box warning">
          <img src="../assets/icons/warning.svg" class="status-icon" alt="warning" />
          <span>未在默认路径找到服务端，请手动指定</span>
        </div>

        <div class="action-row">
          <Button
            type="primary"
            :loading="isLoading"
            @click="selectServerPath"
          >
            选择服务端文件
          </Button>
          <Button
            v-if="serverCheckStatus === 'not_found'"
            type="secondary"
            @click="checkServer"
          >
            重新检查
          </Button>
        </div>
      </div>

      <!-- 步骤2: Nginx载入 -->
      <div v-if="currentStep === 2" class="step-content">
        <h2 class="step-heading">配置Nginx（可选）</h2>
        <p class="step-text">Nginx可作为反向代理，提供更好的性能和安全性</p>

        <div v-if="nginxStatus === 'loaded'" class="status-box success">
          <img src="../assets/icons/success.svg" class="status-icon" alt="success" />
          <span>Nginx已载入</span>
        </div>

        <div v-else-if="nginxStatus === 'skipped'" class="status-box info">
          <img src="../assets/icons/info.svg" class="status-icon" alt="info" />
          <span>已跳过Nginx配置，稍后可在设置中配置</span>
        </div>

        <div v-else class="nginx-options">
          <!-- 手动载入选项 - 仅Windows支持 -->
          <div v-if="supportsNginxManualLoad" class="option-group">
            <h3>选项1: 手动载入</h3>
            <p class="option-desc">如果您已安装Nginx，请选择可执行文件</p>
            <Button type="secondary" :loading="isLoading" @click="loadNginxManually">
              选择Nginx文件
            </Button>
          </div>

          <div v-if="supportsNginxManualLoad && supportsNginxDownload" class="option-divider">或</div>

          <!-- 自动下载选项 - 仅Windows支持 -->
          <div v-if="supportsNginxDownload" class="option-group">
            <h3>选项2: 自动下载</h3>
            <p class="option-desc">自动下载并配置Nginx（推荐）</p>
            <input
              v-model="nginxDownloadUrl"
              type="text"
              class="url-input"
              placeholder="下载地址"
            />
            <Button
              type="primary"
              :loading="isNginxDownloading"
              @click="downloadNginx"
            >
              下载并配置
            </Button>
          </div>

          <!-- Linux平台提示 -->
          <div v-if="!supportsNginxManualLoad && !supportsNginxDownload" class="option-group">
            <h3>Nginx配置</h3>
            <p class="option-desc">
              在Linux系统上，Nginx通过包管理器安装和管理{{ nginxPlatformDisplayText }}
            </p>
            <p class="option-desc">
              请使用系统包管理器安装Nginx，系统将自动检测并使用系统Nginx。
            </p>
          </div>
        </div>

        <div v-if="nginxStatus !== 'loaded'" class="action-row">
          <Button type="secondary" @click="skipNginx">
            跳过此步骤
          </Button>
        </div>
      </div>

      <!-- 步骤3: Git检查 -->
      <div v-if="currentStep === 3" class="step-content">
        <h2 class="step-heading">检查Git环境</h2>
        <p class="step-text">Git是服务端HTTP服务的必需依赖</p>

        <div v-if="gitStatus === 'checking'" class="status-box">
          <span class="loading-text">正在检查Git安装...</span>
        </div>

        <div v-else-if="gitStatus === 'installed'" class="status-box success">
          <img src="../assets/icons/success.svg" class="status-icon" alt="success" />
          <span>Git已安装: {{ gitVersion }}</span>
        </div>

        <div v-else class="status-box error">
          <img src="../assets/icons/error.svg" class="status-icon" alt="error" />
          <div>
            <div>未检测到Git安装</div>
            <div class="install-help">
              请访问 <a href="https://git-scm.com/downloads" target="_blank">git-scm.com</a> 下载安装
            </div>
          </div>
        </div>

        <div class="action-row">
          <Button
            type="secondary"
            @click="checkGit"
            :disabled="gitStatus === 'checking'"
          >
            重新检查
          </Button>
          <Button
            v-if="gitStatus === 'not_installed'"
            type="warning"
            @click="skipGit"
          >
            跳过（不推荐）
          </Button>
        </div>
      </div>

      <!-- 步骤4: 用户偏好 -->
      <div v-if="currentStep === 4" class="step-content">
        <h2 class="step-heading">个性化设置</h2>
        <p class="step-text">选择您喜欢的主题和布局样式</p>

        <div class="preference-section">
          <h3>颜色主题</h3>
          <div class="theme-grid">
            <div
              v-for="theme in presetColorThemes"
              :key="theme.id"
              class="theme-option"
              :class="{ 'theme-selected': selectedTheme === theme.id }"
              @click="selectTheme(theme.id)"
            >
              <div
                class="theme-preview"
                :style="{ backgroundColor: theme.previewColor }"
              />
              <div class="theme-name">{{ theme.name }}</div>
            </div>
          </div>
        </div>

        <div class="preference-section">
          <h3>布局密度</h3>
          <div class="layout-options">
            <Button
              v-for="layout in layoutDensityPresets"
              :key="layout.id"
              :type="selectedLayout === layout.id ? 'primary' : 'secondary'"
              size="sm"
              @click="selectLayout(layout.id)"
            >
              {{ layout.name }}
            </Button>
          </div>
        </div>

        <div class="preference-section security-section">
          <h3>安全设置 <span class="required-badge">必填</span></h3>
          <p class="section-desc">设置安全密码以保护敏感配置，密码长度至少6位</p>
          <div class="security-form">
            <div class="form-group">
              <label class="form-label">安全密码 <span class="required">*</span></label>
              <input
                v-model="securityPassword"
                type="password"
                class="input"
                :class="{ 'input-error': securityPassword && securityPassword.length < 6 }"
                placeholder="设置安全密码（至少6位）"
              />
              <p v-if="securityPassword && securityPassword.length < 6" class="error-text">
                密码长度至少为6位
              </p>
            </div>
            <div class="form-group">
              <label class="form-label">确认密码 <span class="required">*</span></label>
              <input
                v-model="confirmPassword"
                type="password"
                class="input"
                :class="{ 'input-error': confirmPassword && confirmPassword !== securityPassword }"
                placeholder="再次输入安全密码"
              />
              <p v-if="confirmPassword && confirmPassword !== securityPassword" class="error-text">
                两次输入的密码不一致
              </p>
            </div>
          </div>
        </div>
      </div>

      <!-- 底部导航 -->
      <template #footer>
        <div class="guide-footer">
          <Button
            v-if="!isFirstStep"
            type="secondary"
            @click="prevStep"
          >
            上一步
          </Button>
          <div class="spacer" />
          <Button
            v-if="!isLastStep"
            type="primary"
            :disabled="!canProceed"
            @click="nextStep"
          >
            下一步
          </Button>
          <Button
            v-else
            type="success"
            :loading="isLoading"
            @click="savePreferences"
          >
            完成设置
          </Button>
        </div>
      </template>
    </Card>
  </div>
</template>

<style scoped>
/* 容器布局 - 使用现有变量 */
.guide-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-start;
  min-height: 100vh;
  padding: var(--spacing-xl);
  background-color: var(--bg-primary);
  overflow-y: auto;
}

/* 步骤指示器 - 简化设计 */
.step-indicator {
  display: flex;
  align-items: flex-start;
  gap: var(--spacing-lg);
  margin-bottom: var(--spacing-xl);
  max-width: 800px;
  width: 100%;
}

.step-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  flex: 1;
  position: relative;
}

.step-number {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background-color: var(--bg-tertiary);
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: var(--font-size-sm);
  flex-shrink: 0;
}

.step-active .step-number {
  background-color: var(--primary-color);
  color: white;
}

.step-completed .step-number {
  background-color: var(--success-color);
  color: white;
}

.step-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.step-title {
  font-size: var(--font-size-sm);
  font-weight: 500;
  color: var(--text-primary);
}

.step-desc {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
}

.step-line {
  flex: 1;
  height: 1px;
  background-color: var(--border-color);
  margin: 0 var(--spacing-sm);
  margin-top: 16px;
}

/* 卡片样式 */
.guide-card {
  width: 100%;
  max-width: 600px;
  display: flex;
  flex-direction: column;
  max-height: calc(100vh - 180px);
}

.guide-card :deep(.card-body) {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
  max-height: calc(100vh - 280px);
}

/* 步骤内容 */
.step-content {
  padding: var(--spacing-lg);
}

.step-heading {
  font-size: var(--font-size-xl);
  font-weight: 600;
  margin-bottom: var(--spacing-sm);
  color: var(--text-primary);
}

.step-text {
  color: var(--text-secondary);
  margin-bottom: var(--spacing-lg);
}

/* 状态框 - 复用现有颜色变量 */
.status-box {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-md);
  border-radius: var(--border-radius-md);
  background-color: var(--bg-tertiary);
  margin-bottom: var(--spacing-lg);
}

.status-box.success {
  background-color: rgba(16, 185, 129, 0.1);
  border: 1px solid var(--success-color);
}

.status-box.warning {
  background-color: rgba(245, 158, 11, 0.1);
  border: 1px solid var(--warning-color);
}

.status-box.error {
  background-color: rgba(239, 68, 68, 0.1);
  border: 1px solid var(--error-color);
}

.status-box.info {
  background-color: rgba(6, 182, 212, 0.1);
  border: 1px solid var(--info-color);
}

.status-icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
}

.loading-text {
  color: var(--text-secondary);
}

/* 操作行 */
.action-row {
  display: flex;
  gap: var(--spacing-sm);
}

/* Nginx选项 */
.nginx-options {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
  margin-bottom: var(--spacing-lg);
}

.option-group {
  padding: var(--spacing-md);
  background-color: var(--bg-tertiary);
  border-radius: var(--border-radius-md);
}

.option-group h3 {
  font-size: var(--font-size-md);
  margin-bottom: var(--spacing-xs);
}

.option-desc {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  margin-bottom: var(--spacing-md);
}

.option-divider {
  text-align: center;
  color: var(--text-tertiary);
  font-size: var(--font-size-sm);
}

.url-input {
  width: 100%;
  padding: var(--spacing-sm);
  margin-bottom: var(--spacing-sm);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius-md);
  background-color: var(--bg-secondary);
  color: var(--text-primary);
  font-size: var(--font-size-sm);
}

.url-input:focus {
  outline: none;
  border-color: var(--primary-color);
}

/* Git安装帮助 */
.install-help {
  margin-top: var(--spacing-xs);
  font-size: var(--font-size-sm);
}

.install-help a {
  color: var(--primary-color);
  text-decoration: none;
}

.install-help a:hover {
  text-decoration: underline;
}

/* 偏好设置 */
.preference-section {
  margin-bottom: var(--spacing-lg);
}

.preference-section h3 {
  font-size: var(--font-size-md);
  margin-bottom: var(--spacing-md);
  color: var(--text-primary);
}

.theme-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--spacing-md);
}

.theme-option {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-md);
  border-radius: var(--border-radius-md);
  cursor: pointer;
  border: 2px solid transparent;
  transition: border-color var(--transition-fast);
}

.theme-option:hover {
  background-color: var(--bg-tertiary);
}

.theme-selected {
  border-color: var(--primary-color);
  background-color: var(--bg-tertiary);
}

.theme-preview {
  width: 40px;
  height: 40px;
  border-radius: 50%;
}

.theme-name {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}

.layout-options {
  display: flex;
  gap: var(--spacing-sm);
  flex-wrap: wrap;
}

/* 安全设置区域 */
.security-section {
  background-color: var(--bg-tertiary);
  padding: var(--spacing-lg);
  border-radius: var(--border-radius-md);
  border: 1px solid var(--warning-color);
}

.security-section h3 {
  color: var(--warning-color);
  margin-bottom: var(--spacing-sm);
}

.section-desc {
  color: var(--text-secondary);
  font-size: var(--font-size-sm);
  margin-bottom: var(--spacing-md);
}

.security-form {
  max-width: 400px;
}

.security-form .form-group {
  margin-bottom: var(--spacing-md);
}

.security-form .form-label {
  display: block;
  margin-bottom: var(--spacing-xs);
  color: var(--text-secondary);
  font-size: var(--font-size-sm);
}

.security-form .input {
  width: 100%;
  padding: var(--spacing-sm);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius-md);
  background-color: var(--bg-secondary);
  color: var(--text-primary);
  font-size: var(--font-size-sm);
}

.security-form .input:focus {
  outline: none;
  border-color: var(--primary-color);
}

.security-form .input-error {
  border-color: var(--error-color);
}

.security-form .input-error:focus {
  border-color: var(--error-color);
  box-shadow: 0 0 0 2px rgba(239, 68, 68, 0.2);
}

.required {
  color: var(--error-color);
}

.required-badge {
  display: inline-block;
  padding: 2px 8px;
  background-color: var(--error-color);
  color: white;
  font-size: var(--font-size-xs);
  border-radius: var(--border-radius-sm);
  margin-left: var(--spacing-sm);
  font-weight: normal;
}

.error-text {
  color: var(--error-color);
  font-size: var(--font-size-xs);
  margin-top: var(--spacing-xs);
}

/* 底部导航 */
.guide-footer {
  display: flex;
  align-items: center;
  padding: var(--spacing-md) var(--spacing-lg);
  border-top: 1px solid var(--border-color);
}

.spacer {
  flex: 1;
}
</style>
