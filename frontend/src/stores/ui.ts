import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import uiConfig from '@/config/UI.json'
import sidebarConfig from '../config/Sidebar.json'

const STORAGE_KEY = 'ui-state-v1'

interface DragSizes {
  cardSizes: Record<string, { width: number; height: number }>
  panelSizes: Record<string, { width: number }>
  toolSizes: Record<string, Record<string, { height: number }>>
}

interface PanelState {
  visiblePanels: string[]
}

interface ToolState {
  visibleTools: Record<string, string[]>
}

interface UIState {
  dragSizes: DragSizes
  panelState: PanelState
  toolState: ToolState
}

export const useUIStore = defineStore('ui', () => {
  const uiState = ref<UIState>({
    dragSizes: {
      cardSizes: {},
      panelSizes: {},
      toolSizes: {}
    },
    panelState: {
      visiblePanels: []
    },
    toolState: {
      visibleTools: {}
    }
  })

  const navigationItems = computed(() => sidebarConfig.mainSidebar.navigation)

  const auxSidebarConfig = computed(() => uiConfig.containers.auxSidebar)

  const setVisiblePanels = (panelIds: string[]): void => {
    uiState.value.panelState.visiblePanels = [...panelIds]
  }

  const addVisiblePanel = (panelId: string): void => {
    if (!uiState.value.panelState.visiblePanels.includes(panelId)) {
      uiState.value.panelState.visiblePanels.push(panelId)
    }
  }

  const removeVisiblePanel = (panelId: string): void => {
    const index = uiState.value.panelState.visiblePanels.indexOf(panelId)
    if (index > -1) {
      uiState.value.panelState.visiblePanels.splice(index, 1)
    }
  }

  const isPanelVisible = (panelId: string): boolean => {
    return uiState.value.panelState.visiblePanels.includes(panelId)
  }

  const clearPanelState = (): void => {
    uiState.value.panelState.visiblePanels = []
  }

  const setVisibleTools = (toolIds: string[], toolSet: string = 'default'): void => {
    uiState.value.toolState.visibleTools[toolSet] = [...toolIds]
  }

  const addVisibleTool = (toolId: string, toolSet: string = 'default'): void => {
    if (!uiState.value.toolState.visibleTools[toolSet]) {
      uiState.value.toolState.visibleTools[toolSet] = []
    }
    
    if (!uiState.value.toolState.visibleTools[toolSet].includes(toolId)) {
      uiState.value.toolState.visibleTools[toolSet].push(toolId)
    }
  }

  const removeVisibleTool = (toolId: string, toolSet: string = 'default'): void => {
    if (uiState.value.toolState.visibleTools[toolSet]) {
      const index = uiState.value.toolState.visibleTools[toolSet].indexOf(toolId)
      if (index > -1) {
        uiState.value.toolState.visibleTools[toolSet].splice(index, 1)
      }
    }
  }

  const isToolVisible = (toolId: string, toolSet: string = 'default'): boolean => {
    return uiState.value.toolState.visibleTools[toolSet]?.includes(toolId) || false
  }

  const clearToolState = (toolSet: string = 'default'): void => {
    uiState.value.toolState.visibleTools[toolSet] = []
  }

  return {
    uiState,
    navigationItems,
    auxSidebarConfig,
    
    setVisiblePanels,
    addVisiblePanel,
    removeVisiblePanel,
    isPanelVisible,
    clearPanelState,
    
    setVisibleTools,
    addVisibleTool,
    removeVisibleTool,
    isToolVisible,
    clearToolState,
    
    saveCardSize: (id: string, size: { width: number; height: number }) => {
      uiState.value.dragSizes.cardSizes[id] = size
    },
    savePanelSize: (id: string, size: { width: number }) => {
      uiState.value.dragSizes.panelSizes[id] = size
    },
    removePanelSize: (id: string) => {
      if (uiState.value.dragSizes.panelSizes[id]) {
        delete uiState.value.dragSizes.panelSizes[id]
      }
    },
    saveToolSize: (id: string, size: { height: number }, toolSet: string = 'default') => {
      if (!uiState.value.dragSizes.toolSizes[toolSet]) {
        uiState.value.dragSizes.toolSizes[toolSet] = {}
      }
      uiState.value.dragSizes.toolSizes[toolSet][id] = size
    },
    getCardSize: (id: string) => uiState.value.dragSizes.cardSizes[id],
    getPanelSize: (id: string) => uiState.value.dragSizes.panelSizes[id],
    getToolSize: (id: string, toolSet: string = 'default') => {
      return uiState.value.dragSizes.toolSizes[toolSet]?.[id]
    }
  }
}, {
  persist: {
    key: STORAGE_KEY,
    storage: localStorage
  }
})
