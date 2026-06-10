<script setup lang="ts">
/**
 * 设置页面
 * 用户账户设置、偏好设置、安全设置等
 */
import { ref } from 'vue'
import SidebarLayout from '@/components/layouts/SidebarLayout.vue'
import {
  User,
  Lock,
  Bell,
  Connection,
  Brush,
  Check,
} from '@element-plus/icons-vue'

/**
 * 设置菜单项
 */
const settingMenus = [
  { key: 'profile', icon: User, label: '个人资料' },
  { key: 'account', icon: Lock, label: '账户安全' },
  { key: 'notifications', icon: Bell, label: '通知设置' },
  { key: 'integrations', icon: Connection, label: '集成服务' },
  { key: 'appearance', icon: Brush, label: '外观设置' },
]

/**
 * 当前激活的设置菜单
 */
const activeMenu = ref('profile')

/**
 * 个人资料表单数据
 */
const profileForm = ref({
  username: 'alex',
  displayName: 'Alex Chen',
  email: 'alex@example.com',
  bio: 'Full-stack developer passionate about open source.',
  website: 'https://alexchen.dev',
  location: 'Shanghai, China',
  company: 'Perseus',
})

/**
 * 账户安全表单数据
 */
const securityForm = ref({
  currentPassword: '',
  newPassword: '',
  confirmPassword: '',
  twoFactorEnabled: true,
  twoFactorMethod: 'authenticator',
})

/**
 * 通知设置
 */
const notificationSettings = ref({
  emailNotifications: true,
  pushNotifications: false,
  mentionNotifications: true,
  prReviewNotifications: true,
  ciNotifications: false,
  marketingEmails: false,
})

/**
 * 集成服务列表
 */
const integrations = ref([
  {
    id: 'github',
    name: 'GitHub',
    description: '同步 GitHub 仓库',
    icon: '🔗',
    connected: true,
    connectedAt: '2026-01-15',
  },
  {
    id: 'gitlab',
    name: 'GitLab',
    description: '同步 GitLab 仓库',
    icon: '🔗',
    connected: false,
  },
  {
    id: 'slack',
    name: 'Slack',
    description: '接收通知到 Slack',
    icon: '💬',
    connected: true,
    connectedAt: '2026-02-20',
  },
  {
    id: 'vscode',
    name: 'VS Code',
    description: 'VS Code 扩展集成',
    icon: '📝',
    connected: false,
  },
])

/**
 * 外观设置
 */
const appearanceSettings = ref({
  theme: 'light',
  language: 'zh-CN',
  codeFont: 'JetBrains Mono',
  tabSize: 2,
  lineNumbers: true,
  wordWrap: true,
  minimap: false,
})

/**
 * 保存个人资料
 */
const saveProfile = () => {
  // TODO: 调用 API 保存个人资料
  console.log('Saving profile:', profileForm.value)
}

/**
 * 保存安全设置
 */
const saveSecurity = () => {
  // TODO: 调用 API 保存安全设置
  console.log('Saving security settings:', securityForm.value)
}

/**
 * 保存通知设置
 */
const saveNotifications = () => {
  // TODO: 调用 API 保存通知设置
  console.log('Saving notification settings:', notificationSettings.value)
}

/**
 * 连接/断开集成服务
 * @param integrationId 集成服务 ID
 */
const toggleIntegration = (integrationId: string) => {
  const integration = integrations.value.find(i => i.id === integrationId)
  if (integration) {
    integration.connected = !integration.connected
    if (integration.connected) {
      integration.connectedAt = new Date().toISOString().split('T')[0]
    }
  }
}

/**
 * 保存外观设置
 */
const saveAppearance = () => {
  // TODO: 调用 API 保存外观设置
  console.log('Saving appearance settings:', appearanceSettings.value)
}
</script>

