<!--
  仓库模块组件: 代码对比查看器
  用途: 展示两个提交之间的代码差异
  调用: <DiffViewer :repo-id="1" head="HEAD" base="HEAD~1" />
  特性:
    - 文件变更列表
    - 行级差异展示
    - 添加/删除行高亮
    - 文件统计信息
-->
<template>
  <div class="diff-viewer-container">
    <!-- 头部信息 -->
    <div class="diff-header">
      <div class="diff-title">
        <span class="title-icon">🔍</span>
        <span class="title-text">代码对比</span>
      </div>
      <div class="diff-refs" v-if="diffData">
        <span class="ref-badge base" :title="diffData.base">
          {{ formatRef(diffData.base) }}
        </span>
        <span class="ref-arrow">→</span>
        <span class="ref-badge head" :title="diffData.head">
          {{ formatRef(diffData.head) }}
        </span>
      </div>
      <div class="diff-stats" v-if="diffData">
        <span class="stat-item additions">
          +{{ diffData.total_additions }}
        </span>
        <span class="stat-item deletions">
          -{{ diffData.total_deletions }}
        </span>
      </div>
    </div>

    <!-- 加载状态 -->
    <div v-if="isLoading" class="loading-state">
      <span class="loading-icon">⏳</span>
      <span class="loading-text">加载代码对比...</span>
    </div>

    <!-- 错误状态 -->
    <div v-else-if="error" class="error-state">
      <span class="error-icon">⚠️</span>
      <span class="error-text">{{ error }}</span>
      <button class="retry-btn" @click="loadDiff">重试</button>
    </div>

    <!-- 无变更 -->
    <div v-else-if="diffData && diffData.files.length === 0" class="empty-state">
      <span class="empty-icon">✅</span>
      <span class="empty-text">没有代码变更</span>
    </div>

    <!-- 差异内容 -->
    <div v-else-if="diffData" class="diff-content">
      <!-- 文件列表 -->
      <div class="file-list">
        <div
          v-for="file in diffData.files"
          :key="file.path"
          :class="['file-item', { 'active': selectedFile === file.path }]"
          @click="selectedFile = file.path"
        >
          <span class="file-status" :class="file.status">
            {{ getStatusIcon(file.status) }}
          </span>
          <span class="file-path">{{ file.path }}</span>
          <span class="file-changes">
            <span class="change-additions" v-if="file.additions > 0">+{{ file.additions }}</span>
            <span class="change-deletions" v-if="file.deletions > 0">-{{ file.deletions }}</span>
          </span>
        </div>
      </div>

      <!-- 差异详情 -->
      <div class="diff-details">
        <div v-if="selectedFileData" class="diff-file-content">
          <div class="file-header-bar">
            <span class="file-path">{{ selectedFileData.path }}</span>
            <button class="copy-btn" @click="copyDiff" :title="copySuccess ? '已复制!' : '复制差异'">
              {{ copySuccess ? '✅' : '📋' }}
            </button>
          </div>
          <div class="diff-lines">
            <div
              v-for="(line, index) in parsedDiffLines"
              :key="index"
              :class="['diff-line', line.type]"
            >
              <span class="line-number old">{{ line.oldNumber || '' }}</span>
              <span class="line-number new">{{ line.newNumber || '' }}</span>
              <span class="line-marker">{{ line.marker }}</span>
              <span class="line-content">{{ line.content }}</span>
            </div>
          </div>
        </div>
        <div v-else class="no-selection">
          <span class="no-selection-icon">👈</span>
          <span class="no-selection-text">选择左侧文件查看差异</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue';
import { repositoryBrowserApi } from '@/utils/api';
import { ExceptionHandler } from '@/utils/exceptionHandler';

/**
 * 文件变更接口
 */
interface FileChange {
  path: string;
  status: 'added' | 'modified' | 'deleted' | 'renamed';
  additions: number;
  deletions: number;
  diff: string;
}

/**
 * 差异数据接口
 */
interface DiffData {
  head: string;
  base: string;
  files: FileChange[];
  total_additions: number;
  total_deletions: number;
}

/**
 * 解析后的差异行
 */
interface DiffLine {
  type: 'header' | 'addition' | 'deletion' | 'context' | 'info';
  oldNumber?: number;
  newNumber?: number;
  marker: string;
  content: string;
}

/**
 * 组件属性定义
 */
interface DiffViewerProps {
  /** 仓库ID */
  repoId: number;
  /** 目标分支或提交 */
  head?: string;
  /** 对比基准分支或提交 */
  base?: string;
}

