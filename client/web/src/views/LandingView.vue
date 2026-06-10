<script setup lang="ts">
/**
 * 落地页
 * 参考原型: landing.html
 */
import { ref } from 'vue'
import NavLayout from '@/components/layouts/NavLayout.vue'
import {
  Connection,
  UserFilled,
  SetUp,
  Lock,
  ArrowRight,
  Check,
} from '@element-plus/icons-vue'

const features = ref([
  {
    icon: Connection,
    title: 'Git 原生支持',
    description: '完整的 Git 工作流支持，包括分支、标签、合并请求等，让版本控制更加高效。',
    color: '#1976d2',
  },
  {
    icon: UserFilled,
    title: '高效协作',
    description: '代码审查、问题跟踪、Wiki 文档，一站式团队协作，提升开发效率。',
    color: '#388e3c',
  },
  {
    icon: SetUp,
    title: '持续集成',
    description: '内置 CI/CD 流水线，自动化构建、测试和部署，加速软件交付。',
    color: '#f57c00',
  },
  {
    icon: Lock,
    title: '安全可靠',
    description: '企业级安全保障，代码扫描、依赖检测、访问控制，保护你的代码资产。',
    color: '#7b1fa2',
  },
])

const highlights = ref([
  '无限公共和私有仓库',
  '团队协作工具',
  '自动化工作流',
  '企业级安全',
  '24/7 技术支持',
  '99.9% 可用性保证',
])
</script>

<template>
  <NavLayout>
    <div class="landing-page">
      <!-- Hero Section -->
      <section class="hero">
        <div class="hero-content">
          <h1 class="hero-title">
            为开发者打造的
            <br />
            <span class="highlight">现代代码托管平台</span>
          </h1>
          <p class="hero-description">
            Perseus 提供强大的代码管理、协作和部署工具，帮助团队更高效地构建软件。
            无论你是个人开发者还是大型企业，Perseus 都能满足你的需求。
          </p>
          <div class="hero-actions">
            <el-button type="primary" size="large" class="cta-primary">
              开始使用
              <el-icon class="el-icon--right"><ArrowRight /></el-icon>
            </el-button>
            <el-button size="large" class="cta-secondary">
              了解更多
            </el-button>
          </div>
          <div class="hero-stats">
            <div class="stat">
              <div class="stat-value">10M+</div>
              <div class="stat-label">开发者</div>
            </div>
            <div class="stat">
              <div class="stat-value">50M+</div>
              <div class="stat-label">仓库</div>
            </div>
            <div class="stat">
              <div class="stat-value">99.9%</div>
              <div class="stat-label">可用性</div>
            </div>
          </div>
        </div>
        <div class="hero-visual">
          <div class="code-preview">
            <div class="code-header">
              <div class="code-dots">
                <span class="dot red"></span>
                <span class="dot yellow"></span>
                <span class="dot green"></span>
              </div>
              <span class="code-title">perseus-core</span>
            </div>
            <div class="code-body">
              <pre><code>$ git clone https://perseus.dev/user/repo.git
Cloning into 'repo'...
remote: Enumerating objects: 1024, done.
remote: Counting objects: 100% (1024/1024), done.
remote: Compressing objects: 100% (512/512), done.
Receiving objects: 100% (1024/1024), 2.5 MiB/s, done.
Resolving deltas: 100% (256/256), done.

