import { registerQuickSettingMethod } from '@/stores/quickSetting'
import { ThemeType, toggleTheme } from '@/core/themeManager'

const AVAILABLE_THEMES: ThemeType[] = ['modern', 'light', 'dark']

registerQuickSettingMethod(
  'toggleBottomPanel',
  (state, _args, _settingId) => {
    state.bottomPanel = !state.bottomPanel
  },
  (state, _settingId) => !!state.bottomPanel
)

registerQuickSettingMethod(
  'toggleAuxSidebar',
  (state, _args, _settingId) => {
    state.auxSidebar = !state.auxSidebar
  },
  (state, _settingId) => !!state.auxSidebar
)

registerQuickSettingMethod(
  'toggleSidebarCollapse',
  (state, _args, _settingId) => {
    state.sidebarCollapsed = !state.sidebarCollapsed
  },
  (state, _settingId) => !state.sidebarCollapsed
)

registerQuickSettingMethod(
  'toggleTheme',
  (state, _args, _settingId) => {
    const currentThemeValue = state.currentTheme as ThemeType | undefined
    const currentIndex = currentThemeValue ? AVAILABLE_THEMES.indexOf(currentThemeValue) : 0
    const nextTheme = AVAILABLE_THEMES[(currentIndex + 1) % AVAILABLE_THEMES.length]
    console.log('[toggleTheme] 切换前 titleBarVisible:', state.titleBarVisible)
    state.currentTheme = nextTheme
    console.log('[toggleTheme] 切换后 titleBarVisible:', state.titleBarVisible)
    toggleTheme(nextTheme)
  },
  (_state, _settingId) => false,
  (state, name, _settingId) => `${name} (${state.currentTheme ?? 'modern'})`
)
