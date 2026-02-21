/**
 * Pinia Store 入口
 *
 * 集中导出所有 store
 */
export { useServiceStore, type BasicSystemInfo } from './service'
export {
  useThemeStore,
  presetColorThemes,
  layoutDensityPresets,
  type ColorThemeConfig,
  type LayoutDensityConfig
} from './theme'
export {
  useDatabaseStore,
  type DatabaseTypeOption
} from './database'
