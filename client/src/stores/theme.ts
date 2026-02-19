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
 * 颜色主题配置接口
 */
export interface ColorThemeConfig {
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
 * 布局密度配置接口
 */
export interface LayoutDensityConfig {
  /** 配置ID */
  id: string
  /** 配置名称 */
  name: string
  /** 布局文件路径 */
  file: string
}

/**
 * 预设颜色主题列表
 */
export const presetColorThemes: ColorThemeConfig[] = [
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
    previewColor: '#60a5fa'
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
 * 布局密度预设列表
 */
export const layoutDensityPresets: LayoutDensityConfig[] = [
  {
    id: 'compact',
    name: '紧凑布局',
    file: '/src/assets/themes/compact.css'
  },
  {
    id: 'default',
    name: '默认布局',
    file: '/src/assets/themes/default.css'
  },
  {
    id: 'comfortable',
    name: '舒适布局',
    file: '/src/assets/themes/comfortable.css'
  },
  {
    id: 'spacious',
    name: '宽松布局',
    file: '/src/assets/themes/spacious.css'
  }
]

/**
 * 主题 Store
 */
export const useThemeStore = defineStore('theme', () => {
  // ==================== State ====================

  /** 当前颜色主题ID */
  const currentColorThemeId = ref<string>('dark')

  /** 当前布局密度ID */
  const currentLayoutDensityId = ref<string>('default')

  /** 是否已初始化 */
  const isInitialized = ref(false)

  /** 是否正在保存 */
  const isSaving = ref(false)

  // ==================== Getters ====================

  /** 当前颜色主题配置 */
  const currentColorTheme = computed(() => {
    return presetColorThemes.find(t => t.id === currentColorThemeId.value) || presetColorThemes[0]
  })

  /** 当前布局密度配置 */
  const currentLayoutDensity = computed(() => {
    return layoutDensityPresets.find(d => d.id === currentLayoutDensityId.value) || layoutDensityPresets[1]
  })

  // ==================== Actions ====================

  /**
   * 初始化主题系统
   * 从 ClientConfig 加载主题配置
   */
  const initTheme = async (): Promise<void> => {
    if (isInitialized.value) return

    try {
      const config = await getClientConfig()

      // 加载颜色主题ID
      if (config.appearance?.theme) {
        const themeId = config.appearance.theme
        if (presetColorThemes.find(t => t.id === themeId)) {
          currentColorThemeId.value = themeId
        }
      }

      // 加载布局密度ID
      if (config.appearance?.layout_density) {
        const densityId = config.appearance.layout_density
        if (layoutDensityPresets.find(d => d.id === densityId)) {
          currentLayoutDensityId.value = densityId
        }
      }

      // 应用主题
      applyThemes()

      isInitialized.value = true

      // 监听变化并自动保存
      watch([currentColorThemeId, currentLayoutDensityId], () => {
        applyThemes()
        saveThemeConfig()
      })

    } catch (error) {
      console.error('初始化主题失败:', error)
      // 使用默认主题
      applyThemes()
    }
  }

  /**
   * 应用主题CSS文件
   */
  const applyThemes = (): void => {
    const colorTheme = presetColorThemes.find(t => t.id === currentColorThemeId.value)
    const layoutDensity = layoutDensityPresets.find(d => d.id === currentLayoutDensityId.value)

    if (!colorTheme || !layoutDensity) {
      console.warn('Theme not found')
      return
    }

    // 查找或创建颜色主题链接元素
    let colorThemeLink = document.getElementById('color-theme-style') as HTMLLinkElement | null
    if (!colorThemeLink) {
      colorThemeLink = document.createElement('link')
      colorThemeLink.id = 'color-theme-style'
      colorThemeLink.rel = 'stylesheet'
      document.head.appendChild(colorThemeLink)
    }
    colorThemeLink.href = colorTheme.file

    // 查找或创建布局密度链接元素
    let layoutDensityLink = document.getElementById('layout-density-style') as HTMLLinkElement | null
    if (!layoutDensityLink) {
      layoutDensityLink = document.createElement('link')
      layoutDensityLink.id = 'layout-density-style'
      layoutDensityLink.rel = 'stylesheet'
      document.head.appendChild(layoutDensityLink)
    }
    layoutDensityLink.href = layoutDensity.file
  }

  /**
   * 切换颜色主题
   */
  const switchColorTheme = (themeId: string): void => {
    if (!presetColorThemes.find(t => t.id === themeId)) {
      console.warn(`Color theme not found: ${themeId}`)
      return
    }
    currentColorThemeId.value = themeId
  }

  /**
   * 切换布局密度
   */
  const switchLayoutDensity = (densityId: string): void => {
    if (!layoutDensityPresets.find(d => d.id === densityId)) {
      console.warn(`Layout density not found: ${densityId}`)
      return
    }
    currentLayoutDensityId.value = densityId
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
        theme: currentColorThemeId.value,
        layout_density: currentLayoutDensityId.value
      }

      // 保存配置
      await saveClientConfig(config)
    } catch (error) {
      console.error('保存主题配置失败:', error)
    } finally {
      isSaving.value = false
    }
  }

  return {
    // State
    currentColorThemeId,
    currentLayoutDensityId,
    isInitialized,
    isSaving,

    // Getters
    currentColorTheme,
    currentLayoutDensity,

    // Actions
    initTheme,
    switchColorTheme,
    switchLayoutDensity
  }
})
