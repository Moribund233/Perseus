import { apiRequest } from './client';

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

export const notificationsApi = {
  list: (params?: { page?: number; per_page?: number; unread_only?: boolean }) => {
    const qs = params ? '?' + new URLSearchParams(params as Record<string, string>).toString() : '';
    return apiRequest<NotificationListResponse>(`/api/v1/notifications${qs}`);
  },

  getUnreadCount: () =>
    apiRequest<{ count: number }>('/api/v1/notifications/unread-count'),

  markAsRead: (id: string) =>
    apiRequest<void>(`/api/v1/notifications/${id}/read`, { method: 'PATCH' }),

  markAllAsRead: () =>
    apiRequest<void>('/api/v1/notifications/read-all', { method: 'POST' }),

  delete: (id: string) =>
    apiRequest<void>(`/api/v1/notifications/${id}`, { method: 'DELETE' }),

  getPreferences: () =>
    apiRequest<NotificationPreference>('/api/v1/notifications/preferences'),

  updatePreferences: (data: Partial<NotificationPreference>) =>
    apiRequest<NotificationPreference>('/api/v1/notifications/preferences', {
      method: 'PUT',
      body: JSON.stringify(data),
    }),
};
