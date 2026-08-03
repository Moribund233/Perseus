import { create } from 'zustand';
import type { GitStatus } from '../api/workspaces';

interface GitState {
  status: GitStatus | null;
  setStatus: (s: GitStatus | null) => void;
}

export const useGitStore = create<GitState>((set) => ({
  status: null,
  setStatus: (s) => set({ status: s }),
}));
