import { createRouter, createWebHistory } from 'vue-router'
import Layout from '../components/Layout.vue'
import Home from '../views/Home.vue'
import Log from '../views/Log.vue'
import Setting from '../views/Setting.vue'
import Nginx from '../views/Nginx.vue'
import Guide from '../views/Guide.vue'
import { isGuideCompleted } from '../services/api'

/**
 * 路由配置
 */
const routes = [
  {
    path: '/guide',
    name: 'Guide',
    component: Guide,
    meta: {
      title: '首次启动配置',
      standalone: true
    }
  },
  {
    path: '/',
    component: Layout,
    redirect: '/home',
    children: [
      {
        path: 'home',
        name: 'Home',
        component: Home,
        meta: {
          title: '控制台'
        }
      },
      {
        path: 'log',
        name: 'Log',
        component: Log,
        meta: {
          title: '日志'
        }
      },
      {
        path: 'setting',
        name: 'Setting',
        component: Setting,
        meta: {
          title: '设置'
        }
      },
      {
        path: 'nginx',
        name: 'Nginx',
        component: Nginx,
        meta: {
          title: 'Nginx管理'
        }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

/**
 * 路由守卫：确保引导完成前无法访问主页面
 * 防止用户通过直接输入URL跳过引导流程
 */
router.beforeEach(async (to, from, next) => {
  // 如果是访问引导页面，直接允许
  if (to.path === '/guide') {
    next()
    return
  }

  try {
    // 检查引导是否已完成
    const guideCompleted = await isGuideCompleted()

    if (!guideCompleted) {
      // 引导未完成，强制跳转到引导页面
      next('/guide')
    } else {
      // 引导已完成，允许访问
      next()
    }
  } catch (e) {
    console.error('路由守卫检查失败:', e)
    // 出错时默认进入引导流程，确保安全
    next('/guide')
  }
})

export default router
