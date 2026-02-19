<template>
  <!-- 登录和注册页面独占全屏，其他页面使用完整布局 -->
  <template v-if="isAuthPage">
    <router-view />
  </template>
  <template v-else>
    <div class="main-container app-container">
      <TitleBar />
      <div class="content-area">
        <MainSidebar />
        <div class="main-content-area">
          <MainContent />
          <BottomPanel v-if="isBottomPanelVisible" />
        </div>
        <AuxSidebar v-if="isAuxSidebarVisible" />
      </div>
    </div>
  </template>
</template>

<script setup lang="ts">
import { onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useQuickSetting } from '@/stores/quickSetting'
import { useTheme } from '@/core/themeManager.ts'
import { useConfigManager } from '@/core/configManager.ts'
import { useUserStore } from '@/stores/user'
import TitleBar from '@/containers/TitleBar.vue'
import MainSidebar from '@/containers/MainSidebar.vue'
import MainContent from '@/containers/MainContent.vue'
import AuxSidebar from '@/containers/AuxSidebar.vue'
import BottomPanel from '@/containers/BottomPanel.vue'

const route = useRoute()
const { isBottomPanelVisible, isAuxSidebarVisible, currentTheme } = useQuickSetting()
const configManager = useConfigManager()
const userStore = useUserStore()

// 判断当前页面是否为登录或注册页面
const isAuthPage = computed(() => {
  const authRoutes = ['Login', 'Register']
  return authRoutes.includes(route.name as string)
})

// 初始化应用
onMounted(async () => {
  // 恢复用户状态
  userStore.restoreUserFromStorage()
  
  // 初始化配置
  await configManager.initializeConfigs()
  
  // 初始化主题
  const theme = useTheme()
  theme.applyTheme(currentTheme.value)
})
</script>

<style scoped>
/* 此处添加额外样式 */
</style>