$ cd repo
$ perseus init
✓ Repository initialized
✓ CI/CD configured
✓ Ready to deploy</code></pre>
            </div>
          </div>
        </div>
      </section>

      <!-- Features Section -->
      <section class="features">
        <div class="container">
          <div class="section-header">
            <h2 class="section-title">为什么选择 Perseus</h2>
            <p class="section-subtitle">
              我们提供全面的工具链，让你的开发工作更加顺畅
            </p>
          </div>
          <div class="features-grid">
            <div
              v-for="feature in features"
              :key="feature.title"
              class="feature-card"
            >
              <div
                class="feature-icon"
                :style="{ backgroundColor: feature.color + '15', color: feature.color }"
              >
                <el-icon :size="32">
                  <component :is="feature.icon" />
                </el-icon>
              </div>
              <h3 class="feature-title">{{ feature.title }}</h3>
              <p class="feature-description">{{ feature.description }}</p>
            </div>
          </div>
        </div>
      </section>

      <!-- Highlights Section -->
      <section class="highlights">
        <div class="container">
          <div class="highlights-content">
            <div class="highlights-text">
              <h2 class="section-title">企业级功能，免费开始使用</h2>
              <p class="section-subtitle">
                Perseus 提供丰富的功能，无论你是个人开发者还是企业团队，都能找到适合的方案。
              </p>
              <ul class="highlights-list">
                <li v-for="item in highlights" :key="item">
                  <el-icon class="check-icon"><Check /></el-icon>
                  {{ item }}
                </li>
              </ul>
              <el-button type="primary" size="large" class="cta-button">
                免费注册
              </el-button>
            </div>
            <div class="highlights-visual">
              <div class="dashboard-preview">
                <div class="preview-card">
                  <div class="preview-header">
                    <div class="preview-avatar">P</div>
                    <div class="preview-info">
                      <div class="preview-name">perseus-core</div>
                      <div class="preview-meta">TypeScript · 2.8k stars</div>
                    </div>
                  </div>
                  <div class="preview-chart">
                    <div class="chart-bar" style="height: 40%"></div>
                    <div class="chart-bar" style="height: 60%"></div>
                    <div class="chart-bar" style="height: 80%"></div>
                    <div class="chart-bar" style="height: 50%"></div>
                    <div class="chart-bar" style="height: 90%"></div>
                    <div class="chart-bar" style="height: 70%"></div>
                    <div class="chart-bar" style="height: 100%"></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- CTA Section -->
      <section class="cta-section">
        <div class="container">
          <div class="cta-content">
            <h2 class="cta-title">准备好开始了吗？</h2>
            <p class="cta-description">
              加入数百万开发者的行列，使用 Perseus 构建更好的软件。
            </p>
            <div class="cta-actions">
              <el-button type="primary" size="large" class="cta-primary">
                免费开始使用
              </el-button>
              <el-button size="large" class="cta-secondary">
                联系销售
              </el-button>
            </div>
          </div>
        </div>
      </section>

      <!-- Footer -->
      <footer class="footer">
        <div class="container">
          <div class="footer-content">
            <div class="footer-brand">
              <div class="brand-icon">
                <svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor">
                  <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
                </svg>
              </div>
              <span class="brand-text">Perseus</span>
            </div>
            <p class="footer-copyright">
              © 2026 Perseus. All rights reserved.
            </p>
          </div>
        </div>
      </footer>
    </div>
  </NavLayout>
</template>

<style scoped>
.landing-page {
  --section-padding: 112px;
}

.container {
  max-width: 1120px;
  margin: 0 auto;
  padding: 0 36px;
}

/* Hero Section */
.hero {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 64px;
  align-items: center;
  padding: var(--section-padding) 36px;
  max-width: 1200px;
  margin: 0 auto;
}

.hero-title {
  font-size: 64px;
  font-weight: 700;
  line-height: 1.08;
  letter-spacing: -0.02em;
  margin-bottom: 24px;
}

.hero-title .highlight {
  color: var(--perseus-accent);
}

.hero-description {
  font-size: 18px;
  color: var(--perseus-muted);
  line-height: 1.6;
  margin-bottom: 32px;
  max-width: 480px;
}

.hero-actions {
  display: flex;
  gap: 16px;
  margin-bottom: 48px;
}

.cta-primary {
  background: var(--perseus-accent);
  border-color: var(--perseus-accent);
  padding: 16px 32px;
  font-size: 16px;
}

.cta-secondary {
  border-color: var(--perseus-border);
  padding: 16px 32px;
  font-size: 16px;
}

.hero-stats {
  display: flex;
  gap: 48px;
}

.stat-value {
  font-size: 32px;
  font-weight: 700;
  color: var(--perseus-fg);
}

.stat-label {
  font-size: 14px;
  color: var(--perseus-muted);
}

/* Code Preview */
.hero-visual {
  display: flex;
  justify-content: center;
}

.code-preview {
  background: #1a1a1a;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
  width: 100%;
  max-width: 480px;
}

.code-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 20px;
  background: #252525;
  border-bottom: 1px solid #333;
}

.code-dots {
  display: flex;
  gap: 8px;
}

.dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
}

