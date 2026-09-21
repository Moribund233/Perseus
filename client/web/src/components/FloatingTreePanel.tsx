import { useEffect, useRef } from 'react';
import { FolderOutlined, FileOutlined, DeleteOutlined, EditOutlined } from '@ant-design/icons';
import { Tooltip } from 'antd';
import { useTranslation } from 'react-i18next';

interface TreeNode {
  title: string;
  key: string;
  type: 'folder' | 'file';
  fileType?: 'ts' | 'json' | 'md' | 'css' | 'py' | 'html';
  children?: TreeNode[];
}

const hoverBg = '#1c2333';
const textSecondary = '#8b949e';
const textPrimary = '#e6edf3';
const textTertiary = '#6e7681';
const blueLight = '#58a6ff';

function getFileIconColor(fileType?: string): string {
  switch (fileType) {
    case 'ts': return '#3178c6';
    case 'json': return '#d29922';
    case 'md': return blueLight;
    case 'css': return '#563d7c';
    case 'py': return '#3572A5';
    case 'html': return '#e34c26';
    default: return textSecondary;
  }
}

interface Props {
  node: TreeNode;
  level: number;
  activeKeys: Set<string>;
  onItemClick: (level: number, key: string, el: HTMLElement) => void;
  onSelectFile: (key: string) => void;
  onDelete?: (node: TreeNode) => void;
  onMove?: (node: TreeNode) => void;
}

const itemStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: 6,
  padding: '4px 8px',
  fontSize: 13,
  cursor: 'pointer',
  color: textSecondary,
  fontFamily: "'JetBrains Mono', monospace",
  transition: 'all 0.15s',
  borderRadius: 4,
  margin: '1px 2px',
  position: 'relative' as const,
};

export function FloatingTreePanel({
  node,
  level,
  activeKeys,
  onItemClick,
  onSelectFile,
  onDelete,
  onMove,
}: Props) {
  const { t } = useTranslation();
  const panelRef = useRef<HTMLDivElement>(null);

  const dirs = node.children!.filter((c) => c.type === 'folder');
  const files = node.children!.filter((c) => c.type === 'file');
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
    <div ref={panelRef} className={`cm-floating-panel level-${level}`}>
      <div className="cm-floating-panel-inner">
        {sorted.map((child) => {
          if (child.type === 'folder') {
            const active = activeKeys.has(child.key);
            return (
              <div key={child.key} className="cm-floating-item-wrap">
                <div
                  className={`cm-floating-item${active ? ' active' : ''}`}
                  onClick={(e) => onItemClick(level, child.key, e.currentTarget)}
                  style={{
                    ...itemStyle,
                    background: active ? hoverBg : 'transparent',
                    color: active ? textPrimary : textSecondary,
                  }}
                >
                  <span style={{ width: 14, height: 14, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, fontSize: 14, color: blueLight }}>
                    <FolderOutlined />
                  </span>
                  <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{child.title}</span>
                </div>
              </div>
            );
          }
          const iconColor = getFileIconColor(child.fileType);
          return (
            <div
              key={child.key}
              className="cm-floating-item"
              onClick={() => onSelectFile(child.key)}
              style={{ ...itemStyle, paddingRight: 34 }}
            >
              <span style={{ width: 14, height: 14, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, fontSize: 14, color: iconColor }}>
                <FileOutlined />
              </span>
              <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{child.title}</span>
              {(onMove || onDelete) && (
                <div className="cm-tree-delete-btn" style={{ position: 'absolute', right: 6, display: 'flex', gap: 4, opacity: 0, transition: 'opacity 0.15s' }}>
                  {onMove && (
                    <Tooltip title={t('app.codeEditor.moveFile', { defaultValue: '移动/重命名' })}>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onMove(child);
                        }}
                        style={{
                          background: 'none',
                          border: 'none',
                          color: textTertiary,
                          cursor: 'pointer',
                          padding: '0 2px',
                          fontSize: 12,
                          display: 'flex',
                          alignItems: 'center',
                          opacity: 1,
                          fontFamily: "'JetBrains Mono', monospace",
                        }}
                        onMouseEnter={(e) => { e.currentTarget.style.color = blueLight; }}
                        onMouseLeave={(e) => { e.currentTarget.style.color = textTertiary; }}
                      >
                        <EditOutlined />
                      </button>
                    </Tooltip>
                  )}
                  {onDelete && (
                    <Tooltip title={t('app.codeEditor.deleteFile', { defaultValue: '删除文件' })}>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onDelete(child);
                        }}
                        style={{
                          background: 'none',
                          border: 'none',
                          color: textTertiary,
                          cursor: 'pointer',
                          padding: '0 2px',
                          fontSize: 12,
                          display: 'flex',
                          alignItems: 'center',
                          opacity: 1,
                          fontFamily: "'JetBrains Mono', monospace",
                        }}
                        onMouseEnter={(e) => { e.currentTarget.style.color = '#f85149'; }}
                        onMouseLeave={(e) => { e.currentTarget.style.color = textTertiary; }}
                      >
                        <DeleteOutlined />
                      </button>
                    </Tooltip>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}