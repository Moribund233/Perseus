import { useEffect, useState } from 'react';
import { Empty, Tree } from 'antd';
import type { TreeDataNode } from 'antd';
import { useTranslation } from 'react-i18next';
import { getTree, FileNode } from '../../api/workspaces';

function toTreeData(node: FileNode): TreeDataNode {
  return {
    key: node.path,
    title: node.name,
    isLeaf: !node.is_dir,
    children: node.is_dir ? (node.children ?? []).map(toTreeData) : undefined,
  };
}

export default function ExplorerPanel({ workspaceId, onOpen }: { workspaceId: string; onOpen: (p: string) => void }) {
  const { t } = useTranslation();
  const [data, setData] = useState<TreeDataNode[]>([]);

  useEffect(() => {
    getTree(workspaceId)
      .then((root) => setData((root.children ?? []).map(toTreeData)))
      .catch(console.error);
  }, [workspaceId]);

  if (data.length === 0) return <Empty description={t('desktop.explorer.noFiles')} />;
  return <Tree treeData={data} onSelect={(_, info) => onOpen(String(info.node.key))} defaultExpandAll />;
}
