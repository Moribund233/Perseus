<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'

/**
 * 基础模态框组件
 * 支持标题、自定义内容和底部操作
 */

interface Props {
  /** 是否显示模态框 */
  visible: boolean
  /** 模态框标题 */
  title?: string
  /** 是否显示关闭按钮 */
  closable?: boolean
  /** 是否点击遮罩关闭 */
  maskClosable?: boolean
  /** 宽度 */
  width?: string
}

interface Emits {
  (e: 'update:visible', value: boolean): void
  (e: 'close'): void
}

const props = withDefaults(defineProps<Props>(), {
  title: '',
  closable: true,
  maskClosable: true,
  width: '500px'
})

const emit = defineEmits<Emits>()

/**
 * 关闭模态框
 */
const close = (): void => {
  emit('update:visible', false)
  emit('close')
}

/**
 * 处理遮罩点击
 */
const handleMaskClick = (): void => {
  if (props.maskClosable) {
    close()
  }
}

/**
 * 处理键盘事件
 */
const handleKeydown = (e: KeyboardEvent): void => {
  if (e.key === 'Escape' && props.closable) {
    close()
  }
}

onMounted(() => {
  document.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeydown)
})

/**
 * 阻止事件冒泡
 */
const stopPropagation = (e: Event): void => {
  e.stopPropagation()
}
</script>

<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="visible" class="modal-overlay" @click="handleMaskClick">
        <div
          class="modal-content"
          :style="{ width }"
          @click="stopPropagation"
        >
          <!-- 头部 -->
          <div v-if="title || closable" class="modal-header">
            <h3 v-if="title" class="modal-title">{{ title }}</h3>
            <button
              v-if="closable"
              class="modal-close-btn"
              @click="close"
              aria-label="关闭"
            >
              ×
            </button>
          </div>

          <!-- 内容 -->
          <div class="modal-body">
            <slot />
          </div>

          <!-- 底部 -->
          <div v-if="$slots.footer" class="modal-footer">
            <slot name="footer" />
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: var(--spacing-lg);
}

.modal-content {
  background-color: var(--bg-secondary);
  border-radius: var(--border-radius-lg);
  max-width: 90vw;
  max-height: 90vh;
  overflow-y: auto;
  border: 1px solid var(--border-color);
  box-shadow: var(--shadow-lg);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-lg);
  border-bottom: 1px solid var(--border-color);
}

.modal-title {
  margin: 0;
  font-size: var(--font-size-lg);
  font-weight: 600;
  color: var(--text-primary);
}

.modal-close-btn {
  background: none;
  border: none;
  font-size: var(--font-size-xl);
  color: var(--text-secondary);
  cursor: pointer;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--border-radius-md);
  transition: all var(--transition-fast);
}

.modal-close-btn:hover {
  background-color: var(--bg-tertiary);
  color: var(--text-primary);
}

.modal-body {
  padding: var(--spacing-lg);
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-md);
  padding: var(--spacing-lg);
  border-top: 1px solid var(--border-color);
}

/* 过渡动画 */
.modal-enter-active,
.modal-leave-active {
  transition: opacity var(--transition-normal);
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-active .modal-content,
.modal-leave-active .modal-content {
  transition: transform var(--transition-normal);
}

.modal-enter-from .modal-content,
.modal-leave-to .modal-content {
  transform: scale(0.95);
}
</style>
