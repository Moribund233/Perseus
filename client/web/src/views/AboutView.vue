<script setup lang="ts">
/**
 * 关于页面
 * 介绍 Perseus 项目背景、团队、愿景和开源信息
 */
import NavLayout from '@/components/layouts/NavLayout.vue'
import {
  Star,
  ForkSpoon,
  User,
  Document,
  Lock,
  SetUp,
  Connection,
} from '@element-plus/icons-vue'

/**
 * 项目统计数据
 */
const projectStats = [
  { label: 'GitHub Stars', value: '2.8k+', icon: Star },
  { label: 'Forks', value: '340+', icon: ForkSpoon },
  { label: 'Contributors', value: '50+', icon: User },
  { label: 'Releases', value: '24', icon: Document },
]

/**
 * 核心特性
 */
const coreFeatures = [
  {
    icon: Document,
    title: '开源免费',
    description: 'Perseus 是完全开源的项目，采用 MIT 许可证，任何人都可以免费使用、修改和分发。',
  },
  {
    icon: Lock,
    title: '安全可靠',
    description: '企业级的安全保障，包括代码扫描、依赖检测、访问控制，保护你的代码资产。',
  },
  {
    icon: SetUp,
    title: '高性能',
    description: '基于现代技术栈构建，优化的架构设计，确保流畅的用户体验和快速的响应速度。',
  },
  {
    icon: Connection,
    title: '社区驱动',
    description: '由活跃的开发者社区维护和贡献，持续迭代改进，聆听用户反馈。',
  },
]

/**
 * 核心团队
 */
const coreTeam = [
  {
    name: 'Alex Chen',
    role: '项目创始人',
    avatar: 'AC',
    github: 'alexchen',
  },
  {
    name: 'Sarah Li',
    role: '核心开发者',
    avatar: 'SL',
    github: 'sarahli',
  },
  {
    name: 'Mike Wang',
    role: '架构师',
    avatar: 'MW',
    github: 'mikewang',
  },
  {
    name: 'Emily Zhang',
    role: 'UI/UX 设计师',
    avatar: 'EZ',
    github: 'emilyzhang',
  },
]

/**
 * 技术栈
 */
const techStack = [
  { name: 'Vue 3', category: '前端框架', color: '#42b883' },
  { name: 'TypeScript', category: '语言', color: '#3178c6' },
  { name: 'Element Plus', category: 'UI 库', color: '#409eff' },
  { name: 'FastAPI', category: '后端框架', color: '#009688' },
  { name: 'PostgreSQL', category: '数据库', color: '#336791' },
  { name: 'Redis', category: '缓存', color: '#dc382d' },
  { name: 'Docker', category: '容器化', color: '#2496ed' },
  { name: 'Git', category: '版本控制', color: '#f05032' },
]

/**
 * 开源许可证
 */
const license = `MIT License

Copyright (c) 2024 Perseus Team

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.`
</script>

<template>
  <NavLayout>
    <div class="about-page">
      <!-- Hero Section -->
      <section class="hero-section">
        <div class="container">
          <div class="hero-content">
            <h1 class="hero-title">关于 Perseus</h1>
            <p class="hero-description">
              Perseus 是一个现代化的开源代码托管平台，致力于为开发者提供高效、安全、易用的代码管理和协作工具。
              我们相信开源的力量，因此 Perseus 完全免费，任何人都可以参与贡献。
            </p>
            <div class="hero-actions">
              <el-button type="primary" size="large">
                GitHub 仓库
              </el-button>
              <el-button size="large">
                参与贡献
              </el-button>
            </div>
          </div>
        </div>
      </section>

      <!-- 统计数据 -->
      <section class="stats-section">
        <div class="container">
          <div class="stats-grid">
            <div v-for="stat in projectStats" :key="stat.label" class="stat-card">
              <el-icon class="stat-icon" :size="32">
                <component :is="stat.icon" />
              </el-icon>
              <div class="stat-value">{{ stat.value }}</div>
              <div class="stat-label">{{ stat.label }}</div>
            </div>
          </div>
        </div>
      </section>

      <!-- 核心特性 -->
      <section class="features-section">
        <div class="container">
          <h2 class="section-title">为什么选择 Perseus</h2>
          <div class="features-grid">
            <div v-for="feature in coreFeatures" :key="feature.title" class="feature-card">
              <div class="feature-icon">
                <el-icon :size="28">
                  <component :is="feature.icon" />
                </el-icon>
              </div>
              <h3 class="feature-title">{{ feature.title }}</h3>
              <p class="feature-description">{{ feature.description }}</p>
            </div>
          </div>
        </div>
      </section>

      <!-- 技术栈 -->
      <section class="tech-section">
        <div class="container">
          <h2 class="section-title">技术栈</h2>
          <p class="section-subtitle">Perseus 基于现代化的技术栈构建</p>
          <div class="tech-grid">
            <div
              v-for="tech in techStack"
              :key="tech.name"
              class="tech-card"
            >
              <div class="tech-dot" :style="{ backgroundColor: tech.color }" />
              <div class="tech-info">
                <div class="tech-name">{{ tech.name }}</div>
                <div class="tech-category">{{ tech.category }}</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- 核心团队 -->
      <section class="team-section">
        <div class="container">
          <h2 class="section-title">核心团队</h2>
          <p class="section-subtitle">感谢这些优秀的开发者</p>
          <div class="team-grid">
            <div v-for="member in coreTeam" :key="member.name" class="team-card">
              <div class="team-avatar">{{ member.avatar }}</div>
              <h3 class="team-name">{{ member.name }}</h3>
              <p class="team-role">{{ member.role }}</p>
              <a :href="`https://github.com/${member.github}`" class="team-github" target="_blank">
                @{{ member.github }}
              </a>
            </div>
          </div>
        </div>
      </section>

      <!-- 参与贡献 -->
      <section class="contribute-section">
        <div class="container">
          <div class="contribute-card">
            <div class="contribute-content">
              <h2 class="contribute-title">
                参与贡献
              </h2>
              <p class="contribute-desc">
                Perseus 是一个社区驱动的开源项目。无论你是开发者、设计师还是文档撰写者，
                我们都欢迎你的贡献。一起打造更好的代码托管平台！
              </p>
              <div class="contribute-actions">
                <el-button type="primary" size="large">
                  查看贡献指南
                </el-button>
                <el-button size="large">
                  报告问题
                </el-button>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- 许可证 -->
      <section class="license-section">
        <div class="container">
          <h2 class="section-title">开源许可证</h2>
          <div class="license-card">
            <pre class="license-text">{{ license }}</pre>
          </div>
        </div>
      </section>

      <!-- 页脚信息 -->
      <footer class="about-footer">
        <div class="container">
          <p class="footer-copyright">© 2024 Perseus. All rights reserved.</p>
        </div>
      </footer>
    </div>
  </NavLayout>
