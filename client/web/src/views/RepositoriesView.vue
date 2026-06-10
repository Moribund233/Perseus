<script setup lang="ts">
/**
 * 仓库列表页面
 * 展示用户的所有仓库，支持筛选、排序和搜索
 */
import { ref, computed } from 'vue'
import SidebarLayout from '@/components/layouts/SidebarLayout.vue'
import {
  Collection,
  Search,
  Plus,
  Star,
  ForkSpoon,
  Lock,
  View,
  Filter,
  Sort,
  Grid,
  List as ListIcon,
} from '@element-plus/icons-vue'

/**
 * 视图模式
 */
type ViewMode = 'list' | 'grid'

/**
 * 当前视图模式
 */
const viewMode = ref<ViewMode>('list')

/**
 * 搜索关键词
 */
const searchQuery = ref('')

/**
 * 当前筛选类型
 */
const activeFilter = ref('all')

/**
 * 排序方式
 */
const sortBy = ref('updated')

/**
 * 筛选选项
 */
const filters = [
  { key: 'all', label: '全部', count: 24 },
  { key: 'public', label: '公开', count: 18 },
  { key: 'private', label: '私有', count: 6 },
  { key: 'fork', label: 'Fork', count: 3 },
  { key: 'archived', label: '归档', count: 2 },
]

/**
 * 排序选项
 */
const sortOptions = [
  { key: 'updated', label: '最近更新' },
  { key: 'name', label: '名称' },
  { key: 'stars', label: '星标数' },
  { key: 'forks', label: '分支数' },
  { key: 'created', label: '创建时间' },
]

/**
 * 语言筛选
 */
const selectedLanguages = ref<string[]>([])
const languageOptions = [
  { value: 'TypeScript', label: 'TypeScript', count: 8 },
  { value: 'Python', label: 'Python', count: 6 },
  { value: 'Vue', label: 'Vue', count: 4 },
  { value: 'JavaScript', label: 'JavaScript', count: 3 },
  { value: 'Rust', label: 'Rust', count: 2 },
  { value: 'Go', label: 'Go', count: 1 },
]

/**
 * 仓库列表数据
 */