<template>
  <SidebarLayout>
    <div class="settings-page">
      <div class="settings-container">
        <!-- 页面标题 -->
        <header class="page-header">
          <h1 class="page-title">设置</h1>
          <p class="page-subtitle">管理你的账户设置和偏好</p>
        </header>

        <div class="settings-layout">
          <!-- 左侧菜单 -->
          <aside class="settings-sidebar">
            <nav class="settings-nav">
              <button
                v-for="menu in settingMenus"
                :key="menu.key"
                class="settings-nav-item"
                :class="{ 'is-active': activeMenu === menu.key }"
                @click="activeMenu = menu.key"
              >
                <el-icon class="nav-icon">
                  <component :is="menu.icon" />
                </el-icon>
                <span class="nav-label">{{ menu.label }}</span>
              </button>
            </nav>
          </aside>

          <!-- 右侧内容区 -->
          <main class="settings-content">
            <!-- 个人资料设置 -->
            <section v-if="activeMenu === 'profile'" class="settings-section">
              <h2 class="section-title">个人资料</h2>
              <p class="section-description">管理你的公开个人资料信息</p>

              <div class="avatar-section">
                <div class="avatar-preview">
                  <span class="avatar-text">AC</span>
                </div>
                <div class="avatar-actions">
                  <el-button type="primary">更换头像</el-button>
                  <el-button text>删除头像</el-button>
                </div>
              </div>

              <el-form :model="profileForm" label-position="top" class="settings-form">
                <el-row :gutter="24">
                  <el-col :span="12">
                    <el-form-item label="用户名">
                      <el-input v-model="profileForm.username" disabled>
                        <template #prepend>@</template>
                      </el-input>
                    </el-form-item>
                  </el-col>
                  <el-col :span="12">
                    <el-form-item label="显示名称">
                      <el-input v-model="profileForm.displayName" />
                    </el-form-item>
                  </el-col>
                </el-row>

                <el-form-item label="个人简介">
                  <el-input
                    v-model="profileForm.bio"
                    type="textarea"
                    :rows="3"
                    placeholder="介绍一下你自己..."
                  />
                </el-form-item>

                <el-row :gutter="24">
                  <el-col :span="12">
                    <el-form-item label="邮箱">
                      <el-input v-model="profileForm.email" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="12">
                    <el-form-item label="网站">
                      <el-input v-model="profileForm.website" />
                    </el-form-item>
                  </el-col>
                </el-row>

                <el-row :gutter="24">
                  <el-col :span="12">
                    <el-form-item label="位置">
                      <el-input v-model="profileForm.location" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="12">
                    <el-form-item label="公司">
                      <el-input v-model="profileForm.company" />
                    </el-form-item>
                  </el-col>
                </el-row>

                <div class="form-actions">
                  <el-button type="primary" @click="saveProfile">
                    保存更改
                  </el-button>
                </div>
              </el-form>
            </section>

            <!-- 账户安全设置 -->
            <section v-if="activeMenu === 'account'" class="settings-section">
              <h2 class="section-title">账户安全</h2>
              <p class="section-description">管理你的密码和双因素认证</p>

              <div class="security-section">
                <h3 class="subsection-title">修改密码</h3>
                <el-form :model="securityForm" label-position="top" class="settings-form">
                  <el-form-item label="当前密码">
                    <el-input v-model="securityForm.currentPassword" type="password" show-password />
                  </el-form-item>
                  <el-form-item label="新密码">
                    <el-input v-model="securityForm.newPassword" type="password" show-password />
                  </el-form-item>
                  <el-form-item label="确认新密码">
                    <el-input v-model="securityForm.confirmPassword" type="password" show-password />
                  </el-form-item>
                  <div class="form-actions">
                    <el-button type="primary" @click="saveSecurity">更新密码</el-button>
                  </div>
                </el-form>
              </div>

              <el-divider />

              <div class="security-section">
                <h3 class="subsection-title">双因素认证 (2FA)</h3>
                <div class="two-factor-status">
                  <div class="status-icon" :class="{ 'is-enabled': securityForm.twoFactorEnabled }">
                    <el-icon v-if="securityForm.twoFactorEnabled"><Check /></el-icon>
                    <span v-else>×</span>
                  </div>
                  <div class="status-info">
                    <p class="status-title">
                      {{ securityForm.twoFactorEnabled ? '已启用' : '未启用' }}
                    </p>
                    <p class="status-desc">
                      {{ securityForm.twoFactorEnabled
                        ? '你的账户已启用双因素认证，更加安全。'
                        : '启用双因素认证可以提高账户安全性。' }}
                    </p>
                  </div>
                  <el-button
                    :type="securityForm.twoFactorEnabled ? 'danger' : 'primary'"
                    @click="securityForm.twoFactorEnabled = !securityForm.twoFactorEnabled"
                  >
                    {{ securityForm.twoFactorEnabled ? '禁用' : '启用' }}
                  </el-button>
                </div>
              </div>

              <el-divider />

              <div class="security-section danger-zone">
                <h3 class="subsection-title danger-title">危险区域</h3>
                <div class="danger-item">
                  <div class="danger-info">
                    <p class="danger-name">删除账户</p>
                    <p class="danger-desc">删除账户将永久移除所有数据，此操作无法撤销。</p>
                  </div>
                  <el-button type="danger">删除账户</el-button>
                </div>
              </div>
            </section>

            <!-- 通知设置 -->
            <section v-if="activeMenu === 'notifications'" class="settings-section">
              <h2 class="section-title">通知设置</h2>
              <p class="section-description">选择你希望接收的通知类型</p>

              <div class="notification-group">
                <h3 class="subsection-title">邮件通知</h3>
                <div class="notification-items">
                  <div class="notification-item">
                    <div class="notification-info">
                      <p class="notification-name">邮件通知</p>
                      <p class="notification-desc">接收重要更新的邮件通知</p>
                    </div>
                    <el-switch v-model="notificationSettings.emailNotifications" />
                  </div>
                  <div class="notification-item">
                    <div class="notification-info">
                      <p class="notification-name">营销邮件</p>
                      <p class="notification-desc">接收产品更新和促销信息</p>
                    </div>
                    <el-switch v-model="notificationSettings.marketingEmails" />
                  </div>
                </div>
              </div>

              <el-divider />

              <div class="notification-group">
                <h3 class="subsection-title">推送通知</h3>
                <div class="notification-items">
                  <div class="notification-item">
                    <div class="notification-info">
                      <p class="notification-name">浏览器推送</p>
                      <p class="notification-desc">在浏览器中接收实时通知</p>
                    </div>
                    <el-switch v-model="notificationSettings.pushNotifications" />
                  </div>
                </div>
              </div>

              <el-divider />

              <div class="notification-group">
                <h3 class="subsection-title">仓库活动</h3>
                <div class="notification-items">
                  <div class="notification-item">
                    <div class="notification-info">
                      <p class="notification-name">提及通知</p>
                      <p class="notification-desc">当有人在评论中提及你时通知</p>
                    </div>
                    <el-switch v-model="notificationSettings.mentionNotifications" />
                  </div>
                  <div class="notification-item">
                    <div class="notification-info">
                      <p class="notification-name">PR 审查</p>
                      <p class="notification-desc">当有人请求你审查 PR 时通知</p>
                    </div>
                    <el-switch v-model="notificationSettings.prReviewNotifications" />
                  </div>
                  <div class="notification-item">
                    <div class="notification-info">
                      <p class="notification-name">CI/CD 状态</p>
                      <p class="notification-desc">当构建或部署完成时通知</p>
                    </div>
                    <el-switch v-model="notificationSettings.ciNotifications" />
                  </div>
                </div>
              </div>

              <div class="form-actions">
                <el-button type="primary" @click="saveNotifications">
                  保存设置
                </el-button>
              </div>
            </section>

            <!-- 集成服务 -->
            <section v-if="activeMenu === 'integrations'" class="settings-section">
              <h2 class="section-title">集成服务</h2>
              <p class="section-description">连接第三方服务以扩展功能</p>

              <div class="integrations-list">
                <div
                  v-for="integration in integrations"
                  :key="integration.id"
                  class="integration-card"
                >
                  <div class="integration-icon">{{ integration.icon }}</div>
                  <div class="integration-info">
                    <h3 class="integration-name">{{ integration.name }}</h3>
                    <p class="integration-desc">{{ integration.description }}</p>
                    <p v-if="integration.connected" class="integration-status">
                      <el-icon><Check /></el-icon>
                      已连接 · {{ integration.connectedAt }}
                    </p>
                  </div>
                  <el-button
                    :type="integration.connected ? 'danger' : 'primary'"
                    @click="toggleIntegration(integration.id)"
                  >
                    {{ integration.connected ? '断开连接' : '连接' }}
                  </el-button>
                </div>
              </div>
            </section>

            <!-- 外观设置 -->
            <section v-if="activeMenu === 'appearance'" class="settings-section">
              <h2 class="section-title">外观设置</h2>
              <p class="section-description">自定义你的界面外观</p>

              <div class="appearance-group">
                <h3 class="subsection-title">主题</h3>
                <div class="theme-options">
                  <button
                    class="theme-option"
                    :class="{ 'is-selected': appearanceSettings.theme === 'light' }"
                    @click="appearanceSettings.theme = 'light'"
                  >
                    <div class="theme-preview light">
                      <div class="preview-header"></div>
                      <div class="preview-content"></div>
                    </div>
                    <span class="theme-name">浅色</span>
                  </button>
                  <button
                    class="theme-option"
                    :class="{ 'is-selected': appearanceSettings.theme === 'dark' }"
                    @click="appearanceSettings.theme = 'dark'"
                  >
                    <div class="theme-preview dark">
                      <div class="preview-header"></div>
                      <div class="preview-content"></div>
                    </div>
                    <span class="theme-name">深色</span>
                  </button>
                  <button
                    class="theme-option"
                    :class="{ 'is-selected': appearanceSettings.theme === 'auto' }"
                    @click="appearanceSettings.theme = 'auto'"
                  >
                    <div class="theme-preview auto">
                      <div class="preview-header"></div>
                      <div class="preview-content"></div>
                    </div>
                    <span class="theme-name">自动</span>
                  </button>
                </div>
              </div>

              <el-divider />

              <div class="appearance-group">
                <h3 class="subsection-title">代码编辑器</h3>
                <el-form label-position="top" class="settings-form">
                  <el-form-item label="字体">
                    <el-select v-model="appearanceSettings.codeFont" class="w-full">
                      <el-option label="JetBrains Mono" value="JetBrains Mono" />
                      <el-option label="Fira Code" value="Fira Code" />
                      <el-option label="Source Code Pro" value="Source Code Pro" />
                      <el-option label="Consolas" value="Consolas" />
                    </el-select>
                  </el-form-item>

                  <el-form-item label="缩进大小">
                    <el-radio-group v-model="appearanceSettings.tabSize">
                      <el-radio-button :label="2">2 空格</el-radio-button>
                      <el-radio-button :label="4">4 空格</el-radio-button>
                      <el-radio-button :label="8">8 空格</el-radio-button>
                    </el-radio-group>
                  </el-form-item>

                  <el-form-item>
                    <div class="checkbox-group">
                      <el-checkbox v-model="appearanceSettings.lineNumbers">显示行号</el-checkbox>
                      <el-checkbox v-model="appearanceSettings.wordWrap">自动换行</el-checkbox>
                      <el-checkbox v-model="appearanceSettings.minimap">显示缩略图</el-checkbox>
                    </div>
                  </el-form-item>
                </el-form>
              </div>

              <div class="form-actions">
                <el-button type="primary" @click="saveAppearance">
                  保存设置
                </el-button>
              </div>
            </section>
          </main>
        </div>
      </div>
    </div>
  </SidebarLayout>
