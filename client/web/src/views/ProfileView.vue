<script setup lang="ts">
/**
 * 个人资料页面
 * 展示用户的公开资料、仓库列表、贡献统计等
 */
import { ref, computed } from 'vue'
import NavLayout from '@/components/layouts/NavLayout.vue'
import {
  Collection,
  Star,
  UserFilled,
  Location,
  Link,
  OfficeBuilding,
  Calendar,
  Share,
  ForkSpoon,
} from '@element-plus/icons-vue'

/**
 * 用户信息
 */
const userProfile = ref({
  username: 'alex',
  displayName: 'Alex Chen',
  avatar: '',
  bio: 'Full-stack developer passionate about open source. Building tools that make developers\' lives easier.',
  location: 'Shanghai, China',
  website: 'https://alexchen.dev',
  company: 'Perseus',
  joinDate: '2024-03-15',
  followers: 1284,
  following: 256,
})

/**
 * 贡献统计数据
 */
const contributionStats = ref({
  totalCommits: 2847,
  totalRepositories: 42,
  starsEarned: 8932,
  pullRequests: 156,
})

/**
 * 贡献日历数据（模拟最近一年的贡献）
 */
const contributionCalendar = ref(generateContributionData())

/**
 * 生成模拟贡献数据
 * @returns 贡献数据数组
 */