const repositories = ref([
  {
    id: 1,
    name: 'perseus-core',
    description: 'Perseus 核心代码库 - 高性能、可扩展的代码托管平台核心',
    language: 'TypeScript',
    languageColor: '#3178c6',
    stars: 2847,
    forks: 342,
    issues: 23,
    isPrivate: false,
    isFork: false,
    isArchived: false,
    updatedAt: '2小时前',
    createdAt: '2024-01-15',
    topics: ['git', 'hosting', 'collaboration'],
  },
  {
    id: 2,
    name: 'perseus-web',
    description: 'Perseus Web 客户端 - 基于 Vue3 的现代 Web 界面',
    language: 'Vue',
    languageColor: '#42b883',
    stars: 1523,
    forks: 186,
    issues: 15,
    isPrivate: false,
    isFork: false,
    isArchived: false,
    updatedAt: '5小时前',
    createdAt: '2024-02-20',
    topics: ['vue3', 'typescript', 'ui'],
  },
  {
    id: 3,
    name: 'react-hooks-library',
    description: 'A collection of useful React hooks for modern web development',
    language: 'TypeScript',
    languageColor: '#3178c6',
    stars: 1234,
    forks: 89,
    issues: 8,
    isPrivate: false,
    isFork: false,
    isArchived: false,
    updatedAt: '3天前',
    createdAt: '2024-03-10',
    topics: ['react', 'hooks', 'typescript'],
  },
  {
    id: 4,
    name: 'fastapi-starter',
    description: 'FastAPI project template with best practices and common configurations',
    language: 'Python',
    languageColor: '#3572A5',
    stars: 892,
    forks: 156,
    issues: 12,
    isPrivate: false,
    isFork: false,
    isArchived: false,
    updatedAt: '1周前',
    createdAt: '2024-04-05',
    topics: ['fastapi', 'python', 'template'],
  },
  {
    id: 5,
    name: 'vue-dashboard',
    description: 'Modern admin dashboard built with Vue 3 and Element Plus',
    language: 'Vue',
    languageColor: '#42b883',
    stars: 567,
    forks: 78,
    issues: 5,
    isPrivate: false,
    isFork: false,
    isArchived: false,
    updatedAt: '2周前',
    createdAt: '2024-05-12',
    topics: ['vue3', 'dashboard', 'admin'],
  },
  {
    id: 6,
    name: 'internal-tools',
    description: 'Internal development tools and scripts',
    language: 'Python',
    languageColor: '#3572A5',
    stars: 12,
    forks: 2,
    issues: 3,
    isPrivate: true,
    isFork: false,
    isArchived: false,
    updatedAt: '1个月前',
    createdAt: '2024-06-01',
    topics: ['tools', 'automation'],
  },
  {
    id: 7,
    name: 'microservices-template',
    description: '微服务架构项目模板',
    language: 'TypeScript',
    languageColor: '#3178c6',
    stars: 456,
    forks: 67,
    issues: 9,
    isPrivate: false,
    isFork: false,
    isArchived: false,
    updatedAt: '2个月前',
    createdAt: '2024-07-15',
    topics: ['microservices', 'template', 'docker'],
  },
  {
    id: 8,
    name: 'rust-cli-tools',
    description: 'High-performance CLI tools written in Rust',
    language: 'Rust',
    languageColor: '#dea584',
    stars: 234,
    forks: 23,
    issues: 4,
    isPrivate: false,
    isFork: false,
    isArchived: false,
    updatedAt: '3个月前',
    createdAt: '2024-08-20',
    topics: ['rust', 'cli', 'tools'],
  },
  {
    id: 9,
    name: 'go-api-gateway',
    description: 'Go 微服务 API 网关',
    language: 'Go',
    languageColor: '#00ADD8',
    stars: 189,
    forks: 34,
    issues: 6,
    isPrivate: false,
    isFork: false,
    isArchived: false,
    updatedAt: '3个月前',
    createdAt: '2024-09-01',
    topics: ['go', 'api-gateway', 'microservices'],
  },
  {
    id: 10,
    name: 'legacy-project',
    description: '旧项目归档',
    language: 'JavaScript',
    languageColor: '#f1e05a',
    stars: 5,
    forks: 1,
    issues: 0,
    isPrivate: true,
    isFork: false,
    isArchived: true,
    updatedAt: '6个月前',
    createdAt: '2023-06-01',
    topics: [],
  },
])

/**
 * 筛选后的仓库列表
 */
const filteredRepositories = computed(() => {
  let result = repositories.value

  // 搜索筛选
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(
      repo =>
        repo.name.toLowerCase().includes(query) ||
        repo.description.toLowerCase().includes(query)
    )
  }

  // 类型筛选
  switch (activeFilter.value) {
    case 'public':
      result = result.filter(repo => !repo.isPrivate)
      break
    case 'private':
      result = result.filter(repo => repo.isPrivate)
      break
    case 'fork':
      result = result.filter(repo => repo.isFork)
      break
    case 'archived':
      result = result.filter(repo => repo.isArchived)
      break
  }

  // 语言筛选
  if (selectedLanguages.value.length > 0) {
    result = result.filter(repo => selectedLanguages.value.includes(repo.language))
  }

  // 排序
  switch (sortBy.value) {
    case 'name':
      result = result.sort((a, b) => a.name.localeCompare(b.name))
      break
    case 'stars':
      result = result.sort((a, b) => b.stars - a.stars)
      break
    case 'forks':
      result = result.sort((a, b) => b.forks - a.forks)
      break
    case 'created':
      result = result.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
      break
    default:
      // updated - 默认排序
      break
  }

  return result
})

/**
 * 格式化数字
 * @param num 数字
 * @returns 格式化后的字符串
 */
const formatNumber = (num: number) => {
  if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'k'
  }
  return num.toString()
}

/**
 * 创建新仓库
 */
