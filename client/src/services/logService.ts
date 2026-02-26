/**
 * 日志服务（简化版）
 *
 * 通过 Tauri 后端代理 WebSocket 连接
 * 替代前端直接连接，解决 Linux WebKitGTK 不稳定问题
 */

import { invoke } from '@tauri-apps/api/core'
import { listen, type UnlistenFn } from '@tauri-apps/api/event'
import { getServerUrl, getLocalToken } from './api'

/**
 * 日志条目
 */
export interface LogEntry {
  timestamp: string
  level: string
  logger: string
  message: string
}

/**
 * 日志过滤器
 */
export interface LogFilters {
  /** 日志级别过滤，如 ['INFO', 'ERROR'] */
  levels?: string[]
  /** 日志器名称过滤，如 ['app', 'git'] */
  loggers?: string[]
  /** 关键字过滤 */
  keywords?: string[]
}

/**
 * 订阅选项
 */
export interface SubscribeOptions {
  /** 过滤器 */
  filters?: LogFilters
  /** 订阅时获取的历史日志条数 */
  historyCount?: number
}

/**
 * 连接状态
 */
export enum ConnectionState {
  Disconnected = 'Disconnected',
  Connecting = 'Connecting',
  Connected = 'Connected',
  Subscribed = 'Subscribed',
  Error = 'Error'
}

// 事件监听器取消函数
let unlistenState: UnlistenFn | null = null
let unlistenLog: UnlistenFn | null = null
let unlistenHistory: UnlistenFn | null = null
let unlistenError: UnlistenFn | null = null

/**
 * 初始化日志 WebSocket 管理器
 */
export async function initLogWebSocket(): Promise<void> {
  await invoke('init_log_websocket')
}

/**
 * 连接到日志 WebSocket 服务
 *
 * @param token 认证令牌（可选）
 */
export async function connectLogWebSocket(token?: string): Promise<void> {
  const serverUrl = await getServerUrl()
  const wsUrl = serverUrl.replace(/^http/, 'ws')
  const url = `${wsUrl}/ws/logs`

  // 如果没有提供token，尝试获取本地token
  let authToken = token
  if (!authToken) {
    try {
      authToken = await getLocalToken()
    } catch (e) {
      console.warn('获取本地token失败，将使用匿名模式连接:', e)
    }
  }

  await invoke('connect_log_websocket', {
    url,
    token: authToken || null
  })
}

/**
 * 断开日志 WebSocket 连接
 */
export async function disconnectLogWebSocket(): Promise<void> {
  await invoke('disconnect_log_websocket')
}

/**
 * 获取当前连接状态
 */
export async function getLogWebSocketState(): Promise<ConnectionState> {
  return await invoke('get_log_websocket_state')
}

/**
 * 订阅日志
 *
 * @param options 订阅选项
 */
export async function subscribeLogs(options: SubscribeOptions = {}): Promise<void> {
  const opts = {
    filters: options.filters || { levels: ['DEBUG', 'INFO', 'WARNING', 'ERROR'] },
    history_count: options.historyCount || 50
  }
  await invoke('subscribe_logs', { options: opts })
}

/**
 * 取消订阅日志
 */
export async function unsubscribeLogs(): Promise<void> {
  await invoke('unsubscribe_logs')
}

/**
 * 监听连接状态变化
 *
 * @param callback 状态变化回调
 * @returns 取消监听函数
 */
export async function onStateChange(
  callback: (state: ConnectionState) => void
): Promise<() => void> {
  if (unlistenState) {
    unlistenState()
  }

  unlistenState = await listen<ConnectionState>('log:state-change', (event) => {
    callback(event.payload)
  })

  return () => {
    if (unlistenState) {
      unlistenState()
      unlistenState = null
    }
  }
}

/**
 * 监听新日志
 *
 * @param callback 日志回调
 * @returns 取消监听函数
 */
export async function onLog(
  callback: (entry: LogEntry) => void
): Promise<() => void> {
  if (unlistenLog) {
    unlistenLog()
  }

  unlistenLog = await listen<LogEntry>('log:new', (event) => {
    callback(event.payload)
  })

  return () => {
    if (unlistenLog) {
      unlistenLog()
      unlistenLog = null
    }
  }
}

/**
 * 监听历史日志
 *
 * @param callback 历史日志回调
 * @returns 取消监听函数
 */
export async function onHistory(
  callback: (logs: LogEntry[]) => void
): Promise<() => void> {
  if (unlistenHistory) {
    unlistenHistory()
  }

  unlistenHistory = await listen<LogEntry[]>('log:history', (event) => {
    callback(event.payload)
  })

  return () => {
    if (unlistenHistory) {
      unlistenHistory()
      unlistenHistory = null
    }
  }
}

/**
 * 监听错误
 *
 * @param callback 错误回调
 * @returns 取消监听函数
 */
export async function onError(
  callback: (error: string) => void
): Promise<() => void> {
  if (unlistenError) {
    unlistenError()
  }

  unlistenError = await listen<string>('log:error', (event) => {
    callback(event.payload)
  })

  return () => {
    if (unlistenError) {
      unlistenError()
      unlistenError = null
    }
  }
}

/**
 * 清理所有监听器
 */
export function cleanupListeners(): void {
  if (unlistenState) {
    unlistenState()
    unlistenState = null
  }
  if (unlistenLog) {
    unlistenLog()
    unlistenLog = null
  }
  if (unlistenHistory) {
    unlistenHistory()
    unlistenHistory = null
  }
  if (unlistenError) {
    unlistenError()
    unlistenError = null
  }
}
