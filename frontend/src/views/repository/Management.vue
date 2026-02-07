<template>
  <div class="repository-management">
    <div class="page-header">
      <h1>仓库管理</h1>
      <p class="page-description">创建和管理您的代码仓库</p>
    </div>
    
    <div class="content-container">
      <!-- 创建仓库表单 -->
      <Card title="创建仓库" usage="default">
        <form @submit.prevent="handleCreateRepository" class="create-repo-form">
          <div class="form-group">
            <label for="repo-name">仓库名称</label>
            <input 
              type="text" 
              id="repo-name" 
              v-model="newRepo.name" 
              placeholder="输入仓库名称" 
              required
            >
          </div>
          
          <div class="form-group">
            <label for="repo-description">描述</label>
            <textarea 
              id="repo-description" 
              v-model="newRepo.description" 
              placeholder="输入仓库描述（可选）" 
              rows="3"
            ></textarea>
          </div>
          
          <div class="form-group">
            <label>
              <input 
                type="checkbox" 
                v-model="newRepo.is_public" 
              >
              公开仓库
            </label>
          </div>
          
          <div class="form-group">
            <label for="default-branch">默认分支</label>
            <input 
              type="text" 
              id="default-branch" 
              v-model="newRepo.default_branch" 
              placeholder="输入默认分支名称（默认：master）" 
            >
          </div>
          
          <button type="submit" class="submit-btn" :disabled="isCreating">
            {{ isCreating ? '创建中...' : '创建仓库' }}
          </button>
        </form>
      </Card>
      
      <!-- 仓库列表 -->
      <Card title="仓库列表" usage="data">
        <div class="repository-list">
          <div v-if="repositories.length > 0" class="repository-items">
            <div v-for="repo in repositories" :key="repo.id" class="repository-item">
              <div class="repo-info">
                <div class="repo-name">{{ repo.name }}</div>
                <div class="repo-description">{{ repo.description || '无描述' }}</div>
                <div class="repo-meta">
                  <span class="meta-item">
                    <i class="meta-icon">🔀</i>
                    {{ repo.default_branch || 'master' }}
                  </span>
                  <span class="meta-item">
                    <i class="meta-icon">👁️</i>
                    {{ repo.is_public ? '公开' : '私有' }}
                  </span>
                </div>
              </div>
              <div class="repo-actions">
                <button 
                  class="action-btn view-btn" 
                  @click="handleViewRepository(repo.id)"
                >
                  查看详情
                </button>
                <button 
                  class="action-btn delete-btn" 
                  @click="handleDeleteRepository(repo.id)"
                >
                  删除
                </button>
              </div>
            </div>
          </div>
          <div v-else class="empty-state">
            <span class="empty-icon">📁</span>
            <span class="empty-text">暂无仓库</span>
            <span class="empty-hint">点击上方表单创建您的第一个仓库</span>
          </div>
        </div>
      </Card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import Card from '@/components/public/Card.vue';
import { repositoryApi } from '@/utils/api';
import { useUserStore } from '@/stores/user';
import { ExceptionHandler } from '@/utils/exceptionHandler';

// 路由
const router = useRouter();

// 用户store
const userStore = useUserStore();

// 状态管理
const repositories = ref<any[]>([]);
const isCreating = ref(false);
const newRepo = ref({
  name: '',
  description: '',
  is_public: true,
  default_branch: 'master'
});

// 获取仓库列表
const fetchRepositories = async () => {
  try {
    const response = await repositoryApi.getRepositories();
    if (response.success && response.data) {
      repositories.value = response.data;
    } else if (response.error) {
      // 处理API响应错误
      const error = new Error(response.error) as any;
      error.statusCode = 400;
      error.errorType = 'ApiError';
      ExceptionHandler.showErrorMessage(error);
    }
  } catch (error) {
    console.error('获取仓库列表失败:', error);
    ExceptionHandler.globalErrorHandler(error);
  }
};

// 创建仓库
const handleCreateRepository = async () => {
  try {
    isCreating.value = true;
    // 获取当前用户ID作为仓库所有者ID
    const owner_id = userStore.currentUser?.id;
    if (!owner_id) {
      const error = new Error('用户未登录') as any;
      error.errorType = 'AuthenticationException';
      ExceptionHandler.showErrorMessage(error);
      return;
    }
    
    // 自动生成path字段，使用仓库名称的小写版本，并用连字符替换空格
    const path = `/repos/${newRepo.value.name.toLowerCase().replace(/\s+/g, '-')}`;
    
    // 合并仓库数据和所有者ID
    const repoData = {
      ...newRepo.value,
      owner_id,
      path
    };
    
    const response = await repositoryApi.createRepository(repoData);
    if (response.success) {
      // 重置表单
      newRepo.value = {
        name: '',
        description: '',
        is_public: true,
        default_branch: 'master'
      };
      // 重新获取仓库列表
      await fetchRepositories();
      // 跳转到新创建的仓库详情页
      router.push(`/repository/detail/${response.data.id}`);
    } else if (response.error) {
      // 处理API响应错误
      const error = new Error(response.error) as any;
      error.statusCode = 400;
      error.errorType = 'ValidationException';
      ExceptionHandler.showErrorMessage(error);
    }
  } catch (error) {
    console.error('创建仓库失败:', error);
    ExceptionHandler.globalErrorHandler(error);
  } finally {
    isCreating.value = false;
  }
};

