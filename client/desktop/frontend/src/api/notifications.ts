import { proxyRequest } from './client';

export interface Notification {
  id: string;
  user_id: string;
  type: string;
  title: string;
  message: string;
  repository_id: string | null;
  target_type: string | null;
  target_id: string | null;
  is_read: boolean;
  created_at: string;
}

export interface NotificationPreference {
  email_on_mention: boolean;
  email_on_pr_review: boolean;
  email_on_issue_comment: boolean;
  email_on_pr_merge: boolean;
  email_on_release: boolean;
  in_app_on_mention: boolean;
  in_app_on_pr_review: boolean;
  in_app_on_issue_comment: boolean;
}

export interface NotificationListResponse {
  notifications: Notification[];
  total: number;
}

// notificationsApi：全部经本地网关 proxy 转发到目标服务器，首个参数为服务器 id。
export const notificationsApi = {
  list: (serverId: string, params?: { page?: number; per_page?: number; unread_only?: boolean }) => {
    const qs = params ? '?' + new URLSearchParams(params as Record<string, string>).toString() : '';
    return proxyRequest<NotificationListResponse>(serverId, `/api/v1/notifications${qs}`);
  },

  getUnreadCount: (serverId: string) =>
    proxyRequest<{ count: number }>(serverId, '/api/v1/notifications/unread-count'),

  markAsRead: (serverId: string, id: string) =>
    proxyRequest<void>(serverId, `/api/v1/notifications/${id}/read`, { method: 'PATCH' }),

  markAllAsRead: (serverId: string) =>
    proxyRequest<void>(serverId, '/api/v1/notifications/read-all', { method: 'POST' }),

  delete: (serverId: string, id: string) =>
    proxyRequest<void>(serverId, `/api/v1/notifications/${id}`, { method: 'DELETE' }),

  getPreferences: (serverId: string) =>
    proxyRequest<NotificationPreference>(serverId, '/api/v1/notifications/preferences'),

  updatePreferences: (serverId: string, data: Partial<NotificationPreference>) =>
    proxyRequest<NotificationPreference>(serverId, '/api/v1/notifications/preferences', {
      method: 'PUT',
      body: JSON.stringify(data),
    }),
};
