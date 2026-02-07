// API基础配置
const API_BASE_URL = 'http://localhost:8000';

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

// 获取认证令牌
const getAuthToken = (): string | null => {
  // 这里可以根据实际情况修改，比如从localStorage或cookie中获取
  return localStorage.getItem('token');
};

// 通用API请求函数
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
    }
  };

  // 添加认证令牌（如果需要）
  if (requireAuth) {
    const token = getAuthToken();
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
      return {
        success: false,
        error: data.detail || '请求失败'
      };
    }
  } catch (error) {
    console.error('API请求错误:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : '网络错误'
    };
  }
};

// 用户相关API
export const userApi = {
  // 登录
  login: async (credentials: { username: string; password: string }) => {
    return apiRequest<{
      id: number;
      username: string;
      email: string;
      full_name?: string;
      is_active: boolean;
      is_admin: boolean;
    }>('/api/users/login', {
      method: 'POST',
      body: credentials
    });
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
    // 这里假设我们从localStorage获取用户信息
    const userStr = localStorage.getItem('user');
    if (userStr) {
      return JSON.parse(userStr);
    }
    return null;
  },

  // 登出
  logout: () => {
    // 清除本地存储的用户信息
    localStorage.removeItem('user');
    localStorage.removeItem('token');
  },

  // 保存用户信息到本地存储
  saveUserToLocalStorage: (user: any) => {
    localStorage.setItem('user', JSON.stringify(user));
    // 如果有令牌，也保存令牌
    if (user.token) {
      localStorage.setItem('token', user.token);
    }
  }
};

// 通用工具函数
export const apiUtils = {
  // 检查用户是否已登录
  isLoggedIn: (): boolean => {
    return localStorage.getItem('user') !== null;
  },

  // 获取用户角色
  getUserRole: (): string => {
    const userStr = localStorage.getItem('user');
    if (userStr) {
      const user = JSON.parse(userStr);
      return user.is_admin ? 'admin' : 'user';
    }
    return 'guest';
  }
};
