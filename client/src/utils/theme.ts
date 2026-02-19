/**
 * 主题管理工具
 * 
 * 注意：此文件已迁移到 Pinia Store
 * 请使用 `useThemeStore` 替代直接导入这些函数
 * 
 * 保留此文件以向后兼容，实际功能已委托给 Store
 */

import { useThemeStore } from '../stores/theme'
import type { ThemeConfig } from '../stores/theme'

export type { ThemeConfig }
export { presetThemes, adjustableCssVars } from '../stores/theme'

/**
 * 当前主题ID (从 Store 获取)
 * @deprecated 请使用 useThemeStore().currentThemeId
 */
export const currentThemeId = {
  get value() {
    const store = useThemeStore()
    return store.currentThemeId
  },
  set value(val: string) {
    const store = useThemeStore()
    store.switchTheme(val)
  }
}

/**
 * 自定义CSS变量 (从 Store 获取)
 * @deprecated 请使用 useThemeStore().customCssVars
 */
export const customCssVars = {
  get value() {
    const store = useThemeStore()
    return store.customCssVars
  },
  set value(val: Record<string, string>) {
    const store = useThemeStore()
    store.setCssVars(val)
  }
}

/**
 * 初始化主题系统
 * @deprecated 请使用 useThemeStore().initTheme()
 */
export function initTheme(): void {
  const store = useThemeStore()
  store.initTheme()
}

/**
 * 切换主题
 * @deprecated 请使用 useThemeStore().switchTheme()
 */
export function switchTheme(themeId: string): void {
  const store = useThemeStore()
  store.switchTheme(themeId)
}

/**
 * 设置自定义CSS变量
 * @deprecated 请使用 useThemeStore().setCssVar()
 */
export function setCssVar(name: string, value: string): void {
  const store = useThemeStore()
  store.setCssVar(name, value)
}

/**
 * 批量设置自定义CSS变量
 * @deprecated 请使用 useThemeStore().setCssVars()
 */
export function setCssVars(vars: Record<string, string>): void {
  const store = useThemeStore()
  store.setCssVars(vars)
}

/**
 * 获取CSS变量值
 * @deprecated 请使用 useThemeStore().getCssVarValue()
 */
export function getCssVar(name: string): string {
  const store = useThemeStore()
  return store.getCssVarValue(name)
}

/**
 * 应用自定义CSS变量到文档
 * @deprecated 此方法已移除，CSS变量会自动应用
 */
export function applyCustomCssVars(): void {
  // CSS变量现在由Store自动应用
  console.warn('applyCustomCssVars is deprecated. CSS vars are applied automatically by the store.')
}

/**
 * 重置自定义CSS变量
 * @deprecated 请使用 useThemeStore().resetCustomCssVars()
 */
export function resetCustomCssVars(): void {
  const store = useThemeStore()
  store.resetCustomCssVars()
}

/**
 * 从本地存储加载主题配置
 * @deprecated 配置现在从 ClientConfig 加载
 */
export function loadThemeFromStorage(): void {
  // 配置现在从 ClientConfig 加载，此函数不再需要
  console.warn('loadThemeFromStorage is deprecated. Config is now loaded from ClientConfig.')
}

/**
 * 保存主题配置到本地存储
 * @deprecated 配置现在保存到 ClientConfig
 */
export function saveThemeToStorage(): void {
  // 配置现在保存到 ClientConfig，此函数不再需要
  console.warn('saveThemeToStorage is deprecated. Config is now saved to ClientConfig.')
}

/**
 * 获取可调整的CSS变量列表
 * @deprecated 请从 stores/theme 导入 adjustableCssVars
 */
export function getAdjustableCssVars(): Array<{ name: string; label: string; type: 'color' | 'size' | 'number' }> {
  return useThemeStore().$state.isInitialized
    ? [
        { name: '--border-radius-sm', label: '小圆角', type: 'size' },
        { name: '--border-radius-md', label: '中圆角', type: 'size' },
        { name: '--border-radius-lg', label: '大圆角', type: 'size' },
        { name: '--border-radius-xl', label: '超大圆角', type: 'size' },
        { name: '--spacing-xs', label: '超小间距', type: 'size' },
        { name: '--spacing-sm', label: '小间距', type: 'size' },
        { name: '--spacing-md', label: '中间距', type: 'size' },
        { name: '--spacing-lg', label: '大间距', type: 'size' },
        { name: '--spacing-xl', label: '超大间距', type: 'size' },
        { name: '--font-size-xs', label: '超小字体', type: 'size' },
        { name: '--font-size-sm', label: '小字体', type: 'size' },
        { name: '--font-size-md', label: '中字体', type: 'size' },
        { name: '--font-size-lg', label: '大字体', type: 'size' },
        { name: '--font-size-xl', label: '超大字体', type: 'size' },
        { name: '--sidebar-width', label: '侧边栏宽度', type: 'size' }
      ]
    : []
}

/**
 * 导出主题配置为JSON
 * @deprecated 请使用 useThemeStore().exportThemeConfig()
 */
export function exportThemeConfig(): string {
  const store = useThemeStore()
  return store.exportThemeConfig()
}

/**
 * 导入主题配置
 * @deprecated 请使用 useThemeStore().importThemeConfig()
 */
export function importThemeConfig(json: string): boolean {
  const store = useThemeStore()
  return store.importThemeConfig(json)
}
