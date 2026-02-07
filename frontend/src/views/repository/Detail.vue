<template>
  <div class="repository-detail">
    <!-- 仓库头部信息 -->
    <div class="repo-header">
      <div class="repo-basic-info">
        <h1 class="repo-name">{{ repository?.name }}</h1>
        <p class="repo-description">{{ repository?.description || '无描述' }}</p>
        <div class="repo-meta">
          <span class="meta-item">
            <i class="meta-icon">👁️</i>
            {{ repository?.is_public ? '公开' : '私有' }}
          </span>
          <span class="meta-item">
            <i class="meta-icon">🔀</i>
            默认分支: {{ repository?.default_branch || 'master' }}
          </span>
          <span class="meta-item">
            <i class="meta-icon">📦</i>
            分支: {{ branches.length }}
          </span>
          <span class="meta-item">
            <i class="meta-icon">📝</i>
            提交: {{ commits.length }}
          </span>
        </div>
      </div>
      <div class="repo-actions">
        <button class="action-btn" @click="handleBack">
          <i class="btn-icon">←</i>
          返回仓库列表
        </button>
      </div>
    </div>
    
    <!-- 仓库内容区域 -->
    <div class="content-container">
      <!-- 分支信息卡片 -->
      <Card title="分支管理" usage="data" class="content-card">
        <div class="branch-list">
          <div v-if="branches.length > 0" class="branch-items">
            <div v-for="branch in branches" :key="branch.name" class="branch-item">
              <div class="branch-info">
                <div class="branch-name">
                  <span class="branch-icon">{{ branch.is_default ? '🏠' : '🌿' }}</span>
                  {{ branch.name }}
                </div>
                <div class="branch-protection">
                  {{ branch.is_protected ? '🔒 受保护' : '🔓 未受保护' }}
                </div>
              </div>
            </div>
          </div>
          <div v-else class="empty-state">
            <span class="empty-icon">🌿</span>
            <span class="empty-text">暂无分支</span>
          </div>
        </div>
      </Card>
      
      <!-- 提交记录卡片 -->
      <Card title="提交记录" usage="data" class="content-card">
        <div class="commit-list">
          <div v-if="commits.length > 0" class="commit-items">
            <div v-for="commit in commits" :key="commit.hash" class="commit-item">
              <div class="commit-header">
                <div class="commit-hash">{{ commit.hash.substring(0, 7) }}</div>
                <div class="commit-date">{{ formatDate(commit.updated_at) }}</div>
              </div>
              <div class="commit-message">{{ commit.commit_message }}</div>
              <div class="commit-author">
                <i class="author-icon">👤</i>
                {{ commit.author_name }} <{{ commit.author_email }}>
              </div>
            </div>
          </div>
          <div v-else class="empty-state">
            <span class="empty-icon">📝</span>
            <span class="empty-text">暂无提交记录</span>
          </div>
        </div>
      </Card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import Card from '@/components/public/Card.vue';
import { repositoryApi, branchApi, commitApi } from '@/utils/api';
import { ExceptionHandler } from '@/utils/exceptionHandler';

// 路由
const route = useRoute();
const router = useRouter();

// 状态管理
const repository = ref<any>(null);
const branches = ref<any[]>([]);
const commits = ref<any[]>([]);
const isLoading = ref(false);

// 获取仓库ID
const getRepoId = () => {
  const id = route.params.id;
  return typeof id === 'string' ? parseInt(id) : 0;
};

// 格式化日期
const formatDate = (dateString: string): string => {
  const date = new Date(dateString);
  return date.toLocaleString();
};

// 获取仓库详情
const fetchRepository = async () => {
  try {
    const repoId = getRepoId();
    const response = await repositoryApi.getRepository(repoId);
    if (response.success && response.data) {
      repository.value = response.data;
    } else if (response.error) {
      // 处理API响应错误
      const error = new Error(response.error) as any;
      error.statusCode = 400;
      error.errorType = 'ApiError';
      ExceptionHandler.showErrorMessage(error);
    }
  } catch (error) {
    console.error('获取仓库详情失败:', error);
    ExceptionHandler.globalErrorHandler(error);
  }
};

