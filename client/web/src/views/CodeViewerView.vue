<script setup lang="ts">
/**
 * 代码查看器页面
 * 参考原型: code-viewer.html
 */
import { ref, computed } from 'vue'
import {
  ArrowLeft,
  Search,
  CopyDocument,
  Download,
  FullScreen,
  Document,
  CaretRight,
  CaretBottom,
  Clock,
  User,
  Collection,
  Link,
} from '@element-plus/icons-vue'

// 文件树数据
interface FileNode {
  name: string
  type: 'file' | 'directory'
  path: string
  children?: FileNode[]
  isOpen?: boolean
}

const fileTree = ref<FileNode[]>(([
  {
    name: 'src',
    type: 'directory',
    path: 'src',
    isOpen: true,
    children: [
      {
        name: 'core',
        type: 'directory',
        path: 'src/core',
        isOpen: true,
        children: [
          { name: 'forge.ts', type: 'file', path: 'src/core/forge.ts' },
          { name: 'config.ts', type: 'file', path: 'src/core/config.ts' },
        ],
      },
      {
        name: 'utils',
        type: 'directory',
        path: 'src/utils',
        children: [
          { name: 'helpers.ts', type: 'file', path: 'src/utils/helpers.ts' },
          { name: 'constants.ts', type: 'file', path: 'src/utils/constants.ts' },
        ],
      },
      { name: 'main.ts', type: 'file', path: 'src/main.ts' },
      { name: 'types.ts', type: 'file', path: 'src/types.ts' },
    ],
  },
  {
    name: 'tests',
    type: 'directory',
    path: 'tests',
    children: [
      { name: 'forge.test.ts', type: 'file', path: 'tests/forge.test.ts' },
    ],
  },
  { name: 'package.json', type: 'file', path: 'package.json' },
  { name: 'tsconfig.json', type: 'file', path: 'tsconfig.json' },
  { name: 'README.md', type: 'file', path: 'README.md' },
]))

const selectedFile = ref('src/core/forge.ts')
const searchQuery = ref('')

// 模拟代码内容
const codeContent = ref(`/**
 * Forge Core - 核心模块
 * 提供代码仓库管理的基础功能
 */

export interface Repository {
  id: string
  name: string
  description: string
  isPrivate: boolean
  defaultBranch: string
  createdAt: Date
  updatedAt: Date
}

export interface Commit {
  hash: string
  message: string
  author: string
  email: string
  timestamp: Date
  parents: string[]
}

export class Forge {
  private repositories: Map<string, Repository> = new Map()

  /**
   * 创建新仓库
   * @param name 仓库名称
   * @param description 仓库描述
   * @param isPrivate 是否私有
   */
  async createRepository(
    name: string,
    description: string = '',
    isPrivate: boolean = false
  ): Promise<Repository> {
    const repo: Repository = {
      id: this.generateId(),
      name,
      description,
      isPrivate,
      defaultBranch: 'main',
      createdAt: new Date(),
      updatedAt: new Date(),
    }

    this.repositories.set(repo.id, repo)
    return repo
  }

  /**
   * 获取仓库信息
   * @param id 仓库ID
   */
  async getRepository(id: string): Promise<Repository | null> {
    return this.repositories.get(id) || null
  }

  /**
   * 列出所有仓库
   */
  async listRepositories(): Promise<Repository[]> {
    return Array.from(this.repositories.values())
  }

  /**
   * 生成唯一ID
   */
  private generateId(): string {
    return Math.random().toString(36).substring(2, 15)
  }
}

// 导出单例实例
export const forge = new Forge()`)

// 代码行数
const codeLines = computed(() => codeContent.value.split('\n'))

// 切换文件夹展开/折叠
const toggleFolder = (node: FileNode) => {
  if (node.type === 'directory') {
    node.isOpen = !node.isOpen
  }
}

// 选择文件
const selectFile = (path: string) => {
  selectedFile.value = path
}

// 复制代码
const copyCode = async () => {
  try {
    await navigator.clipboard.writeText(codeContent.value)
    // 可以添加提示
  } catch (err) {
    console.error('Failed to copy:', err)
  }
}

// 面包屑路径
const breadcrumbPath = computed(() => {
  return selectedFile.value.split('/')
})
</script>

