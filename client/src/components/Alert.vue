<script setup lang="ts">
/**
 * 基础警告/提示组件
 * 支持多种类型：error, success, warning, info
 */

interface Props {
  /** 提示类型 */
  type?: 'error' | 'success' | 'warning' | 'info'
  /** 是否显示关闭按钮 */
  closable?: boolean
  /** 自定义图标路径（可选） */
  icon?: string
}

interface Emits {
  (e: 'close'): void
}

const props = withDefaults(defineProps<Props>(), {
  type: 'info',
  closable: false,
  icon: undefined
})

const emit = defineEmits<Emits>()

/**
 * 获取默认图标路径
 */
const getDefaultIcon = (): string => {
  const iconMap: Record<string, string> = {
    error: '@/assets/icons/error.svg',
    success: '@/assets/icons/success.svg',
    warning: '@/assets/icons/warning.svg',
    info: '@/assets/icons/info.svg'
  }
  return iconMap[props.type]
}

/**
 * 获取图标样式类
 */
const getIconClass = (): string => {
  const classMap: Record<string, string> = {
    error: 'icon-error',
    success: 'icon-success',
    warning: 'icon-warning',
    info: 'icon-info'
  }
  return classMap[props.type]
}

/**
 * 处理关闭事件
 */
const handleClose = (): void => {
  emit('close')
}
</script>

<template>
  <div class="alert" :class="`alert-${type}`">
    <img
      :src="icon || getDefaultIcon()"
      class="alert-icon"
      :class="getIconClass()"
      :alt="type"
    />
    <span class="alert-content">
      <slot />
    </span>
    <button
      v-if="closable"
      class="alert-close-btn"
      @click="handleClose"
      aria-label="关闭"
    >
      ×
    </button>
  </div>
</template>

<style scoped>
.alert {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-md);
  border-radius: var(--border-radius-md);
  margin-bottom: var(--spacing-md);
}

.alert-icon {
  width: 20px;
  height: 20px;
  min-width: 20px;
  min-height: 20px;
  flex-shrink: 0;
}

.alert-content {
  flex: 1;
}

.alert-close-btn {
  margin-left: auto;
  background: none;
  border: none;
  color: inherit;
  font-size: 20px;
  cursor: pointer;
  padding: 0;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--border-radius-sm);
  opacity: 0.7;
  transition: opacity var(--transition-fast);
}

.alert-close-btn:hover {
  opacity: 1;
  background-color: rgba(0, 0, 0, 0.1);
}

.alert-error {
  background-color: rgba(239, 68, 68, 0.1);
  border: 1px solid var(--error-color);
  color: var(--error-color);
}

.alert-success {
  background-color: rgba(16, 185, 129, 0.1);
  border: 1px solid var(--success-color);
  color: var(--success-color);
}

.alert-warning {
  background-color: rgba(245, 158, 11, 0.1);
  border: 1px solid var(--warning-color);
  color: var(--warning-color);
}

.alert-info {
  background-color: rgba(59, 130, 246, 0.1);
  border: 1px solid var(--primary-color);
  color: var(--primary-color);
}
</style>
