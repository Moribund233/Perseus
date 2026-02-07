<template>
  <Panel title="示例面板1" id="panel1">
    <div class="example-panel-1">
      <h4>示例面板1内容</h4>
      <p>这是第一个示例面板的内容区域，使用新的Panel系统架构。</p>
      <div class="panel-info">
        <p>面板ID: panel1</p>
        <p>状态: 活跃</p>
        <p>架构: 新Panel系统</p>
      </div>
      
      <div class="feature-demo">
        <h5>新功能特性：</h5>
        <ul>
          <li>✅ 统一Panel管理</li>
          <li>✅ 动态组件加载</li>
          <li>✅ 状态集中管理</li>
          <li>✅ 简化组件结构</li>
        </ul>
      </div>
    </div>
  </Panel>
</template>

<script setup lang="ts">
import Panel from '../public/Panel.vue';

// Panel公共组件自动处理可见性和关闭逻辑
</script>

<style scoped>
.example-panel-1 {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 8px;
}

.example-panel-1 h4 {
  margin: 0;
  font-size: 1.1rem;
  color: var(--color-text);
  border-bottom: 1px solid var(--color-card-divider);
  padding-bottom: 8px;
}

.example-panel-1 h5 {
  margin: 0 0 8px 0;
  font-size: 1rem;
  color: var(--color-text);
}

.panel-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 12px;
  background-color: var(--color-card-divider);
  border-radius: var(--radius-sm);
  border-left: 3px solid var(--color-primary);
}

.panel-info p {
  margin: 0;
  font-size: 0.9rem;
  color: var(--color-text-secondary);
}

.feature-demo {
  margin-top: 8px;
}

.feature-demo ul {
  margin: 0;
  padding-left: 20px;
  list-style: none;
}

.feature-demo li {
  margin: 4px 0;
  font-size: 0.9rem;
  color: var(--color-text-secondary);
}
</style>