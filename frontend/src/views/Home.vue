<template>
  <div class="home-page scrollbar-hide scroll-smooth">
    <div class="page-header">
      <h1>欢迎使用 LanGit</h1>
      <p class="page-description">局域网Git服务器 - 轻松管理团队代码协作</p>
    </div>
    
    <div class="cards-container">
      <!-- 系统概述卡片 -->
      <Card title="系统概述" usage="display">
        <p>LanGit 提供了一套完整的局域网Git服务器解决方案，支持团队在本地网络中共享和管理代码仓库。</p>
        <div class="system-features">
          <div class="feature-item">
            <div class="feature-icon">🔧</div>
            <div class="feature-content">
              <h4>轻量级部署</h4>
              <p>基于 FastAPI + Vue3 构建，部署简单，性能优异</p>
            </div>
          </div>
          <div class="feature-item">
            <div class="feature-icon">🌐</div>
            <div class="feature-content">
              <h4>局域网共享</h4>
              <p>支持在同一网络内的多设备访问和协作开发</p>
            </div>
          </div>
          <div class="feature-item">
            <div class="feature-icon">🔒</div>
            <div class="feature-content">
              <h4>安全控制</h4>
              <p>内置防火墙配置，保护您的代码安全</p>
            </div>
          </div>
        </div>
      </Card>
      
      <!-- 服务信息卡片 -->
      <Card title="服务信息" usage="data">
        <div class="service-info">
          <div class="info-item">
            <span class="info-label">服务地址</span>
            <span class="info-value" id="service-url">{{ serviceUrl }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">连接状态</span>
            <span class="info-value" :class="{ 'status-online': isConnected, 'status-offline': !isConnected }">
              {{ isConnected ? '在线' : '离线' }}
            </span>
          </div>
          <div class="info-item">
            <span class="info-label">API文档</span>
            <span class="info-value">
              <a :href="`${API_BASE_URL}/docs`" target="_blank" id="api-docs-link">/docs</a>
            </span>
          </div>
          <div class="info-item">
            <span class="info-label">仓库总数</span>
            <span class="info-value">{{ repositories.length }}</span>
          </div>
        </div>
      </Card>
      
      <!-- 最近仓库卡片 -->
      <Card title="最近仓库" usage="data">
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
            </div>
          </div>
          <div v-else class="empty-state">
            <span class="empty-icon">📁</span>
            <span class="empty-text">暂无仓库</span>
          </div>
        </div>
      </Card>
      
      <!-- 最近提交卡片 -->
      <Card title="最近提交" usage="data">
        <div class="commit-list">
          <div v-if="recentCommits.length > 0" class="commit-items">
            <div v-for="commit in recentCommits" :key="commit.hash" class="commit-item">
              <div class="commit-info">
                <div class="commit-hash">{{ commit.hash.substring(0, 7) }}</div>
                <div class="commit-message">{{ commit.commit_message }}</div>
                <div class="commit-meta">
                  <span class="meta-item">
                    <i class="meta-icon">👤</i>
                    {{ commit.author_name }}
                  </span>
                  <span class="meta-item">
                    <i class="meta-icon">📅</i>
                    {{ formatDate(commit.updated_at) }}
                  </span>
                </div>
              </div>
            </div>
          </div>
          <div v-else class="empty-state">
            <span class="empty-icon">📝</span>
            <span class="empty-text">暂无提交记录</span>
          </div>
        </div>
      </Card>
      
      <!-- 快速操作卡片 -->
      <Card title="快速操作" usage="default">
        <div class="quick-actions">
          <button class="action-btn" @click="handleCreateRepo">
            <span class="btn-icon">📦</span>
            <span class="btn-text">创建仓库</span>
          </button>
          <button class="action-btn" @click="handleViewBranches">
            <span class="btn-icon">🌿</span>
            <span class="btn-text">管理分支</span>
          </button>
          <button class="action-btn" @click="handleViewCommits">
            <span class="btn-icon">📋</span>
            <span class="btn-text">查看提交</span>
          </button>
          <button class="action-btn" @click="handleRefresh">
            <span class="btn-icon">🔄</span>
            <span class="btn-text">刷新数据</span>
          </button>
        </div>
      </Card>
      
      <!-- 开发文档卡片 -->
      <Card title="开发文档" usage="display">
        <div class="docs-list">
          <a :href="`${API_BASE_URL}/docs`" target="_blank" class="docs-item">
            <span class="docs-icon">📖</span>
            <span class="docs-title">API 文档</span>
            <span class="docs-arrow">→</span>
          </a>
          <a href="#" class="docs-item">
            <span class="docs-icon">⚙️</span>
            <span class="docs-title">配置说明</span>
            <span class="docs-arrow">→</span>
          </a>
          <a href="#" class="docs-item">
            <span class="docs-icon">🔧</span>
            <span class="docs-title">使用指南</span>
            <span class="docs-arrow">→</span>
          </a>
          <a href="#" class="docs-item">
            <span class="docs-icon">📝</span>
            <span class="docs-title">更新日志</span>
            <span class="docs-arrow">→</span>
          </a>
        </div>
      </Card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import Card from '@/components/public/Card.vue';
import { repositoryApi, commitApi, API_BASE_URL } from '@/utils/api';

// 状态管理
const serviceUrl = ref(API_BASE_URL);
const isConnected = ref(false);
const repositories = ref<any[]>([]);
const recentCommits = ref<any[]>([]);
const isLoading = ref(false);

// 格式化日期
const formatDate = (dateString: string): string => {
  const date = new Date(dateString);
  return date.toLocaleString();
};

// 检查服务连接
const checkConnection = async () => {
  try {
    const response = await fetch(`${serviceUrl.value}/health`);
    isConnected.value = response.ok;
  } catch (error) {
    isConnected.value = false;
  }
};

// 获取仓库列表
const fetchRepositories = async () => {
  try {
    const response = await repositoryApi.getRepositories();
    if (response.success && response.data) {
      repositories.value = response.data;
    }
  } catch (error) {
    console.error('获取仓库列表失败:', error);
  }
};

// 获取最近提交
const fetchRecentCommits = async () => {
  try {
    // 这里假设我们获取第一个仓库的最近提交
    if (repositories.value.length > 0) {
      const repoId = repositories.value[0].id;
      const response = await commitApi.getCommits(repoId, { limit: 5 });
      if (response.success && response.data) {
        recentCommits.value = response.data;
      }
    }
  } catch (error) {
    console.error('获取最近提交失败:', error);
  }
};

// 刷新数据
const handleRefresh = async () => {
  isLoading.value = true;
  await Promise.all([
    checkConnection(),
    fetchRepositories()
  ]);
  await fetchRecentCommits();
  isLoading.value = false;
};

// 创建仓库
const handleCreateRepo = () => {
  // 这里可以跳转到创建仓库页面或显示创建仓库弹窗
  alert('创建仓库功能开发中...');
};

// 管理分支
const handleViewBranches = () => {
  // 这里可以跳转到分支管理页面
  alert('分支管理功能开发中...');
};

// 查看提交
const handleViewCommits = () => {
  // 这里可以跳转到提交历史页面
  alert('提交历史功能开发中...');
};

// 页面挂载时初始化数据
onMounted(async () => {
  await handleRefresh();
});
</script>

<style scoped>
.home-page {
  padding: 24px;
  min-height: 100%;
  background: var(--color-main-content-bg);
}

.page-header {
  margin-bottom: 32px;
  text-align: center;
}

.page-header h1 {
  font-size: 2.5rem;
  color: var(--color-text);
  margin-bottom: 8px;
}

.page-description {
  font-size: 1.1rem;
  color: var(--color-text-secondary);
  margin: 0;
}

.cards-container {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  justify-content: center;
}

/* 系统特性样式 */
.system-features {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-top: 16px;
}

.feature-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px;
  background-color: var(--color-card-divider);
  border-radius: var(--radius-sm);
  transition: background-color var(--transition-fast);
}

