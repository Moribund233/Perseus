import { create } from 'zustand';
import {
  notificationsApi,
  type Notification,
  type NotificationPreference,
} from '../api/notifications';
import { useServersStore } from './servers';

function serverId(): string | null {
  return useServersStore.getState().currentServerId;
}

interface NotificationsState {
  notifications: Notification[];
  unreadCount: number;
  preferences: NotificationPreference | null;
  isLoading: boolean;
  error: string | null;

  fetchNotifications: () => Promise<void>;
  fetchUnreadCount: () => Promise<void>;
  markAsRead: (id: string) => Promise<void>;
  markAllAsRead: () => Promise<void>;
  remove: (id: string) => Promise<void>;
  fetchPreferences: () => Promise<void>;
  updatePreferences: (data: Partial<NotificationPreference>) => Promise<void>;
  /** F-205: WS 实时推送到达时插入新通知并对齐未读数 */
  addLive: (notification: Notification, unreadCount?: number) => void;
}

export const useNotificationsStore = create<NotificationsState>((set, get) => ({
  notifications: [],
  unreadCount: 0,
  preferences: null,
  isLoading: false,
  error: null,

  fetchNotifications: async () => {
    const sid = serverId();
    if (!sid) { set({ error: 'no server' }); return; }
    set({ isLoading: true, error: null });
    try {
      const data = await notificationsApi.list(sid);
      set({ notifications: data.notifications ?? [], isLoading: false });
    } catch (e) {
      set({ error: (e as Error).message, isLoading: false });
    }
  },

  fetchUnreadCount: async () => {
    const sid = serverId();
    if (!sid) return;
    try {
      const { count } = await notificationsApi.getUnreadCount(sid);
      set({ unreadCount: count });
    } catch {
      /* 离线时保留上次未读数 */
    }
  },

  markAsRead: async (id) => {
    const sid = serverId();
    if (!sid) return;
    try {
      await notificationsApi.markAsRead(sid, id);
      set((state) => ({
        notifications: state.notifications.map((n) =>
          n.id === id ? { ...n, is_read: true } : n),
        unreadCount: Math.max(0, state.unreadCount - (state.notifications.find((n) => n.id === id && !n.is_read) ? 1 : 0)),
      }));
    } catch (e) {
      set({ error: (e as Error).message });
    }
  },

  markAllAsRead: async () => {
    const sid = serverId();
    if (!sid) return;
    try {
      await notificationsApi.markAllAsRead(sid);
      set((state) => ({
        notifications: state.notifications.map((n) => ({ ...n, is_read: true })),
        unreadCount: 0,
      }));
    } catch (e) {
      set({ error: (e as Error).message });
    }
  },

  remove: async (id) => {
    const sid = serverId();
    if (!sid) return;
    try {
      await notificationsApi.delete(sid, id);
      set((state) => {
        const target = state.notifications.find((n) => n.id === id);
        return {
          notifications: state.notifications.filter((n) => n.id !== id),
          unreadCount: target && !target.is_read ? Math.max(0, state.unreadCount - 1) : state.unreadCount,
        };
      });
    } catch (e) {
      set({ error: (e as Error).message });
    }
  },

  fetchPreferences: async () => {
    const sid = serverId();
    if (!sid) return;
    try {
      const preferences = await notificationsApi.getPreferences(sid);
      set({ preferences });
    } catch (e) {
      set({ error: (e as Error).message });
    }
  },

  updatePreferences: async (data) => {
    const sid = serverId();
    if (!sid) return;
    try {
      const preferences = await notificationsApi.updatePreferences(sid, data);
      set({ preferences });
    } catch (e) {
      set({ error: (e as Error).message });
    }
  },

  addLive: (notification, unreadCount) => {
    set((state) => {
      if (state.notifications.some((n) => n.id === notification.id)) {
        // 已存在（如重连后补推）仅对齐未读数
        return unreadCount != null ? { unreadCount } : state;
      }
      return {
        notifications: [notification, ...state.notifications],
        unreadCount: unreadCount ?? state.unreadCount + 1,
      };
    });
  },
}));
