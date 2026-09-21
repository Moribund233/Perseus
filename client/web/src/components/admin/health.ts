import type { ComponentInfo } from '../../api/admin';

export type Tone = 'ok' | 'warn' | 'danger' | 'idle';

/** 组件整体色调：运行 + 健康 → ok；starting/restarting → warn；异常退出 → danger；正常退出 → idle */
export function componentTone(c: ComponentInfo): Tone {
  if (c.state === 'exited' && c.exit_code === 0) return 'idle';
  if (!c.running) {
    if (c.state === 'starting' || c.state === 'restarting') return 'warn';
    return 'danger';
  }
  if (c.health === 'unhealthy') return 'danger';
  if (c.health === 'starting') return 'warn';
  return 'ok';
}

/** 是否属于"需要关注"的异常组件 */
export function isProblem(c: ComponentInfo): boolean {
  return componentTone(c) === 'danger' || componentTone(c) === 'warn';
}

export function formatDuration(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined || seconds < 0) return '—';
  const s = Math.floor(seconds);
  const d = Math.floor(s / 86400);
  const h = Math.floor((s % 86400) / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  if (d > 0) return `${d}d ${h}h`;
  if (h > 0) return `${h}h ${m}m`;
  if (m > 0) return `${m}m ${sec}s`;
  return `${sec}s`;
}

export function formatBytesMb(mb: number | null | undefined): string {
  if (mb === null || mb === undefined) return '—';
  if (mb >= 1024) return `${(mb / 1024).toFixed(2)} GB`;
  return `${mb.toFixed(1)} MB`;
}

/** 按服务名归入原型中的分组 */
const GROUP_OF: Record<string, string> = {
  gateway: 'ingress',
  app: 'application',
  collab: 'application',
  git_cgi: 'git',
  gitcgi: 'git',
  sshd: 'git',
  postgres: 'data',
  redis: 'data',
  docker_socket_proxy: 'data',
  init: 'tasks',
  prometheus: 'monitoring',
  grafana: 'monitoring',
};

export const GROUP_ORDER = ['ingress', 'application', 'git', 'data', 'tasks', 'monitoring', 'other'];

export function groupOf(service: string): string {
  const key = service.toLowerCase().replace(/-/g, '_');
  if (GROUP_OF[key]) return GROUP_OF[key];
  if (key.includes('gateway')) return 'ingress';
  if (key.includes('git') || key.includes('ssh')) return 'git';
  if (key.includes('postgres') || key.includes('redis') || key.includes('db')) return 'data';
  if (key.includes('init')) return 'tasks';
  return 'other';
}