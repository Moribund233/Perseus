/**
 * API 服务层
 * 
 * 封装与 Tauri 后端的通信
 */

import { invoke } from '@tauri-apps/api/core'

// ==================== 类型定义 ====================

/**
 * 服务状态
 */
export interface ServiceStatus {
  status: string
  debug_mode: boolean
  uptime_seconds: number
  uptime_formatted: string
  version: string
  server_time: string
  process: ServerProcessInfo
  requests: RequestStats
  git_operations: GitOperations
}

/**
 * 系统信息
 */
export interface SystemInfo {
  platform: string
  platform_version: string
  architecture: string
  processor: string
  hostname: string
  cpu_count: number
  cpu_freq_mhz: number | null
  cpu_percent: number
  memory_total_gb: number
  memory_used_gb: number
  memory_percent: number
  disk_total_gb: number
  disk_used_gb: number
  disk_percent: number
  network: NetworkInfo
}

/**
 * 网络信息
 */
export interface NetworkInfo {
  bytes_sent: number
  bytes_received: number
  packets_sent: number
  packets_received: number
  errors_in: number
  errors_out: number
}

/**
 * 服务端进程信息
 */
export interface ServerProcessInfo {
  pid: number
  memory_mb: number
  cpu_percent: number
  threads: number
  connections: number
}

/**
 * 请求统计信息
 */
export interface RequestStats {
  total: number
  success: number
  failed: number
  avg_response_time_ms: number
  requests_per_minute: number
}

/**
 * Git操作状态
 */
export interface GitOperations {
  active_clones: number
  active_pushes: number
  queue_size: number
}

/**
 * 性能数据
 */
export interface PerformanceData {
  cpu: number
  memory: number
  uptime: number
  requests: number
}

/**
 * 系统资源
 */
export interface SystemResources {
  cpu_usage: number
  memory_total_mb: number
  memory_used_mb: number
  memory_usage_percent: number
}

/**
 * 进程信息
 */
export interface ProcessInfo {
  pid: number
  name: string
  cpu_usage: number
  memory_mb: number
  status: string
}

/**
 * 操作响应
 */
export interface ActionResponse {
  success: boolean
  message: string
}

/**
 * 配置响应
 */
export interface ConfigResponse {
  success: boolean
  data?: any
  errors: string[]
  hints: string[]
}

/**
 * 服务端代理配置
 */
export interface ServerProxyConfig {
  proxy: boolean
}

/**
 * 服务端服务配置
 */
export interface ServerServiceConfig {
  host: string
  port: number
  workers: number
  log_level: string
}

/**
 * 服务端配置
 */
/**
 * CORS 配置
 */
export interface CORSConfig {
  allow_origins: string[]
  allow_credentials: boolean
  allow_methods: string[]
  allow_headers: string[]
  max_age: number
}

/**
 * 限流配置项
 */
export interface RateLimitItem {
  mode: 'minute' | 'hour'
  value: number
}

/**
 * 限流配置
 */
export interface RateLimitConfig {
  default_limits: RateLimitItem
  strict: RateLimitItem
  standard: RateLimitItem
  generous: RateLimitItem
  git_operations: RateLimitItem
  download: RateLimitItem
}

export interface ServerAppConfig {
  server?: ServerServiceConfig
  proxy: ServerProxyConfig
  cors?: CORSConfig
  rate_limit?: RateLimitConfig
}

/**
 * 日志信息
 */
export interface LogInfoResponse {
  log_dir: string
  today_dir: string
  today_files: LogFileInfo[]
  available_dates: string[]
}

/**
 * 日志文件信息
 */
export interface LogFileInfo {
  name: string
  size: number
  size_formatted: string
  modified: string
}

/**
 * 日志内容响应
 */
export interface LogContentResponse {
  date: string
  log_name: string
  lines: number
  total_lines: number
  content: string
  exists: boolean
}

/**
 * 日志清理响应
 */
export interface LogCleanupResponse {
  success: boolean
  deleted_count: number
  keep_days: number
}

/**
 * 服务端路径配置
 */
export interface ServerPathConfig {
  exe_name: string
  dir_name: string
  custom_path?: string
}

/**
 * 服务器配置
 */
export interface ServerConfig {
  url: string
  auto_connect: boolean
  auto_start: boolean
  path: ServerPathConfig
}

/**
 * 外观配置
 */
export interface AppearanceConfig {
  theme: string
  layout_density?: string
  language: string
  sidebar_collapsed: boolean
}

/**
 * 通知配置
 */