</template>

<style scoped>
.settings-page {
  padding: var(--perseus-space-8);
  min-height: calc(100vh - 64px);
  background: var(--perseus-surface);
}

.settings-container {
  max-width: 960px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: var(--perseus-space-8);
}

.page-title {
  font-size: var(--perseus-text-2xl);
  font-weight: 700;
  letter-spacing: var(--perseus-tracking-display);
  margin-bottom: var(--perseus-space-2);
}

.page-subtitle {
  font-size: var(--perseus-text-base);
  color: var(--perseus-muted);
}

.settings-layout {
  display: grid;
  grid-template-columns: 200px 1fr;
  gap: var(--perseus-space-8);
  align-items: start;
}

/* 侧边栏导航 */
.settings-sidebar {
  position: sticky;
  top: calc(var(--perseus-header-height) + var(--perseus-space-8));
}

.settings-nav {
  display: flex;
  flex-direction: column;
  gap: var(--perseus-space-1);
}

.settings-nav-item {
  display: flex;
  align-items: center;
  gap: var(--perseus-space-3);
  padding: var(--perseus-space-3) var(--perseus-space-4);
  border-radius: var(--perseus-radius-md);
  border: none;
  background: transparent;
  color: var(--perseus-fg-2);
  font-size: var(--perseus-text-sm);
  font-weight: 500;
  cursor: pointer;
  transition: all var(--perseus-motion-fast) var(--perseus-ease-standard);
  text-align: left;
}

