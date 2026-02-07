import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useConfigManager } from '@/core/configManager'
import sidebarConfig from '../config/Sidebar.json'
import type { ThemeType } from '@/core/themeManager'

const STORAGE_KEY = 'quick-setting-state-v1'

interface QuickSettingConfig {
  id: string
  name: string
  icon: string
  method: string
  default: boolean
  description?: string
}

interface NavigationConfig {
  name: string
  icon: string
  route: string
  component: string
  settingId?: string
}

interface QuickSettingState {
  bottomPanel: boolean
  auxSidebar: boolean
  sidebarCollapsed: boolean
  currentTheme: ThemeType
  [key: string]: boolean | string | number
}

interface QuickSettingWithActive extends QuickSettingConfig {
  active: boolean
  displayText?: string
}

type QuickSettingHandler = (state: QuickSettingState, args: unknown[] | undefined, settingId: string) => void | Promise<void>
type QuickSettingStateGetter = (state: QuickSettingState, settingId: string) => boolean | Promise<boolean>
type QuickSettingDisplayTextGetter = (state: QuickSettingState, name: string, settingId: string) => string | Promise<string>

interface QuickSettingMethod {
  handler: QuickSettingHandler
  getState: QuickSettingStateGetter
  getDisplayText?: QuickSettingDisplayTextGetter
}

const methodRegistry: Record<string, QuickSettingMethod> = {}

const registerQuickSettingMethod = (
  method: string,
  handler: QuickSettingHandler,
  getState: QuickSettingStateGetter,
  getDisplayText?: QuickSettingDisplayTextGetter
): void => {
  methodRegistry[method] = { handler, getState, getDisplayText }
}

const getAllMethodNames = (): Set<string> => {
  const methods = new Set<string>()
  sidebarConfig.mainSidebar.quickSettings.forEach((setting: QuickSettingConfig) => {
    methods.add(setting.method)
  })
  return methods
}

const validateMethodRegistration = (): void => {
  const registeredMethods = Object.keys(methodRegistry)
  const configuredMethods = getAllMethodNames()

  configuredMethods.forEach(method => {
    if (!registeredMethods.includes(method)) {
      console.error(`[QuickSetting] 错误: 方法 "${method}" 未注册。请在 quickSettingMethods.ts 中调用 registerQuickSettingMethod() 注册该方法。`)
    }
  })

  registeredMethods.forEach(method => {
    if (!configuredMethods.has(method)) {
      console.warn(`[QuickSetting] 警告: 方法 "${method}" 已注册但在配置中未使用。`)
    }
  })
}

const inferInitialState = (): QuickSettingState => {
  const state: QuickSettingState = {
    bottomPanel: true,
    auxSidebar: true,
    sidebarCollapsed: false,
    currentTheme: 'modern',
  }
  sidebarConfig.mainSidebar.quickSettings.forEach((setting: QuickSettingConfig) => {
    state[setting.id] = setting.default
  })
  return state
}

export const useQuickSettingStore = defineStore('quickSetting', () => {
  const configManager = useConfigManager()

  const state = ref<QuickSettingState>(inferInitialState())

  const applyConfigDefaults = (): void => {
    if (configManager.uiConfig.value) {
      const config = configManager.uiConfig.value
      if (config.containers?.bottomPanel?.visible !== undefined) {
        state.value.bottomPanel = config.containers.bottomPanel.visible
      }
      if (config.containers?.auxSidebar?.visible !== undefined) {
        state.value.auxSidebar = config.containers.auxSidebar.visible
      }
      if (config.sidebar?.mainSidebar?.collapsed !== undefined) {
        state.value.sidebarCollapsed = config.sidebar.mainSidebar.collapsed
      }
    }
  }

  const initializeState = (): void => {
    const savedState = localStorage.getItem(STORAGE_KEY)
    if (savedState) {
      try {
        const parsed = JSON.parse(savedState)
        const initialState = inferInitialState()
        state.value = { ...initialState, ...parsed }
      } catch {
        applyConfigDefaults()
      }
    } else {
      applyConfigDefaults()
    }
    validateMethodRegistration()
  }

  initializeState()

  const quickSettings = computed((): QuickSettingWithActive[] => {
    return sidebarConfig.mainSidebar.quickSettings.map((setting: QuickSettingConfig): QuickSettingWithActive => {
      const methodDef = methodRegistry[setting.method]
      const stateValue = methodDef?.getState(state.value, setting.id)
      const active = stateValue instanceof Promise ? false : stateValue
      const displayTextValue = methodDef?.getDisplayText?.(state.value, setting.name, setting.id)
      const displayText = displayTextValue instanceof Promise ? setting.name : displayTextValue
      return { ...setting, active, displayText }
    })
  })

  const isBottomPanelVisible = computed(() => !!state.value.bottomPanel)
  const isAuxSidebarVisible = computed(() => !!state.value.auxSidebar)
  const isSidebarCollapsed = computed(() => !!state.value.sidebarCollapsed)
  const currentTheme = computed((): ThemeType => state.value.currentTheme ?? 'modern')

  const handleQuickSetting = async (method: string, args: unknown[] | undefined, settingId: string): Promise<void> => {
    const methodDef = methodRegistry[method]
    if (methodDef) {
      const result = methodDef.handler(state.value, args, settingId)
      if (result instanceof Promise) {
        await result
      }
    } else {
      console.warn(`[QuickSetting] 未知的快速设置方法: ${method}`)
    }
  }

  const resetState = (): void => {
    state.value = inferInitialState()
    applyConfigDefaults()
  }

  return {
    state,
    quickSettings,
    isBottomPanelVisible,
    isAuxSidebarVisible,
    isSidebarCollapsed,
    currentTheme,
    handleQuickSetting,
    resetState
  }
}, {
  persist: {
    key: STORAGE_KEY,
    storage: localStorage
  }
})

export function useQuickSetting() {
  const store = useQuickSettingStore()

  const handleQuickSetting = async (method: string, args?: unknown[], settingId?: string): Promise<void> => {
    await store.handleQuickSetting(method, args, settingId ?? method)
  }

  return {
    quickSettings: computed(() => store.quickSettings),
    isBottomPanelVisible: computed(() => store.isBottomPanelVisible),
    isAuxSidebarVisible: computed(() => store.isAuxSidebarVisible),
    isSidebarCollapsed: computed(() => store.isSidebarCollapsed),
    currentTheme: computed((): ThemeType => store.currentTheme),
    handleQuickSetting
  }
}

export function handleQuickSetting(method: string, args: unknown[], settingId: string) {
  useQuickSettingStore().handleQuickSetting(method, args, settingId)
}

export {
  registerQuickSettingMethod,
  type QuickSettingHandler,
  type QuickSettingStateGetter,
  type QuickSettingDisplayTextGetter,
  type QuickSettingConfig,
  type NavigationConfig
}
