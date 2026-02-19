<script setup lang="ts">
import { computed } from 'vue'

/**
 * 基础按钮组件
 * 支持多种类型和尺寸
 */

interface Props {
  /** 按钮类型 */
  type?: 'primary' | 'secondary' | 'success' | 'error' | 'warning' | 'info'
  /** 按钮尺寸 */
  size?: 'sm' | 'md' | 'lg'
  /** 是否禁用 */
  disabled?: boolean
  /** 是否显示加载状态 */
  loading?: boolean
  /** 是否为块级按钮 */
  block?: boolean
  /** 图标路径（可选） */
  icon?: string
  /** 图标类名（可选） */
  iconClass?: string
}

const props = withDefaults(defineProps<Props>(), {
  type: 'secondary',
  size: 'md',
  disabled: false,
  loading: false,
  block: false,
  icon: undefined,
  iconClass: undefined
})

// 加载图标路径
const loaderIcon = new URL('../assets/icons/loader.svg', import.meta.url).href

/**
 * 计算按钮类名
 */
const buttonClass = computed((): string => {
  const classes = ['btn', `btn-${props.type}`, `btn-${props.size}`]
  if (props.block) {
    classes.push('btn-block')
  }
  return classes.join(' ')
})
</script>

<template>
  <button
    :class="buttonClass"
    :disabled="disabled || loading"
  >
    <img
      v-if="loading"
      :src="loaderIcon"
      class="btn-icon spinning"
      alt="loading"
    />
    <img
      v-else-if="icon"
      :src="icon"
      class="btn-icon"
      :class="iconClass"
      alt="icon"
    />
    <slot />
  </button>
</template>

<style scoped>
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-sm);
  border: none;
  border-radius: var(--border-radius-md);
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition-fast);
  white-space: nowrap;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 按钮尺寸 */
.btn-sm {
  padding: var(--spacing-xs) var(--spacing-sm);
  font-size: var(--font-size-sm);
}

.btn-md {
  padding: var(--spacing-sm) var(--spacing-md);
  font-size: var(--font-size-md);
}

.btn-lg {
  padding: var(--spacing-md) var(--spacing-lg);
  font-size: var(--font-size-lg);
}

/* 按钮类型 */
.btn-primary {
  background-color: var(--primary-color);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background-color: var(--primary-hover);
}

.btn-secondary {
  background-color: var(--bg-tertiary);
  color: var(--text-primary);
}

.btn-secondary:hover:not(:disabled) {
  background-color: #475569;
}

.btn-success {
  background-color: var(--success-color);
  color: white;
}

.btn-success:hover:not(:disabled) {
  background-color: #059669;
}

.btn-error {
  background-color: var(--error-color);
  color: white;
}

.btn-error:hover:not(:disabled) {
  background-color: #dc2626;
}

.btn-warning {
  background-color: var(--warning-color);
  color: white;
}

.btn-warning:hover:not(:disabled) {
  background-color: #d97706;
}

.btn-info {
  background-color: var(--info-color);
  color: white;
}

.btn-info:hover:not(:disabled) {
  background-color: #0891b2;
}

/* 块级按钮 */
.btn-block {
  width: 100%;
}

/* 按钮图标 */
.btn-icon {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
}

.btn-sm .btn-icon {
  width: 14px;
  height: 14px;
}

.btn-lg .btn-icon {
  width: 20px;
  height: 20px;
}

/* 旋转动画 */
.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
