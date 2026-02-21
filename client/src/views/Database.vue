<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import Card from '../components/Card.vue'
import Button from '../components/Button.vue'
import Modal from '../components/Modal.vue'
import Alert from '../components/Alert.vue'
import MigrationProgressModal from '../components/database/MigrationProgressModal.vue'
import { useDatabaseStore, useServiceStore } from '../stores'
import type { DatabaseType, DatabaseConfig } from '../services/databaseApi'
import { switchDatabaseType } from '../services/api'

/**
 * 数据库配置页面
 * 使用 Pinia Store 管理状态，避免频繁访问配置接口
 * 数据库类型从客户端加密配置中读取
 */

const dbStore = useDatabaseStore()
const serviceStore = useServiceStore()

// 迁移相关状态
const showMigrationConfirm = ref(false)
const showMigrationProgress = ref(false)
const pendingDbType = ref<DatabaseType | null>(null)

// 图标路径
const icons = {
  database: new URL('../assets/icons/database.svg', import.meta.url).href,
  migrate: new URL('../assets/icons/migrate.svg', import.meta.url).href,
  arrowRight: new URL('../assets/icons/arrow-right.svg', import.meta.url).href,
  checkCircle: new URL('../assets/icons/check-circle.svg', import.meta.url).href,
  alertTriangle: new URL('../assets/icons/alert-triangle.svg', import.meta.url).href,
  refresh: new URL('../assets/icons/refresh.svg', import.meta.url).href,
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
  pg_application_name: 'LangGit',
  mysql_charset: 'utf8mb4',
  mysql_pool_recycle: 3600,
  mysql_connect_timeout: 30,
  mysql_read_timeout: 30,
  mysql_write_timeout: 30
}

// 当前编辑的配置 - 服务未启动时使用默认配置
const config = computed((): DatabaseConfig => dbStore.editingConfig || defaultConfig)

/**
 * 切换数据库类型
 * 同时更新 client.toml 中的 db_type
 */
const handleDbTypeChange = async (newType: DatabaseType): Promise<void> => {
  if (!config.value?.db_type || newType === config.value.db_type) return

  // 先更新 client.toml 中的数据库类型
  try {
    await switchDatabaseType(newType)
  } catch (err) {
    console.error('切换数据库类型失败:', err)
    return
  }

  // 服务未启动时，只更新本地配置，不显示迁移确认
  if (!serviceStore.isRunning) {
    dbStore.switchDbType(newType)
    return
  }

  // 如果类型变更，显示迁移确认
  if (dbStore.serverConfig?.db_type && dbStore.serverConfig.db_type !== newType) {
    pendingDbType.value = newType
    showMigrationConfirm.value = true
  } else {
    dbStore.switchDbType(newType)
  }
}

/**
 * 确认迁移
 */
const confirmMigration = (): void => {
  if (pendingDbType.value) {
    dbStore.switchDbType(pendingDbType.value)
    showMigrationConfirm.value = false
    showMigrationProgress.value = true
  }
}

/**
 * 迁移完成回调
 */
const onMigrationComplete = async (success: boolean): Promise<void> => {
  showMigrationProgress.value = false
  if (success) {
    await dbStore.loadConfig(true)
  } else {
    // 恢复原类型
    if (dbStore.serverConfig?.db_type) {
      dbStore.switchDbType(dbStore.serverConfig.db_type)
    }
  }
  pendingDbType.value = null
}

