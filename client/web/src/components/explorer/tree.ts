import type { RepoFile } from '../../api/repositories';

/**
 * 文件树构建与查找工具（供共用 Explorer 组件使用）。
 */

export interface TreeNode {
  title: string;
  key: string;
  type: 'folder' | 'file';
  fileType?: 'ts' | 'json' | 'md' | 'css' | 'py' | 'html';
  children?: TreeNode[];
}

export function getFileType(filename: string): TreeNode['fileType'] | undefined {
  const ext = filename.split('.').pop()?.toLowerCase();
  if (ext === 'ts' || ext === 'tsx') return 'ts';
  if (ext === 'json') return 'json';
  if (ext === 'md' || ext === 'markdown') return 'md';
  if (ext === 'css' || ext === 'scss' || ext === 'less') return 'css';
  if (ext === 'py') return 'py';
  if (ext === 'html' || ext === 'htm') return 'html';
  return undefined;
}

export function buildTree(files: RepoFile[]): TreeNode[] {
  const root: TreeNode = { title: 'root', key: 'root', type: 'folder', children: [] };
  for (const file of files) {
    const parts = file.path.split('/');
    let current = root;
    for (let i = 0; i < parts.length; i++) {
      const part = parts[i];
      const isLast = i === parts.length - 1;
      const key = parts.slice(0, i + 1).join('/');
      // 目录条目可能先以叶子节点(children 未初始化)出现, 随后才合并到其子路径;
      // 统一在需要挂载子节点前补齐 children, 避免 undefined.push 崩溃。
      if (!current.children) current.children = [];
      let node = current.children.find((c) => c.key === key);
      if (!node) {
        node = {
          title: part,
          key,
          type: isLast ? (file.type === 'directory' ? 'folder' : 'file') : 'folder',
          fileType: isLast ? getFileType(part) : undefined,
          children: isLast ? undefined : [],
        };
        current.children.push(node);
      }
      current = node;
    }
  }
  return root.children || [];
}

export function findFirstFile(nodes: TreeNode[]): TreeNode | null {
  for (const node of nodes) {
    if (node.type === 'file') return node;
    if (node.children) {
      const found = findFirstFile(node.children);
      if (found) return found;
    }
  }
  return null;
}

export function findFileByKey(nodes: TreeNode[], key: string): TreeNode | null {
  for (const node of nodes) {
    if (node.key === key) return node;
    if (node.children) {
      const found = findFileByKey(node.children, key);
      if (found) return found;
    }
  }
  return null;
}
