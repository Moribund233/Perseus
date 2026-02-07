<template>
  <Panel title="设置面板" id="panel3">
    <div class="settings-panel">
      <h4>系统设置</h4>
      
      <div class="settings-section">
        <h5>显示设置</h5>
        <div class="setting-item">
          <label class="setting-label">
            <input type="checkbox" checked />
            <span>启用深色模式</span>
          </label>
        </div>
        <div class="setting-item">
          <label class="setting-label">
            <input type="checkbox" checked />
            <span>显示滚动条</span>
          </label>
        </div>
      </div>

      <div class="settings-section">
        <h5>面板设置</h5>
        <div class="setting-item">
          <label class="setting-label">
            <span>面板宽度</span>
            <select class="setting-select">
              <option>自动</option>
              <option>固定</option>
              <option>最小</option>
            </select>
          </label>
        </div>
        <div class="setting-item">
          <label class="setting-label">
            <span>动画效果</span>
            <input type="range" min="0" max="100" value="75" class="setting-slider" />
          </label>
        </div>
      </div>

      <div class="settings-section">
        <h5>系统信息</h5>
        <div class="info-grid">
          <div class="info-item">
            <span class="info-label">版本:</span>
            <span class="info-value">v1.0.0</span>
          </div>
          <div class="info-item">
            <span class="info-label">构建:</span>
            <span class="info-value">20241231</span>
          </div>
          <div class="info-item">
            <span class="info-label">平台:</span>
            <span class="info-value">Windows</span>
          </div>
        </div>
      </div>
    </div>
  </Panel>
</template>

<script setup lang="ts">
import Panel from '../public/Panel.vue';

// Panel公共组件自动处理可见性和关闭逻辑
</script>

<style scoped>
.settings-panel {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 8px;
}

.settings-panel h4 {
  margin: 0;
  font-size: 1.1rem;
  color: var(--color-text);
  border-bottom: 1px solid var(--color-card-divider);
  padding-bottom: 8px;
}

.settings-section {
  border: 1px solid var(--color-card-border);
  border-radius: var(--radius-sm);
  padding: 16px;
  background: var(--color-card-bg);
}

.settings-section h5 {
  margin: 0 0 12px 0;
  font-size: 1rem;
  color: var(--color-text);
  border-bottom: 1px solid var(--color-card-divider);
  padding-bottom: 8px;
}

.setting-item {
  margin: 12px 0;
}

.setting-label {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  font-size: 0.9rem;
  color: var(--color-text-secondary);
  cursor: pointer;
}

.setting-label input[type="checkbox"] {
  margin-right: 8px;
}

.setting-select {
  padding: 4px 8px;
  border: 1px solid var(--color-card-border);
  border-radius: var(--radius-sm);
  background: var(--color-card-bg);
  color: var(--color-text);
  font-size: 0.8rem;
}

.setting-slider {
  width: 80px;
  accent-color: var(--color-primary);
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 12px;
}

.info-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px;
  background: var(--color-card-divider);
  border-radius: var(--radius-sm);
}

.info-label {
  font-size: 0.8rem;
  color: var(--color-text-secondary);
}

.info-value {
  font-size: 0.9rem;
  color: var(--color-text);
  font-weight: 500;
}
</style>