// 查看仓库详情
const handleViewRepository = (repoId: number) => {
  router.push(`/repository/detail/${repoId}`);
};

// 删除仓库
const handleDeleteRepository = async (repoId: number) => {
  try {
    if (confirm('确定要删除这个仓库吗？此操作不可恢复。')) {
      const response = await repositoryApi.deleteRepository(repoId);
      if (response.success) {
        // 重新获取仓库列表
        await fetchRepositories();
      } else if (response.error) {
        // 处理API响应错误
        const error = new Error(response.error) as any;
        error.statusCode = 400;
        error.errorType = 'ApiError';
        ExceptionHandler.showErrorMessage(error);
      }
    }
  } catch (error) {
    console.error('删除仓库失败:', error);
    ExceptionHandler.globalErrorHandler(error);
  }
};

// 页面挂载时初始化数据
onMounted(async () => {
  await fetchRepositories();
});
</script>

<style scoped>
.repository-management {
  width: 100%;
}

.page-header {
  margin-bottom: 32px;
}

.page-header h1 {
  font-size: 2rem;
  color: var(--color-text);
  margin-bottom: 8px;
}

.page-description {
  font-size: 1rem;
  color: var(--color-text-secondary);
  margin: 0;
}

.content-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* 创建仓库表单样式 */
.create-repo-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-top: 16px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-group label {
  font-size: 0.9rem;
  font-weight: 500;
  color: var(--color-text);
}

.form-group input[type="text"],
.form-group textarea {
  padding: 10px;
  border: 1px solid var(--color-card-border);
  border-radius: var(--radius-sm);
  font-size: 0.9rem;
  background-color: var(--color-card-divider);
  transition: all var(--transition-fast);
}

.form-group input[type="text"]:focus,
.form-group textarea:focus {
  outline: none;
  border-color: var(--color-primary);
  background-color: white;
}

.form-group input[type="checkbox"] {
  margin-right: 8px;
  cursor: pointer;
}

.submit-btn {
  padding: 12px;
  border: none;
  border-radius: var(--radius-sm);
  font-size: 0.9rem;
  font-weight: 500;
  color: white;
  background-color: var(--color-primary);
  cursor: pointer;
  transition: background-color var(--transition-fast);
  margin-top: 8px;
}

.submit-btn:hover:not(:disabled) {
  background-color: var(--color-primary-hover);
}

.submit-btn:disabled {
  background-color: var(--color-card-divider);
  color: var(--color-text-secondary);
  cursor: not-allowed;
}

/* 仓库列表样式 */
.repository-list {
  margin-top: 16px;
}

.repository-items {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.repository-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  background-color: var(--color-card-divider);
  border-radius: var(--radius-sm);
  transition: background-color var(--transition-fast);
}

.repository-item:hover {
  background-color: var(--color-hover);
}

.repo-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.repo-name {
  font-size: 1.1rem;
  font-weight: 500;
  color: var(--color-text);
}

.repo-description {
  font-size: 0.85rem;
  color: var(--color-text-secondary);
}

.repo-meta {
  display: flex;
  gap: 16px;
  margin-top: 8px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 0.8rem;
  color: var(--color-text-secondary);
}

.meta-icon {
  font-size: 0.9rem;
}

.repo-actions {
  display: flex;
  gap: 12px;
}

.action-btn {
  padding: 8px 16px;
  border: none;
  border-radius: var(--radius-sm);
  font-size: 0.85rem;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.view-btn {
  background-color: var(--color-primary);
  color: white;
}

.view-btn:hover {
  background-color: var(--color-primary-hover);
}

.delete-btn {
  background-color: transparent;
  color: var(--color-error);
  border: 1px solid var(--color-error);
}

.delete-btn:hover {
  background-color: var(--color-error);
  color: white;
}

/* 空状态样式 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px;
  color: var(--color-text-secondary);
  gap: 12px;
}

.empty-icon {
  font-size: 3rem;
}

.empty-text {
  font-size: 1.1rem;
}

.empty-hint {
  font-size: 0.9rem;
}
</style>