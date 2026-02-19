/**
 * 安全存储模块
 *
 * 提供安全的 Token 和用户数据存储方案：
 * 1. Token 存储在内存中（避免 XSS 攻击窃取）
 * 2. 用户基本信息使用 localStorage（方便快速恢复UI状态）
 * 3. 支持 httpOnly Cookie 作为备选方案（需要后端配合）
 * 4. 添加 Token 过期自动清理机制
 */

// Token 内存存储
let memoryToken: string | null = null;
let tokenExpiryTime: number | null = null;

// 存储键名
const STORAGE_KEYS = {
  USER: 'user',
  TOKEN: 'token',
  TOKEN_EXPIRY: 'token_expiry',
  REMEMBER_ME: 'remember_me'
} as const;

/**
 * 存储配置选项
 */
export interface StorageOptions {
  /** 是否记住登录状态 */
  rememberMe?: boolean;
  /** Token 过期时间（毫秒） */
  expiresIn?: number;
}

/**
 * 存储 Token 到内存
 *
 * 安全说明：
 * - Token 仅保存在内存中，页面刷新后会丢失
 * - 配合 rememberMe 选项，可以选择是否持久化到 localStorage
 *
 * @param token JWT Token
 * @param options 存储选项
 */
export function setToken(token: string, options: StorageOptions = {}): void {
  const { rememberMe = false, expiresIn = 30 * 60 * 1000 } = options; // 默认30分钟

  // 始终存储在内存中
  memoryToken = token;
  tokenExpiryTime = Date.now() + expiresIn;

  // 如果选择了记住我，同时存储到 localStorage（有一定风险，但方便使用）
  if (rememberMe) {
    try {
      localStorage.setItem(STORAGE_KEYS.TOKEN, token);
      localStorage.setItem(STORAGE_KEYS.TOKEN_EXPIRY, tokenExpiryTime.toString());
      localStorage.setItem(STORAGE_KEYS.REMEMBER_ME, 'true');
    } catch (error) {
      console.warn('存储Token到localStorage失败:', error);
    }
  } else {
    // 清除可能存在的旧 Token
    clearPersistentToken();
  }
}

/**
 * 从内存或存储中获取 Token
 *
 * @returns Token 字符串或 null
 */
export function getToken(): string | null {
  // 首先检查内存中的 Token
  if (memoryToken && tokenExpiryTime && Date.now() < tokenExpiryTime) {
    return memoryToken;
  }

  // 内存中没有，尝试从 localStorage 恢复（仅当选择了记住我）
  try {
    const rememberMe = localStorage.getItem(STORAGE_KEYS.REMEMBER_ME) === 'true';
    if (rememberMe) {
      const storedToken = localStorage.getItem(STORAGE_KEYS.TOKEN);
      const storedExpiry = localStorage.getItem(STORAGE_KEYS.TOKEN_EXPIRY);

      if (storedToken && storedExpiry) {
        const expiryTime = parseInt(storedExpiry, 10);
        if (Date.now() < expiryTime) {
          // 恢复到内存
          memoryToken = storedToken;
          tokenExpiryTime = expiryTime;
          return storedToken;
        } else {
          // Token 已过期，清理
          clearToken();
        }
      }
    }
  } catch (error) {
    console.warn('从localStorage读取Token失败:', error);
  }

  return null;
}

/**
 * 清除所有 Token 存储
 */
export function clearToken(): void {
  // 清除内存
  memoryToken = null;
  tokenExpiryTime = null;

  // 清除持久化存储
  clearPersistentToken();
}

/**
 * 清除持久化 Token 存储
 */
function clearPersistentToken(): void {
  try {
    localStorage.removeItem(STORAGE_KEYS.TOKEN);
    localStorage.removeItem(STORAGE_KEYS.TOKEN_EXPIRY);
    localStorage.removeItem(STORAGE_KEYS.REMEMBER_ME);
  } catch (error) {
    console.warn('清除持久化Token失败:', error);
  }
}

/**
 * 检查 Token 是否即将过期
 *
 * @param thresholdMinutes 提前警告的分钟数，默认5分钟
 * @returns 是否即将过期
 */
export function isTokenExpiringSoon(thresholdMinutes: number = 5): boolean {
  if (!tokenExpiryTime) return true;

  const thresholdMs = thresholdMinutes * 60 * 1000;
  return Date.now() + thresholdMs >= tokenExpiryTime;
}

/**
 * 获取 Token 剩余有效时间（毫秒）
 *
 * @returns 剩余毫秒数，如果已过期返回 0
 */
