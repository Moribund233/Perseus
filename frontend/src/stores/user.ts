import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { userApi } from '@/utils/api';
import {
  getToken,
  getUser,
  clearAll as clearSecureStorage,
  isTokenExpiringSoon,
  initSecureStorage
} from '@/utils/secureStorage';

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
  const isLoggedIn = computed(() => !!userState.value.user && getToken() !== null);
  const isAdmin = computed(() => userState.value.user?.is_admin || false);
  const currentUser = computed(() => userState.value.user);

  /**
   * 用户登录
   *
   * @param credentials 登录凭证
   * @param rememberMe 是否记住登录状态
   */
  const login = async (
    credentials: { username: string; password: string },
    rememberMe: boolean = false
  ) => {
    userState.value.isLoading = true;
    userState.value.error = null;

    try {
      const response = await userApi.login(credentials, rememberMe);

      if (response.success && response.data) {
        userState.value.user = response.data;
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
    // 清除安全存储
    clearSecureStorage();
  };

  /**
   * 获取当前用户信息
   * 优先从安全存储获取，如果没有则尝试从 API 获取
   */
  const fetchCurrentUser = async () => {
    userState.value.isLoading = true;
    userState.value.error = null;

    try {
      // 首先尝试从安全存储获取
      const storedUser = getUser();
      if (storedUser) {
        userState.value.user = storedUser;
      }

      // 然后尝试从 API 获取最新信息（如果已登录）
      if (getToken()) {
        const user = await userApi.getCurrentUser();
        if (user) {
          userState.value.user = user;
        } else {
          // API 返回空，可能是 Token 无效
          logout();
        }
      }
    } catch (error: any) {
      userState.value.error = error.message;
      console.error('获取用户信息失败:', error);

      // 如果是 401 错误，清除登录状态
      if (error.message?.includes('401') || error.message?.includes('未授权')) {
        logout();
      }
    } finally {
      userState.value.isLoading = false;
    }
  };

  /**
   * 从安全存储恢复用户状态
   * 在应用启动时调用
   */
  const restoreUserFromStorage = () => {
    // 初始化安全存储（恢复 rememberMe 的 Token）
    initSecureStorage();

    // 从安全存储获取用户信息
    const user = getUser();
    if (user && getToken()) {
      userState.value.user = user;
      console.log('用户状态已恢复:', user.username);
    }
  };

  /**
   * 检查 Token 是否即将过期
   * 如果即将过期，可以触发刷新 Token 的逻辑
   */
  const checkTokenExpiry = () => {
    if (isTokenExpiringSoon(5)) { // 5分钟阈值
      console.warn('Token 即将过期，建议刷新');
      // 可以在这里触发 Token 刷新逻辑
      // 或者提示用户重新登录
      return true;
    }
    return false;
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
    restoreUserFromStorage,
    checkTokenExpiry
  };
}, {
  // 注意：不再使用 pinia-plugin-persistedstate 持久化 Token
  // Token 存储在内存中，用户信息存储在 localStorage（通过 secureStorage）
  // 如果确实需要 pinia 持久化，只持久化非敏感数据
  persist: false // 禁用 pinia 持久化，使用自定义安全存储
});
