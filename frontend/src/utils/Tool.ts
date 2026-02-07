/**
 * Tool管理系统
 * 提供工具的注册、状态管理、动态加载等功能
 * 集成工具状态持久化
 */

import { ref, reactive, type Component } from 'vue';
import { useUIStore } from '../stores/ui';

// 工具配置接口
export interface ToolConfig {
  id: string;
  title: string;
  visible: boolean;
  component: string;
  key?: string; // 用于配置特定工具集的键名
}

// 工具实例接口
export interface ToolInstance {
  id: string;
  title: string;
  visible: boolean;
  component: Component;
  key?: string;
}

// 工具状态管理
class ToolManager {
  // 工具配置映射，键为工具集名称，值为工具配置数组
  private toolConfigs = ref<Record<string, ToolConfig[]>>({});
  
  // 当前使用的工具集键名
  private currentToolSet = ref<string>('default');
  
  // 工具实例数组（响应式）
  private toolInstances = ref<ToolInstance[]>([]);
  
  // 工具组件映射
  private toolComponents = reactive<Map<string, Component>>(new Map());
  
  // UI状态存储（延迟初始化）
  private _uiStore: ReturnType<typeof useUIStore> | null = null;
  
  // 获取UI存储（延迟初始化）
  private get uiStore() {
    if (!this._uiStore) {
      this._uiStore = useUIStore();
    }
    return this._uiStore;
  }

  /**
   * 初始化工具系统
   * 加载配置文件并注册工具，支持状态恢复
   */
  async initialize(): Promise<void> {
    try {
      console.log('Initializing tool system...');
      
      // 加载工具配置
      const toolConfig = await import('../config/Tool.json');
      this.toolConfigs.value = toolConfig.default;
      console.log('Tool configs loaded:', this.toolConfigs.value);
      
      // 动态加载并注册所有工具组件
      await this.loadAllToolComponents();
      
      // 初始化当前工具集的工具实例
      this.initializeToolInstances();
      
      // 应用保存的工具可见性状态
      this.applySavedToolState();
      
      console.log('Tool system initialized successfully');
      console.log('Total tools:', this.toolInstances.value.length);
      console.log('Visible tools:', this.getVisibleTools().length);
    } catch (error) {
      console.error('Failed to initialize tool system:', error);
    }
  }

  /**
   * 动态加载所有工具集中的工具组件
   */
  private async loadAllToolComponents(): Promise<void> {
    // 收集所有工具配置，去重处理
    const allToolConfigs = new Map<string, ToolConfig>();
    
    // 遍历所有工具集
    for (const [key, configs] of Object.entries(this.toolConfigs.value)) {
      for (const config of configs) {
        // 使用工具ID作为唯一标识，避免重复加载
        if (!allToolConfigs.has(config.id)) {
          allToolConfigs.set(config.id, { ...config, key });
        }
      }
    }
    
    // 加载所有去重后的工具组件
    for (const config of allToolConfigs.values()) {
      try {
        // 动态导入工具组件
        const componentModule = await import(`../components/Tool/${config.component}.vue`);
        this.toolComponents.set(config.id, componentModule.default);
        console.log(`Loaded tool component: ${config.component}`);
      } catch (error) {
        console.error(`Failed to load tool component: ${config.component}`, error);
      }
    }
  }

  /**
   * 初始化当前工具集的工具实例
   */
  private initializeToolInstances(): void {
    // 清空现有实例
    this.toolInstances.value = [];
    
    // 获取当前工具集的配置
    const currentConfigs = this.toolConfigs.value[this.currentToolSet.value] || [];
    
    // 创建工具实例
    for (const config of currentConfigs) {
      this.createToolInstance({ ...config, key: this.currentToolSet.value });
    }
  }

  /**
   * 创建工具实例
   */
  private createToolInstance(config: ToolConfig): void {
    const component = this.toolComponents.get(config.id);
    if (component) {
      const instance: ToolInstance = {
        id: config.id,
        title: config.title,
        visible: config.visible,
        component,
        key: config.key || 'default' // 默认使用default键名
      };
      this.toolInstances.value.push(instance);
    }
  }

