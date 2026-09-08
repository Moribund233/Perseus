import { create } from 'zustand';
import { myWorkApi, type MyIssue, type MyPullRequest } from '../api/myWork';
import { useServersStore } from './servers';

function serverId(): string | null {
  return useServersStore.getState().currentServerId;
}

interface MyWorkState {
  pullRequests: MyPullRequest[];
  issues: MyIssue[];
  isLoading: boolean;
  error: string | null;

  fetchMyPullRequests: (status?: string) => Promise<void>;
  fetchMyIssues: (status?: string) => Promise<void>;
}

export const useMyWorkStore = create<MyWorkState>((set) => ({
  pullRequests: [],
  issues: [],
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
}));
