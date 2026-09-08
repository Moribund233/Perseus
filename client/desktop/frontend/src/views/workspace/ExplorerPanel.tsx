import { useCallback, useEffect, useState } from 'react';
import { Empty, Tooltip, message } from 'antd';
import {
  FolderOutlined,
  FolderOpenOutlined,
  ReloadOutlined,
  PlusOutlined,
  RightOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { getTree, type FileNode } from '../../api/workspaces';
import { logInfo } from '../../stores/logs';

function fileBadge(name: string): { cls: string; label: string } {
  const ext = name.split('.').pop()?.toLowerCase() ?? '';
  switch (ext) {
    case 'py': return { cls: 'fc py', label: 'PY' };
    case 'toml': return { cls: 'fc toml', label: 'TOML' };
    case 'md': return { cls: 'fc md', label: 'MD' };
    case 'ts': case 'tsx': return { cls: 'fc ts', label: 'TS' };
    case 'js': case 'jsx': return { cls: 'fc js', label: 'JS' };
    case 'go': return { cls: 'fc go', label: 'GO' };
    case 'json': return { cls: 'fc json', label: 'JSON' };
    case 'css': return { cls: 'fc css', label: 'CSS' };
    case 'html': return { cls: 'fc html', label: 'HTML' };
    case 'txt': case 'log': return { cls: 'fc txt', label: 'TXT' };
    default: return { cls: 'fc def', label: ext ? ext.slice(0, 4).toUpperCase() : 'FILE' };
  }
}

interface Props {
  workspaceId: string;
  workspaceName: string;
  onOpen: (path: string) => void;
}

export default function ExplorerPanel({ workspaceId, workspaceName, onOpen }: Props) {
  const { t } = useTranslation();
  const [root, setRoot] = useState<FileNode[]>([]);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(
    async (notify = true) => {
      try {
        const r = await getTree(workspaceId);
        setRoot(r.children ?? []);
        if (notify) logInfo(t('desktop.log.explorerLoaded', { defaultValue: '文件树已加载' }));
      } catch (e) {
        message.error(`${t('desktop.explorer.loadFail', { defaultValue: '加载文件树失败' })}: ${(e as Error).message}`);
      }
    },
    [workspaceId, t],
  );

  useEffect(() => {
    setRoot([]);
    setExpanded(new Set());
    void load(false);
  }, [workspaceId, load]);

  useEffect(() => {
    const onRefresh = () => void load(true);
    window.addEventListener('ide:refresh-tree', onRefresh);
    return () => window.removeEventListener('ide:refresh-tree', onRefresh);
  }, [load]);

  const splitChildren = (nodes: FileNode[]) => ({
    dirs: nodes.filter((n) => n.is_dir),
    files: nodes.filter((n) => !n.is_dir),
  });

  const renderNode = (node: FileNode, depth: number): React.ReactNode => {
    if (node.is_dir) {
      const open = expanded.has(node.path);
      return (
        <div key={node.path}>
          <div
            className={`frow${open ? ' open' : ''}`}
            style={{ paddingLeft: 10 + depth * 14 }}
            onClick={() =>
              setExpanded((prev) => {
                const next = new Set(prev);
                if (next.has(node.path)) next.delete(node.path);
                else next.add(node.path);
                return next;
              })
            }
          >
            <RightOutlined className={`chev${open ? ' open' : ''}`} />
            <span className="fc folder">
              {open ? <FolderOpenOutlined /> : <FolderOutlined />}
            </span>
            <span className="fname">{node.name}</span>
          </div>
          {open && node.children && (
            <div className="kids">{renderList(node.children, depth + 1)}</div>
          )}
        </div>
      );
    }
    const b = fileBadge(node.name);
    return (
      <div key={node.path} className="frow" style={{ paddingLeft: 10 + depth * 14 }} onClick={() => onOpen(node.path)}>
        <RightOutlined className="chev leaf" />
        <span className={b.cls}>{b.label}</span>
        <span className="fname">{node.name}</span>
      </div>
    );
  };

  const renderList = (nodes: FileNode[], depth: number): React.ReactNode => {
    const { dirs, files } = splitChildren(nodes);
    return [...dirs, ...files].map((n) => renderNode(n, depth));
  };

  return (
    <div className="sb-pane on" data-pane="explorer">
      <div className="sb-head">
        {t('desktop.explorer.title', { name: workspaceName.toUpperCase(), defaultValue: '资源管理器 · {{name}}' })}
        <span className="right">
          <Tooltip title={t('desktop.explorer.newFile', { defaultValue: '新建文件' })}>
            <button
              className="icon-btn sm"
              onClick={() =>
                message.info(t('desktop.portal.phase2', { defaultValue: 'Phase 2 提供' }))
              }
            >
              <PlusOutlined />
            </button>
          </Tooltip>
          <Tooltip title={t('desktop.explorer.refresh', { defaultValue: '刷新' })}>
            <button
              className={`icon-btn sm${refreshing ? ' spin' : ''}`}
              onClick={() => {
                setRefreshing(true);
                void load(true).finally(() => setRefreshing(false));
              }}
            >
              <ReloadOutlined />
            </button>
          </Tooltip>
        </span>
      </div>
      {root.length === 0 ? (
        <Empty description={t('desktop.explorer.noFiles')} />
      ) : (
        <div className="tree">
          {root.map((n) => renderNode(n, 0))}
        </div>
      )}
    </div>
  );
}