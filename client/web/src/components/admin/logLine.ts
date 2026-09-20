export const LEVELS = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'] as const;

export interface SplitLine {
  head: string;
  level: string | null;
  tail: string;
}

/** 从单行日志中切出级别 token，用于着色（找不到级别时 level=null） */
export function splitLine(line: string): SplitLine {
  const upper = line.toUpperCase();
  for (const lv of LEVELS) {
    const idx = upper.indexOf(lv);
    if (idx >= 0) {
      return { head: line.slice(0, idx), level: lv, tail: line.slice(idx + lv.length) };
    }
  }
  return { head: line, level: null, tail: '' };
}

/** 把日志内容文本切成行数组（去掉末尾空行） */
export function parseLogLines(content: string | null | undefined): string[] {
  if (!content) return [];
  const raw = content.split('\n');
  if (raw.length > 1 && raw[raw.length - 1] === '') raw.pop();
  return raw;
}
