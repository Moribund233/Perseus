<script setup lang="ts">
/**
 * 侧边栏布局组件
 * 用于 Dashboard 等需要侧边栏的页面
 */
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import {
  HomeFilled,
  Collection,
  Search,
  Setting,
  User,
  ArrowLeft,
  ArrowRight,
} from '@element-plus/icons-vue'

const route = useRoute()
const isCollapsed = ref(false)

const toggleSidebar = () => {
  isCollapsed.value = !isCollapsed.value
}

const menuItems = [
  { path: '/dashboard', icon: HomeFilled, label: '仪表盘' },
  { path: '/explore', icon: Search, label: '探索' },
  { path: '/repositories', icon: Collection, label: '仓库' },
]

const bottomItems = [
  { path: '/settings', icon: Setting, label: '设置' },
  { path: '/profile', icon: User, label: '个人资料' },
]

const isActive = (path: string) => route.path === path || route.path.startsWith(path)
</script>

<template>
  <div class="sidebar-layout">
    <!-- 侧边栏 -->
    <aside class="sidebar" :class="{ 'is-collapsed': isCollapsed }">
      <!-- Logo -->
      <div class="sidebar-brand">
        <div class="brand-icon">
          <svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor">
            <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
          </svg>
        </div>
        <span v-show="!isCollapsed" class="brand-text">Perseus</span>
      </div>

      <!-- 主导航 -->
      <nav class="sidebar-nav">
        <ul class="nav-list">
          <li v-for="item in menuItems" :key="item.path">
            <router-link
              :to="item.path"
              class="nav-link"
              :class="{ 'is-active': isActive(item.path) }"
              :title="isCollapsed ? item.label : undefined"
            >
              <el-icon class="nav-icon" :size="20">
                <component :is="item.icon" />
              </el-icon>
              <span v-show="!isCollapsed" class="nav-label">{{ item.label }}</span>
            </router-link>
          </li>
        </ul>
      </nav>

      <!-- 底部导航 -->
      <div class="sidebar-footer">
        <ul class="nav-list">
          <li v-for="item in bottomItems" :key="item.path">
            <router-link
              :to="item.path"
              class="nav-link"
              :class="{ 'is-active': isActive(item.path) }"
              :title="isCollapsed ? item.label : undefined"
            >
              <el-icon class="nav-icon" :size="20">
                <component :is="item.icon" />
              </el-icon>
              <span v-show="!isCollapsed" class="nav-label">{{ item.label }}</span>
            </router-link>
          </li>
        </ul>

        <!-- 折叠按钮 -->
        <button class="collapse-btn" @click="toggleSidebar">
          <el-icon :size="16">
            <ArrowLeft v-if="!isCollapsed" />
            <ArrowRight v-else />
          </el-icon>
        </button>
      </div>
    </aside>

    <!-- 主内容区 -->
    <main class="main-content">
      <slot />
    </main>
  </div>
</template>

<style scoped>
.sidebar-layout {
  display: flex;
  min-height: 100vh;
}

.sidebar {
  width: var(--perseus-sidebar-width);
  background: var(--perseus-surface);
  border-right: 1px solid var(--perseus-border-soft);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  position: fixed;
  top: 0;
  left: 0;
  bottom: 0;
  z-index: 40;
  transition: width var(--perseus-motion-base) var(--perseus-ease-standard);
}

.sidebar.is-collapsed {
  width: var(--perseus-sidebar-collapsed);
}

.sidebar-brand {
  display: flex;
  align-items: center;
  gap: var(--perseus-space-2);
  padding: var(--perseus-space-4) var(--perseus-space-5);
  height: 60px;
  border-bottom: 1px solid var(--perseus-border-soft);
}

.brand-icon {
  width: 32px;
  height: 32px;
  border-radius: var(--perseus-radius-md);
  background: var(--perseus-accent);
  color: var(--perseus-accent-on);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.brand-text {
  font-size: var(--perseus-text-lg);
  font-weight: 600;
  letter-spacing: var(--perseus-tracking-display);
  white-space: nowrap;
}

.sidebar-nav {
  flex: 1;
  padding: var(--perseus-space-3) var(--perseus-space-3);
  overflow-y: auto;
}

.nav-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.nav-list li {
  margin-bottom: var(--perseus-space-1);
}

.nav-link {
  display: flex;
  align-items: center;
  gap: var(--perseus-space-3);
  padding: var(--perseus-space-3) var(--perseus-space-3);
  border-radius: var(--perseus-radius-md);
  color: var(--perseus-fg-2);
  transition: all var(--perseus-motion-fast) var(--perseus-ease-standard);
}

.nav-link:hover {
  background: var(--perseus-surface-warm);
  color: var(--perseus-fg);
}

.nav-link.is-active {
  background: var(--perseus-fg);
  color: var(--perseus-accent-on);
}

.nav-icon {
  flex-shrink: 0;
}

.nav-label {
  font-size: var(--perseus-text-sm);
  font-weight: 500;
  white-space: nowrap;
}

.sidebar-footer {
  padding: var(--perseus-space-3);
  border-top: 1px solid var(--perseus-border-soft);
}

.collapse-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--perseus-space-2);
  margin-top: var(--perseus-space-3);
  border: none;
  background: transparent;
  color: var(--perseus-muted);
  border-radius: var(--perseus-radius-md);
  cursor: pointer;
  transition: all var(--perseus-motion-fast) var(--perseus-ease-standard);
}

.collapse-btn:hover {
  background: var(--perseus-surface-warm);
  color: var(--perseus-fg);
}

.main-content {
  flex: 1;
  margin-left: var(--perseus-sidebar-width);
  min-height: 100vh;
  transition: margin-left var(--perseus-motion-base) var(--perseus-ease-standard);
}

.sidebar.is-collapsed + .main-content {
  margin-left: var(--perseus-sidebar-collapsed);
}

/* 响应式 */
@media (max-width: 768px) {
  .sidebar {
    transform: translateX(-100%);
  }

  .sidebar.is-open {
    transform: translateX(0);
  }

  .main-content {
    margin-left: 0;
  }
}
</style>
