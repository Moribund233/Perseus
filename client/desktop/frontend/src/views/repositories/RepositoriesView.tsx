import { useState, useEffect, useMemo, useCallback, type ReactNode } from 'react';
import { Layout, Button, Avatar, Tabs, Tag, Spin, Empty, message, App as AntApp, Input, Modal, Radio, Tooltip } from 'antd';
import type { TabsProps } from 'antd';
import {
  FolderOutlined,
  FileTextOutlined,
  StarOutlined,
  ForkOutlined,
  BranchesOutlined,
  ReadOutlined,
  CloudDownloadOutlined,
  PlusOutlined,
  SearchOutlined,
  AppstoreOutlined,
  UnorderedListOutlined,
  PlayCircleOutlined,
  RocketOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import {
  useRepositoriesStore,
} from '../../stores/repositories';
import { useServersStore } from '../../stores/servers';
import { repositoriesApi, type RepoBlob, type Repository } from '../../api/repositories';
import { createWorkspace, listWorkspaces } from '../../api/workspaces';
import { useWorkspaceStore } from '../../stores/workspace';
import IssuesView from './IssuesView';
import IssueDetail from './IssueDetail';
import PullRequestsView from './PullRequestsView';
import PullRequestDetail from './PullRequestDetail';
import RepositorySettings from './RepositorySettings';
import BuildsPanel from './BuildsPanel';
import ReleasesPanel from './ReleasesPanel';
import Markdown from '../../components/Markdown';
import RepoExplorer from '../../components/RepoExplorer';
import { fileBadge } from '../workspace/ExplorerPanel';
import { issuesApi } from '../../api/issues';
import { pullRequestsApi } from '../../api/pullRequests';
import type { Issue } from '../../api/issues';
import type { PR } from '../../api/pullRequests';
import { timeAgo } from '../../utils/time';

const { Sider, Content } = Layout;

const borderColor = '#21262d';
const hoverBg = '#1c2333';
const textSecondary = '#8b949e';
const textPrimary = '#e6edf3';
const textTertiary = '#6e7681';
const blueLight = '#58a6ff';
const bgSecondary = '#161b22';
const bgTertiary = '#1c2128';

// 语言标识 → GitHub 风格品牌色（与后端 detect_file_language 标识对应）。
const LANG_COLORS: Record<string, string> = {
  python: '#3572a5',
  javascript: '#f1e05a',
  typescript: '#3178c6',
  html: '#e34c26',
  css: '#563d7c',
  scss: '#c6538c',
  sass: '#a53b70',
  less: '#1d365d',
  go: '#00add8',
  rust: '#dea584',
  java: '#b07219',
  json: '#292929',
  markdown: '#8b949e',
  yaml: '#cb171e',
  xml: '#0060ac',
  shell: '#89e051',
  sql: '#e38c00',
  dockerfile: '#384d54',
  makefile: '#427819',
};

function langLabel(lang: string): { name: string; color: string } {
  const label = lang.charAt(0).toUpperCase() + lang.slice(1);
  return { name: label, color: LANG_COLORS[lang] ?? textTertiary };
}

function repoPrimaryLang(repo: Repository): { name: string; color: string } | null {
  if (!repo.languages) return null;
  const top = Object.entries(repo.languages).sort((a, b) => b[1] - a[1])[0];
  return top ? langLabel(top[0]) : null;
}

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
  const [selectedIssue, setSelectedIssue] = useState<Issue | null>(null);
  const [selectedPR, setSelectedPR] = useState<PR | null>(null);
  const [selectedTreeKey, setSelectedTreeKey] = useState('');
  const [selectedFileContent, setSelectedFileContent] = useState<RepoBlob | null>(null);
  const [fileLoading, setFileLoading] = useState(false);
  const [isStarred, setIsStarred] = useState(false);
  const [cloning, setCloning] = useState(false);
  const [issueCount, setIssueCount] = useState<number | null>(null);
  const [prCount, setPrCount] = useState<number | null>(null);
  const [forking, setForking] = useState(false);
  const fetchRepositories = useRepositoriesStore((s) => s.fetchRepositories);
  const createRepository = useRepositoriesStore((s) => s.createRepository);

  // 列表视图：筛选 / 视图切换 / 新建仓库。
  const [filter, setFilter] = useState('');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [createOpen, setCreateOpen] = useState(false);
  const [createName, setCreateName] = useState('');
  const [createDesc, setCreateDesc] = useState('');
  const [createPublic, setCreatePublic] = useState(true);
  const [creating, setCreating] = useState(false);

  const filtered = useMemo(() => {
    const q = filter.trim().toLowerCase();
    if (!q) return repositories;
    return repositories.filter((r) => r.name.toLowerCase().includes(q) || r.path.toLowerCase().includes(q));
  }, [repositories, filter]);

  // 列表视图：加载仓库列表。
  useEffect(() => {
    if (!currentRepo) {
      fetchRepositories();
    }
  }, [currentRepo, fetchRepositories]);

  // 门户搜索深链：打开目标仓库（必要时先拉取），命中后定位 Tab/详情。
  const pendingOpen = useRepositoriesStore((s) => s.pendingOpen);
  const setPendingOpen = useRepositoriesStore((s) => s.setPendingOpen);

  useEffect(() => {
    if (!pendingOpen || currentRepo) return;
    const [owner, name] = pendingOpen.repoPath.split('/');
    if (!owner || !name) { setPendingOpen(null); return; }
    fetchRepositoryByPath(owner, name);
  }, [pendingOpen, currentRepo, fetchRepositoryByPath, setPendingOpen]);

  useEffect(() => {
    if (!pendingOpen || !currentRepo) return;
    if (currentRepo.path !== pendingOpen.repoPath) {
      clearCurrent();
      return;
    }
    if (pendingOpen.tab) setActiveTab(pendingOpen.tab);
    if (pendingOpen.issueNumber != null) setSelectedIssue({ issue_number: pendingOpen.issueNumber } as Issue);
    if (pendingOpen.prNumber != null) setSelectedPR({ pr_number: pendingOpen.prNumber } as PR);
    setPendingOpen(null);
  }, [pendingOpen, currentRepo, clearCurrent, setPendingOpen]);

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

  // 详情：加载树/读me/分支/提交/star 状态 + Issue/PR 计数。
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
    issuesApi.list(sid, currentRepo.id, { status: 'open', per_page: 1 }).then((d) => setIssueCount(d.total)).catch(() => {});
    pullRequestsApi.list(sid, currentRepo.id, { status: 'open', per_page: 1 }).then((d) => setPrCount(d.total)).catch(() => {});
  }, [currentRepo, server?.id, fetchTree, fetchReadme, fetchBranches, fetchCommits]);

  const onFork = async () => {
    if (!currentRepo || !server) return;
    setForking(true);
    try {
      await repositoriesApi.fork(server.id, currentRepo.id);
      message.success(t('desktop.repos.forkOk', { name: currentRepo.name }));
      const parts = currentRepo.path.split('/');
      await fetchRepositoryByPath(parts[0], parts[1] ?? currentRepo.name);
    } catch (e) {
      message.error(`${t('desktop.repos.forkFail')}: ${(e as Error).message}`);
    } finally {
      setForking(false);
    }
  };

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

  const rootFiles = useMemo(() => storeFiles.filter((f) => !f.path.includes('/')), [storeFiles]);

  // Explorer 目录按需加载
  const handleLoadDir = useCallback((path: string) => {
    if (!currentRepo) return;
    fetchTree(currentRepo.id, currentRepo.default_branch, path).catch(() => {});
  }, [currentRepo, fetchTree]);

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
    const onCreate = async () => {
      if (!createName.trim()) return;
      setCreating(true);
      try {
        await createRepository({ name: createName.trim(), description: createDesc.trim() || undefined, is_public: createPublic });
        message.success(t('desktop.repos.createOk', { name: createName.trim() }));
        setCreateOpen(false);
        setCreateName('');
        setCreateDesc('');
      } catch (e) {
        message.error(`${t('desktop.repos.createFail')}: ${(e as Error).message}`);
      } finally {
        setCreating(false);
      }
    };

    return (
      <div className="page">
        <div className="page-head">
          <h2>{t('app.repositories.title')}</h2>
          <span className="sub">{t('desktop.repos.sub', { name: server?.name ?? '', count: repositories.length })}</span>
          <div className="right">
            <Input
              className="filter-input"
              prefix={<SearchOutlined />}
              placeholder={t('desktop.repos.filterPlaceholder')}
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              allowClear
            />
            <div className="viewtoggle">
              <Tooltip title={t('desktop.repos.gridView')}>
                <button className={viewMode === 'grid' ? 'on' : ''} onClick={() => setViewMode('grid')}><AppstoreOutlined /></button>
              </Tooltip>
              <Tooltip title={t('desktop.repos.listView')}>
                <button className={viewMode === 'list' ? 'on' : ''} onClick={() => setViewMode('list')}><UnorderedListOutlined /></button>
              </Tooltip>
            </div>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>
              {t('desktop.repos.new')}
            </Button>
          </div>
        </div>

        {error && <ErrorBanner>{`${t('desktop.repos.error')}: ${error}`}</ErrorBanner>}

        <div className="repo-scroll scroll">
          {isLoading && <Spin style={{ marginTop: 40, display: 'block' }} />}
          {filtered.length === 0 && !isLoading && !error && (
            <Empty style={{ marginTop: 48 }} description={t('app.repositories.noRepos')} />
          )}
          {viewMode === 'grid' ? (
            <div className="repo-grid">
              {filtered.map((r) => {
                const primaryLang = repoPrimaryLang(r);
                return (
                  <div className="repo-card" key={r.id} onClick={() => openRepo(r)}>
                    <div className="rc-head">
                      <span className="rc-ic"><FolderOutlined /></span>
                      <b>{r.name}</b>
                      <span className={`pill ${r.is_public ? '' : 'blue'}`}>
                        {r.is_public ? t('app.repositories.visibility.public') : t('app.repositories.visibility.private')}
                      </span>
                    </div>
                    <p>{r.description || r.path}</p>
                    <div className="rc-foot">
                      <span><StarOutlined />{r.star_count}</span>
                      <span><ForkOutlined />{r.fork_count}</span>
                      {primaryLang && (
                        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                          <span style={{ width: 10, height: 10, borderRadius: '50%', background: primaryLang.color, flexShrink: 0 }} />
                          {primaryLang.name}
                        </span>
                      )}
                      <span className="rc-time">{timeAgo(r.updated_at, t)}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="repo-rows">
              {filtered.map((r) => {
                const primaryLang = repoPrimaryLang(r);
                return (
                  <div className="repo-row" key={r.id} onClick={() => openRepo(r)}>
                    <span className="rc-ic"><FolderOutlined /></span>
                    <b className="row-name">{r.name}</b>
                    <span className={`pill ${r.is_public ? '' : 'blue'}`}>
                      {r.is_public ? t('app.repositories.visibility.public') : t('app.repositories.visibility.private')}
                    </span>
                    {primaryLang && (
                      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, color: textSecondary, fontSize: 12 }}>
                        <span style={{ width: 10, height: 10, borderRadius: '50%', background: primaryLang.color, flexShrink: 0 }} />
                        {primaryLang.name}
                      </span>
                    )}
                    <span className="row-ago">{timeAgo(r.updated_at, t)}</span>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        <Modal
          open={createOpen}
          title={t('desktop.repos.newTitle')}
          okText={t('desktop.repos.new')}
          confirmLoading={creating}
          onCancel={() => setCreateOpen(false)}
          onOk={onCreate}
        >
          <div className="field">
            <label>{t('desktop.repos.createName')}</label>
            <Input
              placeholder={t('desktop.repos.createNamePh')}
              value={createName}
              onChange={(e) => setCreateName(e.target.value)}
              onPressEnter={onCreate}
            />
          </div>
          <div className="field">
            <label>{t('desktop.repos.createDesc')}</label>
            <Input.TextArea
              autoSize={{ minRows: 2, maxRows: 4 }}
              placeholder={t('desktop.repos.createDescPh')}
              value={createDesc}
              onChange={(e) => setCreateDesc(e.target.value)}
            />
          </div>
          <div className="field">
            <label>{t('desktop.repos.createVisibility')}</label>
            <Radio.Group value={createPublic} onChange={(e) => setCreatePublic(e.target.value)}>
              <Radio value>{t('desktop.repos.createVisPublic')}</Radio>
              <Radio value={false}>{t('desktop.repos.createVisPrivate')}</Radio>
            </Radio.Group>
          </div>
        </Modal>
      </div>
    );
  }

  const tabCount = (n: number | null) =>
    n != null ? <span style={{ fontSize: 11, background: '#0d1117', color: textTertiary, padding: '1px 7px', borderRadius: 10 }}>{n}</span> : null;

  const tabItems: TabsProps['items'] = [
    { key: 'code', label: <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}><FileTextOutlined style={{ fontSize: 14 }} />{t('app.repositories.tabs.code')}</span> },
    { key: 'pullRequests', label: <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}><GitPullRequestIco />{t('app.repositories.tabs.pullRequests')}{tabCount(prCount)}</span> },
    { key: 'issues', label: <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}><IssueIco />{t('app.repositories.tabs.issues')}{tabCount(issueCount)}</span> },
    { key: 'actions', label: <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}><PlayCircleOutlined style={{ fontSize: 14 }} />{t('app.repositories.tabs.actions')}</span> },
    { key: 'releases', label: <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}><RocketOutlined style={{ fontSize: 14 }} />{t('app.repositories.tabs.releases')}</span> },
    { key: 'settings', label: <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}><GearIco />{t('app.repositories.tabs.settings')}</span> },
  ];

  return (
    <Layout style={{ height: '100%', background: 'transparent', overflow: 'hidden' }}>
      <Sider
        width={280}
        style={{ background: bgSecondary, borderRight: `1px solid ${borderColor}`, flexShrink: 0, height: '100%', overflow: 'hidden' }}
        styles={{ body: { display: 'flex', flexDirection: 'column', height: '100%', minHeight: 0, overflow: 'hidden' } }}
      >
        <div style={{ padding: 16, borderBottom: `1px solid ${borderColor}` }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <h3 style={{ fontSize: 13, fontWeight: 600, margin: 0, color: textPrimary }}>{t('app.repositories.explorer')}</h3>
            <Button size="small" type="text" onClick={goBack}>{t('desktop.serverShell.back')}</Button>
          </div>
        </div>
        <div style={{ flex: 1, minHeight: 0, overflow: 'auto', padding: 8 }}>
          <RepoExplorer
            files={storeFiles}
            selectedKey={selectedTreeKey}
            onSelectFile={setSelectedTreeKey}
            onLoadDir={handleLoadDir}
            emptyText={t('app.repositories.empty.noFiles')}
          />
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
            <Tag icon={<BranchesOutlined />} style={{ fontFamily: "'JetBrains Mono', monospace" }}>
              {currentRepo.default_branch}
            </Tag>
            <div style={{ marginLeft: 'auto', display: 'flex', gap: 8 }}>
              <Button icon={<StarOutlined style={{ color: isStarred ? '#e3b341' : undefined }} />} onClick={handleStarToggle}>
                {isStarred ? t('app.repositories.actions.unstar') : t('app.repositories.actions.star')} {currentRepo.star_count}
              </Button>
              <Button icon={<ForkOutlined />} loading={forking} onClick={onFork}>
                {t('desktop.repos.fork')} {currentRepo.fork_count}
              </Button>
              <Button icon={<CloudDownloadOutlined />} loading={cloning} onClick={onClone}>
                {t('desktop.serverShell.clone')}
              </Button>
            </div>
          </div>
          <Tabs activeKey={activeTab} onChange={setActiveTab} items={tabItems}
            style={{ marginBottom: 0 }} />
          {activeTab === 'issues' && (
            <div style={{ flex: 1, minHeight: 0, padding: '16px 0 0', display: 'flex' }}>
              {selectedIssue ? (
                <IssueDetail
                  repoId={currentRepo.id}
                  issueNumber={selectedIssue.issue_number}
                  onBack={() => setSelectedIssue(null)}
                />
              ) : (
                <IssuesView repoId={currentRepo.id} onOpenIssue={setSelectedIssue} />
              )}
            </div>
          )}
          {activeTab === 'pullRequests' && (
            <div style={{ flex: 1, minHeight: 0, padding: '16px 0 0', display: 'flex' }}>
              {selectedPR ? (
                <PullRequestDetail
                  repoId={currentRepo.id}
                  prNumber={selectedPR.pr_number}
                  onBack={() => setSelectedPR(null)}
                />
              ) : (
                <PullRequestsView repoId={currentRepo.id} onOpenPR={setSelectedPR} />
              )}
            </div>
          )}
          {activeTab === 'settings' && (
            <div style={{ flex: 1, minHeight: 0, padding: '16px 0 0', display: 'flex' }}>
              <RepositorySettings repoId={currentRepo.id} />
            </div>
          )}
          {activeTab === 'actions' && (
            <div style={{ flex: 1, minHeight: 0, padding: '16px 0 0', display: 'flex' }}>
              <BuildsPanel repoId={currentRepo.id} />
            </div>
          )}
          {activeTab === 'releases' && (
            <div style={{ flex: 1, minHeight: 0, padding: '16px 0 0', display: 'flex' }}>
              <ReleasesPanel repoId={currentRepo.id} />
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
              {rootFiles.map((file, index) => (
                <div key={file.path}
                  onClick={() => { if (file.type === 'directory') { /* 目录：折叠树由左栏负责 */ return; } setSelectedTreeKey(file.path); }}
                  style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '8px 16px', borderBottom: index === rootFiles.length - 1 ? 'none' : `1px solid ${borderColor}`, fontSize: 13, cursor: 'pointer', transition: 'background 0.15s' }}
                  onMouseEnter={(e) => { e.currentTarget.style.background = hoverBg; }}
                  onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}>
                  {file.type === 'directory' ? (
                    <span style={{ width: 16, height: 16, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, fontSize: 16, color: blueLight }}>
                      <FolderOutlined />
                    </span>
                  ) : (
                    <span className={fileBadge(file.name).cls}>{fileBadge(file.name).label}</span>
                  )}
                  <span style={{ flex: 1, color: textPrimary, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{file.name}</span>
                  {file.type === 'file' && file.last_commit && (
                    <>
                      <span style={{ flex: 2, fontSize: 12, color: textSecondary, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {file.last_commit.message.split('\n')[0]}
                      </span>
                      <span style={{ fontSize: 12, color: textTertiary, flexShrink: 0 }}>{timeAgo(file.last_commit.date, t)}</span>
                    </>
                  )}
                  {file.type === 'directory' && file.sha && (
                    <span style={{ color: textTertiary, fontSize: 12 }}>{t('desktop.serverShell.defaultBranch')}</span>
                  )}
                </div>
              ))}
              {rootFiles.length === 0 && (
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
                  <Markdown>{readme}</Markdown>
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