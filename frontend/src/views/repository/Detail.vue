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

    <!-- 标签页导航 -->
    <div class="tab-navigation">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        :class="['tab-btn', { 'active': currentTab === tab.id }]"
        @click="currentTab = tab.id"
      >
        <span class="tab-icon">{{ tab.icon }}</span>
        {{ tab.name }}
      </button>
    </div>

    <!-- 标签页内容 -->
    <div class="tab-content">
      <!-- 代码浏览标签页 -->
      <div v-show="currentTab === 'browser'" class="browser-tab">
        <div class="browser-layout">
          <!-- 左侧文件树 -->
          <Card title="📁 文件树" usage="browser" class="file-tree-card">
            <FileTree
              :repo-id="getRepoId()"
              :ref-name="currentRef"
              @select="handleFileSelect"
            />
          </Card>

          <!-- 右侧文件查看器 -->
          <Card title="📄 文件内容" usage="browser" class="file-viewer-card">
            <FileViewer
              v-if="selectedFile && selectedFile.type === 'blob'"
              :repo-id="getRepoId()"
              :path="selectedFile.path"
              :ref-name="currentRef"
            />
            <div v-else-if="selectedFile && selectedFile.type === 'tree'" class="folder-placeholder">
              <span class="placeholder-icon">📂</span>
              <span class="placeholder-text">目录: {{ selectedFile.name }}</span>
            </div>
            <div v-else class="file-placeholder">
              <span class="placeholder-icon">📄</span>
              <span class="placeholder-text">选择左侧文件查看内容</span>
            </div>
          </Card>
        </div>
      </div>

      <!-- 提交历史标签页 -->
      <div v-show="currentTab === 'commits'" class="commits-tab">
        <Card title="提交历史" usage="data" class="commits-card">
          <CommitHistory
            :repo-id="getRepoId()"
            :ref-name="currentRef"
            :limit="20"
            @select="handleCommitSelect"
          />
        </Card>
      </div>

      <!-- 代码对比标签页 -->
      <div v-show="currentTab === 'diff'" class="diff-tab">
        <Card title="代码对比" usage="data" class="diff-card">
          <div class="diff-controls">
            <div class="diff-inputs">
              <div class="input-group">
                <label>基准版本:</label>
                <input
                  v-model="diffBase"
                  type="text"
                  placeholder="HEAD~1"
                  class="diff-input"
                />
              </div>
              <div class="input-group">
                <label>目标版本:</label>
                <input
                  v-model="diffHead"
                  type="text"
                  placeholder="HEAD"
                  class="diff-input"
                />
              </div>
              <button class="compare-btn" @click="refreshDiff">
                🔍 对比
              </button>
            </div>
          </div>
          <DiffViewer
            :repo-id="getRepoId()"
            :head="diffHead || 'HEAD'"
            :base="diffBase"
          />
        </Card>
      </div>

      <!-- 分支管理标签页 -->
      <div v-show="currentTab === 'branches'" class="branches-tab">
        <div class="content-container">
          <Card title="分支管理" usage="data" class="content-card">
            <div class="branch-list">
              <div v-if="branches.length > 0" class="branch-items">
                <div
                  v-for="branch in branches"
                  :key="branch.name"
                  :class="['branch-item', { 'active': currentRef === branch.name }]"
                  @click="handleBranchSelect(branch.name)"
                >
                  <div class="branch-info">
                    <div class="branch-name">
                      <span class="branch-icon">{{ branch.is_default ? '🏠' : '🌿' }}</span>
                      {{ branch.name }}
                    </div>
                    <div class="branch-protection">
                      {{ branch.is_protected ? '🔒 受保护' : '🔓 未受保护' }}
                    </div>
                  </div>
                  <button
                    v-if="!branch.is_default"
                    class="checkout-btn"
                    @click.stop="checkoutBranch(branch.name)"
                  >
                    切换
                  </button>
                </div>
              </div>
              <div v-else class="empty-state">
                <span class="empty-icon">🌿</span>
                <span class="empty-text">暂无分支</span>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import Card from '@/components/public/Card.vue';
import FileTree from '@/components/module/repository/FileTree.vue';
import FileViewer from '@/components/module/repository/FileViewer.vue';
import CommitHistory from '@/components/module/repository/CommitHistory.vue';
import DiffViewer from '@/components/module/repository/DiffViewer.vue';
import { repositoryApi, branchApi, commitApi } from '@/utils/api';
import { ExceptionHandler } from '@/utils/exceptionHandler';

/**
 * 标签页配置
 */
interface Tab {
  id: string;
  name: string;
  icon: string;
}

const tabs: Tab[] = [
  { id: 'browser', name: '代码浏览', icon: '📁' },
  { id: 'commits', name: '提交历史', icon: '📝' },
  { id: 'diff', name: '代码对比', icon: '🔍' },
  { id: 'branches', name: '分支管理', icon: '🌿' }
];

// 路由
const route = useRoute();
const router = useRouter();

// 状态管理
const repository = ref<any>(null);
const branches = ref<any[]>([]);
const commits = ref<any[]>([]);
const isLoading = ref(false);
const currentTab = ref('browser');
const currentRef = ref('HEAD');
const selectedFile = ref<{ name: string; type: 'blob' | 'tree'; path: string } | null>(null);
const diffHead = ref('HEAD');
const diffBase = ref('HEAD~1');

// 获取仓库ID
const getRepoId = (): number => {
  const id = route.params.id;
  return typeof id === 'string' ? parseInt(id) : 0;
};