const createRepository = () => {
  // TODO: 打开创建仓库对话框或跳转到创建页面
  console.log('Creating new repository...')
}
</script>

<template>
  <SidebarLayout>
    <div class="repositories-page">
      <div class="container">
        <!-- 页面头部 -->
        <header class="page-header">
          <div class="header-content">
            <h1 class="page-title">仓库</h1>
            <p class="page-subtitle">管理你的所有代码仓库</p>
          </div>
          <el-button type="primary" :icon="Plus" @click="createRepository">
            创建仓库
          </el-button>
        </header>

        <div class="content-layout">
          <!-- 左侧边栏筛选 -->
          <aside class="filter-sidebar">
            <!-- 类型筛选 -->
            <div class="filter-group">
              <h3 class="filter-title">
                <el-icon><Filter /></el-icon>
                筛选
              </h3>
              <div class="filter-list">
                <button
                  v-for="filter in filters"
                  :key="filter.key"
                  class="filter-item"
                  :class="{ 'is-active': activeFilter === filter.key }"
                  @click="activeFilter = filter.key"
                >
                  <span class="filter-label">{{ filter.label }}</span>
                  <span class="filter-count">{{ filter.count }}</span>
                </button>
              </div>
            </div>

            <!-- 语言筛选 -->
            <div class="filter-group">
              <h3 class="filter-title">语言</h3>
              <div class="language-list">
                <label
                  v-for="lang in languageOptions"
                  :key="lang.value"
                  class="language-item"
                >
                  <el-checkbox v-model="selectedLanguages" :label="lang.value">
                    <span class="language-label">{{ lang.label }}</span>
                    <span class="language-count">{{ lang.count }}</span>
                  </el-checkbox>
                </label>
              </div>
            </div>
          </aside>

          <!-- 主内容区 -->
          <main class="main-content">
            <!-- 工具栏 -->
            <div class="toolbar">
              <div class="toolbar-left">
                <el-input
                  v-model="searchQuery"
                  placeholder="搜索仓库..."
                  :prefix-icon="Search"
                  class="search-input"
                  clearable
                />
              </div>
              <div class="toolbar-right">
                <el-select v-model="sortBy" size="small" class="sort-select">
                  <template #prefix>
                    <el-icon><Sort /></el-icon>
                  </template>
                  <el-option
                    v-for="option in sortOptions"
                    :key="option.key"
                    :label="option.label"
                    :value="option.key"
                  />
                </el-select>
                <div class="view-toggle">
                  <button
                    class="view-btn"
                    :class="{ 'is-active': viewMode === 'list' }"
                    @click="viewMode = 'list'"
                    title="列表视图"
                  >
                    <el-icon><ListIcon /></el-icon>
                  </button>
                  <button
                    class="view-btn"
                    :class="{ 'is-active': viewMode === 'grid' }"
                    @click="viewMode = 'grid'"
                    title="网格视图"
                  >
                    <el-icon><Grid /></el-icon>
                  </button>
                </div>
              </div>
            </div>

            <!-- 结果统计 -->
            <div class="results-info">
              显示 {{ filteredRepositories.length }} 个仓库
            </div>

            <!-- 列表视图 -->
            <div v-if="viewMode === 'list'" class="repositories-list">
              <div
                v-for="repo in filteredRepositories"
                :key="repo.id"
                class="repo-list-item"
              >
                <div class="repo-main">
                  <div class="repo-header">
                    <h3 class="repo-name">
                      <router-link :to="`/code-viewer?repo=${repo.name}`">
                        {{ repo.name }}
                      </router-link>
                      <el-tag
                        v-if="repo.isPrivate"
                        size="small"
                        effect="plain"
                        class="repo-tag"
                      >
                        <el-icon><Lock /></el-icon>
                        私有
                      </el-tag>
                      <el-tag
                        v-if="repo.isArchived"
                        size="small"
                        effect="plain"
                        type="info"
                        class="repo-tag"
                      >
                        已归档
                      </el-tag>
                    </h3>
                  </div>
                  <p class="repo-description">{{ repo.description }}</p>
                  <div class="repo-topics" v-if="repo.topics.length > 0">
                    <el-tag
                      v-for="topic in repo.topics"
                      :key="topic"
                      size="small"
                      effect="plain"
                      class="topic-tag"
                    >
                      {{ topic }}
                    </el-tag>
                  </div>
                  <div class="repo-meta">
                    <span class="meta-item">
                      <span
                        class="language-dot"
                        :style="{ backgroundColor: repo.languageColor }"
                      />
                      {{ repo.language }}
                    </span>
                    <span class="meta-item">
                      <el-icon><Star /></el-icon>
                      {{ formatNumber(repo.stars) }}
                    </span>
                    <span class="meta-item">
                      <el-icon><ForkSpoon /></el-icon>
                      {{ formatNumber(repo.forks) }}
                    </span>
                    <span class="meta-item">更新于 {{ repo.updatedAt }}</span>
                  </div>
                </div>
                <div class="repo-actions">
                  <el-button :icon="Star" size="small">
                    Star
                  </el-button>
                </div>
              </div>
            </div>

            <!-- 网格视图 -->
            <div v-else class="repositories-grid">
              <div
                v-for="repo in filteredRepositories"
                :key="repo.id"
                class="repo-grid-item"
              >
                <div class="repo-card-header">
                  <div class="repo-visibility">
                    <el-icon v-if="repo.isPrivate"><Lock /></el-icon>
                    <el-icon v-else><View /></el-icon>
                  </div>
                  <el-button :icon="Star" size="small" text circle />
                </div>
                <h3 class="repo-card-name">
                  <router-link :to="`/code-viewer?repo=${repo.name}`">
                    {{ repo.name }}
                  </router-link>
                </h3>
                <p class="repo-card-description">{{ repo.description }}</p>
                <div class="repo-card-topics" v-if="repo.topics.length > 0">
                  <el-tag
                    v-for="topic in repo.topics.slice(0, 3)"
                    :key="topic"
                    size="small"
                    effect="plain"
                    class="topic-tag"
                  >
                    {{ topic }}
                  </el-tag>
                </div>
                <div class="repo-card-footer">
                  <span class="footer-item">
                    <span
                      class="language-dot"
                      :style="{ backgroundColor: repo.languageColor }"
                    />
                    {{ repo.language }}
                  </span>
                  <span class="footer-item">
                    <el-icon><Star /></el-icon>
                    {{ formatNumber(repo.stars) }}
                  </span>
                  <span class="footer-item">
                    <el-icon><ForkSpoon /></el-icon>
                    {{ formatNumber(repo.forks) }}
                  </span>
                </div>
              </div>
            </div>

            <!-- 空状态 -->
            <div v-if="filteredRepositories.length === 0" class="empty-state">
              <el-icon :size="64" class="empty-icon"><Collection /></el-icon>
              <h3 class="empty-title">未找到仓库</h3>
              <p class="empty-desc">尝试调整筛选条件或搜索关键词</p>
            </div>
          </main>
        </div>
      </div>
    </div>
  </SidebarLayout>
