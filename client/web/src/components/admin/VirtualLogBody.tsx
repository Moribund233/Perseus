import { useEffect, useMemo, useRef } from 'react';
import { Skeleton } from 'antd';
import { useVirtualizer } from '@tanstack/react-virtual';
import { splitLine, type LogRow } from './logLine';

interface VirtualLogBodyProps {
  /** 终端行（日志行或分片分隔行） */
  rows: LogRow[];
  /** 是否自动滚动到底部 */
  follow?: boolean;
  /** 首次加载骨架屏 */
  loading?: boolean;
  emptyText: string;
}

/**
 * 虚拟滚动日志正文：仅渲染视口内行（动态测量行高，兼容折行）。
 * 文件日志 tab 与实时日志流 tab 共用；分隔行不参与行号计数。
 */
export default function VirtualLogBody({
  rows,
  follow = false,
  loading = false,
  emptyText,
}: VirtualLogBodyProps) {
  const termRef = useRef<HTMLDivElement | null>(null);

  // eslint-disable-next-line react-hooks/incompatible-library -- TanStack Virtual 返回非纯函数，React Compiler 无法安全记忆化
  const virtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => termRef.current,
    estimateSize: () => 19,
    overscan: 16,
  });
  const totalSize = virtualizer.getTotalSize();

  // 日志行的序号（分隔行为 -1，不计数）
  const ordinals = useMemo(() => {
    let n = 0;
    return rows.map((r) => (r.kind === 'segment' ? -1 : ++n));
  }, [rows]);

  useEffect(() => {
    if (!follow || rows.length === 0) return;
    virtualizer.scrollToIndex(rows.length - 1, { align: 'end' });
  }, [follow, rows.length, totalSize, virtualizer]);

  if (loading && rows.length === 0) {
    return (
      <div className="ac-log-body" ref={termRef}>
        <div className="ac-log-skeleton">
          <Skeleton active title={false} paragraph={{ rows: 8 }} />
        </div>
      </div>
    );
  }

  return (
    <div className="ac-log-body" ref={termRef}>
      {rows.length === 0 ? (
        <div className="ac-empty">{emptyText}</div>
      ) : (
        <div className="ac-log-vlist" style={{ height: totalSize }}>
          {virtualizer.getVirtualItems().map((vi) => {
            const row = rows[vi.index];
            const baseStyle = { transform: `translateY(${vi.start}px)` };
            if (row.kind === 'segment') {
              return (
                <div
                  className="ac-log-seg"
                  key={vi.key}
                  data-index={vi.index}
                  ref={virtualizer.measureElement}
                  style={baseStyle}
                >
                  <span className="ac-log-seg-rule" />
                  <span className="ac-log-seg-label">{row.text}</span>
                  <span className="ac-log-seg-rule" />
                </div>
              );
            }
            const { head, level, tail } = splitLine(row.text);
            return (
              <div
                className={`ac-log-line${level ? ` lv-${level.toLowerCase()}` : ''}`}
                key={vi.key}
                data-index={vi.index}
                ref={virtualizer.measureElement}
                style={baseStyle}
              >
                <span className="ac-log-no">{ordinals[vi.index]}</span>
                <span className="ac-log-text">
                  {head}
                  {level && <span className="ac-log-lvl">{level}</span>}
                  {tail}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
