import { useEffect, useState } from 'react';
import { Button, Spin, Modal, Form, Select, Input, App as AntApp } from 'antd';
import { useTranslation } from 'react-i18next';
import { PlusOutlined, ExclamationCircleOutlined, CheckCircleOutlined } from '@ant-design/icons';
import { useIssuesStore } from '../../stores/issues';
import type { Issue } from '../../api/issues';

const borderColor = '#21262d';
const hoverBg = '#1c2333';
const activeBg = 'rgba(31,111,235,0.15)';
const textSecondary = '#8b949e';
const textPrimary = '#e6edf3';
const textTertiary = '#6e7681';
const blueLight = '#58a6ff';
const bluePrimary = '#1f6feb';
const bgSecondary = '#161b22';

const priorityColors: Record<string, string> = {
  low: '#8b949e',
  medium: '#d29922',
  high: '#f85149',
  critical: '#f778ba',
};

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

interface IssuesViewProps {
  repoId: string;
  onOpenIssue: (issue: Issue) => void;
}

export default function IssuesView({ repoId, onOpenIssue }: IssuesViewProps) {
  const { t } = useTranslation();
  const { message } = AntApp.useApp();
  const { issues, isLoading, fetchIssues, createIssue } = useIssuesStore();
  const [filter, setFilter] = useState<'open' | 'closed' | 'all'>('open');
  const [modalOpen, setModalOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [form] = Form.useForm<{ title: string; description?: string; priority?: 'low' | 'medium' | 'high' | 'critical' }>();

  useEffect(() => {
    fetchIssues(repoId);
  }, [repoId, fetchIssues]);

  const filterCounts = {
    open: issues.filter((i) => i.status === 'open').length,
    closed: issues.filter((i) => i.status === 'closed').length,
    all: issues.length,
  };
  const filterOrder: Array<'open' | 'closed' | 'all'> = ['open', 'closed', 'all'];
  const filtered = issues.filter((i) => filter === 'all' || i.status === filter);

  const handleCreate = async () => {
    let values: { title: string; description?: string; priority?: 'low' | 'medium' | 'high' | 'critical' };
    try {
      values = await form.validateFields();
    } catch {
      return;
    }
    setCreating(true);
    try {
      await createIssue(repoId, values);
      message.success(t('app.issues.created'));
      setModalOpen(false);
      form.resetFields();
    } catch (e) {
      message.error((e as Error).message || t('app.issues.creationFailed'));
    } finally {
      setCreating(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '8px 0', gap: 16, flexShrink: 0 }}>
        <div style={{ display: 'flex', gap: 4 }}>
          {filterOrder.map((f) => {
            const isActive = filter === f;
            return (
              <button
                key={f}
                onClick={() => setFilter(f)}
                style={{
                  padding: '6px 14px',
                  borderRadius: 8,
                  border: 'none',
                  background: isActive ? activeBg : 'transparent',
                  color: isActive ? blueLight : textSecondary,
                  cursor: 'pointer',
                  fontSize: 13,
                  fontWeight: 500,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                  transition: 'all 0.15s',
                }}
                onMouseEnter={(e) => {
                  if (!isActive) { e.currentTarget.style.background = hoverBg; e.currentTarget.style.color = textPrimary; }
                }}
                onMouseLeave={(e) => {
                  if (!isActive) { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = textSecondary; }
                }}
              >
                {f === 'open' && <ExclamationCircleOutlined style={{ fontSize: 12, color: '#3fb950' }} />}
                {f === 'closed' && <CheckCircleOutlined style={{ fontSize: 12 }} />}
                {t(`app.issues.filters.${f}`)}
                <span style={{ background: isActive ? 'rgba(31,111,235,0.2)' : bgSecondary, color: isActive ? blueLight : textTertiary, padding: '1px 7px', borderRadius: 10, fontSize: 11 }}>{filterCounts[f]}</span>
              </button>
            );
          })}
        </div>
        <Button type="primary" icon={<PlusOutlined style={{ fontSize: 14 }} />} style={{ background: bluePrimary, borderColor: bluePrimary, borderRadius: 8 }}>
          {t('app.issues.newIssue')}
        </Button>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', minHeight: 0 }}>
        {filtered.length === 0 ? (
          <div style={{ padding: 40, textAlign: 'center', color: textTertiary }}>{t('app.issues.noIssues')}</div>
        ) : (
          filtered.map((issue) => (
            <div
              key={issue.id}
              onClick={() => onOpenIssue(issue)}
              style={{ display: 'flex', gap: 12, padding: '14px 4px', borderBottom: `1px solid ${borderColor}`, cursor: 'pointer', transition: 'background 0.15s', alignItems: 'flex-start' }}
              onMouseEnter={(e) => { e.currentTarget.style.background = hoverBg; }}
              onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
            >
              <div style={{ marginTop: 2, fontSize: 18, flexShrink: 0 }}>
                {issue.status === 'open' ? <ExclamationCircleOutlined style={{ color: '#3fb950' }} /> : <CheckCircleOutlined style={{ color: textTertiary }} />}
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 4, color: textPrimary, display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                  {issue.title}
                  <span style={{ color: textTertiary, fontWeight: 400, fontSize: 12 }}>#{issue.issue_number}</span>
                  {issue.priority && (
                    <span style={{ fontSize: 10, fontWeight: 600, borderRadius: 12, background: `${priorityColors[issue.priority]}22`, color: priorityColors[issue.priority], padding: '2px 8px' }}>
                      {t(`app.issues.newIssueModal.priority${issue.priority.charAt(0).toUpperCase() + issue.priority.slice(1)}`)}
                    </span>
                  )}
                </div>
                <div style={{ fontSize: 12, color: textTertiary }}>
                  {t('app.issues.openedBy', { id: issue.issue_number, author: issue.author?.full_name || issue.author?.username || 'Unknown', time: relativeTime(issue.created_at) })}
                </div>
              </div>
              <div style={{ fontSize: 12, color: textTertiary, flexShrink: 0 }}>
                {issue.comment_count ?? 0}
              </div>
            </div>
          ))
        )}
      </div>

      <Modal
        title={t('app.issues.newIssueModal.title')}
        open={modalOpen}
        onOk={handleCreate}
        onCancel={() => setModalOpen(false)}
        okText={t('app.issues.newIssueModal.create')}
        cancelText={t('app.issues.newIssueModal.cancel')}
        confirmLoading={creating}
      >
        <Form form={form} layout="vertical">
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
    </div>
  );
}