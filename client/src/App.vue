<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { isGuideCompleted } from './services/api'

/**
 * 根组件
 *
 * 应用启动时检查引导是否已完成
 * 使用 isGuideCompleted 而不是 hasUserConfigFile 来避免安全漏洞：
 * 如果仅检查配置文件，用户可以在Guide的第1步保存配置后关闭应用，
 * 下次启动时跳过剩余步骤（包括设置安全密码）直接进入客户端
 */

const router = useRouter()

onMounted(async () => {
  try {
    const guideCompleted = await isGuideCompleted()
    if (!guideCompleted) {
      // 引导未完成，进入引导流程
      router.replace('/guide')
    }
  } catch (e) {
    console.error('检查引导状态失败:', e)
    // 出错时默认进入引导流程，确保安全
    router.replace('/guide')
  }
})
</script>

<template>
  <router-view />
</template>

<style>
/* 全局样式已在 main.ts 中导入 */
</style>
