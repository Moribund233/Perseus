/**
 * 编辑器「当前项目」记录 —— 客户端本地保存上次在编辑器中打开的项目，
 * 使退出编辑器后再次进入（/editor 无 owner/repo）时无需重新选择。
 */
const STORAGE_KEY = 'perseus.editor.last';

/** 读取上次在编辑器中打开的项目路径（owner/repo），无记录返回 null */
export function getLastEditorRepo(): string | null {
  try {
    const path = localStorage.getItem(STORAGE_KEY);
    return path && path.includes('/') ? path : null;
  } catch {
    return null;
  }
}

/** 记录编辑器当前项目（owner/repo） */
export function recordEditorRepo(owner: string, repo: string): void {
  try {
    localStorage.setItem(STORAGE_KEY, `${owner}/${repo}`);
  } catch {
    /* ignore storage failures (private mode / quota) */
  }
}