.settings-nav-item:hover {
  background: var(--perseus-surface-warm);
  color: var(--perseus-fg);
}

.settings-nav-item.is-active {
  background: var(--perseus-fg);
  color: var(--perseus-accent-on);
}

.nav-icon {
  flex-shrink: 0;
}

/* 内容区 */
.settings-content {
  background: var(--perseus-bg);
  border: 1px solid var(--perseus-border-soft);
  border-radius: var(--perseus-radius-lg);
  padding: var(--perseus-space-8);
}

.settings-section {
  animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.section-title {
  font-size: var(--perseus-text-xl);
  font-weight: 600;
  margin-bottom: var(--perseus-space-2);
}

.section-description {
  font-size: var(--perseus-text-sm);
  color: var(--perseus-muted);
  margin-bottom: var(--perseus-space-6);
}

.subsection-title {
  font-size: var(--perseus-text-base);
  font-weight: 600;
  margin-bottom: var(--perseus-space-4);
}

/* 头像区域 */
.avatar-section {
  display: flex;
  align-items: center;
  gap: var(--perseus-space-5);
  margin-bottom: var(--perseus-space-6);
  padding: var(--perseus-space-5);
  background: var(--perseus-surface);
  border-radius: var(--perseus-radius-md);
}

.avatar-preview {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: var(--perseus-accent);
  color: var(--perseus-accent-on);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--perseus-text-2xl);
  font-weight: 600;
}

