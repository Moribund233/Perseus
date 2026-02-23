/**
 * 数据库迁移 API 服务
 * 
 * 提供数据库迁移相关的 API 调用
 */

import { invoke } from '@tauri-apps/api/core'

// ==================== 类型定义 ====================

/**
 * 预检查请求
 */
export interface PrecheckRequest {
  target_url: string
}

/**
 * 预检查响应
 */
export interface PrecheckResponse {
  source_db_type: string
  target_db_type: string
  passed: boolean
  is_synced: boolean
  sync_details?: {
    tables_checked: number
    tables_synced: number
    table_details?: Record<string, {
      synced: boolean
      reason?: string
      rows?: number
    }>
  }
  summary: {
    total: number
    errors: number
    warnings: number
    infos: number
  }
  errors: CheckResult[]
  warnings: CheckResult[]
  infos: CheckResult[]
}

/**
 * 检查结果项
 */
export interface CheckResult {
  passed: boolean
  severity: 'error' | 'warning' | 'info'
  category: string
  message: string
  details?: Record<string, any>
}

/**
 * 迁移请求
 */
export interface MigrationRequest {
  target_url: string
  batch_size?: number
  tables?: string[]
}

/**
 * 迁移响应
 */
export interface MigrationResponse {
  success: boolean
  tables_migrated: number
  tables_failed: number
  total_rows_migrated: number
  total_rows_failed: number
  duration_seconds: number
  table_progress: TableProgress[]
  errors: MigrationError[]
  skipped?: boolean
  skip_reason?: string
}

/**
 * 表迁移进度
 */
export interface TableProgress {
  table_name: string
  total_rows: number
  migrated_rows: number
  status: 'pending' | 'in_progress' | 'completed' | 'failed'
  started_at?: string
  completed_at?: string
  error_message?: string
}

/**
 * 迁移错误
 */
export interface MigrationError {
  table: string
  error: string
}

/**
 * 数据库切换请求
 */
export interface DatabaseSwitchRequest {
  db_type: string
  target_url: string
}

/**
 * 数据库切换响应
 */
export interface DatabaseSwitchResponse {
  success: boolean
  message: string
  need_migration: boolean
  migration_result?: MigrationResponse
  need_restart: boolean
}

// ==================== API 函数 ====================

/**
 * 执行迁移预检查
 * @param targetUrl 目标数据库 URL
 * @returns 预检查结果
 */
export async function precheckMigration(targetUrl: string): Promise<PrecheckResponse> {
  return invoke('precheck_migration', { targetUrl })
}

/**
 * 执行数据库迁移
 * @param request 迁移请求
 * @returns 迁移结果
 */
export async function executeMigration(request: MigrationRequest): Promise<MigrationResponse> {
  return invoke('execute_migration', { request })
}

/**
 * 切换数据库
 * 完整的切换流程：预检查 -> 迁移（如需要）-> 更新配置
 * @param dbType 目标数据库类型
 * @param targetUrl 目标数据库 URL
 * @returns 切换结果
 */
export async function switchDatabase(
  dbType: string,
  targetUrl: string
): Promise<DatabaseSwitchResponse> {
  return invoke('switch_database', { dbType, targetUrl })
}

/**
 * 回滚数据库切换
 * 在迁移失败时恢复原来的数据库类型
 * @param originalDbType 原始数据库类型
 */
export async function rollbackDatabaseSwitch(originalDbType: string): Promise<void> {
  return invoke('rollback_database_switch', { originalDbType })
}

/**
 * 获取当前数据库连接信息
 * @returns 当前数据库类型和 URL
 */
export async function getCurrentDatabaseInfo(): Promise<{
  db_type: string
  url: string
}> {
  return invoke('get_current_database_info')
}

/**
 * 测试数据库连接
 * @param url 数据库连接 URL
 * @returns 连接是否成功
 */
export async function testDatabaseConnection(url: string): Promise<{
  success: boolean
  message: string
}> {
  return invoke('test_database_connection', { url })
}
