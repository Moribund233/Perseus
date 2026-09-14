import { create } from 'zustand';

// EditorStatusStore：当前活动编辑器 tab 的协作/保存状态，供 StatusBar 渲染双态徽标。
// 由 EditorTabs 写入（活动 tab 变化、协作状态轮询、协作保存回调），StatusBar 只读。
interface EditorStatusState {
  collabActive: boolean;
  collabSynced: boolean;
  lastSavedCommit: string | null;
  update: (patch: Partial<Pick<EditorStatusState, 'collabActive' | 'collabSynced' | 'lastSavedCommit'>>) => void;
  reset: () => void;
}

export const useEditorStatusStore = create<EditorStatusState>((set) => ({
  collabActive: false,
  collabSynced: false,
  lastSavedCommit: null,
  update: (patch) => set(patch),
  reset: () => set({ collabActive: false, collabSynced: false, lastSavedCommit: null }),
}));
