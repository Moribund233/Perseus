import { ref } from 'vue'

/**
 * 异步操作状态
 */
export interface AsyncState {
  /**
   * 是否正在加载中
   */
  isLoading: boolean
  /**
   * 错误信息
   */
  error: string
}

/**
 * 异步操作处理组合式函数
 *
 * 提供统一的异步操作状态管理和错误处理
 * 自动处理加载状态、错误捕获和清理
 *
 * @param options - 可选配置
 * @returns 状态和执行函数
 *
 * @example
 * ```typescript
 * const { isLoading, error, execute } = useAsyncHandler()
 *
 * const handleSubmit = () => {
 *   execute(async () => {
 *     await submitForm(data.value)
 *     showSuccess('提交成功')
 *   })
 * }
 * ```
 */
export function useAsyncHandler(
  options: {
    /**
     * 错误处理回调
     */
    onError?: (error: Error) => void
    /**
     * 成功处理回调
     */
    onSuccess?: () => void
  } = {}
) {
  const { onError, onSuccess } = options

  /**
   * 加载状态
   */
  const isLoading = ref(false)

  /**
   * 错误信息
   */
  const error = ref('')

  /**
   * 执行异步操作
   * @param asyncFn - 异步函数
   * @param errorMessage - 自定义错误消息前缀
   */
  const execute = async <T>(
    asyncFn: () => Promise<T>,
    errorMessage: string = '操作失败'
  ): Promise<T | undefined> => {
    isLoading.value = true
    error.value = ''

    try {
      const result = await asyncFn()
      onSuccess?.()
      return result
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : String(err)
      error.value = `${errorMessage}: ${errorMsg}`
      console.error(error.value, err)
      onError?.(err instanceof Error ? err : new Error(String(err)))
      return undefined
    } finally {
      isLoading.value = false
    }
  }

  /**
   * 清除错误信息
   */
  const clearError = (): void => {
    error.value = ''
  }

  /**
   * 重置状态
   */
  const reset = (): void => {
    isLoading.value = false
    error.value = ''
  }

  return {
    isLoading,
    error,
    execute,
    clearError,
    reset
  }
}

/**
 * 带结果的异步操作处理组合式函数
 *
 * 与 useAsyncHandler 类似，但会返回操作结果
 *
 * @example
 * ```typescript
 * const { isLoading, error, result, run } = useAsyncResult()
 *
 * const fetchData = () => {
 *   run(async () => {
 *     return await api.getData()
 *   })
 * }
 *
 * // 在模板中使用 result
 * <div v-if="result">{{ result.name }}</div>
 * ```
 */
export function useAsyncResult<T>() {
  const isLoading = ref(false)
  const error = ref('')
  const result = ref<T | null>(null)

  const run = async (
    asyncFn: () => Promise<T>,
    errorMessage: string = '操作失败'
  ): Promise<boolean> => {
    isLoading.value = true
    error.value = ''

    try {
      result.value = await asyncFn()
      return true
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : String(err)
      error.value = `${errorMessage}: ${errorMsg}`
      console.error(error.value, err)
      return false
    } finally {
      isLoading.value = false
    }
  }

  const clear = (): void => {
    isLoading.value = false
    error.value = ''
    result.value = null
  }

  return {
    isLoading,
    error,
    result,
    run,
    clear
  }
}
