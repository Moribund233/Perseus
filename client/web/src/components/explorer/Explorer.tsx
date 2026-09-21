import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';
import { FolderOutlined, FileOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import { Tooltip } from 'antd';
import { useTranslation } from 'react-i18next';
import { FloatingTreePanel } from '../FloatingTreePanel';
import type { RepoFile } from '../../api/repositories';
import { buildTree, findFileByKey, type TreeNode } from './tree';

/**
 * 共用文件资源管理器（Explorer）。
 *
 * 采用「右侧浮动面板」展开目录，避免垂直展开过长；仓库详情页与编辑器复用同一实现。
 * 目录子项按需加载：点击目录时由 onLoadDir 拉取条目，store 合并后此处重建树并渲染面板。
 */

const hoverBg = '#1c2333';
const activeBg = '#1a2332';
const textSecondary = '#8b949e';
const textPrimary = '#e6edf3';
const textTertiary = '#6e7681';
const blueLight = '#58a6ff';

interface FloatPanelPos {
  key: string;
  left: number;
  top: number;
}

function FileIcon({ type, fileType }: { type: 'folder' | 'file'; fileType?: string }) {
  let color = blueLight;
  if (type === 'file') {
    switch (fileType) {
      case 'ts': color = '#3178c6'; break;
      case 'json': color = '#d29922'; break;
      case 'md': color = blueLight; break;
      case 'css': color = '#563d7c'; break;
      case 'py': color = '#3572A5'; break;
      case 'html': color = '#e34c26'; break;
      default: color = textSecondary;
    }
  }
  return (
    <span style={{ width: 14, height: 14, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, fontSize: 14, color }}>
      {type === 'folder' ? <FolderOutlined /> : <FileOutlined />}
    </span>
  );
}

function TreeNodeView({
  node,
  selectedKey,
  onSelect,
  onDelete,
  onMove,
  onDirPin,
}: {
  node: TreeNode;
  selectedKey: string;
  onSelect: (key: string) => void;
  onDelete?: (node: TreeNode) => void;
  onMove?: (node: TreeNode) => void;
  onDirPin?: (key: string, element: HTMLElement) => void;
}) {
  const isSelected = selectedKey === node.key;
  const { t } = useTranslation();

  return (
    <div>
      <div
        data-dir-path={node.type === 'folder' ? node.key : undefined}
        onClick={(e) => {
          if (node.type === 'folder') {
            // 目录子项按需加载: 即便尚未加载也要触发钉出, 由父级拉取后渲染浮动面板
            if (onDirPin) onDirPin(node.key, e.currentTarget);
            return;
          }
          onSelect(node.key);
        }}
        className="cm-file-tree-row"
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          padding: '4px 12px',
          fontSize: 13,
          cursor: 'pointer',
          color: isSelected ? textPrimary : textSecondary,
          background: isSelected ? activeBg : 'transparent',
          transition: 'all 0.15s',
          fontFamily: "'JetBrains Mono', monospace",
          position: 'relative',
        }}
        onMouseEnter={(e) => {
          if (!isSelected) {
            e.currentTarget.style.background = hoverBg;
            e.currentTarget.style.color = textPrimary;
          }
        }}
        onMouseLeave={(e) => {
          if (!isSelected) {
            e.currentTarget.style.background = 'transparent';
            e.currentTarget.style.color = textSecondary;
          }
        }}
      >
        <FileIcon type={node.type} fileType={node.fileType} />
        <span>{node.title}</span>
        {(onDelete || onMove) && node.type === 'file' && (
          <div style={{ marginLeft: 'auto', display: 'flex', gap: 4, opacity: 0, transition: 'opacity 0.15s' }} className="cm-tree-delete-btn">
            {onMove && (
              <Tooltip title={t('app.codeEditor.moveFile', { defaultValue: '移动/重命名' })}>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onMove(node);
                  }}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: textTertiary,
                    cursor: 'pointer',
                    padding: '0 2px',
                    fontSize: 13,
                    display: 'flex',
                    alignItems: 'center',
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
                    onDelete(node);
                  }}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: textTertiary,
                    cursor: 'pointer',
                    padding: '0 2px',
                    fontSize: 13,
                    display: 'flex',
                    alignItems: 'center',
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
    </div>
  );
}

