/**
 * Panel管理系统
 * 提供面板的注册、状态管理、动态加载等功能
 * 集成面板状态持久化
 */

import { ref, reactive, type Component, markRaw } from 'vue';
import { useUIStore } from '../stores/ui';

const STORAGE_KEY = 'ui-state-v1'

// 面板配置接口
export interface PanelConfig {
  id: string;
  title: string;
  visible: boolean;
  component: string;
}

// 面板实例接口
export interface PanelInstance {
  id: string;
  title: string;
  visible: boolean;
  component: Component;
}

// 面板状态管理
class PanelManager {
  // 面板配置列表
  private panelConfigs = ref<PanelConfig[]>([]);
  
  // 面板实例数组（响应式）
  private panelInstances = ref<PanelInstance[]>([]);
  
  // 面板组件映射
  private panelComponents = reactive<Map<string, Component>>(new Map());
  
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
   * 初始化面板系统
   * 加载配置文件并注册面板，支持状态恢复
   */
  async initialize(): Promise<{success: boolean; loaded: number; errors: number}> {
    try {
      // 加载面板配置
      const panelConfig = await import('../config/Panel.json');
      if (!panelConfig || !panelConfig.default || !Array.isArray(panelConfig.default.panels)) {
        throw new Error('Invalid panel configuration format');
      }
      
      this.panelConfigs.value = panelConfig.default.panels;
      
      // 动态加载并注册面板组件
      await this.loadPanelComponents();
      
      // 应用保存的面板可见性状态
      this.applySavedPanelState();
      
      const loadedCount = this.panelInstances.value.length;
      const errorCount = this.panelInstances.value.filter(p => p.title.startsWith('[错误]')).length;
      const successCount = loadedCount - errorCount;
      
      return {
        success: errorCount === 0,
        loaded: successCount,
        errors: errorCount
      };
    } catch (error) {
      const _error = error instanceof Error ? error : new Error(String(error));
      console.error('Failed to initialize panel system:', _error);
      
      // 创建基础错误面板作为降级
      this.createFallbackPanels();
      
      return {
        success: false,
        loaded: 0,
        errors: 1
      };
    }
  }

  /**
   * 动态加载面板组件
   */
  private async loadPanelComponents(): Promise<void> {
    const loadErrors: Array<{component: string; error: Error}> = [];
    
    for (const config of this.panelConfigs.value) {
      try {
        // 动态导入面板组件
        const componentModule = await import(`@/components/Panel/${config.component}.vue`);
        
        if (!componentModule || !componentModule.default) {
          throw new Error(`Component module is invalid for: ${config.component}`);
        }
        
        this.panelComponents.set(config.id, markRaw(componentModule.default));
        
        // 创建面板实例
        this.createPanelInstance(config);
      } catch (error) {
        const _error = error instanceof Error ? error : new Error(String(error));
        console.error(`Failed to load panel component: ${config.component}`, _error);
        
        // 记录错误信息
        loadErrors.push({
          component: config.component,
          error: _error
        });
        
        // 创建错误面板实例作为降级处理
        this.createErrorPanelInstance(config, _error.message);
      }
    }
  }

  /**
   * 创建面板实例
   */
  private createPanelInstance(config: PanelConfig): void {
    const component = this.panelComponents.get(config.id);
    if (component) {
      const instance: PanelInstance = {
        id: config.id,
        title: config.title,
        visible: config.visible,
        component: markRaw(component)
      };
      this.panelInstances.value.push(instance);
    }
  }

  /**
   * 创建错误面板实例（降级处理）
   */
  private createErrorPanelInstance(config: PanelConfig, errorMessage: string): void {
    // 创建简单的错误提示组件
    const errorComponent = {
      template: `
        <div class="error-panel">
          <div class="error-content">
            <h3>⚠️ 面板加载失败</h3>
            <p><strong>面板名称:</strong> ${config.title}</p>
            <p><strong>组件路径:</strong> ${config.component}</p>
            <p><strong>错误信息:</strong> ${errorMessage}</p>
            <button @click="reloadPanel" class="reload-btn">重新加载</button>
          </div>
        </div>
      `,
      methods: {
        reloadPanel() {
          window.location.reload();
        }
      }
    };

    const instance: PanelInstance = {
      id: config.id,
      title: `[错误] ${config.title}`,
      visible: false, // 默认隐藏错误面板
      component: errorComponent
    };
    
    this.panelInstances.value.push(instance);
  }

  /**
   * 创建基础错误面板（系统级降级）
   */
  private createFallbackPanels(): void {
    // 创建基础错误面板
    const fallbackComponent = {
      template: `
        <div class="fallback-panel">
          <div class="fallback-content">
            <h3>🚨 面板系统初始化失败</h3>
            <p>系统无法正常加载面板组件，请检查配置文件和组件路径。</p>
            <button @click="reloadApp" class="reload-btn">重新启动应用</button>
          </div>
        </div>
      `,
      methods: {
        reloadApp() {
          window.location.reload();
        }
      }
    };

    const fallbackPanel: PanelInstance = {
      id: 'fallback-panel',
      title: '系统错误',
      visible: true,
      component: fallbackComponent
    };
    
    this.panelInstances.value.push(fallbackPanel);
  }