</template>

<style scoped>
.repositories-page {
  padding: var(--perseus-space-8);
  min-height: calc(100vh - 64px);
  background: var(--perseus-surface);
}

.container {
  max-width: var(--perseus-container-max);
  margin: 0 auto;
}

/* 页面头部 */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: var(--perseus-space-8);
}

.page-title {
  font-size: var(--perseus-text-2xl);
  font-weight: 700;
  letter-spacing: var(--perseus-tracking-display);
  margin-bottom: var(--perseus-space-2);
}

.page-subtitle {
  font-size: var(--perseus-text-base);
  color: var(--perseus-muted);
}

/* 内容布局 */
.content-layout {
  display: grid;
  grid-template-columns: 220px 1fr;
  gap: var(--perseus-space-8);
  align-items: start;
}

/* 筛选侧边栏 */
.filter-sidebar {
  position: sticky;
  top: calc(var(--perseus-header-height) + var(--perseus-space-8));
}

.filter-group {
  margin-bottom: var(--perseus-space-6);
}

.filter-title {
  display: flex;
  align-items: center;
  gap: var(--perseus-space-2);
  font-size: var(--perseus-text-sm);
  font-weight: 600;
  color: var(--perseus-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: var(--perseus-space-3);
}

.filter-list {
  display: flex;
  flex-direction: column;
  gap: var(--perseus-space-1);
}

.filter-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--perseus-space-2) var(--perseus-space-3);
  border: none;
  background: transparent;
  color: var(--perseus-fg-2);
  font-size: var(--perseus-text-sm);
  border-radius: var(--perseus-radius-md);
  cursor: pointer;
  transition: all var(--perseus-motion-fast);
}