function generateContributionData() {
  const data = []
  const levels = [0, 1, 2, 3, 4]
  for (let i = 0; i < 365; i++) {
    data.push({
      date: new Date(Date.now() - (365 - i) * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      count: Math.random() > 0.6 ? levels[Math.floor(Math.random() * levels.length)] : 0,
    })
  }
  return data
}

/**
 * 贡献等级颜色
 * @param level 贡献等级
 * @returns 颜色类名
 */
const getContributionColor = (level: number | undefined) => {
  const colors = ['', 'level-1', 'level-2', 'level-3', 'level-4']
  return colors[level ?? 0] || ''
}

/**
 * 用户仓库列表
 */
const userRepositories = ref([
  {
    id: 1,
    name: 'perseus-core',
    description: 'Perseus 核心代码库 - 高性能、可扩展的代码托管平台核心',
    language: 'TypeScript',
    languageColor: '#3178c6',
    stars: 2847,
    forks: 342,
    isPrivate: false,
    updatedAt: '2小时前',
  },
  {
    id: 2,
    name: 'react-hooks-library',
    description: 'A collection of useful React hooks for modern web development',
    language: 'TypeScript',
    languageColor: '#3178c6',
    stars: 1234,
    forks: 89,
    isPrivate: false,
    updatedAt: '3天前',
  },
  {
    id: 3,
    name: 'fastapi-starter',
    description: 'FastAPI project template with best practices and common configurations',
    language: 'Python',
    languageColor: '#3572A5',
    stars: 892,
    forks: 156,
    isPrivate: false,
    updatedAt: '1周前',
  },
  {
    id: 4,
    name: 'vue-dashboard',
    description: 'Modern admin dashboard built with Vue 3 and Element Plus',
    language: 'Vue',
    languageColor: '#42b883',
    stars: 567,
    forks: 78,
    isPrivate: false,
    updatedAt: '2周前',
  },
  {
    id: 5,
    name: 'internal-tools',
    description: 'Internal development tools and scripts',
    language: 'Python',
    languageColor: '#3572A5',
    stars: 12,
    forks: 2,
    isPrivate: true,
    updatedAt: '1个月前',
  },
])

/**
 * 活跃标签页
 */
const activeTab = ref('repositories')

/**
 * 排序选项
 */
const sortBy = ref('updated')
const sortOptions = [
  { key: 'updated', label: '最近更新' },
  { key: 'stars', label: '最多星标' },
  { key: 'name', label: '名称' },
]

/**
 * 排序后的仓库列表
 */
const sortedRepositories = computed(() => {
  const repos = [...userRepositories.value]
  switch (sortBy.value) {
    case 'stars':
      return repos.sort((a, b) => b.stars - a.stars)
    case 'name':
      return repos.sort((a, b) => a.name.localeCompare(b.name))
    default:
      return repos
  }
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
 * 最近活动列表
 */
const recentActivities = ref([
  { id: 1, type: 'commit', message: 'feat: add user authentication module', repo: 'perseus-core', time: '2小时前' },
  { id: 2, type: 'pr', message: 'Merge pull request #42 from feature/dashboard', repo: 'perseus-core', time: '5小时前' },
  { id: 3, type: 'star', message: 'Starred rust-lang/rust', repo: 'rust', time: '1天前' },
  { id: 4, type: 'fork', message: 'Forked vuejs/core', repo: 'vue', time: '2天前' },
  { id: 5, type: 'issue', message: 'Opened issue #123: Bug in navigation', repo: 'perseus-core', time: '3天前' },
])
</script>

<template>
  <NavLayout>
    <div class="profile-page">
      <div class="container">
        <!-- 个人资料头部 -->
        <header class="profile-header">
          <div class="profile-avatar">
            <span class="avatar-text">AC</span>
          </div>
          <div class="profile-info">
            <h1 class="profile-name">{{ userProfile.displayName }}</h1>
            <p class="profile-username">@{{ userProfile.username }}</p>
            <p class="profile-bio">{{ userProfile.bio }}</p>
            <div class="profile-meta">
              <span v-if="userProfile.location" class="meta-item">
                <el-icon><Location /></el-icon>
                {{ userProfile.location }}
              </span>
              <span v-if="userProfile.company" class="meta-item">
                <el-icon><OfficeBuilding /></el-icon>
                {{ userProfile.company }}
              </span>
              <span v-if="userProfile.website" class="meta-item">
                <el-icon><Link /></el-icon>
                <a :href="userProfile.website" target="_blank">{{ userProfile.website }}</a>
              </span>
              <span class="meta-item">
                <el-icon><Calendar /></el-icon>
                加入于 {{ userProfile.joinDate }}
              </span>
            </div>
            <div class="profile-stats">
              <router-link to="/profile/followers" class="stat-link">
                <strong>{{ formatNumber(userProfile.followers) }}</strong>
                <span>关注者</span>
              </router-link>
              <router-link to="/profile/following" class="stat-link">
                <strong>{{ formatNumber(userProfile.following) }}</strong>
                <span>关注中</span>
              </router-link>
            </div>
          </div>
          <div class="profile-actions">
            <el-button type="primary">关注</el-button>
            <el-button>私信</el-button>
          </div>
        </header>

        <!-- 贡献统计卡片 -->
        <section class="stats-section">
          <div class="stats-grid">
            <div class="stat-card">
              <div class="stat-icon" style="background: #e3f2fd; color: #1976d2;">
                <el-icon :size="24"><Collection /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ contributionStats.totalRepositories }}</div>
                <div class="stat-label">公开仓库</div>
              </div>
            </div>
            <div class="stat-card">
              <div class="stat-icon" style="background: #fff3e0; color: #f57c00;">
                <el-icon :size="24"><Star /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ formatNumber(contributionStats.starsEarned) }}</div>
                <div class="stat-label">获得星标</div>
              </div>
            </div>
            <div class="stat-card">
              <div class="stat-icon" style="background: #e8f5e9; color: #388e3c;">
                <el-icon :size="24"><Share /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ contributionStats.pullRequests }}</div>
                <div class="stat-label">合并请求</div>
              </div>
            </div>
            <div class="stat-card">
              <div class="stat-icon" style="background: #f3e5f5; color: #7b1fa2;">
                <el-icon :size="24"><UserFilled /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ formatNumber(contributionStats.totalCommits) }}</div>
                <div class="stat-label">代码提交</div>
              </div>
            </div>
          </div>
        </section>

        <!-- 贡献日历 -->
        <section class="contribution-section">
          <div class="contribution-card">
            <h2 class="section-title">贡献活动</h2>
            <div class="contribution-calendar">
              <div
                v-for="(day, index) in contributionCalendar"
                :key="index"
                class="contribution-day"
                :class="getContributionColor(day.count)"
                :title="`${day.date}: ${day.count} 次贡献`"
              />
            </div>
            <div class="contribution-legend">
              <span>少</span>
              <div class="legend-item level-0" />
              <div class="legend-item level-1" />
              <div class="legend-item level-2" />
              <div class="legend-item level-3" />
              <div class="legend-item level-4" />
              <span>多</span>
            </div>
          </div>
        </section>

        <!-- 标签页内容 -->
        <section class="content-section">
          <div class="content-card">
            <!-- 标签页头部 -->
            <div class="tabs-header">
              <div class="tabs-nav">
                <button
                  class="tab-btn"
                  :class="{ 'is-active': activeTab === 'repositories' }"
                  @click="activeTab = 'repositories'"
                >
                  <el-icon><Collection /></el-icon>
                  仓库
                  <span class="tab-count">{{ userRepositories.length }}</span>
                </button>
                <button
                  class="tab-btn"
                  :class="{ 'is-active': activeTab === 'activity' }"
                  @click="activeTab = 'activity'"
                >
                  <el-icon><Share /></el-icon>
                  动态
                </button>
              </div>
              <div v-if="activeTab === 'repositories'" class="tab-actions">
                <el-select v-model="sortBy" size="small" class="sort-select">
                  <el-option
                    v-for="option in sortOptions"
                    :key="option.key"
                    :label="option.label"
                    :value="option.key"
                  />
                </el-select>
              </div>
            </div>

            <!-- 仓库列表 -->
            <div v-if="activeTab === 'repositories'" class="repositories-list">
              <div
                v-for="repo in sortedRepositories"
                :key="repo.id"
                class="repository-item"
              >
                <div class="repo-main">
                  <div class="repo-header">
                    <h3 class="repo-name">
                      <router-link :to="`/code-viewer?repo=${repo.name}`">
                        {{ repo.name }}
                      </router-link>
                      <el-tag v-if="repo.isPrivate" size="small" effect="plain">私有</el-tag>
                    </h3>
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

            <!-- 动态列表 -->
            <div v-if="activeTab === 'activity'" class="activity-list">
              <div
                v-for="activity in recentActivities"
                :key="activity.id"
                class="activity-item"
              >
                <div class="activity-icon">
                  <el-icon v-if="activity.type === 'commit'"><Collection /></el-icon>
                  <el-icon v-else-if="activity.type === 'pr'"><Share /></el-icon>
                  <el-icon v-else-if="activity.type === 'star'"><Star /></el-icon>
                  <el-icon v-else-if="activity.type === 'fork'"><ForkSpoon /></el-icon>
                  <el-icon v-else><UserFilled /></el-icon>
                </div>
                <div class="activity-content">
                  <p class="activity-message">{{ activity.message }}</p>
                  <p class="activity-meta">
                    <router-link :to="`/code-viewer?repo=${activity.repo}`">
                      {{ activity.repo }}
                    </router-link>
                    · {{ activity.time }}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  </NavLayout>
