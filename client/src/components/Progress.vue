<script setup lang="ts">
/**
 * 进度条组件
 */
interface Props {
  /** 进度百分比 (0-100) */
  percent: number
  /** 是否显示文字 */
  showText?: boolean
  /** 进度条高度 */
  height?: string
  /** 主题色 */
  type?: 'primary' | 'success' | 'warning' | 'error'
}

const props = withDefaults(defineProps<Props>(), {
  showText: true,
  height: '8px',
  type: 'primary'
})

const typeColors = {
  primary: 'var(--primary-color)',
  success: 'var(--success-color)',
  warning: 'var(--warning-color)',
  error: 'var(--error-color)'
}

const color = typeColors[props.type]
</script>

<template>
  <div class="progress-wrapper">
    <div class="progress-bar" :style="{ height }">
      <div
        class="progress-fill"
        :style="{
          width: `${Math.min(100, Math.max(0, percent))}%`,
          backgroundColor: color
        }"
      />
    </div>
    <span v-if="showText" class="progress-text">{{ Math.round(percent) }}%</span>
  </div>
</template>

<style scoped>
.progress-wrapper {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.progress-bar {
  flex: 1;
  background-color: var(--bg-tertiary);
  border-radius: var(--border-radius-sm);
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  border-radius: var(--border-radius-sm);
  transition: width 0.3s ease;
}

.progress-text {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  min-width: 40px;
  text-align: right;
}
</style>
