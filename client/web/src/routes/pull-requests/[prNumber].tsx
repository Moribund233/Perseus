import { useEffect, useState } from 'react';
import { Layout, Button, Input, Spin, Dropdown, Avatar, App as AntApp, Alert } from 'antd';
import type { ReactElement } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { ArrowLeftOutlined, PullRequestOutlined, MergeOutlined, CloseCircleOutlined, SendOutlined, DownOutlined } from '@ant-design/icons';
import { useRepositoriesStore } from '../../stores/repositories';
import { usePullRequestsStore } from '../../stores/pullRequests';

const { Content } = Layout;

const borderColor = '#21262d';
const textSecondary = '#8b949e';
const textPrimary = '#e6edf3';
const textTertiary = '#6e7681';
const blueLight = '#58a6ff';
const bgSecondary = '#161b22';
const bgTertiary = '#1c2128';
const green = '#3fb950';
const purple = '#bc8cff';
const red = '#f85149';

function relativeTime(dateStr: string): string {
  const now = Date.now();
  const diff = now - new Date(dateStr).getTime();
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);
  const weeks = Math.floor(days / 7);
  const months = Math.floor(days / 30);
  if (minutes < 1) return 'just now';
  if (minutes < 60) return `${minutes}m ago`;
  if (hours < 24) return `${hours}h ago`;
  if (days < 7) return `${days}d ago`;
  if (weeks < 5) return `${weeks}w ago`;
  return `${months}mo ago`;
}

function getInitials(name: string): string {
  return name.split(/[\s_-]/).map((n) => n[0]).join('').toUpperCase().slice(0, 2) || '?';
}

const avatarColors = ['#1f6feb', '#3fb950', '#58a6ff', '#bc8cff', '#d29922', '#f85149', '#f0883e', '#7956d9'];

function getAvatarColor(initials: string): string {
  let hash = 0;
  for (let i = 0; i < initials.length; i++) {
    hash = initials.charCodeAt(i) + ((hash << 5) - hash);
  }
  return avatarColors[Math.abs(hash) % avatarColors.length];
}

const statusConfig: Record<string, { icon: ReactElement; labelKey: string; text: string }> = {
  open: { icon: <PullRequestOutlined style={{ color: green }} />, labelKey: 'app.pullRequests.detail.open', text: green },
  merged: { icon: <MergeOutlined style={{ color: purple }} />, labelKey: 'app.pullRequests.detail.merged', text: purple },
  closed: { icon: <CloseCircleOutlined style={{ color: red }} />, labelKey: 'app.pullRequests.detail.closed', text: red },
};

