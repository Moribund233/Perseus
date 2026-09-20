import { describe, it, expect } from 'vitest';
import { HISTORY_LIMIT, pushSample, toSpark, toSeries, type MetricSample } from './metricsHistory';

function sample(t: number, over: Partial<MetricSample> = {}): MetricSample {
  return { t, mem: 100, cpu: 1, rpm: 2, avgMs: 3, success: 4, failed: 0, ...over };
}

describe('pushSample', () => {
  it('追加并保留全部（未超上限）', () => {
    const h = pushSample([sample(1)], sample(2));
    expect(h.map((s) => s.t)).toEqual([1, 2]);
  });

  it('超过上限时丢弃最旧采样（滚动窗口）', () => {
    let h: MetricSample[] = [];
    for (let i = 1; i <= HISTORY_LIMIT + 5; i++) h = pushSample(h, sample(i));
    expect(h).toHaveLength(HISTORY_LIMIT);
    expect(h[0].t).toBe(6);
    expect(h[h.length - 1].t).toBe(HISTORY_LIMIT + 5);
  });
});

describe('toSpark', () => {
  it('按选择器投影为 {x,y} 序列（x=采样序号）', () => {
    const h = [sample(1, { mem: 10 }), sample(2, { mem: 20 })];
    expect(toSpark(h, (s) => s.mem)).toEqual([{ x: 0, y: 10 }, { x: 1, y: 20 }]);
  });
});

describe('toSeries', () => {
  it('映射为 time/value 且长度一致', () => {
    const h = [sample(1, { rpm: 7 }), sample(2, { rpm: 9 })];
    const series = toSeries(h, (s) => s.rpm);
    expect(series.map((p) => p.value)).toEqual([7, 9]);
    expect(series[0].time).toBeTruthy();
  });
});
