import { useEffect, useState } from 'react';
import { Layout, Button, Avatar, Tag, Input, Spin, App as AntApp } from 'antd';
import { useParams, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { ArrowLeftOutlined, ExclamationCircleOutlined, CheckCircleOutlined, SendOutlined } from '@ant-design/icons';
import { useRepositoriesStore } from '../../stores/repositories';
import { useIssuesStore } from '../../stores/issues';

const { Content } = Layout;

const borderColor = '#21262d';
const textSecondary = '#8b949e';
const textPrimary = '#e6edf3';
const textTertiary = '#6e7681';
const blueLight = '#58a6ff';
const bgSecondary = '#161b22';
const bgTertiary = '#1c2128';
const green = '#3fb950';

const avatarColors = ['#1f6feb', '#3fb950', '#58a6ff', '#bc8cff', '#d29922', '#f85149', '#f0883e', '#7956d9'];

function relativeTime(dateStr: string): string {
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diff = now - then;
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

function getAvatarColor(initials: string): string {
  let hash = 0;
  for (let i = 0; i < initials.length; i++) {
    hash = initials.charCodeAt(i) + ((hash << 5) - hash);
  }
  return avatarColors[Math.abs(hash) % avatarColors.length];
}

const priorityColors: Record<string, string> = {
  low: '#8b949e',
  medium: '#d29922',
  high: '#f85149',
  critical: '#f778ba',
};

export default function IssueDetailPage() {
  const { owner = '', repo = '', issueNumber = '' } = useParams();
  const navigate = useNavigate();
  const { t } = useTranslation();
  const { message } = AntApp.useApp();
  const { currentRepo, fetchRepositoryByPath } = useRepositoriesStore();
  const {
    currentIssue,
    comments,
    fetchIssue,
    fetchComments,
    createComment,
    closeIssue,
    reopenIssue,
  } = useIssuesStore();

  const num = Number(issueNumber);
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
      fetchIssue(currentRepo.id, num);
      fetchComments(currentRepo.id, num);
    }
  }, [currentRepo, num, fetchIssue, fetchComments]);

  const authorName = currentIssue?.author?.full_name || currentIssue?.author?.username || 'Unknown';

  const handleComment = async () => {
    if (!currentRepo || !body.trim()) return;
    setSubmitting(true);
    try {
      await createComment(currentRepo.id, num, body.trim());
      setBody('');
      fetchComments(currentRepo.id, num);
    } catch (e) {
      message.error((e as Error).message || t('app.issues.detail.commentFailed'));
    } finally {
      setSubmitting(false);
    }
  };

  const handleState = async () => {
    if (!currentRepo || !currentIssue) return;
    setActing(true);
    try {
      if (currentIssue.status === 'open') {
        await closeIssue(currentRepo.id, num);
      } else {
        await reopenIssue(currentRepo.id, num);
      }
    } catch (e) {
      message.error((e as Error).message);
    } finally {
      setActing(false);
    }
  };

  return (
    <Layout style={{ height: '100%', background: 'transparent' }}>
      <Content style={{ overflow: 'auto', padding: '24px 32px' }}>
        <Button type="text" icon={<ArrowLeftOutlined />} onClick={() => navigate(`/repositories/${owner}/${repo}/issues`)} style={{ color: blueLight, paddingLeft: 0, marginBottom: 16 }}>
          {t('app.issues.detail.backToIssues')}
        </Button>

        {!currentIssue ? (
          <div style={{ textAlign: 'center', padding: 48 }}><Spin /></div>
        ) : (
          <>
            <div style={{ border: `1px solid ${borderColor}`, borderRadius: 12, overflow: 'hidden', background: bgSecondary, marginBottom: 20 }}>
              <div style={{ padding: '16px 20px', background: bgTertiary, borderBottom: `1px solid ${borderColor}` }}>
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
                  <div style={{ marginTop: 2, fontSize: 22, flexShrink: 0 }}>
                    {currentIssue.status === 'open'
                      ? <ExclamationCircleOutlined style={{ color: green }} />
                      : <CheckCircleOutlined style={{ color: textTertiary }} />}
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <h2 style={{ fontSize: 20, fontWeight: 700, margin: 0, color: textPrimary, display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
                      <span style={{ color: textTertiary, fontWeight: 500 }}>#{currentIssue.issue_number}</span>
                      {currentIssue.title}
                    </h2>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginTop: 8, color: textSecondary, fontSize: 13, flexWrap: 'wrap' }}>
                      <Tag color={currentIssue.status === 'open' ? 'green' : 'default'}>
                        {currentIssue.status === 'open' ? t('app.issues.detail.open') : t('app.issues.detail.closed')}
                      </Tag>
                      {currentIssue.priority && (
                        <Tag style={{ color: priorityColors[currentIssue.priority] || textSecondary, background: `${priorityColors[currentIssue.priority]}1a`, border: 'none' }}>
                          {t(`app.issues.newIssueModal.priority${currentIssue.priority.charAt(0).toUpperCase() + currentIssue.priority.slice(1)}`)}
                        </Tag>
                      )}
                      <span>{t('app.issues.detail.openedBy', { author: authorName })} · {relativeTime(currentIssue.created_at)}</span>
                      {currentIssue.assignee && (
                        <span>· {t('app.issues.detail.assignee', { name: currentIssue.assignee.full_name || currentIssue.assignee.username })}</span>
                      )}
                      <span style={{ marginLeft: 'auto', display: 'flex', gap: 8 }}>
                        <Button size="small" type={currentIssue.status === 'open' ? 'primary' : 'default'} danger={currentIssue.status === 'open'} loading={acting} onClick={handleState}>
                          {currentIssue.status === 'open' ? t('app.issues.detail.closeIssue') : t('app.issues.detail.reopenIssue')}
                        </Button>
                      </span>
                    </div>
                  </div>
                </div>
              </div>
              <div style={{ padding: '20px' }}>
                {currentIssue.description ? (
                  <div style={{ fontSize: 14, lineHeight: 1.7, color: textPrimary, whiteSpace: 'pre-wrap' }}>{currentIssue.description}</div>
                ) : (
                  <div style={{ color: textTertiary, fontStyle: 'italic' }}>{t('app.issues.detail.noDescription')}</div>
                )}
              </div>
              <div style={{ padding: '12px 20px', background: bgTertiary, borderTop: `1px solid ${borderColor}`, display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, color: textSecondary }}>
                {(currentIssue.labels || []).length > 0 ? (currentIssue.labels as { id: string; name: string; color: string }[]).map((l) => (
                  <Tag key={l.id} style={{ fontSize: 10, fontWeight: 600, borderRadius: 12, background: `${l.color}22`, color: l.color, border: 'none', margin: 0, padding: '2px 8px' }}>{l.name}</Tag>
                )) : <span style={{ color: textTertiary }}>{t('app.issues.detail.noLabels')}</span>}
              </div>
            </div>

            {/* Comments */}
            <h3 style={{ fontSize: 15, fontWeight: 600, margin: '0 0 12px', color: textPrimary }}>
              {t('app.issues.detail.comments', { count: comments.length })}
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
            <div style={{ border: `1px solid ${borderColor}`, borderRadius: 10, overflow: 'hidden', background: bgSecondary }}>
              <div style={{ padding: '10px 16px', background: bgTertiary, borderBottom: `1px solid ${borderColor}`, fontSize: 13, color: textSecondary }}>
                {t('app.issues.detail.leaveComment')}
              </div>
              <div style={{ padding: 16 }}>
                <Input.TextArea rows={3} value={body} onChange={(e) => setBody(e.target.value)} placeholder={t('app.issues.detail.commentPlaceholder')} />
                <div style={{ marginTop: 12, display: 'flex', justifyContent: 'flex-end' }}>
                  <Button type="primary" icon={<SendOutlined />} loading={submitting} disabled={!body.trim()} onClick={handleComment}>
                    {t('app.issues.detail.submitComment')}
                  </Button>
                </div>
              </div>
            </div>
          </>
        )}
      </Content>
    </Layout>
  );
}