// 页面加载
onMounted(() => {
  // 服务启动时才加载配置
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
        配置数据库连接参数，切换数据库类型时需要迁移数据
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

    <!-- 加载中 -->
    <div v-if="dbStore.isLoading && !dbStore.isConfigLoaded" class="loading-state">
      <img :src="icons.refresh" class="spinner-icon" alt="loading" />
      <span>加载配置中...</span>
    </div>

    <template v-if="dbStore.isConfigLoaded || !serviceStore.isRunning">
      <!-- 数据库类型选择 -->
      <Card title="数据库类型" class="mb-lg">
        <div class="db-type-grid">
          <div
            v-for="type in databaseTypes"
            :key="type.value"
            class="db-type-card"
            :class="{ active: config.db_type === type.value }"
            @click="handleDbTypeChange(type.value)"
          >
            <img :src="type.icon" class="db-type-icon" :alt="type.label" />
            <div class="db-type-info">
              <h3 class="db-type-label">{{ type.label }}</h3>
              <p class="db-type-description">{{ type.description }}</p>
            </div>
            <img v-if="config.db_type === type.value" :src="icons.checkCircle" class="db-type-check" alt="selected" />
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

      <!-- SQLite 配置 -->
      <Card v-if="config.db_type === 'sqlite'" title="SQLite 配置" class="mb-lg" :class="{ 'card-disabled': !serviceStore.isRunning }">
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
      <Card v-if="config.db_type === 'postgresql'" title="PostgreSQL 配置" class="mb-lg" :class="{ 'card-disabled': !serviceStore.isRunning }">
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
      <Card v-if="config.db_type === 'mysql'" title="MySQL 配置" class="mb-lg" :class="{ 'card-disabled': !serviceStore.isRunning }">
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
          <Button type="info" :loading="dbStore.isTesting" @click="dbStore.testConnection()" :disabled="!serviceStore.isRunning">
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

    <!-- 迁移确认弹窗 -->
    <Modal v-model:visible="showMigrationConfirm" title="数据库迁移确认" width="500px" :closable="false" :mask-closable="false">
      <div class="migration-confirm-content">
        <img :src="icons.alertTriangle" class="warning-icon" alt="warning" />
        <h3>切换数据库类型需要迁移数据</h3>
        <p>
          您正在从 <strong>{{ dbStore.currentDbTypeLabel }}</strong> 切换到
          <strong>{{ databaseTypes.find(t => t.value === pendingDbType)?.label }}</strong>
        </p>
        <div class="migration-flow">
          <div class="flow-item"><span class="flow-step">1</span><span>导出当前数据库数据</span></div>
          <img :src="icons.arrowRight" class="flow-arrow" alt="arrow" />
          <div class="flow-item"><span class="flow-step">2</span><span>切换数据库类型</span></div>
          <img :src="icons.arrowRight" class="flow-arrow" alt="arrow" />
          <div class="flow-item"><span class="flow-step">3</span><span>导入数据到新数据库</span></div>
        </div>
        <Alert type="warning" class="mt-md">
          迁移过程中服务将暂时不可用，请确保没有正在进行的操作
        </Alert>
      </div>
      <template #footer>
        <Button type="secondary" @click="showMigrationConfirm = false; pendingDbType = null">取消</Button>
        <Button type="primary" :icon="icons.migrate" @click="confirmMigration">开始迁移</Button>
      </template>
    </Modal>
    </template>

    <!-- 迁移进度弹窗 -->
    <MigrationProgressModal
      v-model:visible="showMigrationProgress"
      :source-type="dbStore.serverConfig?.db_type || 'sqlite'"
      :target-type="pendingDbType || 'sqlite'"
      @complete="onMigrationComplete"
    />
  </div>
</template>

<style scoped>
/* 迁移确认内容标题和段落 - 补充样式 */
.migration-confirm-content h3 {
  font-size: var(--font-size-xl);
  color: var(--text-primary);
  margin: 0 0 var(--spacing-md);
}

.migration-confirm-content p {
  color: var(--text-secondary);
  margin-bottom: var(--spacing-lg);
}

/* 禁用状态样式 */
.card-disabled :deep(.card-body) {
  opacity: 0.7;
}

.card-disabled .form-input,
.card-disabled .form-select,
.card-disabled .form-checkbox input[type="checkbox"] {
  cursor: not-allowed;
}
</style>
