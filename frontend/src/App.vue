<template>
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

<script setup lang="ts">
import { onMounted } from 'vue'
import { useQuickSetting } from '@/stores/quickSetting'
import { useTheme } from '@/core/themeManager.ts'
import { useConfigManager } from '@/core/configManager.ts'
import TitleBar from '@/containers/TitleBar.vue'
import MainSidebar from '@/containers/MainSidebar.vue'
import MainContent from '@/containers/MainContent.vue'
import AuxSidebar from '@/containers/AuxSidebar.vue'
import BottomPanel from '@/containers/BottomPanel.vue'

const { isBottomPanelVisible, isAuxSidebarVisible, currentTheme } = useQuickSetting()
const configManager = useConfigManager()

// 初始化应用
onMounted(async () => {
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