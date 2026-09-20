/** 概览页生命体征采样点（由 5s 轮询累积，仅存前端内存） */
export interface MetricSample {
  /** 采样时间 epoch ms */
  t: number;
  /** 内存 MB */
  mem: number;
  /** CPU % */
  cpu: number;
  /** 每分钟请求数 */
  rpm: number;
  /** 平均响应 ms */
  avgMs: number;
  /** 累计成功 */
  success: number;
  /** 累计失败 */
  failed: number;
}

export const HISTORY_LIMIT = 60;

/** 追加一个采样点，保留最近 limit 个（滚动窗口） */
export function pushSample(
  history: MetricSample[],
  sample: MetricSample,
  limit = HISTORY_LIMIT,
): MetricSample[] {
  return [...history, sample].slice(-limit);
}

/** sparkline 数据点（x=采样序号，y=值） */
export interface SparkPoint {
  x: number;
  y: number;
}

/** 投影出 sparkline 数据（G2 需要 x/y 编码） */
export function toSpark(history: MetricSample[], pick: (s: MetricSample) => number): SparkPoint[] {
  return history.map((s, i) => ({ x: i, y: pick(s) }));
}

export interface SeriesPoint {
  time: string;
  value: number;
}

/** 转成折线/面积图数据（x=本地时间字符串） */
export function toSeries(
  history: MetricSample[],
  pick: (s: MetricSample) => number,
): SeriesPoint[] {
  return history.map((s) => ({ time: new Date(s.t).toLocaleTimeString(), value: pick(s) }));
}
