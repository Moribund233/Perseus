<template>
  <div class="debug-page scrollbar-hide scroll-smooth">
    <!-- 子路由页面 -->
    <router-view />
    <Island config="Debug"></Island>
  </div>
</template>

<script setup lang="ts">

import Island from '@/components/public/Island.vue';
</script>

<style scoped>
.debug-page {
  padding: 24px;
  min-height: 100%;
  background: var(--color-main-content-bg);
}
</style>