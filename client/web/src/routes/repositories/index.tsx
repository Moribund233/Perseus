import { useState, useEffect, useMemo, useCallback, type ReactNode } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Layout, Button, Avatar, Tabs, Select, Spin, message } from 'antd';
import type { TabsProps } from 'antd';
import {
  FolderOutlined,
  FileOutlined,
  FileTextOutlined,
  PullRequestOutlined,
  ExclamationCircleOutlined,
  SettingOutlined,
  PlayCircleOutlined,
  TagOutlined,
  EyeOutlined,
  StarOutlined,
  ForkOutlined,
  ReadOutlined,
  UnorderedListOutlined,
  AppstoreOutlined,
  ArrowLeftOutlined,
  EditOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useSpring, animated } from '@react-spring/web';
import RepositoriesSkeleton from '../../components/skeleton/RepositoriesSkeleton';
import Markdown from '../../components/Markdown';
import ReleasesTab from '../../components/repo/ReleasesTab';
import BuildsTab from '../../components/repo/BuildsTab';
import RepoSettingsTab from '../../components/repo/RepoSettingsTab';
import Explorer from '../../components/explorer/Explorer';
import { useRepositoriesStore } from '../../stores/repositories';
import { useIssuesStore } from '../../stores/issues';
import { usePullRequestsStore } from '../../stores/pullRequests';
import { useAuthStore } from '../../stores/auth';
import { repositoriesApi } from '../../api/repositories';
import type { RepoBlob } from '../../api/repositories';

const { Sider, Content } = Layout;

const borderColor = '#21262d';
const hoverBg = '#1c2333';
const textSecondary = '#8b949e';
const textPrimary = '#e6edf3';
const textTertiary = '#6e7681';
const blueLight = '#58a6ff';
const bluePrimary = '#1f6feb';
const bgSecondary = '#161b22';
const bgTertiary = '#1c2128';
const green = '#3fb950';
const purple = '#bc8cff';

