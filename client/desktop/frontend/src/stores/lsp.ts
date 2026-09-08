import { create } from 'zustand';

export type LspStatus = 'idle' | 'connecting' | 'connected' | 'disconnected';

interface LspState {
  status: LspStatus;
  lang: string | null;
  error: string | null;
  setStatus: (s: LspStatus) => void;
  setLang: (lang: string | null) => void;
  setError: (msg: string | null) => void;
}

// 语言服务状态：状态栏“语言服务”指示 + 输出面板记录由各消费方联动。
export const useLspStore = create<LspState>((set) => ({
  status: 'idle',
  lang: null,
  error: null,
  setStatus: (status) => set({ status }),
  setLang: (lang) => set({ lang }),
  setError: (error) => set({ error }),
}));