import { create } from 'zustand';
import { usersApi, type User } from '../api/users';
import { useServersStore } from './servers';

// 当前连接的服务器 id；单服务器同时工作，取自 servers store。
function serverId(): string | null {
  return useServersStore.getState().currentServerId;
}

interface IdentityState {
  me: User | null;
  loading: boolean;
  error: string | null;
  fetchIdentity: () => Promise<void>;
  clear: () => void;
}

export const useIdentityStore = create<IdentityState>((set) => ({
  me: null,
  loading: false,
  error: null,

  fetchIdentity: async () => {
    const sid = serverId();
    if (!sid) {
      set({ me: null, loading: false });
      return;
    }
    set({ loading: true, error: null });
    try {
      const me = await usersApi.getMe(sid);
      set({ me, loading: false });
    } catch (e) {
      set({ error: (e as Error).message, loading: false });
    }
  },

  clear: () => {
    set({ me: null, error: null });
  },
}));