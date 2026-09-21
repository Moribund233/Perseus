import { useCallback, useEffect, useMemo, useState } from 'react';
import { FolderOutlined, RightOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { FileNode } from '../api/workspaces';
import type { RepoFile } from '../api/repositories';
import { fileBadge } from '../views/workspace/ExplorerPanel';
import { FloatingTreePanel } from './FloatingTreePanel';

/**
 * 远程仓库资源管理器（Explorer）。
 *
 * 与工作区 ExplorerPanel 一致的「右侧浮动面板」展开方式，避免垂直展开过长。
 * 远程 /tree 为单层接口：目录子项按需经 onLoadDir 拉取，store 合并后此处重建树并渲染面板。
 */

interface TreeNode {
  key: string;
  name: string;
  type: 'folder' | 'file';
  children?: TreeNode[];
}

function buildTree(files: RepoFile[]): TreeNode[] {
  const treeMap = new Map<string, TreeNode>();
  const roots: TreeNode[] = [];

  const sorted = [...files].sort((a, b) => {
    const aDepth = a.path.split('/').length;
    const bDepth = b.path.split('/').length;
    if (aDepth !== bDepth) return aDepth - bDepth;
    if (a.type !== b.type) return a.type === 'directory' ? -1 : 1;
    return a.name.localeCompare(b.name);
  });

  for (const file of sorted) {
    const parts = file.path.split('/');
    for (let i = 0; i < parts.length; i++) {
      const accumulatedPath = parts.slice(0, i + 1).join('/');
      const isLast = i === parts.length - 1;
      if (!treeMap.has(accumulatedPath)) {
        const node: TreeNode = {
          key: accumulatedPath,
          name: parts[i],
          type: isLast ? (file.type === 'directory' ? 'folder' : 'file') : 'folder',
        };
        if (!isLast) node.children = [];
        treeMap.set(accumulatedPath, node);
      }
    }
  }

  for (const file of sorted) {
    const parts = file.path.split('/');
    for (let i = 0; i < parts.length; i++) {
      const accumulatedPath = parts.slice(0, i + 1).join('/');
      const node = treeMap.get(accumulatedPath)!;
      if (i === 0) {
        if (!roots.find((r) => r.key === node.key)) roots.push(node);
      } else {
        const parent = treeMap.get(parts.slice(0, i).join('/'));
        if (parent) {
          if (!parent.children) parent.children = [];
          if (!parent.children.find((c) => c.key === node.key)) parent.children.push(node);
        }
      }
    }
  }

  return roots;
}

function toFileNode(node: TreeNode): FileNode {
  return {
    name: node.name,
    path: node.key,
    is_dir: node.type === 'folder',
    children: node.children?.map(toFileNode),
  };
}

interface Props {
  files: RepoFile[];
  selectedKey: string;
  onSelectFile: (path: string) => void;
  onLoadDir: (path: string) => void;
  emptyText?: string;
}

interface FloatPanelPos {
  key: string;
  left: number;
  top: number;
}

export default function RepoExplorer({ files, selectedKey, onSelectFile, onLoadDir, emptyText }: Props) {
  const { t } = useTranslation();
  const [pinnedChain, setPinnedChain] = useState<FloatPanelPos[]>([]);
  const fileTree = useMemo(() => buildTree(files), [files]);

  const nodeMap = useMemo(() => {
    const map = new Map<string, FileNode>();
    const walk = (nodes: TreeNode[]) => {
      for (const n of nodes) {
        map.set(n.key, toFileNode(n));
        if (n.children) walk(n.children);
      }
    };
    walk(fileTree);
    return map;
  }, [fileTree]);

  const handleTreePin = useCallback((key: string, el: HTMLElement) => {
    onLoadDir(key);
    const rect = el.getBoundingClientRect();
    setPinnedChain((prev) => {
      if (prev.length === 1 && prev[0].key === key) return [];
      return [{ key, left: rect.right + 4, top: rect.top }];
    });
  }, [onLoadDir]);

  const handlePanelPin = useCallback((level: number, key: string, el: HTMLElement) => {
    onLoadDir(key);
    const rect = el.getBoundingClientRect();
    setPinnedChain((prev) => {
      const base = prev.slice(0, level + 1);
      const reaching = prev.length === level + 2 && prev[level + 1]?.key === key;
      if (reaching) return base;
      return [...base, { key, left: rect.right + 4, top: rect.top }];
    });
  }, [onLoadDir]);

  useEffect(() => {
    if (pinnedChain.length === 0) return;
    const handle = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      if (!target.closest('.floating-tree-panel') && !target.closest('[data-dir-path]')) {
        setPinnedChain([]);
      }
    };
    document.addEventListener('mousedown', handle);
    return () => document.removeEventListener('mousedown', handle);
  }, [pinnedChain.length]);

  const selectFile = useCallback((path: string) => {
    setPinnedChain([]);
    onSelectFile(path);
  }, [onSelectFile]);

  const activeKeys = useMemo(() => {
    const s = new Set<string>();
    for (let i = 1; i < pinnedChain.length; i++) s.add(pinnedChain[i].key);
    return s;
  }, [pinnedChain]);

  if (fileTree.length === 0) {
    return (
      <div style={{ padding: 16, textAlign: 'center' }}>
        <span style={{ color: '#6e7681', fontSize: 13 }}>{emptyText ?? t('desktop.explorer.noFiles')}</span>
      </div>
    );
  }

  return (
    <div className="tree" style={{ position: 'relative' }}>
      {fileTree.map((node) => {
        const isDir = node.type === 'folder';
        const hasChildren = !!node.children?.length;
        const isSelected = selectedKey === node.key;
        const badge = !isDir ? fileBadge(node.name) : null;
        return (
          <div
            key={node.key}
            className={`frow ${isDir ? `dir-row${hasChildren ? ' has-kids' : ''}` : 'file-row'}${isSelected ? ' sel' : ''}`}
            data-dir-path={isDir ? node.key : undefined}
            style={{ paddingLeft: 10 }}
            onClick={(e) => (isDir ? handleTreePin(node.key, e.currentTarget) : selectFile(node.key))}
          >
            {isDir ? (
              hasChildren ? <RightOutlined className="chev" /> : <span className="chev-placeholder" />
            ) : null}
            {isDir ? (
              <span className="fc folder"><FolderOutlined /></span>
            ) : (
              <span className={badge!.cls}>{badge!.label}</span>
            )}
            <span className="fname">{node.name}</span>
          </div>
        );
      })}

      {pinnedChain.map((pos, i) => {
        const node = nodeMap.get(pos.key);
        if (!node || !node.is_dir || !node.children?.length) return null;
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
              onOpenFile={selectFile}
            />
          </div>
        );
      })}
    </div>
  );
}
