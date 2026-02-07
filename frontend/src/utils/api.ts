// API基础配置
export const API_BASE_URL = 'http://192.168.31.248:8080';

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

// 分支相关API
export const branchApi = {
  // 获取仓库分支列表
  getBranches: async (repoId: number) => {
    return apiRequest<any[]>(`/api/repositories/${repoId}/branches`, {
      method: 'GET',
      requireAuth: true
    });
  },

  // 获取单个分支
  getBranch: async (repoId: number, branchName: string) => {
    return apiRequest<any>(`/api/repositories/${repoId}/branches/${branchName}`, {
      method: 'GET',
      requireAuth: true
    });
  },

  // 创建分支
  createBranch: async (repoId: number, branchData: {
    name: string;
    from_branch?: string;
    from_commit?: string;
  }) => {
    return apiRequest<any>(`/api/repositories/${repoId}/branches`, {
      method: 'POST',
      body: branchData,
      requireAuth: true
    });
  },

  // 删除分支
  deleteBranch: async (repoId: number, branchName: string) => {
    return apiRequest<void>(`/api/repositories/${repoId}/branches/${branchName}`, {
      method: 'DELETE',
      requireAuth: true
    });
  },

  // 设置默认分支
  setDefaultBranch: async (repoId: number, branchName: string) => {
    return apiRequest<any>(`/api/repositories/${repoId}/branches/${branchName}/default`, {
      method: 'PUT',
      requireAuth: true
    });
  }
};

// 提交相关API
export const commitApi = {
  // 获取仓库提交历史
  getCommits: async (repoId: number, params?: {
    branch?: string;
    author?: string;
    since?: string;
    until?: string;
    limit?: number;
    offset?: number;
  }) => {
    let url = `/api/repositories/${repoId}/commits`;
    if (params) {
      // 转换所有参数值为字符串
      const stringParams = Object.entries(params).reduce((acc, [key, value]) => {
        acc[key] = String(value);
        return acc;
      }, {} as Record<string, string>);
      const queryString = new URLSearchParams(stringParams).toString();
      if (queryString) {
        url += `?${queryString}`;
      }
    }
    return apiRequest<any[]>(url, {
      method: 'GET',
      requireAuth: true
    });
  },

  // 获取单个提交
  getCommit: async (repoId: number, commitHash: string) => {
    return apiRequest<any>(`/api/repositories/${repoId}/commits/${commitHash}`, {
      method: 'GET',
      requireAuth: true
    });
  },

  // 获取分支提交历史
  getCommitsByBranch: async (repoId: number, branchName: string, params?: {
    since?: string;
    until?: string;
    limit?: number;
    offset?: number;
  }) => {
    let url = `/api/repositories/${repoId}/branches/${branchName}/commits`;
    if (params) {
      // 转换所有参数值为字符串
      const stringParams = Object.entries(params).reduce((acc, [key, value]) => {
        acc[key] = String(value);
        return acc;
      }, {} as Record<string, string>);
      const queryString = new URLSearchParams(stringParams).toString();
      if (queryString) {
        url += `?${queryString}`;
      }
    }
    return apiRequest<any[]>(url, {
      method: 'GET',
      requireAuth: true
    });
  },

  // 获取最新提交
  getLatestCommit: async (repoId: number, branchName?: string) => {
    let url = `/api/repositories/${repoId}/commits/latest`;
    if (branchName) {
      url += `?branch=${branchName}`;
    }
    return apiRequest<any>(url, {
      method: 'GET',
      requireAuth: true
    });
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
