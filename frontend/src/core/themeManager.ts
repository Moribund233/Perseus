// 主题管理器
import { ref, computed } from 'vue'

// 主题类型定义
type ThemeType = 'modern' | 'light' | 'dark'

// 主题配置
interface ThemeConfig {
  name: string
  colors: {
    primary: string
    secondary: string
    background: string
    surface: string
    text: string
    textSecondary: string
    border: string
    hover: string
    active: string
  }
}

// 主题配置映射
const themeConfigs: Record<ThemeType, ThemeConfig> = {
  modern: {
    name: '现代',
    colors: {
      primary: '#3498db',
      secondary: '#2ecc71',
      background: '#f8fafc',
      surface: '#ffffff',
      text: '#1e293b',
      textSecondary: '#64748b',
      border: '#e2e8f0',
      hover: '#f1f5f9',
      active: '#3b82f6'
    }
  },
  light: {
    name: '明亮',
    colors: {
      primary: '#4f46e5',
      secondary: '#059669',
      background: '#ffffff',
      surface: '#f9fafb',
      text: '#111827',
      textSecondary: '#6b7280',
      border: '#e5e7eb',
      hover: '#f3f4f6',
      active: '#6366f1'
    }
  },
  dark: {
    name: '暗黑',
    colors: {
      primary: '#60a5fa',
      secondary: '#34d399',
      background: '#0f172a',
      surface: '#1e293b',
      text: '#f8fafc',
      textSecondary: '#cbd5e1',
      border: '#334155',
      hover: '#334155',
      active: '#3b82f6'
    }
  }
}

// 当前主题
const currentTheme = ref<ThemeType>('modern')

// 应用主题到DOM
const applyTheme = (theme: ThemeType) => {
  const config = themeConfigs[theme]
  const root = document.documentElement
  
  // 设置基础CSS变量
  Object.entries(config.colors).forEach(([key, value]) => {
    root.style.setProperty(`--color-${key}`, value)
  })
  
  // 设置容器相关CSS变量
  root.style.setProperty('--color-titlebar-bg', config.colors.primary)
  root.style.setProperty('--color-titlebar-border', config.colors.border)
  root.style.setProperty('--color-titlebar-text', config.colors.text)
  root.style.setProperty('--color-titlebar-text-secondary', config.colors.textSecondary)
  root.style.setProperty('--color-titlebar-hover', 'rgba(255, 255, 255, 0.1)')
  root.style.setProperty('--color-titlebar-minimize', '#f39c12')
  root.style.setProperty('--color-titlebar-maximize', '#27ae60')
  root.style.setProperty('--color-titlebar-close', '#e74c3c')
  
  // 设置侧边栏相关CSS变量
  root.style.setProperty('--color-sidebar-bg', config.colors.surface)
  root.style.setProperty('--color-sidebar-border', config.colors.border)
  root.style.setProperty('--color-sidebar-text', config.colors.text)
  root.style.setProperty('--color-sidebar-text-secondary', config.colors.textSecondary)
  
  // 设置主内容区域CSS变量
  root.style.setProperty('--color-main-content-bg', config.colors.background)
  root.style.setProperty('--color-main-content-text', config.colors.text)
  
  // 设置主侧边栏CSS变量
  root.style.setProperty('--color-main-sidebar-bg', config.colors.surface)
  root.style.setProperty('--color-main-sidebar-border', config.colors.border)
  root.style.setProperty('--color-main-sidebar-text', config.colors.text)
  root.style.setProperty('--color-main-sidebar-text-secondary', config.colors.textSecondary)
  root.style.setProperty('--color-main-sidebar-section-border', config.colors.border)
  root.style.setProperty('--color-main-sidebar-hover', config.colors.hover)
  root.style.setProperty('--color-main-sidebar-active', config.colors.primary)
  root.style.setProperty('--color-main-sidebar-active-text', config.colors.text)
  
  // 设置图标颜色
  root.style.setProperty('--color-icon-filter', theme === 'dark' ? 'invert(1)' : 'none')
  
  // 设置辅助侧边栏CSS变量
  root.style.setProperty('--color-aux-sidebar-bg', config.colors.surface)
  root.style.setProperty('--color-aux-sidebar-border', config.colors.border)
  root.style.setProperty('--color-aux-sidebar-text', config.colors.text)
  
  // 设置底部面板CSS变量
  root.style.setProperty('--color-bottom-panel-bg', config.colors.surface)
  root.style.setProperty('--color-bottom-panel-border', config.colors.border)
  root.style.setProperty('--color-bottom-panel-text', config.colors.text)
  
  // 设置卡片组件CSS变量
  root.style.setProperty('--color-card-bg', config.colors.surface)
  root.style.setProperty('--color-card-border', config.colors.border)
  root.style.setProperty('--color-card-divider', config.colors.border)
  root.style.setProperty('--color-card-title', config.colors.text)
  root.style.setProperty('--color-card-description', config.colors.textSecondary)
}

// 切换主题
export const toggleTheme = (theme?: ThemeType) => {
  if (theme) {
    currentTheme.value = theme
  } else {
    // 循环切换主题
    const themes: ThemeType[] = ['modern', 'light', 'dark']
    const currentIndex = themes.indexOf(currentTheme.value)
    const nextIndex = (currentIndex + 1) % themes.length
    currentTheme.value = themes[nextIndex]
  }
  
  applyTheme(currentTheme.value)
}

// 获取当前主题配置
const getCurrentThemeConfig = computed(() => {
  return themeConfigs[currentTheme.value]
})

// 获取所有主题
const getAllThemes = computed(() => {
  return Object.entries(themeConfigs).map(([key, config]) => ({
    key: key as ThemeType,
    name: config.name
  }))
})

// 初始化主题
const initTheme = () => {
  // 尝试从localStorage获取保存的主题
  const savedTheme = localStorage.getItem('app-theme') as ThemeType
  if (savedTheme && themeConfigs[savedTheme]) {
    currentTheme.value = savedTheme
  }
  
  applyTheme(currentTheme.value)
}

// 监听主题变化并保存到localStorage
const saveTheme = () => {
  localStorage.setItem('app-theme', currentTheme.value)
}

// 导出主题管理器
export function useTheme() {
  return {
    currentTheme,
    toggleTheme,
    getCurrentThemeConfig,
    getAllThemes,
    initTheme,
    saveTheme,
    applyTheme
  }
}

export type { ThemeType, ThemeConfig }