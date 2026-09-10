import { useEffect, useRef, useState } from 'react';
import { Empty, Input, Modal, Spin, Tag } from 'antd';
import {
  FileTextOutlined,
  FolderOutlined,
  LoadingOutlined,
  SearchOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { globalSearchApi, type GlobalIssueHit, type GlobalPRHit, type GlobalRepoHit, type GlobalSearchResponse } from '../api/search';
import { useServersStore } from '../stores/servers';
import { useRepositoriesStore } from '../stores/repositories';
import { useNavigationStore } from '../stores/navigation';

const borderColor = '#21262d';
const hoverBg = '#1c2333';
const textPrimary = '#e6edf3';
const textSecondary = '#8b949e';
const textTertiary = '#6e7681';
const blueLight = '#58a6ff';
const bgSecondary = '#161b22';

const statusColor: Record<string, string> = {
  open: 'blue',
  closed: 'default',
  merged: 'purple',
};

function statusTag(t: (k: string) => string, status: string) {
  return <Tag color={statusColor[status] ?? 'default'}>{t(`desktop.portal.search.status.${status}`) || status}</Tag>;
}

export default function GlobalSearchView({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { t } = useTranslation();
  const serverId = useServersStore((s) => s.currentServerId);
  const setPendingOpen = useRepositoriesStore((s) => s.setPendingOpen);
  const navigate = useNavigationStore((s) => s.navigate);

  const [query, setQuery] = useState('');
  const [results, setResults] = useState<GlobalSearchResponse | null>(null);
  const [searching, setSearching] = useState(false);
  const [failed, setFailed] = useState(false);
  const [searched, setSearched] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const trimmed = query.trim();

  // 打开时聚焦输入框。
  useEffect(() => {
    if (open) {
      setResults(null);
      setFailed(false);
      setSearched(false);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [open]);

  // 防抖搜索：输入停止 350ms 后请求聚合端点（与 web 端 GlobalSearch 语义一致）。
  useEffect(() => {
    let cancelled = false;
    if (trimmed.length < 2) {
      setResults(null);
      setSearched(false);
      setSearching(false);
      return;
    }
    setSearching(true);
    setFailed(false);
    const timer = setTimeout(async () => {
      if (!serverId) return;
      try {
        const res = await globalSearchApi.search(serverId, trimmed, { per_type: 10 });
        if (!cancelled) {
          setResults(res);
          setSearched(true);
        }
      } catch {
        if (!cancelled) setFailed(true);
      } finally {
        if (!cancelled) setSearching(false);
      }
    }, 350);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [trimmed, serverId]);

  const openDeepLink = (link: { repoPath: string; tab?: 'issues' | 'pullRequests'; issueNumber?: number; prNumber?: number }) => {
    setPendingOpen(link);
    navigate('repositories');
    onClose();
  };

  const openRepoResult = (r: GlobalRepoHit) => openDeepLink({ repoPath: r.path });
  const openIssueResult = (i: GlobalIssueHit) =>
    openDeepLink({ repoPath: i.repository_path, tab: 'issues', issueNumber: i.issue_number });
  const openPRResult = (p: GlobalPRHit) =>
    openDeepLink({ repoPath: p.repository_path, tab: 'pullRequests', prNumber: p.pr_number });

  const hasResults = !!results && (results.repositories.length > 0 || results.issues.length > 0 || results.pull_requests.length > 0);

  const rowStyle: React.CSSProperties = {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    padding: '8px 12px',
    borderRadius: 6,
    cursor: 'pointer',
    fontSize: 13,
    color: textPrimary,
  };

  const renderRow = (key: string, icon: React.ReactNode, main: React.ReactNode, sub: React.ReactNode, onClick: () => void) => (
    <div
      key={key}
      style={rowStyle}
      onClick={onClick}
      onMouseEnter={(e) => { e.currentTarget.style.background = hoverBg; }}
      onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
    >
      <span style={{ color: blueLight, display: 'flex', flexShrink: 0 }}>{icon}</span>
      <span style={{ flex: 1, minWidth: 0, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{main}</span>
      <span style={{ color: textTertiary, fontSize: 12, flexShrink: 0, maxWidth: '40%', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{sub}</span>
    </div>
  );

  const section = (title: string, rows: React.ReactNode[]) =>
    rows.length > 0 && (
      <div style={{ marginBottom: 8 }}>
        <div style={{ fontSize: 11, fontWeight: 600, color: textSecondary, textTransform: 'uppercase', letterSpacing: 1, padding: '8px 12px 4px' }}>{title}</div>
        {rows}
      </div>
    );

  return (
    <Modal
      open={open}
      onCancel={onClose}
      footer={null}
      width={640}
      closable={false}
      styles={{ body: { padding: 0 } }}
    >
      <div style={{ background: bgSecondary, border: `1px solid ${borderColor}`, borderRadius: 8, overflow: 'hidden' }}>
      <div style={{ padding: '12px 16px', borderBottom: `1px solid ${borderColor}`, display: 'flex', alignItems: 'center', gap: 8 }}>
        <SearchOutlined style={{ color: textSecondary }} />
        <Input
          ref={inputRef as never}
          variant="borderless"
          placeholder={t('desktop.portal.search.placeholder')}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          style={{ fontSize: 15, color: textPrimary }}
          allowClear
        />
        {searching && <LoadingOutlined style={{ color: textSecondary }} />}
      </div>

      <div className="scroll" style={{ maxHeight: 420, overflowY: 'auto', padding: '8px 8px 12px' }}>
        {!trimmed || trimmed.length < 2 ? (
          <div style={{ padding: '28px 0', textAlign: 'center', color: textTertiary, fontSize: 13 }}>{t('desktop.portal.search.hint')}</div>
        ) : searching && !results ? (
          <div style={{ padding: '28px 0', textAlign: 'center' }}><Spin /></div>
        ) : failed ? (
          <div style={{ padding: '28px 0', textAlign: 'center', color: '#f85149', fontSize: 13 }}>{t('desktop.portal.search.failed')}</div>
        ) : !hasResults ? (
          searched ? (
            <Empty style={{ padding: '20px 0' }} description={t('desktop.portal.search.empty')} image={Empty.PRESENTED_IMAGE_SIMPLE} />
          ) : null
        ) : (
          <>
            {section(
              t('desktop.portal.search.groupRepos'),
              results!.repositories.map((r) =>
                renderRow(
                  `repo-${r.repository_id}`,
                  <FolderOutlined />,
                  <span><b>{r.name}</b>{r.is_public === false && <Tag color="blue" style={{ marginLeft: 8 }}>{t('app.repositories.visibility.private')}</Tag>}</span>,
                  r.description || r.path,
                  () => openRepoResult(r),
                ),
              ),
            )}
            {section(
              t('desktop.portal.search.groupIssues'),
              results!.issues.map((i) =>
                renderRow(
                  `issue-${i.repository_id}-${i.issue_number}`,
                  <FileTextOutlined />,
                  <span>#{i.issue_number} {i.title} {statusTag(t, i.status)}</span>,
                  i.repository_name,
                  () => openIssueResult(i),
                ),
              ),
            )}
            {section(
              t('desktop.portal.search.groupPRs'),
              results!.pull_requests.map((p) =>
                renderRow(
                  `pr-${p.repository_id}-${p.pr_number}`,
                  <FileTextOutlined />,
                  <span>#{p.pr_number} {p.title} {statusTag(t, p.status)}</span>,
                  p.repository_name,
                  () => openPRResult(p),
                ),
              ),
            )}
          </>
        )}
      </div>
      </div>
    </Modal>
  );
}
