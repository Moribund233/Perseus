<template>
  <div 
    class="main-sidebar scrollbar-hide scroll-smooth" 
    :class="{ collapsed: isSidebarCollapsed }"
    :style="{ width: sidebarWidth + 'px' }"
  >
    <!-- 导航区域 - 位于上方 -->
    <div class="nav-section">
      <div class="nav-items">
        <div 
          v-for="item in navigationItems" 
          :key="item.route"
          class="nav-item"
          :class="{ active: currentRoute === item.route }"
          @click="handleNavigation(item.route)"
        >
          <img class="nav-icon" :src="item.icon" :alt="item.name" />
          <span class="nav-text" v-show="!isSidebarCollapsed">{{ item.name }}</span>
        </div>
      </div>
    </div>

    <!-- 快速设置区域 - 位于下方 -->
    <div class="quick-settings-section">
      <div class="quick-settings">
        <div 
          v-for="setting in quickSettings" 
          :key="setting.id"
          class="quick-setting-item"
          :class="{ active: setting.active }"
          @click="handleClick(setting)"
        >
          <img class="setting-icon" :src="setting.icon" :alt="setting.name" />
          <span class="setting-text" v-show="!isSidebarCollapsed">{{ setting.displayText ?? setting.name }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useQuickSetting, handleQuickSetting } from '@/stores/quickSetting'
import type { NavigationConfig } from '@/stores/quickSetting'
import sidebarConfig from '@/config/Sidebar.json'

const router = useRouter()
const route = useRoute()

const { isSidebarCollapsed } = useQuickSetting()
const navigationItems = computed<NavigationConfig[]>(() => sidebarConfig.mainSidebar.navigation)
const { quickSettings } = useQuickSetting()
const currentRoute = computed(() => route.path)

const sidebarWidth = computed(() => {
  return isSidebarCollapsed.value ? 60 : 250
})

const handleNavigation = (navRoute: string) => {
  router.push(navRoute)
}

const handleClick = (setting: { method: string; active?: boolean; id: string }) => {
  handleQuickSetting(setting.method, [setting.active], setting.id)
}

watch(
  () => route.path,
  (newPath) => {
    console.log('Route changed:', newPath)
  }
)
</script>

<style scoped>
/* 主侧边栏样式现在统一在 containers.css 中 */
/* 这里只保留组件特定的样式覆盖（如果有的话） */
</style>