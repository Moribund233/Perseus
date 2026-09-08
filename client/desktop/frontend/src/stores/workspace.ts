import { create } from 'zustand';
import type { Workspace } from '../api/workspaces';
import * as workspacesApi from '../api/workspaces';

interface WorkspaceState {
  workspaces: Workspace[];
  current: Workspace | null;
  setWorkspaces: (list: Workspace[]) => void;
  setCurrent: (ws: Workspace | null) => void;
  touch: (wsId: string) => void;
  fetchWorkspaces: () => Promise<void>;
}

export const useWorkspaceStore = create<WorkspaceState>((set, get) => ({
  workspaces: [],
  current: null,
  setWorkspaces: (list) => set({ workspaces: list }),
  setCurrent: (ws) => set({ current: ws }),
  touch: async (wsId) => {
    try {
      await workspacesApi.touchWorkspace(wsId);
      void get().fetchWorkspaces();
    } catch {
      /* 忽略 touch 失败 */
    }
  },
  fetchWorkspaces: async () => {
    try {
      const list = await workspacesApi.listWorkspaces();
      set({ workspaces: list });
    } catch {
      /* 静默失败，保留上次列表 */
    }
  },
}));
