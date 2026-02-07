import { createRouter, createWebHistory } from 'vue-router'
import Home from '@/views/Home.vue'
import Setting from '@/views/Setting.vue'
import Debug from '@/views/Debug.vue'
import Example1 from '@/views/debug/Example1.vue'
import Example2 from '@/views/debug/Example2.vue'

const routes = [
  {
    path: '/',
    redirect: '/home'
  },
  {
    path: '/home',
    name: 'Home',
    component: Home
  },
  {
    path: '/setting',
    name: 'Setting',
    component: Setting
  },
  {
    path: '/debug',
    name: 'Debug',
    component: Debug,
    children: [
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

]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router