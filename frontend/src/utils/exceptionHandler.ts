/**
 * 前端异常处理器
 * 
 * 提供统一的异常处理机制，用于处理API请求错误和应用中的各种异常
 */

export interface ErrorResponse {
  error: {
    code: number;
    message: string;
    type: string;
    details?: Array<{
      field: string;
      message: string;
      type: string;
    }>;
  };
}

export interface ApiError extends Error {
  statusCode?: number;
  errorCode?: number;
  errorType?: string;
  details?: Array<{
    field: string;
    message: string;
    type: string;
  }>;
}

export class ExceptionHandler {
  /**
   * 处理API响应错误
   * @param response - API响应对象
   * @returns ApiError - 标准化的API错误对象
   */
  static handleApiError(response: Response): Promise<ApiError> {
    return response.json()
      .then((data: ErrorResponse) => {
        const error: ApiError = new Error(data.error.message);
        error.statusCode = response.status;
        error.errorCode = data.error.code;
        error.errorType = data.error.type;
        error.details = data.error.details;
        
        return Promise.reject(error);
      })
      .catch(() => {
        // 如果无法解析JSON响应，创建一个基本的错误对象
        const error: ApiError = new Error(`HTTP Error: ${response.status} ${response.statusText}`);
        error.statusCode = response.status;
        error.errorType = 'HttpError';
        
        return Promise.reject(error);
      });
  }

  /**
   * 处理网络错误
   * @param error - 网络错误对象
   * @returns ApiError - 标准化的API错误对象
   */
  static handleNetworkError(error: Error): ApiError {
    const apiError: ApiError = new Error('Network Error');
    apiError.errorType = 'NetworkError';
    apiError.message = error.message || 'Network Error';
    
    return apiError;
  }

  /**
   * 处理超时错误
   * @returns ApiError - 标准化的API错误对象
   */
  static handleTimeoutError(): ApiError {
    const error: ApiError = new Error('Request Timeout');
    error.errorType = 'TimeoutError';
    
    return error;
  }

  /**
   * 显示错误消息
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
    // 这里可以集成UI框架的消息提示组件，例如ElMessage
    // ElMessage.error(`Validation Error: ${error.message}`);
    alert(`Validation Error: ${error.message}`);
  }

  /**
   * 显示认证错误
   * @param error - API错误对象
   */
  private static showAuthenticationError(error: ApiError): void {
    console.error('Authentication Error:', error);
    // 这里可以跳转到登录页面
    // router.push('/login');
    alert(`Authentication Error: ${error.message}`);
  }

  /**
   * 显示授权错误
   * @param error - API错误对象
   */
  private static showAuthorizationError(error: ApiError): void {
    console.error('Authorization Error:', error);
    // 这里可以跳转到无权限页面
    // router.push('/403');
    alert(`Authorization Error: ${error.message}`);
  }

  /**
   * 显示资源不存在错误
   * @param error - API错误对象
   */
  private static showNotFoundError(error: ApiError): void {
    console.error('Not Found Error:', error);
    // 这里可以跳转到404页面
    // router.push('/404');
    alert(`Not Found Error: ${error.message}`);
  }

  /**
   * 显示资源冲突错误
   * @param error - API错误对象
   */
  private static showConflictError(error: ApiError): void {
    console.error('Conflict Error:', error);
    // ElMessage.error(`Conflict Error: ${error.message}`);
    alert(`Conflict Error: ${error.message}`);
  }

  /**
   * 显示网络错误
   * @param error - API错误对象
   */
  private static showNetworkErrorMsg(error: ApiError): void {
    console.error('Network Error:', error);
    // ElMessage.error('Network Error: Please check your network connection');
    alert('Network Error: Please check your network connection');
  }

  /**
   * 显示超时错误
   * @param error - API错误对象
   */
  private static showTimeoutErrorMsg(error: ApiError): void {
    console.error('Timeout Error:', error);
    // ElMessage.error('Request Timeout: Please try again later');
    alert('Request Timeout: Please try again later');
  }

  /**
   * 显示通用错误
   * @param error - API错误对象
   */
  private static showGenericError(error: ApiError): void {
    console.error('Generic Error:', error);
    // ElMessage.error(`Error: ${error.message}`);
    alert(`Error: ${error.message}`);
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
    
    this.showErrorMessage(apiError);
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
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers
      },
      ...options
    });

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
    
    throw error;
  }
}
