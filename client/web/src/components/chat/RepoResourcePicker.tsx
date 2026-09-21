import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';
import { Modal, Input, Spin, Empty, Button } from 'antd';
import { FolderOutlined, FileOutlined, FileTextOutlined, DownOutlined, RightOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { repositoriesApi, type RepoFile } from '../../api/repositories';

/**
 * 仓库资源选择器：聊天频道即仓库，用于在消息中引用仓库文件 / 代码片段。
 * - mode='file'：选文件 → 插入指向编辑器该文件的链接。
 * - mode='code'：选文件并选取行区间 → 插入代码片段引用（行内或围栏块）。
 * 目录按需加载（getTree 单层），不依赖共享 store。
 */

const borderColor = '#21262d';
const hoverBg = '#1c2333';
const activeBg = '#1a2332';
const textPrimary = '#e6edf3';
const textSecondary = '#8b949e';
const textTertiary = '#6e7681';
const blueLight = '#58a6ff';
const bluePrimary = '#1f6feb';
const bgPrimary = '#0d1117';
const bgTertiary = '#1c2128';

const MAX_PREVIEW_LINES = 3000;

function sortEntries(entries: RepoFile[]): RepoFile[] {
  return [...entries].sort((a, b) => {
    if (a.type !== b.type) return a.type === 'directory' ? -1 : 1;
    return a.name.localeCompare(b.name);
  });
}

export interface RepoResourcePick {
  path: string;
  startLine?: number;
  endLine?: number;
  snippet?: string;
}

interface Props {
  open: boolean;
  mode: 'file' | 'code';
  repoId: string | null;
  repoPath: string | null;
  defaultBranch?: string | null;
  onCancel: () => void;
  onInsert: (pick: RepoResourcePick) => void;
}

export default function RepoResourcePicker({
  open,
  mode,
  repoId,
  repoPath,
  defaultBranch,
  onCancel,
  onInsert,
}: Props) {
  const { t } = useTranslation();
  const [childrenMap, setChildrenMap] = useState<Record<string, RepoFile[]>>({});
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [loadingDirs, setLoadingDirs] = useState<Set<string>>(new Set());
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [blobLines, setBlobLines] = useState<string[] | null>(null);
  const [blobLoading, setBlobLoading] = useState(false);
  const [rangeStart, setRangeStart] = useState<number | null>(null);
  const [rangeEnd, setRangeEnd] = useState<number | null>(null);
  const [filter, setFilter] = useState('');

  const ref = defaultBranch || undefined;

  const loadDir = useCallback(async (dir: string) => {
    if (!repoId) return;
    setLoadingDirs((prev) => new Set(prev).add(dir));
    try {
      const entries = await repositoriesApi.getTree(repoId, ref, dir || undefined);
      setChildrenMap((prev) => ({ ...prev, [dir]: sortEntries(entries) }));
    } catch {
      setChildrenMap((prev) => ({ ...prev, [dir]: [] }));
    } finally {
      setLoadingDirs((prev) => {
        const next = new Set(prev);
        next.delete(dir);
        return next;
      });
    }
  }, [repoId, ref]);

  // 打开时加载根目录（组件在打开时挂载，状态天然重置）
  useEffect(() => {
    if (!open || !repoId) return;
    let cancelled = false;
    Promise.resolve().then(() => { if (!cancelled) void loadDir(''); });
    return () => { cancelled = true; };
  }, [open, repoId, loadDir]);

  const toggleDir = useCallback((dir: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(dir)) {
        next.delete(dir);
      } else {
        next.add(dir);
        if (!childrenMap[dir]) loadDir(dir);
      }
      return next;
    });
  }, [childrenMap, loadDir]);

  const selectFile = useCallback(async (path: string) => {
    setSelectedPath(path);
    setRangeStart(null);
    setRangeEnd(null);
    if (mode !== 'code' || !repoId) return;
    setBlobLoading(true);
    try {
      const blob = await repositoriesApi.getBlob(repoId, path, ref);
      setBlobLines(blob.content.split('\n'));
    } catch {
      setBlobLines([]);
    } finally {
      setBlobLoading(false);
    }
  }, [mode, repoId, ref]);

  const clickLine = useCallback((line: number, shift: boolean) => {
    setRangeStart((prevStart) => {
      if (shift && prevStart != null) {
        setRangeEnd(line);
        return prevStart;
      }
      setRangeEnd(line);
      return line;
    });
  }, []);

  const selStart = rangeStart != null && rangeEnd != null ? Math.min(rangeStart, rangeEnd) : null;
  const selEnd = rangeStart != null && rangeEnd != null ? Math.max(rangeStart, rangeEnd) : null;

  const canInsert = mode === 'file'
    ? !!selectedPath
    : !!selectedPath && selStart != null;

  const handleOk = useCallback(() => {
    if (!selectedPath) return;
    if (mode === 'file') {
      onInsert({ path: selectedPath });
      return;
    }
    if (selStart == null || selEnd == null || !blobLines) return;
    const snippet = blobLines.slice(selStart - 1, selEnd).join('\n');
    onInsert({ path: selectedPath, startLine: selStart, endLine: selEnd, snippet });
  }, [mode, selectedPath, selStart, selEnd, blobLines, onInsert]);

  function renderTree(dir: string, depth: number): ReactNode {
    const entries = childrenMap[dir];
    if (!entries) {
      return loadingDirs.has(dir) ? (
        <div style={{ padding: '4px 8px', paddingLeft: 8 + depth * 14 }}>
          <Spin size="small" />
        </div>
      ) : null;
    }
    return entries.map((entry) => {
      const isDir = entry.type === 'directory';
      const isOpen = expanded.has(entry.path);
      const isSelected = selectedPath === entry.path;
      return (
        <div key={entry.path}>
          <div
            onClick={() => (isDir ? toggleDir(entry.path) : selectFile(entry.path))}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              padding: '4px 8px',
              paddingLeft: 8 + depth * 14,
              borderRadius: 4,
              cursor: 'pointer',
              fontSize: 13,
              color: isSelected ? textPrimary : textSecondary,
              background: isSelected ? activeBg : 'transparent',
              fontFamily: 'var(--font-mono)',
            }}
            onMouseEnter={(e) => { if (!isSelected) e.currentTarget.style.background = hoverBg; }}
            onMouseLeave={(e) => { if (!isSelected) e.currentTarget.style.background = 'transparent'; }}
          >
            <span style={{ width: 12, display: 'flex', justifyContent: 'center', color: textTertiary, flexShrink: 0 }}>
              {isDir ? (isOpen ? <DownOutlined style={{ fontSize: 9 }} /> : <RightOutlined style={{ fontSize: 9 }} />) : null}
            </span>
            <span style={{ color: isDir ? blueLight : textTertiary, display: 'flex', flexShrink: 0 }}>
              {isDir ? <FolderOutlined /> : <FileOutlined />}
            </span>
            <span style={{ flex: 1, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{entry.name}</span>
          </div>
          {isDir && isOpen && renderTree(entry.path, depth + 1)}
        </div>
      );
    });
  }

  const rootEntries = useMemo(() => childrenMap[''] ?? [], [childrenMap]);
  const visibleRoot = useMemo(
    () => (filter.trim() ? rootEntries.filter((e) => e.name.toLowerCase().includes(filter.trim().toLowerCase())) : rootEntries),
    [rootEntries, filter],
  );

  const title = mode === 'code'
    ? t('app.teamChat.pickCodeTitle', { defaultValue: '选择仓库代码片段' })
    : t('app.teamChat.pickFileTitle', { defaultValue: '选择仓库文件' });

  return (
    <Modal
      title={title}
      open={open}
      onCancel={onCancel}
      onOk={handleOk}
      okText={t('app.teamChat.insert', { defaultValue: '插入' })}
      cancelText={t('app.teamChat.cancel', { defaultValue: '取消' })}
      okButtonProps={{ disabled: !canInsert, style: { background: bluePrimary, borderColor: bluePrimary } }}
      width={mode === 'code' ? 860 : 620}
    >
      {!repoPath ? (
        <Empty description={t('app.teamChat.noRepo', { defaultValue: '当前会话未关联仓库' })} />
      ) : (
        <div style={{ display: 'flex', gap: 12, height: 460 }}>
          <div style={{ width: mode === 'code' ? 300 : '100%', display: 'flex', flexDirection: 'column', minWidth: 0 }}>
            <Input
              size="small"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              placeholder={t('app.teamChat.filterFiles', { defaultValue: '按名称过滤（仅当前已加载层）' })}
              allowClear
              style={{ marginBottom: 8, background: bgTertiary, borderColor, color: textPrimary }}
            />
            <div style={{ flex: 1, overflow: 'auto', border: `1px solid ${borderColor}`, borderRadius: 6, background: bgPrimary, padding: 4 }}>
              {!childrenMap[''] ? (
                <div style={{ padding: 12, textAlign: 'center' }}><Spin size="small" /></div>
              ) : visibleRoot.length === 0 ? (
                <div style={{ padding: 12, color: textTertiary, fontSize: 13, textAlign: 'center' }}>
                  {t('app.repositories.empty.noFiles')}
                </div>
              ) : (
                renderTree('', 0)
              )}
            </div>
          </div>

          {mode === 'code' && (
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
              <div style={{ fontSize: 12, color: textSecondary, marginBottom: 8, fontFamily: 'var(--font-mono)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {selectedPath || t('app.teamChat.pickCodeHint', { defaultValue: '在左侧选择文件，然后点击行选择片段（Shift 点选区间）' })}
              </div>
              <div
                style={{ flex: 1, overflow: 'auto', border: `1px solid ${borderColor}`, borderRadius: 6, background: bgPrimary, padding: '6px 0' }}
              >
                {blobLoading ? (
                  <div style={{ padding: 16, textAlign: 'center' }}><Spin /></div>
                ) : !blobLines ? (
                  <div style={{ padding: 16, color: textTertiary, fontSize: 13, textAlign: 'center' }}>
                    {t('app.teamChat.pickCodeEmpty', { defaultValue: '请选择文件' })}
                  </div>
                ) : blobLines.length === 0 ? (
                  <div style={{ padding: 16, color: textTertiary, fontSize: 13, textAlign: 'center' }}>
                    {t('app.teamChat.pickCodeBinary', { defaultValue: '无法预览该文件' })}
                  </div>
                ) : (
                  blobLines.slice(0, MAX_PREVIEW_LINES).map((line, i) => {
                    const lineNo = i + 1;
                    const inRange = selStart != null && selEnd != null && lineNo >= selStart && lineNo <= selEnd;
                    return (
                      <div
                        key={lineNo}
                        onClick={(e) => clickLine(lineNo, e.shiftKey)}
                        style={{
                          display: 'flex',
                          gap: 10,
                          padding: '0 10px',
                          fontSize: 12.5,
                          lineHeight: 1.6,
                          fontFamily: 'var(--font-mono)',
                          color: inRange ? textPrimary : textSecondary,
                          background: inRange ? 'rgba(31,111,235,0.18)' : 'transparent',
                          cursor: 'pointer',
                          whiteSpace: 'pre',
                        }}
                      >
                        <span style={{ width: 44, textAlign: 'right', color: textTertiary, flexShrink: 0, userSelect: 'none' }}>{lineNo}</span>
                        <span style={{ flex: 1 }}>{line || ' '}</span>
                      </div>
                    );
                  })
                )}
              </div>
              {selStart != null && selEnd != null && (
                <div style={{ marginTop: 8, fontSize: 12, color: textSecondary, display: 'flex', alignItems: 'center', gap: 6 }}>
                  <FileTextOutlined />
                  {t('app.teamChat.pickCodeRange', { defaultValue: '已选 L{{start}}–L{{end}}', start: selStart, end: selEnd })}
                  <Button size="small" type="text" onClick={() => { setRangeStart(null); setRangeEnd(null); }} style={{ color: textTertiary, fontSize: 12 }}>
                    {t('app.teamChat.clear', { defaultValue: '清除' })}
                  </Button>
                </div>
              )}
            </div>
          )}
        </div>
      )}
      <div style={{ marginTop: 8, fontSize: 11, color: textTertiary }}>
        {repoPath}
      </div>
    </Modal>
  );
}
