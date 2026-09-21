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

/** 终端渲染行：普通日志行或分片分隔行 */
export interface LogRow {
  text: string;
  kind?: 'log' | 'segment';
}

/**
 * 按分片起始偏移在日志行间插入分隔行（用于展示滚动分片的接续）。
 *
 * `segmentStarts` 为服务端返回的窗口内分片起点；仅当窗口跨越多个分片时插入，
 * 单个分片不插入（避免无意义的分隔）。offset=0 的分片也会插入，标示窗口起点。
 */
export function buildSegmentedRows(
  lines: string[],
  segmentStarts: { name: string; offset: number }[],
  segmentLabel: (name: string) => string,
): LogRow[] {
  if (segmentStarts.length <= 1) return lines.map((text) => ({ text }));
  const byOffset = new Map(segmentStarts.map((s) => [s.offset, s.name]));
  const rows: LogRow[] = [];
  lines.forEach((text, i) => {
    const name = byOffset.get(i);
    if (name) rows.push({ text: segmentLabel(name), kind: 'segment' });
    rows.push({ text });
  });
  return rows;
}
