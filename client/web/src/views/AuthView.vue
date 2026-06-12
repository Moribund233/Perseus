<script setup lang="ts">
/**
 * 登录/注册页面
 * 使用 Tab 切换登录和注册表单
 */
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  User,
  Lock,
  Message,
  View,
  Hide,
  ArrowLeft,
  Check,
} from '@element-plus/icons-vue'
import { authApi, api, ApiClientError } from '@/api'

const route = useRoute()
const router = useRouter()

/**
 * 当前激活的 Tab
 */
const activeTab = computed({
  get: () => (route.query.tab as string) || 'login',
  set: (value: string) => {
    router.replace({ query: { ...route.query, tab: value } })
  },
})

/**
 * 登录表单数据
 */
const loginForm = ref({
  username: '',
  password: '',
  rememberMe: false,
})

/**
 * 注册表单数据
 */
const registerForm = ref({
  username: '',
  email: '',
  password: '',
  confirmPassword: '',
  agreeTerms: false,
})

/**
 * 密码可见性
 */
const showLoginPassword = ref(false)
const showRegisterPassword = ref(false)
const showConfirmPassword = ref(false)

/**
 * 登录表单引用
 */
const loginFormRef = ref()

/**
 * 注册表单引用
 */
const registerFormRef = ref()

/**
 * 登录表单验证规则
 */
const loginRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于 6 位', trigger: 'blur' },
  ],
}

/**
 * 注册表单验证规则
 */
const registerRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '用户名长度应在 3-20 个字符之间', trigger: 'blur' },
  ],
  email: [
    { required: true, message: '请输入邮箱地址', trigger: 'blur' },
    { type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 8, message: '密码长度不能少于 8 位', trigger: 'blur' },
  ],
  confirmPassword: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    {
      validator: (rule: any, value: string, callback: Function) => {
        if (value !== registerForm.value.password) {
          callback(new Error('两次输入的密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur',
    },
  ],
  agreeTerms: [
    {
      validator: (rule: any, value: boolean, callback: Function) => {
        if (!value) {
          callback(new Error('请同意服务条款和隐私政策'))
        } else {
          callback()
        }
      },
      trigger: 'change',
    },
  ],
}

/**
 * 登录加载状态
 */
const loginLoading = ref(false)

/**
 * 注册加载状态
 */
const registerLoading = ref(false)

/**
 * 处理登录
 */
const handleLogin = async () => {
  if (!loginFormRef.value) return

  try {
    await loginFormRef.value.validate()
    loginLoading.value = true

    const res = await authApi.login({
      username: loginForm.value.username,
      password: loginForm.value.password,
    })
    api.setTokens(res.access_token, res.refresh_token)
    ElMessage.success('登录成功')
    router.push('/dashboard')
  } catch (error) {
    if (error instanceof ApiClientError) {
      ElMessage.error(error.message)
    } else if (error instanceof Error) {
      ElMessage.error('登录失败：' + error.message)
    } else {
      ElMessage.error('登录失败，请重试')
    }
  } finally {
    loginLoading.value = false
  }
}

/**
 * 处理注册
 */
const handleRegister = async () => {
  if (!registerFormRef.value) return

  try {
    await registerFormRef.value.validate()
    registerLoading.value = true

    await authApi.register({
      username: registerForm.value.username,
      email: registerForm.value.email,
      password: registerForm.value.password,
    })
    ElMessage.success('注册成功，请登录')
    activeTab.value = 'login'
    registerForm.value = {
      username: '',
      email: '',
      password: '',
      confirmPassword: '',
      agreeTerms: false,
    }
  } catch (error) {
    if (error instanceof ApiClientError) {
      ElMessage.error(error.message)
    } else if (error instanceof Error) {
      ElMessage.error('注册失败：' + error.message)
    } else {
      ElMessage.error('注册失败，请重试')
    }
  } finally {
    registerLoading.value = false
  }
}

/**
 * 第三方登录选项
 */
const oauthProviders = [
  { name: 'GitHub', icon: 'github' },
  { name: 'Google', icon: 'google' },
  { name: 'GitLab', icon: 'gitlab' },
]

/**
 * 处理第三方登录
 */
const handleOAuth = (provider: string) => {
  console.log('第三方登录:', provider)
  // TODO: 实现 OAuth 登录
}
</script>

<template>
  <div class="auth-page">
    <!-- 背景装饰 -->
    <div class="auth-bg">
      <div class="bg-shape shape-1" />
      <div class="bg-shape shape-2" />
    </div>

    <!-- 返回首页 -->
    <router-link to="/" class="back-link">
      <el-icon><ArrowLeft /></el-icon>
      返回首页
    </router-link>

    <!-- 主要内容 -->
    <div class="auth-container">
      <!-- 左侧品牌区域 -->
      <div class="brand-section">
        <div class="brand-content">
          <div class="brand-logo">
            <svg viewBox="0 0 24 24" width="48" height="48" fill="currentColor">
              <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
            </svg>
          </div>
          <h1 class="brand-name">Perseus</h1>
          <p class="brand-tagline">现代代码托管平台</p>
          <div class="brand-features">
            <div class="feature-item">
              <el-icon><Check /></el-icon>
              <span>免费开源</span>
            </div>
            <div class="feature-item">
              <el-icon><Check /></el-icon>
              <span>无限仓库</span>
            </div>
            <div class="feature-item">
              <el-icon><Check /></el-icon>
              <span>团队协作</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧表单区域 -->
      <div class="form-section">
        <div class="form-card">
          <!-- Tab 切换 -->
          <div class="auth-tabs">
            <button
              class="tab-btn"
              :class="{ 'is-active': activeTab === 'login' }"
              @click="activeTab = 'login'"
            >
              登录
            </button>
            <button
              class="tab-btn"
              :class="{ 'is-active': activeTab === 'register' }"
              @click="activeTab = 'register'"
            >
              注册
            </button>
          </div>

          <!-- 登录表单 -->
          <div v-show="activeTab === 'login'" class="tab-panel">
            <el-form
              ref="loginFormRef"
              :model="loginForm"
              :rules="loginRules"
              class="auth-form"
              @keyup.enter="handleLogin"
            >
              <el-form-item prop="username">
                <el-input
                  v-model="loginForm.username"
                  placeholder="用户名"
                  :prefix-icon="User"
                  size="large"
                />
              </el-form-item>

              <el-form-item prop="password">
                <el-input
                  v-model="loginForm.password"
                  :type="showLoginPassword ? 'text' : 'password'"
                  placeholder="密码"
                  :prefix-icon="Lock"
                  size="large"
                >
                  <template #suffix>
                    <el-icon
                      class="password-toggle"
                      @click="showLoginPassword = !showLoginPassword"
                    >
                      <View v-if="showLoginPassword" />
                      <Hide v-else />
                    </el-icon>
                  </template>
                </el-input>
              </el-form-item>

              <div class="form-options">
                <el-checkbox v-model="loginForm.rememberMe">
                  记住我
                </el-checkbox>
                <span class="forgot-link disabled">
                  忘记密码？
                </span>
              </div>

              <el-button
                type="primary"
                size="large"
                class="submit-btn"
                :loading="loginLoading"
                @click="handleLogin"
              >
                登录
              </el-button>
            </el-form>

            <!-- 第三方登录 -->
            <div class="oauth-section">
              <div class="oauth-divider">
                <span>或使用以下方式登录</span>
              </div>
              <div class="oauth-buttons">
                <button
                  v-for="provider in oauthProviders"
                  :key="provider.name"
                  class="oauth-btn"
                  @click="handleOAuth(provider.name)"
                >
                  {{ provider.name }}
                </button>
              </div>
            </div>
          </div>

          <!-- 注册表单 -->
          <div v-show="activeTab === 'register'" class="tab-panel">
            <el-form
              ref="registerFormRef"
              :model="registerForm"
              :rules="registerRules"
              class="auth-form"
              @keyup.enter="handleRegister"
            >
              <el-form-item prop="username">
                <el-input
                  v-model="registerForm.username"
                  placeholder="用户名"
                  :prefix-icon="User"
                  size="large"
                />
              </el-form-item>

              <el-form-item prop="email">
                <el-input
                  v-model="registerForm.email"
                  placeholder="邮箱地址"
                  :prefix-icon="Message"
                  size="large"
                />
              </el-form-item>

              <el-form-item prop="password">
                <el-input
                  v-model="registerForm.password"
                  :type="showRegisterPassword ? 'text' : 'password'"
                  placeholder="密码"
                  :prefix-icon="Lock"
                  size="large"
                >
                  <template #suffix>
                    <el-icon
                      class="password-toggle"
                      @click="showRegisterPassword = !showRegisterPassword"
                    >
                      <View v-if="showRegisterPassword" />
                      <Hide v-else />
                    </el-icon>
                  </template>
                </el-input>
              </el-form-item>

              <el-form-item prop="confirmPassword">
                <el-input
                  v-model="registerForm.confirmPassword"
                  :type="showConfirmPassword ? 'text' : 'password'"
                  placeholder="确认密码"
                  :prefix-icon="Lock"
                  size="large"
                >
                  <template #suffix>
                    <el-icon
                      class="password-toggle"
                      @click="showConfirmPassword = !showConfirmPassword"
                    >
                      <View v-if="showConfirmPassword" />
                      <Hide v-else />
                    </el-icon>
                  </template>
                </el-input>
              </el-form-item>

              <el-form-item prop="agreeTerms">
                <el-checkbox v-model="registerForm.agreeTerms">
                  我已阅读并同意
                  <span class="terms-link disabled">服务条款</span>
                  和
                  <span class="terms-link disabled">隐私政策</span>
                </el-checkbox>
              </el-form-item>

              <el-button
                type="primary"
                size="large"
                class="submit-btn"
                :loading="registerLoading"
                @click="handleRegister"
              >
                注册
              </el-button>
            </el-form>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.auth-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--perseus-surface);
  position: relative;
  overflow: hidden;
}

