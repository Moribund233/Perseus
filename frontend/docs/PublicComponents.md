# 公共组件

本文档介绍位于 `src/components/public/` 目录下的公共组件，这些组件具有统一的样式和交互模式，可在应用各处复用。

## 目录结构

```
src/components/public/
├── Card.vue    # 卡片组件
├── Island.vue  # 灵动岛组件
├── Panel.vue   # 面板容器组件
└── Tool.vue    # 工具容器组件
```

---

## Card 组件

### 概述

统一卡片样式的基础容器组件，支持自由调整大小和自定义滚动条。

### 使用方式

```vue
<Card title="卡片标题" usage="display">
  <p>卡片内容</p>
</Card>
```

### 属性

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `title` | `string` | `''` | 卡片标题 |
| `usage` | `string` | `'default'` | 卡片用途类型，用于样式变体 |

### 特性

- **拖拽调整大小**: 支持向右和向下拖拽调整尺寸
- **尺寸持久化**: 拖拽结束后自动保存尺寸到 `uiStore`
- **滚动系统**: 内置隐藏式滚动条
- **Flex 布局**: 支持自适应 Flex 布局

### 事件

无自定义事件，通过 `<slot>` 传递内容。

### 插槽

| 插槽名 | 说明 |
|--------|------|
| `default` | 卡片内容区域 |

### 样式变量

```css
.card-container {
  --color-card-bg: var(--color-card-bg);
  --color-card-border: var(--color-card-border);
  --color-card-divider: var(--color-card-divider);
  --color-card-title: var(--color-card-title);
  --color-card-description: var(--color-card-description);
  --radius-md: var(--radius-md);
  --shadow-sm: var(--shadow-sm);
  --shadow-md: var(--shadow-md);
  --transition-normal: var(--transition-normal);
}
```

### 示例

```vue
<template>
  <Card title="数据统计" usage="display">
    <div class="stats-grid">
      <div class="stat-item">用户数: 1,234</div>
      <div class="stat-item">访问量: 5,678</div>
    </div>
  </Card>
</template>
```

---

## Island 组件

### 概述

灵动岛组件，提供两种交互形态：默认线条状，鼠标悬停时展开为岛状路由切换器。

### 使用方式

```vue
<Island config="Debug" />
```

### 属性

| 属性 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `config` | `string` | 是 | 配置名称，对应 `Island.json` 中的配置项 |

### 特性

- **双形态切换**: 线条状 ↔ 岛状
- **配置驱动**: 通过 `Island.json` 动态加载路由项
- **自动隐藏**: 当底部面板或辅助侧边栏可见时自动隐藏
- **路由切换**: 点击图标切换到对应路由

### 配置格式

在 `src/config/Island.json` 中配置：

```json
{
  "Debug": [
    { "name": "示例1", "route": "/debug/example1", "icon": "/src/assets/icons/add.svg" },
    { "name": "示例2", "route": "/debug/example2", "icon": "/src/assets/icons/Setting.svg" }
  ]
}
```

### 事件

无自定义事件。

### 样式行为

| 状态 | 描述 |
|------|------|
| 默认 | 显示线条状，宽度 80px，高度 4px |
| 悬停 | 展开为岛状，显示路由切换器 |
| 激活 | 当前路由对应的图标高亮 |

### 样式变量

```css
.island-container {
  --color-card-bg: var(--color-card-bg);
  --color-card-border: var(--color-card-border);
  --color-hover: var(--color-hover);
  --color-primary: var(--color-primary);
  --shadow-md: var(--shadow-md);
}
```

---

## Panel 组件

### 概述

底部面板容器组件，提供面板的通用功能：标题、关闭按钮、拖拽调整宽度、可见性管理。

### 使用方式

```vue
<Panel title="日志面板" id="logPanel" :visible="isPanelVisible" @close="handleClose">
  <p>面板内容</p>
</Panel>
```

