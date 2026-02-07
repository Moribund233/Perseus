# Drag 与 Scroll 系统

本文档介绍项目的拖拽系统（Drag）和滚动系统（Scroll），以及相关的 CSS 样式类。

---

## 目录

- [拖拽系统](#拖拽系统)
- [滚动系统](#滚动系统)
- [滚动条样式](#滚动条样式)
- [公共组件集成](#公共组件集成)

---

## 拖拽系统

### 概述

拖拽系统提供统一的边框拖拽功能，支持四个方向（上下左右）的尺寸调整，并自动处理尺寸持久化。

### 文件位置

```
src/utils/Drag.ts
```

### 核心类型

```typescript
// 拖拽方向
export type DragDirection = 'top' | 'bottom' | 'left' | 'right'
export type DragDirections = DragDirection | DragDirection[]
```

### 配置选项

```typescript
export interface DragOptions {
  /** 拖拽方向，支持单个或数组 */
  direction: DragDirections
  /** 拖拽过程中的回调函数 */
  onDrag?: (size: number, direction: DragDirection) => void
  /** 拖拽结束时的回调函数 */
  onDragEnd?: (size: number, direction: DragDirection) => void
}
```

### 拖拽方向对应的 CSS 类名

| 方向 | 类名 | 光标样式 |
|------|------|----------|
| 顶部 | `drag-top` | `ns-resize` |
| 底部 | `drag-bottom` | `ns-resize` |
| 左侧 | `drag-left` | `ew-resize` |
| 右侧 | `drag-right` | `ew-resize` |

### 核心函数

#### initDragStyles

初始化拖拽样式系统，将样式注入到全局样式表中。

```typescript
import { initDragStyles } from '@/utils/Drag'

initDragStyles()
```

**说明**：
- 自动检测是否已存在样式，避免重复注入
- 生成的样式包含基础样式和四个方向的样式

#### enableDrag

为原生 DOM 元素启用拖拽功能。

```typescript
import { enableDrag } from '@/utils/Drag'

const cleanup = enableDrag(element, {
  direction: ['right', 'bottom'],
  onDrag: (size, direction) => {
    console.log(`拖拽中: ${size}px, 方向: ${direction}`)
  },
  onDragEnd: (size, direction) => {
    console.log(`拖拽结束: ${size}px`)
    // 保存尺寸到持久化存储
    uiStore.savePanelSize(panelId, { width: size })
  }
})

// 清理函数
cleanup()
```

**参数说明**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `element` | `HTMLElement` | 要启用拖拽的元素 |
| `options` | `DragOptions` | 拖拽配置 |

**返回值**：清理函数，用于移除拖拽功能

#### useDrag

Vue 组合式函数，为 Vue 组件提供拖拽功能。

```typescript
import { useDrag } from '@/utils/Drag'
import { useUIStore } from '@/stores/ui'

const uiStore = useUIStore()
const panelId = 'myPanel'

const { elementRef } = useDrag({
  direction: 'right',
  onDrag: (size, direction) => {
    console.log(`尺寸: ${size}px`)
  },
  onDragEnd: (size, direction) => {
    uiStore.savePanelSize(panelId, { width: size })
  }
})
```

**返回值**：

| 属性 | 类型 | 说明 |
|------|------|------|
| `elementRef` | `Ref<HTMLElement>` | 元素引用 |
| `setupDrag` | `() => void` | 重新设置拖拽功能 |

#### applyDragStyle

快速应用拖拽样式（不包含拖拽功能）。

```typescript
import { applyDragStyle } from '@/utils/Drag'

applyDragStyle(element, ['right', 'bottom'])
```

### 拖拽检测区域

拖拽功能在元素边缘 10px 区域内生效：

```
┌──────────────────────────┐
│        ↑ top (10px)      │
│ ┌────────────────────┐   │
│ │                    │   │
│ │                    │ ← left/right (10px)
│ │                    │   │
│ │                    │   │
│ └────────────────────┘   │
│       ↓ bottom (10px)    │
└──────────────────────────┘
```

### 样式效果

拖拽手柄悬停时显示蓝色指示线：

```css
.drag-handle.drag-right:hover,
.drag-handle.drag-right.drag-active {
  box-shadow: inset -4px 0 0 0 rgba(52, 152, 219, 0.6);
}

.drag-handle.drag-bottom:hover,
.drag-handle.drag-bottom.drag-active {
  box-shadow: inset 0 -4px 0 0 rgba(52, 152, 219, 0.6);
}

.drag-handle.drag-left:hover,
.drag-handle.drag-left.drag-active {
  box-shadow: inset 4px 0 0 0 rgba(52, 152, 219, 0.6);
}

.drag-handle.drag-top:hover,
.drag-handle.drag-top.drag-active {
  box-shadow: inset 0 4px 0 0 rgba(52, 152, 219, 0.6);
}
```

### Flex 布局支持

拖拽系统自动检测 Flex 布局，使用 `flex-basis` 控制尺寸：

```typescript
// Flex row 布局中调整宽度
applySize(element, 300, 'right')
// 输出: element.style.flexBasis = '300px'

// 普通布局中调整宽度
applySize(element, 300, 'right')
// 输出: element.style.width = '300px'
```

---

## 滚动系统

### 概述

滚动系统提供增强的滚动功能，支持鼠标滚轮转换、键盘导航、触摸滑动，并解决纯 CSS 无法通过滚轮触发水平滚动的问题。

### 文件位置

```
src/utils/Scroll.ts
```

### 核心类型

```typescript
export type ScrollDirection = 'horizontal' | 'vertical' | 'both'
```

### 配置选项

```typescript
export interface ScrollOptions {
  /** 滚动速度系数，默认1.0 */
  speed?: number
  /** 是否启用平滑滚动，默认true */
  smooth?: boolean
  /** 是否在滚动时显示滚动条，默认false */
  showScrollbar?: boolean
  /** 滚动条显示时间（毫秒），默认2000 */
  scrollbarTimeout?: number
  /** 滚动方向，默认'both' */
  direction?: ScrollDirection
  /** 是否将垂直滚轮转换为水平滚动，默认false */
  wheelToHorizontal?: boolean
}
```

### 核心函数

#### useScroll

为元素启用滚动功能。

```typescript
import { useScroll } from '@/utils/Scroll'

const cleanup = useScroll(element, {
  direction: 'both',
  speed: 1.0,
  smooth: true,
  showScrollbar: true,
  scrollbarTimeout: 2000,
  wheelToHorizontal: false
})

// 清理
cleanup()
```

**参数说明**：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `element` | `HTMLElement` | - | 目标元素 |
| `options` | `ScrollOptions` | `{}` | 配置选项 |

**返回值**：清理函数

#### useHorizontalScroll

水平滚动专用函数。

```typescript
import { useHorizontalScroll } from '@/utils/Scroll'

const cleanup = useHorizontalScroll(element, {
  speed: 1.5,
  showScrollbar: true
})
```

#### enableScroll

通过选择器批量启用滚动。

```typescript
import { enableScroll } from '@/utils/Scroll'

const cleanups = enableScroll('.scrollable-container', {
  direction: 'both',
  showScrollbar: false
})

// 批量清理
cleanups.forEach(cleanup => cleanup())
```

#### scrollToPosition

滚动到指定位置。

```typescript
import { scrollToPosition } from '@/utils/Scroll'

// 滚动到 100px 位置
scrollToPosition(element, 100)

// 滚动到 50% 位置
scrollToPosition(element, '50%')

// 对象形式指定位置
scrollToPosition(element, { left: 100, top: 200 })

// 禁用平滑滚动
scrollToPosition(element, 100, false)
```

#### getScrollInfo

获取滚动信息。

```typescript
import { getScrollInfo } from '@/utils/Scroll'

const info = getScrollInfo(element)

console.log(info.horizontal)
// { scrollLeft, scrollWidth, clientWidth, scrollable, scrollPercentage }

console.log(info.vertical)
// { scrollTop, scrollHeight, clientHeight, scrollable, scrollPercentage }
```

### 滚动功能特性

#### 1. 滚轮转换

支持将垂直滚轮转换为水平滚动：

```typescript
useScroll(element, {
  wheelToHorizontal: true
})
```

当元素只能水平滚动时，垂直滚轮事件自动转换为水平滚动。

#### 2. 键盘导航

支持以下键盘按键：

| 按键 | 方向 | 说明 |
|------|------|------|
| `←` | 左 | 向左滚动 50px |
| `→` | 右 | 向右滚动 50px |
| `↑` | 上 | 向上滚动 50px |
| `↓` | 下 | 向下滚动 50px |
| `Home` | 首尾 | 滚动到起点 |
| `End` | 首尾 | 滚动到终点 |

#### 3. 触摸滑动

支持触摸设备的滑动滚动。

#### 4. 临时滚动条

滚动时临时显示滚动条：

```typescript
useScroll(element, {
  showScrollbar: true,
  scrollbarTimeout: 2000  // 2秒后隐藏
})
```

### 辅助函数

```typescript
// 检测是否可以水平滚动
canScrollHorizontally(element: HTMLElement): boolean

// 检测是否可以垂直滚动
canScrollVertically(element: HTMLElement): boolean
```

---

## 滚动条样式

### 文件位置

```
src/styles/scrollbar.css
```

### 样式类

| 类名 | 说明 |
|------|------|
| `.scrollbar-hide` | 完全隐藏滚动条 |
| `.scrollbar-thin` | 细滚动条（推荐桌面应用） |
| `.scrollbar-horizontal` | 水平滚动条样式 |
| `.scrollbar-horizontal-hide` | 隐藏水平滚动条 |
| `.scrollbar-vertical` | 垂直滚动条样式 |
| `.scrollbar-vertical-hide` | 隐藏垂直滚动条 |
| `.scroll-smooth` | 平滑滚动 |

### 使用示例

```html
<!-- 完全隐藏滚动条 -->
<div class="scrollbar-hide">
  内容
</div>

<!-- 细滚动条 -->
<div class="scrollbar-thin">
  内容
</div>

<!-- 水平滚动条（默认隐藏） -->
<div class="scrollbar-horizontal">
  内容
</div>

<!-- 组合使用 -->
<div class="scrollbar-thin scroll-smooth">
  内容
</div>
```

### 滚动条规格

#### scrollbar-thin

```css
.scrollbar-thin {
  scrollbar-width: thin;
  scrollbar-color: rgba(0, 0, 0, 0.2) transparent;
}

.scrollbar-thin::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

.scrollbar-thin::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.2);
  border-radius: 4px;
}
```

#### scrollbar-horizontal

```css
.scrollbar-horizontal {
  overflow-x: auto;
  overflow-y: hidden;
}

.scrollbar-horizontal::-webkit-scrollbar {
  height: 6px;
}

.scrollbar-horizontal::-webkit-scrollbar-thumb {
  border-radius: 3px;
  min-width: 40px;
}
```

### 暗色主题适配

系统自动适配暗色主题：

```css
@media (prefers-color-scheme: dark) {
  .scrollbar-thin::-webkit-scrollbar-thumb {
    background: rgba(255, 255, 255, 0.2);
  }
  
  .scrollbar-thin::-webkit-scrollbar-thumb:hover {
    background: rgba(255, 255, 255, 0.3);
  }
}
```

---

## 公共组件集成

### Card 组件

```typescript
import { useDrag } from '@/utils/Drag'
import { useScroll } from '@/utils/Scroll'
import { useUIStore } from '@/stores/ui'

const props = defineProps<{
  title?: string
}>()

const uiStore = useUIStore()
const cardId = `card-${props.title || 'default'}`

const { elementRef } = useDrag({
  direction: ['right', 'bottom'],
  onDragEnd: () => {
    if (elementRef.value) {
      const { width, height } = elementRef.value.getBoundingClientRect()
      uiStore.saveCardSize(cardId, { width, height })
    }
  }
})

onMounted(() => {
  if (elementRef.value) {
    useScroll(elementRef.value, { direction: 'both', showScrollbar: false })
    
    const saved = uiStore.getCardSize(cardId)
    if (saved) {
      elementRef.value.style.width = `${saved.width}px`
      elementRef.value.style.height = `${saved.height}px`
    }
  }
})
```

### Panel 组件

```typescript
import { useDrag } from '@/utils/Drag'
import { useScroll } from '@/utils/Scroll'
import { useUIStore } from '@/stores/ui'

const { elementRef: panelRef } = useDrag({
  direction: ['left', 'right'],
  onDragEnd: () => {
    if (panelRef.value) {
      const width = panelRef.value.offsetWidth
      uiStore.savePanelSize(panelId, { width })
    }
  }
})

onMounted(() => {
  if (contentRef.value) {
    useScroll(contentRef.value, { direction: 'vertical', showScrollbar: false })
  }
  
  const saved = uiStore.getPanelSize(panelId)
  if (saved && panelRef.value) {
    panelRef.value.style.width = `${saved.width}px`
  }
})
```

### Tool 组件

```typescript
import { useDrag } from '@/utils/Drag'
import { useScroll } from '@/utils/Scroll'
import { useUIStore } from '@/stores/ui'
import { toolManager } from '@/utils/Tool'

const { elementRef: toolRef } = useDrag({
  direction: ['top', 'bottom'],
  onDragEnd: () => {
    if (toolRef.value) {
      const height = toolRef.value.offsetHeight
      const toolSet = toolManager.getCurrentToolSet()
      uiStore.saveToolSize(toolId, { height }, toolSet)
    }
  }
})

onMounted(() => {
  if (contentRef.value) {
    useScroll(contentRef.value, { direction: 'both', showScrollbar: false })
  }
  
  const toolSet = toolManager.getCurrentToolSet()
  const saved = uiStore.getToolSize(toolId, toolSet)
  if (saved && toolRef.value) {
    toolRef.value.style.height = `${saved.height}px`
  }
})
```

---

## 最佳实践

### 1. 尺寸持久化

```typescript
// 保存尺寸
const handleDragEnd = (size: number, direction: DragDirection) => {
  const sizeMap: Record<DragDirection, () => { width?: number; height?: number }> = {
    top: () => ({ height: size }),
    bottom: () => ({ height: size }),
    left: () => ({ width: size }),
    right: () => ({ width: size })
  }
  
  const { width, height } = sizeMap[direction]()
  uiStore.saveCardSize(cardId, { width: width ?? 0, height: height ?? 0 })
}
```

### 2. 清理资源

```typescript
onUnmounted(() => {
  cleanup?.()
})
```

### 3. 滚动检测

```typescript
// 在滚动前检测是否可以滚动
const handleWheel = (event: WheelEvent) => {
  if (!canScrollHorizontally(element) && !canScrollVertically(element)) {
    return // 不能滚动时不处理
  }
  // 处理滚动
}
```

### 4. 性能优化

```typescript
// 使用 ResizeObserver 监听尺寸变化
const resizeObserver = new ResizeObserver((entries) => {
  for (const entry of entries) {
    console.log('尺寸变化:', entry.contentRect)
  }
})

onMounted(() => {
  resizeObserver.observe(element)
})

onUnmounted(() => {
  resizeObserver.disconnect()
})
```

### 5. 自定义滚动条样式

```css
.custom-scroll {
  scrollbar-width: thin;
  scrollbar-color: var(--primary-color) transparent;
}

.custom-scroll::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

.custom-scroll::-webkit-scrollbar-thumb {
  background: var(--primary-color);
  border-radius: 3px;
}
```
