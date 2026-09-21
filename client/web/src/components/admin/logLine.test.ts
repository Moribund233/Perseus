import { describe, it, expect } from 'vitest';
import { buildSegmentedRows, parseLogLines, splitLine } from './logLine';

describe('splitLine', () => {
  it('切出 INFO 级别并保留前后文', () => {
    const r = splitLine('2026-09-20 12:00:00 INFO perseus 启动完成');
    expect(r.level).toBe('INFO');
    expect(r.head).toContain('2026-09-20');
    expect(r.tail).toContain('启动完成');
  });

  it('识别 ERROR（大小写不敏感）', () => {
    expect(splitLine('error something broke').level).toBe('ERROR');
  });

  it('无级别 token 时 level=null 且整行归 head', () => {
    const r = splitLine('plain line without level');
    expect(r.level).toBeNull();
    expect(r.head).toBe('plain line without level');
    expect(r.tail).toBe('');
  });
});

describe('parseLogLines', () => {
  it('空内容返回空数组', () => {
    expect(parseLogLines(null)).toEqual([]);
    expect(parseLogLines('')).toEqual([]);
  });

  it('按行切分并去掉末尾空行', () => {
    expect(parseLogLines('a\nb\nc\n')).toEqual(['a', 'b', 'c']);
  });

  it('保留中间空行', () => {
    expect(parseLogLines('a\n\nb')).toEqual(['a', '', 'b']);
  });
});

describe('buildSegmentedRows', () => {
  const label = (name: string) => `── 续 ${name} ──`;

  it('单个分片不插入分隔行', () => {
    const rows = buildSegmentedRows(['a', 'b'], [{ name: 'x.log', offset: 0 }], label);
    expect(rows).toEqual([{ text: 'a' }, { text: 'b' }]);
  });

  it('跨分片时按 offset 插入分隔行', () => {
    const rows = buildSegmentedRows(
      ['old', 'mid', 'new'],
      [
        { name: 'x.log.2', offset: 0 },
        { name: 'x.log.1', offset: 1 },
        { name: 'x.log', offset: 2 },
      ],
      label,
    );
    expect(rows).toEqual([
      { text: '── 续 x.log.2 ──', kind: 'segment' },
      { text: 'old' },
      { text: '── 续 x.log.1 ──', kind: 'segment' },
      { text: 'mid' },
      { text: '── 续 x.log ──', kind: 'segment' },
      { text: 'new' },
    ]);
  });

  it('窗口只覆盖部分分片时按实际 offset 插入', () => {
    const rows = buildSegmentedRows(
      ['a', 'b'],
      [
        { name: 'x.log.1', offset: 0 },
        { name: 'x.log', offset: 1 },
      ],
      label,
    );
    expect(rows.filter((r) => r.kind === 'segment').map((r) => r.text)).toEqual([
      '── 续 x.log.1 ──',
      '── 续 x.log ──',
    ]);
  });
});
