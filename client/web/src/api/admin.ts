import { apiRequest } from './client';

export interface ProcessInfo {
  pid: number;
  memory_mb: number;
  cpu_percent: number;
  threads: number;
  connections: number;
}

export interface RequestMetrics {
  total: number;
  success: number;
  failed: number;
  avg_response_time_ms: number;
  requests_per_minute: number;
}

export interface GitOperationMetrics {
  active_clones: number;
  active_pushes: number;
  queue_size: number;
}

export interface SchemaState {
  applied?: string;
  head?: string;
}

export interface AppStatus {
  status: string;
  debug_mode: boolean;
  uptime_seconds: number;
  uptime_formatted: string;
  version: string;
  server_time: string;
  process: ProcessInfo;
  requests: RequestMetrics;
  git_operations: GitOperationMetrics;
  schema_state: SchemaState;
}

export interface ComponentInfo {
  service: string;
  name: string;
  label: string | null;
  state: string;
  health: string | null;
  running: boolean;
  image: string | null;
  started_at: string | null;
  uptime_seconds: number | null;
  restart_count: number | null;
  exit_code: number | null;
  status_text: string | null;
}

export type ComponentHealth = 'healthy' | 'unhealthy' | 'starting' | null;

export interface ComponentsSummary {
  total: number;
  running: number;
  stopped: number;
  healthy: number;
  unhealthy: number;
  starting: number;
}

export interface ComponentsResponse {
  available: boolean;
  runtime: string;
  project: string | null;
  reason: string | null;
  generated_at: string;
  components: ComponentInfo[];
  summary: ComponentsSummary;
}

export type ConfigSectionData = Record<string, unknown>;

/** GET /api/app/config 响应：data 为全量或单节配置 */
export interface ConfigData {
  [section: string]: ConfigSectionData;
}

/** 配置管理端点统一响应（success/errors/hints） */
export interface ConfigResponse {
  success: boolean;
  data: ConfigData | null;
  errors: string[];
  hints?: string[];
}

export const configApi = {
  getConfig: (section?: string) => {
    const qs = section ? `?section=${encodeURIComponent(section)}` : '';
    return apiRequest<ConfigResponse>(`/api/app/config${qs}`);
  },
  updateConfig: (config: ConfigData) =>
    apiRequest<ConfigResponse>('/api/app/config', {
      method: 'POST',
      body: JSON.stringify({ config }),
    }),
  validateConfig: (config?: ConfigData) =>
    apiRequest<ConfigResponse>('/api/app/config/validate', {
      method: 'POST',
      body: JSON.stringify(config ?? {}),
    }),
  resetConfig: () =>
    apiRequest<ConfigResponse>('/api/app/config/reset', {
      method: 'POST',
    }),
};

export const adminApi = {
  getStatus: () => apiRequest<AppStatus>('/api/app/status'),
  getComponents: () => apiRequest<ComponentsResponse>('/api/app/components'),
  /** 切换调试模式（仅管理员；写 config.toml，重启后生效） */
  setDebugMode: (enabled: boolean) =>
    apiRequest<DebugModeResponse>('/api/app/debug', {
      method: 'POST',
      body: JSON.stringify({ enabled }),
    }),
};

// ---------- 日志 ----------

export interface LogFileInfo {
  name: string;
  size: number;
  size_formatted: string;
  modified: string;
  /** 磁盘分片数（含当前段） */
  parts: number;
  /** 全部分片合计大小 */
  total_size: number;
  total_size_formatted: string;
  /** 已达保留上限，更早分片可能已被丢弃 */
  truncated: boolean;
}

/** GET /api/app/logs 响应 */
export interface LogInfo {
  log_dir: string;
  today_dir: string;
  today_files: LogFileInfo[];
  available_dates: string[];
}

/** 日志分片在返回窗口内的起始偏移 */
export interface LogSegmentStart {
  name: string;
  offset: number;
}

/** GET /api/app/logs/content 响应 */
export interface LogContent {
  date: string;
  log_name: string;
  lines: number;
  total_lines: number;
  content: string;
  exists: boolean;
  /** 窗口覆盖的分片（旧→新） */
  window_parts: string[];
  /** 各分片在窗口内的起始行偏移 */
  segment_starts: LogSegmentStart[];
  /** 是否已达保留上限、更早分片可能被丢弃 */
  truncated: boolean;
}

/** POST /api/app/logs/cleanup 响应 */
export interface LogCleanupResponse {
  success: boolean;
  deleted_count: number;
  keep_days: number;
}

export const logsApi = {
  getInfo: () => apiRequest<LogInfo>('/api/app/logs'),
  getContent: (params: { date?: string; log_name?: string; lines?: number; level?: string }) => {
    const qs = new URLSearchParams();
    if (params.date) qs.set('date', params.date);
    if (params.log_name) qs.set('log_name', params.log_name);
    if (params.lines) qs.set('lines', String(params.lines));
    if (params.level) qs.set('level', params.level);
    const suffix = qs.toString() ? `?${qs.toString()}` : '';
    return apiRequest<LogContent>(`/api/app/logs/content${suffix}`);
  },
  cleanup: (keepDays: number) =>
    apiRequest<LogCleanupResponse>(`/api/app/logs/cleanup?keep_days=${keepDays}`, { method: 'POST' }),
};

// ---------- 运维操作 ----------

/** POST /api/app/restart · POST /api/app/shutdown 响应 */
export interface ActionResponse {
  success: boolean;
  message: string;
}

/** POST /api/app/debug 响应（调试模式切换，重启后生效） */
export interface DebugModeResponse {
  success: boolean;
  debug: boolean | null;
  restart_required: boolean;
  message: string;
}

export const operationsApi = {
  restart: () => apiRequest<ActionResponse>('/api/app/restart', { method: 'POST' }),
  shutdown: () => apiRequest<ActionResponse>('/api/app/shutdown', { method: 'POST' }),
};

// ---------- 调试工具 ----------

/** GET /api/v1/debug/status 响应 */
export interface DebugStatus {
  debug_mode: boolean;
  config_path: string;
  config_exists: boolean;
  database_url: string;
  database_type: string;
  environment: Record<string, string>;
  stress_test_mode: boolean;
}

/** POST /api/v1/debug/initdb 响应 */
export interface InitDbResponse {
  success: boolean;
  message: string;
  details: Record<string, unknown>;
}

/** POST /api/v1/debug/initconf 响应 */
export interface InitConfResponse {
  success: boolean;
  message: string;
  config_path: string;
  backup_path: string | null;
}

export const debugApi = {
  getStatus: () => apiRequest<DebugStatus>('/api/v1/debug/status'),
  initDb: () => apiRequest<InitDbResponse>('/api/v1/debug/initdb', { method: 'POST' }),
  initConf: () => apiRequest<InitConfResponse>('/api/v1/debug/initconf', { method: 'POST' }),
};