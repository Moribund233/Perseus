<script setup lang="ts">
/**
 * 博客页面
 * 展示项目更新日志、技术文章和最新动态
 */
import { ref, computed } from 'vue'
import NavLayout from '@/components/layouts/NavLayout.vue'
import {
  Calendar,
  User,
  Clock,
  Search,
} from '@element-plus/icons-vue'

/**
 * 文章分类
 */
const categories = [
  { key: 'all', label: '全部' },
  { key: 'news', label: '项目动态' },
  { key: 'tech', label: '技术文章' },
  { key: 'release', label: '版本发布' },
  { key: 'community', label: '社区' },
]

/**
 * 当前选中的分类
 */
const activeCategory = ref('all')

/**
 * 搜索关键词
 */
const searchQuery = ref('')

/**
 * 博客文章列表
 */
const blogPosts = ref([
  {
    id: 1,
    title: 'Perseus v2.0 发布：全新界面与性能提升',
    excerpt: '我们很高兴地宣布 Perseus 2.0 正式发布！这次更新带来了全新的用户界面、显著的性能提升以及众多新功能...',
    category: 'release',
    categoryLabel: '版本发布',
    author: 'Perseus 团队',
    date: '2024-06-15',
    readTime: '5 分钟',
    tags: ['v2.0', 'release', 'performance'],
    featured: true,
  },
  {
    id: 2,
    title: '如何使用 Perseus CI/CD 实现自动化部署',
    excerpt: '本文将详细介绍如何配置 Perseus 的持续集成和持续部署功能，帮助你实现开发流程的自动化...',
    category: 'tech',
    categoryLabel: '技术文章',
    author: 'Alex Chen',
    date: '2024-06-10',
    readTime: '8 分钟',
    tags: ['ci/cd', 'devops', 'tutorial'],
    featured: false,
  },
  {
    id: 3,
    title: '社区贡献者月度表彰：五月',
    excerpt: '感谢所有为 Perseus 项目做出贡献的开发者！本月我们特别表彰以下几位优秀的贡献者...',
    category: 'community',
    categoryLabel: '社区',
    author: 'Sarah Li',
    date: '2024-06-05',
    readTime: '3 分钟',
    tags: ['community', 'contributors'],
    featured: false,
  },
  {
    id: 4,
    title: 'Perseus 安全公告：重要更新',
    excerpt: '我们发现并修复了一个潜在的安全问题。建议所有用户尽快升级到最新版本以确保安全...',
    category: 'news',
    categoryLabel: '项目动态',
    author: 'Security Team',
    date: '2024-05-28',
    readTime: '4 分钟',
    tags: ['security', 'update'],
    featured: false,
  },
  {
    id: 5,
    title: '深入理解 Perseus 的权限管理系统',
    excerpt: '权限管理是代码托管平台的核心功能之一。本文将深入探讨 Perseus 的权限设计原理和最佳实践...',
    category: 'tech',
    categoryLabel: '技术文章',
    author: 'Mike Wang',
    date: '2024-05-20',
    readTime: '12 分钟',
    tags: ['security', 'permissions', 'architecture'],
    featured: false,
  },
  {
    id: 6,
    title: 'Perseus v1.9 发布说明',
    excerpt: 'v1.9 版本带来了代码审查功能的重大改进、新的 Webhook 支持以及性能优化...',
    category: 'release',
    categoryLabel: '版本发布',
    author: 'Perseus 团队',
    date: '2024-05-15',
    readTime: '6 分钟',
    tags: ['v1.9', 'release'],
    featured: false,
  },
])

/**
 * 筛选后的文章列表
 */
const filteredPosts = computed(() => {
  let result = blogPosts.value

  // 分类筛选
  if (activeCategory.value !== 'all') {
    result = result.filter(post => post.category === activeCategory.value)
  }

  // 搜索筛选
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(
      post =>
        post.title.toLowerCase().includes(query) ||
        post.excerpt.toLowerCase().includes(query) ||
        post.tags.some(tag => tag.toLowerCase().includes(query))
    )
  }

  return result
})

/**
 * 精选文章
 */
const featuredPost = computed(() => blogPosts.value.find(post => post.featured))

/**
 * 普通文章列表（排除精选文章）
 */
const regularPosts = computed(() =>
  filteredPosts.value.filter(post => !post.featured)
)
</script>

