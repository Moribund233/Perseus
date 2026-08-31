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
  /** 最近 30 天按日活动聚合, key 为 "YYYY-MM-DD" */
  contributions_by_day: Record<string, number>;
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
  provider_username: string;
  created_at: string;
}

export interface PaginationResponse<T> {
  items: T[];
  total: number;
  page: number;
  limit: number;
  pages: number;
  has_next: boolean;
  has_prev: boolean;
}

interface MyUserRef {
  id: string;
  username: string;
  full_name: string | null;
}

export interface MyPullRequest {
  id: string;
  pr_number: number;
  title: string;
  status: string;
  is_draft: boolean;
  repository_id: string;
  author: MyUserRef;
  created_at: string;
}

export interface MyIssue {
  id: string;
  issue_number: number;
  title: string;
  status: string;
  priority: string;
  repository_id: string;
  author: MyUserRef;
  assignee: MyUserRef | null;
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

  getUserPullRequests: (params?: { status?: string; page?: number; limit?: number }) => {
    const qs = params ? '?' + new URLSearchParams(params as Record<string, string>).toString() : '';
    return apiRequest<PaginationResponse<MyPullRequest>>(`/api/v1/users/me/pull-requests${qs}`);
  },

  getUserIssues: (params?: { status?: string; page?: number; limit?: number }) => {
    const qs = params ? '?' + new URLSearchParams(params as Record<string, string>).toString() : '';
    return apiRequest<PaginationResponse<MyIssue>>(`/api/v1/users/me/issues${qs}`);
  },

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
