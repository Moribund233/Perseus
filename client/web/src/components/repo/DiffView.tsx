import { useState } from 'react';
import { Empty } from 'antd';
import { FileOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { DiffFile } from '../../api/repositories';

const borderColor = '#21262d';
const textPrimary = '#e6edf3';
const textSecondary = '#8b949e';
const textTertiary = '#6e7681';
const bgSecondary = '#161b22';
const bgTertiary = '#1c2128';
const green = '#3fb950';
const red = '#f85149';
const amber = '#d29922';
const blue = '#58a6ff';

const statusColor: Record<string, string> = {
  A: green,
  D: red,
  M: amber,
  R: blue,
  C: blue,
  '?': textSecondary,
};

function LineRow({ origin, content, oldNo, newNo }: { origin: string; content: string; oldNo: number | null; newNo: number | null }) {
  const isAdd = origin === '+';
  const isDel = origin === '-';
  const bg = isAdd ? 'rgba(63,185,80,0.12)' : isDel ? 'rgba(248,81,73,0.12)' : 'transparent';
  const marker = isAdd ? green : isDel ? red : textTertiary;
  return (
    <div style={{ display: 'flex', background: bg, fontSize: 12.5, lineHeight: '20px', fontFamily: "'JetBrains Mono','Fira Code','Consolas',monospace" }}>
      <span style={{ width: 44, flexShrink: 0, textAlign: 'right', paddingRight: 8, color: textTertiary, userSelect: 'none' }}>{oldNo ?? ''}</span>
      <span style={{ width: 44, flexShrink: 0, textAlign: 'right', paddingRight: 8, color: textTertiary, userSelect: 'none' }}>{newNo ?? ''}</span>
      <span style={{ width: 16, flexShrink: 0, textAlign: 'center', color: marker, userSelect: 'none' }}>{origin === ' ' ? '' : origin}</span>
      <span style={{ flex: 1, whiteSpace: 'pre-wrap', wordBreak: 'break-all', color: textPrimary, paddingRight: 12 }}>{content}</span>
    </div>
  );
}

function FileDiff({ file }: { file: DiffFile }) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(true);
  const path = file.new_path || file.old_path;
  const color = statusColor[file.status] ?? textSecondary;

  return (
    <div style={{ border: `1px solid ${borderColor}`, borderRadius: 10, overflow: 'hidden', background: bgSecondary, marginBottom: 12 }}>
      <div
        onClick={() => setOpen((v) => !v)}
        style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '9px 14px', background: bgTertiary, cursor: 'pointer', fontSize: 13 }}
      >
        <span style={{ color, fontWeight: 700, width: 14, flexShrink: 0 }}>{file.status}</span>
        <FileOutlined style={{ color: textTertiary, flexShrink: 0 }} />
        <span style={{ color: textPrimary, fontFamily: 'monospace', flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {file.status === 'R' && file.old_path !== file.new_path ? `${file.old_path} → ${path}` : path}
        </span>
        <span style={{ color: green, fontSize: 12, flexShrink: 0 }}>+{file.additions}</span>
        <span style={{ color: red, fontSize: 12, flexShrink: 0 }}>-{file.deletions}</span>
      </div>

      {open && (file.hunks?.length ? file.hunks.map((h, i) => {
        let oldNo = h.old_start;
        let newNo = h.new_start;
        return (
          <div key={i} style={{ borderTop: i === 0 ? `1px solid ${borderColor}` : 'none' }}>
            <div style={{ padding: '2px 14px', background: 'rgba(88,166,255,0.08)', color: blue, fontSize: 12, fontFamily: 'monospace' }}>
              @@ -{h.old_start},{h.old_lines} +{h.new_start},{h.new_lines} @@
            </div>
            {h.lines.map((ln, j) => {
              const o = ln.origin;
              const showOld = o !== '+';
              const showNew = o !== '-';
              const row = <LineRow key={j} origin={o} content={ln.content} oldNo={showOld ? oldNo : null} newNo={showNew ? newNo : null} />;
              if (showOld) oldNo += 1;
              if (showNew) newNo += 1;
              return row;
            })}
          </div>
        );
      }) : (
        <div style={{ padding: '10px 14px', color: textTertiary, fontSize: 12 }}>{t('app.repositories.gitBrowser.binaryOrEmpty')}</div>
      ))}
    </div>
  );
}

export default function DiffView({ files, emptyText }: { files: DiffFile[]; emptyText?: string }) {
  const { t } = useTranslation();
  if (!files.length) {
    return (
      <div style={{ border: `1px solid ${borderColor}`, borderRadius: 12, background: bgSecondary }}>
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={<span style={{ color: textSecondary }}>{emptyText ?? t('app.repositories.gitBrowser.noChanges')}</span>} style={{ padding: 40 }} />
      </div>
    );
  }
  return <div>{files.map((f, i) => <FileDiff key={`${f.new_path}-${i}`} file={f} />)}</div>;
}