export interface NotificationConfig {
  enabled: boolean
  on_error: boolean
  on_warning: boolean
  on_start_stop: boolean
}

/**
 * 日志配置
 */
export interface LogConfig {
  level: string
  retention_days: number
}

/**
 * 高级配置
 */
export interface AdvancedConfig {
  ws_reconnect_interval: number
  connection_timeout: number
  request_timeout: number
}

/**
 * 客户端配置
 */
export interface ClientConfig {
  server: ServerConfig
  appearance: AppearanceConfig
  notification: NotificationConfig
  log: LogConfig
  advanced: AdvancedConfig
  auth_token?: string
  /** 数据库类型（sqlite/postgresql/mysql） */
  db_type?: string
  /** 已安装的数据库类型列表 */
  installed_databases?: string[]
}

/**
 * 连接状态
 */
export interface ConnectionStatus {
  connected: boolean
  latency_ms: number
  message?: string
}

// ==================== 服务控制 API ====================

/**
 * 获取服务状态
 */
export async function getServiceStatus(): Promise<ServiceStatus> {
  return invoke('get_service_status')
}

/**
 * 启动服务
 */
export async function startService(): Promise<ActionResponse> {
  return invoke('start_service')
}

/**
 * 停止服务
 */
export async function stopService(): Promise<ActionResponse> {
  return invoke('stop_service')
}

/**
 * 重启服务
 */
export async function restartService(): Promise<ActionResponse> {
  return invoke('restart_service')
}

/**
 * 检查服务是否运行
 */
export async function isServiceRunning(): Promise<boolean> {
  return invoke('is_service_running')
}

// ==================== 性能监控 API ====================

/**
 * 获取性能数据
 */
export async function getPerformanceData(): Promise<PerformanceData> {
  return invoke('get_performance_data')
}

/**
 * 获取系统资源
 */
export async function getSystemResources(): Promise<SystemResources> {
  return invoke('get_system_resources')
}

/**
 * 获取服务端进程信息
 */
export async function getServerProcessInfo(): Promise<ProcessInfo | null> {
  return invoke('get_server_process_info')
}

// ==================== 日志管理 API ====================

/**
 * 获取日志信息
 */
export async function getLogInfo(): Promise<LogInfoResponse> {
  return invoke('get_log_info')
}

/**
 * 获取日志内容
 */
export async function getLogContent(
  options: {
    date?: string
    logName?: string
    lines?: number
    level?: string
  } = {}
): Promise<LogContentResponse> {
  return invoke('get_log_content', {
    date: options.date || null,
    logName: options.logName || 'app',
    lines: options.lines || 100,
    level: options.level || null
  })
}

/**
 * 清理日志
 */
export async function cleanupLogs(keepDays: number): Promise<LogCleanupResponse> {
  return invoke('cleanup_logs', { keepDays })
}

// ==================== 配置管理 API ====================

/**
 * 获取应用配置
 */
export async function getAppConfig(section?: string): Promise<ConfigResponse> {
  return invoke('get_app_config', { section: section || null })
}

/**
 * 更新应用配置
 */
export async function updateAppConfig(config: any): Promise<ConfigResponse> {
  return invoke('update_app_config', { config })
}

/**
 * 重置应用配置（服务端配置）
 */
export async function resetAppConfig(): Promise<ConfigResponse> {
  return invoke('reset_app_config')
}

/**
 * 重置客户端配置
 * 删除配置文件和引导标记，使应用重新进入引导流程
 */
export async function resetClientConfig(): Promise<void> {
  return invoke('reset_client_config')
}

/**
 * 验证应用配置
 */
export async function validateAppConfig(config?: any): Promise<ConfigResponse> {
  return invoke('validate_app_config', { config: config || null })
}

// ==================== 客户端配置 API ====================

/**
 * 获取客户端配置
 */
export async function getClientConfig(): Promise<ClientConfig> {
  return invoke('get_client_config')
}

/**
 * 保存客户端配置
 */
export async function saveClientConfig(config: ClientConfig): Promise<void> {
  return invoke('save_client_config', { config })
}

/**
 * 更新服务端地址
 */
export async function updateServerUrl(url: string): Promise<void> {
  return invoke('update_server_url', { url })
}

/**
 * 更新认证令牌
 */
export async function updateAuthToken(token?: string): Promise<void> {
  return invoke('update_auth_token', { token: token || null })
}

/**
 * 获取服务端地址
 */
export async function getServerUrl(): Promise<string> {
  return invoke('get_server_url')
}

// ==================== 安全配置 API ====================

/**
 * 设置客户端安全密码
 */
