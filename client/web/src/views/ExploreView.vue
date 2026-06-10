<script setup lang="ts">
/**
 * 探索/浏览页面
 * 参考原型: browse.html
 */
import { ref } from 'vue'
import NavLayout from '@/components/layouts/NavLayout.vue'
import {
  Search,
  Star,
  ForkSpoon,
  Sort,
} from '@element-plus/icons-vue'

const searchQuery = ref('')
const activeFilter = ref('trending')
const sortBy = ref('stars')

const filters = [
  { key: 'trending', label: '趋势' },
  { key: 'featured', label: '精选' },
  { key: 'new', label: '最新' },
]

const sortOptions = [
  { key: 'stars', label: '星标数' },
  { key: 'updated', label: '更新时间' },
  { key: 'forks', label: '分支数' },
]

// 模拟仓库数据
const repositories = ref([
  {
    id: 1,
    owner: 'perseus',
    name: 'perseus-core',
    description: 'Perseus 核心代码库 - 高性能、可扩展的代码托管平台核心',
    language: 'TypeScript',
    languageColor: '#3178c6',
    stars: 2847,
    forks: 342,
    issues: 23,
    updatedAt: '2小时前',
    topics: ['git', 'hosting', 'collaboration'],
  },
  {
    id: 2,
    owner: 'perseus',
    name: 'perseus-web',
    description: 'Perseus Web 客户端 - 基于 Vue3 的现代 Web 界面',
    language: 'Vue',
    languageColor: '#42b883',
    stars: 1523,
    forks: 186,
    issues: 15,
    updatedAt: '5小时前',
    topics: ['vue3', 'typescript', 'ui'],
  },
  {
    id: 3,
    owner: 'community',
    name: 'awesome-devtools',
    description: '精选开发者工具集合，包含各种实用的开发辅助工具',
    language: 'JavaScript',
    languageColor: '#f1e05a',
    stars: 8932,
    forks: 567,
    issues: 42,
    updatedAt: '1天前',
    topics: ['devtools', 'awesome', 'list'],
  },
  {
    id: 4,
    owner: 'opensource',
    name: 'fastapi-starter',
    description: 'FastAPI 项目模板，包含最佳实践和常用配置',
    language: 'Python',
    languageColor: '#3572A5',
    stars: 2156,
    forks: 423,
    issues: 8,
    updatedAt: '3天前',
    topics: ['fastapi', 'python', 'template'],
  },
  {
    id: 5,
    owner: 'rustaceans',
    name: 'rust-web-framework',
    description: '用 Rust 编写的高性能 Web 框架',
    language: 'Rust',
    languageColor: '#dea584',
    stars: 4532,
    forks: 298,
    issues: 67,
    updatedAt: '1周前',
    topics: ['rust', 'web', 'framework'],
  },
  {
    id: 6,
    owner: 'gophers',
    name: 'go-microservices',
    description: 'Go 微服务架构示例项目',
    language: 'Go',
    languageColor: '#00ADD8',
    stars: 3211,
    forks: 445,
    issues: 12,
    updatedAt: '2周前',
    topics: ['go', 'microservices', 'grpc'],
  },
])

const formatNumber = (num: number) => {
  if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'k'
  }
  return num.toString()
}
</script>

<template>
  <NavLayout>
    <div class="explore-page">
      <div class="container">
        <!-- 页面标题 -->
        <header class="page-header">
          <h1 class="page-title">探索仓库</h1>
          <p class="page-subtitle">发现优秀的开源项目和社区资源</p>
        </header>

        <!-- 搜索和筛选栏 -->
        <div class="search-bar">
          <div class="search-input-wrapper">
            <el-input
              v-model="searchQuery"
              placeholder="搜索仓库..."
              :prefix-icon="Search"
              size="large"
              class="search-input"
            />
          </div>

          <div class="filter-tabs">
            <button
              v-for="filter in filters"
              :key="filter.key"
              class="filter-tab"
              :class="{ 'is-active': activeFilter === filter.key }"
              @click="activeFilter = filter.key"
            >
              {{ filter.label }}
            </button>
          </div>

          <div class="sort-dropdown">
            <el-dropdown>
              <el-button :icon="Sort">
                排序: {{ sortOptions.find(o => o.key === sortBy)?.label }}
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item
                    v-for="option in sortOptions"
                    :key="option.key"
                    @click="sortBy = option.key"
                  >
                    {{ option.label }}
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>

        <!-- 仓库列表 -->
        <div class="repo-grid">
          <div
            v-for="repo in repositories"
            :key="repo.id"
            class="repo-card"
          >
            <div class="repo-card-header">
              <div class="repo-avatar">
                {{ repo.owner.charAt(0).toUpperCase() }}
              </div>
              <div class="repo-info">
                <h3 class="repo-name">
                  <span class="repo-owner">{{ repo.owner }}</span>
                  <span class="repo-separator">/</span>
                  <span class="repo-title">{{ repo.name }}</span>
                </h3>
              </div>
            </div>

            <p class="repo-description">{{ repo.description }}</p>

            <div class="repo-topics">
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
            </div>

            <div class="repo-footer">
              <span class="update-time">更新于 {{ repo.updatedAt }}</span>
              <el-button text type="primary" size="small">
                查看详情
              </el-button>
            </div>
          </div>
        </div>

        <!-- 分页 -->
        <div class="pagination-wrapper">
          <el-pagination
            background
            layout="prev, pager, next"
            :total="100"
            :page-size="12"
          />
        </div>
      </div>
    </div>
  </NavLayout>
