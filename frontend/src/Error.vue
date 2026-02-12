<template>
  <div class="error-container">
    <div class="error-content">
      <div class="error-icon">{{ errorIcon }}</div>
      <h1 class="error-code">{{ errorCode }}</h1>
      <h2 class="error-title">{{ errorTitle }}</h2>
      <p class="error-message">{{ errorMessage }}</p>
      
      <!-- 显示详细信息（调试模式或认证用户） -->
      <div v-if="errorDetails || errorTraceback" class="error-details">
        <h3>错误详情</h3>
        <div v-if="errorDetails" class="detail-section">
          <h4>详细信息</h4>
          <pre>{{ errorDetails }}</pre>
        </div>
        <div v-if="errorTraceback" class="detail-section">
          <h4>堆栈跟踪</h4>
          <pre>{{ errorTraceback }}</pre>
        </div>
        <div v-if="requestId" class="detail-section">
          <h4>请求ID</h4>
          <p class="request-id">{{ requestId }}</p>
        </div>
      </div>
      
      <div class="error-actions">
        <button @click="goHome" class="btn btn-primary">
          返回首页
        </button>
        <button @click="goBack" class="btn btn-secondary">
          返回上一页
        </button>
        <button @click="reloadPage" class="btn btn-secondary">
          刷新页面
        </button>
        <button v-if="canReport" @click="reportError" class="btn btn-warning">
          报告错误
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';

const route = useRoute();
const router = useRouter();

// 错误状态
const errorCode = ref<number>(404);
const errorTitle = ref<string>('页面未找到');
const errorMessage = ref<string>('抱歉，您访问的页面不存在或已被删除');
const errorDetails = ref<string | null>(null);
const errorTraceback = ref<string | null>(null);
const errorType = ref<string>('NotFoundError');
const requestId = ref<string | null>(null);
const errorPath = ref<string | null>(null);
const canReport = ref<boolean>(false);

// 计算错误图标
const errorIcon = computed(() => {
  switch (errorCode.value) {
    case 400:
      return '❌';
    case 401:
      return '🔒';
    case 403:
      return '🚫';
    case 404:
      return '🔍';
    case 408:
      return '⏱️';
    case 409:
      return '⚔️';
    case 500:
      return '💥';
    case 502:
      return '🔄';
    case 503:
      return '⚠️';
    case 504:
      return '⏳';
    default:
      return '❓';
  }
});

// 从后端获取错误信息
const fetchErrorInfo = async (code: number, message?: string, type?: string, details?: string, reqId?: string) => {
  try {
    const params = new URLSearchParams();
    if (message) params.append('message', message);
    if (type) params.append('error_type', type);
    if (details) params.append('details', details);
    if (reqId) params.append('request_id', reqId);
    
    const response = await fetch(`/api/errors/info/${code}?${params.toString()}`);
    
    if (response.ok) {
      const data = await response.json();
      errorCode.value = data.code || code;
      errorMessage.value = data.message || message || getDefaultMessage(code);
      errorType.value = data.type || type || 'UnknownError';
      errorDetails.value = data.details || null;
      errorTraceback.value = data.traceback || null;
      requestId.value = data.request_id || reqId || null;
      errorPath.value = data.path || null;
      
      // 如果有详细信息或堆栈跟踪，允许报告错误
      canReport.value = !!(data.details || data.traceback);
    } else {
      // 使用默认错误信息
      setDefaultErrorInfo(code, message);
    }
  } catch (error) {
    console.error('Failed to fetch error info:', error);
    setDefaultErrorInfo(code, message);
  }
  
  // 设置错误标题
  setErrorTitle();
};

// 设置默认错误信息
const setDefaultErrorInfo = (code: number, message?: string) => {
  errorCode.value = code;
  errorMessage.value = message || getDefaultMessage(code);
  canReport.value = false;
};

// 获取默认错误消息
const getDefaultMessage = (code: number): string => {
  const messages: Record<number, string> = {
    400: '您的请求无效，请检查后重试',
    401: '您需要登录才能访问此页面',
    403: '您没有权限访问此页面',
    404: '抱歉，您访问的页面不存在或已被删除',
    408: '服务器响应超时，请稍后重试',
    409: '请求的资源存在冲突，请检查后重试',
    500: '服务器内部错误，请稍后重试',
    502: '网关错误，请稍后重试',
    503: '服务暂时不可用，请稍后重试',
    504: '网关超时，请稍后重试'
  };
  return messages[code] || '发生了未知错误，请稍后重试';
};

// 设置错误标题
const setErrorTitle = () => {
  const titles: Record<number, string> = {
    400: '请求错误',
    401: '未授权',
    403: '禁止访问',
    404: '页面未找到',
    408: '请求超时',
    409: '资源冲突',
    500: '服务器错误',
    502: '网关错误',
    503: '服务不可用',
    504: '网关超时'
  };
  errorTitle.value = titles[errorCode.value] || '未知错误';
};

