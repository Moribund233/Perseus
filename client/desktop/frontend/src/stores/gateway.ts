import { create } from 'zustand';

export interface GatewayConfig {
  baseURL: string;
  gatewayToken: string;
}

interface GatewayState {
  config: GatewayConfig | null;
  ready: boolean;
  setConfig: (c: GatewayConfig) => void;
}

export const useGatewayStore = create<GatewayState>((set) => ({
  config: null,
  ready: false,
  setConfig: (c) => set({ config: c, ready: true }),
}));

export async function initGateway(): Promise<void> {
  // window.go.main.App 由 Wails 生成，Task 9 之后存在。
  const cfg = await window.go!.main.App.GetGatewayConfig();
  useGatewayStore.getState().setConfig(cfg);
}