### 属性

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `title` | `string` | - | 面板标题（必填） |
| `id` | `string` | `panel-${title}` | 面板唯一标识 |
| `visible` | `boolean` | `undefined` | 是否可见，`undefined` 时使用管理器状态 |
| `showClose` | `boolean` | `true` | 是否显示关闭按钮 |

### 可见性优先级

1. `props.visible`（如果提供）
2. `panelManager.isPanelVisible(id)`（如果已注册）
3. 默认可见（直接渲染模式）

### 事件

| 事件名 | 参数 | 说明 |
|--------|------|------|
| `close` | `id?: string` | 点击关闭按钮时触发 |

### 特性

- **拖拽调整宽度**: 支持左右拖拽
- **宽度持久化**: 自动保存和恢复面板宽度
- **滚动系统**: 内容区域支持隐藏式滚动条
- **内存防护**: 完善的清理机制，防止内存泄漏
- **管理器集成**: 可选使用 `panelManager` 进行状态管理

### 插槽

| 插槽名 | 说明 |
|--------|------|
| `default` | 面板内容区域 |

### 组合式 API

组件内部使用以下工具：
- `useDrag`: 拖拽功能
- `useScroll`: 滚动功能
- `useUIStore`: 尺寸持久化
- `panelManager`: 面板管理

### 与 Panel 管理器集成

```typescript
import { panelManager } from '@/utils/Panel'

// 打开面板
panelManager.openPanel('logPanel')

// 关闭面板
panelManager.closePanel('logPanel')

// 切换面板
panelManager.togglePanel('logPanel')

// 检查可见性
panelManager.isPanelVisible('logPanel')
```

---

## Tool 组件

### 概述

辅助侧边栏工具容器组件，提供工具的通用功能：标题、关闭按钮、拖拽调整高度、通信机制。

### 使用方式

```vue
<Tool 
  title="颜色选择器" 
  id="colorTool" 
  :visible="isToolVisible"
  :enableCommunication="true"
  :messageTargets="['otherTool']"
  @close="handleClose"
>
  <template #default="{ sendMessage, onMessage }">
    <!-- 工具内容 -->
  </template>
</Tool>
```

### 属性

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `title` | `string` | - | 工具标题（必填） |
| `id` | `string` | `tool-${title}` | 工具唯一标识 |
| `visible` | `boolean` | `undefined` | 是否可见 |
| `showClose` | `boolean` | `true` | 是否显示关闭按钮 |
| `enableCommunication` | `boolean` | `true` | 是否启用通信机制 |
| `messageTargets` | `string[]` | `[]` | 默认消息目标列表 |

### 事件

| 事件名 | 参数 | 说明 |
|--------|------|------|
| `close` | `id?: string` | 点击关闭按钮时触发 |
| `message` | `message: any` | 收到消息时触发 |

### 插槽

| 插槽名 | 插槽参数 | 说明 |
|--------|----------|------|
| `default` | `{ sendMessage, sendMessageToTargets, onMessage }` | 工具内容区域 |

### 插槽参数说明

| 参数 | 类型 | 说明 |
|------|------|------|
| `sendMessage` | `(target, type, data, contextId) => void` | 发送消息到指定目标 |
| `sendMessageToTargets` | `(type, data, contextId) => void` | 发送到所有预设目标 |
| `onMessage` | `(type, callback) => void` | 监听指定类型消息 |

### 特性

- **拖拽调整高度**: 支持上下拖拽
- **高度持久化**: 自动保存和恢复工具高度
- **滚动系统**: 内容区域支持隐藏式滚动条
- **通信机制**: 支持工具间消息传递
- **管理器集成**: 可选使用 `toolManager` 进行状态管理

### 通信机制

Tool 组件提供完整的消息通信功能，支持跨工具数据传递。

#### 发送消息

