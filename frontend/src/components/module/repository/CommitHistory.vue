<!--
  仓库模块组件: 提交历史
  用途: 展示仓库提交历史，支持分页和提交详情查看
  调用: <CommitHistory :repo-id="1" :ref-name="'master'" @select="handleCommitSelect" />
  特性:
    - 提交列表展示
    - 分页支持
    - 提交信息展示（作者、时间、消息）
    - 提交哈希复制
    - 点击提交查看详情
-->
<template>
  <div class="commit-history-container">
    <!-- 头部 -->
    <div class="history-header">
      <h3 class="history-title">📜 提交历史</h3>
      <div class="history-stats" v-if="total > 0">
        共 {{ total }} 条提交
      </div>
    </div>

    <!-- 加载状态 -->
    <div v-if="isLoading" class="loading-state">
      <span class="loading-icon">⏳</span>
      <span class="loading-text">加载提交历史...</span>
    </div>

    <!-- 错误状态 -->
    <div v-else-if="error" class="error-state">
      <span class="error-icon">⚠️</span>
      <span class="error-text">{{ error }}</span>
      <button class="retry-btn" @click="loadCommits">重试</button>
    </div>

    <!-- 空状态 -->
    <div v-else-if="commits.length === 0" class="empty-state">
      <span class="empty-icon">📝</span>
      <span class="empty-text">暂无提交记录</span>
    </div>

    <!-- 提交列表 -->
    <div v-else class="commit-list">
      <div
        v-for="commit in commits"
        :key="commit.hash"
        :class="['commit-item', { 'selected': selectedHash === commit.hash }]"
        @click="handleCommitClick(commit)"
      >
        <!-- 提交信息 -->
        <div class="commit-main">
          <div class="commit-message" :title="commit.message">
            {{ commit.message.split('\n')[0] }}
          </div>
          <div class="commit-meta">
            <span class="commit-author" :title="commit.author_email">
              👤 {{ commit.author }}
            </span>
            <span class="commit-time" :title="formatFullTime(commit.timestamp)">
              🕐 {{ formatRelativeTime(commit.timestamp) }}
            </span>
          </div>
        </div>

        <!-- 提交哈希 -->
        <div class="commit-hash-wrapper">
          <code
            class="commit-hash"
            @click.stop="copyHash(commit.hash)"
            :title="copySuccess === commit.hash ? '已复制!' : '点击复制'"
          >
            {{ commit.hash.substring(0, 7) }}
          </code>
        </div>
      </div>
    </div>

    <!-- 分页 -->
    <div v-if="total > limit" class="pagination">
      <button
        class="page-btn"
        :disabled="offset === 0"
        @click="handlePrevPage"
      >
        ← 上一页
      </button>
      <span class="page-info">
        {{ offset + 1 }} - {{ Math.min(offset + limit, total) }} / {{ total }}
      </span>
      <button
        class="page-btn"
        :disabled="offset + limit >= total"
        @click="handleNextPage"
      >
        下一页 →
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue';
import { repositoryBrowserApi } from '@/utils/api';
import { ExceptionHandler } from '@/utils/exceptionHandler';

/**
 * 提交记录接口
 */
interface Commit {
  hash: string;
  message: string;
  author: string;
  author_email: string;
  timestamp: number;
  parents: string[];
}

/**
 * 组件属性定义
 */
interface CommitHistoryProps {
  /** 仓库ID */
  repoId: number;
  /** 分支名或提交SHA */
  refName?: string;
  /** 每页数量 */
  limit?: number;
}

const props = withDefaults(defineProps<CommitHistoryProps>(), {
  refName: 'HEAD',
  limit: 20
});

/**
 * 组件事件定义
 */
interface CommitHistoryEmits {
  /** 选择提交时触发 */
  (e: 'select', commit: Commit & { repoId: number }): void;
}

const emit = defineEmits<CommitHistoryEmits>();

// 状态
const commits = ref<Commit[]>([]);
const total = ref<number>(0);
const offset = ref<number>(0);
const isLoading = ref<boolean>(false);
const error = ref<string>('');
const selectedHash = ref<string>('');
const copySuccess = ref<string>('');

/**
 * 加载提交历史
 */
const loadCommits = async () => {
  isLoading.value = true;
  error.value = '';

  try {
    const response = await repositoryBrowserApi.getCommits(
      props.repoId,
      props.refName,
      props.limit,
      offset.value
    );

    if (response.success && response.data) {
      commits.value = response.data.commits;
      total.value = response.data.total;
    } else if (response.error) {
      error.value = response.error;
    }
  } catch (err) {
    console.error('加载提交历史失败:', err);
    error.value = '加载失败，请重试';
    ExceptionHandler.globalErrorHandler(err);
  } finally {
    isLoading.value = false;
  }
};

/**
 * 格式化相对时间
 * @param timestamp Unix 时间戳
 */