.feature-item:hover {
  background-color: var(--color-hover);
}

.feature-icon {
  font-size: 1.5rem;
  margin-top: 2px;
}

.feature-content h4 {
  margin: 0 0 4px 0;
  font-size: 1rem;
  color: var(--color-text);
}

.feature-content p {
  margin: 0;
  font-size: 0.9rem;
  color: var(--color-text-secondary);
}

/* 快速操作样式 */
.quick-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-top: 16px;
}

.action-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 16px;
  background-color: var(--color-card-divider);
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all var(--transition-fast);
  gap: 8px;
}

.action-btn:hover {
  background-color: var(--color-hover);
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.btn-icon {
  font-size: 1.5rem;
}

.btn-text {
  font-size: 0.9rem;
  color: var(--color-text);
}

/* 服务信息样式 */
.service-info {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 16px;
}

.info-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background-color: var(--color-card-divider);
  border-radius: var(--radius-sm);
}

.info-label {
  font-size: 0.9rem;
  color: var(--color-text-secondary);
}

.info-value {
  font-size: 0.9rem;
  color: var(--color-text);
  font-weight: 500;
}

.info-value a {
  color: var(--color-primary);
  text-decoration: none;
}

.info-value a:hover {
  text-decoration: underline;
}

/* 状态样式 */
.status-online {
  color: #10b981;
}

