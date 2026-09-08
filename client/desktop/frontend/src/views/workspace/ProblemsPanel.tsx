import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { useProblemsStore, severityLabel } from '../../stores/problems';

interface Props {
  rootPath: string;
  active: boolean;
  onOpen: (path: string, line?: number) => void;
}

// ProblemsPanel：底部面板“问题”，数据由 LSP publishDiagnostics → problems store 驱动。
export default function ProblemsPanel({ rootPath, active, onOpen }: Props) {
  const { t } = useTranslation();
  const diagnostics = useProblemsStore((s) => s.diagnostics);

  const rows = useMemo(() => {
    const prefix = rootPath.replace(/[\\/]/g, '/').replace(/\/$/, '') + '/';
    return [...diagnostics]
      .sort((a, b) => a.uri.localeCompare(b.uri) || a.range.start.line - b.range.start.line)
      .map((d) => ({
        d,
        file: d.uri.startsWith('file://')
          ? decodeURIComponent(d.uri.slice('file://'.length)).replace(/\\/g, '/').replace(prefix, '')
          : d.uri,
      }));
  }, [diagnostics, rootPath]);

  if (rows.length === 0) {
    return (
      <div className={`bp-body${active ? ' on' : ''}`} data-pane="problems">
        <div className="term-out">{t('desktop.problems.empty', { defaultValue: '暂无问题 ✓' })}</div>
      </div>
    );
  }

  return (
    <div className={`bp-body${active ? ' on' : ''}`} data-pane="problems">
      {rows.map(({ d, file }, i) => (
        <div
          key={`${d.uri}:${d.range.start.line}:${i}`}
          className="prob-row"
          onClick={() => onOpen(file, d.range.start.line + 1)}
        >
          <span className={`ic ${d.severity === 1 ? 'e' : 'w'}`}>
            {d.severity === 1 ? '⨯' : d.severity === 2 ? '⚠' : 'ℹ'}
          </span>
          <span className="msg">{d.message}</span>
          <span className="where">
            {file} [Ln {d.range.start.line + 1}, Col {d.range.start.character + 1}]
          </span>
          <span className="src">{d.source ?? severityLabel(d.severity)}</span>
        </div>
      ))}
    </div>
  );
}