  /**
   * 应用保存的工具状态
   */
  private applySavedToolState(): void {
    // 检查当前工具集是否在UI存储中存在
    const toolSetExists = this.uiStore.uiState.toolState.visibleTools.hasOwnProperty(this.currentToolSet.value);
    
    if (toolSetExists) {
      // 如果工具集存在，使用保存的状态
      this.toolInstances.value.forEach(tool => {
        tool.visible = this.uiStore.isToolVisible(tool.id, this.currentToolSet.value);
      });
      
      console.log(`已应用保存的工具状态（工具集：${this.currentToolSet.value}）:`, this.uiStore.uiState.toolState.visibleTools[this.currentToolSet.value] || []);
    } else {
      // 如果工具集不存在，说明是首次使用，使用配置中的默认值并保存
      // 使用当前工具集配置中的默认可见性
      this.toolInstances.value.forEach(tool => {
        const currentConfigs = this.toolConfigs.value[this.currentToolSet.value] || [];
        const config = currentConfigs.find(c => c.id === tool.id);
        if (config) {
          tool.visible = config.visible;
        }
      });
      
      // 保存默认状态
      this.saveCurrentToolState();
      console.log(`使用默认工具状态并保存（工具集：${this.currentToolSet.value}）`);
    }
  }

  /**
   * 保存当前工具状态
   */
  private saveCurrentToolState(): void {
    const visibleToolIds = this.getVisibleToolIds();
    this.uiStore.setVisibleTools(visibleToolIds, this.currentToolSet.value);
    console.log(`当前工具状态已保存（工具集：${this.currentToolSet.value}）`);
  }

  /**
   * 获取所有工具实例
   */
  getAllTools(): ToolInstance[] {
    return this.toolInstances.value;
  }

  /**
   * 获取可见工具
   */
  getVisibleTools(): ToolInstance[] {
    return this.toolInstances.value.filter(tool => tool.visible);
  }

  /**
   * 切换工具集
   * @param key 工具集键名
   */
  switchToolSet(key: string): void {
    if (this.toolConfigs.value[key]) {
      this.currentToolSet.value = key;
      this.initializeToolInstances();
      this.applySavedToolState();
      console.log(`Switched to tool set: ${key}`);
    } else {
      console.warn(`Tool set ${key} not found`);
    }
  }

  /**
   * 获取当前工具集
   */
  getCurrentToolSet(): string {
    return this.currentToolSet.value;
  }

  /**
   * 获取所有工具集名称
   */
  getToolSetNames(): string[] {
    return Object.keys(this.toolConfigs.value);
  }

  /**
   * 获取工具实例
   */
  getTool(id: string): ToolInstance | undefined {
    return this.toolInstances.value.find(tool => tool.id === id);
  }

  /**
   * 显示工具
   */
  showTool(id: string): void {
    const tool = this.toolInstances.value.find(p => p.id === id);
    if (tool) {
      tool.visible = true;
      this.uiStore.addVisibleTool(id, this.currentToolSet.value);
      console.log(`工具 ${id} 已显示并保存状态（工具集：${this.currentToolSet.value}）`);
    }
  }

  /**
   * 隐藏工具
   */
  hideTool(id: string): void {
    const tool = this.toolInstances.value.find(p => p.id === id);
    if (tool) {
      tool.visible = false;
      this.uiStore.removeVisibleTool(id, this.currentToolSet.value);
      console.log(`工具 ${id} 已隐藏并保存状态（工具集：${this.currentToolSet.value}）`);
    }
  }

  /**
   * 切换工具显示状态
   */
  toggleTool(id: string): void {
    const tool = this.toolInstances.value.find(p => p.id === id);
    if (tool) {
      tool.visible = !tool.visible;
      if (tool.visible) {
        this.uiStore.addVisibleTool(id, this.currentToolSet.value);
      } else {
        this.uiStore.removeVisibleTool(id, this.currentToolSet.value);
      }
    }
  }

