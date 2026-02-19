/**
 * 主题管理 Store
 * 使用 Pinia 管理主题状态，并与 ClientConfig 同步
 */

import { ref, computed, watch } from 'vue'
import { defineStore } from 'pinia'
import {
  getClientConfig,
  saveClientConfig
} from '../services/api'

/**
 * 主题配置接口
 */
export interface ThemeConfig {
  /** 主题ID */
  id: string
  /** 主题名称 */
  name: string
  /** 主题文件路径 */
  file: string
  /** 主题预览色 */
  previewColor: string
}

/**
 * 预设主题列表
 */
export const presetThemes: ThemeConfig[] = [
  {
    id: 'dark',
    name: '深色主题',
    file: '/src/assets/themes/dark.css',
    previewColor: '#3b82f6'
  },
  {
    id: 'light',
    name: '浅色主题',
    file: '/src/assets/themes/light.css',
    previewColor: '#2563eb'
  },
  {
    id: 'purple',
    name: '紫色主题',
    file: '/src/assets/themes/purple.css',
    previewColor: '#8b5cf6'
  },
  {
    id: 'green',
    name: '绿色主题',
    file: '/src/assets/themes/green.css',
    previewColor: '#10b981'
  }
]

/**
 * 可调整的CSS变量列表
 */
export const adjustableCssVars = [
  // 圆角
  { name: '--border-radius-sm', label: '小圆角', type: 'size' as const },
  { name: '--border-radius-md', label: '中圆角', type: 'size' as const },
  { name: '--border-radius-lg', label: '大圆角', type: 'size' as const },
  { name: '--border-radius-xl', label: '超大圆角', type: 'size' as const },

  // 间距
  { name: '--spacing-xs', label: '超小间距', type: 'size' as const },
  { name: '--spacing-sm', label: '小间距', type: 'size' as const },
  { name: '--spacing-md', label: '中间距', type: 'size' as const },
  { name: '--spacing-lg', label: '大间距', type: 'size' as const },
  { name: '--spacing-xl', label: '超大间距', type: 'size' as const },

  // 字体大小
  { name: '--font-size-xs', label: '超小字体', type: 'size' as const },
  { name: '--font-size-sm', label: '小字体', type: 'size' as const },
  { name: '--font-size-md', label: '中字体', type: 'size' as const },
  { name: '--font-size-lg', label: '大字体', type: 'size' as const },
  { name: '--font-size-xl', label: '超大字体', type: 'size' as const },

  // 侧边栏宽度
  { name: '--sidebar-width', label: '侧边栏宽度', type: 'size' as const }
]

/**
 * 主题 Store
 */
