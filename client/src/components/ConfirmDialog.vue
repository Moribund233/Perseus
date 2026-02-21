<script setup lang="ts">
import { computed } from 'vue'
import Modal from './Modal.vue'
import Button from './Button.vue'

/**
 * 确认对话框组件
 *
 * 提供标准化的确认对话框，支持：
 * - 普通确认（单步）
 * - 危险操作确认（双步）
 * - 文本输入验证
 * - 多种对话框类型（info/warning/danger）
 */

interface Props {
  /** 是否显示 */
  visible: boolean
  /** 对话框标题 */
  title?: string
  /** 对话框类型 */
  type?: 'info' | 'warning' | 'danger'
  /** 是否使用双步确认 */
  twoStep?: boolean
  /** 当前步骤（双步确认时使用） */
  step?: 1 | 2
  /** 主消息内容 */
  message: string
  /** 提示信息（副文本） */
  hint?: string
  /** 取消按钮文本 */
  cancelText?: string
  /** 确认按钮文本 */
  confirmText?: string
  /** 是否需要文本输入验证 */
  requireInput?: boolean
  /** 期望输入的文本 */
  expectedInput?: string
  /** 输入框占位符 */
  inputPlaceholder?: string
  /** 是否正在处理中 */
  loading?: boolean
}

interface Emits {
  (e: 'update:visible', value: boolean): void
  (e: 'cancel'): void
  (e: 'confirm'): void
  (e: 'update:input', value: string): void
}

const props = withDefaults(defineProps<Props>(), {
  title: '',
  type: 'info',
  twoStep: false,
  step: 1,
  hint: '',
  cancelText: '取消',
  confirmText: '确认',
  requireInput: false,
  expectedInput: '',
  inputPlaceholder: '',
  loading: false
})

const emit = defineEmits<Emits>()

/**
 * 当前显示的标题
 */
const displayTitle = computed(() => {
  if (props.title) return props.title
  if (props.twoStep) {
    return props.step === 1 ? '确认操作' : '最终确认'
  }
  return '确认'
})

/**
 * 图标类型
 */
const iconType = computed(() => {
  if (props.type === 'danger') return 'danger'
  if (props.type === 'warning') return 'warning'
  return 'info'
})

/**
 * 图标字符
 */
const iconChar = computed(() => {
  const icons: Record<string, string> = {
    info: 'ℹ️',
    warning: '⚠️',
    danger: '🚨'
  }
  return icons[iconType.value] || icons.info
})

/**
 * 确认按钮类型
 */
const confirmButtonType = computed(() => {
  if (props.twoStep && props.step === 2) return 'error'
  if (props.type === 'danger') return 'error'
  if (props.type === 'warning') return 'primary'
  return 'primary'
})

/**
 * 处理取消
 */
const handleCancel = (): void => {
  emit('cancel')
  emit('update:visible', false)
}

/**
 * 处理确认
 */
const handleConfirm = (): void => {
  emit('confirm')
}

/**
 * 处理输入
 */
const handleInput = (e: Event): void => {
  const target = e.target as HTMLInputElement
  emit('update:input', target.value)
}
</script>

<template>
  <Modal
    :visible="visible"
    :title="displayTitle"
    :closable="!loading"
    :mask-closable="!loading"
    width="480px"
    @update:visible="$emit('update:visible', $event)"
    @close="handleCancel"
  >
    <div class="confirm-dialog-content">
      <!-- 图标 -->
      <div class="confirm-icon" :class="iconType">
        {{ iconChar }}
      </div>

      <!-- 主消息 -->
      <p class="confirm-message" :class="iconType">{{ message }}</p>

      <!-- 提示信息 -->
      <p v-if="hint" class="confirm-hint">{{ hint }}</p>

      <!-- 输入验证 -->
      <div v-if="requireInput" class="confirm-input-wrapper">
        <label class="confirm-input-label">
          请输入 "{{ expectedInput }}" 确认
        </label>
        <input
          type="text"
          class="confirm-input"
          :placeholder="inputPlaceholder || expectedInput"
          :disabled="loading"
          @input="handleInput"
          @keyup.enter="handleConfirm"
        />
      </div>
    </div>

    <!-- 底部按钮 -->
    <template #footer>
      <Button
        type="secondary"
        :disabled="loading"
        @click="handleCancel"
      >
        {{ cancelText }}
      </Button>
      <Button
        :type="confirmButtonType"
        :loading="loading"
        @click="handleConfirm"
      >
        {{ confirmText }}
      </Button>
    </template>
  </Modal>
</template>

<style scoped>
.confirm-dialog-content {
  text-align: center;
  padding: var(--spacing-md) 0;
}

.confirm-icon {
  font-size: 48px;
  margin-bottom: var(--spacing-md);
}

.confirm-message {
  margin: 0 0 var(--spacing-sm) 0;
  font-size: var(--font-size-base);
  color: var(--text-primary);
  line-height: 1.6;
}

.confirm-message.warning {
  color: var(--warning-color);
}

.confirm-message.danger {
  color: var(--error-color);
  font-weight: 600;
}

.confirm-hint {
  margin: 0;
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  line-height: 1.5;
}

.confirm-input-wrapper {
  margin-top: var(--spacing-lg);
  text-align: left;
}

.confirm-input-label {
  display: block;
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  margin-bottom: var(--spacing-sm);
}

.confirm-input {
  width: 100%;
  padding: var(--spacing-sm) var(--spacing-md);
  font-size: var(--font-size-base);
  color: var(--text-primary);
  background-color: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius-md);
  transition: border-color var(--transition-fast);
}

.confirm-input:focus {
  outline: none;
  border-color: var(--primary-color);
}

.confirm-input:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