.avatar-actions {
  display: flex;
  gap: var(--perseus-space-3);
}

/* 表单 */
.settings-form {
  max-width: 600px;
}

.form-actions {
  margin-top: var(--perseus-space-6);
  padding-top: var(--perseus-space-6);
  border-top: 1px solid var(--perseus-border-soft);
}

/* 安全设置 */
.security-section {
  margin-bottom: var(--perseus-space-6);
}

.two-factor-status {
  display: flex;
  align-items: center;
  gap: var(--perseus-space-4);
  padding: var(--perseus-space-5);
  background: var(--perseus-surface);
  border-radius: var(--perseus-radius-md);
}

.status-icon {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: var(--perseus-border-soft);
  color: var(--perseus-muted);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--perseus-text-xl);
  font-weight: 600;
}

.status-icon.is-enabled {
  background: var(--perseus-success);
  color: white;
}

.status-info {
  flex: 1;
}

.status-title {
  font-weight: 600;
  margin-bottom: var(--perseus-space-1);
}

.status-desc {
  font-size: var(--perseus-text-sm);
  color: var(--perseus-muted);
}

/* 危险区域 */
.danger-zone {
  border: 1px solid var(--perseus-danger);
  border-radius: var(--perseus-radius-md);
  padding: var(--perseus-space-5);
}

.danger-title {
  color: var(--perseus-danger);
}

.danger-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--perseus-space-4);
}

.danger-name {
  font-weight: 600;
  margin-bottom: var(--perseus-space-1);
}

