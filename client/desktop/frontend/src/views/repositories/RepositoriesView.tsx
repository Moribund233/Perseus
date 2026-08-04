import { useState, useEffect, useMemo, useCallback, type ReactNode } from 'react';
import { Layout, Button, Avatar, Tabs, Tag, Spin, Empty, message, App as AntApp } from 'antd';
import type { TabsProps } from 'antd';
import {
  FolderOutlined,
  FileOutlined,
  FileTextOutlined,
  StarOutlined,
  ForkOutlined,
  ReadOutlined,
  CloudDownloadOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import {
  useRepositoriesStore,
} from '../../stores/repositories';
import { useServersStore } from '../../stores/servers';
import { repositoriesApi, type RepoFile, type RepoBlob, type Repository } from '../../api/repositories';
import { createWorkspace, listWorkspaces } from '../../api/workspaces';
import { useWorkspaceStore } from '../../stores/workspace';

const { Sider, Content } = Layout;

const borderColor = '#21262d';
const hoverBg = '#1c2333';
const activeBg = '#1a2332';
const textSecondary = '#8b949e';
const textPrimary = '#e6edf3';
const textTertiary = '#6e7681';
const blueLight = '#58a6ff';
const bluePrimary = '#1f6feb';
const bgSecondary = '#161b22';
const bgTertiary = '#1c2128';

interface TreeNode {
  key: string;
  name: string;
  type: 'folder' | 'file';
  iconColor?: string;
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

function getIconColor(name: string): string | undefined {
  const ext = name.split('.').pop();
  switch (ext) {
    case 'ts': case 'tsx': return '#3178c6';
    case 'js': case 'jsx': return '#f1e05a';
    case 'json': case 'yaml': case 'yml': return '#f1e05a';
    case 'md': return textSecondary;
    case 'rs': return '#dea584';
    case 'go': return '#00add8';
    case 'py': return '#3572a5';
    case 'css': case 'scss': case 'less': return '#563d7c';
    case 'html': return '#e34c26';
    default: return undefined;
  }
}

function TreeIcon({ type, iconColor }: { type: 'folder' | 'file'; iconColor?: string }) {
  const color = type === 'folder' ? blueLight : iconColor || textSecondary;
  return (
    <span style={{ width: 16, height: 16, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, fontSize: 16, color }}>
      {type === 'folder' ? <FolderOutlined /> : <FileOutlined />}
    </span>
  );
}

function TreeNodeView({
  node, depth, selectedKey, onSelect, branchName, repoId, branchRef,
}: {
  node: TreeNode; depth: number; selectedKey: string; onSelect: (key: string) => void;
  branchName?: string; repoId?: string; branchRef?: string;
}) {
  const isSelected = selectedKey === node.key;
  const hasChildren = node.children && node.children.length > 0;
  const [expanded, setExpanded] = useState(hasChildren);
  const [loading, setLoading] = useState(false);
  const fetchTree = useRepositoriesStore((s) => s.fetchTree);

  const handleClick = async () => {
    onSelect(node.key);
    if (node.type !== 'folder') return;
    if (!hasChildren && !loading && repoId) {
      setLoading(true);
      await fetchTree(repoId, branchRef, node.key);
      setLoading(false);
    }
    setExpanded((v) => !v);
  };

  return (
    <div>
      <div
        onClick={handleClick}
        style={{
          display: 'flex', alignItems: 'center', gap: 8, padding: '6px 10px', borderRadius: 6,
          cursor: 'pointer', fontSize: 13, color: isSelected ? blueLight : textSecondary,
          background: isSelected ? activeBg : 'transparent', marginLeft: depth * 16, transition: 'all 0.15s',
        }}
        onMouseEnter={(e) => { if (!isSelected) { e.currentTarget.style.background = hoverBg; e.currentTarget.style.color = textPrimary; } }}
        onMouseLeave={(e) => { if (!isSelected) { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = textSecondary; } }}
      >
        {(loading && node.type === 'folder') ? (
          <Spin size="small" style={{ width: 16, height: 16, flexShrink: 0 }} />
        ) : (
          <TreeIcon type={node.type} iconColor={node.iconColor} />
        )}
        <span style={{ flex: 1, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{node.name}</span>
        {depth === 0 && branchName && (
          <span style={{ fontSize: 10, color: textTertiary, background: '#0d1117', padding: '1px 6px', borderRadius: 8 }}>{branchName}</span>
        )}
      </div>
      {expanded && hasChildren && (
        <div>
          {node.children!.map((child) => (
            <TreeNodeView key={child.key} node={child} depth={depth + 1} selectedKey={selectedKey} onSelect={onSelect} branchName={branchName} repoId={repoId} branchRef={branchRef} />
          ))}
        </div>
      )}
    </div>
  );
}

const filters = ['all', 'source', 'config', 'tests'] as const;

export default function RepositoriesView() {
  const { t } = useTranslation();
  const { message } = AntApp.useApp();
  const server = useServersStore((s) => s.servers.find((x) => x.id === s.currentServerId));
  const currentRepo = useRepositoriesStore((s) => s.currentRepo);
  const storeFiles = useRepositoriesStore((s) => s.files);
  const branches = useRepositoriesStore((s) => s.branches);
  const commits = useRepositoriesStore((s) => s.commits);
  const readme = useRepositoriesStore((s) => s.readme);
  const isLoading = useRepositoriesStore((s) => s.isLoading);
  const error = useRepositoriesStore((s) => s.error);
  const clearCurrent = useRepositoriesStore((s) => s.clearCurrent);
  const fetchRepositoryByPath = useRepositoriesStore((s) => s.fetchRepositoryByPath);
  const fetchTree = useRepositoriesStore((s) => s.fetchTree);
  const fetchReadme = useRepositoriesStore((s) => s.fetchReadme);
  const fetchBranches = useRepositoriesStore((s) => s.fetchBranches);
  const fetchCommits = useRepositoriesStore((s) => s.fetchCommits);
  const starRepository = useRepositoriesStore((s) => s.starRepository);
  const unstarRepository = useRepositoriesStore((s) => s.unstarRepository);
  const repositories = useRepositoriesStore((s) => s.repositories);

  const [activeTab, setActiveTab] = useState('code');
  const [selectedTreeKey, setSelectedTreeKey] = useState('');
  const [selectedFileContent, setSelectedFileContent] = useState<RepoBlob | null>(null);
  const [fileLoading, setFileLoading] = useState(false);
  const [activeFilter, setActiveFilter] = useState<(typeof filters)[number]>('all');
  const [isStarred, setIsStarred] = useState(false);
  const [cloning, setCloning] = useState(false);
  const fetchRepositories = useRepositoriesStore((s) => s.fetchRepositories);

  // 列表视图：加载仓库列表。
  useEffect(() => {
    if (!currentRepo) {
      fetchRepositories();
    }
  }, [currentRepo, fetchRepositories]);

  const openRepo = async (repo: Repository) => {
    clearCurrent();
    const parts = repo.path.split('/');
    const owner = parts[0];
    await fetchRepositoryByPath(owner, repo.name);
  };

  const goBack = () => clearCurrent();

  const onClone = async () => {
    if (!currentRepo || !server) return;
    setCloning(true);
    try {
      const url = `${server.base_url}/${currentRepo.path}.git`;
      const ws = await createWorkspace({ name: currentRepo.name, path: '', url, clone: true });
      const setWorkspaces = useWorkspaceStore.getState().setWorkspaces;
      setWorkspaces(await listWorkspaces());
      message.success(`${t('desktop.serverShell.cloneOk')} ${ws.path}`);
      useWorkspaceStore.getState().setCurrent(ws);
    } catch (e) {
      message.error(`${t('desktop.serverShell.cloneFail')}: ${(e as Error).message}`);
    } finally {
      setCloning(false);
    }
  };

  // 详情：加载树/读me/分支/提交/star 状态。
  useEffect(() => {
    if (!currentRepo) return;
    if (!currentRepo.status?.initialized) return;
    const ref = currentRepo.default_branch;
    const sid = server?.id;
    if (!sid) return;
    fetchTree(currentRepo.id, ref);
    fetchReadme(currentRepo.id, ref);
    fetchBranches(currentRepo.id);
    fetchCommits(currentRepo.id, { branch: ref });
    repositoriesApi.getStarStatus(sid, currentRepo.id).then((res) => setIsStarred(res.starred)).catch(() => {});
  }, [currentRepo, server?.id, fetchTree, fetchReadme, fetchBranches, fetchCommits]);

  // 选择文件 → 读 blob。
  useEffect(() => {
    let cancelled = false;
    const loadFile = async () => {
      if (!selectedTreeKey || !currentRepo || !server) return;
      const file = storeFiles.find((f) => f.path === selectedTreeKey && f.type === 'file');
      if (!file) { if (!cancelled) setSelectedFileContent(null); return; }
      if (!cancelled) setFileLoading(true);
      try {
        const blob = await repositoriesApi.getBlob(server.id, currentRepo.id, selectedTreeKey, currentRepo.default_branch);
        if (!cancelled) setSelectedFileContent(blob);
      } catch {
        if (!cancelled) setSelectedFileContent(null);
      } finally {
        if (!cancelled) setFileLoading(false);
      }
    };
    loadFile();
    return () => { cancelled = true; };
  }, [selectedTreeKey, currentRepo, storeFiles, server?.id]);

  const repoTree = useMemo(() => buildTree(storeFiles), [storeFiles]);
  const rootFiles = useMemo(() => storeFiles.filter((f) => !f.path.includes('/')), [storeFiles]);
  const displayFiles = useMemo(() => {
    if (activeFilter === 'all') return rootFiles;
    return rootFiles.filter((f) => {
      if (activeFilter === 'source') return /\.(ts|tsx|js|jsx|rs|go|py)$/i.test(f.name);
      if (activeFilter === 'config') return /\.(json|ya?ml|toml)$/i.test(f.name) || f.name === '.gitignore';
      if (activeFilter === 'tests') return f.path.includes('test') || f.path.includes('__tests__') || /\.(test|spec)\./i.test(f.name);
      return true;
    });
  }, [rootFiles, activeFilter]);

  const latestCommit = commits.length > 0 ? commits[0] : null;
  const isRepoEmpty = !!currentRepo && !currentRepo.status?.initialized;

  const handleStarToggle = useCallback(async () => {
    if (!currentRepo) return;
    try {
      if (isStarred) { await unstarRepository(currentRepo.id); setIsStarred(false); }
      else { await starRepository(currentRepo.id); setIsStarred(true); }
    } catch {
      message.error(t('desktop.serverShell.starFail'));
    }
  }, [currentRepo, isStarred, starRepository, unstarRepository, message, t]);

  // ---- 列表视图 ----
  if (!currentRepo) {
    return (
      <Content style={{ padding: '24px 32px', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16, flexShrink: 0 }}>
          <h2 style={{ fontSize: 20, fontWeight: 700, margin: 0, color: textPrimary }}>{t('app.repositories.title')}</h2>
        </div>
        {isLoading && <Spin style={{ marginTop: 40 }} />}
        {error && <ErrorBanner>{error}</ErrorBanner>}
        <div style={{ flex: 1, overflowY: 'auto', minHeight: 0 }}>
          {repositories.length === 0 && !isLoading && !error && (
            <Empty style={{ marginTop: 48 }} description={t('app.repositories.noRepos')} />
          )}
          {repositories.map((r) => (
            <div
              key={r.id}
              onClick={() => openRepo(r)}
              style={{ padding: '12px 16px', border: `1px solid ${borderColor}`, borderRadius: 8, marginBottom: 8, cursor: 'pointer', background: bgSecondary, display: 'flex', alignItems: 'center', gap: 12, transition: 'background 0.15s' }}
              onMouseEnter={(e) => { e.currentTarget.style.background = hoverBg; }}
              onMouseLeave={(e) => { e.currentTarget.style.background = bgSecondary; }}
            >
              <FolderOutlined style={{ fontSize: 20, color: blueLight, flexShrink: 0 }} />
              <span style={{ flex: 1, color: textPrimary, fontWeight: 600, fontSize: 14, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{r.name}</span>
              <Tag color={r.is_public ? 'default' : 'blue'} style={{ marginInlineEnd: 0 }}>
                {r.is_public ? t('app.repositories.visibility.public') : t('app.repositories.visibility.private')}
              </Tag>
              <span style={{ color: textSecondary, fontSize: 12, display: 'flex', alignItems: 'center', gap: 4, flexShrink: 0 }}>
                <StarOutlined style={{ fontSize: 12 }} /> {r.star_count}
              </span>
              <span style={{ color: textSecondary, fontSize: 12, display: 'flex', alignItems: 'center', gap: 4, flexShrink: 0 }}>
                <ForkOutlined style={{ fontSize: 12 }} /> {r.fork_count}
              </span>
            </div>
          ))}
        </div>
      </Content>
    );
  }

  const tabItems: TabsProps['items'] = [
    { key: 'code', label: <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}><FileTextOutlined style={{ fontSize: 14 }} />{t('app.repositories.tabs.code')}</span> },
    { key: 'pullRequests', label: <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}><GitPullRequestIco />{t('app.repositories.tabs.pullRequests')}</span> },
    { key: 'issues', label: <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}><IssueIco />{t('app.repositories.tabs.issues')}</span> },
    { key: 'settings', label: <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}><GearIco />{t('app.repositories.tabs.settings')}</span> },
  ];

  return (
    <Layout style={{ height: '100%', background: 'transparent' }}>
      <Sider
        width={280}
        style={{ background: bgSecondary, borderRight: `1px solid ${borderColor}`, display: 'flex', flexDirection: 'column', flexShrink: 0 }}
      >
        <div style={{ padding: 16, borderBottom: `1px solid ${borderColor}` }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
            <h3 style={{ fontSize: 13, fontWeight: 600, margin: 0, color: textPrimary }}>{t('app.repositories.explorer')}</h3>
            <Button size="small" type="text" onClick={goBack}>{t('desktop.serverShell.back')}</Button>
          </div>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {filters.map((f) => {
              const isActive = activeFilter === f;
              return (
                <span key={f} onClick={() => setActiveFilter(f)}
                  style={{ padding: '3px 10px', borderRadius: 12, fontSize: 11, cursor: 'pointer', transition: 'all 0.2s',
                    background: isActive ? 'rgba(31,111,235,0.15)' : '#0d1117', border: `1px solid ${isActive ? bluePrimary : borderColor}`, color: isActive ? blueLight : textSecondary }}
                  onMouseEnter={(e) => { if (!isActive) { e.currentTarget.style.background = 'rgba(31,111,235,0.15)'; e.currentTarget.style.borderColor = bluePrimary; e.currentTarget.style.color = blueLight; } }}
                  onMouseLeave={(e) => { if (!isActive) { e.currentTarget.style.background = '#0d1117'; e.currentTarget.style.borderColor = borderColor; e.currentTarget.style.color = textSecondary; } }}>
                  {t(`app.repositories.filters.${f}`)}
                </span>
              );
            })}
          </div>
        </div>
        <div style={{ flex: 1, overflowY: 'auto', padding: 8 }}>
          {repoTree.length > 0 ? (
            repoTree.map((node) => (
              <TreeNodeView key={node.key} node={node} depth={0} selectedKey={selectedTreeKey}
                onSelect={setSelectedTreeKey} branchName={currentRepo.default_branch} repoId={currentRepo.id} branchRef={currentRepo.default_branch} />
            ))
          ) : (
            <div style={{ padding: 16, color: textTertiary, fontSize: 13, textAlign: 'center' }}>{t('app.repositories.empty.noFiles')}</div>
          )}
        </div>
      </Sider>

      <Content style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column', padding: '24px 24px 0' }}>
        <div style={{ flexShrink: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 20, flexWrap: 'wrap' }}>
            <span style={{ fontSize: 24, color: blueLight, display: 'flex', alignItems: 'center' }}><FolderOutlined /></span>
            <h2 style={{ fontSize: 20, fontWeight: 700, margin: 0, color: textPrimary }}>{currentRepo.name}</h2>
            <Tag color={currentRepo.is_public ? 'default' : 'blue'}>
              {currentRepo.is_public ? t('app.repositories.visibility.public') : t('app.repositories.visibility.private')}
            </Tag>
            <div style={{ marginLeft: 'auto', display: 'flex', gap: 8 }}>
              <Button icon={<StarOutlined style={{ color: isStarred ? '#e3b341' : undefined }} />} onClick={handleStarToggle}>
                {isStarred ? t('app.repositories.actions.unstar') : t('app.repositories.actions.star')} {currentRepo.star_count}
              </Button>
              <Button icon={<CloudDownloadOutlined />} loading={cloning} onClick={onClone}>
                {t('desktop.serverShell.clone')}
              </Button>
            </div>
          </div>
          <Tabs activeKey={activeTab} onChange={setActiveTab} items={tabItems}
            style={{ marginBottom: 0 }} />
          {activeTab !== 'code' && (
            <div style={{ padding: '24px 0', color: textSecondary, textAlign: 'center' }}>
              {t('desktop.serverShell.comingIn2b')}
            </div>
          )}
        </div>

        {isRepoEmpty ? (
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: textTertiary }}>
            <p>{t('app.repositories.empty.title')} — {t('app.repositories.empty.description')}</p>
          </div>
        ) : (
          <div style={{ flex: 1, overflowY: 'auto', paddingBottom: 24 }}>
            <div style={{ border: `1px solid ${borderColor}`, borderRadius: 12, overflow: 'hidden', marginBottom: 20, background: bgSecondary }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '12px 16px', background: bgTertiary, borderBottom: `1px solid ${borderColor}`, fontSize: 13 }}>
                <Avatar size={24} style={{ background: 'linear-gradient(135deg, #58a6ff, #1f6feb)', fontSize: 10, fontWeight: 600, flexShrink: 0 }}>
                  {latestCommit ? latestCommit.author_name.charAt(0).toUpperCase() : '?'}
                </Avatar>
                <span style={{ flex: 1, color: textSecondary, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {latestCommit ? (<><strong style={{ color: textPrimary, marginRight: 4 }}>{latestCommit.author_name}</strong>{latestCommit.message}</>) : t('app.repositories.empty.noCommits')}
                </span>
                <span style={{ color: textTertiary, fontSize: 12, whiteSpace: 'nowrap' }}>{latestCommit ? latestCommit.hash.slice(0, 7) : ''}</span>
              </div>
              {displayFiles.map((file, index) => (
                <div key={file.path}
                  onClick={() => { if (file.type === 'directory') { /* 目录：折叠树由左栏负责 */ return; } setSelectedTreeKey(file.path); }}
                  style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '8px 16px', borderBottom: index === displayFiles.length - 1 ? 'none' : `1px solid ${borderColor}`, fontSize: 13, cursor: 'pointer', transition: 'background 0.15s' }}
                  onMouseEnter={(e) => { e.currentTarget.style.background = hoverBg; }}
                  onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}>
                  <span style={{ width: 16, height: 16, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, fontSize: 16, color: file.type === 'directory' ? blueLight : getIconColor(file.name) || textSecondary }}>
                    {file.type === 'directory' ? <FolderOutlined /> : <FileOutlined />}
                  </span>
                  <span style={{ flex: 1, color: textPrimary, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{file.name}</span>
                  {file.type === 'directory' && file.sha && (
                    <span style={{ color: textTertiary, fontSize: 12 }}>{t('desktop.serverShell.defaultBranch')}</span>
                  )}
                </div>
              ))}
              {displayFiles.length === 0 && (
                <div style={{ padding: 16, color: textTertiary, fontSize: 13, textAlign: 'center' }}>{t('app.repositories.empty.noFiles')}</div>
              )}
            </div>

            {selectedFileContent && (
              <div style={{ border: `1px solid ${borderColor}`, borderRadius: 12, overflow: 'hidden', background: bgSecondary, marginBottom: 20 }}>
                <div style={{ padding: '12px 16px', background: bgTertiary, borderBottom: `1px solid ${borderColor}`, display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, fontWeight: 500, color: textPrimary }}>
                  <FileTextOutlined style={{ fontSize: 16 }} />
                  {selectedFileContent.path}
                  <span style={{ marginLeft: 'auto', color: textTertiary, fontSize: 12, fontWeight: 400 }}>{selectedFileContent.size} bytes</span>
                </div>
                <pre style={{ margin: 0, padding: 16, fontSize: 13, lineHeight: 1.5, color: textPrimary, overflow: 'auto', maxHeight: 600, background: '#0d1117', fontFamily: "'JetBrains Mono', 'Fira Code', 'Consolas', monospace" }}>
                  {selectedFileContent.content}
                </pre>
              </div>
            )}

            {fileLoading && <div style={{ textAlign: 'center', padding: 40, color: textSecondary }}><Spin /></div>}

            {readme && (
              <div style={{ border: `1px solid ${borderColor}`, borderRadius: 12, overflow: 'hidden', background: bgSecondary }}>
                <div style={{ padding: '12px 16px', background: bgTertiary, borderBottom: `1px solid ${borderColor}`, display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, fontWeight: 500, color: textPrimary }}>
                  <ReadOutlined style={{ fontSize: 16 }} />README.md
                </div>
                <div className="readme-body" style={{ padding: 20, fontSize: 14, lineHeight: 1.7, color: textSecondary, maxHeight: 480, overflow: 'auto' }}>
                  {readme}
                </div>
              </div>
            )}
          </div>
        )}
      </Content>
    </Layout>
  );
}

function RepositoriesLayout({ children }: { children: ReactNode }) {
  return (
    <Content style={{ padding: '24px 32px', overflow: 'hidden' }}>
      {children}
    </Content>
  );
}

function ErrorBanner({ children }: { children: ReactNode }) {
  return (
    <div style={{ color: '#f85149', padding: 12, marginBottom: 12, flexShrink: 0, border: '1px solid #f85149', borderRadius: 8, background: 'rgba(248,81,73,0.1)' }}>
      {children}
    </div>
  );
}

function GitPullRequestIco() {
  return <span style={{ fontSize: 14, width: 14, display: 'inline-block' }}>⑂</span>;
}
function IssueIco() {
  return <span style={{ fontSize: 14, width: 14, display: 'inline-block' }}>!</span>;
}
function GearIco() {
  return <span style={{ fontSize: 14, width: 14, display: 'inline-block' }}>⚙</span>;
}