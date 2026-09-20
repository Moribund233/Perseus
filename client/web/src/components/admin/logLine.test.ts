import { describe, it, expect } from 'vitest';
import { parseLogLines, splitLine } from './logLine';

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
