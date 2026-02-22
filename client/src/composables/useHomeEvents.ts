/**
 * Home页面事件总线
 *
 * 使用 Vue provide/inject 实现组件间通信
 * 各功能组件通过事件总线与 Home 主组件交互
 */

import { inject, provide, ref, type InjectionKey, type Ref } from 'vue'

/**
 * 服务状态类型
 */
export type ServiceStatusType = 'running' | 'stopped' | 'starting' | 'stopping' | null

/**
 * 服务状态接口
 */
export interface ServiceStatus {
  isRunning: boolean
  status: ServiceStatusType
  uptime_formatted?: string
  version?: string
}

/**
 * 进程信息接口
 */
export interface ProcessInfo {
  pid?: number
  cpu_percent?: number
  memory_mb?: number
  memory_percent?: number
  threads?: number
}

/**
 * 本地系统信息接口
 */
export interface LocalSystemInfo {
  cpu_percent: number
  memory_percent: number
  memory_used_gb: number
  memory_total_gb: number
  network?: {
    bytes_sent: number
    bytes_received: number
  }
}

/**
 * 请求统计接口
 */
export interface RequestStats {
  total: number
  success: number
  failed: number
}

/**
 * Git状态接口
 */
export interface GitStatus {
  operations_count: number
  push_queue_count: number
  active_syncs: number
}

/**
 * 健康状态接口
 */
export interface HealthStatus {
  database: string
  git: string
  storage: string
}

/**
 * Home页面完整状态
 */
export interface HomeFullState {
  service: {
    isLoading: boolean
    error: string | null
    successMessage: string | null
    warningMessage: string | null
  }
  performance: {
    cpuHistory: number[]
    memoryHistory: number[]
    networkSentHistory: number[]
    networkReceivedHistory: number[]
  }
}

/**
 * 事件类型定义
 */
export interface HomeEvents {
  /** 服务启动 */
  'service:start': void
  /** 服务停止 */
  'service:stop': void
  /** 服务重启 */
  'service:restart': void
  /** 刷新状态 */
  'service:refresh': void
  /** 服务状态变化 */
  'service:statusChange': { status: ServiceStatusType; isRunning: boolean }
  /** 显示错误 */
  'error:show': string
  /** 清除错误 */
  'error:clear': void
  /** 显示成功消息 */
  'success:show': string
  /** 清除成功消息 */
  'success:clear': void
  /** 显示警告消息 */
  'warning:show': string
  /** 清除警告消息 */
  'warning:clear': void
  /** 需要数据库迁移 */
  'migration:required': { sourceType: 'sqlite' | 'postgresql' | 'mysql'; targetType: 'sqlite' | 'postgresql' | 'mysql'; sourceUrl: string; targetUrl: string }
  /** 数据库迁移完成 */
  'migration:complete': { success: boolean }
  /** 显示迁移进度弹窗 */
  'migration:show': { sourceType: 'sqlite' | 'postgresql' | 'mysql'; targetType: 'sqlite' | 'postgresql' | 'mysql'; sourceUrl: string; targetUrl: string }
  /** 关闭迁移进度弹窗 */
  'migration:close': void
}

/**
 * 事件处理器类型
 */
export type HomeEventHandler<T extends keyof HomeEvents> = (payload: HomeEvents[T]) => void

/**
 * 事件总线接口
 */
