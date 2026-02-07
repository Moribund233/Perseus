# 快速设置系统

## 概述

快速设置（Quick Setting）系统是一个配置驱动的 UI 交互模块，用于管理侧边栏中的可交互设置项。用户可以通过点击这些设置项来触发预设的操作，如切换面板显示、切换主题、导航等。

## 系统架构

```
Sidebar.json (配置源)
        │
        ▼
┌───────────────────────┐
│   stores/quickSetting │ ◄─── Pinia Store (状态管理)
│   - state             │      持久化: quick-setting-state-v1
│   - quickSettings     │
└───────────────────────┘
        │
        ▼
┌───────────────────────┐
│ quickSettingMethods   │ ◄─── 方法注册模块
│ - registerQuickSettingMethod()
└───────────────────────┘
        │
        ▼
┌───────────────────────┐
│   MainSidebar.vue     │ ◄─── UI 渲染
│   - 导航区域          │
│   - 快速设置区域      │
└───────────────────────┘
```

## 目录结构

```
src/
├── stores/
│   └── quickSetting.ts    # Pinia Store，状态管理与持久化
├── utils/
│   └── quickSettingMethods.ts  # 方法注册与实现
├── config/
│   └── Sidebar.json       # 快速设置项配置
└── containers/
    └── MainSidebar.vue    # 快速设置 UI 组件
```

## 核心文件说明

### 1. stores/quickSetting.ts

Pinia Store，负责状态管理和持久化。

**主要职责：**
- 维护快速设置的状态（`state`）
- 从 `Sidebar.json` 读取配置生成 `quickSettings` 列表
- 提供 `handleQuickSetting()` 方法执行设置操作
- 状态持久化到 localStorage（key: `quick-setting-state-v1`）

**导出的组合式函数：**
```typescript
useQuickSetting()      // 获取快速设置状态和操作方法
handleQuickSetting()   // 直接执行快速设置操作
```

### 2. utils/quickSettingMethods.ts

快速设置方法的注册与实现模块。

**使用方式：**
```typescript
registerQuickSettingMethod(
  'methodName',      // 方法名称 (与配置中的 method 对应)
  handler,           // 状态变更处理器
  getState,          // 获取当前激活状态
  getDisplayText     // (可选) 自定义显示文本
)
```

### 3. config/Sidebar.json

快速设置项的配置文件，位于 `mainSidebar.quickSettings` 数组中。

**配置字段：**
| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | string | 设置项唯一标识 |
| `name` | string | UI 显示名称 |
| `icon` | string | 图标路径 |
| `method` | string | 关联的方法名 |
| `default` | boolean | 默认激活状态 |
| `description` | string | (可选) 功能描述 |

---

## 创建快速设置项

### 步骤 1：配置 Sidebar.json

在 `src/config/Sidebar.json` 的 `mainSidebar.quickSettings` 数组中添加新配置：

```json
{
  "id": "immersiveMode",
  "name": "沉浸模式",
  "icon": "/src/assets/icons/immersive.svg",
  "method": "toggleImmersiveMode",
  "default": false,
  "description": "进入沉浸式阅读模式"
}
```

### 步骤 2：更新类型定义

在 `src/stores/quickSetting.ts` 中更新 `QuickSettingState` 接口：

```typescript
interface QuickSettingState {
  bottomPanel: boolean
  auxSidebar: boolean
  sidebarCollapsed: boolean
  currentTheme: ThemeType
  
  // 新增设置项的属性
  immersiveMode: boolean
  
  [key: string]: boolean | string | number
}
```

### 步骤 3：注册方法

在 `src/utils/quickSettingMethods.ts` 中注册方法：

```typescript
registerQuickSettingMethod(
  'toggleImmersiveMode',
  (state, _args, _settingId) => {
    // handler: 执行状态变更
    state.immersiveMode = !state.immersiveMode
  },
  (state, _settingId) => {
    // getState: 返回当前激活状态
    return !!state.immersiveMode
  },
  (state, name, _settingId) => {
    // getDisplayText: (可选) 自定义显示文本
    return `${name} (${state.immersiveMode ? '开启' : '关闭'})`
  }
)
```

### 步骤 4：在 UI 中使用

组件中可以通过 `useQuickSetting` 组合式函数访问：

```typescript
import { useQuickSetting } from '@/stores/quickSetting'

const { isImmersiveMode } = useQuickSetting()

// 或者直接调用
await handleQuickSetting('toggleImmersiveMode', undefined, 'immersiveMode')
```

---

## 方法注册参数说明

`registerQuickSettingMethod` 接受四个参数：

| 参数 | 类型 | 说明 |
|------|------|------|
| `method` | `string` | 方法名称，需与配置文件中的 `method` 字段一致 |
| `handler` | `(state, args, settingId) => void` | 状态变更处理器，接收状态对象、参数和设置 ID |
| `getState` | `(state, settingId) => boolean` | 返回当前激活状态 |
| `getDisplayText` | `(state, name, settingId) => string` | (可选) 返回自定义显示文本 |

### handler 参数说明

```typescript
(state, args, settingId) => {
  // state: QuickSettingState，包含所有设置状态
  // args: 调用时传递的参数数组
  // settingId: 当前设置项的 ID
}
```

---

## 示例：创建导航设置项

### 配置文件 (Sidebar.json)
```json
{
  "id": "goHome",
  "name": "返回首页",
  "icon": "/src/assets/icons/home.svg",
  "method": "navigateTo",
  "default": false,
  "description": "导航到首页"
}
```

### 方法注册 (quickSettingMethods.ts)
```typescript
registerQuickSettingMethod(
  'navigateTo',
  (_, args, _settingId) => {
    // 已有导航方法，可直接使用
    if (args && args.length > 0 && typeof args[0] === 'string') {
      router.push(args[0])
    }
  },
  () => false
)
```

### 使用方式
```typescript
// 在组件中
handleQuickSetting('navigateTo', ['/home'], 'goHome')
```

---

## 状态持久化

快速设置状态会自动持久化到 localStorage：

- **存储 Key**: `quick-setting-state-v1`
- **存储内容**: 包含所有设置项的当前状态
- **恢复逻辑**: 应用启动时从 localStorage 恢复，若无保存数据则使用配置文件默认值

---

## 注意事项

1. **方法名唯一性**: 每个 `method` 名称在系统中必须唯一
2. **配置与方法匹配**: `Sidebar.json` 中的 `method` 必须有对应注册的方法
3. **类型安全**: 新增设置项时建议同步更新 `QuickSettingState` 接口
4. **异步支持**: `handler` 和 `getState` 可以返回 `Promise` 以支持异步操作
