<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import Modal from '../Modal.vue'
import Button from '../Button.vue'
import { migrateDatabase, type MigrationResult } from '../../services/databaseApi'

/**
 * 迁移进度弹窗组件
 */

interface Props {
  /** 是否显示 */
  visible: boolean
  /** 源数据库类型 */
  sourceType: string
  /** 目标数据库类型 */
  targetType: string
}

interface Emits {
  (e: 'update:visible', value: boolean): void
  (e: 'complete', success: boolean): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

// 图标路径
const migrateIcon = new URL('../../assets/icons/migrate.svg', import.meta.url).href
const checkCircleIcon = new URL('../../assets/icons/check-circle.svg', import.meta.url).href
const errorIcon = new URL('../../assets/icons/error.svg', import.meta.url).href
const databaseIcon = new URL('../../assets/icons/database.svg', import.meta.url).href

// 迁移状态
const isMigrating = ref(false)
const isCompleted = ref(false)
const isSuccess = ref(false)
const error = ref<string | null>(null)

// 进度信息
const currentStep = ref(0)
const progressPercent = ref(0)
const statusMessage = ref('准备迁移...')
const tableProgress = ref<Record<string, { total: number; migrated: number }>>({})

// 总步骤数
const totalSteps = 4

// 步骤列表
const steps = [
  { id: 1, label: '导出数据', description: '从源数据库导出所有数据' },
  { id: 2, label: '创建表结构', description: '在目标数据库创建表结构' },
  { id: 3, label: '导入数据', description: '将数据导入到目标数据库' },
  { id: 4, label: '验证迁移', description: '验证数据完整性' }
]

// 计算属性
const canClose = computed(() => !isMigrating.value)

const sourceLabel = computed(() => {
  const labels: Record<string, string> = {
    sqlite: 'SQLite',
    postgresql: 'PostgreSQL',
    mysql: 'MySQL'
  }
  return labels[props.sourceType] || props.sourceType
})

const targetLabel = computed(() => {
  const labels: Record<string, string> = {
    sqlite: 'SQLite',
    postgresql: 'PostgreSQL',
    mysql: 'MySQL'
  }
  return labels[props.targetType] || props.targetType
})

const totalRecords = computed(() => {
  return Object.values(tableProgress.value).reduce((sum, t) => sum + t.total, 0)
})

const migratedRecords = computed(() => {
  return Object.values(tableProgress.value).reduce((sum, t) => sum + t.migrated, 0)
})

// 模拟进度更新（实际应通过 WebSocket 或轮询获取）
let progressInterval: ReturnType<typeof setInterval> | null = null



/**
 * 开始迁移
 */
const startMigration = async (): Promise<void> => {
  isMigrating.value = true
  isCompleted.value = false
  isSuccess.value = false
  error.value = null
  currentStep.value = 1
  progressPercent.value = 0
  statusMessage.value = '开始导出数据...'
  tableProgress.value = {}

  try {
    // 模拟进度更新
    simulateProgress()

    // 调用迁移 API
    const result: MigrationResult = await migrateDatabase({
      sourceType: props.sourceType,
      targetType: props.targetType
    })

    // 清除进度模拟
    if (progressInterval) {
      clearInterval(progressInterval)
      progressInterval = null
    }

    if (result.success) {
      isSuccess.value = true
      isCompleted.value = true
      currentStep.value = totalSteps
      progressPercent.value = 100
      statusMessage.value = '迁移完成'
      tableProgress.value = result.tables || {}
    } else {
      throw new Error(result.message || '迁移失败')
    }
  } catch (err) {
    // 清除进度模拟
    if (progressInterval) {
      clearInterval(progressInterval)
      progressInterval = null
    }

    isSuccess.value = false
    isCompleted.value = true
    error.value = err instanceof Error ? err.message : '迁移过程中发生错误'
    statusMessage.value = '迁移失败'
  } finally {
    isMigrating.value = false
  }
}

/**
 * 模拟进度（实际项目中应替换为真实的进度获取）
 */
const simulateProgress = (): void => {
  const stepProgress = [
    { step: 1, message: '正在导出数据...', duration: 2000 },
    { step: 2, message: '正在创建表结构...', duration: 1500 },
    { step: 3, message: '正在导入数据...', duration: 3000 },
    { step: 4, message: '正在验证迁移...', duration: 1000 }
  ]

  let currentStepIndex = 0
  let stepStartTime = Date.now()

  progressInterval = setInterval(() => {
    if (currentStepIndex >= stepProgress.length) {
      if (progressInterval) {
        clearInterval(progressInterval)
      }
      return
    }

    const step = stepProgress[currentStepIndex]
    const elapsed = Date.now() - stepStartTime
    const progress = Math.min((elapsed / step.duration) * 100, 100)

    currentStep.value = step.step
    statusMessage.value = step.message
    progressPercent.value = ((step.step - 1) * 25) + (progress * 0.25)

    // 模拟表进度
    if (step.step === 3) {
      tableProgress.value = {
        users: { total: 100, migrated: Math.floor(100 * progress / 100) },
        repositories: { total: 50, migrated: Math.floor(50 * progress / 100) },
        branches: { total: 200, migrated: Math.floor(200 * progress / 100) },
        commits: { total: 1000, migrated: Math.floor(1000 * progress / 100) }
      }
    }

    if (progress >= 100) {
      currentStepIndex++
      stepStartTime = Date.now()
    }
  }, 100)
}

/**
 * 关闭弹窗
 */
const close = (): void => {
  if (!canClose.value) return
  emit('update:visible', false)
  emit('complete', isSuccess.value)
}

/**
 * 处理完成
 */
const handleComplete = (): void => {
  close()
}

/**
 * 重试迁移
 */
const retryMigration = (): void => {
  error.value = null
  isCompleted.value = false
  startMigration()
}

// 组件挂载时开始迁移
onMounted(() => {
  if (props.visible) {
    startMigration()
  }
})

// 组件卸载时清理
onUnmounted(() => {
  if (progressInterval) {
    clearInterval(progressInterval)
  }
})
</script>

<template>
  <Modal
    :visible="visible"
    title="数据库迁移"
    width="600px"
    :closable="canClose"
    :mask-closable="canClose"
    @update:visible="close"
  >
    <div class="migration-progress">
      <!-- 数据库类型展示 -->
      <div class="db-transition">
        <div class="db-box">
          <img :src="databaseIcon" class="db-icon" alt="source" />
          <span class="db-label">{{ sourceLabel }}</span>
        </div>
        <div class="transition-arrow">
          <img :src="migrateIcon" class="arrow-icon" :class="{ spinning: isMigrating }" alt="arrow" />
        </div>
        <div class="db-box">
          <img :src="databaseIcon" class="db-icon" alt="target" />
          <span class="db-label">{{ targetLabel }}</span>
        </div>
      </div>