const formatRelativeTime = (timestamp: number): string => {
  const now = Date.now() / 1000;
  const diff = now - timestamp;

  if (diff < 60) {
    return '刚刚';
  } else if (diff < 3600) {
    return `${Math.floor(diff / 60)} 分钟前`;
  } else if (diff < 86400) {
    return `${Math.floor(diff / 3600)} 小时前`;
  } else if (diff < 604800) {
    return `${Math.floor(diff / 86400)} 天前`;
  } else if (diff < 2592000) {
    return `${Math.floor(diff / 604800)} 周前`;
  } else if (diff < 31536000) {
    return `${Math.floor(diff / 2592000)} 个月前`;
  } else {
    return `${Math.floor(diff / 31536000)} 年前`;
  }
};

/**
 * 格式化完整时间
 * @param timestamp Unix 时间戳
 */
const formatFullTime = (timestamp: number): string => {
  const date = new Date(timestamp * 1000);
  return date.toLocaleString();
};

/**
 * 处理提交点击
 * @param commit 提交记录
 */
const handleCommitClick = (commit: Commit) => {
  selectedHash.value = commit.hash;
  emit('select', { ...commit, repoId: props.repoId });
};

/**
 * 复制提交哈希
 * @param hash 提交哈希
 */
const copyHash = async (hash: string) => {
  try {
    await navigator.clipboard.writeText(hash);
    copySuccess.value = hash;
    setTimeout(() => {
      copySuccess.value = '';
    }, 2000);
  } catch (err) {
    console.error('复制失败:', err);
    ExceptionHandler.showErrorMessage(new Error('复制到剪贴板失败'));
  }
};

/**
 * 上一页
 */
const handlePrevPage = () => {
  if (offset.value >= props.limit) {
    offset.value -= props.limit;
    loadCommits();
  }
};

/**
 * 下一页
 */
const handleNextPage = () => {
  if (offset.value + props.limit < total.value) {
    offset.value += props.limit;
    loadCommits();
  }
};

// 监听属性变化，重新加载
watch(
  () => [props.repoId, props.refName],
  () => {
    offset.value = 0;
    loadCommits();
  },
  { immediate: true }
);

// 组件挂载时加载
onMounted(() => {
  loadCommits();
});
</script>

<style scoped>
.commit-history-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  background-color: var(--color-bg-secondary);
  border-radius: var(--radius-md);
  overflow: hidden;
}

/* 头部 */
.history-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1rem;
  background-color: var(--color-bg-tertiary);
  border-bottom: 1px solid var(--color-border);
}

.history-title {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  color: var(--color-text-primary);
}

.history-stats {
  font-size: 0.85rem;
  color: var(--color-text-secondary);
}

/* 状态提示 */
.loading-state,
.error-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  padding: 2rem;
  color: var(--color-text-secondary);
}

.loading-icon,
.error-icon,
.empty-icon {
  font-size: 2.5rem;
  margin-bottom: 0.75rem;
}

.loading-text,
.error-text,
.empty-text {
  font-size: 0.95rem;
}

/* 错误状态 */
.error-state {
  color: var(--color-error);
}

.retry-btn {
  margin-top: 1rem;
  padding: 0.5rem 1rem;
  background-color: var(--color-primary);
  color: white;
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: opacity var(--transition-fast);
}

.retry-btn:hover {
  opacity: 0.9;
}

/* 提交列表 */
.commit-list {
  flex: 1;
  overflow-y: auto;
  padding: 0.5rem;
}

.commit-item {
  display: flex;
  align-items: flex-start;
  padding: 0.75rem;
  margin-bottom: 0.5rem;
  background-color: var(--color-bg-primary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.commit-item:hover {
  border-color: var(--color-primary);
  box-shadow: var(--shadow-sm);
}

.commit-item.selected {
  border-color: var(--color-primary);
  background-color: var(--color-primary-light);
}

/* 提交主信息 */
.commit-main {
  flex: 1;
  min-width: 0;
  margin-right: 0.75rem;
}

.commit-message {
  font-weight: 500;
  color: var(--color-text-primary);
  margin-bottom: 0.4rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.commit-meta {
  display: flex;
  gap: 1rem;
  font-size: 0.8rem;
  color: var(--color-text-secondary);
}

.commit-author,
.commit-time {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

/* 提交哈希 */
.commit-hash-wrapper {
  flex-shrink: 0;
}

.commit-hash {
  display: inline-block;
  padding: 0.25rem 0.5rem;
  background-color: var(--color-bg-tertiary);
  border-radius: var(--radius-sm);
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 0.8rem;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.commit-hash:hover {
  background-color: var(--color-primary);
  color: white;
}

/* 分页 */
.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  padding: 0.75rem;
  background-color: var(--color-bg-tertiary);
  border-top: 1px solid var(--color-border);
}

.page-btn {
  padding: 0.4rem 0.8rem;
  background-color: var(--color-bg-primary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 0.85rem;
  transition: all var(--transition-fast);
}

.page-btn:hover:not(:disabled) {
  border-color: var(--color-primary);
  background-color: var(--color-primary-light);
}

.page-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.page-info {
  font-size: 0.85rem;
  color: var(--color-text-secondary);
}

/* 滚动条样式 */
.commit-list::-webkit-scrollbar {
  width: 6px;
}

.commit-list::-webkit-scrollbar-track {
  background: transparent;
}

.commit-list::-webkit-scrollbar-thumb {
  background: var(--color-border);
  border-radius: 3px;
}

.commit-list::-webkit-scrollbar-thumb:hover {
  background: var(--color-border-hover);
}
</style>
