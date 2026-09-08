import { create } from 'zustand';

// 门户视图：启动台 / 仓库 / 服务器管理 / 设置。
// 打开工作区（IDE）由 workspace.current 决定，不在此路由内。
export type PortalView = 'welcome' | 'repositories' | 'servers' | 'settings';

interface NavigationState {
  view: PortalView;
  navigate: (view: PortalView) => void;
}

export const useNavigationStore = create<NavigationState>((set) => ({
  view: 'welcome',
  navigate: (view) => set({ view }),
}));