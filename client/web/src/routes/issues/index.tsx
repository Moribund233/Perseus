import { useEffect, useMemo, useState } from 'react';
import { Layout, Button, Avatar, Tag, Modal, Form, Input, Select, Spin, message } from 'antd';
import { useParams, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { PlusOutlined, MessageOutlined, ExclamationCircleOutlined, CheckCircleOutlined } from '@ant-design/icons';
import { useRepositoriesStore } from '../../stores/repositories';
import { useIssuesStore } from '../../stores/issues';

const { Content } = Layout;

interface IssueFormValues {
  title: string;
  description?: string;
  priority?: 'low' | 'medium' | 'high' | 'critical';
}

const borderColor = '#21262d';
const hoverBg = '#1c2333';
const activeBg = 'rgba(31,111,235,0.15)';
const textSecondary = '#8b949e';
const textPrimary = '#e6edf3';
const textTertiary = '#6e7681';
const blueLight = '#58a6ff';
const bluePrimary = '#1f6feb';
const bgSecondary = '#161b22';
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

function statusIcon(status: string) {
  if (status === 'open') return <ExclamationCircleOutlined style={{ color: green, fontSize: 20 }} />;
  return <CheckCircleOutlined style={{ color: textTertiary, fontSize: 20 }} />;
}

export default function IssuesPage() {
  const { owner = '', repo = '' } = useParams();
  const navigate = useNavigate();
  const { t } = useTranslation();
  const { currentRepo, fetchRepositoryByPath } = useRepositoriesStore();
  const { issues, isLoading, error, fetchIssues, createIssue } = useIssuesStore();

  const [filter, setFilter] = useState<'open' | 'closed' | 'all'>('open');
  const [modalOpen, setModalOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [form] = Form.useForm<IssueFormValues>();

  useEffect(() => {
    if (!currentRepo && owner && repo) {
      fetchRepositoryByPath(owner, repo);
    }
  }, [owner, repo, currentRepo, fetchRepositoryByPath]);

  useEffect(() => {
    if (currentRepo) {
      fetchIssues(currentRepo.id, filter === 'all' ? undefined : filter);
    }
  }, [currentRepo?.id, filter, fetchIssues]);

  const filterCounts = useMemo(() => {
    const open = issues.filter((i) => i.status === 'open').length;
    const closed = issues.filter((i) => i.status === 'closed').length;
    return { open, closed, all: issues.length };
  }, [issues]);

  const filtered = useMemo(() => {
    if (filter === 'all') return issues;
    return issues.filter((i) => i.status === filter);
  }, [issues, filter]);

const handleCreate = async () => {
    if (!currentRepo) return;
    let values: IssueFormValues;
    try {
      values = await form.validateFields();
    } catch {
      return;
    }
    setCreating(true);
    try {
      await createIssue(currentRepo.id, {
        title: values.title,
        description: values.description,
        priority: values.priority,
      });
      message.success(t('app.issues.created'));
      setModalOpen(false);
      form.resetFields();
      fetchIssues(currentRepo.id, filter === 'all' ? undefined : filter);
    } catch (e) {
      message.error((e as Error).message || t('app.issues.creationFailed'));
    } finally {
      setCreating(false);
    }
  };

  const filterOrder: Array<'open' | 'closed' | 'all'> = ['open', 'closed', 'all'];

  return (
    <Layout style={{ height: '100%', background: 'transparent' }}>
      <Content style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
        {/* Toolbar */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px 24px', borderBottom: `1px solid ${borderColor}`, flexShrink: 0, gap: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Button
              type="text" size="small"
              onClick={() => navigate(`/repositories/${owner}/${repo}`)}
              style={{ color: blueLight, fontSize: 13 }}
            >
              ← {t('app.issues.backToRepo')}
            </Button>
            <h2 style={{ fontSize: 18, fontWeight: 700, margin: 0, color: textPrimary }}>{t('app.issues.title')}</h2>
          </div>
          <div style={{ display: 'flex', gap: 4 }}>
            {filterOrder.map((f) => {
              const isActive = filter === f;
              return (
                <button
                  key={f}
                  onClick={() => setFilter(f)}
                  style={{
                    padding: '6px 14px', borderRadius: 8, border: 'none', background: isActive ? activeBg : 'transparent',
                    color: isActive ? blueLight : textSecondary, cursor: 'pointer', fontSize: 13, fontWeight: 500,
                    display: 'flex', alignItems: 'center', gap: 6, transition: 'all 0.15s',
                  }}
                >
                  {t(`app.issues.filters.${f}`)}
                  <span style={{ background: isActive ? 'rgba(31,111,235,0.2)' : bgSecondary, color: isActive ? blueLight : textTertiary, padding: '1px 7px', borderRadius: 10, fontSize: 11 }}>
                    {filterCounts[f]}
                  </span>
                </button>
              );
            })}
          </div>
          <div style={{ display: 'flex', flexShrink: 0 }}>
            <Button type="primary" icon={<PlusOutlined style={{ fontSize: 14 }} />} onClick={() => setModalOpen(true)}
              style={{ background: bluePrimary, borderColor: bluePrimary, borderRadius: 8, fontSize: 13, height: 32, display: 'flex', alignItems: 'center', gap: 6, fontWeight: 500 }}>
              {t('app.issues.newIssue')}
            </Button>
          </div>
        </div>

        {error && <div style={{ padding: '12px 24px', color: '#f85149', fontSize: 13, borderBottom: `1px solid ${borderColor}` }}>{error}</div>}

        {/* Issue List */}
        <div style={{ flex: 1, overflow: 'auto', padding: '0 24px' }}>
          {isLoading && filtered.length === 0 && (
            <div style={{ textAlign: 'center', padding: 48 }}><Spin /></div>
          )}
          {!isLoading && filtered.length === 0 && (
            <div style={{ textAlign: 'center', padding: 48, color: textTertiary, fontSize: 14 }}>
              {t('app.issues.noIssues')}
            </div>
          )}
          {filtered.map((issue) => (
            <div
              key={issue.id}
              onClick={() => navigate(`/repositories/${owner}/${repo}/issues/${issue.issue_number}`)}
              style={{ display: 'flex', gap: 12, padding: '16px 24px', margin: '0 -24px', borderBottom: `1px solid ${borderColor}`, cursor: 'pointer', transition: 'background 0.15s', alignItems: 'flex-start' }}
              onMouseEnter={(e) => { e.currentTarget.style.background = hoverBg; }}
              onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
            >
              <div style={{ marginTop: 2, fontSize: 20, flexShrink: 0 }}>{statusIcon(issue.status)}</div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 4, display: 'flex', alignItems: 'center', gap: 8, color: textPrimary, flexWrap: 'wrap' }}>
                  {issue.title}
                  {(issue.labels || []).map((l) => (
                    <Tag key={l.id} style={{ fontSize: 10, fontWeight: 600, borderRadius: 12, background: `${l.color}22`, color: l.color, border: 'none', margin: 0, padding: '2px 8px' }}>
                      {l.name}
                    </Tag>
                  ))}
                </div>
                <div style={{ fontSize: 12, color: textTertiary }}>
                  {t('app.issues.openedBy', { id: issue.issue_number, author: issue.author?.full_name || issue.author?.username || 'Unknown', time: relativeTime(issue.created_at) })}
                </div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 16, flexShrink: 0 }}>
                {issue.comment_count != null && (
                  <span style={{ fontSize: 12, color: textTertiary, display: 'flex', alignItems: 'center', gap: 4 }}>
                    <MessageOutlined style={{ color: blueLight, fontSize: 14 }} /> {issue.comment_count}
                  </span>
                )}
                <div style={{ display: 'flex', alignItems: 'center' }}>
                  <Avatar size={24} style={{ background: getAvatarColor(getInitials(issue.author?.full_name || issue.author?.username || '?')), fontSize: 9, fontWeight: 600, border: `2px solid ${bgSecondary}` }}>
                    {getInitials(issue.author?.full_name || issue.author?.username || '?')}
                  </Avatar>
                </div>
              </div>
            </div>
          ))}
        </div>
      </Content>

      <Modal
        title={t('app.issues.newIssueModal.title')}
        open={modalOpen}
        onOk={handleCreate}
        onCancel={() => setModalOpen(false)}
        okText={t('app.issues.newIssueModal.create')}
        cancelText={t('app.issues.newIssueModal.cancel')}
        confirmLoading={creating}
        width={520}
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="title" label={t('app.issues.newIssueModal.titleLabel')} rules={[{ required: true, message: t('app.issues.newIssueModal.titleRequired') }]}>
            <Input placeholder={t('app.issues.newIssueModal.titlePlaceholder')} maxLength={255} />
          </Form.Item>
          <Form.Item name="description" label={t('app.issues.newIssueModal.description')}>
            <Input.TextArea rows={4} placeholder={t('app.issues.newIssueModal.descriptionPlaceholder')} />
          </Form.Item>
          <Form.Item name="priority" label={t('app.issues.newIssueModal.priority')} initialValue="medium">
            <Select
              options={[
                { value: 'low', label: t('app.issues.newIssueModal.priorityLow') },
                { value: 'medium', label: t('app.issues.newIssueModal.priorityMedium') },
                { value: 'high', label: t('app.issues.newIssueModal.priorityHigh') },
                { value: 'critical', label: t('app.issues.newIssueModal.priorityCritical') },
              ]}
            />
          </Form.Item>
        </Form>
      </Modal>
    </Layout>
  );
}