<template>
  <div class="code-viewer">
    <!-- 顶部导航栏 -->
    <header class="repo-nav">
      <div class="nav-left">
        <router-link to="/explore" class="back-link">
          <el-icon><ArrowLeft /></el-icon>
          <span>返回仓库列表</span>
        </router-link>
        <div class="repo-title">
          <span class="owner">perseus</span>
          <span class="separator">/</span>
          <span class="name">perseus-core</span>
        </div>
      </div>
      <div class="nav-right">
        <el-button :icon="Link" text>
          main
        </el-button>
        <el-button type="primary" :icon="CopyDocument" @click="copyCode">
          复制
        </el-button>
      </div>
    </header>

    <!-- 主体内容 -->
    <div class="viewer-body">
      <!-- 文件树侧边栏 -->
      <aside class="file-tree">
        <div class="tree-header">
          <el-input
            v-model="searchQuery"
            placeholder="搜索文件..."
            :prefix-icon="Search"
            size="small"
          />
        </div>
        <div class="tree-content">
          <ul class="tree-list">
            <li
              v-for="node in fileTree"
              :key="node.path"
              class="tree-item"
            >
              <div
                class="tree-node"
                :class="{
                  'is-directory': node.type === 'directory',
                  'is-file': node.type === 'file',
                  'is-selected': selectedFile === node.path,
                }"
                @click="node.type === 'directory' ? toggleFolder(node) : selectFile(node.path)"
              >
                <el-icon v-if="node.type === 'directory'" class="folder-icon">
                  <CaretBottom v-if="node.isOpen" />
                  <CaretRight v-else />
                </el-icon>
                <el-icon v-else class="file-icon">
                  <Document />
                </el-icon>
                <span class="node-name">{{ node.name }}</span>
              </div>
              <!-- 子节点 -->
              <ul v-if="node.type === 'directory' && node.isOpen && node.children" class="tree-children">
                <li
                  v-for="child in node.children"
                  :key="child.path"
                  class="tree-item"
                >
                  <div
                    class="tree-node"
                    :class="{
                      'is-directory': child.type === 'directory',
                      'is-file': child.type === 'file',
                      'is-selected': selectedFile === child.path,
                    }"
                    @click="child.type === 'directory' ? toggleFolder(child) : selectFile(child.path)"
                  >
                    <el-icon v-if="child.type === 'directory'" class="folder-icon">
                      <CaretBottom v-if="child.isOpen" />
                      <CaretRight v-else />
                    </el-icon>
                    <el-icon v-else class="file-icon">
                      <Document />
                    </el-icon>
                    <span class="node-name">{{ child.name }}</span>
                  </div>
                  <!-- 孙子节点 -->
                  <ul v-if="child.type === 'directory' && child.isOpen && child.children" class="tree-children">
                    <li
                      v-for="grandChild in child.children"
                      :key="grandChild.path"
                      class="tree-item"
                    >
                      <div
                        class="tree-node is-file"
                        :class="{ 'is-selected': selectedFile === grandChild.path }"
                        @click="selectFile(grandChild.path)"
                      >
                        <el-icon class="file-icon">
                          <Document />
                        </el-icon>
                        <span class="node-name">{{ grandChild.name }}</span>
                      </div>
                    </li>
                  </ul>
                </li>
              </ul>
            </li>
          </ul>
        </div>
      </aside>

      <!-- 代码查看区 -->
      <main class="code-area">
        <!-- 面包屑 -->
        <div class="breadcrumb-bar">
          <el-icon><Collection /></el-icon>
          <span
            v-for="(part, index) in breadcrumbPath"
            :key="index"
            class="breadcrumb-item"
          >
            <span v-if="index > 0" class="breadcrumb-separator">/</span>
            {{ part }}
          </span>
        </div>

        <!-- 代码内容 -->
        <div class="code-container">
          <table class="code-table">
            <tbody>
              <tr
                v-for="(line, index) in codeLines"
                :key="index"
                class="code-line"
              >
                <td class="line-number">{{ index + 1 }}</td>
                <td class="line-content">
                  <pre><code>{{ line || ' ' }}</code></pre>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- 文件信息栏 -->
        <div class="file-info">
          <div class="info-left">
            <span class="info-item">
              <el-icon><User /></el-icon>
              最后修改者: John Doe
            </span>
            <span class="info-item">
              <el-icon><Clock /></el-icon>
              2天前
            </span>
          </div>
          <div class="info-right">
            <el-button text :icon="FullScreen">全屏</el-button>
            <el-button text :icon="Download">下载</el-button>
          </div>
        </div>
      </main>
    </div>
  </div>
</template>

<style scoped>
.code-viewer {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--perseus-bg);
}

/* 顶部导航 */
.repo-nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 56px;
  padding: 0 var(--perseus-space-5);
  border-bottom: 1px solid var(--perseus-border-soft);
  background: var(--perseus-bg);
  flex-shrink: 0;
}

.nav-left {
  display: flex;
  align-items: center;
  gap: var(--perseus-space-4);
}

