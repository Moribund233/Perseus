type TFn = (key: string, opts?: Record<string, unknown>) => string;

// 相对时间：刚刚 / N 分钟前 / N 小时前 / N 天前 / 日期。
export function timeAgo(iso: string | null | undefined, t: TFn): string {
  if (!iso) return t('desktop.timeAgo.never', { defaultValue: '从未' });
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return '';
  const diff = Date.now() - then;
  const min = Math.floor(diff / 60000);
  if (min < 1) return t('desktop.timeAgo.justNow', { defaultValue: '刚刚' });
  if (min < 60) return t('desktop.timeAgo.minutes', { count: min, defaultValue: `${min} 分钟前` });
  const hours = Math.floor(min / 60);
  if (hours < 24) return t('desktop.timeAgo.hours', { count: hours, defaultValue: `${hours} 小时前` });
  const days = Math.floor(hours / 24);
  if (days < 30) return t('desktop.timeAgo.days', { count: days, defaultValue: `${days} 天前` });
  return t('desktop.timeAgo.days', { count: 30, defaultValue: '30+ 天前' });
}

export function formatDate(iso: string | null | undefined, t: TFn): string {
  if (!iso) return t('desktop.timeAgo.never', { defaultValue: '从未' });
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return t('desktop.timeAgo.never', { defaultValue: '从未' });
  return d.toLocaleDateString(undefined, { year: 'numeric', month: '2-digit', day: '2-digit' });
}