.filter-item:hover {
  background: var(--perseus-surface-warm);
  color: var(--perseus-fg);
}

.filter-item.is-active {
  background: var(--perseus-fg);
  color: var(--perseus-accent-on);
}

.filter-count {
  font-size: var(--perseus-text-xs);
  color: var(--perseus-muted);
}

.filter-item.is-active .filter-count {
  color: rgba(255, 255, 255, 0.7);
}

/* 语言筛选 */
.language-list {
  display: flex;
  flex-direction: column;
  gap: var(--perseus-space-2);
}

.language-item {
  display: flex;
  align-items: center;
}

.language-item :deep(.el-checkbox) {
  width: 100%;
}

.language-item :deep(.el-checkbox__label) {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  padding-right: var(--perseus-space-2);
}

.language-label {
  font-size: var(--perseus-text-sm);
}

.language-count {
  font-size: var(--perseus-text-xs);
  color: var(--perseus-muted);
}

/* 主内容区 */
.main-content {
  background: var(--perseus-bg);
  border: 1px solid var(--perseus-border-soft);
  border-radius: var(--perseus-radius-lg);
  padding: var(--perseus-space-6);
}

/* 工具栏 */
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--perseus-space-5);
  gap: var(--perseus-space-4);
}

.toolbar-left {
  flex: 1;
  max-width: 400px;
}

.search-input :deep(.el-input__wrapper) {
  border-radius: var(--perseus-radius-pill);
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: var(--perseus-space-3);
}

.sort-select {
  width: 150px;
}

.view-toggle {
  display: flex;
  border: 1px solid var(--perseus-border);
  border-radius: var(--perseus-radius-md);
  overflow: hidden;
}

.view-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: none;
  background: transparent;
  color: var(--perseus-muted);
  cursor: pointer;
  transition: all var(--perseus-motion-fast);
}

.view-btn:hover {
  background: var(--perseus-surface);
  color: var(--perseus-fg);
}

.view-btn.is-active {
  background: var(--perseus-fg);
  color: var(--perseus-accent-on);
}

/* 结果统计 */
.results-info {
  font-size: var(--perseus-text-sm);
  color: var(--perseus-muted);
  margin-bottom: var(--perseus-space-4);
}

/* 列表视图 */
.repositories-list {
  display: flex;
  flex-direction: column;
}

.repo-list-item {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--perseus-space-4);
  padding: var(--perseus-space-5) 0;
  border-bottom: 1px solid var(--perseus-border-soft);
  transition: background var(--perseus-motion-fast);
}

.repo-list-item:last-child {
  border-bottom: none;
}

.repo-list-item:hover {
  background: var(--perseus-surface);
  margin: 0 calc(-1 * var(--perseus-space-6));
  padding-left: var(--perseus-space-6);
  padding-right: var(--perseus-space-6);
}

.repo-main {
  flex: 1;
  min-width: 0;
}

.repo-name {
  display: flex;
  align-items: center;
  gap: var(--perseus-space-2);
  font-size: var(--perseus-text-lg);
  font-weight: 600;
  margin-bottom: var(--perseus-space-2);
}

.repo-name a {
  color: var(--perseus-accent);
  text-decoration: none;
}

.repo-name a:hover {
  text-decoration: underline;
}

.repo-tag {
  font-size: var(--perseus-text-xs);
}