  /**
   * 关闭工具（触发关闭事件）
   */
  closeTool(id: string): void {
    this.hideTool(id);
    // 可以在这里添加关闭回调
  }

  /**
   * 检查工具是否可见
   */
  isToolVisible(id: string): boolean {
    return this.uiStore.isToolVisible(id, this.currentToolSet.value);
  }

  /**
   * 获取可见工具的ID列表
   */
  getVisibleToolIds(): string[] {
    return this.toolInstances.value
      .filter(tool => tool.visible)
      .map(tool => tool.id);
  }

  /**
   * 注册新工具
   */
  registerTool(config: ToolConfig, component: Component): void {
    // 使用默认工具集
    const toolSet = config.key || 'default';
    
    // 如果工具集不存在，创建它
    if (!this.toolConfigs.value[toolSet]) {
      this.toolConfigs.value[toolSet] = [];
    }
    
    // 检查工具是否已存在
    const existingIndex = this.toolConfigs.value[toolSet].findIndex(c => c.id === config.id);
    if (existingIndex > -1) {
      // 更新现有配置
      this.toolConfigs.value[toolSet][existingIndex] = config;
    } else {
      // 添加新配置
      this.toolConfigs.value[toolSet].push(config);
    }
    
    // 更新组件映射
    this.toolComponents.set(config.id, component);
    
    // 如果是当前工具集，更新实例
    if (toolSet === this.currentToolSet.value) {
      // 移除旧实例（如果存在）
      const instanceIndex = this.toolInstances.value.findIndex(tool => tool.id === config.id);
      if (instanceIndex > -1) {
        this.toolInstances.value.splice(instanceIndex, 1);
      }
      // 创建新实例
      this.createToolInstance(config);
    }
    
    console.log(`Tool ${config.id} registered to tool set ${toolSet}`);
  }

  /**
   * 卸载工具
   */
  unregisterTool(id: string): void {
    // 从实例中移除
    const instanceIndex = this.toolInstances.value.findIndex(tool => tool.id === id);
    if (instanceIndex > -1) {
      this.toolInstances.value.splice(instanceIndex, 1);
    }
    
    // 从组件映射中移除
    this.toolComponents.delete(id);
    
    // 从所有工具集中移除配置
    for (const [toolSet, configs] of Object.entries(this.toolConfigs.value)) {
      const configIndex = configs.findIndex(config => config.id === id);
      if (configIndex > -1) {
        this.toolConfigs.value[toolSet].splice(configIndex, 1);
        console.log(`Tool ${id} removed from tool set ${toolSet}`);
      }
    }
    
    console.log(`Tool ${id} unregistered`);
  }
}

// 创建单例实例
export const toolManager = new ToolManager();

// 组合式函数，方便在组件中使用
export function useTool() {
  return {
    // 获取所有工具
    getAllTools: () => toolManager.getAllTools(),
    
    // 获取可见工具
    getVisibleTools: () => toolManager.getVisibleTools(),
    
    // 获取可见工具ID列表
    getVisibleToolIds: () => toolManager.getVisibleToolIds(),
    
    // 获取指定工具
    getTool: (id: string) => toolManager.getTool(id),
    
    // 显示工具
    showTool: (id: string) => toolManager.showTool(id),
    
    // 隐藏工具
    hideTool: (id: string) => toolManager.hideTool(id),
    
    // 切换工具
    toggleTool: (id: string) => toolManager.toggleTool(id),
    
    // 关闭工具
    closeTool: (id: string) => toolManager.closeTool(id),
    
    // 注册工具
    registerTool: (config: ToolConfig, component: Component) => 
      toolManager.registerTool(config, component),
    
    // 卸载工具
    unregisterTool: (id: string) => toolManager.unregisterTool(id),
    
    // 切换工具集
    switchToolSet: (key: string) => toolManager.switchToolSet(key),
    
    // 获取当前工具集
    getCurrentToolSet: () => toolManager.getCurrentToolSet(),
    
    // 获取所有工具集名称
    getToolSetNames: () => toolManager.getToolSetNames()
  };
}