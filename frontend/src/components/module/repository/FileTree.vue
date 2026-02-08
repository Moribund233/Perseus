<!--
  仓库模块组件: 文件树
  用途: 展示仓库文件结构，支持目录展开/折叠、文件选择
  调用: <FileTree :repo-id="1" :ref-name="'master'" @select="handleSelect" />
  特性:
    - 树形结构展示文件和目录
    - 支持懒加载（点击目录展开时加载子目录）
    - 文件/目录图标区分
    - 选中状态高亮
-->
<template>
  <div class="file-tree-container">
    <!-- 加载状态 -->
    <div v-if="isLoading" class="loading-state">
      <span class="loading-icon">⏳</span>
      <span class="loading-text">加载中...</span>
    </div>

    <!-- 错误状态 -->
    <div v-else-if="error" class="error-state">
      <span class="error-icon">⚠️</span>
      <span class="error-text">{{ error }}</span>
      <button class="retry-btn" @click="loadTree">重试</button>
    </div>

    <!-- 空状态 -->
    <div v-else-if="entries.length === 0" class="empty-state">
      <span class="empty-icon">📂</span>
      <span class="empty-text">空目录</span>
    </div>

    <!-- 文件树列表 -->
    <div v-else class="file-tree">
      <div
        v-for="entry in sortedEntries"
        :key="entry.path"
        :class="['file-tree-item', { 'selected': selectedPath === entry.path }]"
        @click="handleEntryClick(entry)"
      >
        <!-- 目录项 -->
        <template v-if="entry.type === 'tree'">
          <span class="entry-icon">
            {{ isExpanded(entry.path) ? '📂' : '📁' }}
          </span>
          <span class="entry-name">{{ entry.name }}</span>
          <span class="expand-icon">
            {{ isExpanded(entry.path) ? '▼' : '▶' }}
          </span>
        </template>

        <!-- 文件项 -->
        <template v-else>
          <span class="entry-icon">{{ getFileIcon(entry.name) }}</span>
          <span class="entry-name">{{ entry.name }}</span>
        </template>

        <!-- 子目录（递归） -->
        <div
          v-if="entry.type === 'tree' && isExpanded(entry.path)"
          class="file-tree-children"
        >
          <FileTree
            :repo-id="repoId"
            :ref-name="refName"
            :path="entry.path"
            :parent-expanded="true"
            @select="$emit('select', $event)"
          />
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
 * 文件树条目接口
 */
interface TreeEntry {
  name: string;
  type: 'blob' | 'tree';
  path: string;
}

/**
 * 组件属性定义
 */
interface FileTreeProps {
  /** 仓库ID */
  repoId: number;
  /** 分支名或提交SHA */
  refName?: string;
  /** 当前路径 */
  path?: string;
  /** 父级是否展开（用于递归组件） */
  parentExpanded?: boolean;
}

const props = withDefaults(defineProps<FileTreeProps>(), {
  refName: 'HEAD',
  path: '',
  parentExpanded: false
});

/**
 * 组件事件定义
 */
interface FileTreeEmits {
  /** 选择文件或目录时触发 */
  (e: 'select', entry: TreeEntry & { repoId: number; refName: string }): void;
}

const emit = defineEmits<FileTreeEmits>();

// 状态
const entries = ref<TreeEntry[]>([]);
const isLoading = ref(false);
const error = ref<string>('');
const selectedPath = ref<string>('');
const expandedPaths = ref<Set<string>>(new Set());

/**
 * 排序后的条目（目录在前，文件在后，按名称排序）
 */
const sortedEntries = computed(() => {
  return [...entries.value].sort((a, b) => {
    // 目录排在文件前面
    if (a.type !== b.type) {
      return a.type === 'tree' ? -1 : 1;
    }
    // 按名称排序
    return a.name.localeCompare(b.name);
  });
});

/**
 * 判断路径是否已展开
 * @param path 路径
 */
const isExpanded = (path: string): boolean => {
  return expandedPaths.value.has(path);
};

/**
 * 切换目录展开状态
 * @param path 路径
 */
const toggleExpand = (path: string) => {
  if (expandedPaths.value.has(path)) {
    expandedPaths.value.delete(path);
  } else {
    expandedPaths.value.add(path);
  }
};

/**
 * 获取文件图标
 * @param filename 文件名
 */
const getFileIcon = (filename: string): string => {
  const ext = filename.split('.').pop()?.toLowerCase() || '';
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
};

/**
 * 处理条目点击
 * @param entry 条目
 */
const handleEntryClick = (entry: TreeEntry) => {
  selectedPath.value = entry.path;

  if (entry.type === 'tree') {
    // 点击目录，切换展开状态
    toggleExpand(entry.path);
  }

  // 触发选择事件
  emit('select', {
    ...entry,
    repoId: props.repoId,
    refName: props.refName
  });
};

/**
 * 加载文件树
 */
const loadTree = async () => {
  if (!props.parentExpanded && props.path !== '') {
    // 如果父级未展开且不是根目录，不加载
    return;
  }

  isLoading.value = true;
  error.value = '';

  try {
    const response = await repositoryBrowserApi.getTree(
      props.repoId,
      props.refName,
      props.path
    );

    if (response.success && response.data) {
      entries.value = response.data.entries;
    } else if (response.error) {
      error.value = response.error;
    }
  } catch (err) {
    console.error('加载文件树失败:', err);
    error.value = '加载失败，请重试';
    ExceptionHandler.globalErrorHandler(err);
  } finally {
    isLoading.value = false;
  }
};

// 监听属性变化，重新加载
watch(
  () => [props.repoId, props.refName, props.path],
  () => {
    loadTree();
  },
  { immediate: true }
);

// 组件挂载时加载
onMounted(() => {
  loadTree();
});
</script>

<style scoped>
.file-tree-container {
  width: 100%;
  height: 100%;
  overflow: auto;
}

/* 加载状态 */
.loading-state,
.error-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  color: var(--color-text-secondary);
}

.loading-icon,
.error-icon,
.empty-icon {
  font-size: 2rem;
  margin-bottom: 0.5rem;
}

.loading-text,
.error-text,
.empty-text {
  font-size: 0.9rem;
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

/* 文件树 */
.file-tree {
  padding: 0.5rem 0;
}

.file-tree-item {
  display: flex;
  align-items: center;
  padding: 0.4rem 0.75rem;
  cursor: pointer;
  transition: background-color var(--transition-fast);
  border-radius: var(--radius-sm);
  margin: 0 0.5rem;
  flex-wrap: wrap;
}

.file-tree-item:hover {
  background-color: var(--color-hover);
}

.file-tree-item.selected {
  background-color: var(--color-primary-light);
}

.entry-icon {
  margin-right: 0.5rem;
  font-size: 1rem;
  width: 1.2rem;
  text-align: center;
}

.entry-name {
  flex: 1;
  font-size: 0.9rem;
  color: var(--color-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.expand-icon {
  font-size: 0.7rem;
  color: var(--color-text-secondary);
  margin-left: 0.5rem;
}

/* 子目录 */
.file-tree-children {
  width: 100%;
  margin-top: 0.25rem;
  padding-left: 1rem;
  border-left: 1px solid var(--color-border-light);
}
</style>
