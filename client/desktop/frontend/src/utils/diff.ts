import type { DiffFile, DiffHunk } from '../api/repositories';

/**
 * 将 Git 统一 diff 文本解析为结构化的文件/行块列表。
 * 用于 PR diff（后端返回裸 patch 文本）渲染，复用 RepoDiffView。
 */
export function parseUnifiedDiff(patch: string): DiffFile[] {
  const files: DiffFile[] = [];
  if (!patch) return files;

  let current: DiffFile | null = null;
  let hunk: DiffHunk | null = null;

  const pushHunk = () => {
    if (current && hunk) {
      current.hunks = current.hunks || [];
      current.hunks.push(hunk);
    }
    hunk = null;
  };

  for (const line of patch.split('\n')) {
    if (line.startsWith('diff --git ')) {
      pushHunk();
      const m = /^diff --git a\/(.*?) b\/(.*)$/.exec(line);
      current = {
        old_path: m?.[1] ?? '',
        new_path: m?.[2] ?? '',
        status: 'M',
        additions: 0,
        deletions: 0,
        hunks: [],
      };
      files.push(current);
      continue;
    }
    if (!current) continue;

    if (line.startsWith('new file mode')) { current.status = 'A'; continue; }
    if (line.startsWith('deleted file mode')) { current.status = 'D'; continue; }
    if (line.startsWith('rename from ')) { current.status = 'R'; current.old_path = line.slice(12); continue; }
    if (line.startsWith('rename to ')) { current.new_path = line.slice(10); continue; }
    if (
      line.startsWith('index ') ||
      line.startsWith('similarity ') ||
      line.startsWith('dissimilarity ') ||
      line.startsWith('old mode ') ||
      line.startsWith('new mode ') ||
      line.startsWith('--- ') ||
      line.startsWith('+++ ') ||
      line.startsWith('Binary files ')
    ) {
      continue;
    }

    if (line.startsWith('@@')) {
      pushHunk();
      const m = /^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@/.exec(line);
      hunk = {
        old_start: Number(m?.[1] ?? 0),
        old_lines: Number(m?.[2] ?? 1),
        new_start: Number(m?.[3] ?? 0),
        new_lines: Number(m?.[4] ?? 1),
        lines: [],
      };
      continue;
    }

    if (hunk && line !== '') {
      const origin = line[0];
      if (origin === '+') current.additions += 1;
      if (origin === '-') current.deletions += 1;
      hunk.lines.push({ origin, content: line.slice(1) });
    }
  }

  pushHunk();
  return files;
}
