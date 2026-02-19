<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { hasUserConfigFile } from './services/api'

/**
 * 根组件
 *
 * 应用启动时检查用户配置文件是否存在
 * 如果不存在则进入引导流程，由Guide页面接管配置生成
 */

const router = useRouter()

onMounted(async () => {
  try {
    const hasConfig = await hasUserConfigFile()
    if (!hasConfig) {
      // 配置文件不存在，进入引导流程
      router.replace('/guide')
    }
  } catch (e) {
    console.error('检查配置文件失败:', e)
  }
})
</script>

<template>
  <router-view />
</template>

<style>
/* 全局样式已在 main.ts 中导入 */
</style>
