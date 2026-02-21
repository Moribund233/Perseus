/**
 * 数据库管理 API 服务层
 * 
 * 封装与 Tauri 后端的通信
 */

import { invoke } from '@tauri-apps/api/core'

// ==================== 类型定义 ====================

/**
 * 数据库类型
 */
export type DatabaseType = 'sqlite' | 'postgresql' | 'mysql'

/**
 * 数据库配置
 */
export interface DatabaseConfig {
  /** 数据库类型（从环境变量派生，可能不存在于配置文件中） */
  db_type?: DatabaseType
  /** 连接池大小 */
  pool_size: number
  /** 最大溢出连接数 */
  max_overflow: number
  /** 连接超时时间（秒） */
  pool_timeout: number
  /** 连接回收时间（秒） */
  pool_recycle: number
  /** 是否打印 SQL 语句 */
  echo: boolean
  /** SQLite 内部超时时间（秒） */
  sqlite_timeout: number
  /** SQLite 检查同线程 */
  sqlite_check_same_thread: boolean
  /** SQLite 隔离级别 */
  sqlite_isolation_level: string | null
  /** 是否启用 WAL 模式 */
  enable_wal: boolean
  /** WAL 同步模式 */
  wal_synchronous: string
  /** WAL 缓存大小 */
  wal_cache_size: number
  /** WAL 临时表存储 */
  wal_temp_store: string
  /** 压力测试连接池大小 */
  stress_pool_size: number
  /** 压力测试最大溢出连接数 */
  stress_max_overflow: number
  /** 压力测试连接超时时间（秒） */
  stress_pool_timeout: number
  /** 压力测试连接回收时间（秒） */
  stress_pool_recycle: number
  /** 压力测试 SQLite 超时时间（秒） */
  stress_sqlite_timeout: number
  /** 压力测试是否打印 SQL 语句 */
  stress_echo: boolean
  /** PostgreSQL SSL 模式 */
  pg_ssl_mode: string
  /** PostgreSQL 连接超时时间（秒） */
  pg_connect_timeout: number
  /** PostgreSQL 应用名称 */
  pg_application_name: string
  /** MySQL 字符集 */
  mysql_charset: string
  /** MySQL 连接回收时间（秒） */
  mysql_pool_recycle: number
  /** MySQL 连接超时时间（秒） */
  mysql_connect_timeout: number
  /** MySQL 读取超时时间（秒） */
  mysql_read_timeout: number
  /** MySQL 写入超时时间（秒） */
  mysql_write_timeout: number
}

/**
 * 连接测试结果
 */
export interface ConnectionTestResult {
  /** 是否成功 */
  success: boolean
  /** 结果消息 */
  message: string
  /** 延迟（毫秒） */
  latency_ms?: number
}

/**
 * 迁移进度
 */
export interface MigrationProgress {
  /** 当前步骤 */
  step: number
  /** 总步骤数 */
  total_steps: number
  /** 进度百分比 */
  percent: number
  /** 状态消息 */
  message: string
  /** 表迁移进度 */
  tables?: Record<string, { total: number; migrated: number }>
}

/**
 * 迁移结果
 */
export interface MigrationResult {
  /** 是否成功 */
  success: boolean
  /** 结果消息 */
  message: string
  /** 表迁移详情 */
  tables?: Record<string, { total: number; migrated: number }>
  /** 导出文件路径 */
  export_file?: string
}

/**
 * 迁移参数
 */
export interface MigrationParams {
  /** 源数据库类型 */
  source_type: string
  /** 目标数据库类型 */
  target_type: string
  /** 源数据库 URL */
  source_url: string
  /** 目标数据库 URL */
  target_url: string
  [key: string]: unknown
}

/**
 * 数据库状态响应（从服务端 API 获取）
 */
export interface DatabaseStatusResponse {
  /** 服务端记录的上次实际数据库类型 */
  current_db_type: DatabaseType | null
  /** 从环境变量解析的目标数据库类型 */
  target_db_type: DatabaseType
  /** 是否需要数据迁移 */
  migration_required: boolean
  /** 状态信息 */
  message: string
}

/**
 * 数据库状态
 */
export interface DatabaseStatus {
  /** 是否已连接 */
  connected: boolean
  /** 数据库类型 */
  db_type: DatabaseType
  /** 连接池信息 */
  pool_info?: {
    size: number
    checked_in: number
    checked_out: number
    overflow: number
  }
  /** 数据库大小（MB） */
  size_mb?: number
  /** 表数量 */
  table_count?: number
  /** 记录总数 */
  total_records?: number
}

// ==================== API 函数 ====================

/**
 * 获取数据库配置
 * 使用通用的应用配置接口，指定 section 为 database
 */
export async function getDatabaseConfig(): Promise<DatabaseConfig> {
  const response = await invoke<{ success: boolean; data: DatabaseConfig }>('get_app_config', { section: 'database' })
  if (!response.success || !response.data) {
    throw new Error('获取数据库配置失败')
  }
  // 如果后端没有返回 db_type，默认为 sqlite
  if (!response.data.db_type) {
    response.data.db_type = 'sqlite'
  }
  return response.data
}

/**
 * 更新数据库配置
 * 使用通用的应用配置更新接口
 */
export async function updateDatabaseConfig(config: DatabaseConfig): Promise<void> {
  const response = await invoke<{ success: boolean; errors: string[] }>('update_app_config', {
    config: { database: config }
  })
  if (!response.success) {
    throw new Error(response.errors.join('; ') || '更新数据库配置失败')
  }
}

/**
 * 测试数据库连接
 * 使用通用的配置验证接口
 */
export async function testDatabaseConnection(config: DatabaseConfig): Promise<ConnectionTestResult> {
  const response = await invoke<{ success: boolean; errors: string[] }>('validate_app_config', {
    config: { database: config }
  })
  return {
    success: response.success,
    message: response.success ? '连接配置验证通过' : (response.errors.join('; ') || '连接配置验证失败')
  }
}

/**
 * 获取数据库状态（从服务端 API）
 */
export async function getDatabaseStatusFromApi(): Promise<DatabaseStatusResponse> {
  const response = await invoke<DatabaseStatusResponse>('get_database_status_from_api')
  return response
}

/**
 * 执行数据库迁移
 */
export async function migrateDatabase(params: MigrationParams): Promise<MigrationResult> {
  return invoke('migrate_database', params)
}

/**
 * 获取迁移进度
 */
export async function getMigrationProgress(): Promise<MigrationProgress> {
  return invoke('get_migration_progress')
}

/**
 * 获取数据库状态
 */
export async function getDatabaseStatus(): Promise<DatabaseStatus> {
  return invoke('get_database_status')
}

/**
 * 初始化数据库
 */
export async function initializeDatabase(): Promise<{ success: boolean; message: string }> {
  return invoke('initialize_database')
}

/**
 * 导出数据库数据
 */
export async function exportDatabaseData(): Promise<{ success: boolean; file_path: string; record_count: number }> {
  return invoke('export_database_data')
}

/**
 * 导入数据库数据
 */
export async function importDatabaseData(filePath: string): Promise<{ success: boolean; imported_count: number }> {
  return invoke('import_database_data', { filePath })
}
