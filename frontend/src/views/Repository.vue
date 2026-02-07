<template>
  <div class="repository-page scrollbar-hide scroll-smooth">
    <!-- 子路由页面 -->
    <router-view />
    <Island config="Repository"></Island>
  </div>
</template>

<script setup lang="ts">

import Island from '@/components/public/Island.vue';
</script>

<style scoped>
.repository-page {
  padding: 24px;
  min-height: 100%;
  background: var(--color-main-content-bg);
}
</style>