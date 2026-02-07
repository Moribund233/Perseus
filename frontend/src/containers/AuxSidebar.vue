<template>
  <div class="aux-sidebar scrollbar-hide scroll-smooth" ref="elementRef">
    <!-- 使用ToolView统一渲染所有活跃工具 -->
    <ToolView :config="currentToolSet" />
    
    <!-- 新的添加工具区域 -->
    <div class="add-tool-area">
      <!-- 模式1：添加按钮模式 -->
      <div v-if="!showInactiveList" class="add-button-mode">
        <button class="add-button" @click="toggleInactiveList">
          <img src="@/assets/icons/add.svg" alt="添加工具" class="add-icon" />
          <span>添加工具</span>
        </button>
      </div>
      
      <!-- 模式2：非活跃工具列表 -->
      <div v-else class="inactive-tool-list">
        <div class="list-header">
          <h4>非活跃工具</h4>
          <button class="back-button" @click="toggleInactiveList">
            <span>返回</span>
          </button>
        </div>
        <div class="tool-list">
          <div 
            v-for="tool in inactiveTools" 
            :key="tool.id"
            class="tool-item"
            @click="activateTool(tool.id)"
          >
            <span class="tool-title">{{ tool.title }}</span>
            <span class="activate-text">激活</span>
          </div>
          <div v-if="inactiveTools.length === 0" class="no-tools">
            暂无非活跃工具
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { enableDrag } from '@/utils/Drag'
import ToolView from '@/components/views/ToolView.vue'
import { toolManager } from '@/utils/Tool'

const elementRef = ref<HTMLElement>()
const route = useRoute()

// 控制是否显示非活跃工具列表
const showInactiveList = ref(false)

// 路由与工具集配置映射
const routeToToolSetMap: Record<string, string> = {
  'Example1': 'example1', // Example1路由对应example1工具集
  // 可以添加更多路由映射
};

// 计算当前工具集
const currentToolSet = computed(() => {
  // 根据路由名称获取对应的工具集配置
  const toolSet = routeToToolSetMap[route.name as string] || 'default';
  return toolSet;
});

// 计算所有工具（响应式）
const allTools = computed(() => toolManager.getAllTools())

// 计算非活跃工具列表（未显示的工具）
const inactiveTools = computed(() => {
  const visibleToolIds = toolManager.getVisibleToolIds()
  return allTools.value.filter(tool => !visibleToolIds.includes(tool.id))
})

// 切换显示非活跃工具列表
const toggleInactiveList = () => {
  showInactiveList.value = !showInactiveList.value
}

// 激活选中的工具
const activateTool = (toolId: string) => {
  toolManager.showTool(toolId)
  // 激活后返回按钮模式
  showInactiveList.value = false
}

onMounted(() => {
  if (elementRef.value) {
    enableDrag(elementRef.value, {
      direction: 'left',
    })
  }
})
</script>

<style scoped>
/* 添加工具区域样式 */
.add-tool-area {
  width: 100%;
  padding: 8px;
  display: flex;
  justify-content: center;
}

/* 添加按钮模式样式 */
.add-button-mode {
  width: 100%;
  display: flex;
  justify-content: center;
}

.add-button {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: none;
  border: 2px dashed var(--color-border);
  border-radius: 8px;
  padding: 15px;
  cursor: pointer;
  transition: all 0.3s ease;
  color: var(--color-text-secondary);
  width: 120px;
  height: 120px;
}

.add-button:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
  background-color: var(--color-primary-bg);
  transform: scale(1.05);
}

.add-icon {
  width: 40px;
  height: 40px;
  margin-bottom: 10px;
  opacity: 0.7;
}

.add-button:hover .add-icon {
  opacity: 1;
}

.add-button span {
  font-size: 14px;
  font-weight: 500;
}

/* 非活跃工具列表样式 */
.inactive-tool-list {
  width: 100%;
  background-color: var(--color-bg);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-md);
  overflow: hidden;
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px 20px;
  border-bottom: 1px solid var(--color-border);
  background-color: var(--color-bg);
}

.list-header h4 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text);
}

.back-button {
  background: none;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  padding: 6px 12px;
  cursor: pointer;
  font-size: 13px;
  color: var(--color-text-secondary);
  transition: all 0.2s;
}

.back-button:hover {
  background-color: var(--color-bg-hover);
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.tool-list {
  max-height: 300px;
  overflow-y: auto;
  padding: 15px;
}

.tool-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  margin-bottom: 8px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
  border: 1px solid var(--color-border);
  background-color: var(--color-bg);
}

.tool-item:hover {
  background-color: var(--color-bg-hover);
  border-color: var(--color-primary);
  transform: translateX(4px);
}

.tool-title {
  font-size: 14px;
  color: var(--color-text);
  font-weight: 500;
}

.activate-text {
  font-size: 12px;
  color: var(--color-primary);
  font-weight: 600;
}

.no-tools {
  text-align: center;
  padding: 40px 20px;
  color: var(--color-text-secondary);
  font-size: 14px;
  font-style: italic;
}
</style>