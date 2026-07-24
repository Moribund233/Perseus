import { apiRequest } from './client';

export interface PlatformStats {
  repository_count: number;
  commit_count: number;
  user_count: number;
  uptime_seconds: number;
}

export const statsApi = {
  getPlatformStats: () => apiRequest<PlatformStats>('/api/v1/stats/platform'),
};
