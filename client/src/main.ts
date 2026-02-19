import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { useThemeStore } from './stores'

// 导入全局样式
import './styles/variables.css'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)

// 初始化主题系统（必须在 pinia 创建之后）
const themeStore = useThemeStore()
themeStore.initTheme()

app.mount('#app')
