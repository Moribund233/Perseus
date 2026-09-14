import { create } from 'zustand';
import { myWorkApi, type DashboardData, type MyIssue, type MyPullRequest } from '../api/myWork';
import { useServersStore } from './servers';

function serverId(): string | null {
  return useServersStore.getState().currentServerId;
}

interface MyWorkState {
  pullRequests: MyPullRequest[];
  issues: MyIssue[];
  dashboard: DashboardData | null;
  isLoading: boolean;
  error: string | null;

  fetchMyPullRequests: (status?: string) => Promise<void>;
  fetchMyIssues: (status?: string) => Promise<void>;
  fetchDashboard: () => Promise<void>;
}

export const useMyWorkStore = create<MyWorkState>((set) => ({
  pullRequests: [],
  issues: [],
  dashboard: null,
  isLoading: false,
  error: null,

  fetchMyPullRequests: async (status) => {
    const sid = serverId();
    if (!sid) { set({ error: 'no server' }); return; }
    set({ isLoading: true, error: null });
    try {
      const res = await myWorkApi.getMyPullRequests(sid, { status, page: 1, limit: 100 });
      set({ pullRequests: res.items ?? [], isLoading: false });
    } catch (e) {
      set({ error: (e as Error).message, isLoading: false });
    }
  },

  fetchMyIssues: async (status) => {
    const sid = serverId();
    if (!sid) { set({ error: 'no server' }); return; }
    set({ isLoading: true, error: null });
    try {
      const res = await myWorkApi.getMyIssues(sid, { status, page: 1, limit: 100 });
      set({ issues: res.items ?? [], isLoading: false });
    } catch (e) {
      set({ error: (e as Error).message, isLoading: false });
    }
  },

  // 仪表盘统计/贡献图/活动流：失败时置 null 展示空态，不阻断列表。
  fetchDashboard: async () => {
    const sid = serverId();
    if (!sid) return;
    try {
      const dashboard = await myWorkApi.getDashboard(sid);
      set({ dashboard });
    } catch {
      set({ dashboard: null });
    }
  },
}));
