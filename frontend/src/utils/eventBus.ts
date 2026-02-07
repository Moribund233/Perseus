import mitt from 'mitt'

export interface ToolMessage {
  type: string
  data: any
  source: string
  target?: string
  timestamp: number
}

export const eventBus = mitt<Record<string, any>>()

export function sendToolMessage(
  source: string,
  target: string,
  type: string,
  data: any
): void {
  const message: ToolMessage = {
    type,
    data,
    source,
    target,
    timestamp: Date.now()
  }

  if (process.env.NODE_ENV !== 'production') {
    console.log(`[EventBus] 发送消息: ${type} from ${source} to ${target}`, data)
  }

  eventBus.emit('tool:message', message)
  eventBus.emit(type, { ...data, source })
}

export function sendMessageToTargets(
  source: string,
  targets: string[],
  type: string,
  data: any
): void {
  targets.forEach(target => {
    sendToolMessage(source, target, type, data)
  })
}

export function onToolMessage(
  target: string,
  type: string,
  callback: (data: any, message: ToolMessage) => void
): () => void {
  const handler = (eventData: any) => {
    callback(eventData, {
      type,
      data: eventData,
      source: eventData.source,
      target,
      timestamp: Date.now()
    })
  }

  eventBus.on(type, handler)

  return () => {
    eventBus.off(type, handler)
  }
}

export function onAnyMessage(
  callback: (message: ToolMessage) => void
): () => void {
  eventBus.on('tool:message', (data: any) => {
    callback(data)
  })
  return () => {
    eventBus.off('tool:message')
  }
}

export function registerTool(toolId: string): void {
  if (process.env.NODE_ENV !== 'production') {
    console.log(`[EventBus] 工具已注册: ${toolId}`)
  }
  eventBus.emit('tool:registered', { toolId })
}

export function unregisterTool(toolId: string): void {
  if (process.env.NODE_ENV !== 'production') {
    console.log(`[EventBus] 工具已注销: ${toolId}`)
  }
  eventBus.emit('tool:unregistered', { toolId })
}
