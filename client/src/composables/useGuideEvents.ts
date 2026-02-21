/**
 * Guide引导流程事件总线
 *
 * 使用 Vue provide/inject 实现组件间通信
 * 各步骤组件通过事件总线与Guide主组件交互
 */

import { inject, provide, ref, type InjectionKey, type Ref } from 'vue'
import type { ClientConfig } from '../services/api'

/**
 * 步骤状态类型
 */
export type StepStatus = 'idle' | 'checking' | 'found' | 'not_found' | 'loaded' | 'skipped' | 'installed'

/**
 * 引导流程状态
 */
export interface GuideState {
  /** 当前步骤 (1-4) */
  currentStep: number
  /** 是否正在保存 */
  isSaving: boolean
  /** 全局错误信息 */
  error: string
  /** 客户端配置 */
  clientConfig: ClientConfig | null
}

/**
 * 步骤1状态：安全密码设置
 */
export interface SecurityPasswordState {
  /** 安全密码 */
  securityPassword: string
  /** 确认密码 */
  confirmPassword: string
  /** 密码是否有效 */
  isPasswordValid: boolean
  /** 是否已保存 */
  isSaved: boolean
}

/**
 * 步骤2状态：服务端检查
 */
export interface ServerCheckState {
  /** 服务端路径 */
  path: string
  /** 检查状态 */
  status: 'idle' | 'checking' | 'found' | 'not_found'
}

/**
 * 步骤3状态：Nginx配置
 */
export interface NginxConfigState {
  /** Nginx状态 */
  status: 'not_loaded' | 'loaded' | 'skipped'
}

/**
 * 步骤4状态：Git检查
 */
export interface GitCheckState {
  /** Git检查状态 */
  status: 'idle' | 'checking' | 'installed' | 'not_installed'
  /** Git版本 */
  version: string
}

/**
 * 数据库类型选项
 */
export type DatabaseType = 'sqlite' | 'postgresql' | 'mysql'

/**
 * 步骤5状态：用户偏好
 */
export interface UserPreferenceState {
  /** 选中的主题 */
  selectedTheme: string
  /** 选中的布局密度 */
  selectedLayout: string
  /** 数据库类型 */
  dbType: DatabaseType
}

/**
 * 完整的引导状态
 */
export interface GuideFullState {
  guide: GuideState
  securityPassword: SecurityPasswordState
  serverCheck: ServerCheckState
  nginxConfig: NginxConfigState
  gitCheck: GitCheckState
  userPreference: UserPreferenceState
}

/**
 * 事件类型定义
 */
export interface GuideEvents {
  /** 步骤完成事件 */
  'step:complete': { step: number; data?: unknown }
  /** 步骤跳过事件 */
  'step:skip': { step: number }
  /** 导航到下一步 */
  'nav:next': void
  /** 导航到上一步 */
  'nav:prev': void
  /** 完成引导 */
  'guide:complete': void
  /** 设置错误信息 */
  'error:set': string
  /** 清除错误信息 */
  'error:clear': void
}

/**
 * 事件处理器类型
 */
export type GuideEventHandler<T extends keyof GuideEvents> = (payload: GuideEvents[T]) => void

/**
 * 事件总线接口
 */
export interface GuideEventBus {
  /** 状态 - 响应式 */
  state: Ref<GuideFullState>
  /** 更新步骤1状态（安全密码） */
  updateSecurityPassword: (state: Partial<SecurityPasswordState>) => void
  /** 更新步骤2状态（服务端检查） */
  updateServerCheck: (state: Partial<ServerCheckState>) => void
  /** 更新步骤3状态（Nginx配置） */
  updateNginxConfig: (state: Partial<NginxConfigState>) => void
  /** 更新步骤4状态（Git检查） */
  updateGitCheck: (state: Partial<GitCheckState>) => void
  /** 更新步骤5状态（用户偏好） */
  updateUserPreference: (state: Partial<UserPreferenceState>) => void
  /** 设置当前步骤 */
  setCurrentStep: (step: number) => void
  /** 设置错误信息 */
  setError: (error: string) => void
  /** 清除错误信息 */
  clearError: () => void
  /** 设置保存状态 */
  setSaving: (isSaving: boolean) => void
  /** 触发事件 */
  emit: <T extends keyof GuideEvents>(event: T, payload: GuideEvents[T]) => void
  /** 注册事件监听 */
  on: <T extends keyof GuideEvents>(event: T, handler: GuideEventHandler<T>) => void
  /** 移除事件监听 */
  off: <T extends keyof GuideEvents>(event: T, handler: GuideEventHandler<T>) => void
}

/**
 * Injection Key
 */
export const GuideEventBusKey: InjectionKey<GuideEventBus> = Symbol('GuideEventBus')

/**
 * 创建事件总线
 * @param initialConfig - 初始客户端配置
 * @returns 事件总线实例
 */
