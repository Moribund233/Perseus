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
