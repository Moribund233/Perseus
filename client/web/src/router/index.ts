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
    redirect: '/explore',
  },
  {
    path: '/settings',
    name: 'settings',
    component: () => import('@/views/DashboardView.vue'), // 临时使用 Dashboard
    meta: {
      title: '设置 - Perseus',
    },
  },
  {
    path: '/profile',
    name: 'profile',
    component: () => import('@/views/DashboardView.vue'), // 临时使用 Dashboard
    meta: {
      title: '个人资料 - Perseus',
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
router.beforeEach((to, from, next) => {
  const title = to.meta.title as string
  if (title) {
    document.title = title
  }
  next()
})

export default router