/* 背景装饰 */
.auth-bg {
  position: absolute;
  inset: 0;
  overflow: hidden;
  pointer-events: none;
}

.bg-shape {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.5;
}

.shape-1 {
  width: 600px;
  height: 600px;
  background: linear-gradient(135deg, #e0e0e0 0%, #f5f5f5 100%);
  top: -200px;
  right: -200px;
}

.shape-2 {
  width: 400px;
  height: 400px;
  background: linear-gradient(135deg, #f5f5f5 0%, #e0e0e0 100%);
  bottom: -100px;
  left: -100px;
}

/* 返回链接 */
.back-link {
  position: absolute;
  top: var(--perseus-space-6);
  left: var(--perseus-space-6);
  display: flex;
  align-items: center;
  gap: var(--perseus-space-2);
  color: var(--perseus-fg-2);
  font-size: var(--perseus-text-sm);
  text-decoration: none;
  transition: color var(--perseus-motion-fast);
}

.back-link:hover {
  color: var(--perseus-fg);
}

/* 主容器 */
.auth-container {
  display: flex;
  width: 100%;
  max-width: 1000px;
  min-height: 600px;
  background: var(--perseus-bg);
  border-radius: var(--perseus-radius-lg);
  box-shadow: var(--perseus-elev-raised);
  overflow: hidden;
  margin: var(--perseus-space-8);
  position: relative;
  z-index: 1;
}

/* 品牌区域 */
.brand-section {
  flex: 1;
  background: var(--perseus-fg);
  color: var(--perseus-accent-on);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--perseus-space-10);
}

.brand-content {
  text-align: center;
}

.brand-logo {
  margin-bottom: var(--perseus-space-4);
}

.brand-name {
  font-size: var(--perseus-text-2xl);
  font-weight: 700;
  letter-spacing: var(--perseus-tracking-display);
  margin-bottom: var(--perseus-space-2);
}

.brand-tagline {
  font-size: var(--perseus-text-base);
  color: rgba(255, 255, 255, 0.7);
  margin-bottom: var(--perseus-space-8);
}

.brand-features {
  display: flex;
  flex-direction: column;
  gap: var(--perseus-space-3);
}

.feature-item {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--perseus-space-2);
  font-size: var(--perseus-text-sm);
  color: rgba(255, 255, 255, 0.8);
}

