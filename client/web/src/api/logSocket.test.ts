import { describe, expect, it } from 'vitest';
import { buildSubscribePayload, formatStreamLine, parseLogMessage } from './logSocket';

describe('api/logSocket 纯函数', () => {
  it('buildSubscribePayload 空过滤项不下发', () => {
    expect(buildSubscribePayload({}, 50)).toEqual({
      type: 'subscribe_logs',
      filters: {},
      history_count: 50,
    });
    expect(buildSubscribePayload({ levels: [], loggers: [], keywords: [] }, 10)).toEqual({
      type: 'subscribe_logs',
      filters: {},
      history_count: 10,
    });
  });

  it('buildSubscribePayload 携带全部过滤项', () => {
    expect(
      buildSubscribePayload({ levels: ['INFO', 'ERROR'], loggers: ['app.git'], keywords: ['fail'] }, 200),
    ).toEqual({
      type: 'subscribe_logs',
      filters: { levels: ['INFO', 'ERROR'], loggers: ['app.git'], keywords: ['fail'] },
      history_count: 200,
    });
  });

  it('parseLogMessage 仅接受字段完整的 log 消息', () => {
    expect(
      parseLogMessage({ type: 'log', timestamp: 't', level: 'INFO', logger: 'app', message: 'm' }),
    ).toEqual({ timestamp: 't', level: 'INFO', logger: 'app', message: 'm' });

    expect(parseLogMessage({ type: 'log_history', logs: [] })).toBeNull();
    expect(parseLogMessage({ type: 'log', timestamp: 't', level: 'INFO' })).toBeNull();
    expect(
      parseLogMessage({ type: 'log', timestamp: 't', level: 'ERROR', message: 'm' }),
    ).toEqual({ timestamp: 't', level: 'ERROR', logger: '', message: 'm' });
  });

  it('formatStreamLine 与后端 formatter 对齐（供 splitLine 着色）', () => {
    expect(
      formatStreamLine({
        timestamp: '2026-09-20 10:00:00',
        level: 'INFO',
        logger: 'app.git',
        message: 'done',
      }),
    ).toBe('2026-09-20 10:00:00 - app.git - INFO - done');
  });
});