export function getTokenRemainingTime(): number {
  if (!tokenExpiryTime) return 0;

  const remaining = tokenExpiryTime - Date.now();
  return Math.max(0, remaining);
}

/**
 * 存储用户信息（非敏感信息）
 *
 * 存储内容：
 * - 用户ID、用户名、邮箱等基本信息
 * - 不包含 Token、密码等敏感信息
 *
 * @param user 用户对象
 */
export function setUser(user: any): void {
  try {
    // 过滤敏感字段
    const safeUser = filterSensitiveFields(user);
    localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(safeUser));
  } catch (error) {
    console.warn('存储用户信息失败:', error);
  }
}

/**
 * 获取用户信息
 *
 * @returns 用户对象或 null
 */
export function getUser(): any | null {
  try {
    const userStr = localStorage.getItem(STORAGE_KEYS.USER);
    if (userStr) {
      return JSON.parse(userStr);
    }
  } catch (error) {
    console.warn('读取用户信息失败:', error);
  }
  return null;
}

/**
 * 清除用户信息
 */
export function clearUser(): void {
  try {
    localStorage.removeItem(STORAGE_KEYS.USER);
  } catch (error) {
    console.warn('清除用户信息失败:', error);
  }
}

/**
 * 过滤敏感字段
 *
 * @param user 原始用户对象
 * @returns 过滤后的用户对象
 */
function filterSensitiveFields(user: any): any {
  if (!user || typeof user !== 'object') return user;

  const sensitiveFields = ['password', 'token', 'secret', 'credentials', 'api_key'];
  const filtered: any = {};

  for (const [key, value] of Object.entries(user)) {
    // 跳过敏感字段
    if (sensitiveFields.some(field => key.toLowerCase().includes(field))) {
      continue;
    }
    filtered[key] = value;
  }

  return filtered;
}

/**
 * 完全登出清理
 * 清除所有存储的用户相关数据
 */
export function clearAll(): void {
  clearToken();
  clearUser();
}

/**
 * 检查是否已登录
 *
 * @returns 是否已登录
 */
export function isAuthenticated(): boolean {
  return getToken() !== null;
}

/**
 * 初始化安全存储
 * 在应用启动时调用，恢复 rememberMe 的 Token
 */
export function initSecureStorage(): void {
  // 尝试恢复 Token（如果选择了记住我）
  const token = getToken();
  if (token) {
    console.log('安全存储：已恢复登录状态');
  }
}

/**
 * 设置 Cookie（用于后端支持 httpOnly Cookie 时）
 *
 * 注意：前端无法读取 httpOnly Cookie，此函数仅用于设置非 httpOnly 的辅助 Cookie
 *
 * @param name Cookie 名称
 * @param value Cookie 值
 * @param options Cookie 选项
 */
export function setCookie(
  name: string,
  value: string,
  options: {
    expires?: Date;
    maxAge?: number;
    path?: string;
    secure?: boolean;
    sameSite?: 'strict' | 'lax' | 'none';
  } = {}
): void {
  const {
    expires,
    maxAge,
    path = '/',
    secure = true,
    sameSite = 'strict'
  } = options;

  let cookieString = `${encodeURIComponent(name)}=${encodeURIComponent(value)}`;

  if (expires) {
    cookieString += `; expires=${expires.toUTCString()}`;
  }

  if (maxAge !== undefined) {
    cookieString += `; max-age=${maxAge}`;
  }

  cookieString += `; path=${path}`;

  if (secure) {
    cookieString += '; secure';
  }

  cookieString += `; samesite=${sameSite}`;

  document.cookie = cookieString;
}

/**
 * 获取 Cookie 值
 *
 * @param name Cookie 名称
 * @returns Cookie 值或 null
 */
export function getCookie(name: string): string | null {
  const cookies = document.cookie.split(';');
  for (const cookie of cookies) {
    const [cookieName, cookieValue] = cookie.trim().split('=');
    if (decodeURIComponent(cookieName) === name) {
      return decodeURIComponent(cookieValue);
    }
  }
  return null;
}

/**
 * 删除 Cookie
 *
 * @param name Cookie 名称
 * @param path Cookie 路径
 */
export function deleteCookie(name: string, path: string = '/'): void {
  document.cookie = `${encodeURIComponent(name)}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=${path}`;
}

// 默认导出
export default {
  setToken,
  getToken,
  clearToken,
  setUser,
  getUser,
  clearUser,
  clearAll,
  isAuthenticated,
  isTokenExpiringSoon,
  getTokenRemainingTime,
  initSecureStorage,
  setCookie,
  getCookie,
  deleteCookie
};
