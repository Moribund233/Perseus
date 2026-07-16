import { apiRequest } from './client';

export interface UserProfile {
  id: string;
  username: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  is_admin: boolean;
  avatar_url?: string;
  created_at: string;
  updated_at: string;
}

export interface UpdateProfileRequest {
  username?: string;
  email?: string;
  full_name?: string;
}

export interface DashboardData {
  repo_count: number;
  open_prs: number;
  open_issues: number;
  recent_activities: Record<string, unknown>[];
  recent_prs: Record<string, unknown>[];
  recent_issues: Record<string, unknown>[];
}

export interface SSHKey {
  id: string;
  name: string;
  public_key: string;
  fingerprint: string;
  created_at: string;
}

export interface ChangePasswordRequest {
  old_password: string;
  new_password: string;
}

export interface OAuthAccount {
  provider: string;
  provider_user_id: string;
  created_at: string;
}

export const settingsApi = {
  getUser: (userId: string) =>
    apiRequest<UserProfile>(`/api/v1/users/${userId}`),

  updateProfile: (userId: string, data: UpdateProfileRequest) =>
    apiRequest<UserProfile>(`/api/v1/users/${userId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  getDashboard: () =>
    apiRequest<DashboardData>('/api/v1/users/me/dashboard'),

  getUserPullRequests: () =>
    apiRequest<Record<string, unknown>[]>('/api/v1/users/me/pull-requests'),

  getUserIssues: () =>
    apiRequest<Record<string, unknown>[]>('/api/v1/users/me/issues'),

  changePassword: (data: ChangePasswordRequest) =>
    apiRequest<void>('/api/v1/users/me/password', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  uploadAvatar: (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return apiRequest<UserProfile>('/api/v1/users/me/avatar', {
      method: 'POST',
      body: formData,
      headers: {}, // Let fetch set multipart boundary
    });
  },

  getAvatarUrl: (userId: string) =>
    `/api/v1/users/${userId}/avatar`,

  listSSHKeys: () =>
    apiRequest<SSHKey[]>('/api/v1/keys'),

  addSSHKey: (data: { name: string; public_key: string }) =>
    apiRequest<SSHKey>('/api/v1/keys', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  deleteSSHKey: (keyId: string) =>
    apiRequest<void>(`/api/v1/keys/${keyId}`, { method: 'DELETE' }),

  listOAuthAccounts: () =>
    apiRequest<OAuthAccount[]>('/api/v1/users/me/oauth'),

  unlinkOAuth: (provider: string) =>
    apiRequest<void>(`/api/v1/users/me/oauth/${provider}`, { method: 'DELETE' }),
};
