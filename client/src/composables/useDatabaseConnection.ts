/**
 * 数据库连接管理 Composable
 *
 * 负责客户端数据库连接测试和状态管理
 * - 从加密配置读取当前 db_type 对应的 URL
 * - 测试数据库连接状态
 * - 缓存测试结果，直到 db_type 变化
 */

import { ref, computed } from 'vue'
import { invoke } from '@tauri-apps/api/core'
import { getDatabaseType, getDatabaseUrls } from '../services/api'

/**
 * 连接状态类型
 */
export type ConnectionStatus = 'idle' | 'checking' | 'connected' | 'disconnected' | 'error'

/**
 * 连接测试结果
 */
export interface ConnectionTestResult {
  status: ConnectionStatus
  message: string
  latency?: number
  error?: string
}

/**
 * 数据库连接状态
 */
export interface DatabaseConnectionState {
  /** 当前数据库类型 */
  dbType: string
  /** 数据库 URL */
  dbUrl: string
  /** 连接状态 */
  status: ConnectionStatus
  /** 状态消息 */
  message: string
  /** 连接延迟（毫秒） */
  latency?: number
  /** 最后检查时间 */
  lastCheckedAt?: number
}

// 全局状态（跨组件共享）
const connectionState = ref<DatabaseConnectionState>({
  dbType: 'sqlite',
  dbUrl: '',
  status: 'idle',
  message: '未检查'
})

const isChecking = ref(false)

/**
 * 测试 SQLite 连接
 * @param url - SQLite URL
 */
async function testSQLiteConnection(url: string): Promise<ConnectionTestResult> {
  try {
    // 从 URL 提取文件路径
    const match = url.match(/^sqlite:\/\/(.+)$/)
    if (!match) {
      return { status: 'error', message: 'URL 格式不正确', error: 'Invalid URL format' }
    }
    const filePath = match[1]

    // 使用 Tauri 命令检查文件是否存在
    const exists = await invoke<boolean>('check_sqlite_file', { filePath })

    if (exists) {
      return { status: 'connected', message: '数据库文件可访问', latency: 0 }
    } else {
      return { status: 'disconnected', message: '数据库文件不存在', error: 'File not found' }
    }
  } catch (err) {
    return { status: 'error', message: '检查失败', error: String(err) }
  }
}

/**
 * 测试 PostgreSQL/MySQL 连接
 * @param url - 数据库 URL
 * @param type - 数据库类型
 */
async function testRemoteConnection(url: string, type: string): Promise<ConnectionTestResult> {
  const startTime = Date.now()

  try {
    // 解析 URL 获取主机和端口
    const urlObj = new URL(url)
    const hostname = urlObj.hostname
    const port = parseInt(urlObj.port) || (type === 'postgresql' ? 5432 : 3306)

    // 使用 Tauri 命令测试 TCP 连接
    const result = await invoke<{ success: boolean; error?: string }>('test_tcp_connection', {
      host: hostname,
      port
    })

    const latency = Date.now() - startTime

    if (result.success) {
      return { status: 'connected', message: `连接成功 (${latency}ms)`, latency }
    } else {
      return { status: 'disconnected', message: '无法连接到数据库服务器', error: result.error }
    }
  } catch (err) {
    return { status: 'error', message: '连接测试失败', error: String(err) }
  }
}

/**
 * 使用数据库连接 Composable
 */
export function useDatabaseConnection() {
  /**
   * 当前连接状态
   */
  const state = computed(() => connectionState.value)

  /**
   * 是否正在检查
   */
  const checking = computed(() => isChecking.value)

  /**
   * 状态徽章配置
   */
  const badgeConfig = computed(() => {
    const configs: Record<ConnectionStatus, { text: string; type: 'success' | 'error' | 'warning' | 'info' }> = {
      idle: { text: '未检查', type: 'info' },
      checking: { text: '检查中...', type: 'info' },
      connected: { text: '已连接', type: 'success' },
      disconnected: { text: '未连接', type: 'error' },
      error: { text: '检查失败', type: 'warning' }
    }
    return configs[connectionState.value.status]
  })

  /**
   * 检查数据库连接
   * 如果 db_type 未变化且已有结果，则返回缓存
   */
  async function checkConnection(force: boolean = false): Promise<ConnectionTestResult> {
    // 如果正在检查，等待完成
    if (isChecking.value) {
      return { status: 'checking', message: '正在检查中...' }
    }

    isChecking.value = true

    try {
      // 获取当前数据库类型和 URL
      const [dbType, urls] = await Promise.all([
        getDatabaseType(),
        getDatabaseUrls()
      ])

      const currentUrl = urls?.[dbType] || ''

      // 检查是否需要重新测试
      if (!force &&
          connectionState.value.dbType === dbType &&
          connectionState.value.dbUrl === currentUrl &&
          connectionState.value.status !== 'idle') {
        isChecking.value = false
        return {
          status: connectionState.value.status,
          message: connectionState.value.message,
          latency: connectionState.value.latency
        }
      }

      // 更新状态为检查中
      connectionState.value = {
        dbType,
        dbUrl: currentUrl,
        status: 'checking',
        message: '正在检查连接...'
      }

      // 如果没有 URL，直接返回未配置
      if (!currentUrl || currentUrl.trim().length === 0) {
        const result: ConnectionTestResult = {
          status: 'error',
          message: '数据库 URL 未配置'
        }
        connectionState.value = {
          ...connectionState.value,
          status: result.status,
          message: result.message,
          lastCheckedAt: Date.now()
        }
        return result
      }

      // 根据类型测试连接
      let result: ConnectionTestResult
      if (dbType === 'sqlite') {
        result = await testSQLiteConnection(currentUrl)
      } else {
        result = await testRemoteConnection(currentUrl, dbType)
      }

      // 更新状态
      connectionState.value = {
        ...connectionState.value,
        status: result.status,
        message: result.message,
        latency: result.latency,
        lastCheckedAt: Date.now()
      }

      return result
    } catch (err) {
      const errorResult: ConnectionTestResult = {
        status: 'error',
        message: '检查过程出错',
        error: String(err)
      }
      connectionState.value = {
        ...connectionState.value,
        status: 'error',
        message: errorResult.message,
        lastCheckedAt: Date.now()
      }
      return errorResult
    } finally {
      isChecking.value = false
    }
  }

  /**
   * 重置连接状态
   */
  function resetState(): void {
    connectionState.value = {
      dbType: 'sqlite',
      dbUrl: '',
      status: 'idle',
      message: '未检查'
    }
  }

  /**
   * 强制刷新（当 db_type 变化时调用）
   */
  async function refresh(): Promise<ConnectionTestResult> {
    return checkConnection(true)
  }

  return {
    state,
    checking,
    badgeConfig,
    checkConnection,
    refresh,
    resetState
  }
}