export async function setSecurityPassword(password: string): Promise<void> {
  return invoke('set_security_password', { password })
}

/**
 * 验证客户端安全密码
 */
export async function verifySecurityPassword(password: string): Promise<boolean> {
  return invoke('verify_security_password', { password })
}

/**
 * 检查是否已设置安全密码
 */
export async function hasSecurityPassword(): Promise<boolean> {
  return invoke('has_security_password')
}

/**
 * 获取调试模式状态
 */
export async function getDebugMode(): Promise<boolean> {
  return invoke('get_debug_mode')
}

/**
 * 更新调试模式
 */
export async function updateDebugMode(debug: boolean): Promise<void> {
  return invoke('update_debug_mode', { debug })
}

/**
 * 重置所有安全令牌（需要管理员权限）
 */
export async function resetAllTokens(): Promise<void> {
  return invoke('reset_all_tokens')
}

/**
 * 获取 JWT 密钥
 */
export async function getJwtSecretKey(): Promise<string> {
  return invoke('get_jwt_secret_key')
}

/**
 * 获取本地 Token
 */
export async function getLocalToken(): Promise<string> {
  return invoke('get_local_token')
}

// ==================== 健康检查 API ====================

/**
 * 健康检查响应
 */
export interface HealthStatus {
  status: string
  timestamp: string
  service: string
}

/**
 * 检查连接
 */
export async function checkConnection(): Promise<boolean> {
  return invoke('check_connection')
}

/**
 * 获取健康状态
 */
export async function getHealthStatus(): Promise<HealthStatus> {
  return invoke('get_health_status')
}

// ==================== 本地系统信息 API ====================

/**
 * 获取本地系统信息
 * 由客户端Tauri后端直接获取，不经过服务端
 */
export async function getLocalSystemInfo(): Promise<SystemInfo> {
  return invoke('get_local_system_info')
}

// ==================== Nginx管理 API ====================

/**
 * Nginx状态响应
 */
export interface NginxStatusResponse {
  is_loaded: boolean
  status: string
  pid?: number
  version?: string
  exe_path?: string
  config_dir?: string
}

/**
 * Nginx操作响应
 */
export interface NginxActionResponse {
  success: boolean
  message: string
  status?: string
  pid?: number
}

/**
 * 获取Nginx状态
 */
export async function getNginxStatus(): Promise<NginxStatusResponse> {
  return invoke('get_nginx_status')
}

/**
 * 载入Nginx
 * @param exe_path Nginx可执行文件路径
 */
export async function loadNginx(exe_path: string): Promise<NginxActionResponse> {
  return invoke('load_nginx', { exe_path })
}

/**
 * 启动Nginx
 */
export async function startNginx(): Promise<NginxActionResponse> {
  return invoke('start_nginx')
}

/**
 * 停止Nginx
 */
export async function stopNginx(): Promise<NginxActionResponse> {
  return invoke('stop_nginx')
}

/**
 * 重启Nginx
 */
export async function restartNginx(): Promise<NginxActionResponse> {
  return invoke('restart_nginx')
}

/**
 * 下载并解压Nginx
 * @param url 下载URL
 * @param target_dir 目标目录（可选）
 */
export async function downloadAndExtractNginx(
  url: string,
  target_dir?: string
): Promise<NginxActionResponse> {
  return invoke('download_and_extract_nginx', { url, target_dir: target_dir || null })
}

/**
 * 获取Nginx下载URL
 */
export async function getNginxDownloadUrl(): Promise<string> {
  return invoke('get_nginx_download_url')
}

/**
 * 更新Nginx下载URL
 * @param url 新的下载URL
 */
export async function updateNginxDownloadUrl(url: string): Promise<NginxActionResponse> {
  return invoke('update_nginx_download_url', { url })
}

/**
 * 验证Nginx可执行文件
 * @param exe_path Nginx可执行文件路径
 */
export async function validateNginx(exe_path: string): Promise<string> {
  return invoke('validate_nginx', { exe_path })
}

/**
 * Nginx代理配置
 */
export interface NginxProxyConfig {
  enabled: boolean
  listen_port: number
  backend_url: string
  add_security_headers: boolean
  add_cors_headers: boolean
  cors_origins: string
  cors_methods: string
  cors_headers: string
  enable_hsts: boolean
  hsts_max_age: number
  server_name: string
  // 性能优化配置
  connect_timeout: number
  send_timeout: number
  read_timeout: number
  enable_keepalive: boolean
  keepalive_connections: number
  worker_processes: string
  enable_performance: boolean
}

/**
 * Nginx配置保存响应
 */