```typescript
// 发送消息到单个目标
sendMessage('targetToolId', 'update', { data: 'value' })

// 发送到所有预设目标
sendMessageToTargets('batchUpdate', { items: [...] })

// 带上下文 ID
sendMessage('target', 'action', payload, 'request-123')
```

#### 接收消息

```typescript
onMessage('update', (data, message) => {
  console.log('收到消息:', data)
  console.log('完整消息:', message)
})
```

### 与 Tool 管理器集成

```typescript
import { toolManager } from '@/utils/Tool'

// 打开工具
toolManager.openTool('colorTool')

// 关闭工具
toolManager.closeTool('colorTool')

// 切换工具
toolManager.toggleTool('colorTool')

// 检查可见性
toolManager.isToolVisible('colorTool')

// 获取当前工具集
toolManager.getCurrentToolSet()
```

### 通信存储集成

Tool 组件自动集成 `communicationStore`，提供消息路由功能：

```typescript
import { useCommunicationStore } from '@/stores/communication'

const commStore = useCommunicationStore()

// 发送消息
commStore.sendMessage(from, to, type, data, contextId)

// 注册监听器
commStore.addMessageListener(target, type, callback)

// 注销监听器
commStore.removeMessageListener(target, type)
```

### Provide/Inject

组件通过 `provide` 向子组件注入通信方法：

```typescript
// 子组件获取通信方法
import { inject } from 'vue'

const communication = inject('toolCommunication') as {
  sendMessage: (target: string, type: string, data: any) => void
  onMessage: (type: string, callback: Function) => void
}
```

---

## 组件对比

| 特性 | Card | Panel | Tool |
|------|------|-------|------|
| 用途 | 通用卡片 | 底部面板容器 | 侧边栏工具容器 |
| 拖拽方向 | 右、下 | 左、右 | 上、下 |
| 持久化属性 | 宽、高 | 宽 | 高 |
| 通信机制 | 无 | 无 | 有 |
| 标题位置 | 顶部居左 | 顶部居中 | 顶部居中 |
| 关闭按钮 | 无 | 有 | 有 |

---

## 样式系统

所有公共组件共享以下 CSS 变量：

```css
:root {
  /* 颜色 */
  --color-card-bg: #ffffff;
  --color-card-border: #e5e7eb;
  --color-card-divider: #f3f4f6;
  --color-card-title: #1f2937;
  --color-card-description: #6b7280;
  --color-hover: #f3f4f6;
  --color-primary: #3b82f6;
  
  /* 圆角 */
  --radius-md: 8px;
  
  /* 阴影 */
  --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
  --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  
  /* 过渡 */
  --transition-normal: 0.2s ease;
  --transition-fast: 0.15s ease;
}
```

---

## 最佳实践

### 1. 尺寸持久化

Card、Panel、Tool 组件会自动处理尺寸持久化，但需要确保：

```typescript
// 组件已正确设置 id
<Card id="myCard" title="我的卡片">...</Card>

// UI Store 已初始化
import { useUIStore } from '@/stores/ui'
const uiStore = useUIStore()
```

### 2. 可见性管理

选择合适的可见性管理方式：

**方式一：Props 控制**
```vue
<Panel :visible="isVisible" @close="isVisible = false">
  内容
</Panel>
```

**方式二：管理器控制**
```vue
<Panel id="myPanel">
  内容
</Panel>
```
```typescript
panelManager.openPanel('myPanel')
```

### 3. 工具通信

启用通信机制时，正确处理消息：

```vue
<Tool title="工具" :enableCommunication="true">
  <template #default="{ sendMessage, onMessage }">
    <ChildComponent 
      :sendMessage="sendMessage"
      @message="onMessage('update', handleUpdate)"
    />
  </template>
</Tool>
```

### 4. 清理资源

组件已内置完善的清理逻辑，无需手动处理。但在自定义逻辑中应遵循：

```typescript
onUnmounted(() => {
  // 移除事件监听
  // 取消订阅
  // 清理定时器
})
```
