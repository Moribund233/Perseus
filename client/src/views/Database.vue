<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import Card from '../components/Card.vue'
import Button from '../components/Button.vue'
import Modal from '../components/Modal.vue'
import Alert from '../components/Alert.vue'
import MigrationProgressModal from '../components/database/MigrationProgressModal.vue'
import { useDatabaseStore } from '../stores'
import type { DatabaseType } from '../services/databaseApi'
import { getDatabaseType, switchDatabaseType } from '../services/api'

/**
 * 数据库配置页面
 * 使用 Pinia Store 管理状态，避免频繁访问配置接口
 * 数据库类型从客户端加密配置中读取
 */

const dbStore = useDatabaseStore()

// 从加密配置读取的数据库类型
const clientDbType = ref<DatabaseType>('sqlite')
const isLoadingClientDbType = ref(false)

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

// 当前编辑的配置
const config = computed(() => dbStore.editingConfig)

/**
 * 切换数据库类型
 * 同时更新 client.toml 中的 db_type
 */
const handleDbTypeChange = async (newType: DatabaseType): Promise<void> => {
  if (!config.value?.db_type || newType === config.value.db_type) return

  // 先更新 client.toml 中的数据库类型
  try {
    await switchDatabaseType(newType)
    clientDbType.value = newType
  } catch (err) {
    console.error('切换数据库类型失败:', err)
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

/**
 * 从客户端加密配置加载数据库类型
 */
const loadClientDbType = async (): Promise<void> => {
  isLoadingClientDbType.value = true
  try {
    const dbType = await getDatabaseType()
    clientDbType.value = dbType as DatabaseType
  } catch (err) {
    console.error('加载客户端数据库类型失败:', err)
    // 保持默认 sqlite
  } finally {
    isLoadingClientDbType.value = false
  }
}

// 页面加载
onMounted(() => {
  if (!dbStore.isConfigLoaded) {
    dbStore.loadConfig()
  }
  // 从加密配置加载数据库类型
  loadClientDbType()
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

    <!-- 消息提示 -->
    <Alert v-if="dbStore.error" type="error" closable @close="dbStore.clearMessages()" class="mb-lg">
      {{ dbStore.error }}
    </Alert>
    <Alert v-if="dbStore.successMessage" type="success" closable @close="dbStore.clearMessages()" class="mb-lg">
      {{ dbStore.successMessage }}
    </Alert>

    <!-- 加载中 -->
    <div v-if="dbStore.isLoading && !config" class="loading-state">
      <img :src="icons.refresh" class="spinner-icon" alt="loading" />
      <span>加载配置中...</span>
    </div>

    <!-- 未加载配置时显示提示 -->
    <div v-else-if="!config" class="empty-state">
      <img :src="icons.database" class="empty-icon" alt="database" />
      <h3>数据库配置未加载</h3>
      <p>请启动服务端以加载数据库配置信息</p>
      <Button type="primary" :icon="icons.refresh" @click="dbStore.loadConfig(true)" :disabled="dbStore.isLoading">
        重新加载
      </Button>
    </div>

    <template v-else>
      <!-- 客户端加密配置中的数据库类型显示 -->
      <Card v-if="!isLoadingClientDbType" title="客户端数据库配置" class="mb-lg client-db-info">
        <div class="client-db-type-display">
          <div class="db-type-badge" :class="clientDbType">
            <img :src="icons[clientDbType]" class="badge-icon" :alt="clientDbType" />
            <span class="badge-text">
              {{ clientDbType === 'sqlite' ? 'SQLite' :
                 clientDbType === 'postgresql' ? 'PostgreSQL' : 'MySQL' }}
            </span>
          </div>
          <div class="client-db-info-text">
            <p>当前客户端配置的数据库类型</p>
            <p class="hint">修改数据库类型请在「高级设置」-「敏感配置」-「数据库配置」中进行</p>
          </div>
        </div>
      </Card>
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
      <Card title="连接池配置" class="mb-lg">
        <div class="form-grid">
          <div class="form-group">
            <label class="form-label">连接池大小</label>
            <input v-model.number="config.pool_size" type="number" class="form-input" min="1" />
            <span class="form-hint">默认连接池中的连接数</span>
          </div>
          <div class="form-group">
            <label class="form-label">最大溢出连接数</label>
            <input v-model.number="config.max_overflow" type="number" class="form-input" min="0" />
            <span class="form-hint">超过连接池大小时允许创建的额外连接</span>
          </div>
          <div class="form-group">
            <label class="form-label">连接超时时间（秒）</label>
            <input v-model.number="config.pool_timeout" type="number" class="form-input" min="1" />
            <span class="form-hint">获取连接的最大等待时间</span>
          </div>
          <div class="form-group">
            <label class="form-label">连接回收时间（秒）</label>
            <input v-model.number="config.pool_recycle" type="number" class="form-input" min="0" />
            <span class="form-hint">连接自动回收的时间，0表示不回收</span>
          </div>
        </div>
        <div class="form-group mt-md">
          <label class="form-checkbox">
            <input v-model="config.echo" type="checkbox" />
            <span>打印 SQL 语句（调试用）</span>
          </label>
        </div>
      </Card>

      <!-- SQLite 配置 -->
      <Card v-if="config.db_type === 'sqlite'" title="SQLite 配置" class="mb-lg">
        <div class="form-grid">
          <div class="form-group">
            <label class="form-label">内部超时时间（秒）</label>
            <input v-model.number="config.sqlite_timeout" type="number" class="form-input" min="1" />
          </div>
          <div class="form-group">
            <label class="form-label">WAL 同步模式</label>
            <select v-model="config.wal_synchronous" class="form-select">
              <option value="OFF">OFF</option>
              <option value="NORMAL">NORMAL</option>
              <option value="FULL">FULL</option>
              <option value="EXTRA">EXTRA</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">WAL 缓存大小</label>
            <input v-model.number="config.wal_cache_size" type="number" class="form-input" min="0" />
          </div>
          <div class="form-group">
            <label class="form-label">临时表存储</label>
            <select v-model="config.wal_temp_store" class="form-select">
              <option value="DEFAULT">DEFAULT</option>
              <option value="FILE">FILE</option>
              <option value="MEMORY">MEMORY</option>
            </select>
          </div>
        </div>
        <div class="form-group mt-md">
          <label class="form-checkbox">
            <input v-model="config.enable_wal" type="checkbox" />
            <span>启用 WAL 模式（提高并发性能）</span>
          </label>
        </div>
        <div class="form-group mt-sm">
          <label class="form-checkbox">
            <input v-model="config.sqlite_check_same_thread" type="checkbox" />
            <span>检查同线程（仅调试使用）</span>
          </label>
        </div>
        <div class="form-group mt-sm">
          <label class="form-label">隔离级别</label>
          <select v-model="config.sqlite_isolation_level" class="form-select">
            <option :value="null">自动提交模式</option>
            <option value="READ UNCOMMITTED">READ UNCOMMITTED</option>
            <option value="READ COMMITTED">READ COMMITTED</option>
            <option value="SERIALIZABLE">SERIALIZABLE</option>
          </select>
          <span class="form-hint">SQLite 事务隔离级别，null 表示自动提交模式</span>
        </div>
      </Card>

      <!-- PostgreSQL 配置 -->
      <Card v-if="config.db_type === 'postgresql'" title="PostgreSQL 配置" class="mb-lg">
        <div class="form-grid">
          <div class="form-group">
            <label class="form-label">SSL 模式</label>
            <select v-model="config.pg_ssl_mode" class="form-select">
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
            <input v-model.number="config.pg_connect_timeout" type="number" class="form-input" min="1" />
          </div>
          <div class="form-group">
            <label class="form-label">应用名称</label>
            <input v-model="config.pg_application_name" type="text" class="form-input" />
          </div>
        </div>
      </Card>

      <!-- MySQL 配置 -->
      <Card v-if="config.db_type === 'mysql'" title="MySQL 配置" class="mb-lg">
        <div class="form-grid">
          <div class="form-group">
            <label class="form-label">字符集</label>
            <input v-model="config.mysql_charset" type="text" class="form-input" />
          </div>
          <div class="form-group">
            <label class="form-label">连接超时时间（秒）</label>
            <input v-model.number="config.mysql_connect_timeout" type="number" class="form-input" min="1" />
          </div>
          <div class="form-group">
            <label class="form-label">读取超时时间（秒）</label>
            <input v-model.number="config.mysql_read_timeout" type="number" class="form-input" min="1" />
          </div>
          <div class="form-group">
            <label class="form-label">写入超时时间（秒）</label>
            <input v-model.number="config.mysql_write_timeout" type="number" class="form-input" min="1" />
          </div>
        </div>
      </Card>

      <!-- 操作按钮 -->
      <div class="action-bar">
        <div class="action-left">
          <Button type="secondary" :icon="icons.refresh" @click="dbStore.loadConfig(true)" :disabled="dbStore.isLoading">
            刷新
          </Button>
          <Button type="info" :loading="dbStore.isTesting" @click="dbStore.testConnection()">
            测试连接
          </Button>
        </div>
        <div class="action-right">
          <Button type="secondary" @click="dbStore.resetConfig()" :disabled="!dbStore.hasChanges || dbStore.isSaving">
            重置
          </Button>
          <Button type="primary" :loading="dbStore.isSaving" :disabled="!dbStore.hasChanges" @click="dbStore.saveConfig()">
            保存配置
          </Button>
        </div>
      </div>
    </template>

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
.database-page {
  padding: var(--spacing-lg);
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: var(--spacing-xl);
}

.header-title {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-sm);
}

.header-icon {
  width: 32px;
  height: 32px;
}

.header-title h1 {
  font-size: var(--font-size-2xl);
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.header-description {
  color: var(--text-secondary);
  font-size: var(--font-size-md);
  margin: 0;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-xl);
  gap: var(--spacing-md);
  color: var(--text-secondary);
}

.spinner-icon {
  width: 32px;
  height: 32px;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.db-type-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: var(--spacing-md);
}

.db-type-card {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-lg);
  border: 2px solid var(--border-color);
  border-radius: var(--border-radius-md);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.db-type-card:hover {
  border-color: var(--primary-color);
  background-color: var(--bg-tertiary);
}

.db-type-card.active {
  border-color: var(--primary-color);
  background-color: var(--primary-color-alpha);
}

.db-type-icon {
  width: 40px;
  height: 40px;
}

.db-type-info {
  flex: 1;
}

.db-type-label {
  font-size: var(--font-size-lg);
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 var(--spacing-xs);
}

.db-type-description {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  margin: 0;
}

.db-type-check {
  width: 24px;
  height: 24px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: var(--spacing-lg);
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.form-label {
  font-size: var(--font-size-sm);
  font-weight: 500;
  color: var(--text-primary);
}

.form-input,
.form-select {
  padding: var(--spacing-sm) var(--spacing-md);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius-md);
  background-color: var(--bg-primary);
  color: var(--text-primary);
  font-size: var(--font-size-md);
}

.form-input:focus,
.form-select:focus {
  outline: none;
  border-color: var(--primary-color);
}

.form-hint {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
}

.form-checkbox {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  cursor: pointer;
  font-size: var(--font-size-sm);
  color: var(--text-primary);
}

.form-checkbox input[type="checkbox"] {
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.action-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-lg);
  background-color: var(--bg-secondary);
  border-radius: var(--border-radius-md);
  border: 1px solid var(--border-color);
}

.action-left,
.action-right {
  display: flex;
  gap: var(--spacing-md);
}

.migration-confirm-content {
  text-align: center;
  padding: var(--spacing-lg);
}

.warning-icon {
  width: 64px;
  height: 64px;
  color: var(--warning-color);
  margin-bottom: var(--spacing-md);
}

.migration-confirm-content h3 {
  font-size: var(--font-size-xl);
  color: var(--text-primary);
  margin: 0 0 var(--spacing-md);
}

.migration-confirm-content p {
  color: var(--text-secondary);
  margin-bottom: var(--spacing-lg);
}

.migration-flow {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-md);
  margin: var(--spacing-lg) 0;
  flex-wrap: wrap;
}

.flow-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-md);
  background-color: var(--bg-tertiary);
  border-radius: var(--border-radius-sm);
}

