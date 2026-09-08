import { useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { useLogsStore } from '../../stores/logs';

export default function OutputPanel({ active }: { active: boolean }) {
  const { t } = useTranslation();
  const lines = useLogsStore((s) => s.lines);
  const bodyRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const el = bodyRef.current;
    if (el && active) el.scrollTop = el.scrollHeight;
  }, [lines, active]);

  if (lines.length === 0) {
    return (
      <div className={`bp-body${active ? ' on' : ''}`} data-pane="output">
        <div className="term-out">{t('desktop.output.empty', { defaultValue: '暂无输出' })}</div>
      </div>
    );
  }

  return (
    <div className={`bp-body${active ? ' on' : ''}`} data-pane="output" ref={bodyRef}>
      {lines.map((l, i) => (
        <div key={i} className="log-row">
          <span className="log-time">[{l.time}]</span>{' '}
          <span className={l.kind === 'err' ? 'term-err' : l.kind === 'lsp' ? 'term-prompt' : 'term-out'}>
            {l.text}
          </span>
        </div>
      ))}
    </div>
  );
}