.danger-desc {
  font-size: var(--perseus-text-sm);
  color: var(--perseus-muted);
}

/* 通知设置 */
.notification-group {
  margin-bottom: var(--perseus-space-6);
}

.notification-items {
  display: flex;
  flex-direction: column;
  gap: var(--perseus-space-4);
}

.notification-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--perseus-space-4);
  padding: var(--perseus-space-4);
  background: var(--perseus-surface);
  border-radius: var(--perseus-radius-md);
}

.notification-name {
  font-weight: 500;
  margin-bottom: var(--perseus-space-1);
}

.notification-desc {
  font-size: var(--perseus-text-sm);
  color: var(--perseus-muted);
}

/* 集成服务 */
.integrations-list {
  display: flex;
  flex-direction: column;
  gap: var(--perseus-space-4);
}

.integration-card {
  display: flex;
  align-items: center;
  gap: var(--perseus-space-4);
  padding: var(--perseus-space-5);
  background: var(--perseus-surface);
  border: 1px solid var(--perseus-border-soft);
  border-radius: var(--perseus-radius-md);
  transition: border-color var(--perseus-motion-fast);
}

.integration-card:hover {
  border-color: var(--perseus-border);
}

.integration-icon {
  width: 48px;
  height: 48px;
  border-radius: var(--perseus-radius-md);
  background: var(--perseus-bg);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
}

.integration-info {
  flex: 1;
}

.integration-name {
  font-weight: 600;
  margin-bottom: var(--perseus-space-1);
}

.integration-desc {
  font-size: var(--perseus-text-sm);
  color: var(--perseus-muted);
}

.integration-status {
  font-size: var(--perseus-text-xs);
  color: var(--perseus-success);
  margin-top: var(--perseus-space-1);
  display: flex;
  align-items: center;
  gap: var(--perseus-space-1);
}

/* 外观设置 */
.appearance-group {
  margin-bottom: var(--perseus-space-6);
}

.theme-options {
  display: flex;
  gap: var(--perseus-space-4);
}

.theme-option {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--perseus-space-3);
  padding: var(--perseus-space-3);
  border: 2px solid transparent;
  border-radius: var(--perseus-radius-md);
  background: transparent;
  cursor: pointer;
  transition: all var(--perseus-motion-fast);
}

.theme-option:hover {
  background: var(--perseus-surface);
}

.theme-option.is-selected {
  border-color: var(--perseus-accent);
  background: var(--perseus-surface);
}

.theme-preview {
  width: 80px;
  height: 60px;
  border-radius: var(--perseus-radius-sm);
  overflow: hidden;
  border: 1px solid var(--perseus-border);
}

.theme-preview .preview-header {
  height: 16px;
}

.theme-preview .preview-content {
  height: 44px;
}

.theme-preview.light .preview-header {
  background: #e2e2e2;
}

.theme-preview.light .preview-content {
  background: #ffffff;
}

.theme-preview.dark .preview-header {
  background: #333333;
}

.theme-preview.dark .preview-content {
  background: #1a1a1a;
}

.theme-preview.auto {
  background: linear-gradient(to right, #ffffff 50%, #1a1a1a 50%);
}

.theme-preview.auto .preview-header {
  background: linear-gradient(to right, #e2e2e2 50%, #333333 50%);
}

.theme-name {
  font-size: var(--perseus-text-sm);
  font-weight: 500;
}

.checkbox-group {
  display: flex;
  flex-direction: column;
  gap: var(--perseus-space-3);
}

.w-full {
  width: 100%;
}

/* 响应式 */
@media (max-width: 768px) {
  .settings-page {
    padding: var(--perseus-space-4);
  }

  .settings-layout {
    grid-template-columns: 1fr;
  }

  .settings-sidebar {
    position: static;
  }

  .settings-nav {
    flex-direction: row;
    flex-wrap: wrap;
  }

  .settings-content {
    padding: var(--perseus-space-5);
  }

  .theme-options {
    flex-wrap: wrap;
  }

  .danger-item {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
