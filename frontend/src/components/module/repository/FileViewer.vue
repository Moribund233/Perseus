<!--
  仓库模块组件: 文件查看器
  用途: 展示文件内容，支持语法高亮和二进制文件提示
  调用: <FileViewer :repo-id="1" :path="'src/app.py'" :ref-name="'master'" />
  特性:
    - 语法高亮（基于文件扩展名）
    - 二进制文件检测和提示
    - 文件大小显示
    - 行号显示
    - 代码复制功能
-->
<template>
  <div class="file-viewer-container">
    <!-- 文件头部信息 -->
    <div class="file-header">
      <div class="file-info">
        <span class="file-icon">{{ fileIcon }}</span>
        <span class="file-name">{{ fileName }}</span>
        <span v-if="fileSize > 0" class="file-size">({{ formattedSize }})</span>
      </div>
      <div class="file-actions">
        <button
          v-if="!isBinary && content"
          class="action-btn"
          @click="copyContent"
          :title="copySuccess ? '已复制!' : '复制内容'"
        >
          {{ copySuccess ? '✅' : '📋' }}
        </button>
        <button class="action-btn" @click="loadContent" title="刷新">
          🔄
        </button>
      </div>
    </div>

    <!-- 加载状态 -->
    <div v-if="isLoading" class="loading-state">
      <span class="loading-icon">⏳</span>
      <span class="loading-text">加载文件内容...</span>
    </div>

    <!-- 错误状态 -->
    <div v-else-if="error" class="error-state">
      <span class="error-icon">⚠️</span>
      <span class="error-text">{{ error }}</span>
      <button class="retry-btn" @click="loadContent">重试</button>
    </div>

    <!-- 二进制文件提示 -->
    <div v-else-if="isBinary" class="binary-state">
      <span class="binary-icon">📦</span>
      <span class="binary-text">二进制文件</span>
      <span class="binary-hint">该文件无法直接查看</span>
    </div>

    <!-- 空文件提示 -->
    <div v-else-if="!content" class="empty-state">
      <span class="empty-icon">📄</span>
      <span class="empty-text">空文件</span>
    </div>

    <!-- 文件内容 -->
    <div v-else class="file-content-wrapper">
      <div class="line-numbers">
        <div
          v-for="lineNum in lineCount"
          :key="lineNum"
          class="line-number"
        >
          {{ lineNum }}
        </div>
      </div>
      <pre class="file-content"><code :class="languageClass" v-html="highlightedContent"></code></pre>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue';
import { repositoryBrowserApi } from '@/utils/api';
import { ExceptionHandler } from '@/utils/exceptionHandler';

/**
 * 组件属性定义
 */
interface FileViewerProps {
  /** 仓库ID */
  repoId: number;
  /** 文件路径 */
  path: string;
  /** 分支名或提交SHA */
  refName?: string;
}

const props = withDefaults(defineProps<FileViewerProps>(), {
  refName: 'HEAD'
});

// 状态
const content = ref<string>('');
const fileSize = ref<number>(0);
const isBinary = ref<boolean>(false);
const isLoading = ref<boolean>(false);
const error = ref<string>('');
const copySuccess = ref<boolean>(false);

/**
 * 文件名
 */
const fileName = computed(() => {
  return props.path.split('/').pop() || props.path;
});

/**
 * 文件图标
 */
const fileIcon = computed(() => {
  const ext = fileName.value.split('.').pop()?.toLowerCase() || '';
  const iconMap: Record<string, string> = {
    'py': '🐍',
    'js': '📜',
    'ts': '📘',
    'vue': '🟢',
    'html': '🌐',
    'css': '🎨',
    'json': '📋',
    'md': '📝',
    'txt': '📄',
    'yml': '⚙️',
    'yaml': '⚙️',
    'toml': '⚙️',
    'ini': '⚙️',
    'sh': '⌨️',
    'bat': '⌨️',
    'ps1': '⌨️',
    'sql': '🗄️',
    'jpg': '🖼️',
    'jpeg': '🖼️',
    'png': '🖼️',
    'gif': '🖼️',
    'svg': '🖼️',
    'pdf': '📕',
    'zip': '📦',
    'tar': '📦',
    'gz': '📦',
    '7z': '📦',
    'exe': '⚡',
    'dll': '⚙️',
    'gitignore': '🙈',
    'dockerfile': '🐳',
    'makefile': '🔧'
  };
  return iconMap[ext] || '📄';
});

/**
 * 格式化文件大小
 */
const formattedSize = computed(() => {
  const size = fileSize.value;
  if (size < 1024) {
    return `${size} B`;
  } else if (size < 1024 * 1024) {
    return `${(size / 1024).toFixed(2)} KB`;
  } else {
    return `${(size / (1024 * 1024)).toFixed(2)} MB`;
  }
});

