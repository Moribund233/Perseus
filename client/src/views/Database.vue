<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import Card from '../components/Card.vue'
import Button from '../components/Button.vue'
import Alert from '../components/Alert.vue'
import Modal from '../components/Modal.vue'
import Progress from '../components/Progress.vue'
import { useDatabaseStore, useServiceStore } from '../stores'
import type { DatabaseType, DatabaseConfig } from '../services/databaseApi'
import { switchDatabaseType, getDatabaseType, getDatabaseUrls, getStressTest } from '../services/api'
import { switchDatabase, precheckMigration, type PrecheckResponse, type MigrationResponse } from '../services/migrationApi'
import { useDatabaseConnection } from '../composables/useDatabaseConnection'

/**
 * 数据库配置页面
 * 使用 Pinia Store 管理状态，避免频繁访问配置接口
 * 数据库类型从客户端加密配置中读取
 */

const dbStore = useDatabaseStore()
const serviceStore = useServiceStore()
const { checkConnection, checking } = useDatabaseConnection()

// 压力测试模式状态
const isStressTestMode = ref(false)

// 确认弹窗状态
const showConfirmModal = ref(false)
const pendingDbType = ref<DatabaseType | null>(null)
// 切换成功提示
const showRestartAlert = ref(false)
// URL 未配置提示
const showUrlNotConfiguredAlert = ref(false)
const urlNotConfiguredDbType = ref<DatabaseType | null>(null)
// 切换进度弹窗
const showProgressModal = ref(false)
const progressMessage = ref('')
const progressPercent = ref(0)
const isSwitching = ref(false)
// 切换结果提示
const showResultAlert = ref(false)
const resultType = ref<'success' | 'error'>('success')
const resultMessage = ref('')
// 预检查结果
const precheckResult = ref<PrecheckResponse | null>(null)
// 迁移结果
const migrationResult = ref<MigrationResponse | null>(null)

// 数据库 URL 缓存
const databaseUrls = ref<Record<string, string>>({})

// 从客户端配置读取的数据库类型
const clientDbType = ref<DatabaseType>('sqlite')
// 原始数据库类型（用于回滚）
const originalDbType = ref<DatabaseType>('sqlite')
// 是否正在加载客户端配置
const isLoadingClientConfig = ref(true)

// 图标路径
const icons = {
  database: new URL('../assets/icons/database.svg', import.meta.url).href,
  refresh: new URL('../assets/icons/refresh.svg', import.meta.url).href,
  checkCircle: new URL('../assets/icons/check-circle.svg', import.meta.url).href,
  sqlite: new URL('../assets/icons/sqlite.svg', import.meta.url).href,
  postgresql: new URL('../assets/icons/postgresql.svg', import.meta.url).href,
  mysql: new URL('../assets/icons/mysql.svg', import.meta.url).href
}

// 数据库类型选项（带图标）
const databaseTypes = computed(() =>
  dbStore.dbTypeOptions.map(option => ({
    ...option,
    icon: icons[option.value]
  }))
)

// 默认数据库配置
const defaultConfig: DatabaseConfig = {
  db_type: 'sqlite',
  pool_size: 10,
  max_overflow: 20,
  pool_timeout: 30,
  pool_recycle: 3600,
  echo: false,
  sqlite_timeout: 30,
  sqlite_check_same_thread: false,
  sqlite_isolation_level: null,
  enable_wal: true,
  wal_synchronous: 'NORMAL',
  wal_cache_size: 2000,
  wal_temp_store: 'MEMORY',
  stress_pool_size: 20,
  stress_max_overflow: 40,
  stress_pool_timeout: 60,
  stress_pool_recycle: 1800,
  stress_sqlite_timeout: 60,
  stress_echo: false,
  pg_ssl_mode: 'prefer',
  pg_connect_timeout: 30,
  pg_application_name: 'LanGit',
  mysql_charset: 'utf8mb4',
  mysql_pool_recycle: 3600,
  mysql_connect_timeout: 30,
  mysql_read_timeout: 30,
  mysql_write_timeout: 30
}

// 当前编辑的配置 - 服务未启动时使用默认配置，但使用客户端配置中的 db_type
const config = computed((): DatabaseConfig => {
  if (dbStore.editingConfig) {
    return dbStore.editingConfig
  }
  // 服务未启动时，使用客户端配置中的 db_type
  return { ...defaultConfig, db_type: clientDbType.value }
})

