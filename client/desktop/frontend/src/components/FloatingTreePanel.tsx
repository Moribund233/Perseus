import { useEffect, useRef } from 'react';
import {
  EditOutlined,
  FolderOutlined,
  FolderOpenOutlined,
  RightOutlined,
} from '@ant-design/icons';
import { type FileNode } from '../api/workspaces';
import { fileBadge } from '../views/workspace/ExplorerPanel';

interface Props {
  node: FileNode;
  level: number;
  activeKeys: Set<string>;
  onItemClick: (level: number, key: string, el: HTMLElement) => void;
  onOpenFile: (path: string) => void;
  onRename?: (path: string) => void;
}

export function FloatingTreePanel({
  node,
  level,
  activeKeys,
  onItemClick,
  onOpenFile,
  onRename,
}: Props) {
  const panelRef = useRef<HTMLDivElement>(null);
  const dirs = node.children!.filter((c) => c.is_dir);
  const files = node.children!.filter((c) => !c.is_dir);
  const sorted = [...dirs, ...files];

  useEffect(() => {
    const el = panelRef.current;
    const anchor = el?.closest('.floating-tree-anchor') as HTMLElement | null;
    if (!el || !anchor) return;
    const rect = el.getBoundingClientRect();
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    const curLeft = anchor.style.left ? parseInt(anchor.style.left, 10) : 0;
    const curTop = anchor.style.top ? parseInt(anchor.style.top, 10) : 0;
    if (rect.right > vw - 8) {
      anchor.style.left = `${curLeft - (rect.right - vw + 8)}px`;
    }
    if (rect.bottom > vh - 8) {
      anchor.style.top = `${curTop - (rect.bottom - vh + 8)}px`;
    }
  }, []);

  return (
    <div ref={panelRef} className={`floating-tree-panel level-${level}`}>
      <div className="floating-tree-panel-inner">
        {sorted.map((child) => {
          if (child.is_dir) {
            const hasKids = child.children && child.children.length > 0;
            const active = activeKeys.has(child.path);
            return (
              <div key={child.path} className="floating-item-wrap">
                <div
                  className={`frow dir-row floating-item${active ? ' active' : ''}`}
                  onClick={(e) => onItemClick(level, child.path, e.currentTarget)}
                >
                  {hasKids ? (
                    <RightOutlined className="chev" />
                  ) : (
                    <span className="chev-placeholder" />
                  )}
                  <span className="fc folder">
                    {active ? <FolderOpenOutlined /> : <FolderOutlined />}
                  </span>
                  <span className="fname">{child.name}</span>
                  {onRename && (
                    <button
                      className="icon-btn sm row-rename-btn"
                      title="Move / rename"
                      onClick={(e) => {
                        e.stopPropagation();
                        onRename(child.path);
                      }}
                    >
                      <EditOutlined />
                    </button>
                  )}
                </div>
              </div>
            );
          }
          const b = fileBadge(child.name);
          return (
            <div
              key={child.path}
              className="frow file-row floating-item"
              onClick={() => onOpenFile(child.path)}
            >
              <span className={b.cls}>{b.label}</span>
              <span className="fname">{child.name}</span>
              {onRename && (
                <button
                  className="icon-btn sm row-rename-btn"
                  title="Move / rename"
                  onClick={(e) => {
                    e.stopPropagation();
                    onRename(child.path);
                  }}
                >
                  <EditOutlined />
                </button>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}