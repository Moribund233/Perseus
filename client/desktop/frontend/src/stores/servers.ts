import { create } from 'zustand';
import type { ServerRecord } from '../api/servers';
import { serversApi } from '../api/servers';

const CURRENT_KEY = 'perseus.currentServerId';
// Welcome「管理服务器」按钮的内存态路由值: 仅本会话有效, 不持久化,
// 否则下次启动会直接进入 ServerShell 管理页而跳过 Welcome。
export const MANAGER_VIEW = '__manager__';

function readCurrent(): string | null {
  try {
    const v = localStorage.getItem(CURRENT_KEY);
    if (v === MANAGER_VIEW) {
      localStorage.removeItem(CURRENT_KEY);
      return null;
    }
    return v;
  } catch {
    return null;
  }
}

interface ServersState {
  servers: ServerRecord[];
  currentServerId: string | null;
  loading: boolean;
  error: string | null;
  setServers: (list: ServerRecord[]) => void;
  upsert: (s: ServerRecord) => void;
  remove: (id: string) => void;
  setCurrent: (id: string | null) => void;
  refreshHealth: (id: string) => Promise<ServerRecord | null>;
  fetchServers: () => Promise<void>;
}

export const useServersStore = create<ServersState>((set, get) => ({
  servers: [],
  currentServerId: readCurrent(),
  loading: false,
  error: null,

  setServers: (list) => set({ servers: list }),
  upsert: (s) =>
    set((state) => ({
      servers: state.servers.some((x) => x.id === s.id)
        ? state.servers.map((x) => (x.id === s.id ? s : x))
        : [s, ...state.servers],
    })),
  remove: (id) =>
    set((state) => {
      const next = state.servers.filter((x) => x.id !== id);
      const current = state.currentServerId === id ? null : state.currentServerId;
      if (current === null) {
        try {
          localStorage.removeItem(CURRENT_KEY);
        } catch { /* ignore */ }
      }
      return { servers: next, currentServerId: current };
    }),

  setCurrent: (id) => {
    try {
      if (id && id !== MANAGER_VIEW) {
        localStorage.setItem(CURRENT_KEY, id);
      } else {
        localStorage.removeItem(CURRENT_KEY);
      }
    } catch { /* ignore */ }
    set({ currentServerId: id });
  },

  refreshHealth: async (id) => {
    try {
      const res = await serversApi.health(id);
      const server = get().servers.find((x) => x.id === id);
      if (server) {
        const updated: ServerRecord = { ...server, health: res.health as ServerRecord['health'] };
        get().upsert(updated);
        return updated;
      }
      return null;
    } catch {
      const server = get().servers.find((x) => x.id === id);
      if (server) {
        const updated: ServerRecord = { ...server, health: 'offline' };
        get().upsert(updated);
        return updated;
      }
      return null;
    }
  },

  fetchServers: async () => {
    set({ loading: true, error: null });
    try {
      const list = await serversApi.list();
      set({ servers: list, loading: false });
      const current = get().currentServerId;
      if (current && !list.some((x) => x.id === current)) {
        get().setCurrent(null);
      }
    } catch (e) {
      set({ error: (e as Error).message, loading: false });
    }
  },
}));