// 当前数据库类型标签
const currentDbTypeLabel = computed(() => {
  const type = databaseTypes.value.find(t => t.value === clientDbType.value)
  return type?.label || clientDbType.value
})

// 待切换的数据库类型标签
const pendingDbTypeLabel = computed(() => {
  if (!pendingDbType.value) return ''
  const type = databaseTypes.value.find(t => t.value === pendingDbType.value)
  return type?.label || pendingDbType.value
})

/**
 * 检查数据库 URL 是否已配置
 */
const isDatabaseUrlConfigured = (dbType: DatabaseType): boolean => {
  const url = databaseUrls.value[dbType]
  return !!url && url.trim().length > 0
}

/**
 * 切换数据库类型
 * 完整的切换流程：预检查 -> 迁移（如需要）-> 更新配置
 */
const handleDbTypeChange = async (newType: DatabaseType): Promise<void> => {
  if (newType === clientDbType.value) return

  // 检查目标数据库类型的 URL 是否已配置
  if (!isDatabaseUrlConfigured(newType)) {
    urlNotConfiguredDbType.value = newType
    showUrlNotConfiguredAlert.value = true
    return
  }

  // 检查服务是否运行
  if (!serviceStore.isRunning) {
    // 服务未运行时，仅更新客户端配置
    pendingDbType.value = newType
    showConfirmModal.value = true
    return
  }

  // 服务运行时，执行完整的切换流程
  pendingDbType.value = newType
  showConfirmModal.value = true
}

/**
 * 关闭 URL 未配置提示
 */
const closeUrlNotConfiguredAlert = (): void => {
  showUrlNotConfiguredAlert.value = false
  urlNotConfiguredDbType.value = null
}

/**
 * 关闭结果提示
 */
const closeResultAlert = (): void => {
  showResultAlert.value = false
}

/**
 * 确认切换数据库类型
 * 完整的切换流程：预检查 -> 迁移（如需要）-> 更新配置
 */
const confirmSwitch = async (): Promise<void> => {
  if (!pendingDbType.value) return

  // 保存原始数据库类型用于回滚
  originalDbType.value = clientDbType.value

  // 服务未运行时，仅更新客户端配置
  if (!serviceStore.isRunning) {
    try {
      await switchDatabaseType(pendingDbType.value)
      clientDbType.value = pendingDbType.value
      showConfirmModal.value = false
      showRestartAlert.value = true
      pendingDbType.value = null
    } catch (err) {
      console.error('切换数据库类型失败:', err)
      resultType.value = 'error'
      resultMessage.value = '切换失败: ' + String(err)
      showResultAlert.value = true
    }
    return
  }

  // 服务运行时，执行完整的切换流程
  showConfirmModal.value = false
  showProgressModal.value = true
  isSwitching.value = true
  progressMessage.value = '正在初始化...'
  progressPercent.value = 10

  try {
    const targetUrl = databaseUrls.value[pendingDbType.value]

    // 步骤1: 执行预检查
    progressMessage.value = '正在执行预检查...'
    progressPercent.value = 20

    const precheck = await precheckMigration(targetUrl)
    precheckResult.value = precheck

    if (!precheck.passed) {
      // 预检查未通过
      const errors = precheck.errors.map(e => e.message).join('; ')
      throw new Error('预检查未通过: ' + errors)
    }

    progressPercent.value = 40

    // 步骤2: 检查是否需要迁移
    if (precheck.is_synced) {
      // 数据库已同步，无需迁移
      progressMessage.value = '数据库已同步，正在更新配置...'
      progressPercent.value = 80

      // 更新客户端配置
      await switchDatabaseType(pendingDbType.value)
      clientDbType.value = pendingDbType.value

      progressPercent.value = 100
      progressMessage.value = '切换完成'

      // 显示成功结果
      setTimeout(() => {
        showProgressModal.value = false
        isSwitching.value = false
        resultType.value = 'success'
        resultMessage.value = '数据库已同步，切换成功。请重启服务以应用新的数据库配置。'
        showResultAlert.value = true
        showRestartAlert.value = true
        pendingDbType.value = null
      }, 500)
      return
    }

    // 步骤3: 需要迁移，执行完整切换流程
    progressMessage.value = '需要数据迁移，正在执行...'
    progressPercent.value = 50

    const result = await switchDatabase(pendingDbType.value, targetUrl)

    if (result.success) {
      // 切换成功
      migrationResult.value = result.migration_result || null
      clientDbType.value = pendingDbType.value

      progressPercent.value = 100
      progressMessage.value = '切换完成'

      setTimeout(() => {
        showProgressModal.value = false
        isSwitching.value = false
        resultType.value = 'success'
        if (result.need_migration) {
          const tables = result.migration_result?.tables_migrated || 0
          const rows = result.migration_result?.total_rows_migrated || 0
          resultMessage.value = `切换成功！已迁移 ${tables} 个表，${rows} 行数据。请重启服务以应用新的数据库配置。`
        } else {
          resultMessage.value = '数据库已同步，切换成功。请重启服务以应用新的数据库配置。'
        }
        showResultAlert.value = true
        showRestartAlert.value = true
        pendingDbType.value = null
      }, 500)
    } else {
      // 切换失败，自动回滚
      throw new Error(result.message)
    }
  } catch (err) {
    console.error('数据库切换失败:', err)

    // 关闭进度弹窗
    showProgressModal.value = false
    isSwitching.value = false

    // 显示错误结果
    resultType.value = 'error'
    resultMessage.value = '切换失败: ' + String(err)
    showResultAlert.value = true

    // 清除待处理类型
    pendingDbType.value = null
  }
}

