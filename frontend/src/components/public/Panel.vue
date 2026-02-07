<!-- 
  公共组件: 底部面板容器
  用途: 底部面板内的独立模块容器
  特性:
    - 与底部面板高度一致
    - 支持自由调整宽度
    - 顶部居中标题
    - 右上角关闭按钮
    - 支持显隐控制
    - 封装可见性和关闭逻辑
-->
<template>
  <div ref="panelRef" class="panel-container" :class="{ 'panel-hidden': !isVisible }">
    <!-- 面板头部 -->
    <div class="panel-header">
      <h3 class="panel-title">{{ title }}</h3>
      <button v-if="showClose" class="panel-close-btn" @click="handleClose">
        <span class="close-icon">×</span>
      </button>
    </div>
    
    <!-- 面板内容区域 -->
    <div ref="contentRef" class="panel-content scrollbar-thin scrollbar-vertical">
      <slot></slot>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useDrag } from '@/utils/Drag';
import { useScroll } from '@/utils/Scroll';
import { onMounted, onUnmounted, ref, computed, watch } from 'vue';
import { useUIStore } from '@/stores/ui';
import { panelManager } from '@/utils/Panel';

// 组件属性
interface PanelProps {
  title: string; // 面板标题
  id?: string; // 面板唯一标识
  visible?: boolean; // 是否可见
  showClose?: boolean; // 是否显示关闭按钮
}

const props = withDefaults(defineProps<PanelProps>(), {
  id: '',
  visible: undefined,
  showClose: true
});

// UI存储
const uiStore = useUIStore();
const panelId = computed(() => props.id || `panel-${props.title}`);

// 组件事件
const emit = defineEmits<{
  close: [id?: string]; // 关闭事件
}>();

// 计算可见性：优先使用props.visible，如果没有则通过Panel管理器获取
// 如果既没有提供visible属性，也没有在Panel管理器中注册，则默认可见（直接渲染模式）
const isVisible = computed(() => {
  if (props.visible !== undefined) {
    return props.visible;
  }
  // 通过Panel管理器获取可见性状态
  const managedVisible = panelManager.isPanelVisible(panelId.value);
  // 如果没有在管理器中注册，则默认可见（直接渲染模式）
  return managedVisible !== false ? true : false;
});

// 面板引用
const { elementRef: panelRef } = useDrag({
  direction: ['right', 'left'],
  onDrag: (size, direction) => {
    console.log(`Panel resized: ${size}px in direction ${direction}`);
  },
  onDragEnd: () => {
    // 拖拽结束时保存宽度
    if (panelRef.value) {
      const width = panelRef.value.offsetWidth;
      uiStore.savePanelSize(panelId.value, { width });
    }
  }
});

// 内容区域引用
const contentRef = ref<HTMLElement | null>(null);

// 内存泄漏防护相关变量
const cleanupFunctions: Array<() => void> = [];
let scrollCleanup: (() => void) | null = null;
let resizeObserver: ResizeObserver | null = null;
let visibilityWatcher: (() => void) | null = null;

// 使用Scroll系统，支持隐藏式滚动条
onMounted(() => {
  console.log(`🔄 Panel mounted: ${panelId.value}`);
  
  // 初始化滚动系统
  if (contentRef.value) {
    const scrollResult = useScroll(contentRef.value, {
      direction: 'vertical',
      showScrollbar: false
    });
    
    if (scrollResult && typeof scrollResult === 'function') {
      scrollCleanup = scrollResult;
      cleanupFunctions.push(scrollResult);
    }
  }
  
  // 恢复保存的宽度
  if (panelRef.value) {
    const savedSize = uiStore.getPanelSize(panelId.value);
    if (savedSize) {
      panelRef.value.style.width = `${savedSize.width}px`;
    }
  }
  
  // 添加尺寸变化监听
  if (panelRef.value) {
    resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        if (entry.target === panelRef.value) {
          const width = entry.contentRect.width;
          // 可以在这里添加尺寸变化的处理逻辑
          console.log(`📏 Panel width changed: ${width}px`);
        }
      }
    });
    
    resizeObserver.observe(panelRef.value);
    cleanupFunctions.push(() => {
      if (resizeObserver) {
        resizeObserver.disconnect();
        resizeObserver = null;
      }
    });
  }
  
  // 监听可见性变化
  visibilityWatcher = watch(isVisible, (newVisible, oldVisible) => {
    console.log(`👁️ Panel visibility changed: ${panelId.value} from ${oldVisible} to ${newVisible}`);
    
    // 当面板隐藏时，可以执行一些清理操作
    if (!newVisible && oldVisible) {
      // 面板被隐藏，可以暂停一些不必要的操作
    }
  });
  
  cleanupFunctions.push(() => {
    if (visibilityWatcher) {
      visibilityWatcher();
      visibilityWatcher = null;
    }
  });
});

// 组件卸载时的清理
onUnmounted(() => {
  console.log(`🧹 Panel unmounting: ${panelId.value}`);
  
  // 执行所有清理函数
  cleanupFunctions.forEach(cleanup => {
    try {
      cleanup();
    } catch (error) {
      console.warn(`Error during cleanup for panel ${panelId.value}:`, error);
    }
  });
  
  // 清空清理函数数组
  cleanupFunctions.length = 0;
  
  // 清理引用
  if (scrollCleanup) {
    scrollCleanup();
    scrollCleanup = null;
  }
  
  if (resizeObserver) {
    resizeObserver.disconnect();
    resizeObserver = null;
  }
  
  if (visibilityWatcher) {
    visibilityWatcher();
    visibilityWatcher = null;
  }
  
  console.log(`✅ Panel cleanup completed: ${panelId.value}`);
});

// 处理关闭事件
const handleClose = () => {
  // 如果提供了visible属性，则通过emit事件让父组件控制可见性
  if (props.visible !== undefined) {
    emit('close', props.id);
    return;
  }
  
  // 否则通过Panel管理器关闭面板
  if (props.id) {
    panelManager.closePanel(props.id);
  }
  // 同时发出关闭事件，保持兼容性
  emit('close', props.id);
};
</script>

<style scoped>
.panel-container {
  display: flex;
  flex-direction: column;
  background-color: var(--color-card-bg);
  border: 1px solid var(--color-card-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
  transition: all var(--transition-normal);
  min-width: 200px;
  height: calc(100% - 16px); /* 减去底部面板的内边距和间距 */
  margin: 8px 0;
  flex-shrink: 0;
}

.panel-hidden {
  display: none;
}

/* 面板头部 */
.panel-header {
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  padding: 8px 16px;
  background-color: var(--color-card-bg);
  border-bottom: 1px solid var(--color-card-divider);
}

.panel-title {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: var(--color-card-title);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 关闭按钮 */
.panel-close-btn {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  width: 24px;
  height: 24px;
  padding: 0;
  background: transparent;
  border: none;
  border-radius: 50%;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--transition-fast);
  color: var(--color-text-secondary);
}

.panel-close-btn:hover {
  background-color: var(--color-hover);
  color: var(--color-text);
}

.close-icon {
  font-size: 16px;
  line-height: 1;
  font-weight: bold;
}

/* 面板内容 */
.panel-content {
  flex: 1;
  padding: 16px;
  overflow: auto;
  color: var(--color-card-description);
  font-size: 14px;
}

/* 拖拽样式 */
.panel-container.drag-handle {
  position: relative;
  z-index: 10;
}
</style>