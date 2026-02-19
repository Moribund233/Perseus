/**
 * WebSocket 日志服务
 *
 * 提供实时日志推送功能，替代传统的 HTTP 轮询
 */

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
 * 日志订阅选项
 */
export interface SubscribeOptions {
  /** 过滤器 */
  filters?: LogFilters
  /** 订阅时获取的历史日志条数 */
  historyCount?: number
}

/**
 * WebSocket 日志客户端状态
 */
export enum LogClientState {
  DISCONNECTED = 'disconnected',
  CONNECTING = 'connecting',
  CONNECTED = 'connected',
  SUBSCRIBED = 'subscribed',
  ERROR = 'error'
}

/**
 * WebSocket 日志客户端
 */
export class WebSocketLogClient {
  private ws: WebSocket | null = null
  private state: LogClientState = LogClientState.DISCONNECTED
  private reconnectTimer: number | null = null
  private pingTimer: number | null = null
  private messageHandlers: Set<(entry: LogEntry) => void> = new Set()
  private stateHandlers: Set<(state: LogClientState) => void> = new Set()
  private historyHandlers: Set<(logs: LogEntry[]) => void> = new Set()
  private errorHandlers: Set<(error: string) => void> = new Set()

  private url: string = ''
  private token: string | null = null
  private reconnectAttempts: number = 0
  private maxReconnectAttempts: number = 5
  private reconnectInterval: number = 3000

  /**
   * 获取当前状态
   */
  getState(): LogClientState {
    return this.state
  }

  /**
   * 是否已连接
   */
  isConnected(): boolean {
    return this.state === LogClientState.CONNECTED || this.state === LogClientState.SUBSCRIBED
  }

  /**
   * 是否已订阅
   */
  isSubscribed(): boolean {
    return this.state === LogClientState.SUBSCRIBED
  }

  /**
   * 连接到 WebSocket 服务器
   *
   * @param token 认证令牌（可选，默认使用本地token）
   */
  async connect(token?: string): Promise<void> {
    if (this.ws?.readyState === WebSocket.OPEN) {
      return
    }

    this.setState(LogClientState.CONNECTING)

    try {
      // 如果没有提供token，尝试获取本地token
      if (!token) {
        try {
          token = await getLocalToken()
        } catch (e) {
          console.warn('获取本地token失败，将使用匿名模式连接:', e)
        }
      }

      this.token = token || null
      const serverUrl = await getServerUrl()
      const wsUrl = serverUrl.replace(/^http/, 'ws')
      this.url = `${wsUrl}/ws/logs${this.token ? `?token=${this.token}` : ''}`

      return new Promise<void>((resolve, reject) => {
        this.ws = new WebSocket(this.url)

        this.ws.onopen = () => {
          this.reconnectAttempts = 0
          this.setState(LogClientState.CONNECTED)
          this.startPing()
          resolve()
        }

        this.ws.onmessage = (event) => {
          this.handleMessage(event.data)
        }

        this.ws.onclose = () => {
          this.cleanup()
          this.setState(LogClientState.DISCONNECTED)
          this.attemptReconnect()
        }

        this.ws.onerror = (_error) => {
          this.setState(LogClientState.ERROR)
          this.notifyError('WebSocket 连接错误')
          reject(new Error('WebSocket 连接错误'))
        }
      })
    } catch (error) {
      this.setState(LogClientState.ERROR)
      throw error
    }
  }

  /**
   * 断开连接
   */
  disconnect(): void {
    this.cleanup()
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
    this.setState(LogClientState.DISCONNECTED)
  }