// 格式化日期（保留供将来使用）
// const formatDate = (dateString: string): string => {
//   const date = new Date(dateString);
//   return date.toLocaleString();
// };

// 获取仓库详情
const fetchRepository = async () => {
  try {
    const repoId = getRepoId();
    const response = await repositoryApi.getRepository(repoId);
    if (response.success && response.data) {
      repository.value = response.data;
      // 设置默认分支
      if (repository.value?.default_branch) {
        currentRef.value = repository.value.default_branch;
      }
    } else if (response.error) {
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

// 处理文件选择
const handleFileSelect = (entry: { name: string; type: 'blob' | 'tree'; path: string; repoId: number; refName: string }) => {
  selectedFile.value = {
    name: entry.name,
    type: entry.type,
    path: entry.path
  };
};

// 处理提交选择
const handleCommitSelect = (commit: any) => {
  console.log('选中提交:', commit);
  // 可以在这里添加跳转到提交详情的逻辑
};

// 处理分支选择
const handleBranchSelect = (branchName: string) => {
  currentRef.value = branchName;
};

// 切换分支
const checkoutBranch = async (branchName: string) => {
  currentRef.value = branchName;
  // 使用 alert 替代 showSuccessMessage
  alert(`已切换到分支: ${branchName}`);
};

// 刷新代码对比
const refreshDiff = () => {
  // DiffViewer 组件会自动响应 props 变化
};

// 返回仓库列表
const handleBack = () => {
  router.push('/repository/management');
};

// 监听路由参数变化
watch(() => route.params.id, () => {
  refreshData();
  selectedFile.value = null;
});

// 页面挂载时初始化数据
onMounted(async () => {
  await refreshData();
});
</script>

<style scoped>
.repository-detail {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
}

/* 仓库头部样式 */
.repo-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 24px;
  background-color: var(--color-card-divider);
  border-radius: var(--radius-md);
  margin-bottom: 16px;
  flex-shrink: 0;
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

/* 标签页导航 */
.tab-navigation {
  display: flex;
  gap: 8px;
  padding: 0 0 16px 0;
  border-bottom: 1px solid var(--color-border);
  margin-bottom: 16px;
  flex-shrink: 0;
}

.tab-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 20px;
  background-color: transparent;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  font-size: 0.95rem;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.tab-btn:hover {
  background-color: var(--color-hover);
  border-color: var(--color-border-hover);
}

.tab-btn.active {
  background-color: var(--color-primary);
  border-color: var(--color-primary);
  color: white;
}

.tab-icon {
  font-size: 1rem;
}

/* 标签页内容 */
.tab-content {
  flex: 1;
  overflow: hidden;
  min-height: 0;
}

.tab-content > div {
  height: 100%;
}

/* 代码浏览标签页 */
.browser-tab {
  height: 100%;
}

.browser-layout {
  display: flex;
  gap: 16px;
  height: 100%;
}

.file-tree-card {
  width: 300px;
  flex-shrink: 0;
  height: 100%;
}

.file-viewer-card {
  flex: 1;
  height: 100%;
  min-width: 0;
}

.file-placeholder,
.folder-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--color-text-secondary);
  gap: 12px;
}

.placeholder-icon {
  font-size: 3rem;
}

.placeholder-text {
  font-size: 1rem;
}

/* 提交历史标签页 */
.commits-tab,
.diff-tab {
  height: 100%;
}

.commits-card,
.diff-card {
  height: 100%;
}

/* 代码对比控制 */
.diff-controls {
  padding: 12px 16px;
  background-color: var(--color-bg-tertiary);
  border-bottom: 1px solid var(--color-border);
}

.diff-inputs {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.input-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.input-group label {
  font-size: 0.9rem;
  color: var(--color-text-secondary);
  white-space: nowrap;
}

.diff-input {
  padding: 6px 10px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  font-size: 0.9rem;
  font-family: 'Consolas', 'Monaco', monospace;
  width: 120px;
}

.diff-input:focus {
  outline: none;
  border-color: var(--color-primary);
}

.compare-btn {
  padding: 8px 16px;
  background-color: var(--color-primary);
  color: white;
  border: none;
  border-radius: var(--radius-sm);
  font-size: 0.9rem;
  cursor: pointer;
  transition: opacity var(--transition-fast);
}

.compare-btn:hover {
  opacity: 0.9;
}

/* 分支管理标签页 */
.branches-tab {
  height: 100%;
}

.content-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
  height: 100%;
}

.content-card {
  width: 100%;
  height: 100%;
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
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  background-color: var(--color-card-divider);
  border-radius: var(--radius-sm);
  transition: all var(--transition-fast);
  cursor: pointer;
}

.branch-item:hover {
  background-color: var(--color-hover);
}

.branch-item.active {
  background-color: var(--color-primary-light);
  border: 1px solid var(--color-primary);
}

.branch-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex: 1;
  margin-right: 16px;
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

.checkout-btn {
  padding: 6px 12px;
  background-color: var(--color-primary);
  color: white;
  border: none;
  border-radius: var(--radius-sm);
  font-size: 0.85rem;
  cursor: pointer;
  transition: opacity var(--transition-fast);
}

.checkout-btn:hover {
  opacity: 0.9;
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
@media (max-width: 1024px) {
  .browser-layout {
    flex-direction: column;
  }

  .file-tree-card {
    width: 100%;
    height: 300px;
  }

  .file-viewer-card {
    height: calc(100% - 316px);
  }
}

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

  .tab-navigation {
    flex-wrap: wrap;
  }

  .tab-btn {
    padding: 8px 12px;
    font-size: 0.85rem;
  }

  .diff-inputs {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
