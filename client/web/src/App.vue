<script setup lang="ts">
/**
 * Perseus Web Client - 根组件
 */
</script>

<template>
  <router-view />
</template>

<style>
/* 全局样式 */
html {
  scroll-behavior: smooth;
}

body {
  margin: 0;
  padding: 0;
}

/* Element Plus 样式覆盖 */
.el-button {
  --el-button-font-weight: 500;
}

.el-button--primary {
  --el-button-bg-color: var(--perseus-accent);
  --el-button-border-color: var(--perseus-accent);
  --el-button-hover-bg-color: #333;
  --el-button-hover-border-color: #333;
}

.el-input__wrapper {
  --el-input-border-color: var(--perseus-border);
  --el-input-hover-border-color: var(--perseus-fg-2);
  --el-input-focus-border-color: var(--perseus-accent);
}

.el-tag {
  --el-tag-bg-color: var(--perseus-surface);
  --el-tag-border-color: var(--perseus-border-soft);
}
</style>
