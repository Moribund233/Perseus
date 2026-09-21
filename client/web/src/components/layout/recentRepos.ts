/**
 * 最近打开的项目（仓库）——客户端本地记录，供顶栏快速切换。
 *
 * 无后端依赖：以 localStorage 维护最近访问的仓库列表（去重、上限 8）。
 */
export interface RecentRepo {
  owner: string;
  repo: string;
  /** owner/repo */
  path: string;
  openedAt: number;
}

const STORAGE_KEY = 'perseus.recent.repos';
const MAX_ITEMS = 8;

/** 读取最近打开的项目（解析失败返回空数组） */
export function getRecentRepos(): RecentRepo[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(
      (r): r is RecentRepo =>
        !!r &&
        typeof (r as RecentRepo).owner === 'string' &&
        typeof (r as RecentRepo).repo === 'string' &&
        typeof (r as RecentRepo).path === 'string',
    );
  } catch {
    return [];
  }
}

/** 记录一次访问（置顶去重、裁剪到上限），返回更新后的列表 */
export function recordRecentRepo(owner: string, repo: string): RecentRepo[] {
  const path = `${owner}/${repo}`;
  const next = [
    { owner, repo, path, openedAt: Date.now() },
    ...getRecentRepos().filter((r) => r.path !== path),
  ].slice(0, MAX_ITEMS);
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  } catch {
    /* ignore storage failures (private mode / quota) */
  }
  return next;
}