.status-offline {
  color: #ef4444;
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
  padding: 12px;
  background-color: var(--color-card-divider);
  border-radius: var(--radius-sm);
  transition: background-color var(--transition-fast);
}

.repository-item:hover {
  background-color: var(--color-hover);
}

.repo-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.repo-name {
  font-size: 1rem;
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
  padding: 12px;
  background-color: var(--color-card-divider);
  border-radius: var(--radius-sm);
  transition: background-color var(--transition-fast);
}

.commit-item:hover {
  background-color: var(--color-hover);
}

.commit-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.commit-hash {
  font-size: 0.85rem;
  font-family: monospace;
  color: var(--color-primary);
}

.commit-message {
  font-size: 0.9rem;
  color: var(--color-text);
}

.commit-meta {
  display: flex;
  gap: 16px;
  margin-top: 8px;
}

/* 空状态样式 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 32px;
  color: var(--color-text-secondary);
  gap: 8px;
}

.empty-icon {
  font-size: 2rem;
}

.empty-text {
  font-size: 0.9rem;
}

/* 最近活动样式 */
.activity-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 16px;
}

.activity-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background-color: var(--color-card-divider);
  border-radius: var(--radius-sm);
}

.activity-time {
  font-size: 0.8rem;
  color: var(--color-text-secondary);
  min-width: 80px;
}

.activity-content {
  font-size: 0.9rem;
  color: var(--color-text);
  flex: 1;
  margin-left: 16px;
}

/* 开发文档样式 */
.docs-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 16px;
}

.docs-item {
  display: flex;
  align-items: center;
  padding: 12px;
  background-color: var(--color-card-divider);
  border-radius: var(--radius-sm);
  text-decoration: none;
  transition: all var(--transition-fast);
  gap: 12px;
}

.docs-item:hover {
  background-color: var(--color-hover);
  transform: translateX(4px);
}

.docs-icon {
  font-size: 1.2rem;
}

.docs-title {
  flex: 1;
  color: var(--color-text);
  font-size: 0.9rem;
}

.docs-arrow {
  color: var(--color-text-secondary);
  font-size: 0.8rem;
}

/* 关于样式 */
.about-content {
  margin-top: 16px;
}

.about-content p {
  margin: 8px 0;
  font-size: 0.9rem;
  color: var(--color-text);
}

.about-desc {
  color: var(--color-text-secondary) !important;
  font-size: 0.85rem !important;
}

/* 响应式设计 */
@media (min-width: 768px) {
  .cards-container {
    justify-content: flex-start;
  }
  
  .card-container {
    width: calc(50% - 10px);
  }
}

@media (min-width: 1200px) {
  .card-container {
    width: calc(33.333% - 13.333px);
  }
}
</style>
