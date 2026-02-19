<script setup lang="ts">
import Sidebar from './Sidebar.vue'
</script>

<template>
  <div class="layout">
    <Sidebar />
    <main class="main-content">
      <router-view />
    </main>
  </div>
</template>

<style scoped>
.layout {
  display: flex;
  height: 100vh;
  width: 100vw;
  overflow: hidden;
}

.main-content {
  flex: 1;
  overflow: auto;
  background-color: var(--bg-primary);
  padding: var(--spacing-lg);
}
</style>