const props = withDefaults(defineProps<DiffViewerProps>(), {
  head: 'HEAD'
});

// 状态
const diffData = ref<DiffData | null>(null);
const isLoading = ref<boolean>(false);
const error = ref<string>('');
const selectedFile = ref<string>('');
const copySuccess = ref<boolean>(false);

/**
 * 选中的文件数据
 */
const selectedFileData = computed(() => {
  if (!diffData.value || !selectedFile.value) return null;
  return diffData.value.files.find(f => f.path === selectedFile.value) || null;
});

/**
 * 解析后的差异行
 */
const parsedDiffLines = computed((): DiffLine[] => {
  if (!selectedFileData.value) return [];

  const lines: DiffLine[] = [];
  const diffLines = selectedFileData.value.diff.split('\n');
  let oldLineNum = 0;
  let newLineNum = 0;

  for (const line of diffLines) {
    if (line.startsWith('@@')) {
      // 解析 @@ 行号信息
      const match = line.match(/@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@/);
      if (match) {
        oldLineNum = parseInt(match[1]) - 1;
        newLineNum = parseInt(match[2]) - 1;
      }
      lines.push({
        type: 'header',
        marker: '',
        content: line
      });
    } else if (line.startsWith('+')) {
      newLineNum++;
      lines.push({
        type: 'addition',
        newNumber: newLineNum,
        marker: '+',
        content: line.substring(1)
      });
    } else if (line.startsWith('-')) {
      oldLineNum++;
      lines.push({
        type: 'deletion',
        oldNumber: oldLineNum,
        marker: '-',
        content: line.substring(1)
      });
    } else if (line.startsWith('\\')) {
      lines.push({
        type: 'info',
        marker: '',
        content: line
      });
    } else {
      oldLineNum++;
      newLineNum++;
      lines.push({
        type: 'context',
        oldNumber: oldLineNum,
        newNumber: newLineNum,
        marker: ' ',
        content: line
      });
    }
  }

  return lines;
});

/**
 * 格式化引用名称
 * @param ref 引用
 */
const formatRef = (ref: string): string => {
  if (ref.length > 12) {
    return ref.substring(0, 7) + '...';
  }
  return ref;
};

/**
 * 获取状态图标
 * @param status 状态
 */
const getStatusIcon = (status: string): string => {
  const icons: Record<string, string> = {
    'added': '➕',
    'modified': '📝',
    'deleted': '➖',
    'renamed': '📛'
  };
  return icons[status] || '❓';
};

/**
 * 加载代码对比
 */
const loadDiff = async () => {
  isLoading.value = true;
  error.value = '';
  diffData.value = null;
  selectedFile.value = '';

  try {
    const response = await repositoryBrowserApi.getDiff(
      props.repoId,
      props.head,
      props.base
    );

    if (response.success && response.data) {
      diffData.value = response.data;
      // 默认选中第一个文件
      if (response.data.files.length > 0) {
        selectedFile.value = response.data.files[0].path;
      }
    } else if (response.error) {
      error.value = response.error;
    }
  } catch (err) {
    console.error('加载代码对比失败:', err);
    error.value = '加载失败，请重试';
    ExceptionHandler.globalErrorHandler(err);
  } finally {
    isLoading.value = false;
  }
};

/**
 * 复制差异内容
 */
const copyDiff = async () => {
  if (!selectedFileData.value) return;

  try {
    await navigator.clipboard.writeText(selectedFileData.value.diff);
    copySuccess.value = true;
    setTimeout(() => {
      copySuccess.value = false;
    }, 2000);
  } catch (err) {
    console.error('复制失败:', err);
    ExceptionHandler.showErrorMessage(new Error('复制到剪贴板失败'));
  }
};

// 监听属性变化，重新加载
watch(
  () => [props.repoId, props.head, props.base],
  () => {
    loadDiff();
  },
  { immediate: true }
);

// 组件挂载时加载
onMounted(() => {
  loadDiff();
});
</script>

<style scoped>
.diff-viewer-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  background-color: var(--color-bg-secondary);
  border-radius: var(--radius-md);
  overflow: hidden;
}

/* 头部 */
.diff-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1rem;
  background-color: var(--color-bg-tertiary);
  border-bottom: 1px solid var(--color-border);
  flex-wrap: wrap;
  gap: 0.5rem;
}

.diff-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 600;
  color: var(--color-text-primary);
}

.title-icon {
  font-size: 1.1rem;
}

