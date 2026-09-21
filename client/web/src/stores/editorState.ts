import { create } from 'zustand';

// 编辑器未保存状态：由 EditorPage 写入，供全局导航（如顶栏切换项目）在离开编辑器前提示。
interface EditorStateStore {
  /** 当前文件相对保存基线有未提交改动 */
  dirty: boolean;
  /** 协作会话仍有未同步到服务端的变更 */
  pending: boolean;
  setDirty: (dirty: boolean) => void;
  setPending: (pending: boolean) => void;
  reset: () => void;
}

export const useEditorStateStore = create<EditorStateStore>((set) => ({
  dirty: false,
  pending: false,
  setDirty: (dirty) => set({ dirty }),
  setPending: (pending) => set({ pending }),
  reset: () => set({ dirty: false, pending: false }),
}));