</template>

<style scoped>
.about-page {
  background: var(--perseus-surface);
  min-height: calc(100vh - 64px);
}

.container {
  max-width: var(--perseus-container-max);
  margin: 0 auto;
  padding: 0 var(--perseus-container-gutter);
}

/* Hero Section */
.hero-section {
  padding: var(--perseus-space-16) 0;
  text-align: center;
  background: linear-gradient(180deg, var(--perseus-bg) 0%, var(--perseus-surface) 100%);
}

.hero-title {
  font-size: var(--perseus-text-3xl);
  font-weight: 700;
  letter-spacing: var(--perseus-tracking-display);
  margin-bottom: var(--perseus-space-5);
}

.hero-description {
  font-size: var(--perseus-text-lg);
  color: var(--perseus-fg-2);
  line-height: var(--perseus-leading-body);
  max-width: 720px;
  margin: 0 auto var(--perseus-space-6);
}

.hero-actions {
  display: flex;
  justify-content: center;
  gap: var(--perseus-space-3);
}

/* 统计数据 */
.stats-section {
  padding: var(--perseus-space-8) 0;
  background: var(--perseus-bg);
  border-top: 1px solid var(--perseus-border-soft);
  border-bottom: 1px solid var(--perseus-border-soft);
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--perseus-space-6);
}

.stat-card {
  text-align: center;
  padding: var(--perseus-space-6);
}

.stat-icon {
  color: var(--perseus-accent);
  margin-bottom: var(--perseus-space-3);
}

.stat-value {
  font-size: var(--perseus-text-2xl);
  font-weight: 700;
  margin-bottom: var(--perseus-space-1);
}

.stat-label {
  font-size: var(--perseus-text-sm);
  color: var(--perseus-muted);
}

/* 通用 Section 样式 */
section {
  padding: var(--perseus-space-16) 0;
}

.section-title {
  font-size: var(--perseus-text-2xl);
  font-weight: 700;
  text-align: center;
  margin-bottom: var(--perseus-space-3);
}

.section-subtitle {
  font-size: var(--perseus-text-base);
  color: var(--perseus-muted);
  text-align: center;
  margin-bottom: var(--perseus-space-10);
}

/* 核心特性 */
.features-section {
  background: var(--perseus-surface);
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--perseus-space-6);
}

.feature-card {
  background: var(--perseus-bg);
  border: 1px solid var(--perseus-border-soft);
  border-radius: var(--perseus-radius-lg);
  padding: var(--perseus-space-8);
  transition: all var(--perseus-motion-fast);
}

.feature-card:hover {
  border-color: var(--perseus-border);
  box-shadow: var(--perseus-elev-raised);
}

.feature-icon {
  width: 56px;
  height: 56px;
  border-radius: var(--perseus-radius-md);
  background: var(--perseus-surface-warm);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--perseus-accent);
  margin-bottom: var(--perseus-space-4);
}

.feature-title {
  font-size: var(--perseus-text-lg);
  font-weight: 600;
  margin-bottom: var(--perseus-space-2);
}

.feature-description {
  font-size: var(--perseus-text-sm);
  color: var(--perseus-fg-2);
  line-height: var(--perseus-leading-body);
}