// 从路由参数中加载错误信息
const loadErrorInfo = () => {
  const code = parseInt(route.params.code as string, 10) || 404;
  const message = route.params.message as string;
  const details = route.params.details as string;
  const type = route.params.type as string;
  const reqId = route.params.request_id as string;
  
  // 获取错误信息（优先从后端获取）
  fetchErrorInfo(code, message, type, details, reqId);
};

// 报告错误
const reportError = async () => {
  try {
    const errorData = {
      code: errorCode.value,
      type: errorType.value,
      message: errorMessage.value,
      details: errorDetails.value,
      traceback: errorTraceback.value,
      path: errorPath.value || window.location.href,
      timestamp: new Date().toISOString()
    };
    
    const response = await fetch('/api/errors/report', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(errorData)
    });
    
    if (response.ok) {
      alert('错误已报告，感谢您的反馈！');
      canReport.value = false;
    } else {
      alert('报告错误失败，请稍后重试。');
    }
  } catch (error) {
    console.error('Failed to report error:', error);
    alert('报告错误失败，请检查网络连接。');
  }
};

// 返回首页
const goHome = () => {
  router.push('/');
};

// 返回上一页
const goBack = () => {
  if (window.history.length > 1) {
    window.history.back();
  } else {
    router.push('/');
  }
};

// 刷新页面
const reloadPage = () => {
  window.location.reload();
};

// 监听路由变化，重新加载错误信息
onMounted(() => {
  loadErrorInfo();
});
</script>

<style scoped>
.error-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background-color: #f5f7fa;
  padding: 20px;
  font-family: 'Arial', sans-serif;
}

.error-content {
  text-align: center;
  background-color: white;
  padding: 40px;
  border-radius: 12px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  max-width: 800px;
  width: 100%;
}

.error-icon {
  font-size: 80px;
  margin-bottom: 20px;
  opacity: 0.8;
}

.error-code {
  font-size: 120px;
  font-weight: bold;
  margin: 0;
  color: #333;
  line-height: 1;
}

.error-title {
  font-size: 32px;
  font-weight: 600;
  margin: 10px 0;
  color: #555;
}

.error-message {
  font-size: 18px;
  color: #777;
  margin: 20px 0 30px;
  line-height: 1.5;
}

.error-actions {
  display: flex;
  gap: 15px;
  justify-content: center;
  margin: 30px 0;
  flex-wrap: wrap;
}

.btn {
  padding: 12px 24px;
  font-size: 16px;
  font-weight: 500;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.3s ease;
  text-decoration: none;
  display: inline-block;
}

.btn-primary {
  background-color: #409eff;
  color: white;
}

.btn-primary:hover {
  background-color: #66b1ff;
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(64, 158, 255, 0.3);
}

.btn-secondary {
  background-color: #909399;
  color: white;
}

.btn-secondary:hover {
  background-color: #a6a9ad;
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(144, 147, 153, 0.3);
}

.btn-warning {
  background-color: #e6a23c;
  color: white;
}

.btn-warning:hover {
  background-color: #ebb563;
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(230, 162, 60, 0.3);
}

.error-details {
  margin: 30px 0;
  text-align: left;
  background-color: #f5f7fa;
  padding: 20px;
  border-radius: 8px;
  border: 1px solid #ebeef5;
}

.error-details h3 {
  font-size: 20px;
  font-weight: 600;
  margin: 0 0 20px;
  color: #333;
  text-align: center;
}

.detail-section {
  margin-bottom: 20px;
}

.detail-section:last-child {
  margin-bottom: 0;
}

.detail-section h4 {
  font-size: 16px;
  font-weight: 600;
  margin: 0 0 10px;
  color: #555;
}

.detail-section pre {
  margin: 0;
  padding: 15px;
  background-color: #282c34;
  color: #abb2bf;
  border-radius: 6px;
  overflow-x: auto;
  font-size: 14px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.request-id {
  font-family: 'Courier New', monospace;
  font-size: 14px;
  color: #666;
  background-color: #e4e7ed;
  padding: 8px 12px;
  border-radius: 4px;
  margin: 0;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .error-content {
    padding: 30px 20px;
  }
  
  .error-icon {
    font-size: 60px;
  }
  
  .error-code {
    font-size: 80px;
  }
  
  .error-title {
    font-size: 24px;
  }
  
  .error-message {
    font-size: 16px;
  }
  
  .error-actions {
    flex-direction: column;
    align-items: center;
  }
  
  .btn {
    width: 100%;
    max-width: 200px;
  }
  
  .error-details {
    padding: 15px;
  }
  
  .detail-section pre {
    font-size: 12px;
    padding: 10px;
  }
}
</style>