.dot.red { background: #ff5f56; }
.dot.yellow { background: #ffbd2e; }
.dot.green { background: #27c93f; }

.code-title {
  font-size: 14px;
  color: #888;
  font-family: var(--perseus-font-mono);
}

.code-body {
  padding: 20px;
  overflow-x: auto;
}

.code-body pre {
  margin: 0;
  font-family: var(--perseus-font-mono);
  font-size: 13px;
  line-height: 1.6;
  color: #e6e6e6;
}

.code-body code {
  font-family: inherit;
  background: transparent;
  padding: 0;
}

/* Features Section */
.features {
  padding: var(--section-padding) 0;
  background: var(--perseus-surface);
}

.section-header {
  text-align: center;
  margin-bottom: 64px;
}

.section-title {
  font-size: 40px;
  font-weight: 700;
  letter-spacing: -0.02em;
  margin-bottom: 16px;
}

.section-subtitle {
  font-size: 18px;
  color: var(--perseus-muted);
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 24px;
}

.feature-card {
  background: var(--perseus-bg);
  border: 1px solid var(--perseus-border-soft);
  border-radius: 12px;
  padding: 32px;
  transition: all 0.2s ease;
}

.feature-card:hover {
  border-color: var(--perseus-border);
  box-shadow: 0 12px 30px rgba(0, 0, 0, 0.08);
}

.feature-icon {
  width: 64px;
  height: 64px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 24px;
}

.feature-title {
  font-size: 20px;
  font-weight: 600;
  margin-bottom: 12px;
}

.feature-description {
  font-size: 14px;
  color: var(--perseus-muted);
  line-height: 1.6;
}

/* Highlights Section */
.highlights {
  padding: var(--section-padding) 0;
}

.highlights-content {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 64px;
  align-items: center;
}

.highlights-text .section-title {
  text-align: left;
  margin-bottom: 16px;
}

.highlights-text .section-subtitle {
  text-align: left;
  margin-bottom: 32px;
}

.highlights-list {
  list-style: none;
  padding: 0;
  margin: 0 0 32px 0;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.highlights-list li {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 16px;
  color: var(--perseus-fg-2);
}

.check-icon {
  color: var(--perseus-success);
}

/* Dashboard Preview */
.dashboard-preview {
  display: flex;
  justify-content: center;
}

.preview-card {
  background: var(--perseus-bg);
  border: 1px solid var(--perseus-border-soft);
  border-radius: 12px;
  padding: 24px;
  width: 100%;
  max-width: 360px;
  box-shadow: 0 12px 30px rgba(0, 0, 0, 0.08);
}

.preview-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
}

.preview-avatar {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: var(--perseus-accent);
  color: var(--perseus-accent-on);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 20px;
}

.preview-name {
  font-weight: 600;
  font-size: 16px;
  margin-bottom: 4px;
}

.preview-meta {
  font-size: 14px;
  color: var(--perseus-muted);
}

.preview-chart {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  height: 120px;
}

.chart-bar {
  flex: 1;
  background: var(--perseus-accent);
  border-radius: 4px 4px 0 0;
  opacity: 0.8;
  transition: opacity 0.2s;
}

.chart-bar:hover {
  opacity: 1;
}

/* CTA Section */
.cta-section {
  padding: var(--section-padding) 0;
  background: var(--perseus-surface);
}

.cta-content {
  text-align: center;
  max-width: 600px;
  margin: 0 auto;
}

.cta-title {
  font-size: 40px;
  font-weight: 700;
  letter-spacing: -0.02em;
  margin-bottom: 16px;
}

.cta-description {
  font-size: 18px;
  color: var(--perseus-muted);
  margin-bottom: 32px;
}

.cta-actions {
  display: flex;
  justify-content: center;
  gap: 16px;
}

/* Footer */
.footer {
  padding: 48px 0;
  border-top: 1px solid var(--perseus-border-soft);
}

.footer-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.footer-brand {
  display: flex;
  align-items: center;
  gap: 12px;
}

.brand-icon {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: var(--perseus-accent);
  color: var(--perseus-accent-on);
  display: flex;
  align-items: center;
  justify-content: center;
}

.brand-text {
  font-size: 18px;
  font-weight: 600;
}

.footer-copyright {
  font-size: 14px;
  color: var(--perseus-muted);
}

/* Responsive */
@media (max-width: 1024px) {
  .hero {
    grid-template-columns: 1fr;
    text-align: center;
  }

  .hero-title {
    font-size: 48px;
  }

  .hero-description {
    margin-left: auto;
    margin-right: auto;
  }

  .hero-actions {
    justify-content: center;
  }

  .hero-stats {
    justify-content: center;
  }

  .features-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .highlights-content {
    grid-template-columns: 1fr;
  }

  .highlights-text .section-title,
  .highlights-text .section-subtitle {
    text-align: center;
  }

  .highlights-list {
    max-width: 480px;
    margin-left: auto;
    margin-right: auto;
  }

  .cta-button {
    display: block;
    margin: 0 auto;
  }
}

@media (max-width: 640px) {
  .container {
    padding: 0 16px;
  }

  .hero {
    padding: 56px 16px;
  }

  .hero-title {
    font-size: 32px;
  }

  .section-title {
    font-size: 28px;
  }

  .features-grid {
    grid-template-columns: 1fr;
  }

  .highlights-list {
    grid-template-columns: 1fr;
  }

  .hero-actions,
  .cta-actions {
    flex-direction: column;
  }

  .footer-content {
    flex-direction: column;
    gap: 16px;
    text-align: center;
  }
}
</style>
