import { apiRequest } from './client';

export interface ProcessInfo {
  pid: number;
  memory_mb: number;
  cpu_percent: number;
  threads: number;
  connections: number;
}

export interface RequestMetrics {
  total_requests: number;
  active_requests: number;
  requests_per_second: number;
  average_response_time: number;
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

export const adminApi = {
  getStatus: () => apiRequest<AppStatus>('/api/app/status'),
  getComponents: () => apiRequest<ComponentsResponse>('/api/app/components'),
};