.back-link {
  display: flex;
  align-items: center;
  gap: var(--perseus-space-2);
  font-size: var(--perseus-text-sm);
  color: var(--perseus-muted);
  transition: color var(--perseus-motion-fast);
}

.back-link:hover {
  color: var(--perseus-fg);
}

.repo-title {
  font-size: var(--perseus-text-base);
  font-weight: 600;
}

.owner {
  color: var(--perseus-muted);
}

.separator {
  color: var(--perseus-muted);
  margin: 0 var(--perseus-space-1);
}

.name {
  color: var(--perseus-fg);
}

.nav-right {
  display: flex;
  align-items: center;
  gap: var(--perseus-space-3);
}

/* 主体内容 */
.viewer-body {
  flex: 1;
  display: flex;
  overflow: hidden;
}

/* 文件树 */
.file-tree {
  width: var(--perseus-filetree-width);
  border-right: 1px solid var(--perseus-border-soft);
  display: flex;
  flex-direction: column;
  background: var(--perseus-surface);
  flex-shrink: 0;
}

.tree-header {
  padding: var(--perseus-space-3);
  border-bottom: 1px solid var(--perseus-border-soft);
}

.tree-content {
  flex: 1;
  overflow-y: auto;
  padding: var(--perseus-space-2) 0;
}

.tree-list,
.tree-children {
  list-style: none;
  padding: 0;
  margin: 0;
}

.tree-children {
  padding-left: var(--perseus-space-4);
}

.tree-node {
  display: flex;
  align-items: center;
  gap: var(--perseus-space-2);
  padding: var(--perseus-space-2) var(--perseus-space-3);
  cursor: pointer;
  font-size: var(--perseus-text-sm);
  color: var(--perseus-fg-2);
  transition: all var(--perseus-motion-fast);
}

.tree-node:hover {
  background: var(--perseus-surface-warm);
  color: var(--perseus-fg);
}

.tree-node.is-selected {
  background: var(--perseus-accent);
  color: var(--perseus-accent-on);
}

.folder-icon,
.file-icon {
  color: var(--perseus-muted);
  flex-shrink: 0;
}

.tree-node.is-selected .folder-icon,
.tree-node.is-selected .file-icon {
  color: var(--perseus-accent-on);
}

.node-name {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 代码区 */
.code-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.breadcrumb-bar {
  display: flex;
  align-items: center;
  gap: var(--perseus-space-1);
  padding: var(--perseus-space-3) var(--perseus-space-5);
  border-bottom: 1px solid var(--perseus-border-soft);
  font-size: var(--perseus-text-sm);
  color: var(--perseus-fg-2);
}

.breadcrumb-separator {
  color: var(--perseus-muted);
  margin: 0 var(--perseus-space-1);
}

.code-container {
  flex: 1;
  overflow: auto;
  background: var(--perseus-bg);
}

.code-table {
  width: 100%;
  border-collapse: collapse;
  font-family: var(--perseus-font-mono);
  font-size: 14px;
  line-height: 1.6;
}

.code-line {
  transition: background var(--perseus-motion-fast);
}

.code-line:hover {
  background: var(--perseus-surface);
}

.line-number {
  width: 60px;
  padding: 0 var(--perseus-space-4);
  text-align: right;
  color: var(--perseus-muted);
  background: var(--perseus-surface);
  border-right: 1px solid var(--perseus-border-soft);
  user-select: none;
  vertical-align: top;
}

.line-content {
  padding: 0 var(--perseus-space-4);
  white-space: pre;
  vertical-align: top;
}

.line-content pre {
  margin: 0;
  padding: 0;
  background: transparent;
  border: none;
  font-family: inherit;
}

.line-content code {
  font-family: inherit;
  background: transparent;
  padding: 0;
}

/* 文件信息栏 */
.file-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--perseus-space-3) var(--perseus-space-5);
  border-top: 1px solid var(--perseus-border-soft);
  background: var(--perseus-surface);
  font-size: var(--perseus-text-xs);
  color: var(--perseus-muted);
}

.info-left {
  display: flex;
  align-items: center;
  gap: var(--perseus-space-4);
}

.info-item {
  display: flex;
  align-items: center;
  gap: var(--perseus-space-1);
}

.info-right {
  display: flex;
  align-items: center;
  gap: var(--perseus-space-2);
}

/* 响应式 */
@media (max-width: 768px) {
  .file-tree {
    display: none;
  }

  .repo-nav {
    flex-wrap: wrap;
    height: auto;
    padding: var(--perseus-space-3);
    gap: var(--perseus-space-3);
  }

  .nav-left {
    flex-wrap: wrap;
  }
}
</style>
