import { ref } from 'vue'

/**
 * 配置保存组合式函数
 *
 * 提供统一的配置保存状态管理和错误处理逻辑
 * 适用于所有需要保存配置的场景
 *
 * @param saveApi - 保存配置的API函数
 * @param emit - 组件的emit函数，用于发送成功/错误事件
 * @returns 保存状态和保存函数
 *
 * @example
 * ```typescript
 * const { isSaving, save } = useConfigSaver(
 *   saveClientConfig,
 *   emit
 * )
 *
 * const handleSave = () => {
 *   save(clientConfig.value, '配置保存成功')
 * }
 * ```
 */
export function useConfigSaver<T>(
  saveApi: (config: T) => Promise<void>,
  emit: {
    (e: 'error', message: string): void
    (e: 'success', message: string): void
  }
) {
  /**
   * 保存状态
   */
  const isSaving = ref(false)

  /**
   * 保存配置
   * @param config - 要保存的配置对象
   * @param successMessage - 保存成功时显示的消息
   */
  const save = async (config: T, successMessage: string): Promise<void> => {
    isSaving.value = true
    emit('error', '')
    emit('success', '')

    try {
      await saveApi(config)
      emit('success', successMessage)
    } catch (err) {
      console.error('保存配置失败:', err)
      emit('error', `保存失败: ${String(err)}`)
    } finally {
      isSaving.value = false
    }
  }

  return {
    isSaving,
    save
  }
}