/**
 * 行数
 */
const lineCount = computed(() => {
  return content.value.split('\n').length;
});

/**
 * 代码语言类名
 */
const languageClass = computed(() => {
  const ext = fileName.value.split('.').pop()?.toLowerCase() || '';
  const langMap: Record<string, string> = {
    'py': 'language-python',
    'js': 'language-javascript',
    'ts': 'language-typescript',
    'vue': 'language-vue',
    'html': 'language-html',
    'css': 'language-css',
    'json': 'language-json',
    'md': 'language-markdown',
    'yml': 'language-yaml',
    'yaml': 'language-yaml',
    'toml': 'language-toml',
    'sh': 'language-bash',
    'sql': 'language-sql'
  };
  return langMap[ext] || 'language-plaintext';
});

/**
 * 高亮后的内容（简单的 HTML 转义）
 */
const highlightedContent = computed(() => {
  return escapeHtml(content.value);
});

/**
 * HTML 转义
 * @param text 文本
 */
const escapeHtml = (text: string): string => {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
};

/**
 * 加载文件内容
 */
const loadContent = async () => {
  if (!props.path) {
    error.value = '未指定文件路径';
    return;
  }

  isLoading.value = true;
  error.value = '';
  content.value = '';
  fileSize.value = 0;
  isBinary.value = false;

  try {
    const response = await repositoryBrowserApi.getBlob(
      props.repoId,
      props.path,
      props.refName
    );

    if (response.success && response.data) {
      content.value = response.data.content;
      fileSize.value = response.data.size;
      isBinary.value = response.data.is_binary;
    } else if (response.error) {
      error.value = response.error;
    }
  } catch (err) {
    console.error('加载文件内容失败:', err);
    error.value = '加载失败，请重试';
    ExceptionHandler.globalErrorHandler(err);
  } finally {
    isLoading.value = false;
  }
};

/**
 * 复制内容到剪贴板
 */
const copyContent = async () => {
  try {
    await navigator.clipboard.writeText(content.value);
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
  () => [props.repoId, props.path, props.refName],
  () => {
    loadContent();
  },
  { immediate: true }
);

// 组件挂载时加载
onMounted(() => {
  loadContent();
});
</script>

<style scoped>
.file-viewer-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  background-color: var(--color-bg-secondary);
  border-radius: var(--radius-md);
  overflow: hidden;
}

/* 文件头部 */
.file-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1rem;
  background-color: var(--color-bg-tertiary);
  border-bottom: 1px solid var(--color-border);
}

.file-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  overflow: hidden;
}

.file-icon {
  font-size: 1.2rem;
}

.file-name {
  font-weight: 500;
  color: var(--color-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-size {
  font-size: 0.8rem;
  color: var(--color-text-secondary);
}

.file-actions {
  display: flex;
  gap: 0.5rem;
}

.action-btn {
  padding: 0.4rem 0.6rem;
  background-color: transparent;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 1rem;
  transition: all var(--transition-fast);
}

.action-btn:hover {
  background-color: var(--color-hover);
  border-color: var(--color-primary);
}

/* 状态提示 */
.loading-state,
.error-state,
.empty-state,
.binary-state {
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
.empty-icon,
.binary-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.loading-text,
.error-text,
.empty-text,
.binary-text {
  font-size: 1rem;
  margin-bottom: 0.5rem;
}

.binary-hint {
  font-size: 0.85rem;
  color: var(--color-text-tertiary);
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
}

/* 文件内容 */
.file-content-wrapper {
  display: flex;
  flex: 1;
  overflow: auto;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 0.9rem;
  line-height: 1.5;
}

.line-numbers {
  flex-shrink: 0;
  padding: 1rem 0.5rem;
  background-color: var(--color-bg-tertiary);
  border-right: 1px solid var(--color-border);
  text-align: right;
  user-select: none;
}

.line-number {
  color: var(--color-text-tertiary);
  min-width: 2rem;
  padding: 0 0.5rem;
}

.file-content {
  flex: 1;
  margin: 0;
  padding: 1rem;
  background-color: transparent;
  overflow: visible;
  white-space: pre;
  word-wrap: normal;
}

.file-content code {
  display: block;
  color: var(--color-text-primary);
}

/* 滚动条样式 */
.file-content-wrapper::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

.file-content-wrapper::-webkit-scrollbar-track {
  background: var(--color-bg-tertiary);
}

.file-content-wrapper::-webkit-scrollbar-thumb {
  background: var(--color-border);
  border-radius: 4px;
}

.file-content-wrapper::-webkit-scrollbar-thumb:hover {
  background: var(--color-border-hover);
}
</style>