export default function PullRequestDetailPage() {
  const { owner = '', repo = '', prNumber = '' } = useParams();
  const navigate = useNavigate();
  const { t } = useTranslation();
  const { message } = AntApp.useApp();
  const { currentRepo, fetchRepositoryByPath } = useRepositoriesStore();
  const {
    currentPR,
    comments,
    fetchPullRequest,
    fetchComments,
    createComment,
    closePullRequest,
    mergePullRequest,
  } = usePullRequestsStore();

  const num = Number(prNumber);
  const [body, setBody] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [acting, setActing] = useState(false);

  useEffect(() => {
    if (!currentRepo && owner && repo) {
      fetchRepositoryByPath(owner, repo);
    }
  }, [owner, repo, currentRepo, fetchRepositoryByPath]);

  useEffect(() => {
    if (currentRepo) {
      fetchPullRequest(currentRepo.id, num);
      fetchComments(currentRepo.id, num);
    }
  }, [currentRepo?.id, num, fetchPullRequest, fetchComments]);

  const authorName = currentPR?.author?.full_name || currentPR?.author?.username || 'Unknown';

  const status = currentPR?.status || 'open';
  const statusCfg = statusConfig[status] || statusConfig.open;

  const handleComment = async () => {
    if (!currentRepo || !body.trim()) return;
    setSubmitting(true);
    try {
      await createComment(currentRepo.id, num, { content: body.trim() });
      setBody('');
      fetchComments(currentRepo.id, num);
    } catch (e) {
      message.error((e as Error).message || t('app.pullRequests.detail.commentFailed'));
    } finally {
      setSubmitting(false);
    }
  };

  const handleClose = async () => {
    if (!currentRepo || !currentPR) return;
    setActing(true);
    try {
      await closePullRequest(currentRepo.id, num);
    } catch (e) {
      message.error((e as Error).message);
    } finally {
      setActing(false);
    }
  };

  const handleMerge = async (method?: 'merge' | 'squash' | 'rebase') => {
    if (!currentRepo || !currentPR) return;
    setActing(true);
    try {
      await mergePullRequest(currentRepo.id, num, method);
    } catch (e) {
      message.error((e as Error).message);
    } finally {
      setActing(false);
    }
  };

  const mergeItems = [
    { key: 'merge', label: t('app.pullRequests.detail.mergeMerge') },
    { key: 'squash', label: t('app.pullRequests.detail.mergeSquash') },
    { key: 'rebase', label: t('app.pullRequests.detail.mergeRebase') },
  ];

  return (
    <Layout style={{ height: '100%', background: 'transparent' }}>
      <Content style={{ overflow: 'auto', padding: '24px 32px' }}>
        <Button type="text" icon={<ArrowLeftOutlined />} onClick={() => navigate(`/repositories/${owner}/${repo}/pulls`)} style={{ color: blueLight, paddingLeft: 0, marginBottom: 16 }}>
          {t('app.pullRequests.detail.backToPullRequests')}
        </Button>

        {!currentPR ? (
          <div style={{ textAlign: 'center', padding: 48 }}><Spin /></div>
        ) : (
          <>
            <div style={{ border: `1px solid ${borderColor}`, borderRadius: 12, overflow: 'hidden', background: bgSecondary, marginBottom: 20 }}>
              <div style={{ padding: '16px 20px', background: bgTertiary, borderBottom: `1px solid ${borderColor}` }}>
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
                  <div style={{ marginTop: 2, fontSize: 22, flexShrink: 0 }}>{statusCfg.icon}</div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <h2 style={{ fontSize: 20, fontWeight: 700, margin: 0, color: textPrimary, display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
                      <span style={{ color: textTertiary, fontWeight: 500 }}>#{currentPR.pr_number}</span>
                      {currentPR.title}
                    </h2>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginTop: 8, color: textSecondary, fontSize: 13, flexWrap: 'wrap' }}>
                      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, border: `1px solid ${statusCfg.text}66`, borderRadius: 14, padding: '2px 12px', color: statusCfg.text, fontWeight: 600, fontSize: 12 }}>
                        {statusCfg.icon} {t(statusCfg.labelKey)}
                      </span>
                      <span>
                        <span style={{ color: blueLight, fontWeight: 500 }}>{currentPR.source_branch}</span>
                        {' → '}
                        <span style={{ color: textPrimary, fontWeight: 500 }}>{currentPR.target_branch}</span>
                      </span>
                      <span>{t('app.pullRequests.detail.openedByPR', { author: authorName })} · {relativeTime(currentPR.created_at)}</span>
                      <span style={{ marginLeft: 'auto', display: 'flex', gap: 8 }}>
                        {currentPR.status === 'open' && (
                          <>
                            <Button size="small" danger onClick={handleClose} loading={acting} disabled={acting}>
                              {t('app.pullRequests.detail.closePR')}
                            </Button>
                            <Dropdown
                              menu={{ items: mergeItems, onClick: ({ key }) => handleMerge(key as 'merge' | 'squash' | 'rebase') }}
                              disabled={acting}
                            >
                              <Button size="small" type="primary" loading={acting && status !== 'closed'} icon={<MergeOutlined />}>
                                <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                                  {t('app.pullRequests.detail.mergePR')} <DownOutlined style={{ fontSize: 10 }} />
                                </span>
                              </Button>
                            </Dropdown>
                          </>
                        )}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
              <div style={{ padding: '20px' }}>
                {currentPR.description ? (
                  <div style={{ fontSize: 14, lineHeight: 1.7, color: textPrimary, whiteSpace: 'pre-wrap' }}>{currentPR.description}</div>
                ) : (
                  <div style={{ color: textTertiary, fontStyle: 'italic' }}>{t('app.pullRequests.detail.noDescription')}</div>
                )}
              </div>
              {(currentPR.labels || []).length > 0 && (
                <div style={{ padding: '12px 20px', background: bgTertiary, borderTop: `1px solid ${borderColor}`, display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, color: textSecondary }}>
                  {(currentPR.labels as { id: string; name: string; color: string }[]).map((l) => (
                    <span key={l.id} style={{ fontSize: 10, fontWeight: 600, borderRadius: 12, background: `${l.color}22`, color: l.color, border: 'none', padding: '2px 8px' }}>{l.name}</span>
                  ))}
                </div>
              )}
            </div>

            {/* Comments */}
            <h3 style={{ fontSize: 15, fontWeight: 600, margin: '0 0 12px', color: textPrimary }}>
              {t('app.pullRequests.detail.comments', { count: comments.length })}
            </h3>
            {comments.map((c) => (
              <div key={c.id} style={{ border: `1px solid ${borderColor}`, borderRadius: 12, overflow: 'hidden', background: bgSecondary, marginBottom: 12 }}>
                <div style={{ padding: '10px 16px', background: bgTertiary, borderBottom: `1px solid ${borderColor}`, display: 'flex', alignItems: 'center', gap: 10, fontSize: 13 }}>
                  <Avatar size={22} style={{ background: getAvatarColor(getInitials(c.author?.full_name || c.author?.username || '?')), fontSize: 9, fontWeight: 600 }}>
                    {getInitials(c.author?.full_name || c.author?.username || '?')}
                  </Avatar>
                  <strong style={{ color: textPrimary }}>{c.author?.full_name || c.author?.username || 'Unknown'}</strong>
                  <span style={{ color: textTertiary }}>· {relativeTime(c.created_at)}</span>
                </div>
                <div style={{ padding: '12px 16px', fontSize: 14, color: textPrimary, whiteSpace: 'pre-wrap' }}>{c.content}</div>
              </div>
            ))}

            {/* Comment input */}
            {currentPR.status === 'open' ? (
              <div style={{ border: `1px solid ${borderColor}`, borderRadius: 10, overflow: 'hidden', background: bgSecondary }}>
                <div style={{ padding: '10px 16px', background: bgTertiary, borderBottom: `1px solid ${borderColor}`, fontSize: 13, color: textSecondary }}>
                  {t('app.pullRequests.detail.leaveComment')}
                </div>
                <div style={{ padding: 16 }}>
                  <Input.TextArea rows={3} value={body} onChange={(e) => setBody(e.target.value)} placeholder={t('app.pullRequests.detail.commentPlaceholder')} />
                  <div style={{ marginTop: 12, display: 'flex', justifyContent: 'flex-end' }}>
                    <Button type="primary" icon={<SendOutlined />} loading={submitting} disabled={!body.trim()} onClick={handleComment}>
                      {t('app.pullRequests.detail.submitComment')}
                    </Button>
                  </div>
                </div>
              </div>
            ) : (
              <Alert type="info" showIcon message={t('app.pullRequests.detail.threadClosed')} style={{ background: bgSecondary, borderColor: borderColor }} />
            )}
          </>
        )}
      </Content>
    </Layout>
  );
}