export const useThemeStore = defineStore('theme', () => {
  // ==================== State ====================

  /** 当前主题ID */
  const currentThemeId = ref<string>('dark')

  /** 自定义CSS变量 */
  const customCssVars = ref<Record<string, string>>({})

  /** 是否已初始化 */
  const isInitialized = ref(false)

  /** 是否正在保存 */
  const isSaving = ref(false)

  // ==================== Getters ====================

  /** 当前主题配置 */
  const currentTheme = computed(() => {
    return presetThemes.find(t => t.id === currentThemeId.value) || presetThemes[0]
  })

  /** 获取CSS变量当前值 */
  const getCssVarValue = (name: string): string => {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  }

  // ==================== Actions ====================

  /**
   * 初始化主题系统
   * 从 ClientConfig 加载主题配置
   */
  const initTheme = async (): Promise<void> => {
    if (isInitialized.value) return

    try {
      const config = await getClientConfig()

      // 加载主题ID
      if (config.appearance?.theme) {
        const themeId = config.appearance.theme
        if (presetThemes.find(t => t.id === themeId)) {
          currentThemeId.value = themeId
        }
      }

      // 加载自定义CSS变量
      if (config.appearance?.custom_css_vars) {
        customCssVars.value = { ...config.appearance.custom_css_vars }
      }

      // 应用主题
      loadThemeFile(currentThemeId.value)
      applyCustomCssVars()

      isInitialized.value = true

      // 监听变化并自动保存
      watch([currentThemeId, customCssVars], () => {
        saveThemeConfig()
      }, { deep: true })

    } catch (error) {
      console.error('初始化主题失败:', error)
      // 使用默认主题
      loadThemeFile('dark')
    }
  }

  /**
   * 加载主题CSS文件
   */
  const loadThemeFile = (themeId: string): void => {
    const theme = presetThemes.find(t => t.id === themeId)
    if (!theme) {
      console.warn(`Theme not found: ${themeId}`)
      return
    }

    // 查找或创建主题链接元素
    let linkElement = document.getElementById('theme-style') as HTMLLinkElement | null

    if (!linkElement) {
      linkElement = document.createElement('link')
      linkElement.id = 'theme-style'
      linkElement.rel = 'stylesheet'
      document.head.appendChild(linkElement)
    }

    linkElement.href = theme.file
  }

  /**
   * 切换主题
   */
  const switchTheme = (themeId: string): void => {
    if (!presetThemes.find(t => t.id === themeId)) {
      console.warn(`Theme not found: ${themeId}`)
      return
    }
    currentThemeId.value = themeId
    loadThemeFile(themeId)
  }

  /**
   * 设置自定义CSS变量
   */
  const setCssVar = (name: string, value: string): void => {
    customCssVars.value[name] = value
    applyCustomCssVars()
  }

  /**
   * 批量设置自定义CSS变量
   */
  const setCssVars = (vars: Record<string, string>): void => {
    Object.assign(customCssVars.value, vars)
    applyCustomCssVars()
  }

  /**
   * 应用自定义CSS变量到文档
   */
  const applyCustomCssVars = (): void => {
    const root = document.documentElement
    Object.entries(customCssVars.value).forEach(([name, value]) => {
      if (value) {
        root.style.setProperty(name, value)
      }
    })
  }

  /**
   * 重置自定义CSS变量
   */
  const resetCustomCssVars = (): void => {
    const root = document.documentElement
    Object.keys(customCssVars.value).forEach((name) => {
      root.style.removeProperty(name)
    })
    customCssVars.value = {}
  }

  /**
   * 保存主题配置到 ClientConfig
   */
  const saveThemeConfig = async (): Promise<void> => {
    if (isSaving.value) return

    isSaving.value = true
    try {
      // 获取当前配置
      const config = await getClientConfig()

      // 更新外观配置
      config.appearance = {
        ...config.appearance,
        theme: currentThemeId.value,
        custom_css_vars: { ...customCssVars.value }
      }

      // 保存配置
      await saveClientConfig(config)
    } catch (error) {
      console.error('保存主题配置失败:', error)
    } finally {
      isSaving.value = false
    }
  }

  /**
   * 导出主题配置
   */
  const exportThemeConfig = (): string => {
    return JSON.stringify({
      themeId: currentThemeId.value,
      customVars: customCssVars.value,
      exportTime: new Date().toISOString()
    }, null, 2)
  }

  /**
   * 导入主题配置
   */
  const importThemeConfig = (json: string): boolean => {
    try {
      const config = JSON.parse(json)
      if (config.themeId && presetThemes.find(t => t.id === config.themeId)) {
        switchTheme(config.themeId)
      }
      if (config.customVars) {
        setCssVars(config.customVars)
      }
      return true
    } catch (error) {
      console.error('导入主题配置失败:', error)
      return false
    }
  }

  return {
    // State
    currentThemeId,
    customCssVars,
    isInitialized,
    isSaving,

    // Getters
    currentTheme,
    getCssVarValue,

    // Actions
    initTheme,
    switchTheme,
    setCssVar,
    setCssVars,
    resetCustomCssVars,
    saveThemeConfig,
    exportThemeConfig,
    importThemeConfig
  }
})
