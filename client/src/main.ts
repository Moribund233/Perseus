import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { useThemeStore, useServiceStore } from './stores'

// 导入全局样式
import './styles/variables.css'
import './styles/page-common.css'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)

// 初始化主题系统（必须在 pinia 创建之后）
const themeStore = useThemeStore()
themeStore.initTheme()

// 初始化服务状态检查（会自动连接日志 WebSocket）
const serviceStore = useServiceStore()
serviceStore.startAutoRefresh(30000) // 30秒检查一次服务状态

app.mount('#app')
