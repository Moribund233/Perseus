<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import Button from '../components/Button.vue'
import Card from '../components/Card.vue'
import Alert from '../components/Alert.vue'
import SecurityPasswordStep from '../components/guide/SecurityPasswordStep.vue'
import ServerCheckStep from '../components/guide/ServerCheckStep.vue'
import NginxConfigStep from '../components/guide/NginxConfigStep.vue'
import GitCheckStep from '../components/guide/GitCheckStep.vue'
import UserPreferenceStep from '../components/guide/UserPreferenceStep.vue'
import {
  getClientConfig,
  type ClientConfig
} from '../services/api'
import { useThemeStore } from '../stores'
import { provideGuideEventBus } from '../composables/useGuideEvents'

/**
 * 首次启动引导页面
 *
 * 功能流程：
 * 1. 安全密码设置 - 设置安全密码并生成加密配置文件
 * 2. 服务端检查 - 检测/指定服务端路径
 * 3. Nginx载入 - 可选的Nginx预配置
 * 4. Git检查 - 验证Git环境
 * 5. 用户偏好 - 主题和布局设置
 *
 * 状态管理：使用provide/inject实现的事件总线
 * 各步骤组件通过事件总线独立管理自己的状态
 */

useThemeStore()

// 客户端配置
const clientConfig = ref<ClientConfig | null>(null)

// 创建并提供事件总线
const eventBus = provideGuideEventBus(clientConfig.value)

// 从事件总线获取状态引用
const stateRef = eventBus.state

// 解包状态以便在模板中使用
const guideState = computed(() => stateRef.value.guide)
const serverCheckState = computed(() => stateRef.value.serverCheck)
const gitCheckState = computed(() => stateRef.value.gitCheck)

// 步骤定义
const steps = [
  { id: 1, title: '安全密码', description: '设置安全密码' },
  { id: 2, title: '服务端检查', description: '配置服务端路径' },
  { id: 3, title: 'Nginx载入', description: '可选的反向代理' },
  { id: 4, title: 'Git检查', description: '验证Git环境' },
  { id: 5, title: '用户偏好', description: '主题和布局设置' }
]

// 计算属性
const isFirstStep = computed(() => guideState.value.currentStep === 1)

const canProceed = computed(() => {
  switch (guideState.value.currentStep) {
    case 1:
      // 安全密码步骤在组件内部处理
      return false
    case 2:
      return serverCheckState.value.status === 'found'
    case 3:
      return true // Nginx可选
    case 4:
      return gitCheckState.value.status === 'installed' || gitCheckState.value.status === 'not_installed'
    case 5:
      // 步骤5的保存按钮在组件内部处理
      return false
    default:
      return false
  }
})

// 初始化
onMounted(async () => {
  try {
    clientConfig.value = await getClientConfig()
    // 更新事件总线中的配置
    stateRef.value.guide.clientConfig = clientConfig.value
    // 初始化主题、布局和数据库类型
    eventBus.updateUserPreference({
      selectedTheme: clientConfig.value?.appearance?.theme || 'dark',
      selectedLayout: clientConfig.value?.appearance?.layout_density || 'default',
      dbType: (clientConfig.value?.db_type as 'sqlite' | 'postgresql' | 'mysql') || 'sqlite'
    })
  } catch (e) {
    console.error('初始化失败:', e)
  }
})

// ==================== 导航控制 ====================

function nextStep() {
  if (guideState.value.currentStep < 5) {
    eventBus.setCurrentStep(guideState.value.currentStep + 1)
    eventBus.clearError()
  }
}

function prevStep() {
  if (guideState.value.currentStep > 1) {
    eventBus.setCurrentStep(guideState.value.currentStep - 1)
    eventBus.clearError()
  }
}

// ==================== 事件监听 ====================

// 监听导航事件
onMounted(() => {
  eventBus.on('nav:next', nextStep)
  eventBus.on('nav:prev', prevStep)
})

// 清理事件监听
onUnmounted(() => {
  eventBus.off('nav:next', nextStep)
  eventBus.off('nav:prev', prevStep)
})
</script>

<template>
  <div class="guide-container">
    <!-- 步骤指示器 -->
    <div class="step-indicator">
      <div
        v-for="(step, index) in steps"
        :key="step.id"
        class="step-item"
        :class="{
          'step-active': guideState.currentStep === step.id,
          'step-completed': guideState.currentStep > step.id
        }"
      >
        <div class="step-number">{{ index + 1 }}</div>
        <div class="step-info">
          <div class="step-title">{{ step.title }}</div>
          <div class="step-desc">{{ step.description }}</div>
        </div>
        <div v-if="index < steps.length - 1" class="step-line" />
      </div>
    </div>

    <!-- 步骤内容 -->
    <Card class="guide-card">
      <!-- 错误提示 -->
      <Alert v-if="guideState.error" type="error" closable @close="eventBus.clearError()">
        {{ guideState.error }}
      </Alert>

      <!-- 步骤1: 安全密码设置 -->
      <SecurityPasswordStep v-if="guideState.currentStep === 1" />

      <!-- 步骤2: 服务端检查 -->
      <ServerCheckStep v-if="guideState.currentStep === 2" />

      <!-- 步骤3: Nginx载入 -->
      <NginxConfigStep v-if="guideState.currentStep === 3" />

      <!-- 步骤4: Git检查 -->
      <GitCheckStep v-if="guideState.currentStep === 4" />

      <!-- 步骤5: 用户偏好 -->
      <UserPreferenceStep v-if="guideState.currentStep === 5" />

      <!-- 底部导航 - 仅在非最后一步且非安全密码步骤显示 -->
      <template #footer>
        <div v-if="guideState.currentStep !== 5 && guideState.currentStep !== 1" class="guide-footer">
          <Button
            v-if="!isFirstStep"
            type="secondary"
            @click="prevStep"
          >
            上一步
          </Button>
          <div class="spacer" />
          <Button
            type="primary"
            :disabled="!canProceed"
            @click="nextStep"
          >
            下一步
          </Button>
        </div>
        <!-- 最后一步的按钮在UserPreferenceStep组件内部处理 -->
        <div v-else-if="guideState.currentStep === 5" class="guide-footer">
          <Button
            type="secondary"
            @click="prevStep"
          >
            上一步
          </Button>
          <div class="spacer" />
        </div>
        <!-- 安全密码步骤的按钮在SecurityPasswordStep组件内部处理 -->
        <div v-else class="guide-footer">
          <div class="spacer" />
        </div>
      </template>
    </Card>
  </div>
</template>

<style scoped>
/* Guide 页面特定样式 - 其他样式来自 page-common.css */

/* 卡片深度选择器样式 */
.guide-card :deep(.card-body) {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
  max-height: calc(100vh - 280px);
}
</style>
