<template>
  <div class="bottom-panel" ref="elementRef">
    <!-- 使用PanelView统一渲染所有活跃面板 -->
    <PanelView />
    
    <!-- 新的添加面板区域 -->
    <div class="add-panel-area">
      <!-- 模式1：添加按钮模式 -->
      <div v-if="!showInactiveList" class="add-button-mode">
        <button class="add-button" @click="toggleInactiveList">
          <img src="@/assets/icons/add.svg" alt="添加面板" class="add-icon" />
          <span>添加面板</span>
        </button>
      </div>
      
      <!-- 模式2：非活跃面板列表 -->
      <div v-else class="inactive-panel-list">
        <div class="list-header">
          <h4>非活跃面板</h4>
          <button class="back-button" @click="toggleInactiveList">
            <span>返回</span>
          </button>
        </div>
        <div class="panel-list">
          <div 
            v-for="panel in inactivePanels" 
            :key="panel.id"
            class="panel-item"
            @click="activatePanel(panel.id)"
          >
            <span class="panel-title">{{ panel.title }}</span>
            <span class="activate-text">激活</span>
          </div>
          <div v-if="inactivePanels.length === 0" class="no-panels">
            暂无非活跃面板
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import PanelView from '@/components/views/PanelView.vue';
import { enableDrag } from '@/utils/Drag'
import { panelManager } from '@/utils/Panel';

const elementRef = ref<HTMLElement>()

// 控制是否显示非活跃面板列表
const showInactiveList = ref(false);

// 获取所有面板配置
const allPanels = panelManager.getAllPanels();

// 计算非活跃面板列表（未显示的面板）
const inactivePanels = computed(() => {
  const visiblePanelIds = panelManager.getVisiblePanelIds();
  return allPanels.filter(panel => !visiblePanelIds.includes(panel.id));
});

// 切换显示非活跃面板列表
const toggleInactiveList = () => {
  showInactiveList.value = !showInactiveList.value;
};

// 激活选中的面板
const activatePanel = (panelId: string) => {
  panelManager.showPanel(panelId);
  // 激活后返回按钮模式
  showInactiveList.value = false;
};

onMounted(() => {
  if (elementRef.value) {
    enableDrag(elementRef.value, {
      direction: 'top',
    })
  };
})
</script>

<style scoped>

/* 添加面板区域样式 */
.add-panel-area {
  height: 100%;
  min-width: 200px;
  background-color: var(--color-bg-secondary);
  border-left: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
}

/* 添加按钮模式样式 */
.add-button-mode {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: 20px;
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

/* 非活跃面板列表样式 */
.inactive-panel-list {
  height: 100%;
  display: flex;
  flex-direction: column;
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

.panel-list {
  flex: 1;
  overflow-y: auto;
  padding: 15px;
}

.panel-item {
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

.panel-item:hover {
  background-color: var(--color-bg-hover);
  border-color: var(--color-primary);
  transform: translateX(4px);
}

.panel-title {
  font-size: 14px;
  color: var(--color-text);
  font-weight: 500;
}

.activate-text {
  font-size: 12px;
  color: var(--color-primary);
  font-weight: 600;
}

.no-panels {
  text-align: center;
  padding: 40px 20px;
  color: var(--color-text-secondary);
  font-size: 14px;
  font-style: italic;
}
</style>