<template>
  <NavLayout>
    <div class="blog-page">
      <!-- 页面头部 -->
      <header class="page-header">
        <div class="container">
          <h1 class="page-title">博客</h1>
          <p class="page-subtitle">项目更新、技术文章和社区动态</p>
        </div>
      </header>

      <div class="container">
        <!-- 分类筛选和搜索 -->
        <div class="filter-bar">
          <div class="category-tabs">
            <button
              v-for="cat in categories"
              :key="cat.key"
              class="category-tab"
              :class="{ 'is-active': activeCategory === cat.key }"
              @click="activeCategory = cat.key"
            >
              {{ cat.label }}
            </button>
          </div>
          <div class="search-box">
            <el-input
              v-model="searchQuery"
              placeholder="搜索文章..."
              :prefix-icon="Search"
              clearable
            />
          </div>
        </div>

        <!-- 精选文章 -->
        <article v-if="featuredPost && activeCategory === 'all' && !searchQuery" class="featured-post">
          <div class="featured-badge">精选</div>
          <div class="featured-content">
            <div class="post-meta">
              <span class="category-tag">{{ featuredPost.categoryLabel }}</span>
              <span class="meta-item">
                <el-icon><Calendar /></el-icon>
                {{ featuredPost.date }}
              </span>
              <span class="meta-item">
                <el-icon><Clock /></el-icon>
                {{ featuredPost.readTime }}
              </span>
            </div>
            <h2 class="featured-title">
              <router-link :to="`/blog/${featuredPost.id}`">
                {{ featuredPost.title }}
              </router-link>
            </h2>
            <p class="featured-excerpt">{{ featuredPost.excerpt }}</p>
            <div class="post-footer">
              <div class="author">
                <el-icon><User /></el-icon>
                {{ featuredPost.author }}
              </div>
              <div class="tags">
                <el-tag
                  v-for="tag in featuredPost.tags"
                  :key="tag"
                  size="small"
                  effect="plain"
                  class="post-tag"
                >
                  {{ tag }}
                </el-tag>
              </div>
            </div>
          </div>
        </article>

        <!-- 文章列表 -->
        <div class="posts-grid">
          <article
            v-for="post in regularPosts"
            :key="post.id"
            class="post-card"
          >
            <div class="post-meta">
              <span class="category-tag">{{ post.categoryLabel }}</span>
              <span class="meta-item">
                <el-icon><Calendar /></el-icon>
                {{ post.date }}
              </span>
            </div>
            <h3 class="post-title">
              <router-link :to="`/blog/${post.id}`">
                {{ post.title }}
              </router-link>
            </h3>
            <p class="post-excerpt">{{ post.excerpt }}</p>
            <div class="post-footer">
              <div class="author">
                <el-icon><User /></el-icon>
                {{ post.author }}
              </div>
              <span class="meta-item">
                <el-icon><Clock /></el-icon>
                {{ post.readTime }}
              </span>
            </div>
          </article>
        </div>

        <!-- 空状态 -->
        <div v-if="filteredPosts.length === 0" class="empty-state">
          <el-icon :size="48" class="empty-icon"><Search /></el-icon>
          <h3 class="empty-title">未找到相关文章</h3>
          <p class="empty-desc">尝试调整筛选条件或搜索关键词</p>
        </div>

        <!-- 订阅区域 -->
        <section class="subscribe-section">
          <div class="subscribe-card">
            <h2 class="subscribe-title">订阅更新</h2>
            <p class="subscribe-desc">获取 Perseus 的最新动态和技术文章</p>
            <div class="subscribe-form">
              <el-input
                placeholder="输入你的邮箱地址"
                class="subscribe-input"
              />
              <el-button type="primary">订阅</el-button>
            </div>
          </div>
        </section>
      </div>
    </div>
  </NavLayout>
</template>

<style scoped>
.blog-page {
  padding-bottom: var(--perseus-space-16);
  background: var(--perseus-surface);
  min-height: calc(100vh - 64px);
}

.container {
  max-width: var(--perseus-container-max);
  margin: 0 auto;
  padding: 0 var(--perseus-container-gutter);
}

/* 页面头部 */
.page-header {
  padding: var(--perseus-space-12) 0 var(--perseus-space-8);
  text-align: center;
  background: linear-gradient(180deg, var(--perseus-bg) 0%, var(--perseus-surface) 100%);
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

/* 筛选栏 */
.filter-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--perseus-space-8);
  gap: var(--perseus-space-4);
}

.category-tabs {
  display: flex;
  gap: var(--perseus-space-2);
  flex-wrap: wrap;
}

.category-tab {
  padding: var(--perseus-space-2) var(--perseus-space-4);
  border: none;
  background: transparent;
  color: var(--perseus-fg-2);
  font-size: var(--perseus-text-sm);
  font-weight: 500;
  border-radius: var(--perseus-radius-pill);
  cursor: pointer;
  transition: all var(--perseus-motion-fast);
}

.category-tab:hover {
  background: var(--perseus-surface-warm);
  color: var(--perseus-fg);
}

.category-tab.is-active {
  background: var(--perseus-fg);
  color: var(--perseus-accent-on);
}

.search-box {
  width: 280px;
}

.search-box :deep(.el-input__wrapper) {
  border-radius: var(--perseus-radius-pill);
}

/* 精选文章 */
.featured-post {
  position: relative;
  background: var(--perseus-bg);
  border: 1px solid var(--perseus-border-soft);
  border-radius: var(--perseus-radius-lg);
  padding: var(--perseus-space-8);
  margin-bottom: var(--perseus-space-8);
  transition: all var(--perseus-motion-fast);
}

