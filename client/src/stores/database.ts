/**
 * 数据库配置管理 Store
 *
 * 使用 Pinia 管理数据库配置状态，避免频繁访问配置接口
 * 提供配置的获取、更新、测试连接等功能
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  getDatabaseConfig,
  updateDatabaseConfig,
  testDatabaseConnection,
  getDatabaseStatus,
  getDatabaseStatusFromApi,
  migrateDatabase,
  type DatabaseConfig,
  type DatabaseType,
  type DatabaseStatus,
  type ConnectionTestResult,
  type DatabaseStatusResponse,
  type MigrationParams
} from '../services/databaseApi'
import { getDatabaseUrl } from '../services/api'

/**
 * 数据库类型选项
 */
export interface DatabaseTypeOption {
  value: DatabaseType
  label: string
  description: string
}

export const useDatabaseStore = defineStore('database', () => {
  // ============ State ============
  /** 服务器原始配置 */
  const serverConfig = ref<DatabaseConfig | null>(null)
  /** 本地编辑中的配置 */
  const editingConfig = ref<DatabaseConfig | null>(null)
  const isLoading = ref(false)
  const isSaving = ref(false)
  const isTesting = ref(false)
  const error = ref<string | null>(null)
  const successMessage = ref<string | null>(null)
  const connectionTested = ref(false)
  const connectionSuccess = ref(false)
  const connectionMessage = ref('')
  const lastLoadTime = ref(0)
  const dbStatus = ref<DatabaseStatus | null>(null)

  // ============ Getters ============

  /**
   * 当前数据库类型
   */
  const currentDbType = computed((): DatabaseType => {
    return editingConfig.value?.db_type || 'sqlite'
  })

  /**
   * 当前数据库类型标签
   */
  const currentDbTypeLabel = computed((): string => {
    const labels: Record<DatabaseType, string> = {
      sqlite: 'SQLite',
      postgresql: 'PostgreSQL',
      mysql: 'MySQL'
    }
    return labels[currentDbType.value] || currentDbType.value
  })

  /**
   * 配置是否已加载
   */
  const isConfigLoaded = computed((): boolean => {
    return serverConfig.value !== null
  })

  /**
   * 是否可以加载（避免过于频繁的加载）
   */
  const canLoad = computed((): boolean => {
    const now = Date.now()
    return !isLoading.value && (now - lastLoadTime.value > 1000)
  })

  /**
   * 配置是否有变更
   */
  const hasChanges = computed((): boolean => {
    if (!serverConfig.value || !editingConfig.value) return false
    return JSON.stringify(editingConfig.value) !== JSON.stringify(serverConfig.value)
  })

  /**
   * 数据库类型选项列表
   */
  const dbTypeOptions = computed((): DatabaseTypeOption[] => [
    {
      value: 'sqlite',
      label: 'SQLite',
      description: '轻量级本地数据库，适合开发和测试'
    },
    {
      value: 'postgresql',
      label: 'PostgreSQL',
      description: '强大的开源关系型数据库，适合生产环境'
    },
    {
      value: 'mysql',
      label: 'MySQL',
      description: '流行的开源数据库，广泛使用于Web应用'
    }
  ])

  // ============ Actions ============

  /**
   * 加载数据库配置
   * @param force 是否强制刷新，忽略缓存
   */
  async function loadConfig(force: boolean = false): Promise<boolean> {
    if (!force && !canLoad.value) {
      return true
    }

    isLoading.value = true
    error.value = null
    successMessage.value = null

    try {
      const data = await getDatabaseConfig()
      serverConfig.value = JSON.parse(JSON.stringify(data))
      editingConfig.value = JSON.parse(JSON.stringify(data))
      lastLoadTime.value = Date.now()
      connectionTested.value = false
      return true
    } catch (err: any) {
      // 检查是否是连接错误（服务端未启动）
      const errorMsg = err?.message || String(err)
      if (errorMsg.includes('Connection refused') ||
          errorMsg.includes('无法连接') ||
          errorMsg.includes('Failed to fetch') ||
          errorMsg.includes('NetworkError')) {
        error.value = '服务端未启动，请先启动服务端以加载数据库配置'
      } else {
        error.value = '加载数据库配置失败'
      }
      console.error('加载数据库配置失败:', err)
      return false
    } finally {
      isLoading.value = false
    }
  }

  /**
   * 更新数据库配置
   */
  async function saveConfig(): Promise<boolean> {
    if (!editingConfig.value) return false

    isSaving.value = true
    error.value = null
    successMessage.value = null

    try {
      await updateDatabaseConfig(editingConfig.value)
      serverConfig.value = JSON.parse(JSON.stringify(editingConfig.value))
      successMessage.value = '配置保存成功，重启服务后生效'
      connectionTested.value = false
      return true
    } catch (err) {
      error.value = '保存配置失败'
      console.error('保存配置失败:', err)
      return false
    } finally {
      isSaving.value = false
    }
  }

  /**
   * 测试数据库连接
   */
  async function testConnection(): Promise<ConnectionTestResult> {
    if (!editingConfig.value) {
      return { success: false, message: '配置未加载' }
    }

    isTesting.value = true
    connectionTested.value = false
    error.value = null
    successMessage.value = null

    try {
      const result = await testDatabaseConnection(editingConfig.value)
      connectionTested.value = true
      connectionSuccess.value = result.success
      connectionMessage.value = result.message

      if (result.success) {
        successMessage.value = '连接测试成功'
      } else {
        error.value = result.message
      }

      return result
    } catch (err) {
      connectionTested.value = true
      connectionSuccess.value = false
      connectionMessage.value = '连接测试失败'
      error.value = '连接测试失败'
      console.error('连接测试失败:', err)
      return { success: false, message: '连接测试失败' }
    } finally {
      isTesting.value = false
    }
  }

  /**
   * 切换数据库类型
   * @param newType 新的数据库类型
   * @returns 是否发生了类型变更
   */
  function switchDbType(newType: DatabaseType): boolean {
    if (!editingConfig.value) return false

    const oldType = editingConfig.value.db_type || 'sqlite'
    if (oldType === newType) return false

    editingConfig.value.db_type = newType
    return true
  }

  /**
   * 重置配置到服务器版本
   */
  function resetConfig(): void {
    if (serverConfig.value) {
      editingConfig.value = JSON.parse(JSON.stringify(serverConfig.value))
      successMessage.value = '配置已重置'
      connectionTested.value = false
    }
  }

  /**
   * 清除消息
   */
  function clearMessages(): void {
    error.value = null
    successMessage.value = null
  }

  /**
   * 获取数据库状态
   */
  async function refreshStatus(): Promise<DatabaseStatus | null> {
    try {
      const status = await getDatabaseStatus()
      dbStatus.value = status
      return status
    } catch (err) {
      console.error('获取数据库状态失败:', err)
      return null
    }
  }

  /**
   * 从服务端 API 获取数据库状态（用于迁移检测）
   */
  async function checkMigrationStatus(): Promise<DatabaseStatusResponse | null> {
    try {
      const status = await getDatabaseStatusFromApi()
      return status
    } catch (err) {
      console.error('获取迁移状态失败:', err)
      return null
    }
  }

  /**
   * 执行数据库迁移
   * @param sourceType 源数据库类型
   * @param targetType 目标数据库类型
   */
  async function executeMigration(sourceType: DatabaseType, targetType: DatabaseType): Promise<{ success: boolean; message: string }> {
    try {
      // 从加密配置获取源和目标数据库 URL
      const [sourceUrl, targetUrl] = await Promise.all([
        getDatabaseUrl(sourceType),
        getDatabaseUrl(targetType)
      ])

      const params: MigrationParams = {
        source_type: sourceType,
        target_type: targetType,
        source_url: sourceUrl,
        target_url: targetUrl
      }

      const result = await migrateDatabase(params)
      
      if (result.success) {
        // 迁移成功，更新本地配置
        if (editingConfig.value) {
          editingConfig.value.db_type = targetType
        }
        successMessage.value = '数据库迁移成功'
      } else {
        error.value = result.message || '迁移失败'
      }

      return {
        success: result.success,
        message: result.message
      }
    } catch (err: any) {
      const message = err?.message || '迁移过程中发生错误'
      error.value = message
      console.error('执行迁移失败:', err)
      return { success: false, message }
    }
  }

  /**
   * 重置状态
   */
  function reset(): void {
    serverConfig.value = null
    editingConfig.value = null
    isLoading.value = false
    isSaving.value = false
    isTesting.value = false
    error.value = null
    successMessage.value = null
    connectionTested.value = false
    connectionSuccess.value = false
    connectionMessage.value = ''
    lastLoadTime.value = 0
    dbStatus.value = null
  }

  return {
    // State
    serverConfig,
    editingConfig,
    isLoading,
    isSaving,
    isTesting,
    error,
    successMessage,
    connectionTested,
    connectionSuccess,
    connectionMessage,
    lastLoadTime,
    dbStatus,
    // Getters
    currentDbType,
    currentDbTypeLabel,
    isConfigLoaded,
    canLoad,
    hasChanges,
    dbTypeOptions,
    // Actions
    loadConfig,
    saveConfig,
    testConnection,
    switchDbType,
    resetConfig,
    clearMessages,
    refreshStatus,
    checkMigrationStatus,
    executeMigration,
    reset
  }
})