export interface ExplorerProps {
  /** 扁平文件条目（store.files），按路径构建树 */
  files: RepoFile[];
  selectedKey: string;
  onSelectFile: (key: string) => void;
  /** 目录点击时按需加载其子项（结果经 store 合并后自动重建） */
  onLoadDir?: (key: string) => void;
  onDelete?: (node: TreeNode) => void;
  onMove?: (node: TreeNode) => void;
  emptyText?: ReactNode;
}

export default function Explorer({
  files,
  selectedKey,
  onSelectFile,
  onLoadDir,
  onDelete,
  onMove,
  emptyText,
}: ExplorerProps) {
  const [pinnedChain, setPinnedChain] = useState<FloatPanelPos[]>([]);
  const fileTree = useMemo(() => buildTree(files), [files]);

  // 选择文件时收起浮动面板
  const selectFile = useCallback((key: string) => {
    setPinnedChain([]);
    onSelectFile(key);
  }, [onSelectFile]);

  const handleTreePin = useCallback((key: string, el: HTMLElement) => {
    onLoadDir?.(key);
    const rect = el.getBoundingClientRect();
    setPinnedChain((prev) => {
      if (prev.length === 1 && prev[0].key === key) return [];
      return [{ key, left: rect.right + 4, top: rect.top }];
    });
  }, [onLoadDir]);

  const handlePanelPin = useCallback((level: number, key: string, el: HTMLElement) => {
    onLoadDir?.(key);
    const rect = el.getBoundingClientRect();
    setPinnedChain((prev) => {
      const base = prev.slice(0, level + 1);
      const reaching = prev.length === level + 2 && prev[level + 1]?.key === key;
      if (reaching) return base;
      return [...base, { key, left: rect.right + 4, top: rect.top }];
    });
  }, [onLoadDir]);

  // 点击面板/目录行以外区域时收起浮动面板
  useEffect(() => {
    if (!pinnedChain.length) return;
    const handle = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      if (!target.closest('.cm-floating-panel') && !target.closest('[data-dir-path]')) {
        setPinnedChain([]);
      }
    };
    document.addEventListener('mousedown', handle);
    return () => document.removeEventListener('mousedown', handle);
  }, [pinnedChain.length]);

  return (
    <>
      <div style={{ flex: 1, minHeight: 0, overflow: 'auto', padding: '4px 0', position: 'relative' }}>
        {fileTree.length > 0 ? (
          fileTree.map((node) => (
            <TreeNodeView
              key={node.key}
              node={node}
              selectedKey={selectedKey}
              onSelect={selectFile}
              onDelete={onDelete}
              onMove={onMove}
              onDirPin={handleTreePin}
            />
          ))
        ) : (
          <div style={{ padding: 16, color: textTertiary, fontSize: 13, textAlign: 'center' }}>{emptyText}</div>
        )}
      </div>

      {pinnedChain.length > 0 && (() => {
        const activeKeys = new Set(pinnedChain.slice(1).map((p) => p.key));
        return pinnedChain.map((pos, i) => {
          const node = findFileByKey(fileTree, pos.key);
          if (!node || node.type !== 'folder' || !node.children?.length) return null;
          return (
            <div
              key={pos.key}
              className="floating-tree-anchor"
              style={{ position: 'fixed', top: pos.top, left: pos.left, zIndex: 200 }}
            >
              <FloatingTreePanel
                node={node}
                level={i}
                activeKeys={activeKeys}
                onItemClick={handlePanelPin}
                onSelectFile={selectFile}
                onDelete={onDelete}
                onMove={onMove}
              />
            </div>
          );
        });
      })()}
    </>
  );
}
