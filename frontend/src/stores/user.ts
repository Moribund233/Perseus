import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { userApi } from '@/utils/api';

// 用户类型定义
interface User {
  id: number;
  username: string;
  email: string;
  full_name?: string;
  is_active: boolean;
  is_admin: boolean;
}

// 用户状态定义
interface UserState {
  user: User | null;
  isLoading: boolean;
  error: string | null;
}

export const useUserStore = defineStore('user', () => {
  // 状态
  const userState = ref<UserState>({
    user: null,
    isLoading: false,
    error: null
  });

  // 计算属性
  const isLoggedIn = computed(() => !!userState.value.user);
  const isAdmin = computed(() => userState.value.user?.is_admin || false);
  const currentUser = computed(() => userState.value.user);

  // 登录
  const login = async (credentials: { username: string; password: string }) => {
    userState.value.isLoading = true;
    userState.value.error = null;

    try {
      const response = await userApi.login(credentials);
      
      if (response.success && response.data) {
        userState.value.user = response.data;
        // 同时保存到localStorage，以便在刷新页面时恢复状态
        userApi.saveUserToLocalStorage(response.data);
        return true;
      } else {
        throw new Error(response.error || '登录失败');
      }
    } catch (error: any) {
      userState.value.error = error.message;
      console.error('登录失败:', error);
      return false;
    } finally {
      userState.value.isLoading = false;
    }
  };

  // 注册
  const register = async (userData: { username: string; email: string; password: string }) => {
    userState.value.isLoading = true;
    userState.value.error = null;

    try {
      const response = await userApi.register(userData);
      
      if (response.success) {
        return true;
      } else {
        throw new Error(response.error || '注册失败');
      }
    } catch (error: any) {
      userState.value.error = error.message;
      console.error('注册失败:', error);
      return false;
    } finally {
      userState.value.isLoading = false;
    }
  };

  // 登出
  const logout = () => {
    userState.value.user = null;
    userApi.logout();
  };

  // 获取当前用户信息
  const fetchCurrentUser = async () => {
    userState.value.isLoading = true;
    userState.value.error = null;

    try {
      const user = await userApi.getCurrentUser();
      if (user) {
        userState.value.user = user;
      }
    } catch (error: any) {
      userState.value.error = error.message;
      console.error('获取用户信息失败:', error);
    } finally {
      userState.value.isLoading = false;
    }
  };

  // 从本地存储恢复用户状态
  const restoreUserFromLocalStorage = () => {
    // 直接从localStorage读取用户信息，避免异步操作
    const userStr = localStorage.getItem('user');
    if (userStr) {
      try {
        const user = JSON.parse(userStr);
        userState.value.user = user;
      } catch (error) {
        console.error('解析用户信息失败:', error);
        // 清除无效的用户信息
        localStorage.removeItem('user');
      }
    }
  };

  return {
    // 状态
    user: userState,
    
    // 计算属性
    isLoggedIn,
    isAdmin,
    currentUser,
    
    // 方法
    login,
    register,
    logout,
    fetchCurrentUser,
    restoreUserFromLocalStorage
  };
}, {
  // 持久化配置
  persist: {
    key: 'user-state',
    storage: localStorage
  }
});