</template>

<style scoped>
.profile-page {
  padding: var(--perseus-space-8) 0;
  min-height: calc(100vh - 64px);
  background: var(--perseus-surface);
}

.container {
  max-width: var(--perseus-container-max);
  margin: 0 auto;
  padding: 0 var(--perseus-container-gutter);
}

/* 个人资料头部 */
.profile-header {
  display: flex;
  gap: var(--perseus-space-6);
  margin-bottom: var(--perseus-space-8);
  padding: var(--perseus-space-8);
  background: var(--perseus-bg);
  border: 1px solid var(--perseus-border-soft);
  border-radius: var(--perseus-radius-lg);
}

.profile-avatar {
  flex-shrink: 0;
}

.avatar-text {
  width: 120px;
  height: 120px;
  border-radius: 50%;
  background: var(--perseus-accent);
  color: var(--perseus-accent-on);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 48px;
  font-weight: 600;
}

.profile-info {
  flex: 1;
}

.profile-name {
  font-size: var(--perseus-text-2xl);
  font-weight: 700;
  letter-spacing: var(--perseus-tracking-display);
  margin-bottom: var(--perseus-space-1);
}

.profile-username {
  font-size: var(--perseus-text-lg);
  color: var(--perseus-muted);
  margin-bottom: var(--perseus-space-3);
}

.profile-bio {
  font-size: var(--perseus-text-base);
  color: var(--perseus-fg-2);
  line-height: 1.6;
  margin-bottom: var(--perseus-space-4);
  max-width: 600px;
}

.profile-meta {
  display: flex;
  flex-wrap: wrap;
  gap: var(--perseus-space-4);
  margin-bottom: var(--perseus-space-4);
}

.meta-item {
  display: flex;
  align-items: center;
  gap: var(--perseus-space-1);
  font-size: var(--perseus-text-sm);
  color: var(--perseus-muted);
}

.meta-item a {
  color: var(--perseus-accent);
  text-decoration: none;
}

.meta-item a:hover {
  text-decoration: underline;
}

.profile-stats {
  display: flex;
  gap: var(--perseus-space-6);
}

.stat-link {
  display: flex;
  align-items: center;
  gap: var(--perseus-space-1);
  font-size: var(--perseus-text-sm);
  color: var(--perseus-fg-2);
  text-decoration: none;
}

.stat-link strong {
  font-weight: 600;
  color: var(--perseus-fg);
}

.stat-link:hover {
  color: var(--perseus-accent);
}

.profile-actions {
  display: flex;
  gap: var(--perseus-space-3);
  flex-shrink: 0;
}

/* 统计卡片 */
.stats-section {
  margin-bottom: var(--perseus-space-8);
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--perseus-space-4);
}

.stat-card {
  display: flex;
  align-items: center;
  gap: var(--perseus-space-4);
  padding: var(--perseus-space-5);
  background: var(--perseus-bg);
  border: 1px solid var(--perseus-border-soft);
  border-radius: var(--perseus-radius-lg);
  transition: box-shadow var(--perseus-motion-fast);
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
}

/* 贡献日历 */
.contribution-section {
  margin-bottom: var(--perseus-space-8);
}

.contribution-card {
  padding: var(--perseus-space-6);
  background: var(--perseus-bg);
  border: 1px solid var(--perseus-border-soft);
  border-radius: var(--perseus-radius-lg);
}