export interface NginxConfigSaveResponse {
  success: boolean
  message: string
  need_restart: boolean
}

/**
 * 获取Nginx代理配置
 */
export async function getNginxProxyConfig(): Promise<NginxProxyConfig> {
  return invoke('get_nginx_proxy_config')
}

/**
 * 保存Nginx代理配置
 * @param config 代理配置
 */
export async function saveNginxProxyConfig(
  config: NginxProxyConfig
): Promise<NginxConfigSaveResponse> {
  return invoke('save_nginx_proxy_config', { config })
}

/**
 * Nginx平台信息
 */
export interface NginxPlatformInfo {
  platform: string
  supports_manual_load: boolean
  supports_download: boolean
  uses_package_manager: boolean
  package_manager?: string
  package_version?: string
  config_path?: string
}

/**
 * 获取Nginx平台信息
 */
export async function getNginxPlatformInfo(): Promise<NginxPlatformInfo> {
  return invoke('get_nginx_platform_info')
}

// ==================== 引导页面 API ====================

/**
 * 服务端检查结果
 */
export interface ServerCheckResult {
  found: boolean
  path?: string
  version?: string
  autoDetected: boolean
}

/**
 * Git检查结果
 */
export interface GitCheckResult {
  installed: boolean
  version?: string
  path?: string
  httpBackendAvailable: boolean
}

/**
 * 检查服务端路径
 */
export async function checkServerPath(): Promise<ServerCheckResult> {
  return invoke('check_server_path')
}

/**
 * 验证并保存服务端路径
 * @param path 服务端可执行文件路径
 */
export async function validateAndSaveServerPath(path: string): Promise<ServerCheckResult> {
  return invoke('validate_and_save_server_path', { path })
}

/**
 * 检查Git安装
 */
export async function checkGitInstallation(): Promise<GitCheckResult> {
  return invoke('check_git_installation')
}

/**
 * 标记引导完成
 */
export async function markGuideCompleted(): Promise<void> {
  return invoke('mark_guide_completed')
}

/**
 * 检查是否已完成引导
 */
export async function isGuideCompleted(): Promise<boolean> {
  return invoke('is_guide_completed')
}

/**
 * 检查是否存在用户配置文件
 * 用于判断是否需要显示引导页面
 */
export async function hasUserConfigFile(): Promise<boolean> {
  return invoke('has_user_config_file')
}

// ==================== 压力测试和数据库配置 API ====================

/**
 * 获取压力测试模式状态
 */
export async function getStressTest(): Promise<boolean> {
  return invoke('get_stress_test')
}

/**
 * 更新压力测试模式
 * @param stress 是否启用压力测试
 */
export async function updateStressTest(stress: boolean): Promise<void> {
  return invoke('update_stress_test', { stress })
}

/**
 * 获取所有数据库连接 URL
 * @returns 数据库类型到 URL 的映射
 */
export async function getDatabaseUrls(): Promise<Record<string, string>> {
  return invoke('get_database_urls')
}

/**
 * 获取指定类型的数据库连接 URL
 * @param dbType 数据库类型: 'sqlite' | 'postgresql' | 'mysql'
 */
export async function getDatabaseUrl(dbType: string): Promise<string> {
  return invoke('get_database_url', { dbType })
}

/**
 * 获取数据库类型（从 client.toml 读取）
 * @returns 当前选择的数据库类型: 'sqlite' | 'postgresql' | 'mysql'
 */
export async function getDatabaseType(): Promise<string> {
  return invoke('get_database_type')
}

/**
 * 切换数据库类型（保存到 client.toml）
 * @param dbType 数据库类型: 'sqlite' | 'postgresql' | 'mysql'
 */
export async function switchDatabaseType(dbType: string): Promise<void> {
  return invoke('switch_database_type', { dbType })
}

/**
 * 更新指定类型的数据库连接 URL
 * @param dbType 数据库类型: 'sqlite' | 'postgresql' | 'mysql'
 * @param url 数据库连接 URL
 */
export async function updateDatabaseUrl(dbType: string, url: string): Promise<void> {
  return invoke('update_database_url', { dbType, url })
}

/**
 * 检测系统中已安装的数据库
 * 
 * 检查 Python 环境中可用的数据库驱动：
 * - SQLite: 总是可用（内置于 Python）
 * - PostgreSQL: 需要 pg8000 驱动
 * - MySQL: 需要 pymysql 驱动
 * 
 * @returns 已安装的数据库类型列表，如 ['sqlite', 'postgresql']
 */
export async function checkInstalledDatabases(): Promise<string[]> {
  return invoke('check_installed_databases')
}