.feature-item .el-icon {
  color: var(--perseus-success);
}

/* 表单区域 */
.form-section {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--perseus-space-10);
}

.form-card {
  width: 100%;
  max-width: 360px;
}

/* Tab 切换 */
.auth-tabs {
  display: flex;
  gap: var(--perseus-space-6);
  margin-bottom: var(--perseus-space-8);
  border-bottom: 2px solid var(--perseus-border-soft);
}

.tab-btn {
  padding: var(--perseus-space-3) 0;
  border: none;
  background: transparent;
  color: var(--perseus-muted);
  font-size: var(--perseus-text-lg);
  font-weight: 600;
  cursor: pointer;
  position: relative;
  transition: color var(--perseus-motion-fast);
}

.tab-btn:hover {
  color: var(--perseus-fg);
}

.tab-btn.is-active {
  color: var(--perseus-fg);
}

.tab-btn.is-active::after {
  content: '';
  position: absolute;
  bottom: -2px;
  left: 0;
  right: 0;
  height: 2px;
  background: var(--perseus-accent);
}

/* 表单样式 */
.auth-form :deep(.el-form-item) {
  margin-bottom: var(--perseus-space-4);
}

.auth-form :deep(.el-input__wrapper) {
  border-radius: var(--perseus-radius-md);
  box-shadow: 0 0 0 1px var(--perseus-border) inset;
}

.auth-form :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px var(--perseus-accent) inset;
}

.password-toggle {
  cursor: pointer;
  color: var(--perseus-muted);
  transition: color var(--perseus-motion-fast);
}

.password-toggle:hover {
  color: var(--perseus-fg);
}

.form-options {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--perseus-space-6);
}

.forgot-link {
  font-size: var(--perseus-text-sm);
  color: var(--perseus-accent);
  text-decoration: none;
}

.forgot-link:hover {
  text-decoration: underline;
}

.forgot-link.disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.terms-link {
  color: var(--perseus-accent);
  text-decoration: none;
}

.terms-link:hover {
  text-decoration: underline;
}

.terms-link.disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.submit-btn {
  width: 100%;
  border-radius: var(--perseus-radius-md);
  font-weight: 600;
}

/* 第三方登录 */
.oauth-section {
  margin-top: var(--perseus-space-8);
}

.oauth-divider {
  display: flex;
  align-items: center;
  gap: var(--perseus-space-3);
  margin-bottom: var(--perseus-space-5);
}

.oauth-divider::before,
.oauth-divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--perseus-border-soft);
}

.oauth-divider span {
  font-size: var(--perseus-text-xs);
  color: var(--perseus-muted);
}

.oauth-buttons {
  display: flex;
  gap: var(--perseus-space-3);
}

.oauth-btn {
  flex: 1;
  padding: var(--perseus-space-3) var(--perseus-space-4);
  border: 1px solid var(--perseus-border);
  background: var(--perseus-bg);
  color: var(--perseus-fg-2);
  font-size: var(--perseus-text-sm);
  border-radius: var(--perseus-radius-md);
  cursor: pointer;
  transition: all var(--perseus-motion-fast);
}

.oauth-btn:hover {
  border-color: var(--perseus-accent);
  color: var(--perseus-fg);
}

/* 响应式 */
@media (max-width: 768px) {
  .auth-container {
    flex-direction: column;
    margin: var(--perseus-space-4);
    min-height: auto;
  }

  .brand-section {
    padding: var(--perseus-space-8) var(--perseus-space-6);
  }

  .brand-features {
    flex-direction: row;
    justify-content: center;
    flex-wrap: wrap;
  }

  .form-section {
    padding: var(--perseus-space-6);
  }

  .back-link {
    top: var(--perseus-space-4);
    left: var(--perseus-space-4);
  }
}

@media (max-width: 480px) {
  .brand-section {
    display: none;
  }

  .auth-container {
    margin: 0;
    border-radius: 0;
    min-height: 100vh;
  }

  .form-section {
    padding: var(--perseus-space-8) var(--perseus-space-5);
  }
}
</style>
