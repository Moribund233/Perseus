<!-- 
  公共组件: 辅助侧边栏工具容器
  用途: 辅助侧边栏内的独立工具模块容器
  特性:
    - 与辅助侧边栏宽度一致
    - 支持自由调整高度
    - 顶部居中标题
    - 右上角关闭按钮
    - 支持显隐控制
    - 封装可见性和关闭逻辑
    - 内置通信机制，支持工具与页面间消息传递（基于事件总线）
-->
<template>
  <div ref="toolRef" class="tool-container" :class="{ 'tool-hidden': !isVisible }">
    <!-- 工具头部 -->
    <div class="tool-header">
      <h3 class="tool-title">{{ title }}</h3>
      <button v-if="showClose" class="tool-close-btn" @click="handleClose">
        <span class="close-icon">×</span>
      </button>
    </div>
    
    <!-- 工具内容区域 -->
    <div ref="contentRef" class="tool-content scrollbar-thin">
      <slot 
        :sendMessage="sendMessage" 
        :sendMessageToTargets="sendMessageToTargets" 
        :onMessage="onMessage"
      ></slot>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useDrag } from '@/utils/Drag';
import { useScroll } from '@/utils/Scroll';
import { onMounted, ref, computed, onUnmounted, provide } from 'vue';
import { useUIStore } from '@/stores/ui';
import { toolManager } from '@/utils/Tool';
import { 
  sendToolMessage, 
  sendMessageToTargets as busSendMessageToTargets,
  onToolMessage,
  registerTool,
  unregisterTool
} from '@/utils/eventBus';

// 组件属性
interface ToolProps {
  title: string; // 工具标题
  id?: string; // 工具唯一标识
  visible?: boolean; // 是否可见
  showClose?: boolean; // 是否显示关闭按钮
  enableCommunication?: boolean; // 是否启用通信机制
  messageTargets?: string[]; // 默认消息目标
}

const props = withDefaults(defineProps<ToolProps>(), {
  id: '',
  visible: undefined,
  showClose: true,
  enableCommunication: true,
  messageTargets: () => []
});

// 存储
const uiStore = useUIStore();
const toolId = computed(() => props.id || `tool-${props.title}`);

// 组件事件
const emit = defineEmits<{
  close: [id?: string]; // 关闭事件
  message: [message: any]; // 消息事件
}>();

// 计算可见性：优先使用props.visible，如果没有则通过Tool管理器获取
const isVisible = computed(() => {
  if (props.visible !== undefined) {
    return props.visible;
  }
  const managedVisible = toolManager.isToolVisible(toolId.value);
  return managedVisible !== false ? true : false;
});

// 消息监听器存储
const messageListeners = new Map<string, (data: any, message: any) => void>();

// 发送消息
const sendMessage = (target: string, type: string, data: any) => {
  if (!props.enableCommunication) return;
  sendToolMessage(toolId.value, target, type, data);
};

// 发送消息到多个目标
const sendMessageToTargets = (type: string, data: any) => {
  if (!props.enableCommunication || props.messageTargets.length === 0) return;
  busSendMessageToTargets(toolId.value, props.messageTargets, type, data);
};

// 监听消息
const onMessage = (type: string, callback: (data: any, message: any) => void) => {
  if (!props.enableCommunication) return;
  
  messageListeners.set(type, callback);
  const unsubscribe = onToolMessage(toolId.value, type, callback);
  
  return unsubscribe;
};

// 提供通信方法给子组件
provide('toolCommunication', {
  sendMessage,
  sendMessageToTargets,
  onMessage,
  toolId: toolId.value
});

// 工具引用
const { elementRef: toolRef } = useDrag({
  direction: ['top', 'bottom'],
  onDrag: (size, direction) => {
    console.log(`Tool resized: ${size}px in direction ${direction}`);
  },
  onDragEnd: () => {
    if (toolRef.value) {
      const height = toolRef.value.offsetHeight;
      const currentToolSet = toolManager.getCurrentToolSet();
      uiStore.saveToolSize(toolId.value, { height }, currentToolSet);
    }
  }
});

// 内容区域引用
const contentRef = ref<HTMLElement | null>(null);

// 使用Scroll系统
onMounted(() => {
  if (contentRef.value) {
    useScroll(contentRef.value, {
      direction: 'both',
      showScrollbar: false
    });
  }
  
  if (toolRef.value) {
    const currentToolSet = toolManager.getCurrentToolSet();
    const savedSize = uiStore.getToolSize(toolId.value, currentToolSet);
    if (savedSize) {
      toolRef.value.style.height = `${savedSize.height}px`;
    }
  }
  
  if (props.enableCommunication) {
    registerTool(toolId.value);
  }
});

// 组件卸载时清理
onUnmounted(() => {
  if (props.enableCommunication) {
    messageListeners.clear();
    unregisterTool(toolId.value);
    console.log(`[Tool] ${toolId.value} communication cleanup completed`);
  }
});

// 处理关闭事件
const handleClose = () => {
  if (props.visible !== undefined) {
    emit('close', props.id);
    return;
  }
  
  if (props.id) {
    toolManager.closeTool(props.id);
  }
  emit('close', props.id);
};
</script>

<style scoped>
.tool-container {
  display: flex;
  flex-direction: column;
  background-color: var(--color-card-bg);
  border: 1px solid var(--color-card-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
  transition: all var(--transition-normal);
  min-height: 150px;
  width: calc(100% - 16px);
  margin: 8px;
  flex-shrink: 0;
}

.tool-hidden {
  display: none;
}

.tool-header {
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  padding: 8px 16px;
  background-color: var(--color-card-bg);
  border-bottom: 1px solid var(--color-card-divider);
}

.tool-title {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: var(--color-card-title);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.tool-close-btn {
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

.tool-close-btn:hover {
  background-color: var(--color-hover);
  color: var(--color-text);
}

.close-icon {
  font-size: 16px;
  line-height: 1;
  font-weight: bold;
}

.tool-content {
  flex: 1;
  padding: 16px;
  overflow: auto;
  color: var(--color-card-description);
  font-size: 14px;
}

.tool-container.drag-handle {
  position: relative;
  z-index: 10;
}
</style>