.diff-refs {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.ref-badge {
  padding: 0.25rem 0.5rem;
  border-radius: var(--radius-sm);
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 0.8rem;
}

.ref-badge.base {
  background-color: var(--color-bg-primary);
  border: 1px solid var(--color-border);
  color: var(--color-text-secondary);
}

.ref-badge.head {
  background-color: var(--color-primary-light);
  border: 1px solid var(--color-primary);
  color: var(--color-primary);
}

.ref-arrow {
  color: var(--color-text-secondary);
}

.diff-stats {
  display: flex;
  gap: 0.75rem;
}

.stat-item {
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 0.9rem;
  font-weight: 600;
}

.stat-item.additions {
  color: var(--color-success);
}

.stat-item.deletions {
  color: var(--color-error);
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
}

/* 差异内容 */
.diff-content {
  display: flex;
  flex: 1;
  overflow: hidden;
}

/* 文件列表 */
.file-list {
  width: 280px;
  flex-shrink: 0;
  border-right: 1px solid var(--color-border);
  overflow-y: auto;
  background-color: var(--color-bg-tertiary);
}

.file-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.6rem 0.75rem;
  cursor: pointer;
  transition: background-color var(--transition-fast);
  border-bottom: 1px solid var(--color-border-light);
}

.file-item:hover {
  background-color: var(--color-hover);
}

.file-item.active {
  background-color: var(--color-primary-light);
  border-left: 3px solid var(--color-primary);
}

.file-status {
  font-size: 0.9rem;
}

.file-path {
  flex: 1;
  font-size: 0.85rem;
  color: var(--color-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-changes {
  display: flex;
  gap: 0.4rem;
  font-size: 0.75rem;
  font-family: 'Consolas', 'Monaco', monospace;
}

.change-additions {
  color: var(--color-success);
}

.change-deletions {
  color: var(--color-error);
}

/* 差异详情 */
.diff-details {
  flex: 1;
  overflow: auto;
  background-color: var(--color-bg-primary);
}

.no-selection {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--color-text-secondary);
}

.no-selection-icon {
  font-size: 2rem;
  margin-bottom: 0.5rem;
}

.diff-file-content {
  min-height: 100%;
}

.file-header-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1rem;
  background-color: var(--color-bg-tertiary);
  border-bottom: 1px solid var(--color-border);
  position: sticky;
  top: 0;
  z-index: 10;
}

.file-header-bar .file-path {
  font-weight: 500;
}

.copy-btn {
  padding: 0.3rem 0.5rem;
  background-color: transparent;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 0.9rem;
  transition: all var(--transition-fast);
}

.copy-btn:hover {
  background-color: var(--color-hover);
  border-color: var(--color-primary);
}

/* 差异行 */
.diff-lines {
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 0.85rem;
  line-height: 1.5;
}

.diff-line {
  display: flex;
  padding: 0.1rem 0;
  white-space: pre;
}

.diff-line:hover {
  filter: brightness(0.98);
}

.line-number {
  width: 3rem;
  text-align: right;
  padding: 0 0.5rem;
  color: var(--color-text-tertiary);
  user-select: none;
  flex-shrink: 0;
}

.line-marker {
  width: 1rem;
  text-align: center;
  user-select: none;
  flex-shrink: 0;
}

.line-content {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 行类型样式 */
.diff-line.header {
  background-color: var(--color-bg-tertiary);
  color: var(--color-text-secondary);
}

.diff-line.addition {
  background-color: rgba(40, 167, 69, 0.1);
}

.diff-line.addition .line-marker {
  color: var(--color-success);
}

.diff-line.deletion {
  background-color: rgba(220, 53, 69, 0.1);
}

.diff-line.deletion .line-marker {
  color: var(--color-error);
}

.diff-line.context {
  background-color: transparent;
}

.diff-line.info {
  background-color: var(--color-bg-tertiary);
  color: var(--color-text-secondary);
}

/* 滚动条样式 */
.file-list::-webkit-scrollbar,
.diff-details::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

.file-list::-webkit-scrollbar-track,
.diff-details::-webkit-scrollbar-track {
  background: transparent;
}

.file-list::-webkit-scrollbar-thumb,
.diff-details::-webkit-scrollbar-thumb {
  background: var(--color-border);
  border-radius: 3px;
}

.file-list::-webkit-scrollbar-thumb:hover,
.diff-details::-webkit-scrollbar-thumb:hover {
  background: var(--color-border-hover);
}
</style>
