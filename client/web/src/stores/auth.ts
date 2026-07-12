import { create } from 'zustand';
import { authApi, type LoginRequest, type RegisterRequest } from '../api/auth';

export interface User {
  id: number;
  username: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  is_admin: boolean;
  avatar_url?: string;
  created_at?: string;
  updated_at?: string;
}

interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;

  login: (data: LoginRequest) => Promise<void>;
  register: (data: RegisterRequest) => Promise<void>;
  logout: () => void;
  loadUser: () => Promise<void>;
  setAccessToken: (token: string) => void;
  initialize: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  accessToken: localStorage.getItem('access_token'),
  refreshToken: localStorage.getItem('refresh_token'),
  isAuthenticated: false,
  isLoading: true,

  login: async (data) => {
    const res = await authApi.login(data);
    localStorage.setItem('access_token', res.token);
    localStorage.setItem('refresh_token', res.refresh_token);
    set({
      user: {
        id: res.id,
        username: res.username,
        email: res.email,
        full_name: res.full_name,
        is_active: res.is_active,
        is_admin: res.is_admin,
      },
      accessToken: res.token,
      refreshToken: res.refresh_token,
      isAuthenticated: true,
    });
  },

  register: async (data) => {
    await authApi.register(data);
    const res = await authApi.login({
      username: data.username,
      password: data.password,
    });
    localStorage.setItem('access_token', res.token);
    localStorage.setItem('refresh_token', res.refresh_token);
    set({
      user: {
        id: res.id,
        username: res.username,
        email: res.email,
        full_name: res.full_name,
        is_active: res.is_active,
        is_admin: res.is_admin,
      },
      accessToken: res.token,
      refreshToken: res.refresh_token,
      isAuthenticated: true,
    });
  },

  logout: () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    set({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
    });
  },

  loadUser: async () => {
    try {
      const user = await authApi.getMe();
      set({ user, isAuthenticated: true });
    } catch {
      const { refreshToken } = get();
      if (refreshToken) {
        try {
          const res = await authApi.refresh({ refresh_token: refreshToken });
          localStorage.setItem('access_token', res.access_token);
          localStorage.setItem('refresh_token', res.refresh_token);
          set({ accessToken: res.access_token, refreshToken: res.refresh_token });
          const user = await authApi.getMe();
          set({ user, isAuthenticated: true });
        } catch {
          get().logout();
        }
      } else {
        get().logout();
      }
    } finally {
      set({ isLoading: false });
    }
  },

  setAccessToken: (token) => {
    localStorage.setItem('access_token', token);
    set({ accessToken: token });
  },

  initialize: async () => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      set({ isLoading: false });
      return;
    }
    await get().loadUser();
  },
}));
