<script setup lang="ts">
import Button from '../Button.vue'
import { useThemeStore, presetColorThemes, layoutDensityPresets } from '../../stores'
import {
  getClientConfig,
  saveClientConfig,
  markGuideCompleted
} from '../../services/api'
import { useGuideEventBus, type DatabaseType } from '../../composables/useGuideEvents'
import { useRouter } from 'vue-router'

/**
 * 用户偏好设置步骤组件
 *
 * 功能：提供主题选择、布局密度设置和数据库类型选择
 * 状态管理：通过事件总线与Guide主组件通信
 * 保存逻辑：组件内部完成所有配置的保存
 */

const router = useRouter()
const eventBus = useGuideEventBus()
const themeStore = useThemeStore()

// 从事件总线获取状态
const state = eventBus.state.value.userPreference
const guideState = eventBus.state.value.guide
const serverState = eventBus.state.value.serverCheck

/**
 * 数据库类型选项
 */
const dbTypeOptions = [
  {
    value: 'sqlite' as DatabaseType,
    label: 'SQLite',
    description: '轻量级本地数据库，适合开发和测试'
  },
  {
    value: 'postgresql' as DatabaseType,
    label: 'PostgreSQL',
    description: '强大的开源关系型数据库，适合生产环境'
  },
  {
    value: 'mysql' as DatabaseType,
    label: 'MySQL',
    description: '流行的开源数据库，广泛使用于Web应用'
  }
]

/**
 * 选择主题并实时预览
 * @param themeId - 主题ID
 */
function selectTheme(themeId: string): void {
  eventBus.updateUserPreference({ selectedTheme: themeId })
  themeStore.switchColorTheme(themeId)
}

/**
 * 选择布局密度并实时预览
 * @param layoutId - 布局密度ID
 */
function selectLayout(layoutId: string): void {
  eventBus.updateUserPreference({ selectedLayout: layoutId })
  themeStore.switchLayoutDensity(layoutId)
}

/**
 * 选择数据库类型
 * @param dbType - 数据库类型
 */
function selectDbType(dbType: DatabaseType): void {
  eventBus.updateUserPreference({ dbType })
}

/**
 * 保存用户偏好设置
 * 组件内部完成所有配置的保存和跳转
 */
async function savePreferences(): Promise<void> {
  eventBus.setSaving(true)
  eventBus.clearError()

  try {
    // 获取当前客户端配置
    const clientConfig = guideState.clientConfig || await getClientConfig()

    // 构建最终配置对象
    const finalConfig = {
      server: {
        url: clientConfig?.server?.url || 'http://127.0.0.1:8000',
        auto_connect: clientConfig?.server?.auto_connect ?? true,
        auto_start: clientConfig?.server?.auto_start ?? false,
        path: {
          exe_name: clientConfig?.server?.path?.exe_name || 'langit-server.exe',
          dir_name: clientConfig?.server?.path?.dir_name || 'langit-server',
          custom_path: serverState.path || clientConfig?.server?.path?.custom_path
        }
      },
      appearance: {
        theme: state.selectedTheme,
        language: clientConfig?.appearance?.language || 'zh',
        sidebar_collapsed: clientConfig?.appearance?.sidebar_collapsed ?? false,
        layout_density: state.selectedLayout
      },
      notification: {
        enabled: clientConfig?.notification?.enabled ?? true,
        on_error: clientConfig?.notification?.on_error ?? true,
        on_warning: clientConfig?.notification?.on_warning ?? false,
        on_start_stop: clientConfig?.notification?.on_start_stop ?? true
      },
      log: {
        level: clientConfig?.log?.level || 'info',
        retention_days: clientConfig?.log?.retention_days ?? 7
      },
      advanced: {
        ws_reconnect_interval: clientConfig?.advanced?.ws_reconnect_interval ?? 3000,
        connection_timeout: clientConfig?.advanced?.connection_timeout ?? 30,
        request_timeout: clientConfig?.advanced?.request_timeout ?? 30
      },
      db_type: state.dbType
    }

    // 保存配置
    await saveClientConfig(finalConfig)

    // 标记引导完成
    await markGuideCompleted()

    // 触发引导完成事件
    eventBus.emit('guide:complete', undefined)

    // 跳转到主页
    router.replace('/home')
  } catch (e) {
    eventBus.setError('保存配置失败: ' + String(e))
    console.error('保存配置失败:', e)
  } finally {
    eventBus.setSaving(false)
  }
}
</script>

