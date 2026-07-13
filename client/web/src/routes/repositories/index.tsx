import { useState, useEffect, useMemo, useCallback, type ReactNode } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Layout, Button, Avatar, Tabs, Select, message } from 'antd';
import type { TabsProps } from 'antd';
import {
  FolderOutlined,
  FileOutlined,
  FileTextOutlined,
  PullRequestOutlined,
  ExclamationCircleOutlined,
  SettingOutlined,
  PlayCircleOutlined,
  EyeOutlined,
  StarOutlined,
  ForkOutlined,
  ReadOutlined,
  UnorderedListOutlined,
  AppstoreOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import RepositoriesSkeleton from '../../components/skeleton/RepositoriesSkeleton';
import { useRepositoriesStore } from '../../stores/repositories';
import { useAuthStore } from '../../stores/auth';
import { repositoriesApi } from '../../api/repositories';
import type { RepoFile } from '../../api/repositories';

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
const green = '#3fb950';
const purple = '#bc8cff';

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
        if (!isLast) {
          node.children = [];
        }
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
        if (!roots.find((r) => r.key === node.key)) {
          roots.push(node);
        }
      } else {
        const parentPath = parts.slice(0, i).join('/');
        const parent = treeMap.get(parentPath);
        if (parent && parent.children && !parent.children.find((c) => c.key === node.key)) {
          parent.children.push(node);
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

function ActionButton({ icon, children, onClick }: { icon: ReactNode; children: ReactNode; onClick?: () => void }) {
  return (
    <Button
      icon={<span style={{ fontSize: 14 }}>{icon}</span>}
      onClick={onClick}
      style={{
        background: bgTertiary,
        color: textPrimary,
        border: `1px solid ${borderColor}`,
        padding: '6px 14px',
        borderRadius: 8,
        fontSize: 13,
        fontWeight: 500,
        display: 'flex',
        alignItems: 'center',
        gap: 6,
        height: 32,
        lineHeight: '20px',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.borderColor = textTertiary;
        e.currentTarget.style.background = hoverBg;
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderColor = borderColor;
        e.currentTarget.style.background = bgTertiary;
      }}
    >
      {children}
    </Button>
  );
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
  node,
  depth,
  selectedKey,
  onSelect,
  branchName,
}: {
  node: TreeNode;
  depth: number;
  selectedKey: string;
  onSelect: (key: string) => void;
  branchName?: string;
}) {
  const isSelected = selectedKey === node.key;
  const hasChildren = node.children && node.children.length > 0;
  const [expanded, setExpanded] = useState(hasChildren);

  return (
    <div>
      <div
        onClick={() => {
          onSelect(node.key);
          if (hasChildren) setExpanded(!expanded);
        }}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          padding: '6px 10px',
          borderRadius: 6,
          cursor: 'pointer',
          fontSize: 13,
          color: isSelected ? blueLight : textSecondary,
          background: isSelected ? activeBg : 'transparent',
          marginLeft: depth * 16,
          transition: 'all 0.15s',
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
        <TreeIcon type={node.type} iconColor={node.iconColor} />
        <span style={{ flex: 1, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{node.name}</span>
        {depth === 0 && branchName && (
          <span
            style={{
              fontSize: 10,
              color: textTertiary,
              background: '#0d1117',
              padding: '1px 6px',
              borderRadius: 8,
            }}
          >
            {branchName}
          </span>
        )}
      </div>
      {expanded && hasChildren && (
        <div>
          {node.children!.map((child) => (
            <TreeNodeView key={child.key} node={child} depth={depth + 1} selectedKey={selectedKey} onSelect={onSelect} branchName={branchName} />
          ))}
        </div>
      )}
    </div>
  );
}

export default function RepositoriesPage() {
  const { owner, repo } = useParams<{ owner?: string; repo?: string }>();
  const { t } = useTranslation();
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const {
    repositories,
    currentRepo,
    files: storeFiles,
    branches,
    commits,
    readme,
    isLoading,
    error,
    fetchRepositories,
    fetchRepositoriesByUser,
    fetchRepositoryByPath,
    fetchTree,
    fetchReadme,
    fetchBranches,
    fetchCommits,
    starRepository,
    unstarRepository,
    clearCurrent,
  } = useRepositoriesStore();

  const [activeTab, setActiveTab] = useState('code');
  const [selectedTreeKey, setSelectedTreeKey] = useState('');
  const [activeFilter, setActiveFilter] = useState('all');
  const [isStarred, setIsStarred] = useState(false);
  const [repoFilter, setRepoFilter] = useState<'mine' | 'all'>('mine');
  const [viewMode, setViewMode] = useState<'list' | 'grid'>('list');

  useEffect(() => {
    if (repo && owner) {
      fetchRepositoryByPath(owner, repo);
    } else if (user) {
      if (repoFilter === 'mine') {
        fetchRepositoriesByUser(user.id);
      } else {
        fetchRepositories();
      }
    }
    return () => {
      if (repo) clearCurrent();
    };
  }, [owner, repo, user?.id, repoFilter]);

  const isRepoEmpty = !!currentRepo && !currentRepo.status?.initialized;

  useEffect(() => {
    if (currentRepo) {
      if (!currentRepo.status?.initialized) return;
      const ref = currentRepo.default_branch;
      fetchTree(currentRepo.id, ref);
      fetchReadme(currentRepo.id, ref);
      fetchBranches(currentRepo.id);
      fetchCommits(currentRepo.id);
      repositoriesApi.getStarStatus(currentRepo.id).then((res) => {
        setIsStarred(res.starred);
      }).catch(() => {});
    }
  }, [currentRepo?.id]);

  const repoTree = useMemo(() => buildTree(storeFiles), [storeFiles]);

  const rootFiles = useMemo(
    () => storeFiles.filter((f) => !f.path.includes('/')),
    [storeFiles]
  );

  const displayFiles = useMemo(() => {
    if (activeFilter === 'all') return rootFiles;
    return rootFiles.filter((f) => {
      if (activeFilter === 'source') return /\.(ts|tsx|js|jsx|rs|go|py)$/i.test(f.name);
      if (activeFilter === 'config') return /\.(json|ya?ml|toml)$/i.test(f.name) || f.name === '.gitignore';
      if (activeFilter === 'tests') return f.path.includes('test') || f.path.includes('__tests__') || /\.(test|spec)\./i.test(f.name);
      return true;
    });
  }, [rootFiles, activeFilter]);

  const latestCommit = useMemo(
    () => (commits.length > 0 ? commits[0] : null),
    [commits]
  );

  const handleStarToggle = useCallback(async () => {
    if (!currentRepo) return;
    try {
      if (isStarred) {
        await unstarRepository(currentRepo.id);
        setIsStarred(false);
      } else {
        await starRepository(currentRepo.id);
        setIsStarred(true);
      }
    } catch {
      message.error('Failed to update star');
    }
  }, [currentRepo, isStarred, starRepository, unstarRepository]);

  if (isLoading) return <RepositoriesSkeleton />;

  if (!repo || !owner) {
    return (
      <Layout style={{ height: '100%', background: 'transparent' }}>
        <style>{`
          .repo-filter-dropdown .ant-select-item-option-active {
            background: rgba(88, 166, 255, 0.12) !important;
          }
          .repo-filter-dropdown .ant-select-item-option-selected {
            background: rgba(88, 166, 255, 0.2) !important;
            color: #58a6ff !important;
          }
          .repo-filter-dropdown .ant-select-item-option {
            color: #8b949e;
          }
        `}</style>
        <Content style={{ padding: '24px 32px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
            <h2 style={{ fontSize: 20, fontWeight: 700, margin: 0, color: textPrimary }}>
              {t('app.repositories.title')}
            </h2>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <Select
                value={repoFilter}
                onChange={(val) => setRepoFilter(val as 'mine' | 'all')}
                style={{ width: 180 }}
                size="small"
                variant="borderless"
                dropdownStyle={{ background: '#1c2128' }}
                popupClassName="repo-filter-dropdown"
              >
                <Select.Option value="mine">{t('app.repositories.filter.mine')}</Select.Option>
                <Select.Option value="all">{t('app.repositories.filter.all')}</Select.Option>
              </Select>
              <div style={{ display: 'flex', border: `1px solid ${borderColor}`, borderRadius: 6, overflow: 'hidden' }}>
                <button
                  onClick={() => setViewMode('list')}
                  style={{
                    padding: '6px 10px',
                    background: viewMode === 'list' ? hoverBg : 'transparent',
                    color: viewMode === 'list' ? textPrimary : textSecondary,
                    border: 'none',
                    cursor: 'pointer',
                    fontSize: 14,
                    display: 'flex',
                    alignItems: 'center',
                    transition: 'all 0.15s',
                  }}
                  onMouseEnter={(e) => { if (viewMode !== 'list') { e.currentTarget.style.background = hoverBg; e.currentTarget.style.color = textPrimary; } }}
                  onMouseLeave={(e) => { if (viewMode !== 'list') { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = textSecondary; } }}
                >
                  <UnorderedListOutlined />
                </button>
                <button
                  onClick={() => setViewMode('grid')}
                  style={{
                    padding: '6px 10px',
                    background: viewMode === 'grid' ? hoverBg : 'transparent',
                    color: viewMode === 'grid' ? textPrimary : textSecondary,
                    border: 'none',
                    cursor: 'pointer',
                    fontSize: 14,
                    display: 'flex',
                    alignItems: 'center',
                    transition: 'all 0.15s',
                  }}
                  onMouseEnter={(e) => { if (viewMode !== 'grid') { e.currentTarget.style.background = hoverBg; e.currentTarget.style.color = textPrimary; } }}
                  onMouseLeave={(e) => { if (viewMode !== 'grid') { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = textSecondary; } }}
                >
                  <AppstoreOutlined />
                </button>
              </div>
            </div>
          </div>
          {error && (
            <div style={{ color: '#f85149', padding: 12, marginBottom: 12, border: `1px solid #f85149`, borderRadius: 8, background: 'rgba(248,81,73,0.1)' }}>
              {error}
            </div>
          )}
          {viewMode === 'list' ? (
            <div>
              {repositories.map((r) => {
                const repoOwner = r.path.split('/')[0];
                return (
                  <div
                    key={r.id}
                    onClick={() => navigate(`/repositories/${repoOwner}/${r.name}`)}
                    style={{
                      padding: '12px 16px',
                      border: `1px solid ${borderColor}`,
                      borderRadius: 8,
                      marginBottom: 8,
                      cursor: 'pointer',
                      background: bgSecondary,
                      display: 'flex',
                      alignItems: 'center',
                      gap: 12,
                      transition: 'background 0.15s',
                    }}
                    onMouseEnter={(e) => { e.currentTarget.style.background = hoverBg; }}
                    onMouseLeave={(e) => { e.currentTarget.style.background = bgSecondary; }}
                  >
                    <FolderOutlined style={{ fontSize: 20, color: blueLight, flexShrink: 0 }} />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <span style={{ color: textPrimary, fontWeight: 600, fontSize: 14 }}>{r.name}</span>
                      <span style={{ color: textSecondary, marginLeft: 8, fontSize: 12 }}>{repoOwner}</span>
                    </div>
                    <span
                      style={{
                        fontSize: 11,
                        padding: '2px 8px',
                        border: `1px solid ${borderColor}`,
                        borderRadius: 12,
                        color: textSecondary,
                        flexShrink: 0,
                      }}
                    >
                      {r.is_public ? 'Public' : 'Private'}
                    </span>
                    <span style={{ color: textSecondary, fontSize: 12, display: 'flex', alignItems: 'center', gap: 4, flexShrink: 0 }}>
                      <StarOutlined style={{ fontSize: 12 }} /> {r.star_count}
                    </span>
                    <span style={{ color: textSecondary, fontSize: 12, display: 'flex', alignItems: 'center', gap: 4, flexShrink: 0 }}>
                      <ForkOutlined style={{ fontSize: 12 }} /> {r.fork_count}
                    </span>
                  </div>
                );
              })}
            </div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 12 }}>
              {repositories.map((r) => {
                const repoOwner = r.path.split('/')[0];
                return (
                  <div
                    key={r.id}
                    onClick={() => navigate(`/repositories/${repoOwner}/${r.name}`)}
                    style={{
                      padding: 16,
                      border: `1px solid ${borderColor}`,
                      borderRadius: 8,
                      cursor: 'pointer',
                      background: bgSecondary,
                      transition: 'background 0.15s',
                      display: 'flex',
                      flexDirection: 'column',
                    }}
                    onMouseEnter={(e) => { e.currentTarget.style.background = hoverBg; }}
                    onMouseLeave={(e) => { e.currentTarget.style.background = bgSecondary; }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
                      <FolderOutlined style={{ fontSize: 20, color: blueLight, flexShrink: 0 }} />
                      <span style={{ color: textPrimary, fontWeight: 600, fontSize: 14, flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{r.name}</span>
                      <span style={{ fontSize: 11, padding: '2px 8px', border: `1px solid ${borderColor}`, borderRadius: 12, color: textSecondary, flexShrink: 0 }}>
                        {r.is_public ? 'Public' : 'Private'}
                      </span>
                    </div>
                    <div style={{ fontSize: 12, color: textSecondary, marginBottom: 10 }}>{repoOwner}</div>
                    {r.description && (
                      <div style={{ fontSize: 13, color: textSecondary, marginBottom: 12, lineHeight: 1.4, flex: 1 }}>
                        {r.description}
                      </div>
                    )}
                    <div style={{ display: 'flex', gap: 16, fontSize: 12, color: textSecondary, marginTop: 'auto' }}>
                      <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                        <StarOutlined style={{ fontSize: 12 }} /> {r.star_count}
                      </span>
                      <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                        <ForkOutlined style={{ fontSize: 12 }} /> {r.fork_count}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
          {repositories.length === 0 && !isLoading && !error && (
            <p style={{ color: textSecondary, textAlign: 'center', padding: 40 }}>{t('app.repositories.noRepos')}</p>
          )}
        </Content>
      </Layout>
    );
  }

  if (!currentRepo) {
    return (
      <Layout style={{ height: '100%', background: 'transparent' }}>
        <Content style={{ padding: 24 }}>
          <div style={{ color: '#f85149', padding: 12, border: `1px solid #f85149`, borderRadius: 8, background: 'rgba(248,81,73,0.1)' }}>
            {error || t('app.repositories.notFound')}
          </div>
        </Content>
      </Layout>
    );
  }

  const filters = ['all', 'source', 'config', 'tests'] as const;

  const tabItems: TabsProps['items'] = [
    { key: 'code', label: <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}><FileTextOutlined style={{ fontSize: 14 }} />{t('app.repositories.tabs.code')}</span> },
    { key: 'pullRequests', label: <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}><PullRequestOutlined style={{ fontSize: 14 }} />{t('app.repositories.tabs.pullRequests')}<span className="tab-count">{branches.length}</span></span> },
    { key: 'issues', label: <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}><ExclamationCircleOutlined style={{ fontSize: 14 }} />{t('app.repositories.tabs.issues')}<span className="tab-count">{commits.length}</span></span> },
    { key: 'actions', label: <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}><PlayCircleOutlined style={{ fontSize: 14 }} />Actions</span> },
    { key: 'settings', label: <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}><SettingOutlined style={{ fontSize: 14 }} />{t('app.repositories.tabs.settings')}</span> },
  ];

  if (isRepoEmpty) {
    return (
      <Layout style={{ height: '100%', background: 'transparent' }}>
        <Content style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', gap: 12 }}>
          <div style={{ fontSize: 48, color: textTertiary, marginBottom: 8 }}>
            <FolderOutlined />
          </div>
          <h2 style={{ fontSize: 20, fontWeight: 600, margin: 0, color: textPrimary }}>{t('app.repositories.empty.title')}</h2>
          <p style={{ fontSize: 14, color: textSecondary, margin: 0 }}>{t('app.repositories.empty.description')}</p>
        </Content>
      </Layout>
    );
  }

  return (
    <Layout style={{ height: '100%', background: 'transparent' }}>
      <style>{`
        .repo-tabs .ant-tabs-nav {
          margin-bottom: 20px !important;
        }
        .repo-tabs .ant-tabs-tab {
          padding: 10px 16px !important;
          font-size: 13px !important;
          color: ${textSecondary} !important;
          border-bottom: 2px solid transparent !important;
          transition: all 0.2s !important;
        }
        .repo-tabs .ant-tabs-tab:hover {
          color: ${textPrimary} !important;
        }
        .repo-tabs .ant-tabs-tab-active {
          color: ${textPrimary} !important;
          border-bottom: 2px solid ${bluePrimary} !important;
        }
        .repo-tabs .ant-tabs-ink-bar {
          display: none !important;
        }
        .repo-tabs .ant-tabs-tab .tab-count {
          background: #0d1117;
          padding: 1px 7px;
          border-radius: 10px;
          font-size: 11px;
          margin-left: 4px;
        }
        .readme-body .badge {
          display: inline-block;
          padding: 3px 10px;
          border-radius: 12px;
          font-size: 11px;
          font-weight: 600;
          margin-right: 6px;
        }
        .readme-body .badge-blue {
          background: rgba(31, 111, 235, 0.15);
          color: ${blueLight};
        }
        .readme-body .badge-green {
          background: rgba(63, 185, 80, 0.15);
          color: ${green};
        }
        .readme-body .badge-purple {
          background: rgba(188, 140, 255, 0.15);
          color: ${purple};
        }
      `}</style>

      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
      <Sider
        width={280}
        style={{
          background: bgSecondary,
          borderRight: `1px solid ${borderColor}`,
          display: 'flex',
          flexDirection: 'column',
          flexShrink: 0,
        }}
      >
        <div style={{ padding: 16, borderBottom: `1px solid ${borderColor}` }}>
          <h3 style={{ fontSize: 13, fontWeight: 600, marginBottom: 10, color: textPrimary }}>{t('app.repositories.explorer')}</h3>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {filters.map((f) => {
              const isActive = activeFilter === f;
              return (
                <span
                  key={f}
                  onClick={() => setActiveFilter(f)}
                  style={{
                    padding: '3px 10px',
                    borderRadius: 12,
                    fontSize: 11,
                    cursor: 'pointer',
                    transition: 'all 0.2s',
                    background: isActive ? 'rgba(31,111,235,0.15)' : '#0d1117',
                    border: `1px solid ${isActive ? bluePrimary : borderColor}`,
                    color: isActive ? blueLight : textSecondary,
                  }}
                  onMouseEnter={(e) => {
                    if (!isActive) {
                      e.currentTarget.style.background = 'rgba(31,111,235,0.15)';
                      e.currentTarget.style.borderColor = bluePrimary;
                      e.currentTarget.style.color = blueLight;
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!isActive) {
                      e.currentTarget.style.background = '#0d1117';
                      e.currentTarget.style.borderColor = borderColor;
                      e.currentTarget.style.color = textSecondary;
                    }
                  }}
                >
                  {t(`app.repositories.filters.${f}`)}
                </span>
              );
            })}
          </div>
        </div>
        <div style={{ flex: 1, overflowY: 'auto', padding: 8 }}>
          {repoTree.length > 0 ? (
            repoTree.map((node) => (
              <TreeNodeView
                key={node.key}
                node={node}
                depth={0}
                selectedKey={selectedTreeKey}
                onSelect={(key) => setSelectedTreeKey(key)}
                branchName={currentRepo.default_branch}
              />
            ))
          ) : (
            <div style={{ padding: 16, color: textTertiary, fontSize: 13, textAlign: 'center' }}>
              {t('app.repositories.noFiles')}
            </div>
          )}
        </div>
      </Sider>

      <Content style={{ flex: 1, overflowY: 'auto', padding: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 20, flexWrap: 'wrap' }}>
          <span style={{ fontSize: 24, color: blueLight, display: 'flex', alignItems: 'center' }}>
            <FolderOutlined />
          </span>
          <h2 style={{ fontSize: 20, fontWeight: 700, margin: 0, color: textPrimary }}>{currentRepo.name}</h2>
          <span
            style={{
              fontSize: 11,
              padding: '2px 8px',
              border: `1px solid ${borderColor}`,
              borderRadius: 12,
              color: textSecondary,
            }}
          >
            {currentRepo.is_public ? t('app.repositories.visibility.public') : t('app.repositories.visibility.private')}
          </span>
          <div style={{ marginLeft: 'auto', display: 'flex', gap: 8 }}>
            <ActionButton icon={<EyeOutlined />}>{t('app.repositories.actions.watch')}</ActionButton>
            <ActionButton icon={<StarOutlined style={{ color: isStarred ? '#e3b341' : undefined }} />} onClick={handleStarToggle}>
              {isStarred ? t('app.repositories.actions.unstar') : t('app.repositories.actions.star')} {currentRepo.star_count}
            </ActionButton>
            <ActionButton icon={<ForkOutlined />}>{t('app.repositories.actions.fork')} {currentRepo.fork_count}</ActionButton>
          </div>
        </div>

        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={tabItems}
          className="repo-tabs"
        />

        <div
          style={{
            border: `1px solid ${borderColor}`,
            borderRadius: 12,
            overflow: 'hidden',
            marginBottom: 20,
            background: bgSecondary,
          }}
        >
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 12,
              padding: '12px 16px',
              background: bgTertiary,
              borderBottom: `1px solid ${borderColor}`,
              fontSize: 13,
            }}
          >
            <Avatar size={24} style={{ background: 'linear-gradient(135deg, #58a6ff, #1f6feb)', fontSize: 10, fontWeight: 600, flexShrink: 0 }}>
              {latestCommit ? latestCommit.author_name.charAt(0).toUpperCase() : '?'}
            </Avatar>
            <span style={{ flex: 1, color: textSecondary, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              {latestCommit ? (
                <>
                  <strong style={{ color: textPrimary, marginRight: 4 }}>{latestCommit.author_name}</strong>
                  {latestCommit.message}
                </>
              ) : (
                t('app.repositories.noCommits')
              )}
            </span>
            <span style={{ color: textTertiary, fontSize: 12, whiteSpace: 'nowrap' }}>
              {latestCommit ? `${latestCommit.hash.slice(0, 7)}` : ''}
            </span>
          </div>

          {displayFiles.map((file, index) => (
            <div
              key={file.path}
              onClick={() => file.type === 'directory' && navigate(`/editor/${owner}/${repo}`)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 12,
                padding: '8px 16px',
                borderBottom: index === displayFiles.length - 1 ? 'none' : `1px solid ${borderColor}`,
                fontSize: 13,
                cursor: file.type === 'directory' ? 'pointer' : 'default',
                transition: 'background 0.15s',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = hoverBg;
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'transparent';
              }}
            >
              <span
                style={{
                  width: 16,
                  height: 16,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0,
                  fontSize: 16,
                  color: file.type === 'directory' ? blueLight : getIconColor(file.name) || textSecondary,
                }}
              >
                {file.type === 'directory' ? <FolderOutlined /> : <FileOutlined />}
              </span>
              <span style={{ flex: 1, color: textPrimary, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{file.name}</span>
              <span style={{ flex: 2, color: textSecondary, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>-</span>
              <span style={{ color: textTertiary, fontSize: 12, width: 100, textAlign: 'right', whiteSpace: 'nowrap' }}></span>
            </div>
          ))}
          {displayFiles.length === 0 && (
            <div style={{ padding: 16, color: textTertiary, fontSize: 13, textAlign: 'center' }}>
              {t('app.repositories.noFiles')}
            </div>
          )}
        </div>

        {readme && (
          <div
            style={{
              border: `1px solid ${borderColor}`,
              borderRadius: 12,
              overflow: 'hidden',
              background: bgSecondary,
            }}
          >
            <div
              style={{
                padding: '12px 16px',
                background: bgTertiary,
                borderBottom: `1px solid ${borderColor}`,
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                fontSize: 13,
                fontWeight: 500,
                color: textPrimary,
              }}
            >
              <ReadOutlined style={{ fontSize: 16 }} />
              README.md
            </div>
            <div
              className="readme-body"
              dangerouslySetInnerHTML={{ __html: readme }}
              style={{ padding: 20, fontSize: 14, lineHeight: 1.7, color: textSecondary }}
            />
          </div>
        )}
      </Content>
      </div>
    </Layout>
  );
}