.repo-description {
  font-size: var(--perseus-text-sm);
  color: var(--perseus-fg-2);
  margin-bottom: var(--perseus-space-3);
  line-height: 1.5;
}

.repo-topics {
  display: flex;
  flex-wrap: wrap;
  gap: var(--perseus-space-2);
  margin-bottom: var(--perseus-space-3);
}

.topic-tag {
  background: var(--perseus-surface-warm);
  border-color: var(--perseus-border-soft);
}

.repo-meta {
  display: flex;
  align-items: center;
  gap: var(--perseus-space-4);
  font-size: var(--perseus-text-xs);
  color: var(--perseus-muted);
}

.meta-item {
  display: flex;
  align-items: center;
  gap: var(--perseus-space-1);
}

.language-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

/* 网格视图 */
.repositories-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: var(--perseus-space-4);
}

.repo-grid-item {
  display: flex;
  flex-direction: column;
  padding: var(--perseus-space-5);
  background: var(--perseus-surface);
  border: 1px solid var(--perseus-border-soft);
  border-radius: var(--perseus-radius-md);
  transition: all var(--perseus-motion-fast);
}

.repo-grid-item:hover {
  border-color: var(--perseus-border);
  box-shadow: var(--perseus-elev-raised);
}

.repo-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--perseus-space-3);
}

.repo-visibility {
  color: var(--perseus-muted);
}

.repo-card-name {
  font-size: var(--perseus-text-base);
  font-weight: 600;
  margin-bottom: var(--perseus-space-2);
}

.repo-card-name a {
  color: var(--perseus-accent);
  text-decoration: none;
}

.repo-card-name a:hover {
  text-decoration: underline;
}

.repo-card-description {
  font-size: var(--perseus-text-sm);
  color: var(--perseus-fg-2);
  line-height: 1.5;
  margin-bottom: var(--perseus-space-3);
  flex: 1;
  display: -webkit-box;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.repo-card-topics {
  display: flex;
  flex-wrap: wrap;
  gap: var(--perseus-space-1);
  margin-bottom: var(--perseus-space-3);
}

.repo-card-footer {
  display: flex;
  align-items: center;
  gap: var(--perseus-space-3);
  font-size: var(--perseus-text-xs);
  color: var(--perseus-muted);
  padding-top: var(--perseus-space-3);
  border-top: 1px solid var(--perseus-border-soft);
}

.footer-item {
  display: flex;
  align-items: center;
  gap: var(--perseus-space-1);
}

/* 空状态 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--perseus-space-12) 0;
  text-align: center;
}

.empty-icon {
  color: var(--perseus-border);
  margin-bottom: var(--perseus-space-4);
}

.empty-title {
  font-size: var(--perseus-text-lg);
  font-weight: 600;
  margin-bottom: var(--perseus-space-2);
}

.empty-desc {
  font-size: var(--perseus-text-sm);
  color: var(--perseus-muted);
}

/* 响应式 */
@media (max-width: 920px) {
  .content-layout {
    grid-template-columns: 1fr;
  }

  .filter-sidebar {
    position: static;
    display: flex;
    gap: var(--perseus-space-6);
    overflow-x: auto;
    padding-bottom: var(--perseus-space-3);
  }

  .filter-group {
    flex-shrink: 0;
  }

  .filter-list {
    flex-direction: row;
  }

  .language-list {
    flex-direction: row;
    flex-wrap: wrap;
    max-width: 300px;
  }
}

@media (max-width: 768px) {
  .repositories-page {
    padding: var(--perseus-space-4);
  }

  .page-header {
    flex-direction: column;
    gap: var(--perseus-space-4);
  }

  .toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .toolbar-left {
    max-width: none;
  }

  .toolbar-right {
    justify-content: space-between;
  }

  .repositories-grid {
    grid-template-columns: 1fr;
  }

  .repo-list-item {
    flex-direction: column;
  }

  .repo-actions {
    width: 100%;
  }

  .repo-actions .el-button {
    width: 100%;
  }
}
</style>
