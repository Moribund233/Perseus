<template>
  <div class="register-container">
    <div class="register-form-wrapper">
      <h1 class="register-title">LanGit 注册</h1>
      <form @submit.prevent="handleRegister" class="register-form">
        <div class="form-group">
          <label for="username" class="form-label">用户名</label>
          <input
            type="text"
            id="username"
            v-model="form.username"
            placeholder="请输入用户名"
            class="form-input"
            required
          />
        </div>
        <div class="form-group">
          <label for="email" class="form-label">邮箱</label>
          <input
            type="email"
            id="email"
            v-model="form.email"
            placeholder="请输入邮箱"
            class="form-input"
            required
          />
        </div>
        <div class="form-group">
          <label for="password" class="form-label">密码</label>
          <input
            type="password"
            id="password"
            v-model="form.password"
            placeholder="请输入密码"
            class="form-input"
            required
          />
        </div>
        <div class="form-group">
          <label for="confirmPassword" class="form-label">确认密码</label>
          <input
            type="password"
            id="confirmPassword"
            v-model="form.confirmPassword"
            placeholder="请再次输入密码"
            class="form-input"
            required
          />
        </div>
        <!-- 错误信息提示 -->
        <div v-if="errorMessage" class="error-message">
          {{ errorMessage }}
        </div>
        <button type="submit" class="register-button" :disabled="isLoading || !isFormValid">
          {{ isLoading ? '注册中...' : '注册' }}
        </button>
        <div class="register-footer">
          <span>已有账号？</span>
          <router-link to="/login" class="login-link">立即登录</router-link>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { useRouter } from 'vue-router';
import { userApi } from '@/utils/api';

// 表单数据
const form = ref({
  username: '',
  email: '',
  password: '',
  confirmPassword: ''
});

// 状态
const isLoading = ref(false);
const errorMessage = ref('');

// 路由
const router = useRouter();

// 表单验证
const isFormValid = computed(() => {
  return (
    form.value.username.trim() !== '' &&
    form.value.email.trim() !== '' &&
    form.value.password.trim() !== '' &&
    form.value.password === form.value.confirmPassword
  );
});

// 注册处理
const handleRegister = async () => {
  isLoading.value = true;
  errorMessage.value = '';

  try {
    // 准备注册数据
    const registerData = {
      username: form.value.username,
      email: form.value.email,
      password: form.value.password
    };

    const response = await userApi.register(registerData);

    if (response.success) {
      // 注册成功，跳转到登录页面
      router.push('/login');
    } else {
      throw new Error(response.error || '注册失败');
    }
  } catch (error: any) {
    errorMessage.value = error.message;
    console.error('注册失败:', error);
  } finally {
    isLoading.value = false;
  }
};
</script>

<style scoped>
.register-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background-color: #f5f7fa;
  padding: 20px;
}

.register-form-wrapper {
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  padding: 40px;
  width: 100%;
  max-width: 400px;
}

.register-title {
  font-size: 24px;
  font-weight: 600;
  color: #333;
  margin-bottom: 30px;
  text-align: center;
}

.form-group {
  margin-bottom: 20px;
}

.form-label {
  display: block;
  font-size: 14px;
  font-weight: 500;
  color: #666;
  margin-bottom: 8px;
}

.form-input {
  width: 100%;
  padding: 12px 16px;
  font-size: 14px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  transition: border-color 0.3s;
}

.form-input:focus {
  outline: none;
  border-color: #409eff;
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.2);
}

.register-button {
  width: 100%;
  padding: 12px;
  font-size: 16px;
  font-weight: 500;
  color: #fff;
  background-color: #409eff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.3s;
}

.register-button:hover:not(:disabled) {
  background-color: #66b1ff;
}

.register-button:disabled {
  background-color: #a0cfff;
  cursor: not-allowed;
}

.error-message {
  margin-bottom: 16px;
  padding: 10px 12px;
  background-color: #fef0f0;
  border: 1px solid #fde2e2;
  border-radius: 4px;
  color: #f56c6c;
  font-size: 14px;
  text-align: center;
}

.register-footer {
  margin-top: 20px;
  text-align: center;
  font-size: 14px;
  color: #909399;
}

.login-link {
  color: #409eff;
  text-decoration: none;
  margin-left: 8px;
  cursor: pointer;
}

.login-link:hover {
  color: #66b1ff;
  text-decoration: underline;
}
</style>