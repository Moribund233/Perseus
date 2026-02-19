import { createRouter, createWebHistory } from 'vue-router'
import Layout from '../components/Layout.vue'
import Home from '../views/Home.vue'
import Log from '../views/Log.vue'
import Setting from '../views/Setting.vue'
import Nginx from '../views/Nginx.vue'
import Guide from '../views/Guide.vue'

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

export default router