  /**
   * 订阅日志
   *
   * @param options 订阅选项
   */
  subscribe(options: SubscribeOptions = {}): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      throw new Error('WebSocket 未连接')
    }

    const message = {
      type: 'subscribe_logs',
      filters: {
        levels: options.filters?.levels || ['INFO', 'WARNING', 'ERROR'],
        loggers: options.filters?.loggers,
        keywords: options.filters?.keywords
      },
      history_count: options.historyCount || 50
    }

    this.ws.send(JSON.stringify(message))
  }

  /**
   * 取消订阅
   */
  unsubscribe(): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      return
    }

    this.ws.send(JSON.stringify({ type: 'unsubscribe_logs' }))
    this.setState(LogClientState.CONNECTED)
  }

  /**
   * 获取日志统计
   */
  getStats(): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      return
    }

    this.ws.send(JSON.stringify({ type: 'get_log_stats' }))
  }

  /**
   * 注册日志消息处理器
   *
   * @param handler 处理函数
   * @returns 取消注册函数
   */
  onLog(handler: (entry: LogEntry) => void): () => void {
    this.messageHandlers.add(handler)
    return () => this.messageHandlers.delete(handler)
  }

  /**
   * 注册状态变化处理器
   *
   * @param handler 处理函数
   * @returns 取消注册函数
   */
  onStateChange(handler: (state: LogClientState) => void): () => void {
    this.stateHandlers.add(handler)
    return () => this.stateHandlers.delete(handler)
  }

  /**
   * 注册历史日志处理器
   *
   * @param handler 处理函数
   * @returns 取消注册函数
   */
  onHistory(handler: (logs: LogEntry[]) => void): () => void {
    this.historyHandlers.add(handler)
    return () => this.historyHandlers.delete(handler)
  }

  /**
   * 注册错误处理器
   *
   * @param handler 处理函数
   * @returns 取消注册函数
   */
  onError(handler: (error: string) => void): () => void {
    this.errorHandlers.add(handler)
    return () => this.errorHandlers.delete(handler)
  }

  /**
   * 处理收到的消息
   */
  private handleMessage(data: string): void {
    try {
      const message = JSON.parse(data)

      switch (message.type) {
        case 'log':
          this.notifyLog({
            timestamp: message.timestamp,
            level: message.level,
            logger: message.logger,
            message: message.message
          })
          break

        case 'log_history':
          if (message.logs) {
            this.notifyHistory(message.logs)
          }
          break

        case 'logs_subscribed':
          this.setState(LogClientState.SUBSCRIBED)
          break

        case 'logs_unsubscribed':
          this.setState(LogClientState.CONNECTED)
          break

        case 'pong':
          // 心跳响应，无需处理
          break

        case 'error':
          this.notifyError(message.error || '未知错误')
          break
      }
    } catch (error) {
      console.error('解析 WebSocket 消息失败:', error)
    }
  }

  /**
   * 设置状态并通知监听器
   */
  private setState(state: LogClientState): void {
    this.state = state
    this.stateHandlers.forEach(handler => handler(state))
  }

  /**
   * 通知日志处理器
   */
  private notifyLog(entry: LogEntry): void {
    this.messageHandlers.forEach(handler => handler(entry))
  }

  /**
   * 通知历史日志处理器
   */
  private notifyHistory(logs: LogEntry[]): void {
    this.historyHandlers.forEach(handler => handler(logs))
  }

  /**
   * 通知错误处理器
   */
  private notifyError(error: string): void {
    this.errorHandlers.forEach(handler => handler(error))
  }

  /**
   * 启动心跳
   */
  private startPing(): void {
    this.pingTimer = window.setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({
          type: 'ping',
          timestamp: Date.now()
        }))
      }
    }, 30000) // 30 秒心跳
  }

  /**
   * 清理资源
   */
  private cleanup(): void {
    if (this.pingTimer) {
      clearInterval(this.pingTimer)
      this.pingTimer = null
    }
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
  }

  /**
   * 尝试重连
   */
  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      this.notifyError('WebSocket 重连失败，已达到最大重试次数')
      return
    }

    this.reconnectAttempts++
    this.reconnectTimer = window.setTimeout(() => {
      this.connect(this.token || undefined)
    }, this.reconnectInterval)
  }
}

// 全局单例实例
let globalLogClient: WebSocketLogClient | null = null

/**
 * 获取全局 WebSocket 日志客户端
 */
export function getWebSocketLogClient(): WebSocketLogClient {
  if (!globalLogClient) {
    globalLogClient = new WebSocketLogClient()
  }
  return globalLogClient
}

/**
 * 销毁全局 WebSocket 日志客户端
 */
export function destroyWebSocketLogClient(): void {
  if (globalLogClient) {
    globalLogClient.disconnect()
    globalLogClient = null
  }
}