      <!-- 步骤指示器 -->
      <div class="steps-indicator">
        <div
          v-for="step in steps"
          :key="step.id"
          class="step-item"
          :class="{
            active: step.id === currentStep,
            completed: step.id < currentStep,
            pending: step.id > currentStep
          }"
        >
          <div class="step-number">
            <img v-if="step.id < currentStep" :src="checkCircleIcon" class="step-check" alt="completed" />
            <span v-else>{{ step.id }}</span>
          </div>
          <div class="step-info">
            <span class="step-label">{{ step.label }}</span>
            <span class="step-description">{{ step.description }}</span>
          </div>
        </div>
      </div>

      <!-- 进度条 -->
      <div class="progress-section">
        <div class="progress-header">
          <span class="progress-status">{{ statusMessage }}</span>
          <span class="progress-percent">{{ Math.round(progressPercent) }}%</span>
        </div>
        <div class="progress-bar">
          <div
            class="progress-fill"
            :style="{ width: `${progressPercent}%` }"
            :class="{ error: error, success: isCompleted && isSuccess }"
          />
        </div>
      </div>

      <!-- 表迁移进度 -->
      <div v-if="Object.keys(tableProgress).length > 0" class="tables-progress">
        <h4 class="tables-title">表迁移进度</h4>
        <div class="tables-list">
          <div
            v-for="(progress, tableName) in tableProgress"
            :key="tableName"
            class="table-item"
          >
            <div class="table-header">
              <span class="table-name">{{ tableName }}</span>
              <span class="table-count">
                {{ progress.migrated }} / {{ progress.total }}
              </span>
            </div>
            <div class="table-bar">
              <div
                class="table-fill"
                :style="{ width: `${progress.total > 0 ? (progress.migrated / progress.total) * 100 : 0}%` }"
              />
            </div>
          </div>
        </div>
        <div class="total-records">
          总计: {{ migratedRecords }} / {{ totalRecords }} 条记录
        </div>
      </div>

      <!-- 错误信息 -->
      <div v-if="error" class="error-section">
        <img :src="errorIcon" class="error-icon" alt="error" />
        <p class="error-message">{{ error }}</p>
      </div>

      <!-- 成功信息 -->
      <div v-if="isCompleted && isSuccess" class="success-section">
        <img :src="checkCircleIcon" class="success-icon" alt="success" />
        <p class="success-message">数据库迁移成功完成！</p>
        <p class="success-hint">服务将在重启后使用新的数据库</p>
      </div>
    </div>

    <template #footer>
      <template v-if="isCompleted">
        <Button v-if="error" type="secondary" @click="retryMigration">
          重试
        </Button>
        <Button type="primary" @click="handleComplete">
          {{ error ? '关闭' : '完成' }}
        </Button>
      </template>
      <template v-else>
        <Button type="primary" :loading="true" disabled>
          迁移中...
        </Button>
      </template>
    </template>
  </Modal>
