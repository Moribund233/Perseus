<!-- 
 公共组件: 灵动岛
 用途: 用于切换子路由
 显示位置 : 主内容区域底部居中
 调用 : 示例：<Island config="Debug"></Island>
 配置方式 : 由config/island.json配置
 特性
    1. 支持自定义配置，通过config属性指定配置内容
    2. 父路由检测,为所有子路由保留灵动岛显示
    3. 两种形态：默认线条状，鼠标悬停时变为岛状并渲染图标
-->
<template>
  <div 
    class="island-container" 
    :class="{ 'island-hovered': isHovered }"
    v-if="!isBottomPanelVisible && !isAuxSidebarVisible"
  >
    <!-- 线条状形态 -->
    <div class="island-line"></div>
    
    <!-- 岛状形态 - 路由切换器 -->
    <div class="island-switcher">
      <button
        v-for="(item, index) in islandItems"
        :key="item.route || index"
        class="island-item"
        :class="{ 'island-item-active': isActive(item.route) }"
        @click="navigateTo(item.route)"
        :title="item.name"
      >
        <img v-if="item.icon" :src="item.icon" :alt="item.name" class="island-icon">
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { useQuickSetting } from '@/stores/quickSetting';

// 组件属性
interface IslandProps {
  config: string; // 配置名称
}

const props = defineProps<IslandProps>();

// 路由实例
const router = useRouter();
const route = useRoute();

// 获取底部面板可见状态和辅助侧边栏可见状态
const { isBottomPanelVisible, isAuxSidebarVisible } = useQuickSetting();

// 状态管理
const isHovered = ref(false);
const islandItems = ref<any[]>([]);

// 计算当前激活的路由
const isActive = (routePath: string) => {
  return route.path === routePath;
};

// 路由导航
const navigateTo = (routePath: string) => {
  router.push(routePath);
};

// 加载配置
const loadConfig = async () => {
  try {
    const islandConfig = await import('../../config/Island.json');
    // 安全访问配置，避免类型错误
    const config = (islandConfig.default as Record<string, any[]>)[props.config] || [];
    islandItems.value = config;
  } catch (error) {
    console.error('Failed to load island config:', error);
    islandItems.value = [];
  }
};

// 监听配置变化
watch(() => props.config, () => {
  loadConfig();
});

// 组件挂载时加载配置
onMounted(() => {
  loadConfig();
});
</script>

<style scoped>
.island-container {
  position: fixed;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  justify-content: center;
  width: fit-content;
  cursor: pointer;
  transition: all 0.3s ease;
  z-index: 1000;
}

/* 线条状形态 - 默认 */
.island-line {
  width: 80px;
  height: 4px;
  background-color: var(--color-card-border);
  border-radius: 2px;
  transition: all 0.3s ease;
}

/* 岛状形态 - 鼠标悬停时显示 */
.island-switcher {
  position: absolute;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%) translateY(100%);
  display: flex;
  gap: 8px;
  padding: 8px;
  background-color: var(--color-card-bg);
  border: 1px solid var(--color-card-border);
  border-radius: 20px;
  box-shadow: var(--shadow-md);
  opacity: 0;
  visibility: hidden;
  transition: all 0.3s ease;
}

/* 鼠标悬停时的形态变化 */
.island-container:hover {
  .island-line {
    opacity: 0;
    visibility: hidden;
  }
  
  .island-switcher {
    opacity: 1;
    visibility: visible;
    transform: translateX(-50%) translateY(0);
  }
}

/* 岛状形态下的容器样式 */
.island-container.island-hovered {
  .island-line {
    opacity: 0;
    visibility: hidden;
  }
  
  .island-switcher {
    opacity: 1;
    visibility: visible;
    transform: translateX(-50%) translateY(0);
  }
}

/* 路由项样式 */
.island-item {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 8px;
  background-color: transparent;
  border: none;
  border-radius: 16px;
  color: var(--color-text);
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.island-item:hover {
  background-color: var(--color-hover);
}

.island-item-active {
  background-color: var(--color-primary);
  color: white;
}

/* 图标样式 */
.island-icon {
  width: 16px;
  height: 16px;
  filter: var(--color-icon-filter);
}

.island-item-active .island-icon {
  filter: brightness(0) invert(1);
}
</style>