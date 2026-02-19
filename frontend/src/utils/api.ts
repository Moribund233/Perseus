// API基础配置 - 从环境变量读取
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

// 导入安全存储
import {
  getToken,
  setToken,
  setUser,
  getUser,
  clearAll,
  StorageOptions
} from './secureStorage';

// 通用请求配置
interface RequestOptions {
  method?: string;
  headers?: Record<string, string>;
  body?: any;
  requireAuth?: boolean;
}

// 响应类型
interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
}

// 登录响应类型
interface LoginResponse {
  id: number;
  username: string;
  email: string;
  full_name?: string;
  is_active: boolean;
  is_admin: boolean;
  token?: string;
  expires_in?: number;
}

/**
 * 通用API请求函数
 *
 * 安全特性：
 * - 自动从安全存储获取 Token
 * - 支持请求超时
 * - 自动处理 401 未授权错误
 */
export const apiRequest = async <T>(
  endpoint: string,
  options: RequestOptions = {}
): Promise<ApiResponse<T>> => {
  const {
    method = 'GET',
    headers = {},
    body,
    requireAuth = false
  } = options;

  // 构建请求配置
  const config: RequestInit = {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...headers
    },
    // 添加超时信号
    signal: AbortSignal.timeout(30000) // 30秒超时
  };

  // 添加认证令牌（如果需要）
  if (requireAuth) {
    const token = getToken();
    if (token) {
      config.headers = {
        ...config.headers,
        'Authorization': `Bearer ${token}`
      };
    }
  }

  // 添加请求体（如果有）
  if (body) {
    config.body = JSON.stringify(body);
  }

  try {
    // 发送请求
    const response = await fetch(`${API_BASE_URL}${endpoint}`, config);
    const data = await response.json();

    if (response.ok) {
      return {
        success: true,
        data
      };
    } else {
      // 处理 401 未授权错误
      if (response.status === 401) {
        // Token 可能已过期，清除存储
        clearAll();
        // 可以在这里触发全局登出事件
        window.dispatchEvent(new CustomEvent('auth:logout', {
          detail: { reason: 'token_expired' }
        }));
      }

      return {
        success: false,
        error: data.detail || data.error || '请求失败'
      };
    }
  } catch (error) {
    console.error('API请求错误:', error);

    // 处理超时错误
    if (error instanceof DOMException && error.name === 'AbortError') {
      return {
        success: false,
        error: '请求超时，请稍后重试'
      };
    }

    return {
      success: false,
      error: error instanceof Error ? error.message : '网络错误'
    };
  }
};

// 用户相关API
export const userApi = {
  /**
   * 用户登录
   *
   * @param credentials 登录凭证
   * @param rememberMe 是否记住登录状态
   */
  login: async (
    credentials: { username: string; password: string },
    rememberMe: boolean = false
  ) => {
    const response = await apiRequest<LoginResponse>('/api/users/login', {
      method: 'POST',
      body: credentials
    });

    if (response.success && response.data) {
      // 保存用户信息（过滤敏感字段）
      setUser(response.data);

      // 保存 Token 到安全存储
      if (response.data.token) {
        const storageOptions: StorageOptions = {
          rememberMe,
          expiresIn: response.data.expires_in || 30 * 60 * 1000 // 默认30分钟
        };
        setToken(response.data.token, storageOptions);
      }
    }

    return response;
  },

  // 注册
  register: async (userData: { username: string; email: string; password: string }) => {
    return apiRequest<{
      id: number;
      username: string;
      email: string;
      full_name?: string;
      is_active: boolean;
      is_admin: boolean;
    }>('/api/users', {
      method: 'POST',
      body: userData
    });
  },

  // 获取当前用户信息
  getCurrentUser: async () => {
    // 首先尝试从安全存储获取
    const user = getUser();
    if (user) {
      return user;
    }

    // 如果没有，尝试从 API 获取
    const response = await apiRequest<LoginResponse>('/api/users/me', {
      method: 'GET',
      requireAuth: true
    });

    if (response.success && response.data) {
      setUser(response.data);
      return response.data;
    }

    return null;
  },

  // 更新当前用户信息
  updateCurrentUser: async (userData: Partial<LoginResponse>) => {
    const response = await apiRequest<LoginResponse>('/api/users/me', {
      method: 'PUT',
      body: userData,
      requireAuth: true
    });

    if (response.success && response.data) {
      setUser(response.data);
    }

    return response;
  },

  // 登出
  logout: () => {
    // 清除所有存储
    clearAll();
  },

  // 保存用户信息到本地存储（已废弃，使用 setUser 替代）
  saveUserToLocalStorage: (user: any) => {
    setUser(user);
  },

  // 获取存储的 Token（用于调试）
  getStoredToken: () => {
    return getToken();
  },

  // 检查是否已登录
  isLoggedIn: () => {
    return getToken() !== null;
  }
};

// 仓库相关API
export const repositoryApi = {
  // 获取仓库列表
  getRepositories: async () => {
    return apiRequest<any[]>('/api/repositories', {
      method: 'GET',
      requireAuth: true
    });
  },

  // 获取单个仓库
  getRepository: async (repoId: number) => {
    return apiRequest<any>(`/api/repositories/${repoId}`, {
      method: 'GET',
      requireAuth: true
    });
  },

  // 创建仓库
  createRepository: async (repoData: {
    name: string;
    path: string;
    owner_id: number;
    description?: string;
    is_public?: boolean;
    default_branch?: string;
  }) => {
    return apiRequest<any>('/api/repositories', {
      method: 'POST',
      body: repoData,
      requireAuth: true
    });
  },

  // 更新仓库
  updateRepository: async (repoId: number, repoData: {
    name?: string;
    description?: string;
    is_public?: boolean;
    default_branch?: string;
  }) => {
    return apiRequest<any>(`/api/repositories/${repoId}`, {
      method: 'PUT',
      body: repoData,
      requireAuth: true
    });
  },

  // 删除仓库
  deleteRepository: async (repoId: number) => {
    return apiRequest<void>(`/api/repositories/${repoId}`, {
      method: 'DELETE',
      requireAuth: true
    });
  }
};

// 导出安全存储相关函数
export {
  getToken,
  setToken,
  setUser,
  getUser,
  clearAll
};

// 默认导出
export default {
  apiRequest,
  userApi,
  repositoryApi
};
