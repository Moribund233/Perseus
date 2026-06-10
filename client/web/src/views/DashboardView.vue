<script setup lang="ts">
/**
 * 仪表盘页面
 * 参考原型: dashboard.html
 */
import { ref } from 'vue'
import SidebarLayout from '@/components/layouts/SidebarLayout.vue'
import {
  Collection,
  Star,
  Share,
  TrendCharts,
  Plus,
  ArrowRight,
} from '@element-plus/icons-vue'

// 模拟数据
const recentRepositories = ref([
  {
    id: 1,
    name: 'perseus-core',
    description: '核心代码库',
    language: 'TypeScript',
    languageColor: '#3178c6',
    stars: 128,
    updatedAt: '2小时前',
    isPrivate: false,
  },
  {
    id: 2,
    name: 'perseus-web',
    description: 'Web 客户端',
    language: 'Vue',
    languageColor: '#42b883',
    stars: 86,
    updatedAt: '5小时前',
    isPrivate: false,
  },
  {
    id: 3,
    name: 'internal-tools',
    description: '内部工具集',
    language: 'Python',
    languageColor: '#3572A5',
    stars: 12,
    updatedAt: '1天前',
    isPrivate: true,
  },
])

const recentActivity = ref([
  { id: 1, type: 'commit', message: '更新了用户认证模块', repo: 'perseus-core', time: '10分钟前' },
  { id: 2, type: 'pr', message: '合并了功能分支 feature/auth', repo: 'perseus-web', time: '2小时前' },
  { id: 3, type: 'issue', message: '修复了登录页面的样式问题', repo: 'perseus-web', time: '5小时前' },
])

const contributionStats = ref({
  commits: 142,
  pullRequests: 18,
  issues: 7,
  reviews: 34,
})
</script>

<template>
  <SidebarLayout>
    <div class="dashboard">
      <!-- 页面头部 -->
      <header class="dashboard-header">
        <div class="header-content">
          <h1 class="page-title">仪表盘</h1>
          <p class="page-subtitle">欢迎回来，查看你的项目和活动</p>
        </div>
        <el-button type="primary" :icon="Plus" class="create-btn">
          创建仓库
        </el-button>
      </header>

      <!-- 统计卡片 -->
      <section class="stats-section">
        <el-row :gutter="16">
          <el-col :xs="12" :sm="12" :md="6">
            <div class="stat-card">
              <div class="stat-icon" style="background: #e3f2fd; color: #1976d2;">
                <el-icon :size="24"><TrendCharts /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ contributionStats.commits }}</div>
                <div class="stat-label">提交</div>
              </div>
            </div>
          </el-col>
          <el-col :xs="12" :sm="12" :md="6">
            <div class="stat-card">
              <div class="stat-icon" style="background: #e8f5e9; color: #388e3c;">
                <el-icon :size="24"><Share /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ contributionStats.pullRequests }}</div>
                <div class="stat-label">合并请求</div>
              </div>
            </div>
          </el-col>
          <el-col :xs="12" :sm="12" :md="6">
            <div class="stat-card">
              <div class="stat-icon" style="background: #fff3e0; color: #f57c00;">
                <el-icon :size="24"><Collection /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ contributionStats.issues }}</div>
                <div class="stat-label">待处理问题</div>
              </div>
            </div>
          </el-col>
          <el-col :xs="12" :sm="12" :md="6">
            <div class="stat-card">
              <div class="stat-icon" style="background: #f3e5f5; color: #7b1fa2;">
                <el-icon :size="24"><Star /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ contributionStats.reviews }}</div>
                <div class="stat-label">代码审查</div>
              </div>
            </div>
          </el-col>
        </el-row>
      </section>

      <!-- 主要内容区 -->
      <div class="dashboard-content">
        <el-row :gutter="24">
          <!-- 左侧：最近仓库 -->
          <el-col :xs="24" :lg="16">
            <section class="content-section">
              <div class="section-header">
                <h2 class="section-title">
                  <el-icon><Collection /></el-icon>
                  最近仓库
                </h2>
                <el-button text :icon="ArrowRight">查看全部</el-button>
              </div>

              <div class="repo-list">
                <div
                  v-for="repo in recentRepositories"
                  :key="repo.id"
                  class="repo-card"
                >
                  <div class="repo-header">
                    <div class="repo-name-wrapper">
                      <el-icon v-if="repo.isPrivate" class="repo-visibility">
                        <Lock />
                      </el-icon>
                      <el-icon v-else class="repo-visibility">
                        <View />
                      </el-icon>
                      <h3 class="repo-name">{{ repo.name }}</h3>
                    </div>
                    <el-tag size="small" effect="plain">{{ repo.language }}</el-tag>
                  </div>
                  <p class="repo-description">{{ repo.description }}</p>
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
                      {{ repo.stars }}
                    </span>
                    <span class="meta-item">更新于 {{ repo.updatedAt }}</span>
                  </div>
                </div>
              </div>
            </section>
          </el-col>

          <!-- 右侧：最近活动 -->
          <el-col :xs="24" :lg="8">
            <section class="content-section">
              <div class="section-header">
                <h2 class="section-title">
                  <el-icon><Timer /></el-icon>
                  最近活动
                </h2>
              </div>

              <div class="activity-list">
                <div
                  v-for="activity in recentActivity"
                  :key="activity.id"
                  class="activity-item"
                >
                  <div class="activity-icon">
                    <el-icon v-if="activity.type === 'commit'"><CircleCheck /></el-icon>
                    <el-icon v-else-if="activity.type === 'pr'"><Share /></el-icon>
                    <el-icon v-else><Warning /></el-icon>
                  </div>
                  <div class="activity-content">
                    <p class="activity-message">{{ activity.message }}</p>
                    <p class="activity-repo">{{ activity.repo }} · {{ activity.time }}</p>
                  </div>
                </div>
              </div>
            </section>
          </el-col>
        </el-row>
      </div>
    </div>
  </SidebarLayout>
