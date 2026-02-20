<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useServiceStore, useThemeStore } from '../stores'

const route = useRoute()

// 使用 Pinia store（自动刷新逻辑已在 store 中统一管理）
const serviceStore = useServiceStore()
const { isRunning, isRefreshing } = storeToRefs(serviceStore)

// 使用主题 Store
const themeStore = useThemeStore()

// 计算属性：服务状态
const serviceStatus = computed(() => isRunning.value)
const isLoading = computed(() => isRefreshing.value)

// 侧边栏折叠状态
const isCollapsed = ref(false)

/**
 * 切换侧边栏折叠状态
 */
const toggleSidebar = (): void => {
  isCollapsed.value = !isCollapsed.value
}

interface NavItem {
  path: string
  name: string
  icon: string
}

// 图标路径映射表（使用路径字符串方式）
const iconMap: Record<string, string> = {
  home: new URL('../assets/icons/home.svg', import.meta.url).href,
  log: new URL('../assets/icons/log.svg', import.meta.url).href,
  proxy: new URL('../assets/icons/proxy.svg', import.meta.url).href,
  setting: new URL('../assets/icons/setting.svg', import.meta.url).href,
  database: new URL('../assets/icons/database.svg', import.meta.url).href,
  menu: new URL('../assets/icons/menu.svg', import.meta.url).href,
  sun: new URL('../assets/icons/sun.svg', import.meta.url).href,
  moon: new URL('../assets/icons/moon.svg', import.meta.url).href
}

/**
 * 切换深浅主题
 */
const toggleDarkLightTheme = (): void => {
  const currentTheme = themeStore.currentColorThemeId
  if (currentTheme === 'light') {
    themeStore.switchColorTheme('dark')
  } else {
    themeStore.switchColorTheme('light')
  }
}

/**
 * 判断当前是否为浅色主题
 */
const isLightTheme = computed(() => themeStore.currentColorThemeId === 'light')



const navItems: NavItem[] = [
  { path: '/home', name: '控制台', icon: 'home' },
  { path: '/log', name: '日志', icon: 'log' },
  { path: '/nginx', name: '代理', icon: 'proxy' },
  { path: '/database', name: '数据库', icon: 'database' },
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
  <aside class="sidebar" :class="{ collapsed: isCollapsed }">
    <div class="sidebar-header">
      <button class="menu-btn" @click="toggleSidebar" title="切换侧边栏">
        <img :src="getIconPath('menu')" class="menu-icon" alt="menu" />
      </button>
      <span v-show="!isCollapsed" class="logo-text">LanGit</span>
    </div>

    <nav class="sidebar-nav">
      <router-link
        v-for="item in navItems"
        :key="item.path"
        :to="item.path"
        class="nav-item"
        :class="{ active: isActive(item.path) }"
        :title="item.name"
      >
        <img :src="getIconPath(item.icon)" class="nav-icon" :alt="item.name" />
        <span v-show="!isCollapsed" class="nav-text">{{ item.name }}</span>
      </router-link>
    </nav>

    <div class="sidebar-footer">
      <button
        class="theme-toggle-btn"
        :class="{ collapsed: isCollapsed }"
        @click="toggleDarkLightTheme"
        :title="isLightTheme ? '切换到深色主题' : '切换到浅色主题'"
      >
        <img
          :src="isLightTheme ? getIconPath('moon') : getIconPath('sun')"
          class="theme-icon"
          :alt="isLightTheme ? 'moon' : 'sun'"
        />
        <span v-show="!isCollapsed" class="theme-text">
          {{ isLightTheme ? '深色模式' : '浅色模式' }}
        </span>
      </button>
      <div class="server-status" :class="{ loading: isLoading, collapsed: isCollapsed }">
        <span class="status-dot" :class="{ online: serviceStatus }"></span>
        <span v-show="!isCollapsed" class="status-text">{{ serviceStatus ? '在线' : '离线' }}</span>
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
  transition: width var(--transition-normal);
}

.sidebar.collapsed {
  width: var(--sidebar-collapsed-width);
}

.sidebar-header {
  padding: var(--spacing-md);
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.menu-btn {
  background: none;
  border: none;
  padding: var(--spacing-sm);
  cursor: pointer;
  border-radius: var(--border-radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background-color var(--transition-fast);
}

.menu-btn:hover {
  background-color: var(--bg-hover);
}

.menu-icon {
  width: 24px;
  height: 24px;
  filter: var(--icon-filter);
}

.logo-text {
  font-size: var(--font-size-xl);
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.5px;
  white-space: nowrap;
}

.sidebar-nav {
  flex: 1;
  padding: var(--spacing-md);
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: var(--spacing-md);
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

.sidebar.collapsed .nav-item {
  justify-content: center;
  padding: var(--spacing-md) var(--spacing-sm);
}

.nav-icon {
  width: 26px;
  height: 26px;
  flex-shrink: 0;
  filter: var(--icon-filter);
}

.nav-item.active .nav-icon {
  filter: none;
}

.nav-text {
  font-size: var(--font-size-md);
  font-weight: 500;
  white-space: nowrap;
}

.sidebar-footer {
  padding: var(--spacing-md);
  border-top: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.theme-toggle-btn {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-md);
  background-color: var(--bg-tertiary);
  border: none;
  border-radius: var(--border-radius-md);
  color: var(--text-secondary);
  font-size: var(--font-size-sm);
  cursor: pointer;
  transition: all var(--transition-fast);
  width: 100%;
}

.theme-toggle-btn:hover {
  background-color: var(--bg-hover);
  color: var(--text-primary);
}

.theme-toggle-btn.collapsed {
  justify-content: center;
  padding: var(--spacing-sm);
}

.theme-icon {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
  filter: var(--icon-filter);
}

.theme-text {
  white-space: nowrap;
}

.server-status {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-md);
  background-color: var(--bg-tertiary);
  border-radius: var(--border-radius-md);
  transition: all var(--transition-fast);
}

.server-status.collapsed {
  justify-content: center;
  padding: var(--spacing-sm);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: var(--error-color);
  animation: pulse 2s infinite;
  flex-shrink: 0;
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
  white-space: nowrap;
}
</style>
