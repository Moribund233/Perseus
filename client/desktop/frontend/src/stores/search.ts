import { create } from 'zustand';
import { workspaceSearchApi, type LocalSearchHit } from '../api/search';
import { useWorkspaceStore } from './workspace';

interface SearchState {
  query: string;
  results: LocalSearchHit[];
  total: number;
  truncated: boolean;
  searching: boolean;
  error: string | null;
  lastPath: string | null;

  search: (q: string, opts?: { path?: string }) => Promise<void>;
  clear: () => void;
}

export const useSearchStore = create<SearchState>((set, get) => ({
  query: '',
  results: [],
  total: 0,
  truncated: false,
  searching: false,
  error: null,
  lastPath: null,

  search: async (q, opts) => {
    const ws = useWorkspaceStore.getState().current;
    const query = q.trim();
    if (!ws || !query) {
      set({ results: [], total: 0, truncated: false, query, searching: false, error: null });
      return;
    }
    set({ query, searching: true, error: null });
    try {
      const res = await workspaceSearchApi.search(ws.id, query, {
        path: opts?.path,
        max_results: 500,
      });
      set({
        results: res.results ?? [],
        total: res.total ?? 0,
        truncated: res.truncated ?? false,
        searching: false,
        lastPath: res.path,
      });
    } catch (e) {
      set({ error: (e as Error).message, searching: false });
    }
  },

  clear: () => set({ query: '', results: [], total: 0, truncated: false, error: null, lastPath: null }),
}));

export function useSearchResults(): LocalSearchHit[] {
  return useSearchStore((s) => s.results);
}