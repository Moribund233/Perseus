<template>
  <div ref="toolContentRef" class="tool-view scrollbar-thin scrollbar-vertical" >
    <component
      v-for="tool in visibleTools"
      :key="tool.id"
      :is="tool.component"
    />
  </div>

</template>

<script setup lang="ts">
import { onMounted, computed, ref, watch } from 'vue';
import { toolManager, useTool } from '@/utils/Tool';
import { useScroll } from '@/utils/Scroll';

// 组件属性
const props = defineProps<{
  config?: string; // 工具集配置键名
}>();

// 使用Tool管理器
const { getVisibleTools } = useTool();

// 工具内容区域引用
const toolContentRef = ref<HTMLElement>()

// 切换工具集
const switchToolSet = () => {
  if (props.config) {
    toolManager.switchToolSet(props.config);
  } else {
    toolManager.switchToolSet('default');
  }
};

// 计算可见工具（响应式）
const visibleTools = computed(() => {
  const tools = getVisibleTools();
  return tools;
});

// 监听配置变化，切换工具集
watch(() => props.config, () => {
  switchToolSet();
});

// 初始化工具系统
onMounted(async () => {
  await toolManager.initialize();
  
  // 初始切换工具集
  switchToolSet();
  
  if (toolContentRef.value) {
    useScroll(toolContentRef.value, {
      direction: 'vertical',
      showScrollbar: false,
      wheelToHorizontal: false // 垂直滚动条，不需要转换
    });
  }
});

</script>

<style scoped>
.tool-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow-y: auto;
  overflow-x: hidden;
}

/* 确保工具在垂直方向排列 */
.tool-view > * {
  flex-shrink: 0;
  margin: 4px 0;
}

.tool-view > *:not(:last-child) {
  margin-bottom: 8px;
}
</style>