// 获取分支列表
const fetchBranches = async () => {
  try {
    const repoId = getRepoId();
    const response = await branchApi.getBranches(repoId);
    if (response.success && response.data) {
      branches.value = response.data;
    } else if (response.error) {
      // 处理API响应错误
      const error = new Error(response.error) as any;
      error.statusCode = 400;
      error.errorType = 'ApiError';
      ExceptionHandler.showErrorMessage(error);
    }
  } catch (error) {
    console.error('获取分支列表失败:', error);
    ExceptionHandler.globalErrorHandler(error);
  }
};

// 获取提交记录
const fetchCommits = async () => {
  try {
    const repoId = getRepoId();
    const response = await commitApi.getCommits(repoId, { limit: 10 });
    if (response.success && response.data) {
      commits.value = response.data;
    } else if (response.error) {
      // 处理API响应错误
      const error = new Error(response.error) as any;
      error.statusCode = 400;
      error.errorType = 'ApiError';
      ExceptionHandler.showErrorMessage(error);
    }
  } catch (error) {
    console.error('获取提交记录失败:', error);
    ExceptionHandler.globalErrorHandler(error);
  }
};

// 刷新数据
const refreshData = async () => {
  isLoading.value = true;
  try {
    await Promise.all([
      fetchRepository(),
      fetchBranches(),
      fetchCommits()
    ]);
  } catch (error) {
    console.error('刷新数据失败:', error);
    ExceptionHandler.globalErrorHandler(error);
  } finally {
    isLoading.value = false;
  }
};

// 返回仓库列表
const handleBack = () => {
  router.push('/repository/management');
};

// 监听路由参数变化
watch(() => route.params.id, () => {
  refreshData();
});

// 页面挂载时初始化数据
onMounted(async () => {
  await refreshData();
});
</script>

<style scoped>
.repository-detail {
  width: 100%;
}

/* 仓库头部样式 */
.repo-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 24px;
  background-color: var(--color-card-divider);
  border-radius: var(--radius-md);
  margin-bottom: 24px;
}

.repo-basic-info {
  flex: 1;
}

.repo-name {
  font-size: 2rem;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: 8px;
}

.repo-description {
  font-size: 1rem;
  color: var(--color-text-secondary);
  margin-bottom: 16px;
}

.repo-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.9rem;
  color: var(--color-text-secondary);
}

.meta-icon {
  font-size: 1rem;
}

.repo-actions {
  display: flex;
  gap: 12px;
  margin-left: 24px;
}

.action-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  background-color: var(--color-primary);
  color: white;
  border: none;
  border-radius: var(--radius-sm);
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  transition: background-color var(--transition-fast);
}

.action-btn:hover {
  background-color: var(--color-primary-hover);
}

.btn-icon {
  font-size: 1rem;
}

/* 内容区域样式 */
.content-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.content-card {
  width: 100%;
}

/* 分支列表样式 */
.branch-list {
  margin-top: 16px;
}

.branch-items {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.branch-item {
  padding: 16px;
  background-color: var(--color-card-divider);
  border-radius: var(--radius-sm);
  transition: background-color var(--transition-fast);
}

.branch-item:hover {
  background-color: var(--color-hover);
}

.branch-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.branch-name {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 1rem;
  font-weight: 500;
  color: var(--color-text);
}

.branch-icon {
  font-size: 1.2rem;
}

.branch-protection {
  font-size: 0.85rem;
  color: var(--color-text-secondary);
}

/* 提交列表样式 */
.commit-list {
  margin-top: 16px;
}

.commit-items {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.commit-item {
  padding: 16px;
  background-color: var(--color-card-divider);
  border-radius: var(--radius-sm);
  transition: background-color var(--transition-fast);
}

.commit-item:hover {
  background-color: var(--color-hover);
}

.commit-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.commit-hash {
  font-size: 0.85rem;
  font-family: monospace;
  color: var(--color-primary);
}

.commit-date {
  font-size: 0.85rem;
  color: var(--color-text-secondary);
}

.commit-message {
  font-size: 1rem;
  color: var(--color-text);
  margin-bottom: 8px;
}

.commit-author {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.85rem;
  color: var(--color-text-secondary);
}

.author-icon {
  font-size: 1rem;
}

/* 空状态样式 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px;
  color: var(--color-text-secondary);
  gap: 8px;
}

.empty-icon {
  font-size: 2rem;
}

.empty-text {
  font-size: 1rem;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .repo-header {
    flex-direction: column;
    gap: 16px;
  }
  
  .repo-actions {
    margin-left: 0;
  }
  
  .repo-meta {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
}
</style>