import { create } from 'zustand';
import type { Workspace } from '../api/workspaces';

interface WorkspaceState {
  workspaces: Workspace[];
  current: Workspace | null;
  setWorkspaces: (list: Workspace[]) => void;
  setCurrent: (ws: Workspace | null) => void;
}

export const useWorkspaceStore = create<WorkspaceState>((set) => ({
  workspaces: [],
  current: null,
  setWorkspaces: (list) => set({ workspaces: list }),
  setCurrent: (ws) => set({ current: ws }),
}));