<template>
  <div class="step-content">
    <h2 class="step-heading">个性化设置</h2>
    <p class="step-text">选择您喜欢的主题、布局样式和数据库类型</p>

    <!-- 颜色主题选择 -->
    <div class="preference-section">
      <h3>颜色主题</h3>
      <div class="theme-grid">
        <div
          v-for="theme in presetColorThemes"
          :key="theme.id"
          class="theme-option"
          :class="{ 'theme-selected': state.selectedTheme === theme.id }"
          @click="selectTheme(theme.id)"
        >
          <div
            class="theme-preview"
            :style="{ backgroundColor: theme.previewColor }"
          />
          <div class="theme-name">{{ theme.name }}</div>
        </div>
      </div>
    </div>

    <!-- 布局密度选择 -->
    <div class="preference-section">
      <h3>布局密度</h3>
      <div class="layout-options">
        <Button
          v-for="layout in layoutDensityPresets"
          :key="layout.id"
          :type="state.selectedLayout === layout.id ? 'primary' : 'secondary'"
          size="sm"
          @click="selectLayout(layout.id)"
        >
          {{ layout.name }}
        </Button>
      </div>
    </div>

    <!-- 数据库类型选择 -->
    <div class="preference-section">
      <h3>数据库类型</h3>
      <div class="db-type-options">
        <div
          v-for="dbType in dbTypeOptions"
          :key="dbType.value"
          class="db-type-option"
          :class="{ 'db-type-selected': state.dbType === dbType.value }"
          @click="selectDbType(dbType.value)"
        >
          <div class="db-type-header">
            <div class="db-type-radio">
              <div v-if="state.dbType === dbType.value" class="db-type-radio-inner" />
            </div>
            <div class="db-type-label">{{ dbType.label }}</div>
          </div>
          <div class="db-type-description">{{ dbType.description }}</div>
        </div>
      </div>
    </div>

    <!-- 保存按钮 -->
    <div class="action-row">
      <Button
        type="success"
        :loading="guideState.isSaving"
        @click="savePreferences"
      >
        完成设置
      </Button>
    </div>
  </div>
</template>

<style scoped>
@import '../../styles/guide-steps.css';

.preference-section {
  margin-bottom: var(--spacing-xl);
}

.preference-section h3 {
  margin: 0 0 var(--spacing-md) 0;
  font-size: var(--font-size-base);
  font-weight: 500;
  color: var(--text-primary);
}

.theme-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
  gap: var(--spacing-md);
}

.theme-option {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-md);
  border: 2px solid var(--border-color);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: all 0.2s ease;
}

.theme-option:hover {
  border-color: var(--primary-color);
}

.theme-option.theme-selected {
  border-color: var(--primary-color);
  background-color: var(--primary-color-alpha);
}

.theme-preview {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
}

.theme-name {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}

.layout-options {
  display: flex;
  gap: var(--spacing-sm);
  flex-wrap: wrap;
}

/* 数据库类型选择样式 */
.db-type-options {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.db-type-option {
  padding: var(--spacing-md);
  border: 2px solid var(--border-color);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: all 0.2s ease;
}

.db-type-option:hover {
  border-color: var(--primary-color);
  background-color: var(--bg-secondary);
}

.db-type-option.db-type-selected {
  border-color: var(--primary-color);
  background-color: var(--primary-color-alpha);
}

.db-type-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-xs);
}

.db-type-radio {
  width: 18px;
  height: 18px;
  border: 2px solid var(--border-color);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.db-type-selected .db-type-radio {
  border-color: var(--primary-color);
}

.db-type-radio-inner {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background-color: var(--primary-color);
}

.db-type-label {
  font-weight: 500;
  color: var(--text-primary);
}

.db-type-description {
  font-size: var(--font-size-sm);
  color: var(--text-tertiary);
  padding-left: calc(18px + var(--spacing-sm));
}
</style>