.flow-step {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  background-color: var(--primary-color);
  color: white;
  border-radius: 50%;
  font-size: var(--font-size-sm);
  font-weight: 600;
}

.flow-arrow {
  width: 20px;
  height: 20px;
  color: var(--text-tertiary);
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-2xl);
  gap: var(--spacing-md);
  text-align: center;
  background-color: var(--bg-secondary);
  border-radius: var(--border-radius-lg);
  border: 1px solid var(--border-color);
}

.empty-icon {
  width: 64px;
  height: 64px;
  opacity: 0.5;
}

.empty-state h3 {
  font-size: var(--font-size-xl);
  color: var(--text-primary);
  margin: 0;
}

.empty-state p {
  color: var(--text-secondary);
  margin: 0 0 var(--spacing-md);
}

/* 客户端数据库配置显示 */
.client-db-info {
  background-color: var(--bg-secondary);
}

.client-db-type-display {
  display: flex;
  align-items: center;
  gap: var(--spacing-lg);
  padding: var(--spacing-md);
}

.db-type-badge {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-md);
  border-radius: var(--border-radius-md);
  font-weight: 600;
  font-size: var(--font-size-lg);
}

.db-type-badge.sqlite {
  background-color: rgba(59, 130, 246, 0.15);
  color: #3b82f6;
  border: 1px solid rgba(59, 130, 246, 0.3);
}

.db-type-badge.postgresql {
  background-color: rgba(59, 130, 246, 0.15);
  color: #3b82f6;
  border: 1px solid rgba(59, 130, 246, 0.3);
}

.db-type-badge.mysql {
  background-color: rgba(234, 179, 8, 0.15);
  color: #eab308;
  border: 1px solid rgba(234, 179, 8, 0.3);
}

.badge-icon {
  width: 24px;
  height: 24px;
}

.client-db-info-text {
  flex: 1;
}

.client-db-info-text p {
  margin: 0;
  color: var(--text-primary);
  font-size: var(--font-size-md);
}

.client-db-info-text .hint {
  color: var(--text-secondary);
  font-size: var(--font-size-sm);
  margin-top: var(--spacing-xs);
}

.mb-lg { margin-bottom: var(--spacing-lg); }
.mt-md { margin-top: var(--spacing-md); }
.mt-sm { margin-top: var(--spacing-sm); }
</style>