</template>

<style scoped>
.migration-progress {
  padding: var(--spacing-md);
}

/* 数据库类型展示 */
.db-transition {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-lg);
  margin-bottom: var(--spacing-xl);
  padding: var(--spacing-lg);
  background-color: var(--bg-tertiary);
  border-radius: var(--border-radius-md);
}

.db-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-md);
  background-color: var(--bg-secondary);
  border-radius: var(--border-radius-md);
  border: 2px solid var(--border-color);
  min-width: 100px;
}

.db-icon {
  width: 32px;
  height: 32px;
  color: var(--primary-color);
}

.db-label {
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--text-primary);
}

.transition-arrow {
  display: flex;
  align-items: center;
  justify-content: center;
}

.arrow-icon {
  width: 32px;
  height: 32px;
  color: var(--primary-color);
}

.arrow-icon.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

/* 步骤指示器 */
.steps-indicator {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-xl);
}

.step-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-md);
  border-radius: var(--border-radius-md);
  transition: all var(--transition-fast);
}

.step-item.active {
  background-color: var(--primary-color-alpha);
}

.step-item.completed {
  opacity: 0.7;
}

.step-item.pending {
  opacity: 0.5;
}

.step-number {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background-color: var(--bg-tertiary);
  border: 2px solid var(--border-color);
  font-weight: 600;
  color: var(--text-secondary);
  flex-shrink: 0;
}

.step-item.active .step-number {
  background-color: var(--primary-color);
  border-color: var(--primary-color);
  color: white;
}

.step-item.completed .step-number {
  background-color: var(--success-color);
  border-color: var(--success-color);
}

.step-check {
  width: 20px;
  height: 20px;
  color: white;
}

.step-info {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.step-label {
  font-weight: 600;
  color: var(--text-primary);
}

.step-description {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}

/* 进度条 */
.progress-section {
  margin-bottom: var(--spacing-lg);
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-sm);
}

.progress-status {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}

.progress-percent {
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--primary-color);
}

.progress-bar {
  height: 8px;
  background-color: var(--bg-tertiary);
  border-radius: var(--border-radius-sm);
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background-color: var(--primary-color);
  border-radius: var(--border-radius-sm);
  transition: width 0.3s ease;
}

.progress-fill.error {
  background-color: var(--error-color);
}

.progress-fill.success {
  background-color: var(--success-color);
}

/* 表迁移进度 */
.tables-progress {
  margin-bottom: var(--spacing-lg);
  padding: var(--spacing-md);
  background-color: var(--bg-tertiary);
  border-radius: var(--border-radius-md);
}

.tables-title {
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 var(--spacing-md);
}

.tables-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-md);
}

.table-item {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.table-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.table-name {
  font-size: var(--font-size-sm);
  color: var(--text-primary);
  text-transform: capitalize;
}

.table-count {
  font-size: var(--font-size-xs);
  color: var(--text-secondary);
}

.table-bar {
  height: 4px;
  background-color: var(--bg-secondary);
  border-radius: var(--border-radius-sm);
  overflow: hidden;
}

.table-fill {
  height: 100%;
  background-color: var(--primary-color);
  border-radius: var(--border-radius-sm);
  transition: width 0.3s ease;
}

.total-records {
  text-align: right;
  font-size: var(--font-size-xs);
  color: var(--text-secondary);
  padding-top: var(--spacing-sm);
  border-top: 1px solid var(--border-color);
}

/* 错误信息 */
.error-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-lg);
  background-color: var(--error-color-alpha);
  border-radius: var(--border-radius-md);
  margin-top: var(--spacing-lg);
}

.error-icon {
  width: 48px;
  height: 48px;
  color: var(--error-color);
}

.error-message {
  color: var(--error-color);
  text-align: center;
  margin: 0;
}

/* 成功信息 */
.success-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-lg);
  background-color: var(--success-color-alpha);
  border-radius: var(--border-radius-md);
  margin-top: var(--spacing-lg);
}

.success-icon {
  width: 48px;
  height: 48px;
  color: var(--success-color);
}

.success-message {
  color: var(--success-color);
  font-weight: 600;
  margin: 0;
}

.success-hint {
  color: var(--text-secondary);
  font-size: var(--font-size-sm);
  margin: 0;
}
</style>
