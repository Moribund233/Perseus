<script setup lang="ts">
import { computed } from 'vue'

/**
 * 状态徽章组件
 * 用于显示各种状态标签
 */

interface Props {
  /** 状态类型 */
  status: 'running' | 'stopped' | 'error' | 'warning' | 'success' | 'info' | 'default' | string
  /** 显示的文本（可选，默认根据状态自动显示） */
  text?: string
  /** 是否显示圆点 */
  showDot?: boolean
  /** 尺寸 */
  size?: 'sm' | 'md' | 'lg'
}

const props = withDefaults(defineProps<Props>(), {
  text: undefined,
  showDot: true,
  size: 'md'
})

/**
 * 状态文本映射
 */
const statusTextMap: Record<string, string> = {
  running: '运行中',
  stopped: '已停止',
  error: '错误',
  warning: '警告',
  success: '成功',
  info: '信息',
  default: '未知'
}

/**
 * 获取显示文本
 */
const displayText = computed((): string => {
  return props.text || statusTextMap[props.status] || props.status
})

/**
 * 计算徽章类名
 */
const badgeClass = computed((): string => {
  const classes = ['status-badge', `status-${props.status}`, `size-${props.size}`]
  if (props.showDot) {
    classes.push('with-dot')
  }
  return classes.join(' ')
})
</script>

<template>
  <span :class="badgeClass">
    <span v-if="showDot" class="status-dot"></span>
    <span class="status-text">{{ displayText }}</span>
  </span>
</template>

<style scoped>
.status-badge {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-xs);
  border-radius: var(--border-radius-md);
  font-weight: 500;
  white-space: nowrap;
}

/* 尺寸 */
.size-sm {
  padding: 2px 8px;
  font-size: var(--font-size-xs);
}

.size-md {
  padding: var(--spacing-xs) var(--spacing-sm);
  font-size: var(--font-size-sm);
}

.size-lg {
  padding: var(--spacing-sm) var(--spacing-md);
  font-size: var(--font-size-md);
}

/* 状态点 */
.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

/* 状态样式 */
.status-running {
  background-color: rgba(16, 185, 129, 0.2);
  color: var(--success-color);
}

.status-running .status-dot {
  background-color: var(--success-color);
  box-shadow: 0 0 8px var(--success-color);
}

.status-stopped {
  background-color: rgba(16, 185, 129, 0.2);
  color: var(--text-muted);
}

.status-stopped .status-dot {
  background-color: var(--text-muted);
}

.status-error {
  background-color: rgba(239, 68, 68, 0.2);
  color: var(--error-color);
}

.status-error .status-dot {
  background-color: var(--error-color);
}

.status-warning {
  background-color: rgba(245, 158, 11, 0.2);
  color: var(--warning-color);
}

.status-warning .status-dot {
  background-color: var(--warning-color);
}

.status-success {
  background-color: rgba(16, 185, 129, 0.2);
  color: var(--success-color);
}

.status-success .status-dot {
  background-color: var(--success-color);
}

.status-info {
  background-color: rgba(59, 130, 246, 0.2);
  color: var(--primary-color);
}

.status-info .status-dot {
  background-color: var(--primary-color);
}

.status-default {
  background-color: var(--bg-tertiary);
  color: var(--text-secondary);
}

.status-default .status-dot {
  background-color: var(--text-muted);
}
</style>
