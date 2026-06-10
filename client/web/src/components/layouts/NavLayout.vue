<script setup lang="ts">
/**
 * 顶部导航布局组件
 * 用于 Explore、Landing 等需要顶部导航的页面
 */
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import { Search, Menu } from '@element-plus/icons-vue'

const route = useRoute()
const searchQuery = ref('')
const isMobileMenuOpen = ref(false)

const navItems = [
  { path: '/explore', label: '探索' },
  { path: '/pricing', label: '价格' },
  { path: '/docs', label: '文档' },
]

const isActive = (path: string) => route.path === path
</script>

<template>
  <div class="nav-layout">
    <!-- 顶部导航 -->
    <header class="top-nav">
      <div class="nav-inner">
        <!-- Logo -->
        <router-link to="/" class="nav-brand">
          <div class="brand-icon">
            <svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor">
              <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
            </svg>
          </div>
          <span class="brand-text">Perseus</span>
        </router-link>

        <!-- 搜索框 -->
        <div class="nav-search">
          <el-input
            v-model="searchQuery"
            placeholder="搜索仓库..."
            :prefix-icon="Search"
            class="search-input"
          />
        </div>

        <!-- 导航链接 -->
        <nav class="nav-links">
          <router-link
            v-for="item in navItems"
            :key="item.path"
            :to="item.path"
            class="nav-link"
            :class="{ 'is-active': isActive(item.path) }"
          >
            {{ item.label }}
          </router-link>
        </nav>

        <!-- 右侧操作区 -->
        <div class="nav-actions">
          <el-button type="primary" class="sign-in-btn">登录</el-button>
          <el-button class="sign-up-btn">注册</el-button>
        </div>

        <!-- 移动端菜单按钮 -->
        <button class="mobile-menu-btn" @click="isMobileMenuOpen = !isMobileMenuOpen">
          <el-icon :size="24">
            <Menu />
          </el-icon>
        </button>
      </div>
    </header>

    <!-- 移动端菜单 -->
    <div v-if="isMobileMenuOpen" class="mobile-menu">
      <div class="mobile-search">
        <el-input
          v-model="searchQuery"
          placeholder="搜索仓库..."
          :prefix-icon="Search"
        />
      </div>
      <nav class="mobile-nav-links">
        <router-link
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="mobile-nav-link"
          :class="{ 'is-active': isActive(item.path) }"
          @click="isMobileMenuOpen = false"
        >
          {{ item.label }}
        </router-link>
      </nav>
      <div class="mobile-actions">
        <el-button type="primary" class="w-full">登录</el-button>
        <el-button class="w-full">注册</el-button>
      </div>
    </div>

    <!-- 主内容区 -->
    <main class="main-content">
      <slot />
    </main>
  </div>
</template>

<style scoped>
.nav-layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.top-nav {
  position: sticky;
  top: 0;
  z-index: 50;
  background: rgba(255, 255, 255, 0.94);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--perseus-border-soft);
}

.nav-inner {
  max-width: var(--perseus-container-max);
  margin: 0 auto;
  padding: 0 var(--perseus-container-gutter);
  height: 64px;
  display: flex;
  align-items: center;
  gap: var(--perseus-space-6);
}

.nav-brand {
  display: flex;
  align-items: center;
  gap: var(--perseus-space-2);
  flex-shrink: 0;
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
}

.brand-text {
  font-size: var(--perseus-text-lg);
  font-weight: 600;
  letter-spacing: var(--perseus-tracking-display);
}

.nav-search {
  flex: 1;
  max-width: 400px;
}

.search-input :deep(.el-input__wrapper) {
  background: var(--perseus-surface);
  border-radius: var(--perseus-radius-pill);
  box-shadow: none;
  border: 1px solid var(--perseus-border-soft);
}

.nav-links {
  display: flex;
  align-items: center;
  gap: var(--perseus-space-6);
}

.nav-link {
  font-size: var(--perseus-text-sm);
  font-weight: 500;
  color: var(--perseus-fg-2);
  padding: var(--perseus-space-2) 0;
  position: relative;
  transition: color var(--perseus-motion-fast) var(--perseus-ease-standard);
}

.nav-link:hover {
  color: var(--perseus-fg);
}

.nav-link.is-active {
  color: var(--perseus-fg);
}

.nav-link.is-active::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: var(--perseus-accent);
  border-radius: var(--perseus-radius-pill);
}

.nav-actions {
  display: flex;
  align-items: center;
  gap: var(--perseus-space-3);
}

.sign-in-btn {
  background: var(--perseus-accent);
  border-color: var(--perseus-accent);
}

.sign-up-btn {
  border-color: var(--perseus-border);
}

.mobile-menu-btn {
  display: none;
  background: none;
  border: none;
  color: var(--perseus-fg);
  cursor: pointer;
  padding: var(--perseus-space-2);
}

.mobile-menu {
  display: none;
  position: fixed;
  top: 64px;
  left: 0;
  right: 0;
  bottom: 0;
  background: var(--perseus-bg);
  z-index: 49;
  padding: var(--perseus-space-6);
}

.mobile-search {
  margin-bottom: var(--perseus-space-6);
}

.mobile-nav-links {
  display: flex;
  flex-direction: column;
  gap: var(--perseus-space-4);
  margin-bottom: var(--perseus-space-6);
}

.mobile-nav-link {
  font-size: var(--perseus-text-lg);
  font-weight: 500;
  color: var(--perseus-fg-2);
  padding: var(--perseus-space-3) 0;
}

.mobile-nav-link.is-active {
  color: var(--perseus-fg);
}

.mobile-actions {
  display: flex;
  flex-direction: column;
  gap: var(--perseus-space-3);
}

.w-full {
  width: 100%;
}

.main-content {
  flex: 1;
}

/* 响应式 */
@media (max-width: 768px) {
  .nav-links,
  .nav-actions {
    display: none;
  }

  .mobile-menu-btn {
    display: block;
    margin-left: auto;
  }

  .mobile-menu {
    display: block;
  }

  .nav-search {
    display: none;
  }
}
</style>