</template>

<style scoped>
.explore-page {
  padding: var(--perseus-space-8) 0;
  min-height: calc(100vh - 64px);
  background: var(--perseus-surface);
}

.container {
  max-width: var(--perseus-container-max);
  margin: 0 auto;
  padding: 0 var(--perseus-container-gutter);
}

.page-header {
  text-align: center;
  margin-bottom: var(--perseus-space-8);
}

.page-title {
  font-size: var(--perseus-text-3xl);
  font-weight: 700;
  letter-spacing: var(--perseus-tracking-display);
  margin-bottom: var(--perseus-space-3);
}

.page-subtitle {
  font-size: var(--perseus-text-lg);
  color: var(--perseus-muted);
}

/* 搜索栏 */
.search-bar {
  display: flex;
  align-items: center;
  gap: var(--perseus-space-4);
  margin-bottom: var(--perseus-space-8);
  flex-wrap: wrap;
}

.search-input-wrapper {
  flex: 1;
  min-width: 300px;
}

.search-input :deep(.el-input__wrapper) {
  border-radius: var(--perseus-radius-pill);
  box-shadow: none;
  border: 1px solid var(--perseus-border);
  padding: 0 var(--perseus-space-5);
}

.filter-tabs {
  display: flex;
  gap: var(--perseus-space-2);
}

.filter-tab {
  padding: var(--perseus-space-2) var(--perseus-space-4);
  border: none;
  background: transparent;
  color: var(--perseus-fg-2);
  font-size: var(--perseus-text-sm);
  font-weight: 500;
  border-radius: var(--perseus-radius-md);
  cursor: pointer;
  transition: all var(--perseus-motion-fast) var(--perseus-ease-standard);
}

.filter-tab:hover {
  background: var(--perseus-surface-warm);
  color: var(--perseus-fg);
}

.filter-tab.is-active {
  background: var(--perseus-fg);
  color: var(--perseus-accent-on);
}

/* 仓库网格 */
.repo-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: var(--perseus-space-5);
  margin-bottom: var(--perseus-space-8);
}

.repo-card {
  background: var(--perseus-bg);
  border: 1px solid var(--perseus-border-soft);
  border-radius: var(--perseus-radius-lg);
  padding: var(--perseus-space-6);
  transition: all var(--perseus-motion-fast) var(--perseus-ease-standard);
}

.repo-card:hover {
  border-color: var(--perseus-border);
  box-shadow: var(--perseus-elev-raised);
}

.repo-card-header {
  display: flex;
  align-items: center;
  gap: var(--perseus-space-3);
  margin-bottom: var(--perseus-space-4);
}

.repo-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--perseus-accent);
  color: var(--perseus-accent-on);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: var(--perseus-text-lg);
}

.repo-name {
  font-size: var(--perseus-text-base);
  font-weight: 600;
}

.repo-owner {
  color: var(--perseus-muted);
}

.repo-separator {
  color: var(--perseus-muted);
  margin: 0 var(--perseus-space-1);
}

.repo-title {
  color: var(--perseus-fg);
}

.repo-description {
  font-size: var(--perseus-text-sm);
  color: var(--perseus-fg-2);
  line-height: 1.6;
  margin-bottom: var(--perseus-space-4);
  display: -webkit-box;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.repo-topics {
  display: flex;
  flex-wrap: wrap;
  gap: var(--perseus-space-2);
  margin-bottom: var(--perseus-space-4);
}

.topic-tag {
  background: var(--perseus-surface-warm);
  border-color: var(--perseus-border-soft);
}

.repo-meta {
  display: flex;
  align-items: center;
  gap: var(--perseus-space-4);
  margin-bottom: var(--perseus-space-4);
  font-size: var(--perseus-text-sm);
  color: var(--perseus-muted);
}

.meta-item {
  display: flex;
  align-items: center;
  gap: var(--perseus-space-1);
}

.language-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
}

.repo-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: var(--perseus-space-4);
  border-top: 1px solid var(--perseus-border-soft);
}

.update-time {
  font-size: var(--perseus-text-xs);
  color: var(--perseus-muted);
}

/* 分页 */
.pagination-wrapper {
  display: flex;
  justify-content: center;
  padding: var(--perseus-space-8) 0;
}

/* 响应式 */
@media (max-width: 768px) {
  .page-title {
    font-size: var(--perseus-text-2xl);
  }

  .search-bar {
    flex-direction: column;
    align-items: stretch;
  }

  .search-input-wrapper {
    min-width: auto;
  }

  .filter-tabs {
    justify-content: center;
  }

  .repo-grid {
    grid-template-columns: 1fr;
  }
}
</style>