.section-title {
  font-size: var(--perseus-text-lg);
  font-weight: 600;
  margin-bottom: var(--perseus-space-5);
}

.contribution-calendar {
  display: grid;
  grid-template-columns: repeat(53, 1fr);
  gap: 3px;
  overflow-x: auto;
  padding-bottom: var(--perseus-space-3);
}

.contribution-day {
  aspect-ratio: 1;
  border-radius: 2px;
  background: var(--perseus-border-soft);
  min-width: 10px;
}

.contribution-day.level-1 {
  background: #9be9a8;
}

.contribution-day.level-2 {
  background: #40c463;
}

.contribution-day.level-3 {
  background: #30a14e;
}

.contribution-day.level-4 {
  background: #216e39;
}

.contribution-legend {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--perseus-space-1);
  margin-top: var(--perseus-space-3);
  font-size: var(--perseus-text-xs);
  color: var(--perseus-muted);
}

.legend-item {
  width: 10px;
  height: 10px;
  border-radius: 2px;
}

.legend-item.level-0 {
  background: var(--perseus-border-soft);
}

.legend-item.level-1 {
  background: #9be9a8;
}

.legend-item.level-2 {
  background: #40c463;
}

.legend-item.level-3 {
  background: #30a14e;
}

.legend-item.level-4 {
  background: #216e39;
}

/* 内容区 */
.content-card {
  background: var(--perseus-bg);
  border: 1px solid var(--perseus-border-soft);
  border-radius: var(--perseus-radius-lg);
  overflow: hidden;
}

.tabs-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--perseus-space-4) var(--perseus-space-6);
  border-bottom: 1px solid var(--perseus-border-soft);
}

.tabs-nav {
  display: flex;
  gap: var(--perseus-space-1);
}

.tab-btn {
  display: flex;
  align-items: center;
  gap: var(--perseus-space-2);
  padding: var(--perseus-space-2) var(--perseus-space-4);
  border: none;
  background: transparent;
  color: var(--perseus-fg-2);
  font-size: var(--perseus-text-sm);
  font-weight: 500;
  border-radius: var(--perseus-radius-md);
  cursor: pointer;
  transition: all var(--perseus-motion-fast);
}

.tab-btn:hover {
  background: var(--perseus-surface);
  color: var(--perseus-fg);
}

.tab-btn.is-active {
  background: var(--perseus-fg);
  color: var(--perseus-accent-on);
}

.tab-count {
  padding: 2px 6px;
  background: var(--perseus-border-soft);
  border-radius: var(--perseus-radius-pill);
  font-size: var(--perseus-text-xs);
}

.tab-btn.is-active .tab-count {
  background: rgba(255, 255, 255, 0.2);
}

.sort-select {
  width: 140px;
}

/* 仓库列表 */
.repositories-list {
  display: flex;
  flex-direction: column;
}

.repository-item {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--perseus-space-4);
  padding: var(--perseus-space-5) var(--perseus-space-6);
  border-bottom: 1px solid var(--perseus-border-soft);
  transition: background var(--perseus-motion-fast);
}

.repository-item:last-child {
  border-bottom: none;
}

.repository-item:hover {
  background: var(--perseus-surface);
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

.repo-description {
  font-size: var(--perseus-text-sm);
  color: var(--perseus-fg-2);
  margin-bottom: var(--perseus-space-3);
  line-height: 1.5;
}

.repo-meta {
  display: flex;
  align-items: center;
  gap: var(--perseus-space-4);
  font-size: var(--perseus-text-xs);
  color: var(--perseus-muted);
}

.language-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

/* 动态列表 */
.activity-list {
  display: flex;
  flex-direction: column;
}

.activity-item {
  display: flex;
  gap: var(--perseus-space-3);
  padding: var(--perseus-space-4) var(--perseus-space-6);
  border-bottom: 1px solid var(--perseus-border-soft);
}

.activity-item:last-child {
  border-bottom: none;
}

.activity-icon {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--perseus-surface);
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

.activity-meta {
  font-size: var(--perseus-text-xs);
  color: var(--perseus-muted);
}

.activity-meta a {
  color: var(--perseus-accent);
  text-decoration: none;
}

.activity-meta a:hover {
  text-decoration: underline;
}

/* 响应式 */
@media (max-width: 768px) {
  .profile-header {
    flex-direction: column;
    align-items: center;
    text-align: center;
    padding: var(--perseus-space-5);
  }

  .profile-meta {
    justify-content: center;
  }

  .profile-stats {
    justify-content: center;
  }

  .profile-actions {
    width: 100%;
    justify-content: center;
  }

  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .contribution-calendar {
    grid-template-columns: repeat(26, 1fr);
  }

  .tabs-header {
    flex-direction: column;
    gap: var(--perseus-space-3);
    align-items: flex-start;
  }

  .repository-item {
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
