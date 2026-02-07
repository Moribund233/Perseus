// 配置文件管理器 - 支持热重载
import { ref } from 'vue'

// 配置类型定义
interface SidebarConfig {
  mainSidebar: {
    navigation: Array<{
      name: string
      icon: string
      route: string
      component: string
    }>
    quickSettings: Array<{
      id: string
      name: string
      icon: string
      method: string
      default: boolean
    }>
  }
  auxSidebar: {
    sections: Array<{
      name: string
      items: Array<{
        name: string
        icon: string
        action: string
      }>
    }>
  }
}

interface UIConfig {
  containers: {
    bottomPanel: {
      visible: boolean
    }
    auxSidebar: {
      visible: boolean
    }
  }
  sidebar: {
    mainSidebar: {
      collapsed: boolean
    }
  }
}

// 配置状态
const sidebarConfig = ref<SidebarConfig | null>(null)
const uiConfig = ref<UIConfig | null>(null)
const configVersion = ref(0)

// 配置内容哈希，用于检测实际变化
let sidebarHash = ''
let uiHash = ''

// 计算对象哈希（简单的JSON字符串化）
const calculateHash = (obj: any): string => {
  return JSON.stringify(obj)
}

// 加载配置文件
const loadConfigFile = async <T>(filePath: string): Promise<T> => {
  try {
    // 使用动态导入来获取 JSON 文件
    const module = await import(/* @vite-ignore */ filePath)
    return module.default as T
  } catch (error) {
    console.error(`Error loading config file ${filePath}:`, error)
    throw error
  }
}

// 初始化配置
const initializeConfigs = async () => {
  try {
    const [sidebar, ui] = await Promise.all([
      loadConfigFile<SidebarConfig>('../config/Sidebar.json'),
      loadConfigFile<UIConfig>('../config/UI.json')
    ])
    
    // 计算初始配置的哈希值
    sidebarHash = calculateHash(sidebar)
    uiHash = calculateHash(ui)
    
    sidebarConfig.value = sidebar
    uiConfig.value = ui
    configVersion.value++
    
    console.log('Configs loaded successfully')
  } catch (error) {
    console.error('Failed to initialize configs:', error)
  }
}

// 重新加载配置
const reloadConfigs = async () => {
  try {
    const [sidebar, ui] = await Promise.all([
      loadConfigFile<SidebarConfig>('../config/Sidebar.json'),
      loadConfigFile<UIConfig>('../config/UI.json')
    ])
    
    // 计算新配置的哈希值
    const newSidebarHash = calculateHash(sidebar)
    const newUIHash = calculateHash(ui)
    
    // 检查内容是否真的有变化（使用哈希比较）
    const sidebarChanged = newSidebarHash !== sidebarHash
    const uiChanged = newUIHash !== uiHash
    
    if (sidebarChanged || uiChanged) {
      // 更新配置和哈希值
      sidebarConfig.value = sidebar
      uiConfig.value = ui
      sidebarHash = newSidebarHash
      uiHash = newUIHash
      configVersion.value++
      console.log('Configs reloaded successfully')
      return true
    } else {
      console.log('Configs unchanged, skipping reload')
      return false
    }
  } catch (error) {
    console.error('Failed to reload configs:', error)
    return false
  }
}

// 开发环境下的热重载监听 - 优化版本
if (import.meta.env.DEV) {
  let lastCheckTime = Date.now()
  let isReloading = false
  
  // 使用更智能的轮询机制，避免不必要的重载
  const checkForChanges = async () => {
    if (isReloading) return // 防止并发重载
    
    try {
      // 检查配置文件的时间戳（通过import缓存机制）
      const currentTime = Date.now()
      if (currentTime - lastCheckTime < 5000) return // 最少5秒检查一次
      
      isReloading = true
      lastCheckTime = currentTime
      
      // 尝试重新导入配置，如果有变更会触发模块热重载
      const [newSidebar, newUI] = await Promise.all([
        loadConfigFile<SidebarConfig>('../config/Sidebar.json'),
        loadConfigFile<UIConfig>('../config/UI.json')
      ])
      
      // 计算新配置的哈希值
      const newSidebarHash = calculateHash(newSidebar)
      const newUIHash = calculateHash(newUI)
      
      // 检查内容是否真的有变化（使用哈希比较）
      const sidebarChanged = newSidebarHash !== sidebarHash
      const uiChanged = newUIHash !== uiHash
      
      if (sidebarChanged || uiChanged) {
        // 更新配置和哈希值
        sidebarConfig.value = newSidebar
        uiConfig.value = newUI
        sidebarHash = newSidebarHash
        uiHash = newUIHash
        configVersion.value++
        console.log('配置已更新，检测到内容变化')
      }
      
      isReloading = false
    } catch (error) {
      isReloading = false
      // 忽略检查错误，可能是文件暂时不可用
    }
  }
  
  // 启动智能检查
  const CHECK_INTERVAL = 3000 // 3秒检查间隔
  setInterval(checkForChanges, CHECK_INTERVAL)
}

// 导出API
export const useConfigManager = () => {
  return {
    // 配置数据
    sidebarConfig: sidebarConfig,
    uiConfig: uiConfig,
    configVersion,
    
    // 方法
    initializeConfigs,
    reloadConfigs,
    
    // 计算属性
    isConfigLoaded: () => sidebarConfig.value !== null && uiConfig.value !== null
  }
}

export type { SidebarConfig, UIConfig }