export function createGuideEventBus(initialConfig: ClientConfig | null): GuideEventBus {
  // 创建响应式状态
  const state = ref<GuideFullState>({
    guide: {
      currentStep: 1,
      isSaving: false,
      error: '',
      clientConfig: initialConfig
    },
    securityPassword: {
      securityPassword: '',
      confirmPassword: '',
      isPasswordValid: false,
      isSaved: false
    },
    serverCheck: {
      path: '',
      status: 'idle'
    },
    nginxConfig: {
      status: 'not_loaded'
    },
    gitCheck: {
      status: 'idle',
      version: ''
    },
    userPreference: {
      selectedTheme: initialConfig?.appearance?.theme || 'dark',
      selectedLayout: initialConfig?.appearance?.layout_density || 'default',
      dbType: (initialConfig?.db_type as DatabaseType) || 'sqlite'
    }
  })

  // 事件监听器存储
  const listeners: { [K in keyof GuideEvents]?: GuideEventHandler<K>[] } = {}

  /**
   * 触发事件
   */
  function emit<T extends keyof GuideEvents>(event: T, payload: GuideEvents[T]): void {
    const handlers = listeners[event]
    if (handlers) {
      handlers.forEach(handler => handler(payload))
    }
  }

  /**
   * 注册事件监听
   */
  function on<T extends keyof GuideEvents>(event: T, handler: GuideEventHandler<T>): void {
    if (!listeners[event]) {
      listeners[event] = []
    }
    listeners[event]!.push(handler)
  }

  /**
   * 移除事件监听
   */
  function off<T extends keyof GuideEvents>(event: T, handler: GuideEventHandler<T>): void {
    const handlers = listeners[event]
    if (handlers) {
      const index = handlers.indexOf(handler)
      if (index > -1) {
        handlers.splice(index, 1)
      }
    }
  }

  return {
    state,
    updateSecurityPassword: (newState) => {
      Object.assign(state.value.securityPassword, newState)
    },
    updateServerCheck: (newState) => {
      Object.assign(state.value.serverCheck, newState)
    },
    updateNginxConfig: (newState) => {
      Object.assign(state.value.nginxConfig, newState)
    },
    updateGitCheck: (newState) => {
      Object.assign(state.value.gitCheck, newState)
    },
    updateUserPreference: (newState) => {
      Object.assign(state.value.userPreference, newState)
    },
    setCurrentStep: (step) => {
      state.value.guide.currentStep = step
    },
    setError: (error) => {
      state.value.guide.error = error
    },
    clearError: () => {
      state.value.guide.error = ''
    },
    setSaving: (isSaving) => {
      state.value.guide.isSaving = isSaving
    },
    emit,
    on,
    off
  }
}

/**
 * 在Guide组件中提供事件总线
 * @param initialConfig - 初始客户端配置
 */
export function provideGuideEventBus(initialConfig: ClientConfig | null): GuideEventBus {
  const eventBus = createGuideEventBus(initialConfig)
  provide(GuideEventBusKey, eventBus)
  return eventBus
}

/**
 * 在步骤组件中使用事件总线
 * @returns 事件总线实例
 * @throws 如果不在Guide组件内调用会抛出错误
 */
export function useGuideEventBus(): GuideEventBus {
  const eventBus = inject(GuideEventBusKey)
  if (!eventBus) {
    throw new Error('useGuideEventBus must be used within a Guide component')
  }
  return eventBus
}

/**
 * 在步骤组件中监听Guide事件
 * @returns 事件监听辅助函数
 */
export function useGuideEvents() {
  const eventBus = useGuideEventBus()

  /**
   * 监听步骤完成事件
   * @param handler - 事件处理器
   */
  function onStepComplete(handler: GuideEventHandler<'step:complete'>) {
    eventBus.on('step:complete', handler)
    return () => eventBus.off('step:complete', handler)
  }

  /**
   * 监听步骤跳过事件
   * @param handler - 事件处理器
   */
  function onStepSkip(handler: GuideEventHandler<'step:skip'>) {
    eventBus.on('step:skip', handler)
    return () => eventBus.off('step:skip', handler)
  }

  /**
   * 监听导航事件
   * @param handler - 事件处理器
   */
  function onNavNext(handler: () => void) {
    const wrapper: GuideEventHandler<'nav:next'> = () => handler()
    eventBus.on('nav:next', wrapper)
    return () => eventBus.off('nav:next', wrapper)
  }

  /**
   * 监听导航事件
   * @param handler - 事件处理器
   */
  function onNavPrev(handler: () => void) {
    const wrapper: GuideEventHandler<'nav:prev'> = () => handler()
    eventBus.on('nav:prev', wrapper)
    return () => eventBus.off('nav:prev', wrapper)
  }

  return {
    eventBus,
    onStepComplete,
    onStepSkip,
    onNavNext,
    onNavPrev
  }
}