</template>

<style scoped>
.dashboard {
  padding: var(--perseus-space-8);
  max-width: 1200px;
  margin: 0 auto;
}

.dashboard-header {
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

.create-btn {
  background: var(--perseus-accent);
  border-color: var(--perseus-accent);
}

/* 统计卡片 */
.stats-section {
  margin-bottom: var(--perseus-space-8);
}

.stat-card {
  display: flex;
  align-items: center;
  gap: var(--perseus-space-4);
  padding: var(--perseus-space-5);
  background: var(--perseus-bg);
  border: 1px solid var(--perseus-border-soft);
  border-radius: var(--perseus-radius-lg);
  transition: box-shadow var(--perseus-motion-fast) var(--perseus-ease-standard);
}

.stat-card:hover {
  box-shadow: var(--perseus-elev-raised);
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: var(--perseus-radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
}

.stat-value {
  font-size: var(--perseus-text-xl);
  font-weight: 700;
  color: var(--perseus-fg);
}

.stat-label {
  font-size: var(--perseus-text-sm);
  color: var(--perseus-muted);
  margin-top: var(--perseus-space-1);
}

/* 内容区 */
.dashboard-content {
  margin-top: var(--perseus-space-8);
}

.content-section {
  background: var(--perseus-bg);
  border: 1px solid var(--perseus-border-soft);
  border-radius: var(--perseus-radius-lg);
  padding: var(--perseus-space-6);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--perseus-space-5);
}

.section-title {
  font-size: var(--perseus-text-lg);
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: var(--perseus-space-2);
}

/* 仓库列表 */
.repo-list {
  display: flex;
  flex-direction: column;
  gap: var(--perseus-space-4);
}

.repo-card {
  padding: var(--perseus-space-5);
  background: var(--perseus-surface);
  border: 1px solid var(--perseus-border-soft);
  border-radius: var(--perseus-radius-md);
  transition: border-color var(--perseus-motion-fast) var(--perseus-ease-standard);
}

.repo-card:hover {
  border-color: var(--perseus-border);
}

.repo-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--perseus-space-3);
}

.repo-name-wrapper {
  display: flex;
  align-items: center;
  gap: var(--perseus-space-2);
}

.repo-visibility {
  color: var(--perseus-muted);
}

.repo-name {
  font-size: var(--perseus-text-base);
  font-weight: 600;
  color: var(--perseus-fg);
}

.repo-description {
  font-size: var(--perseus-text-sm);
  color: var(--perseus-muted);
  margin-bottom: var(--perseus-space-3);
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

/* 活动列表 */
.activity-list {
  display: flex;
  flex-direction: column;
  gap: var(--perseus-space-4);
}

.activity-item {
  display: flex;
  gap: var(--perseus-space-3);
  padding: var(--perseus-space-3) 0;
  border-bottom: 1px solid var(--perseus-border-soft);
}

.activity-item:last-child {
  border-bottom: none;
}

.activity-icon {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--perseus-surface-warm);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--perseus-muted);
  flex-shrink: 0;
}

.activity-content {
  flex: 1;
}

.activity-message {
  font-size: var(--perseus-text-sm);
  color: var(--perseus-fg);
  margin-bottom: var(--perseus-space-1);
}

.activity-repo {
  font-size: var(--perseus-text-xs);
  color: var(--perseus-muted);
}

/* 响应式 */
@media (max-width: 768px) {
  .dashboard {
    padding: var(--perseus-space-4);
  }

  .dashboard-header {
    flex-direction: column;
    gap: var(--perseus-space-4);
  }

  .page-title {
    font-size: var(--perseus-text-xl);
  }
}
</style>
