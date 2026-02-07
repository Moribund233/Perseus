<template>
  <div class="home-page scrollbar-hide scroll-smooth">
    <div class="page-header">
      <h1>欢迎使用 LanGit</h1>
      <p class="page-description">局域网Git服务器 - 轻松管理团队代码协作</p>
    </div>
    
    <div class="cards-container">
      <!-- 系统概述卡片 -->
      <Card title="系统概述" usage="display">
        <p>LanGit 提供了一套完整的局域网Git服务器解决方案，支持团队在本地网络中共享和管理代码仓库。</p>
        <div class="system-features">
          <div class="feature-item">
            <div class="feature-icon">🔧</div>
            <div class="feature-content">
              <h4>轻量级部署</h4>
              <p>基于 FastAPI + Vue3 构建，部署简单，性能优异</p>
            </div>
          </div>
          <div class="feature-item">
            <div class="feature-icon">🌐</div>
            <div class="feature-content">
              <h4>局域网共享</h4>
              <p>支持在同一网络内的多设备访问和协作开发</p>
            </div>
          </div>
          <div class="feature-item">
            <div class="feature-icon">🔒</div>
            <div class="feature-content">
              <h4>安全控制</h4>
              <p>内置防火墙配置，保护您的代码安全</p>
            </div>
          </div>
        </div>
      </Card>
      
      <!-- 快速操作卡片 -->
      <Card title="快速操作" usage="default">
        <div class="quick-actions">
          <button class="action-btn">
            <span class="btn-icon">▶️</span>
            <span class="btn-text">启动服务</span>
          </button>
          <button class="action-btn">
            <span class="btn-icon">⏹️</span>
            <span class="btn-text">停止服务</span>
          </button>
          <button class="action-btn">
            <span class="btn-icon">🔄</span>
            <span class="btn-text">重启服务</span>
          </button>
          <button class="action-btn">
            <span class="btn-icon">📊</span>
            <span class="btn-text">服务状态</span>
          </button>
        </div>
      </Card>
      
      <!-- 服务信息卡片 -->
      <Card title="服务信息" usage="data">
        <div class="service-info">
          <div class="info-item">
            <span class="info-label">服务地址</span>
            <span class="info-value" id="service-url">未启动</span>
          </div>
          <div class="info-item">
            <span class="info-label">连接状态</span>
            <span class="info-value" id="connection-status">离线</span>
          </div>
          <div class="info-item">
            <span class="info-label">API文档</span>
            <span class="info-value">
              <a href="#" id="api-docs-link">/docs</a>
            </span>
          </div>
        </div>
      </Card>
      
      <!-- 最近活动卡片 -->
      <Card title="最近活动" usage="data">
        <div class="activity-list">
          <div class="activity-item">
            <div class="activity-time">系统启动</div>
            <div class="activity-content">服务初始化完成，等待连接</div>
          </div>
          <div class="activity-item">
            <div class="activity-time">准备就绪</div>
            <div class="activity-content">点击启动服务开始使用</div>
          </div>
        </div>
      </Card>
      
      <!-- 开发文档卡片 -->
      <Card title="开发文档" usage="display">
        <div class="docs-list">
          <a href="#" class="docs-item">
            <span class="docs-icon">📖</span>
            <span class="docs-title">API 文档</span>
            <span class="docs-arrow">→</span>
          </a>
          <a href="#" class="docs-item">
            <span class="docs-icon">⚙️</span>
            <span class="docs-title">配置说明</span>
            <span class="docs-arrow">→</span>
          </a>
          <a href="#" class="docs-item">
            <span class="docs-icon">🔧</span>
            <span class="docs-title">使用指南</span>
            <span class="docs-arrow">→</span>
          </a>
          <a href="#" class="docs-item">
            <span class="docs-icon">📝</span>
            <span class="docs-title">更新日志</span>
            <span class="docs-arrow">→</span>
          </a>
        </div>
      </Card>
      
      <!-- 关于卡片 -->
      <Card title="关于" usage="display">
        <div class="about-content">
          <p><strong>LanGit</strong> - 局域网Git服务器</p>
          <p>版本: 1.0.0</p>
          <p class="about-desc">专为团队协作设计的轻量级Git服务器解决方案</p>
        </div>
      </Card>
    </div>
  </div>
