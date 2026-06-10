/**
 * 路由配置
 */
import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'landing',
    component: () => import('@/views/LandingView.vue'),
    meta: {
      title: 'Perseus - 现代代码托管平台',
    },
  },
  {
    path: '/dashboard',
    name: 'dashboard',
    component: () => import('@/views/DashboardView.vue'),
    meta: {
      title: '仪表盘 - Perseus',
      requiresAuth: true,
    },
  },
  {
    path: '/explore',
    name: 'explore',
    component: () => import('@/views/ExploreView.vue'),
    meta: {
      title: '探索 - Perseus',
    },
  },
  {
    path: '/code-viewer',
    name: 'code-viewer',
    component: () => import('@/views/CodeViewerView.vue'),
    meta: {
      title: '代码查看 - Perseus',
    },
  },
  {
    path: '/repositories',
    name: 'repositories',
    component: () => import('@/views/RepositoriesView.vue'),
    meta: {
      title: '仓库 - Perseus',
      requiresAuth: true,
    },
  },
  {
    path: '/settings',
    name: 'settings',
    component: () => import('@/views/SettingsView.vue'),
    meta: {
      title: '设置 - Perseus',
      requiresAuth: true,
    },
  },
  {
    path: '/profile',
    name: 'profile',
    component: () => import('@/views/ProfileView.vue'),
    meta: {
      title: '个人资料 - Perseus',
    },
  },
  {
    path: '/blog',
    name: 'blog',
    component: () => import('@/views/BlogView.vue'),
    meta: {
      title: '博客 - Perseus',
    },
  },
  {
    path: '/about',
    name: 'about',
    component: () => import('@/views/AboutView.vue'),
    meta: {
      title: '关于 - Perseus',
    },
  },
  {
    path: '/auth',
    name: 'auth',
    component: () => import('@/views/AuthView.vue'),
    meta: {
      title: '登录 / 注册 - Perseus',
      guestOnly: true,
    },
  },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
  scrollBehavior() {
    return { top: 0 }
  },
})

// 路由守卫 - 设置页面标题
router.beforeEach((to) => {
  const title = to.meta.title as string
  if (title) {
    document.title = title
  }
})

export default router
