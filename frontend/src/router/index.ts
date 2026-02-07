import { createRouter, createWebHistory } from 'vue-router'
import Home from '@/views/Home.vue'
import Setting from '@/views/Setting.vue'
import Debug from '@/views/Debug.vue'
import Example1 from '@/views/debug/Example1.vue'
import Example2 from '@/views/debug/Example2.vue'
import Login from '@/views/Login.vue'
import Register from '@/views/Register.vue'
import Repository from '@/views/Repository.vue'
import Management from '@/views/repository/Management.vue'
import Detail from '@/views/repository/Detail.vue'
import { useUserStore } from '@/stores/user'

const routes = [
  {
    path: '/',
    redirect: '/home'
  },
  {
    path: '/home',
    name: 'Home',
    component: Home,
    meta: { requiresAuth: true } // 需要登录才能访问
  },
  {
    path: '/setting',
    name: 'Setting',
    component: Setting,
    meta: { requiresAuth: true } // 需要登录才能访问
  },
  {
    path: '/debug',
    name: 'Debug',
    component: Debug,
    meta: { requiresAuth: true }, // 需要登录才能访问
    children: [
      {
        path: '',
        redirect: '/debug/example1'
      },
      {
        path: 'example1',
        name: 'Example1',
        component: Example1
      },
      {
        path: 'example2',
        name: 'Example2',
        component: Example2
      }
    ]
  },
  {
    path: '/login',
    name: 'Login',
    component: Login,
    meta: { requiresAuth: false } // 不需要登录就能访问
  },
  {
    path: '/register',
    name: 'Register',
    component: Register,
    meta: { requiresAuth: false } // 不需要登录就能访问
  },
  {
    path: '/repository',
    name: 'Repository',
    component: Repository,
    meta: { requiresAuth: true }, // 需要登录才能访问
    children: [
      {
        path: '',
        redirect: '/repository/management'
      },
      {
        path: 'management',
        name: 'RepositoryManagement',
        component: Management
      },
      {
        path: 'detail/:id',
        name: 'RepositoryDetail',
        component: Detail
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach((to, _, next) => {
  const userStore = useUserStore()
  
  // 检查路由是否需要登录
  if (to.meta.requiresAuth !== false && to.meta.requiresAuth !== undefined) {
    // 需要登录，检查用户是否已登录
    if (userStore.isLoggedIn) {
      // 已登录，继续导航
      next()
    } else {
      // 未登录，重定向到登录页面
      next('/login')
    }
  } else {
    // 不需要登录，直接导航
    next()
  }
})

export default router