</template>

<script setup lang="ts">
import Card from '@/components/public/Card.vue';
</script>

<style scoped>
.home-page {
  padding: 24px;
  min-height: 100%;
  background: var(--color-main-content-bg);
}

.page-header {
  margin-bottom: 32px;
  text-align: center;
}

.page-header h1 {
  font-size: 2.5rem;
  color: var(--color-text);
  margin-bottom: 8px;
}

.page-description {
  font-size: 1.1rem;
  color: var(--color-text-secondary);
  margin: 0;
}

.cards-container {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  justify-content: center;
}

/* 系统特性样式 */
.system-features {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-top: 16px;
}

.feature-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px;
  background-color: var(--color-card-divider);
  border-radius: var(--radius-sm);
  transition: background-color var(--transition-fast);
}

.feature-item:hover {
  background-color: var(--color-hover);
}

.feature-icon {
  font-size: 1.5rem;
  margin-top: 2px;
}

.feature-content h4 {
  margin: 0 0 4px 0;
  font-size: 1rem;
  color: var(--color-text);
}

.feature-content p {
  margin: 0;
  font-size: 0.9rem;
  color: var(--color-text-secondary);
}

/* 快速操作样式 */
.quick-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-top: 16px;
}

.action-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 16px;
  background-color: var(--color-card-divider);
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all var(--transition-fast);
  gap: 8px;
}

.action-btn:hover {
  background-color: var(--color-hover);
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.btn-icon {
  font-size: 1.5rem;
}

.btn-text {
  font-size: 0.9rem;
  color: var(--color-text);
}

/* 服务信息样式 */
.service-info {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 16px;
}

.info-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background-color: var(--color-card-divider);
  border-radius: var(--radius-sm);
}

.info-label {
  font-size: 0.9rem;
  color: var(--color-text-secondary);
}

.info-value {
  font-size: 0.9rem;
  color: var(--color-text);
  font-weight: 500;
}

.info-value a {
  color: var(--color-primary);
  text-decoration: none;
}

.info-value a:hover {
  text-decoration: underline;
}

/* 最近活动样式 */
.activity-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 16px;
}

.activity-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background-color: var(--color-card-divider);
  border-radius: var(--radius-sm);
}

.activity-time {
  font-size: 0.8rem;
  color: var(--color-text-secondary);
  min-width: 80px;
}

.activity-content {
  font-size: 0.9rem;
  color: var(--color-text);
  flex: 1;
  margin-left: 16px;
}

/* 开发文档样式 */
.docs-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 16px;
}

.docs-item {
  display: flex;
  align-items: center;
  padding: 12px;
  background-color: var(--color-card-divider);
  border-radius: var(--radius-sm);
  text-decoration: none;
  transition: all var(--transition-fast);
  gap: 12px;
}

.docs-item:hover {
  background-color: var(--color-hover);
  transform: translateX(4px);
}

.docs-icon {
  font-size: 1.2rem;
}

.docs-title {
  flex: 1;
  color: var(--color-text);
  font-size: 0.9rem;
}

.docs-arrow {
  color: var(--color-text-secondary);
  font-size: 0.8rem;
}

/* 关于样式 */
.about-content {
  margin-top: 16px;
}

.about-content p {
  margin: 8px 0;
  font-size: 0.9rem;
  color: var(--color-text);
}

.about-desc {
  color: var(--color-text-secondary) !important;
  font-size: 0.85rem !important;
}

/* 响应式设计 */
@media (min-width: 768px) {
  .cards-container {
    justify-content: flex-start;
  }
  
  .card-container {
    width: calc(50% - 10px);
  }
}

@media (min-width: 1200px) {
  .card-container {
    width: calc(33.333% - 13.333px);
  }
}
</style>