/* 技术栈 */
.tech-section {
  background: var(--perseus-bg);
}

.tech-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--perseus-space-4);
}

.tech-card {
  display: flex;
  align-items: center;
  gap: var(--perseus-space-3);
  padding: var(--perseus-space-4);
  background: var(--perseus-surface);
  border: 1px solid var(--perseus-border-soft);
  border-radius: var(--perseus-radius-md);
  transition: all var(--perseus-motion-fast);
}

.tech-card:hover {
  border-color: var(--perseus-border);
}

.tech-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  flex-shrink: 0;
}

.tech-name {
  font-size: var(--perseus-text-sm);
  font-weight: 600;
}

.tech-category {
  font-size: var(--perseus-text-xs);
  color: var(--perseus-muted);
}

/* 核心团队 */
.team-section {
  background: var(--perseus-surface);
}

.team-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--perseus-space-6);
}

.team-card {
  text-align: center;
  padding: var(--perseus-space-6);
  background: var(--perseus-bg);
  border: 1px solid var(--perseus-border-soft);
  border-radius: var(--perseus-radius-lg);
  transition: all var(--perseus-motion-fast);
}

.team-card:hover {
  border-color: var(--perseus-border);
  box-shadow: var(--perseus-elev-raised);
}

.team-avatar {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: var(--perseus-surface-warm);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--perseus-text-xl);
  font-weight: 600;
  color: var(--perseus-fg);
  margin: 0 auto var(--perseus-space-4);
}

.team-name {
  font-size: var(--perseus-text-base);
  font-weight: 600;
  margin-bottom: var(--perseus-space-1);
}

.team-role {
  font-size: var(--perseus-text-sm);
  color: var(--perseus-muted);
  margin-bottom: var(--perseus-space-3);
}

.team-github {
  display: inline-flex;
  align-items: center;
  gap: var(--perseus-space-1);
  font-size: var(--perseus-text-sm);
  color: var(--perseus-accent);
  text-decoration: none;
}

.team-github:hover {
  text-decoration: underline;
}

/* 参与贡献 */
.contribute-section {
  background: var(--perseus-bg);
  padding: var(--perseus-space-8) 0;
}

.contribute-card {
  background: var(--perseus-fg);
  color: var(--perseus-accent-on);
  border-radius: var(--perseus-radius-lg);
  padding: var(--perseus-space-10);
}

.contribute-content {
  max-width: 640px;
  margin: 0 auto;
  text-align: center;
}

.contribute-title {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--perseus-space-3);
  font-size: var(--perseus-text-2xl);
  font-weight: 700;
  margin-bottom: var(--perseus-space-4);
}

.contribute-title .el-icon {
  color: #ff6b6b;
}

.contribute-desc {
  font-size: var(--perseus-text-base);
  color: rgba(255, 255, 255, 0.8);
  line-height: var(--perseus-leading-body);
  margin-bottom: var(--perseus-space-6);
}

.contribute-actions {
  display: flex;
  justify-content: center;
  gap: var(--perseus-space-3);
}

/* 许可证 */
.license-section {
  background: var(--perseus-surface);
  padding-bottom: var(--perseus-space-8);
}

.license-card {
  max-width: 800px;
  margin: 0 auto;
  background: var(--perseus-bg);
  border: 1px solid var(--perseus-border-soft);
  border-radius: var(--perseus-radius-lg);
  padding: var(--perseus-space-6);
}

.license-text {
  font-family: var(--perseus-font-mono);
  font-size: var(--perseus-text-sm);
  color: var(--perseus-fg-2);
  line-height: 1.6;
  white-space: pre-wrap;
  margin: 0;
}

/* 页脚 */
.about-footer {
  background: var(--perseus-fg);
  color: var(--perseus-accent-on);
  padding: var(--perseus-space-8) 0;
  text-align: center;
}

.footer-text {
  font-size: var(--perseus-text-base);
  margin-bottom: var(--perseus-space-2);
}

.heart-icon {
  color: #ff6b6b;
  vertical-align: middle;
}

.footer-copyright {
  font-size: var(--perseus-text-sm);
  color: rgba(255, 255, 255, 0.6);
}

/* 响应式 */
@media (max-width: 1024px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .tech-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .team-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .hero-section {
    padding: var(--perseus-space-10) 0;
  }

  .hero-title {
    font-size: var(--perseus-text-2xl);
  }

  .hero-description {
    font-size: var(--perseus-text-base);
  }

  .hero-actions {
    flex-direction: column;
  }

  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: var(--perseus-space-4);
  }

  .stat-card {
    padding: var(--perseus-space-4);
  }

  .features-grid {
    grid-template-columns: 1fr;
  }

  .tech-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .team-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .contribute-card {
    padding: var(--perseus-space-6);
  }

  .contribute-actions {
    flex-direction: column;
  }

  section {
    padding: var(--perseus-space-10) 0;
  }
}

@media (max-width: 480px) {
  .stats-grid,
  .tech-grid,
  .team-grid {
    grid-template-columns: 1fr;
  }
}
</style>
