import { useCallback, useEffect, useMemo, useState } from 'react';
import { Empty, Input, Modal, Tooltip, message } from 'antd';
import {
  EditOutlined,
  FolderOutlined,
  ReloadOutlined,
  PlusOutlined,
  RightOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { getTree, renameFile, type FileNode } from '../../api/workspaces';
import { logInfo } from '../../stores/logs';
import { FloatingTreePanel } from '../../components/FloatingTreePanel';

export function fileBadge(name: string): { cls: string; label: string } {
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

interface FloatPanelPos {
  key: string;
  left: number;
  top: number;
}

export default function ExplorerPanel({ workspaceId, workspaceName, onOpen }: Props) {
  const { t } = useTranslation();
  const [root, setRoot] = useState<FileNode[]>([]);
  const [refreshing, setRefreshing] = useState(false);

  const [pinnedChain, setPinnedChain] = useState<FloatPanelPos[]>([]);

  const [renameTarget, setRenameTarget] = useState<string | null>(null);
  const [renameFrom, setRenameFrom] = useState('');
  const [renameTo, setRenameTo] = useState('');
  const [renaming, setRenaming] = useState(false);

  const nodeMap = useMemo(() => {
    const map = new Map<string, FileNode>();
    const walk = (nodes: FileNode[]) => {
      for (const n of nodes) {
        map.set(n.path, n);
        if (n.children) walk(n.children);
      }
    };
    walk(root);
    return map;
  }, [root]);

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
    setPinnedChain([]);
    void load(false);
  }, [workspaceId, load]);

  useEffect(() => {
    const onRefresh = () => void load(true);
    window.addEventListener('ide:refresh-tree', onRefresh);
    return () => window.removeEventListener('ide:refresh-tree', onRefresh);
  }, [load]);

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

  const handleTreePin = useCallback((key: string, el: HTMLElement) => {
    const rect = el.getBoundingClientRect();
    setPinnedChain((prev) => {
      if (prev.length === 1 && prev[0].key === key) return [];
      return [{ key, left: rect.right + 4, top: rect.top }];
    });
  }, []);

  const handlePanelClick = useCallback((level: number, key: string, el: HTMLElement) => {
    const rect = el.getBoundingClientRect();
    setPinnedChain((prev) => {
      const base = prev.slice(0, level + 1);
      const reaching = prev.length === level + 2 && prev[level + 1]?.key === key;
      if (reaching) return base;
      return [...base, { key, left: rect.right + 4, top: rect.top }];
    });
  }, []);

  const handleOpenRename = useCallback((path: string) => {
    setPinnedChain([]);
    setRenameFrom(path);
    setRenameTo(path);
    setRenameTarget(path);
  }, []);

  const handleRenameSubmit = useCallback(async () => {
    if (!renameTarget) return;
    const from = renameFrom.trim();
    const to = renameTo.trim();
    if (!from || !to) {
      message.warning(t('desktop.explorer.renameFailed', { defaultValue: '移动/重命名失败' }));
      return;
    }
    setRenaming(true);
    try {
      await renameFile(workspaceId, from, to);
      setRenameTarget(null);
      message.success(t('desktop.explorer.fileRenamed', { defaultValue: '已移动/重命名' }));
      await load(true);
    } catch (e) {
      message.error(`${t('desktop.explorer.renameFailed', { defaultValue: '移动/重命名失败' })}: ${(e as Error).message}`);
    } finally {
      setRenaming(false);
    }
  }, [renameTarget, renameFrom, renameTo, workspaceId, load, t]);

  const displayChain = pinnedChain;
  const activeKeys = useMemo(() => {
    const s = new Set<string>();
    for (let i = 1; i < displayChain.length; i++) s.add(displayChain[i].key);
    return s;
  }, [displayChain]);

  const renderNode = (node: FileNode, depth: number): React.ReactNode => {
    if (node.is_dir) {
      const hasChildren = node.children && node.children.length > 0;
      return (
        <div key={node.path}>
          <div
            className={`frow dir-row${hasChildren ? ' has-kids' : ''}`}
            data-dir-path={node.path}
            style={{ paddingLeft: 10 + depth * 14 }}
            onClick={(e) => hasChildren && handleTreePin(node.path, e.currentTarget)}
          >
            {hasChildren ? (
              <RightOutlined className="chev" />
            ) : (
              <span className="chev-placeholder" />
            )}
            <span className="fc folder">
              <FolderOutlined />
            </span>
            <span className="fname">{node.name}</span>
            <button
              className="icon-btn sm row-rename-btn"
              title={t('desktop.explorer.rename', { defaultValue: '移动/重命名' })}
              onClick={(e) => {
                e.stopPropagation();
                handleOpenRename(node.path);
              }}
            >
              <EditOutlined />
            </button>
          </div>
        </div>
      );
    }
    const b = fileBadge(node.name);
    return (
      <div
        key={node.path}
        className="frow file-row"
        style={{ paddingLeft: 10 + depth * 14 }}
        onClick={() => {
          setPinnedChain([]);
          onOpen(node.path);
        }}
      >
        <span className={b.cls}>{b.label}</span>
        <span className="fname">{node.name}</span>
        <button
          className="icon-btn sm row-rename-btn"
          title={t('desktop.explorer.rename', { defaultValue: '移动/重命名' })}
          onClick={(e) => {
            e.stopPropagation();
            handleOpenRename(node.path);
          }}
        >
          <EditOutlined />
        </button>
      </div>
    );
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

      <Modal
        open={renameTarget !== null}
        title={t('desktop.explorer.renameTitle', { defaultValue: '移动/重命名文件' })}
        okText={t('desktop.explorer.rename', { defaultValue: '移动/重命名' })}
        cancelText={t('desktop.common.cancel', { defaultValue: '取消' })}
        confirmLoading={renaming}
        onOk={() => void handleRenameSubmit()}
        onCancel={() => { if (!renaming) setRenameTarget(null); }}
        destroyOnClose
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 4 }}>
          <Input
            value={renameFrom}
            placeholder={t('desktop.explorer.renameFromPlaceholder', { defaultValue: '当前路径' })}
            onChange={(e) => setRenameFrom(e.target.value)}
          />
          <Input
            value={renameTo}
            placeholder={t('desktop.explorer.renameToPlaceholder', { defaultValue: '目标路径' })}
            onChange={(e) => setRenameTo(e.target.value)}
            onPressEnter={() => void handleRenameSubmit()}
          />
        </div>
      </Modal>

      {displayChain.map((pos, i) => {
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
              onItemClick={handlePanelClick}
              onOpenFile={onOpen}
              onRename={handleOpenRename}
            />
          </div>
        );
      })}
    </div>
  );
}