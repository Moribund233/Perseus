<!-- 
  公共组件: 卡片
  用途: 统一卡片样式开发
  调用: <Card title="卡片标题" usage="display"></Card>
  特性:
    - 简易调用
    - 支持Flex布局自适应
    - 集成Drag系统，每个卡片都支持自由调整大小
    - 集成Scroll系统，支持隐藏式滚动条
-->
<template>
  <div ref="elementRef" :class="['card-container', 'scrollbar-thin', usage ? 'card-usage-' + usage : '']">
    <!-- 卡片标题 -->
    <div class="card-header" v-if="title">
      <h3 class="card-title">{{ title }}</h3>
    </div>
    
    <!-- 卡片内容区域 -->
    <div class="card-content">
      <slot></slot>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useDrag } from '@/utils/Drag';
import { useScroll } from '@/utils/Scroll';
import { onMounted } from 'vue';
import { useUIStore } from '@/stores/ui';

// 组件属性
interface CardProps {
  title?: string; // 卡片标题
  usage?: string; // 卡片用途类型
}

const props = withDefaults(defineProps<CardProps>(), {
  title: '',
  usage: 'default'
});

// UI存储
const uiStore = useUIStore();
const cardId = `card-${props.title || 'default'}`;

// 使用Drag系统，支持自由调整大小
const { elementRef } = useDrag({
  direction: ['right', 'bottom'],
  onDrag: (size, direction) => {
    console.log(`Card resized: ${size}px in direction ${direction}`);
  },
  onDragEnd: () => {
    // 拖拽结束时保存尺寸
    if (elementRef.value) {
      const width = elementRef.value.offsetWidth;
      const height = elementRef.value.offsetHeight;
      uiStore.saveCardSize(cardId, { width, height });
    }
  }
});

// 使用Scroll系统，支持隐藏式滚动条
onMounted(() => {
  if (elementRef.value) {
    useScroll(elementRef.value, {
      direction: 'both',
      showScrollbar: false
    });
    
    // 恢复保存的尺寸
    const savedSize = uiStore.getCardSize(cardId);
    if (savedSize) {
      elementRef.value.style.width = `${savedSize.width}px`;
      elementRef.value.style.height = `${savedSize.height}px`;
    }
  }
});
</script>

<style scoped>
.card-container {
  background-color: var(--color-card-bg);
  border: 1px solid var(--color-card-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: all var(--transition-normal);
  min-width: 200px;
  min-height: 150px;
  flex-shrink: 0;
}

.card-container:hover {
  box-shadow: var(--shadow-md);
}

/* 卡片头部 */
.card-header {
  padding: 16px;
  border-bottom: 1px solid var(--color-card-divider);
  background-color: var(--color-card-bg);
}

.card-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--color-card-title);
}

/* 卡片内容 */
.card-content {
  padding: 16px;
  flex: 1;
  overflow: auto;
  color: var(--color-card-description);
}

</style>