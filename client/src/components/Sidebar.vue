<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useServiceStore } from '../stores'

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

const navItems: NavItem[] = [
  { path: '/home', name: '控制台', icon: 'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6' },
  { path: '/log', name: '日志', icon: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z' },
  { path: '/nginx', name: '代理', icon: 'M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5' },
  { path: '/setting', name: '设置', icon: 'M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z M15 12a3 3 0 11-6 0 3 3 0 016 0z' }
]

const isActive = (path: string): boolean => {
  return route.path === path
}
</script>

<template>
  <aside class="sidebar">
    <div class="sidebar-header">
      <div class="logo">
        <svg class="logo-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M5 12h14M12 5l7 7-7 7"/>
        </svg>
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
        <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path :d="item.icon"/>
        </svg>
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
  background-color: var(--bg-tertiary);
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