/**
 * 取消切换
 */
const cancelSwitch = (): void => {
  showConfirmModal.value = false
  pendingDbType.value = null
}

// 页面加载
onMounted(async () => {
  // 无论服务是否启动，都先读取客户端配置中的数据库类型和 URL
  try {
    const [dbType, urls, stressTest] = await Promise.all([
      getDatabaseType(),
      getDatabaseUrls(),
      getStressTest()
    ])
    if (dbType && ['sqlite', 'postgresql', 'mysql'].includes(dbType)) {
      clientDbType.value = dbType as DatabaseType
    }
    if (urls) {
      databaseUrls.value = urls
    }
    isStressTestMode.value = stressTest
  } catch (err) {
    console.error('获取客户端配置失败:', err)
  } finally {
    isLoadingClientConfig.value = false
  }

  // 服务启动时才加载服务端配置
  if (serviceStore.isRunning && !dbStore.isConfigLoaded) {
    dbStore.loadConfig()
  }
})
</script>

<template>
  <div class="database-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="header-title">
        <img :src="icons.database" class="header-icon" alt="database" />
        <h1>数据库配置</h1>
      </div>
      <p class="header-description">
        配置数据库连接参数，支持 SQLite、PostgreSQL、MySQL 多种数据库类型
      </p>
    </div>

    <!-- 服务未启动提示 -->
    <Alert v-if="!serviceStore.isRunning" type="info" class="mb-lg">
      服务未启动，请前往控制台启动服务以加载数据库配置
    </Alert>

    <!-- 消息提示 - 服务启动时才显示错误 -->
    <Alert v-if="dbStore.error && serviceStore.isRunning" type="error" closable @close="dbStore.clearMessages()" class="mb-lg">
      {{ dbStore.error }}
    </Alert>
    <Alert v-if="dbStore.successMessage" type="success" closable @close="dbStore.clearMessages()" class="mb-lg">
      {{ dbStore.successMessage }}
    </Alert>
    <!-- 重启提示 - 数据库类型切换成功后显示 -->
    <Alert v-if="showRestartAlert" type="warning" closable @close="showRestartAlert = false" class="mb-lg">
      数据库类型已切换，请前往控制台重启应用以应用新的数据库配置
    </Alert>

    <!-- 切换结果提示 -->
    <Alert v-if="showResultAlert" :type="resultType" closable @close="closeResultAlert" class="mb-lg">
      {{ resultMessage }}
    </Alert>

    <!-- URL 未配置提示 -->
    <Alert v-if="showUrlNotConfiguredAlert" type="error" closable @close="closeUrlNotConfiguredAlert" class="mb-lg">
      <div>
        <p>无法切换到 {{ urlNotConfiguredDbType?.toUpperCase() }}：数据库连接 URL 未配置</p>
        <p style="margin-top: var(--spacing-xs); font-size: var(--font-size-sm);">
          请前往「设置 → 开发者选项」中配置 {{ urlNotConfiguredDbType?.toUpperCase() }} 的数据库连接 URL
        </p>
      </div>
    </Alert>

    <!-- 加载中 -->
    <div v-if="isLoadingClientConfig || (dbStore.isLoading && !dbStore.isConfigLoaded)" class="loading-state">
      <img :src="icons.refresh" class="spinner-icon" alt="loading" />
      <span>加载配置中...</span>
    </div>

    <template v-if="!isLoadingClientConfig && (dbStore.isConfigLoaded || !serviceStore.isRunning)">
      <!-- 数据库类型选择 -->
      <Card title="数据库类型" class="mb-lg">
        <div class="db-type-grid">
          <div
            v-for="type in databaseTypes"
            :key="type.value"
            class="db-type-card"
            :class="{ active: clientDbType === type.value }"
            @click="handleDbTypeChange(type.value)"
          >
            <img :src="type.icon" class="db-type-icon" :alt="type.label" />
            <div class="db-type-info">
              <h3 class="db-type-label">{{ type.label }}</h3>
              <p class="db-type-description">{{ type.description }}</p>
            </div>
            <img v-if="clientDbType === type.value" :src="icons.checkCircle" class="db-type-check" alt="selected" />
          </div>
        </div>
      </Card>

      <!-- 连接池配置 -->
      <Card title="连接池配置" class="mb-lg" :class="{ 'card-disabled': !serviceStore.isRunning }">
        <div class="form-grid">
          <div class="form-group">
            <label class="form-label">连接池大小</label>
            <input v-model.number="config.pool_size" type="number" class="form-input" min="1" :disabled="!serviceStore.isRunning" />
            <span class="form-hint">默认连接池中的连接数</span>
          </div>
          <div class="form-group">
            <label class="form-label">最大溢出连接数</label>
            <input v-model.number="config.max_overflow" type="number" class="form-input" min="0" :disabled="!serviceStore.isRunning" />
            <span class="form-hint">超过连接池大小时允许创建的额外连接</span>
          </div>
          <div class="form-group">
            <label class="form-label">连接超时时间（秒）</label>
            <input v-model.number="config.pool_timeout" type="number" class="form-input" min="1" :disabled="!serviceStore.isRunning" />
            <span class="form-hint">获取连接的最大等待时间</span>
          </div>
          <div class="form-group">
            <label class="form-label">连接回收时间（秒）</label>
            <input v-model.number="config.pool_recycle" type="number" class="form-input" min="0" :disabled="!serviceStore.isRunning" />
            <span class="form-hint">连接自动回收的时间，0表示不回收</span>
          </div>
        </div>
        <div class="form-group mt-md">
          <label class="form-checkbox">
            <input v-model="config.echo" type="checkbox" :disabled="!serviceStore.isRunning" />
            <span>打印 SQL 语句（调试用）</span>
          </label>
        </div>
      </Card>

      <!-- 压力测试配置 - 仅在压力测试模式开启时显示 -->
      <Card v-if="isStressTestMode" title="压力测试模式配置" class="mb-lg stress-test-card" :class="{ 'card-disabled': !serviceStore.isRunning }">
        <template #header-extra>
          <span class="stress-test-badge">压力测试模式已启用</span>
        </template>
        <div class="form-grid">
          <div class="form-group">
            <label class="form-label">压力测试连接池大小</label>
            <input v-model.number="config.stress_pool_size" type="number" class="form-input" min="1" :disabled="!serviceStore.isRunning" />
            <span class="form-hint">压力测试模式下连接池中的连接数</span>
          </div>
          <div class="form-group">
            <label class="form-label">压力测试最大溢出连接数</label>
            <input v-model.number="config.stress_max_overflow" type="number" class="form-input" min="0" :disabled="!serviceStore.isRunning" />
            <span class="form-hint">压力测试模式下允许创建的额外连接</span>
          </div>
          <div class="form-group">
            <label class="form-label">压力测试连接超时时间（秒）</label>
            <input v-model.number="config.stress_pool_timeout" type="number" class="form-input" min="1" :disabled="!serviceStore.isRunning" />
            <span class="form-hint">压力测试模式下获取连接的最大等待时间</span>
          </div>
          <div class="form-group">
            <label class="form-label">压力测试连接回收时间（秒）</label>
            <input v-model.number="config.stress_pool_recycle" type="number" class="form-input" min="0" :disabled="!serviceStore.isRunning" />
            <span class="form-hint">压力测试模式下连接自动回收的时间</span>
          </div>
        </div>
        <div v-if="clientDbType === 'sqlite'" class="form-grid mt-md">
          <div class="form-group">
            <label class="form-label">压力测试 SQLite 超时时间（秒）</label>
            <input v-model.number="config.stress_sqlite_timeout" type="number" class="form-input" min="1" :disabled="!serviceStore.isRunning" />
            <span class="form-hint">压力测试模式下 SQLite 内部超时时间</span>
          </div>
        </div>
        <div class="form-group mt-md">
          <label class="form-checkbox">
            <input v-model="config.stress_echo" type="checkbox" :disabled="!serviceStore.isRunning" />
            <span>压力测试模式打印 SQL 语句（调试用）</span>
          </label>
        </div>
        <div class="stress-test-hint mt-md">
          <Alert type="info">
          重启服务后自动应用压力测试参数。
          </Alert>
        </div>
      </Card>

      <!-- SQLite 配置 -->
      <Card v-if="clientDbType === 'sqlite'" title="SQLite 配置" class="mb-lg" :class="{ 'card-disabled': !serviceStore.isRunning }">
        <div class="form-grid">
          <div class="form-group">
            <label class="form-label">内部超时时间（秒）</label>
            <input v-model.number="config.sqlite_timeout" type="number" class="form-input" min="1" :disabled="!serviceStore.isRunning" />
          </div>
          <div class="form-group">
            <label class="form-label">WAL 同步模式</label>
            <select v-model="config.wal_synchronous" class="form-select" :disabled="!serviceStore.isRunning">
              <option value="OFF">OFF</option>
              <option value="NORMAL">NORMAL</option>
              <option value="FULL">FULL</option>
              <option value="EXTRA">EXTRA</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">WAL 缓存大小</label>
            <input v-model.number="config.wal_cache_size" type="number" class="form-input" min="0" :disabled="!serviceStore.isRunning" />
          </div>
          <div class="form-group">
            <label class="form-label">临时表存储</label>
            <select v-model="config.wal_temp_store" class="form-select" :disabled="!serviceStore.isRunning">
              <option value="DEFAULT">DEFAULT</option>
              <option value="FILE">FILE</option>
              <option value="MEMORY">MEMORY</option>
            </select>
          </div>
        </div>
        <div class="form-group mt-md">
          <label class="form-checkbox">
            <input v-model="config.enable_wal" type="checkbox" :disabled="!serviceStore.isRunning" />
            <span>启用 WAL 模式（提高并发性能）</span>
          </label>
        </div>
        <div class="form-group mt-sm">
          <label class="form-checkbox">
            <input v-model="config.sqlite_check_same_thread" type="checkbox" :disabled="!serviceStore.isRunning" />
            <span>检查同线程（仅调试使用）</span>
          </label>
        </div>
        <div class="form-group mt-sm">
          <label class="form-label">隔离级别</label>
          <select v-model="config.sqlite_isolation_level" class="form-select" :disabled="!serviceStore.isRunning">
            <option :value="null">自动提交模式</option>
            <option value="READ UNCOMMITTED">READ UNCOMMITTED</option>
            <option value="READ COMMITTED">READ COMMITTED</option>
            <option value="SERIALIZABLE">SERIALIZABLE</option>
          </select>
          <span class="form-hint">SQLite 事务隔离级别，null 表示自动提交模式</span>
        </div>
      </Card>

      <!-- PostgreSQL 配置 -->
      <Card v-if="clientDbType === 'postgresql'" title="PostgreSQL 配置" class="mb-lg" :class="{ 'card-disabled': !serviceStore.isRunning }">
        <div class="form-grid">
          <div class="form-group">
            <label class="form-label">SSL 模式</label>
            <select v-model="config.pg_ssl_mode" class="form-select" :disabled="!serviceStore.isRunning">
              <option value="disable">disable</option>
              <option value="allow">allow</option>
              <option value="prefer">prefer</option>
              <option value="require">require</option>
              <option value="verify-ca">verify-ca</option>
              <option value="verify-full">verify-full</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">连接超时时间（秒）</label>
            <input v-model.number="config.pg_connect_timeout" type="number" class="form-input" min="1" :disabled="!serviceStore.isRunning" />
          </div>
          <div class="form-group">
            <label class="form-label">应用名称</label>
            <input v-model="config.pg_application_name" type="text" class="form-input" :disabled="!serviceStore.isRunning" />
          </div>
        </div>
      </Card>

      <!-- MySQL 配置 -->
      <Card v-if="clientDbType === 'mysql'" title="MySQL 配置" class="mb-lg" :class="{ 'card-disabled': !serviceStore.isRunning }">
        <div class="form-grid">
          <div class="form-group">
            <label class="form-label">字符集</label>
            <input v-model="config.mysql_charset" type="text" class="form-input" :disabled="!serviceStore.isRunning" />
          </div>
          <div class="form-group">
            <label class="form-label">连接超时时间（秒）</label>
            <input v-model.number="config.mysql_connect_timeout" type="number" class="form-input" min="1" :disabled="!serviceStore.isRunning" />
          </div>
          <div class="form-group">
            <label class="form-label">读取超时时间（秒）</label>
            <input v-model.number="config.mysql_read_timeout" type="number" class="form-input" min="1" :disabled="!serviceStore.isRunning" />
          </div>
          <div class="form-group">
            <label class="form-label">写入超时时间（秒）</label>
            <input v-model.number="config.mysql_write_timeout" type="number" class="form-input" min="1" :disabled="!serviceStore.isRunning" />
          </div>
        </div>
      </Card>

      <!-- 操作按钮 -->
      <div class="action-bar">
        <div class="action-left">
          <Button type="secondary" :icon="icons.refresh" @click="dbStore.loadConfig(true)" :disabled="!serviceStore.isRunning || dbStore.isLoading">
            刷新
          </Button>
          <Button type="info" :loading="checking" @click="checkConnection()" :disabled="!serviceStore.isRunning">
            测试连接
          </Button>
        </div>
        <div class="action-right">
          <Button type="secondary" @click="dbStore.resetConfig()" :disabled="!serviceStore.isRunning || !dbStore.hasChanges || dbStore.isSaving">
            重置
          </Button>
          <Button type="primary" :loading="dbStore.isSaving" :disabled="!serviceStore.isRunning || !dbStore.hasChanges" @click="dbStore.saveConfig()">
            保存配置
          </Button>
        </div>
      </div>
    </template>

    <!-- 切换确认弹窗 - 使用基础 Modal 组件 -->
    <Modal v-model:visible="showConfirmModal" title="切换数据库类型" width="400px">
      <p style="margin: 0; color: var(--text-primary);">
        您正在从 <strong>{{ currentDbTypeLabel }}</strong> 切换到 <strong>{{ pendingDbTypeLabel }}</strong>
      </p>
      <p v-if="serviceStore.isRunning" style="margin: var(--spacing-sm) 0 0; font-size: var(--font-size-sm); color: var(--text-secondary);">
        系统将自动执行预检查和数据迁移（如需要）。切换后需要重启应用才能生效。
      </p>
      <p v-else style="margin: var(--spacing-sm) 0 0; font-size: var(--font-size-sm); color: var(--text-secondary);">
        服务未运行，将仅更新客户端配置。切换后需要重启应用才能生效。
      </p>
      <template #footer>
        <Button type="secondary" @click="cancelSwitch">取消</Button>
        <Button type="primary" @click="confirmSwitch">确认切换</Button>
      </template>
    </Modal>

    <!-- 切换进度弹窗 -->
    <Modal v-model:visible="showProgressModal" title="正在切换数据库" :closable="false" width="400px">
      <div class="progress-content">
        <p class="progress-message">{{ progressMessage }}</p>
        <Progress :percent="progressPercent" :show-text="true" />
      </div>
    </Modal>
  </div>
