<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useServiceStore } from '../stores'

// 导入图标
import logoIcon from '../assets/icons/logo.svg'
import homeIcon from '../assets/icons/home.svg'
import logIcon from '../assets/icons/log.svg'
import proxyIcon from '../assets/icons/proxy.svg'
import settingIcon from '../assets/icons/setting.svg'

const route = useRoute()

// 使用 Pinia store（自动刷新逻辑已在 store 中统一管理）
const serviceStore = useServiceStore()
const { isRunning, isRefreshing } = storeToRefs(serviceStore)

// 计算属性：服务状态
const serviceStatus = computed(() => isRunning.value)
const isLoading = computed(() => isRefreshing.value)

interface NavItem {
  path: string
  name: string
  icon: string
}

// 图标映射表
const iconMap: Record<string, string> = {
  home: homeIcon,
  log: logIcon,
  proxy: proxyIcon,
  setting: settingIcon
}

const navItems: NavItem[] = [
  { path: '/home', name: '控制台', icon: 'home' },
  { path: '/log', name: '日志', icon: 'log' },
  { path: '/nginx', name: '代理', icon: 'proxy' },
  { path: '/setting', name: '设置', icon: 'setting' }
]

const isActive = (path: string): boolean => {
  return route.path === path
}

/**
 * 获取图标路径
 */
const getIconPath = (iconName: string): string => {
  return iconMap[iconName] || ''
}
</script>

<template>
  <aside class="sidebar">
    <div class="sidebar-header">
      <div class="logo">
        <img :src="logoIcon" class="logo-icon" alt="logo" />
        <span class="logo-text">LanGit</span>
      </div>
    </div>

    <nav class="sidebar-nav">
      <router-link
        v-for="item in navItems"
        :key="item.path"
        :to="item.path"
        class="nav-item"
        :class="{ active: isActive(item.path) }"
      >
        <img :src="getIconPath(item.icon)" class="nav-icon" :alt="item.name" />
        <span class="nav-text">{{ item.name }}</span>
      </router-link>
    </nav>

    <div class="sidebar-footer">
      <div class="server-status" :class="{ loading: isLoading }">
        <span class="status-dot" :class="{ online: serviceStatus }"></span>
        <span class="status-text">{{ serviceStatus ? '服务运行中' : '服务已停止' }}</span>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  width: var(--sidebar-width);
  height: 100vh;
  background-color: var(--bg-secondary);
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.sidebar-header {
  padding: var(--spacing-lg);
  border-bottom: 1px solid var(--border-color);
}

.logo {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.logo-icon {
  width: 32px;
  height: 32px;
  color: var(--primary-color);
}

.logo-text {
  font-size: var(--font-size-xl);
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.5px;
}

.sidebar-nav {
  flex: 1;
  padding: var(--spacing-md);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.nav-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-md);
  border-radius: var(--border-radius-md);
  color: var(--text-secondary);
  text-decoration: none;
  transition: all var(--transition-fast);
}

.nav-item:hover {
  background-color: var(--bg-hover);
  color: var(--text-primary);
}

.nav-item.active {
  background-color: var(--primary-color);
  color: white;
}

.nav-icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
}

.nav-text {
  font-size: var(--font-size-md);
  font-weight: 500;
}

.sidebar-footer {
  padding: var(--spacing-md);
  border-top: 1px solid var(--border-color);
}

.server-status {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-md);
  background-color: var(--bg-tertiary);
  border-radius: var(--border-radius-md);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: var(--error-color);
  animation: pulse 2s infinite;
}

.status-dot.online {
  background-color: var(--success-color);
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

.status-text {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}
</style>
