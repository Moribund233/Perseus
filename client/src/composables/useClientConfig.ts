import { ref, onMounted } from 'vue'
import {
  getClientConfig,
  saveClientConfig,
  type ClientConfig
} from '../services/api'

/**
 * 默认客户端配置
 */
const defaultClientConfig: ClientConfig = {
  server: {
    url: 'http://127.0.0.1:8000',
    auto_connect: true,
    auto_start: false,
    path: {
      exe_name: 'langit-server.exe',
      dir_name: 'langit-server',
      custom_path: undefined
    }
  },
  appearance: {
    theme: 'dark',
    language: 'zh',
    sidebar_collapsed: false
  },
  notification: {
    enabled: true,
    on_error: true,
    on_warning: false,
    on_start_stop: true
  },
  log: {
    level: 'info',
    retention_days: 7
  },
  advanced: {
    ws_reconnect_interval: 3000,
    connection_timeout: 30,
    request_timeout: 30
  }
}

/**
 * 客户端配置管理组合式函数
 *
 * 提供客户端配置的加载、保存和状态管理
 * 自动处理加载状态和错误通知
 *
 * @param emit - 组件的emit函数，用于发送成功/错误事件
 * @param options - 可选配置
 * @returns 配置对象、加载状态和相关操作函数
 *
 * @example
 * ```typescript
 * const {
 *   clientConfig,
 *   isLoading,
 *   isSaving,
 *   loadConfig,
 *   saveConfig
 * } = useClientConfig(emit)
 *
 * // 自动加载配置
 * onMounted(() => {
 *   loadConfig()
 * })
 * ```
 */
export function useClientConfig(
  emit: {
    (e: 'error', message: string): void
    (e: 'success', message: string): void
  },
  options: {
    autoLoad?: boolean
    successMessage?: string
  } = {}
) {
  const { autoLoad = true, successMessage = '客户端配置保存成功' } = options

  /**
   * 客户端配置
   */
  const clientConfig = ref<ClientConfig>({ ...defaultClientConfig })

  /**
   * 加载状态
   */
  const isLoading = ref(false)

  /**
   * 保存状态
   */
  const isSaving = ref(false)

  /**
   * 加载客户端配置
   */
  const loadConfig = async (): Promise<void> => {
    isLoading.value = true
    try {
      const config = await getClientConfig()
      clientConfig.value = { ...defaultClientConfig, ...config }
    } catch (err) {
      console.error('加载客户端配置失败:', err)
      emit('error', `加载客户端配置失败: ${String(err)}`)
    } finally {
      isLoading.value = false
    }
  }

  /**
   * 保存客户端配置
   */
  const saveConfig = async (): Promise<void> => {
    isSaving.value = true
    emit('error', '')
    emit('success', '')

    try {
      await saveClientConfig(clientConfig.value)
      emit('success', successMessage)
    } catch (err) {
      console.error('保存客户端配置失败:', err)
      emit('error', `保存客户端配置失败: ${String(err)}`)
    } finally {
      isSaving.value = false
    }
  }

  /**
   * 更新配置的部分字段
   * @param partial - 部分配置对象
   */
  const updateConfig = (partial: Partial<ClientConfig>): void => {
    clientConfig.value = { ...clientConfig.value, ...partial }
  }

  /**
   * 重置配置为默认值
   */
  const resetConfig = (): void => {
    clientConfig.value = { ...defaultClientConfig }
  }

  // 自动加载配置
  if (autoLoad) {
    onMounted(() => {
      loadConfig()
    })
  }

  return {
    clientConfig,
    isLoading,
    isSaving,
    loadConfig,
    saveConfig,
    updateConfig,
    resetConfig
  }
}