</template>

<style scoped>
/* 仅保留 Database.vue 特有的样式 */

/* 禁用状态样式 */
.card-disabled :deep(.card-body) {
  opacity: 0.7;
}

.card-disabled .form-input,
.card-disabled .form-select,
.card-disabled .form-checkbox input[type="checkbox"] {
  cursor: not-allowed;
}

/* 进度弹窗样式 */
.progress-content {
  padding: var(--spacing-md) 0;
}

.progress-message {
  margin: 0 0 var(--spacing-md);
  color: var(--text-primary);
  font-size: var(--font-size-md);
  text-align: center;
}

/* 压力测试模式卡片样式 */
.stress-test-card :deep(.card-header) {
  background: linear-gradient(135deg, var(--warning-color) 0%, var(--warning-dark) 100%);
  color: white;
}

.stress-test-badge {
  display: inline-block;
  padding: 2px 8px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: var(--border-radius-sm);
  font-size: var(--font-size-xs);
  font-weight: 500;
}

.stress-test-hint {
  border-top: 1px dashed var(--border-color);
  padding-top: var(--spacing-md);
  margin-top: var(--spacing-md);
}

@media (max-width: 768px) {
  .action-bar {
    flex-direction: column;
    gap: var(--spacing-md);
  }

  .action-left,
  .action-right {
    width: 100%;
    justify-content: stretch;
  }
}
</style>
