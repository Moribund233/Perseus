/**
 * 前端异常处理器
 * 
 * 提供统一的异常处理机制，用于处理API请求错误和应用中的各种异常
 * 支持跳转到错误页面显示详细错误信息
 */

import { useRouter } from 'vue-router';

export interface ErrorResponse {
  error: {
    code: number;
    message: string;
    type: string;
    details?: string;
    traceback?: string;
    timestamp?: string;
    request_id?: string;
  };
}

export interface ApiError extends Error {
  statusCode?: number;
  errorCode?: number;
  errorType?: string;
  details?: string;
  traceback?: string;
  requestId?: string;
  timestamp?: string;
}

export interface ErrorReportData {
  code: number;
  type: string;
  message: string;
  details?: string | null;
  traceback?: string | null;
  path: string;
  timestamp: string;
}

export class ExceptionHandler {
  private static router: ReturnType<typeof useRouter> | null = null;

  /**
   * 初始化异常处理器
   * @param router - Vue Router 实例
   */
  static init(router: ReturnType<typeof useRouter>) {
    this.router = router;
  }

  /**
   * 处理API响应错误
   * @param response - API响应对象
   * @returns ApiError - 标准化的API错误对象
   */
  static async handleApiError(response: Response): Promise<ApiError> {
    try {
      const data: ErrorResponse = await response.json();
      const error: ApiError = new Error(data.error.message);
      error.statusCode = response.status;
      error.errorCode = data.error.code;
      error.errorType = data.error.type;
      error.details = data.error.details;
      error.traceback = data.error.traceback;
      error.requestId = data.error.request_id;
      error.timestamp = data.error.timestamp;
      
      // 自动跳转到错误页面
      this.navigateToErrorPage(error);
      
      return Promise.reject(error);
    } catch (parseError) {
      // 如果无法解析JSON响应，创建一个基本的错误对象
      const error: ApiError = new Error(`HTTP Error: ${response.status} ${response.statusText}`);
      error.statusCode = response.status;
      error.errorType = 'HttpError';
      
      // 跳转到错误页面
      this.navigateToErrorPage(error);
      
      return Promise.reject(error);
    }
  }

  /**
   * 处理网络错误
   * @param error - 网络错误对象
   * @returns ApiError - 标准化的API错误对象
   */
  static handleNetworkError(error: Error): ApiError {
    const apiError: ApiError = new Error('网络连接失败，请检查网络设置');
    apiError.errorType = 'NetworkError';
    apiError.statusCode = 0;
    apiError.message = error.message || '网络连接失败';
    
    // 跳转到错误页面
    this.navigateToErrorPage(apiError);
    
    return apiError;
  }

  /**
   * 处理超时错误
   * @returns ApiError - 标准化的API错误对象
   */
  static handleTimeoutError(): ApiError {
    const error: ApiError = new Error('请求超时，请稍后重试');
    error.errorType = 'TimeoutError';
    error.statusCode = 408;
    
    // 跳转到错误页面
    this.navigateToErrorPage(error);
    
    return error;
  }

  /**
   * 跳转到错误页面
   * @param error - API错误对象
   */
  static navigateToErrorPage(error: ApiError): void {
    if (!this.router) {
      console.warn('ExceptionHandler not initialized with router');
      return;
    }

    const errorParams = {
      code: error.statusCode?.toString() || '500',
      message: error.message,
      type: error.errorType || 'UnknownError',
      details: error.details || '',
      request_id: error.requestId || ''
    };

    // 使用 replace 避免错误页面被加入历史记录
    this.router.replace({
      name: 'Error',
      params: errorParams
    });
  }

  /**
   * 显示错误消息（非跳转方式）
   * @param error - API错误对象
   */
  static showErrorMessage(error: ApiError): void {
    // 根据错误类型显示不同的错误消息
    switch (error.errorType) {
      case 'ValidationException':
        this.showValidationError(error);
        break;
      case 'AuthenticationException':
        this.showAuthenticationError(error);
        break;
      case 'AuthorizationException':
        this.showAuthorizationError(error);
        break;
      case 'NotFoundException':
        this.showNotFoundError(error);
        break;
      case 'ConflictException':
        this.showConflictError(error);
        break;
      case 'NetworkError':
        this.showNetworkErrorMsg(error);
        break;
      case 'TimeoutError':
        this.showTimeoutErrorMsg(error);
        break;
      default:
        this.showGenericError(error);
        break;
    }
  }

  /**
   * 显示验证错误
   * @param error - API错误对象
   */
  private static showValidationError(error: ApiError): void {
    console.error('Validation Error:', error);
    // 这里可以集成UI框架的消息提示组件
    this.showNotification('error', `验证错误: ${error.message}`);
  }

