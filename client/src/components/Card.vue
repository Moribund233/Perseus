<script setup lang="ts">
import { computed } from 'vue'

/**
 * 基础卡片组件
 * 支持标题、副标题和自定义操作区域
 */

interface Props {
  /** 卡片标题 */
  title?: string
  /** 卡片副标题 */
  subtitle?: string
  /** 是否显示边框 */
  bordered?: boolean
  /** 是否显示阴影 */
  shadow?: boolean
  /** 自定义类名 */
  customClass?: string
}

const props = withDefaults(defineProps<Props>(), {
  title: undefined,
  subtitle: undefined,
  bordered: true,
  shadow: false,
  customClass: ''
})

/**
 * 计算卡片类名
 */
const cardClass = computed((): string => {
  const classes = ['card']
  if (props.bordered) {
    classes.push('card-bordered')
  }
  if (props.shadow) {
    classes.push('card-shadow')
  }
  if (props.customClass) {
    classes.push(props.customClass)
  }
  return classes.join(' ')
})
</script>

<template>
  <div :class="cardClass">
    <!-- 卡片头部 -->
    <div v-if="title || $slots.header || $slots.actions" class="card-header">
      <div v-if="title || subtitle" class="card-header-content">
        <h2 v-if="title" class="card-title">{{ title }}</h2>
        <p v-if="subtitle" class="card-subtitle">{{ subtitle }}</p>
      </div>
      <slot name="header" />
      <div v-if="$slots.actions" class="card-actions">
        <slot name="actions" />
      </div>
    </div>

    <!-- 卡片内容 -->
    <div class="card-body">
      <slot />
    </div>

    <!-- 卡片底部 -->
    <div v-if="$slots.footer" class="card-footer">
      <slot name="footer" />
    </div>
  </div>
</template>

<style scoped>
.card {
  background-color: var(--bg-secondary);
  border-radius: var(--border-radius-md);
  overflow: hidden;
}

.card-bordered {
  border: 1px solid var(--border-color);
}

.card-shadow {
  box-shadow: var(--shadow-md);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-lg);
  border-bottom: 1px solid var(--border-color);
  gap: var(--spacing-md);
}

.card-header-content {
  flex: 1;
}

.card-title {
  font-size: var(--font-size-lg);
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.card-subtitle {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  margin: var(--spacing-xs) 0 0 0;
}

.card-actions {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.card-body {
  padding: var(--spacing-lg);
}

.card-footer {
  padding: var(--spacing-md) var(--spacing-lg);
  border-top: 1px solid var(--border-color);
  background-color: var(--bg-tertiary);
}
</style>