  /**
   * 应用保存的面板状态
   */
  private applySavedPanelState(): void {
    const stored = localStorage.getItem(STORAGE_KEY);
    let hasActualData = false;
    
    if (stored) {
      try {
        const parsed = JSON.parse(stored);
        hasActualData = (
          (parsed.panelState && parsed.panelState.visiblePanels) ||
          (parsed.state && parsed.state.ui && parsed.state.ui.panelState)
        );
      } catch {}
    }
    
    if (stored && hasActualData) {
      this.panelInstances.value.forEach(panel => {
        panel.visible = this.uiStore.isPanelVisible(panel.id);
      });
    } else {
      this.panelInstances.value.forEach(panel => {
        const config = this.panelConfigs.value.find(c => c.id === panel.id);
        if (config) {
          panel.visible = config.visible;
        }
      });
      this.saveCurrentPanelState();
    }
  }

  /**
   * 保存当前面板状态
   */
  private saveCurrentPanelState(): void {
    const visiblePanelIds = this.getVisiblePanelIds();
    this.uiStore.setVisiblePanels(visiblePanelIds);
  }

  /**
   * 获取所有面板实例
   */
  getAllPanels(): PanelInstance[] {
    return this.panelInstances.value;
  }

  /**
   * 获取可见面板
   */
  getVisiblePanels(): PanelInstance[] {
    return this.panelInstances.value.filter(panel => panel.visible);
  }

  /**
   * 获取面板实例
   */
  getPanel(id: string): PanelInstance | undefined {
    return this.panelInstances.value.find(panel => panel.id === id);
  }

  /**
   * 显示面板
   */
  showPanel(id: string): void {
    const panel = this.panelInstances.value.find(p => p.id === id);
    if (panel) {
      panel.visible = true;
      this.uiStore.addVisiblePanel(id);
    }
  }

  /**
   * 隐藏面板
   */
  hidePanel(id: string): void {
    const panel = this.panelInstances.value.find(p => p.id === id);
    if (panel) {
      panel.visible = false;
      this.uiStore.removeVisiblePanel(id);
    }
  }

  /**
   * 切换面板显示状态
   */
  togglePanel(id: string): void {
    const panel = this.panelInstances.value.find(p => p.id === id);
    if (panel) {
      panel.visible = !panel.visible;
    }
  }

  /**
   * 关闭面板（触发关闭事件）
   */
  closePanel(id: string): void {
    this.hidePanel(id);
    // 可以在这里添加关闭回调
  }

  /**
   * 检查面板是否可见
   */
  isPanelVisible(id: string): boolean {
    return this.uiStore.isPanelVisible(id);
  }

  /**
   * 获取可见面板的ID列表
   */
  getVisiblePanelIds(): string[] {
    return this.panelInstances.value
      .filter(panel => panel.visible)
      .map(panel => panel.id);
  }

  /**
   * 注册新面板
   */
  registerPanel(config: PanelConfig, component: Component): void {
    this.panelConfigs.value.push(config);
    this.panelComponents.set(config.id, component);
    this.createPanelInstance(config);
  }

  /**
   * 卸载面板（完全清理）
   */
  unregisterPanel(id: string): void {
    // 清理面板实例
    const index = this.panelInstances.value.findIndex(panel => panel.id === id);
    if (index > -1) {
      const panel = this.panelInstances.value[index];
      
      // 执行面板特定的清理逻辑（如果有的话）
      this.cleanupPanelResources(panel);
      
      this.panelInstances.value.splice(index, 1);
    }
    
    // 清理组件引用
    if (this.panelComponents.has(id)) {
      this.panelComponents.delete(id);
    }
    
    // 清理配置
    const configIndex = this.panelConfigs.value.findIndex(config => config.id === id);
    if (configIndex > -1) {
      this.panelConfigs.value.splice(configIndex, 1);
    }
    
    // 清理UI状态
    this.uiStore.removeVisiblePanel(id);
    this.uiStore.removePanelSize(id);
  }

  /**
   * 清理面板资源（扩展点）
   */
  private cleanupPanelResources(panel: PanelInstance): void {
    // 这里可以添加面板特定的资源清理逻辑
    // 例如：清理事件监听器、定时器、网络请求等
    
    // 检查是否为错误面板，如果是可以执行额外的清理
    if (panel.title.startsWith('[错误]')) {
      // 错误面板特定的清理逻辑
    }
    
    // 可以在这里添加更多资源清理逻辑
  }

  /**
   * 清理所有面板资源（系统级清理）
   */
  cleanupAll(): void {
    // 清理所有面板实例
    while (this.panelInstances.value.length > 0) {
      const panel = this.panelInstances.value[0];
      this.unregisterPanel(panel.id);
    }
    
    // 清理组件映射
    this.panelComponents.clear();
    
    // 清理配置
    this.panelConfigs.value = [];
  }
}

// 创建单例实例
export const panelManager = new PanelManager();

// 组合式函数，方便在组件中使用
export function usePanel() {
  return {
    // 获取所有面板
    getAllPanels: () => panelManager.getAllPanels(),
    
    // 获取可见面板
    getVisiblePanels: () => panelManager.getVisiblePanels(),
    
    // 获取可见面板ID列表
    getVisiblePanelIds: () => panelManager.getVisiblePanelIds(),
    
    // 获取指定面板
    getPanel: (id: string) => panelManager.getPanel(id),
    
    // 显示面板
    showPanel: (id: string) => panelManager.showPanel(id),
    
    // 隐藏面板
    hidePanel: (id: string) => panelManager.hidePanel(id),
    
    // 切换面板
    togglePanel: (id: string) => panelManager.togglePanel(id),
    
    // 关闭面板
    closePanel: (id: string) => panelManager.closePanel(id),
    
    // 注册面板
    registerPanel: (config: PanelConfig, component: Component) => 
      panelManager.registerPanel(config, component),
    
    // 卸载面板
    unregisterPanel: (id: string) => panelManager.unregisterPanel(id)
  };
}