  /**
   * 显示认证错误
   * @param error - API错误对象
   */
  private static showAuthenticationError(error: ApiError): void {
    console.error('Authentication Error:', error);
    // 可以跳转到登录页面
    if (this.router) {
      this.router.push('/login');
    }
  }

  /**
   * 显示授权错误
   * @param error - API错误对象
   */
  private static showAuthorizationError(error: ApiError): void {
    console.error('Authorization Error:', error);
    // 跳转到403错误页面
    this.navigateToErrorPage(error);
  }

  /**
   * 显示资源不存在错误
   * @param error - API错误对象
   */
  private static showNotFoundError(error: ApiError): void {
    console.error('Not Found Error:', error);
    // 跳转到404错误页面
    this.navigateToErrorPage(error);
  }

  /**
   * 显示资源冲突错误
   * @param error - API错误对象
   */
  private static showConflictError(error: ApiError): void {
    console.error('Conflict Error:', error);
    this.showNotification('warning', `冲突错误: ${error.message}`);
  }

  /**
   * 显示网络错误
   * @param error - API错误对象
   */
  private static showNetworkErrorMsg(error: ApiError): void {
    console.error('Network Error:', error);
    this.showNotification('error', '网络连接失败，请检查网络设置');
  }

  /**
   * 显示超时错误
   * @param error - API错误对象
   */
  private static showTimeoutErrorMsg(error: ApiError): void {
    console.error('Timeout Error:', error);
    this.showNotification('warning', '请求超时，请稍后重试');
  }

  /**
   * 显示通用错误
   * @param error - API错误对象
   */
  private static showGenericError(error: ApiError): void {
    console.error('Generic Error:', error);
    this.showNotification('error', `错误: ${error.message}`);
  }

  /**
   * 显示通知（可替换为UI框架的通知组件）
   * @param type - 通知类型
   * @param message - 通知消息
   */
  private static showNotification(type: 'error' | 'warning' | 'info', message: string): void {
    // TODO: 替换为实际的通知组件，例如 Element Plus 的 ElMessage
    console.log(`[${type.toUpperCase()}] ${message}`);
    // 临时使用 alert
    if (type === 'error') {
      alert(message);
    }
  }

  /**
   * 全局异常捕获
   * @param error - 异常对象
   */
  static globalErrorHandler(error: any): void {
    console.error('Global Error:', error);
    
    let apiError: ApiError;
    
    if (error instanceof Error) {
      apiError = error as ApiError;
    } else {
      apiError = new Error(JSON.stringify(error));
      apiError.errorType = 'UnknownError';
    }
    
    // 跳转到错误页面
    this.navigateToErrorPage(apiError);
  }

  /**
   * 报告错误到服务端
   * @param errorData - 错误数据
   * @returns Promise<boolean> - 是否报告成功
   */
  static async reportError(errorData: ErrorReportData): Promise<boolean> {
    try {
      const response = await fetch('/api/errors/report', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(errorData)
      });
      
      return response.ok;
    } catch (error) {
      console.error('Failed to report error:', error);
      return false;
    }
  }
}

/**
 * API请求封装，自动处理异常
 * @param url - 请求URL
 * @param options - 请求选项
 * @returns Promise<T> - 请求结果
 */
export async function fetchApi<T>(url: string, options: RequestInit = {}): Promise<T> {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000); // 30秒超时

    const response = await fetch(url, {
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers
      },
      ...options
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      await ExceptionHandler.handleApiError(response);
    }

    return await response.json();
  } catch (error) {
    if (error instanceof TypeError && (error as TypeError).message === 'Failed to fetch') {
      // 网络错误
      const networkError = ExceptionHandler.handleNetworkError(error as Error);
      throw networkError;
    }
    
    if (error instanceof DOMException && error.name === 'AbortError') {
      // 超时错误
      const timeoutError = ExceptionHandler.handleTimeoutError();
      throw timeoutError;
    }
    
    throw error;
  }
}

/**
 * 创建API请求钩子（用于Vue组件）
 * @returns Object - API请求方法
 */
export function useApi() {
  return {
    get: <T>(url: string) => fetchApi<T>(url, { method: 'GET' }),
    post: <T>(url: string, data?: any) => fetchApi<T>(url, { 
      method: 'POST', 
      body: data ? JSON.stringify(data) : undefined 
    }),
    put: <T>(url: string, data?: any) => fetchApi<T>(url, { 
      method: 'PUT', 
      body: data ? JSON.stringify(data) : undefined 
    }),
    delete: <T>(url: string) => fetchApi<T>(url, { method: 'DELETE' })
  };
}