export interface HomeEventBus {
  /** 状态 - 响应式 */
  state: Ref<HomeFullState>
  /** 设置加载状态 */
  setLoading: (loading: boolean) => void
  /** 设置错误信息 */
  setError: (error: string | null) => void
  /** 清除错误信息 */
  clearError: () => void
  /** 设置成功消息 */
  setSuccess: (message: string | null) => void
  /** 清除成功消息 */
  clearSuccess: () => void
  /** 设置警告消息 */
  setWarning: (message: string | null) => void
  /** 清除警告消息 */
  clearWarning: () => void
  /** 更新性能历史数据 */
  updatePerformanceHistory: (cpu: number, memory: number, networkSent: number, networkReceived: number) => void
  /** 触发事件 */
  emit: <T extends keyof HomeEvents>(event: T, payload?: HomeEvents[T]) => void
  /** 注册事件监听 */
  on: <T extends keyof HomeEvents>(event: T, handler: HomeEventHandler<T>) => void
  /** 移除事件监听 */
  off: <T extends keyof HomeEvents>(event: T, handler: HomeEventHandler<T>) => void
}

/**
 * Injection Key
 */
export const HomeEventBusKey: InjectionKey<HomeEventBus> = Symbol('HomeEventBus')

/**
 * 创建事件总线
 * @returns 事件总线实例
 */
export function createHomeEventBus(): HomeEventBus {
  // 创建响应式状态
  const state = ref<HomeFullState>({
    service: {
      isLoading: false,
      error: null,
      successMessage: null,
      warningMessage: null
    },
    performance: {
      cpuHistory: new Array(20).fill(0),
      memoryHistory: new Array(20).fill(0),
      networkSentHistory: new Array(20).fill(0),
      networkReceivedHistory: new Array(20).fill(0)
    }
  })

  // 事件监听器存储
  const listeners: { [K in keyof HomeEvents]?: HomeEventHandler<K>[] } = {}

  /**
   * 触发事件
   */
  function emit<T extends keyof HomeEvents>(event: T, payload?: HomeEvents[T]): void {
    const handlers = listeners[event]
    if (handlers) {
      handlers.forEach(handler => handler(payload as HomeEvents[T]))
    }
  }

  /**
   * 注册事件监听
   */
  function on<T extends keyof HomeEvents>(event: T, handler: HomeEventHandler<T>): void {
    if (!listeners[event]) {
      listeners[event] = []
    }
    listeners[event]!.push(handler)
  }

  /**
   * 移除事件监听
   */
  function off<T extends keyof HomeEvents>(event: T, handler: HomeEventHandler<T>): void {
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
    setLoading: (loading: boolean) => {
      state.value.service.isLoading = loading
    },
    setError: (error: string | null) => {
      state.value.service.error = error
    },
    clearError: () => {
      state.value.service.error = null
    },
    setSuccess: (message: string | null) => {
      state.value.service.successMessage = message
    },
    clearSuccess: () => {
      state.value.service.successMessage = null
    },
    setWarning: (message: string | null) => {
      state.value.service.warningMessage = message
    },
    clearWarning: () => {
      state.value.service.warningMessage = null
    },
    updatePerformanceHistory: (cpu: number, memory: number, networkSent: number, networkReceived: number) => {
      // 更新 CPU 历史
      state.value.performance.cpuHistory.shift()
      state.value.performance.cpuHistory.push(cpu)

      // 更新内存历史
      state.value.performance.memoryHistory.shift()
      state.value.performance.memoryHistory.push(memory)

      // 更新网络历史
      state.value.performance.networkSentHistory.shift()
      state.value.performance.networkSentHistory.push(networkSent)
      state.value.performance.networkReceivedHistory.shift()
      state.value.performance.networkReceivedHistory.push(networkReceived)
    },
    emit,
    on,
    off
  }
}

/**
 * 在 Home 组件中提供事件总线
 */
export function provideHomeEventBus(): HomeEventBus {
  const eventBus = createHomeEventBus()
  provide(HomeEventBusKey, eventBus)
  return eventBus
}

/**
 * 在子组件中使用事件总线
 * @returns 事件总线实例
 * @throws 如果不在 Home 组件内调用会抛出错误
 */
export function useHomeEventBus(): HomeEventBus {
  const eventBus = inject(HomeEventBusKey)
  if (!eventBus) {
    throw new Error('useHomeEventBus must be used within a Home component')
  }
  return eventBus
}
