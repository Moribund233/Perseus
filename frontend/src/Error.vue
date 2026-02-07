<template>
  <div class="error-container">
    <div class="error-content">
      <div class="error-icon">{{ errorIcon }}</div>
      <h1 class="error-code">{{ errorCode }}</h1>
      <h2 class="error-title">{{ errorTitle }}</h2>
      <p class="error-message">{{ errorMessage }}</p>
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
      </div>
      <div v-if="errorDetails" class="error-details">
        <h3>错误详情</h3>
        <pre>{{ errorDetails }}</pre>
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

// 从路由参数中获取错误信息
const loadErrorInfo = () => {
  const code = route.params.code as string;
  const message = route.params.message as string;
  const details = route.params.details as string;
  
  if (code) {
    errorCode.value = parseInt(code, 10);
  }
  
  if (message) {
    errorMessage.value = message;
  }
  
  if (details) {
    errorDetails.value = decodeURIComponent(details);
  }
  
  // 根据错误码设置默认标题和消息
  switch (errorCode.value) {
    case 400:
      errorTitle.value = '请求错误';
      if (!message) {
        errorMessage.value = '您的请求无效，请检查后重试';
      }
      break;
    case 401:
      errorTitle.value = '未授权';
      if (!message) {
        errorMessage.value = '您需要登录才能访问此页面';
      }
      break;
    case 403:
      errorTitle.value = '禁止访问';
      if (!message) {
        errorMessage.value = '您没有权限访问此页面';
      }
      break;
    case 404:
      errorTitle.value = '页面未找到';
      if (!message) {
        errorMessage.value = '抱歉，您访问的页面不存在或已被删除';
      }
      break;
    case 408:
      errorTitle.value = '请求超时';
      if (!message) {
        errorMessage.value = '服务器响应超时，请稍后重试';
      }
      break;
    case 409:
      errorTitle.value = '资源冲突';
      if (!message) {
        errorMessage.value = '请求的资源存在冲突，请检查后重试';
      }
      break;
    case 500:
      errorTitle.value = '服务器错误';
      if (!message) {
        errorMessage.value = '服务器内部错误，请稍后重试';
      }
      break;
    case 502:
      errorTitle.value = '网关错误';
      if (!message) {
        errorMessage.value = '网关错误，请稍后重试';
      }
      break;
    case 503:
      errorTitle.value = '服务不可用';
      if (!message) {
        errorMessage.value = '服务暂时不可用，请稍后重试';
      }
      break;
    case 504:
      errorTitle.value = '网关超时';
      if (!message) {
        errorMessage.value = '网关超时，请稍后重试';
      }
      break;
    default:
      errorTitle.value = '未知错误';
      if (!message) {
        errorMessage.value = '发生了未知错误，请稍后重试';
      }
      break;
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
  max-width: 600px;
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

.error-details {
  margin-top: 30px;
  text-align: left;
  background-color: #f5f7fa;
  padding: 20px;
  border-radius: 8px;
  border: 1px solid #ebeef5;
}

.error-details h3 {
  font-size: 18px;
  font-weight: 600;
  margin: 0 0 15px;
  color: #333;
}

.error-details pre {
  margin: 0;
  padding: 15px;
  background-color: #282c34;
  color: #abb2bf;
  border-radius: 6px;
  overflow-x: auto;
  font-size: 14px;
  line-height: 1.5;
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
}
</style>
