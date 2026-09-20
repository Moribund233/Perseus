import { useTranslation } from 'react-i18next';
import type { ComponentInfo } from '../../api/admin';
import HealthChip from './HealthChip';
import StatusDot from './StatusDot';
import { componentTone, formatDuration, isProblem, type Tone } from './health';

interface ComponentRowProps {
  component: ComponentInfo;
  /** 最近 N 次检查的色调（旧→新），用于迷你历史条 */
  history: Tone[];
  selected: boolean;
  onClick: () => void;
}

function stateLabel(state: string): string {
  switch (state) {
    case 'running': return 'running';
    case 'exited': return 'exited';
    case 'restarting': return 'restarting';
    case 'created': return 'created';
    case 'dead': return 'dead';
    case 'paused': return 'paused';
    default: return 'unknown';
  }
}

export default function ComponentRow({ component: c, history, selected, onClick }: ComponentRowProps) {
  const { t } = useTranslation();
  const tone = componentTone(c);
  const labelKey = c.health ? c.health : stateLabel(c.state);
  const metaParts = [
    c.uptime_seconds !== null && c.uptime_seconds !== undefined ? formatDuration(c.uptime_seconds) : null,
    c.restart_count != null ? `r${c.restart_count}` : null,
    c.image || null,
  ].filter(Boolean);

  return (
    <div
      className={`ac-comp-row${selected ? ' selected' : ''}`}
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onClick(); } }}
    >
      <StatusDot tone={tone} title={c.status_text || undefined} />
      <div className="ac-comp-main">
        <div className="ac-comp-name">
          {c.label || c.service}
          {isProblem(c) && <span className="ac-comp-service">{t('app.admin.components.problem')}</span>}
        </div>
        <div className="ac-comp-service">
          {c.service}
          {c.status_text ? ` · ${c.status_text}` : ''}
        </div>
        <div className="ac-comp-meta">{metaParts.join(' · ')}</div>
      </div>
      <div className="ac-comp-side">
        <span className="ac-history" title={t('app.admin.components.historyTitle')}>
          {history.map((toneItem, i) => (
            <span key={i} className={`ac-history-bar ${toneItem}`} />
          ))}
        </span>
        <HealthChip tone={tone}>{t(`app.admin.components.health.${labelKey}`)}</HealthChip>
      </div>
    </div>
  );
}