.featured-post:hover {
  border-color: var(--perseus-border);
  box-shadow: var(--perseus-elev-raised);
}

.featured-badge {
  position: absolute;
  top: var(--perseus-space-4);
  right: var(--perseus-space-4);
  background: var(--perseus-accent);
  color: var(--perseus-accent-on);
  font-size: var(--perseus-text-xs);
  font-weight: 600;
  padding: var(--perseus-space-1) var(--perseus-space-3);
  border-radius: var(--perseus-radius-pill);
}

.featured-content {
  max-width: 800px;
}

.post-meta {
  display: flex;
  align-items: center;
  gap: var(--perseus-space-4);
  margin-bottom: var(--perseus-space-4);
  flex-wrap: wrap;
}

.category-tag {
  font-size: var(--perseus-text-xs);
  font-weight: 600;
  color: var(--perseus-accent);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: var(--perseus-space-1);
  font-size: var(--perseus-text-sm);
  color: var(--perseus-muted);
}

.featured-title {
  font-size: var(--perseus-text-2xl);
  font-weight: 700;
  margin-bottom: var(--perseus-space-4);
  line-height: var(--perseus-leading-tight);
}

.featured-title a {
  color: var(--perseus-fg);
  text-decoration: none;
}

.featured-title a:hover {
  color: var(--perseus-accent);
}

.featured-excerpt {
  font-size: var(--perseus-text-base);
  color: var(--perseus-fg-2);
  line-height: var(--perseus-leading-body);
  margin-bottom: var(--perseus-space-6);
}

.post-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--perseus-space-3);
}

.author {
  display: flex;
  align-items: center;
  gap: var(--perseus-space-2);
  font-size: var(--perseus-text-sm);
  color: var(--perseus-fg-2);
}

.tags {
  display: flex;
  gap: var(--perseus-space-2);
}

.post-tag {
  background: var(--perseus-surface-warm);
  border-color: var(--perseus-border-soft);
}

/* 文章网格 */
.posts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: var(--perseus-space-6);
  margin-bottom: var(--perseus-space-12);
}

.post-card {
  background: var(--perseus-bg);
  border: 1px solid var(--perseus-border-soft);
  border-radius: var(--perseus-radius-lg);
  padding: var(--perseus-space-6);
  transition: all var(--perseus-motion-fast);
}

.post-card:hover {
  border-color: var(--perseus-border);
  box-shadow: var(--perseus-elev-raised);
}

.post-card .post-meta {
  margin-bottom: var(--perseus-space-3);
}

.post-title {
  font-size: var(--perseus-text-lg);
  font-weight: 600;
  margin-bottom: var(--perseus-space-3);
  line-height: var(--perseus-leading-tight);
}

.post-title a {
  color: var(--perseus-fg);
  text-decoration: none;
}

.post-title a:hover {
  color: var(--perseus-accent);
}

.post-excerpt {
  font-size: var(--perseus-text-sm);
  color: var(--perseus-fg-2);
  line-height: var(--perseus-leading-body);
  margin-bottom: var(--perseus-space-4);
  display: -webkit-box;
  line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.post-card .post-footer {
  padding-top: var(--perseus-space-4);
  border-top: 1px solid var(--perseus-border-soft);
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

/* 订阅区域 */
.subscribe-section {
  margin-top: var(--perseus-space-8);
}

.subscribe-card {
  background: var(--perseus-fg);
  color: var(--perseus-accent-on);
  border-radius: var(--perseus-radius-lg);
  padding: var(--perseus-space-8);
  text-align: center;
}

.subscribe-title {
  font-size: var(--perseus-text-xl);
  font-weight: 700;
  margin-bottom: var(--perseus-space-2);
}

.subscribe-desc {
  font-size: var(--perseus-text-base);
  color: rgba(255, 255, 255, 0.7);
  margin-bottom: var(--perseus-space-6);
}

.subscribe-form {
  display: flex;
  gap: var(--perseus-space-3);
  max-width: 480px;
  margin: 0 auto;
}

.subscribe-input {
  flex: 1;
}

.subscribe-input :deep(.el-input__wrapper) {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(255, 255, 255, 0.2);
  color: white;
}

.subscribe-input :deep(.el-input__inner) {
  color: white;
}

.subscribe-input :deep(.el-input__inner::placeholder) {
  color: rgba(255, 255, 255, 0.5);
}

/* 响应式 */
@media (max-width: 768px) {
  .page-header {
    padding: var(--perseus-space-8) 0 var(--perseus-space-6);
  }

  .page-title {
    font-size: var(--perseus-text-2xl);
  }

  .filter-bar {
    flex-direction: column;
    align-items: stretch;
  }

  .search-box {
    width: 100%;
  }

  .posts-grid {
    grid-template-columns: 1fr;
  }

  .featured-post {
    padding: var(--perseus-space-5);
  }

  .featured-title {
    font-size: var(--perseus-text-xl);
  }

  .post-footer {
    flex-direction: column;
    align-items: flex-start;
  }

  .subscribe-form {
    flex-direction: column;
  }
}
</style>