/** "src/utils/a.ts" → "src/utils"；根级返回 "" */
function parentPath(path: string): string {
  const i = path.lastIndexOf('/');
  return i >= 0 ? path.slice(0, i) : '';
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

function FadeBlock({ children, ...rest }: { children: React.ReactNode; [key: string]: unknown }) {
  const style = useSpring({
    from: { opacity: 0 },
    to: { opacity: 1 },
    reset: true,
    config: { tension: 280, friction: 30 },
  });
  return <animated.div style={style} {...rest}>{children}</animated.div>;
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

export default function RepositoriesPage() {
  const { owner, repo } = useParams<{ owner?: string; repo?: string }>();
  const { t } = useTranslation();
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const {
    repositories,
    currentRepo,
    files: storeFiles,
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
    watchRepository,
    unwatchRepository,
    forkRepository,
    clearCurrent,
  } = useRepositoriesStore();

  const [activeTab, setActiveTab] = useState('code');
  const [selectedTreeKey, setSelectedTreeKey] = useState('');
  const [selectedFileContent, setSelectedFileContent] = useState<RepoBlob | null>(null);
  const [fileLoading, setFileLoading] = useState(false);
  const [currentDir, setCurrentDir] = useState('');
  const [dirLoading, setDirLoading] = useState(false);
  const [isStarred, setIsStarred] = useState(false);
  const [isWatching, setIsWatching] = useState(false);
  const [repoFilter, setRepoFilter] = useState<'mine' | 'all'>('mine');
  const [viewMode, setViewMode] = useState<'list' | 'grid'>('list');
  const { issues, fetchIssues } = useIssuesStore();
  const { pullRequests, fetchPullRequests } = usePullRequestsStore();

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
  }, [owner, repo, user, user?.id, repoFilter, fetchRepositoryByPath, fetchRepositoriesByUser, fetchRepositories, clearCurrent]);

  useEffect(() => {
    let cancelled = false;
    const loadFile = async () => {
      if (!selectedTreeKey || !currentRepo) return;
      const file = storeFiles.find((f) => f.path === selectedTreeKey && f.type === 'file');
      if (!file) {
        if (!cancelled) setSelectedFileContent(null);
        return;
      }
      if (!cancelled) setFileLoading(true);
      try {
        const blob = await repositoriesApi.getBlob(currentRepo.id, selectedTreeKey, currentRepo.default_branch);
        if (!cancelled) setSelectedFileContent(blob);
      } catch {
        if (!cancelled) setSelectedFileContent(null);
      } finally {
        if (!cancelled) setFileLoading(false);
      }
    };
    loadFile();
    return () => { cancelled = true; };
  }, [selectedTreeKey, currentRepo, storeFiles]);

  const isRepoEmpty = !!currentRepo && !currentRepo.status?.initialized;

  useEffect(() => {
    if (currentRepo) {
      if (!currentRepo.status?.initialized) return;
      const ref = currentRepo.default_branch;
      fetchTree(currentRepo.id, ref);
      fetchReadme(currentRepo.id, ref);
      fetchBranches(currentRepo.id);
      fetchCommits(currentRepo.id, { branch: ref });
      fetchIssues(currentRepo.id, 'open');
      fetchPullRequests(currentRepo.id);
      repositoriesApi.getStarStatus(currentRepo.id).then((res) => {
        setIsStarred(res.starred);
      }).catch(() => {});
      repositoriesApi.getWatchStatus(currentRepo.id).then((res) => {
        setIsWatching(res.watching);
      }).catch(() => {});
    }
  }, [currentRepo, fetchTree, fetchReadme, fetchBranches, fetchCommits, fetchIssues, fetchPullRequests]);

  // 当前目录下的条目（目录 + 文件）
  const dirEntries = useMemo(
    () => storeFiles.filter((f) => parentPath(f.path) === currentDir),
    [storeFiles, currentDir]
  );

  /** 进入目录：清空文件选择并把列表切到该目录 */
  const goToDir = useCallback((path: string) => {
    setSelectedTreeKey('');
    setSelectedFileContent(null);
    setCurrentDir(path);
  }, []);

  /** 从文件列表进入目录：若子项尚未加载则拉取 */
  const openDir = useCallback(async (path: string) => {
    if (!currentRepo) return;
    goToDir(path);
    const loaded = storeFiles.some((f) => parentPath(f.path) === path);
    if (!loaded) {
      setDirLoading(true);
      try {
        await fetchTree(currentRepo.id, currentRepo.default_branch, path);
      } finally {
        setDirLoading(false);
      }
    }
  }, [currentRepo, storeFiles, fetchTree, goToDir]);

  /** Explorer 目录按需加载 */
  const handleLoadDir = useCallback((key: string) => {
    if (!currentRepo) return;
    fetchTree(currentRepo.id, currentRepo.default_branch, key).catch(() => {});
  }, [currentRepo, fetchTree]);

  const closeViewer = useCallback(() => {
    setSelectedTreeKey('');
    setSelectedFileContent(null);
  }, []);

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

  const handleWatchToggle = useCallback(async () => {
    if (!currentRepo) return;
    try {
      if (isWatching) {
        await unwatchRepository(currentRepo.id);
        setIsWatching(false);
      } else {
        await watchRepository(currentRepo.id);
        setIsWatching(true);
      }
    } catch {
      message.error(t('app.repositories.watchFailed'));
    }
  }, [currentRepo, isWatching, watchRepository, unwatchRepository, t]);

  const handleFork = useCallback(async () => {
    if (!currentRepo) return;
    try {
      const fork = await forkRepository(currentRepo.id);
      message.success(t('app.repositories.forkSuccess', { name: fork.path }));
      navigate(`/repositories/${fork.path}`);
    } catch {
      message.error(t('app.repositories.forkFailed'));
    }
  }, [currentRepo, forkRepository, navigate, t]);

  if (isLoading && repositories.length === 0) return <RepositoriesSkeleton />;

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
        <Content style={{ padding: '24px 32px', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16, flexShrink: 0 }}>
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
                styles={{ popup: { root: { background: '#1c2128' } } }}
                classNames={{ popup: { root: 'repo-filter-dropdown' } }}
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
            <div style={{ color: '#f85149', padding: 12, marginBottom: 12, flexShrink: 0, border: `1px solid #f85149`, borderRadius: 8, background: 'rgba(248,81,73,0.1)' }}>
              {error}
            </div>
          )}
          <div style={{ flex: 1, overflowY: 'auto', minHeight: 0 }}>
            <FadeBlock key={`${repoFilter}-${viewMode}`}>
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
            </FadeBlock>
            {repositories.length === 0 && !isLoading && !error && (
              <p style={{ color: textSecondary, textAlign: 'center', padding: 40 }}>{t('app.repositories.noRepos')}</p>
            )}
          </div>
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

  const tabItems: TabsProps['items'] = [
    { key: 'code', label: <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}><FileTextOutlined style={{ fontSize: 14 }} />{t('app.repositories.tabs.code')}</span> },
    { key: 'pullRequests', label: <span style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer' }} onClick={() => navigate(`/repositories/${owner}/${repo}/pulls`)}><PullRequestOutlined style={{ fontSize: 14 }} />{t('app.repositories.tabs.pullRequests')}<span className="tab-count">{pullRequests.length}</span></span> },
    { key: 'issues', label: <span style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer' }} onClick={() => navigate(`/repositories/${owner}/${repo}/issues`)}><ExclamationCircleOutlined style={{ fontSize: 14 }} />{t('app.repositories.tabs.issues')}<span className="tab-count">{issues.length}</span></span> },
    { key: 'releases', label: <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}><TagOutlined style={{ fontSize: 14 }} />{t('app.repositories.tabs.releases')}</span> },
    { key: 'actions', label: <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}><PlayCircleOutlined style={{ fontSize: 14 }} />{t('app.repositories.tabs.actions')}</span> },
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
    <Layout style={{ height: '100%', background: 'transparent', overflow: 'hidden' }}>
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
      {activeTab === 'code' && (
      <Sider
        width={280}
        style={{
          background: bgSecondary,
          borderRight: `1px solid ${borderColor}`,
          flexShrink: 0,
          height: '100%',
          overflow: 'hidden',
        }}
        styles={{ body: { display: 'flex', flexDirection: 'column', height: '100%', minHeight: 0, overflow: 'hidden' } }}
      >
        <div style={{ padding: '10px 12px', borderBottom: `1px solid ${borderColor}` }}>
          <h3 style={{ fontSize: 13, fontWeight: 600, margin: 0, color: textPrimary }}>{t('app.repositories.explorer')}</h3>
        </div>
        <Explorer
          files={storeFiles}
          selectedKey={selectedTreeKey}
          onSelectFile={setSelectedTreeKey}
          onLoadDir={handleLoadDir}
          emptyText={t('app.repositories.empty.noFiles')}
        />
      </Sider>
      )}

      <Content style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column', padding: '24px 24px 0' }}>
        <div style={{ flexShrink: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 20, flexWrap: 'wrap' }}>
            <Button
              type="text"
              icon={<ArrowLeftOutlined />}
              onClick={() => navigate('/repositories')}
              style={{ color: textSecondary, fontSize: 13, padding: '0 8px', height: 30, flexShrink: 0 }}
              onMouseEnter={(e) => { e.currentTarget.style.color = textPrimary; }}
              onMouseLeave={(e) => { e.currentTarget.style.color = textSecondary; }}
            >
              {t('app.repositories.backToRepos')}
            </Button>
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
              <ActionButton icon={<EyeOutlined style={{ color: isWatching ? blueLight : undefined }} />} onClick={handleWatchToggle}>
                {isWatching ? t('app.repositories.actions.unwatch') : t('app.repositories.actions.watch')} {currentRepo.watch_count ?? 0}
              </ActionButton>
              <ActionButton icon={<StarOutlined style={{ color: isStarred ? '#e3b341' : undefined }} />} onClick={handleStarToggle}>
                {isStarred ? t('app.repositories.actions.unstar') : t('app.repositories.actions.star')} {currentRepo.star_count}
              </ActionButton>
              <ActionButton icon={<ForkOutlined />} onClick={handleFork}>{t('app.repositories.actions.fork')} {currentRepo.fork_count}</ActionButton>
            </div>
          </div>

          <Tabs
            activeKey={activeTab}
            onChange={setActiveTab}
            items={tabItems}
            className="repo-tabs"
          />
        </div>

        {activeTab === 'code' ? (
        selectedFileContent ? (
        <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column', paddingBottom: 24 }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: '10px 14px',
              background: bgTertiary,
              border: `1px solid ${borderColor}`,
              borderBottom: 'none',
              borderRadius: '12px 12px 0 0',
              fontSize: 13,
              fontWeight: 500,
              color: textPrimary,
            }}
          >
            <span
              onClick={closeViewer}
              title={t('app.repositories.backToList')}
              style={{ display: 'flex', alignItems: 'center', cursor: 'pointer', color: textSecondary, flexShrink: 0 }}
              onMouseEnter={(e) => { e.currentTarget.style.color = blueLight; }}
              onMouseLeave={(e) => { e.currentTarget.style.color = textSecondary; }}
            >
              <ArrowLeftOutlined />
            </span>
            <FileTextOutlined style={{ fontSize: 16, flexShrink: 0 }} />
            <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{selectedFileContent.path}</span>
            <span style={{ marginLeft: 'auto', color: textTertiary, fontSize: 12, fontWeight: 400, whiteSpace: 'nowrap' }}>
              {selectedFileContent.size} bytes
            </span>
            <Button
              size="small"
              icon={<EditOutlined />}
              onClick={() => navigate(`/editor/${owner}/${repo}?file=${encodeURIComponent(selectedFileContent.path)}`)}
              style={{ background: bgSecondary, color: textPrimary, border: `1px solid ${borderColor}`, fontSize: 12, height: 26, flexShrink: 0 }}
            >
              {t('app.repositories.openInEditor')}
            </Button>
          </div>
          <pre
            style={{
              flex: 1,
              minHeight: 0,
              margin: 0,
              padding: 16,
              fontSize: 13,
              lineHeight: 1.5,
              color: textPrimary,
              overflow: 'auto',
              border: `1px solid ${borderColor}`,
              borderRadius: '0 0 12px 12px',
              background: '#0d1117',
              fontFamily: "'JetBrains Mono', 'Fira Code', 'Consolas', monospace",
            }}
          >
            {selectedFileContent.content}
          </pre>
        </div>
        ) : (
        <div style={{ flex: 1, overflowY: 'auto', paddingBottom: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 12, fontSize: 13, flexWrap: 'wrap' }}>
          <span
            onClick={() => goToDir('')}
            style={{ color: currentDir ? blueLight : textPrimary, cursor: currentDir ? 'pointer' : 'default', fontWeight: currentDir ? 400 : 600 }}
          >
            {currentRepo?.name}
          </span>
          {currentDir.split('/').filter(Boolean).map((seg, i, arr) => {
            const upTo = arr.slice(0, i + 1).join('/');
            const isLast = i === arr.length - 1;
            return (
              <span key={upTo} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span style={{ color: textTertiary }}>/</span>
                <span
                  onClick={() => goToDir(upTo)}
                  style={{ color: isLast ? textPrimary : blueLight, cursor: isLast ? 'default' : 'pointer', fontWeight: isLast ? 600 : 400 }}
                >
                  {seg}
                </span>
              </span>
            );
          })}
          {dirLoading && <Spin size="small" style={{ marginLeft: 4 }} />}
        </div>
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
                t('app.repositories.empty.noCommits')
              )}
            </span>
            <span style={{ color: textTertiary, fontSize: 12, whiteSpace: 'nowrap' }}>
              {latestCommit ? `${latestCommit.hash.slice(0, 7)}` : ''}
            </span>
          </div>

          {dirEntries.map((file, index) => (
            <div
              key={file.path}
              onClick={() => {
                if (file.type === 'directory') {
                  void openDir(file.path);
                } else {
                  setSelectedTreeKey(file.path);
                }
              }}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 12,
                padding: '8px 16px',
                borderBottom: index === dirEntries.length - 1 ? 'none' : `1px solid ${borderColor}`,
                fontSize: 13,
                cursor: 'pointer',
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
              <span style={{ flex: 2, color: textSecondary, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {file.type === 'file' && file.last_commit ? (
                  <>
                    <strong style={{ color: textPrimary, marginRight: 4 }}>{file.last_commit.author}</strong>
                    {file.last_commit.message}
                  </>
                ) : '-'}
              </span>
              <span style={{ color: textTertiary, fontSize: 12, width: 100, textAlign: 'right', whiteSpace: 'nowrap' }}>
                {file.type === 'file' && file.last_commit ? (() => {
                  const d = new Date(file.last_commit.date);
                  if (Number.isNaN(d.getTime())) return '';
                  const diff = Date.now() - d.getTime();
                  if (diff < 60_000) return t('app.repositories.fileList.timeUnits.justNow');
                  if (diff < 3_600_000) return t('app.repositories.fileList.timeUnits.minutesAgo', { n: Math.floor(diff / 60_000) });
                  if (diff < 86_400_000) return t('app.repositories.fileList.timeUnits.hoursAgo', { n: Math.floor(diff / 3_600_000) });
                  if (diff < 7 * 86_400_000) return t('app.repositories.fileList.timeUnits.daysAgo', { n: Math.floor(diff / 86_400_000) });
                  if (diff < 30 * 86_400_000) return t('app.repositories.fileList.timeUnits.monthsAgo', { n: Math.floor(diff / (30 * 86_400_000)) });
                  return t('app.repositories.fileList.timeUnits.yearsAgo', { n: Math.floor(diff / (365 * 86_400_000)) });
                })() : ''}
              </span>
            </div>
          ))}
          {dirEntries.length === 0 && (
            <div style={{ padding: 16, color: textTertiary, fontSize: 13, textAlign: 'center' }}>
              {t('app.repositories.empty.noFiles')}
            </div>
          )}
        </div>

        {fileLoading && (
          <div style={{ textAlign: 'center', padding: 40, color: textSecondary }}>
            <Spin />
          </div>
        )}

        {readme && currentDir === '' && (
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
              style={{ padding: 20, fontSize: 14, lineHeight: 1.7, color: textSecondary }}
            >
              <Markdown>{readme}</Markdown>
            </div>
          </div>
        )}
      </div>
      )
      ) : (
        <div style={{ flex: 1, overflowY: 'auto', padding: '4px 0 24px' }}>
          {activeTab === 'releases' && <ReleasesTab repoId={currentRepo.id} />}
          {activeTab === 'actions' && <BuildsTab repoId={currentRepo.id} />}
          {activeTab === 'settings' && <RepoSettingsTab repoId={currentRepo.id} />}
        </div>
      )}
      </Content>
      </div>
    </Layout>
  );
}
