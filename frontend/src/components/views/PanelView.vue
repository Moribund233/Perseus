<template>
  <div ref="PanelContentRef" class="panel-view scrollbar-thin scrollbar-horizontal" >
    <component
      v-for="panel in visiblePanels"
      :key="panel.id"
      :is="panel.component"
    />
  </div>

</template>

<script setup lang="ts">
import { onMounted, onUnmounted, computed, ref, watch } from 'vue';
import { panelManager, usePanel } from '@/utils/Panel';
import { useScroll } from '@/utils/Scroll';

// 使用Panel管理器
const { getVisiblePanels } = usePanel();

// 面板内容区域引用
const PanelContentRef = ref<HTMLElement>();

// 内存泄漏防护相关变量
let scrollCleanup: (() => void) | null = null;
let panelWatcher: (() => void) | null = null;
let resizeObserver: ResizeObserver | null = null;

// 计算可见面板（响应式）
const visiblePanels = computed(() => {
  return getVisiblePanels();
});

// 初始化面板系统
onMounted(async () => {
  try {
    await panelManager.initialize();
    
    // 初始化滚动系统
    if (PanelContentRef.value) {
      const scrollResult = useScroll(PanelContentRef.value, {
        direction: 'horizontal',
        showScrollbar: false,
        wheelToHorizontal: true // 启用垂直滚轮转水平滚动
      });
      
      if (scrollResult && typeof scrollResult === 'function') {
        scrollCleanup = scrollResult;
      }
    }
    
    // 监听面板内容区域尺寸变化
    if (PanelContentRef.value) {
      resizeObserver = new ResizeObserver((entries) => {
        for (const entry of entries) {
          if (entry.target === PanelContentRef.value) {
            // 尺寸变化监听
          }
        }
      });
      
      resizeObserver.observe(PanelContentRef.value);
    }
    
    // 监听可见面板变化
    panelWatcher = watch(visiblePanels, () => {
      // 面板可见性变化监听
    });
    
  } catch (error) {
    console.error('Failed to initialize PanelView:', error);
  }
});

// 组件卸载时的清理
onUnmounted(() => {
  // 清理滚动系统
  if (scrollCleanup) {
    scrollCleanup();
    scrollCleanup = null;
  }
  
  // 清理尺寸监听器
  if (resizeObserver) {
    resizeObserver.disconnect();
    resizeObserver = null;
  }
  
  // 清理面板监听器
  if (panelWatcher) {
    panelWatcher();
    panelWatcher = null;
  }
  
  // 清理面板管理器资源（可选，根据需要决定是否清理）
  // panelManager.cleanupAll();
});

</script>

<style scoped>
.panel-view {
  display: flex;
  height: 100%;
  align-items: stretch;
  overflow-x: auto;
  overflow-y: hidden;
}

/* 确保面板在水平方向排列 */
.panel-view > * {
  flex-shrink: 0;
  margin: 8px 0;
}

.panel-view > *:not(:last-child) {
  margin-right: 8px;
}
</style>