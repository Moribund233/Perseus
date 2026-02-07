<template>
  <Panel title="示例面板2" id="panel2">
    <div class="example-panel-2">
      <h4>数据分析面板</h4>
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-value">1,234</div>
          <div class="stat-label">总访问量</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">567</div>
          <div class="stat-label">活跃用户</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">89%</div>
          <div class="stat-label">完成率</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">4.5</div>
          <div class="stat-label">平均评分</div>
        </div>
      </div>
      
      <div class="chart-placeholder">
        <h5>趋势图表</h5>
        <div class="chart-area">
          <div class="chart-bar" style="height: 40%"></div>
          <div class="chart-bar" style="height: 60%"></div>
          <div class="chart-bar" style="height: 80%"></div>
          <div class="chart-bar" style="height: 45%"></div>
          <div class="chart-bar" style="height: 70%"></div>
          <div class="chart-bar" style="height: 90%"></div>
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
.example-panel-2 {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 8px;
}

.example-panel-2 h4 {
  margin: 0;
  font-size: 1.1rem;
  color: var(--color-text);
  border-bottom: 1px solid var(--color-card-divider);
  padding-bottom: 8px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.stat-card {
  background: var(--color-card-bg);
  border: 1px solid var(--color-card-border);
  border-radius: var(--radius-sm);
  padding: 16px;
  text-align: center;
  transition: all var(--transition-fast);
}

.stat-card:hover {
  border-color: var(--color-primary);
  box-shadow: var(--shadow-sm);
}

.stat-value {
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--color-primary);
  margin-bottom: 4px;
}

.stat-label {
  font-size: 0.8rem;
  color: var(--color-text-secondary);
}

.chart-placeholder {
  margin-top: 8px;
}

.chart-placeholder h5 {
  margin: 0 0 12px 0;
  font-size: 1rem;
  color: var(--color-text);
}

.chart-area {
  display: flex;
  align-items: end;
  gap: 8px;
  height: 120px;
  padding: 16px;
  background: var(--color-card-divider);
  border-radius: var(--radius-sm);
}

.chart-bar {
  flex: 1;
  background: linear-gradient(to top, var(--color-primary), var(--color-primary-light));
  border-radius: var(--radius-sm) var(--radius-sm) 0 0;
  min-height: 20px;
  transition: all var(--transition-normal);
}

.chart-bar:hover {
  background: linear-gradient(to top, var(--color-primary-hover), var(--color-primary));
}
</style>