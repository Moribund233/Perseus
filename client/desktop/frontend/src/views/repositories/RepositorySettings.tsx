import { useEffect, useState } from 'react';
import { Button, Modal, Form, Input, Select, Switch, Checkbox, App as AntApp, Avatar, Tag, Popconfirm } from 'antd';
import { UserOutlined, LinkOutlined, PlusOutlined, DeleteOutlined, ThunderboltOutlined, ApartmentOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { TFunction } from 'i18next';
import { repositorySettingsApi, type Webhook, type RepoMember, type RepoUser } from '../../api/repositorySettings';
import { useServersStore } from '../../stores/servers';

const borderColor = '#21262d';
const hoverBg = '#1c2333';
const activeBg = 'rgba(31,111,235,0.15)';
const textSecondary = '#8b949e';
const textPrimary = '#e6edf3';
const textTertiary = '#6e7681';
const blueLight = '#58a6ff';
const bluePrimary = '#1f6feb';
const bgSecondary = '#161b22';
const bgTertiary = '#0d1117';

const WEBHOOK_EVENTS = [
  'push',
  'tag_push',
  'pull_request.opened',
  'pull_request.updated',
  'pull_request.merged',
  'pull_request.closed',
  'pull_request.reopened',
  'release.created',
  'release.published',
  'release.updated',
  'release.deleted',
  'issue.opened',
  'issue.closed',
  'issue.reopened',
  'issue.updated',
  'repository.created',
  'repository.deleted',
  'repository.forked',
] as const;

const ROLES = ['owner', 'admin', 'developer', 'readonly'] as const;

const roleColor: Record<string, string> = {
  owner: '#f85149',
  admin: '#d29922',
  developer: '#3fb950',
  readonly: '#8b949e',
};

function relativeTime(dateStr: string | null): string {
  if (!dateStr) return '';
  const now = Date.now();
  const diff = now - new Date(dateStr).getTime();
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);
  if (minutes < 1) return 'now';
  if (minutes < 60) return `${minutes}m`;
  if (hours < 24) return `${hours}h`;
  if (days < 7) return `${days}d`;
  return `${Math.floor(days / 30)}mo`;
}

interface RepositorySettingsProps {
  repoId: string;
}

export default function RepositorySettings({ repoId }: RepositorySettingsProps) {
  const { t } = useTranslation();
  const { message } = AntApp.useApp();
  const serverId = useServersStore((s) => s.servers.find((x) => x.id === s.currentServerId)?.id || '');

  const [activeSub, setActiveSub] = useState<'webhooks' | 'collaborators'>('webhooks');

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ display: 'flex', gap: 4, padding: '8px 0', flexShrink: 0 }}>
        {(['webhooks', 'collaborators'] as const).map((key) => {
          const isActive = activeSub === key;
          return (
            <button
              key={key}
              onClick={() => setActiveSub(key)}
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
              {key === 'webhooks' ? <LinkOutlined style={{ fontSize: 12 }} /> : <ApartmentOutlined style={{ fontSize: 12 }} />}
              {key === 'webhooks' ? t('app.repositorySettings.webhooks') : t('app.repositorySettings.collaborators')}
            </button>
          );
        })}
      </div>

      <div style={{ flex: 1, overflowY: 'auto', minHeight: 0 }}>
        {activeSub === 'webhooks' ? (
          <WebhooksPanel repoId={repoId} serverId={serverId} t={t} message={message} />
        ) : (
          <CollaboratorsPanel repoId={repoId} serverId={serverId} t={t} message={message} />
        )}
      </div>
    </div>
  );
}

function WebhooksPanel({ repoId, serverId, t, message }: {
  repoId: string;
  serverId: string;
  t: TFunction;
  message: ReturnType<typeof AntApp.useApp>['message'];
}) {
  const [webhooks, setWebhooks] = useState<Webhook[]>([]);
  const [loading, setLoading] = useState(false);
  const [toggling, setToggling] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [form] = Form.useForm<{ url: string; events: string[]; secret?: string }>();

  const load = async () => {
    setLoading(true);
    try {
      setWebhooks(await repositorySettingsApi.listWebhooks(serverId, repoId));
    } catch (e) {
      message.error((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [repoId, serverId]);

  const handleCreate = async () => {
    let values: { url: string; events: string[]; secret?: string };
    try {
      values = await form.validateFields();
    } catch {
      return;
    }
    setCreating(true);
    try {
      await repositorySettingsApi.createWebhook(serverId, repoId, {
        url: values.url,
        events: values.events,
        secret: values.secret || undefined,
      });
      message.success(t('app.repositorySettings.webhooksTab.created'));
      setModalOpen(false);
      form.resetFields();
      load();
    } catch (e) {
      message.error((e as Error).message);
    } finally {
      setCreating(false);
    }
  };

  const handleToggle = async (wh: Webhook) => {
    setToggling(true);
    try {
      await repositorySettingsApi.updateWebhook(serverId, repoId, wh.id, { is_active: !wh.is_active });
      load();
    } catch (e) {
      message.error((e as Error).message || t('app.repositorySettings.webhooksTab.toggleFailed'));
    } finally {
      setToggling(false);
    }
  };

  const handleDelete = async (wh: Webhook) => {
    try {
      await repositorySettingsApi.deleteWebhook(serverId, repoId, wh.id);
      message.success(t('app.repositorySettings.webhooksTab.deleted'));
      load();
    } catch (e) {
      message.error((e as Error).message);
    }
  };

  const handleTest = async (wh: Webhook) => {
    try {
      await repositorySettingsApi.testWebhook(serverId, repoId, wh.id);
      message.success(t('app.repositorySettings.webhooksTab.tested'));
    } catch (e) {
      message.error((e as Error).message);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', padding: '8px 0', flexShrink: 0 }}>
        <Button type="primary" icon={<PlusOutlined style={{ fontSize: 14 }} />} style={{ background: bluePrimary, borderColor: bluePrimary, borderRadius: 8 }} onClick={() => setModalOpen(true)}>
          {t('app.repositorySettings.webhooksTab.addWebhook')}
        </Button>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', minHeight: 0 }}>
        {webhooks.length === 0 ? (
          <div style={{ padding: 40, textAlign: 'center', color: textTertiary }}>{t('app.repositorySettings.webhooksTab.empty')}</div>
        ) : (
          webhooks.map((wh) => (
            <div key={wh.id} style={{ display: 'flex', gap: 12, padding: '12px 4px', borderBottom: `1px solid ${borderColor}`, alignItems: 'center' }}>
              <div style={{ fontSize: 16, color: blueLight, flexShrink: 0 }}><LinkOutlined /></div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 13, fontWeight: 600, color: textPrimary, wordBreak: 'break-all' }}>{wh.url}</div>
                <div style={{ fontSize: 12, color: textSecondary, marginTop: 4 }}>
                  <span style={{ fontSize: 12, color: textTertiary, marginRight: 6 }}>{t('app.repositorySettings.webhooksTab.lastTriggered')}:</span>
                  {wh.last_triggered_at ? relativeTime(wh.last_triggered_at) : t('app.repositorySettings.webhooksTab.never')}
                  {wh.last_response_status ? ` · ${wh.last_response_status}` : ''}
                </div>
                <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginTop: 6 }}>
                  {wh.events.map((ev) => (
                    <span key={ev} style={{ fontSize: 11, fontWeight: 500, borderRadius: 10, background: activeBg, color: blueLight, padding: '1px 8px' }}>{t(`app.repositorySettings.events.${ev}`)}</span>
                  ))}
                </div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
                <Switch
                  size="small"
                  checked={wh.is_active}
                  loading={toggling}
                  onChange={() => handleToggle(wh)}
                  checkedChildren={t('app.repositorySettings.webhooksTab.active')}
                  unCheckedChildren={t('app.repositorySettings.webhooksTab.inactive')}
                />
                <Button size="small" icon={<ThunderboltOutlined />} onClick={() => handleTest(wh)}>{t('app.repositorySettings.webhooksTab.test')}</Button>
                <Popconfirm
                  title={t('app.repositorySettings.webhooksTab.delete')}
                  onConfirm={() => handleDelete(wh)}
                  okText={t('app.repositorySettings.webhooksTab.delete')}
                  cancelText={t('app.repositorySettings.webhooksTab.cancel')}
                  okButtonProps={{ danger: true }}
                >
                  <Button size="small" danger icon={<DeleteOutlined />} />
                </Popconfirm>
              </div>
            </div>
          ))
        )}
      </div>

      <Modal
        title={t('app.repositorySettings.webhooksTab.createTitle')}
        open={modalOpen}
        onOk={handleCreate}
        onCancel={() => setModalOpen(false)}
        okText={t('app.repositorySettings.webhooksTab.save')}
        cancelText={t('app.repositorySettings.webhooksTab.cancel')}
        confirmLoading={creating}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="url" label={t('app.repositorySettings.webhooksTab.urlLabel')} rules={[{ required: true, message: t('app.repositorySettings.webhooksTab.urlRequired') }]}>
            <Input placeholder={t('app.repositorySettings.webhooksTab.urlPlaceholder')} />
          </Form.Item>
          <Form.Item name="events" label={t('app.repositorySettings.webhooksTab.eventsLabel')} rules={[{ required: true, message: t('app.repositorySettings.webhooksTab.eventsRequired') }]}>
            <Checkbox.Group style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              {WEBHOOK_EVENTS.map((ev) => (
                <Checkbox key={ev} value={ev}><span style={{ fontSize: 12 }}>{t(`app.repositorySettings.events.${ev}`)}</span></Checkbox>
              ))}
            </Checkbox.Group>
          </Form.Item>
          <Form.Item name="secret" label={t('app.repositorySettings.webhooksTab.secretLabel')}>
            <Input placeholder={t('app.repositorySettings.webhooksTab.secretPlaceholder')} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}

function CollaboratorsPanel({ repoId, serverId, t, message }: {
  repoId: string;
  serverId: string;
  t: TFunction;
  message: ReturnType<typeof AntApp.useApp>['message'];
}) {
  const [members, setMembers] = useState<RepoMember[]>([]);
  const [users, setUsers] = useState<RepoUser[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [adding, setAdding] = useState(false);
  const [form] = Form.useForm<{ user_id: string; role: string }>();

  const load = async () => {
    setLoading(true);
    try {
      setMembers(await repositorySettingsApi.listMembers(serverId, repoId));
    } catch (e) {
      message.error((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const openAdd = async () => {
    try {
      if (users.length === 0) {
        setUsers(await repositorySettingsApi.listUsers(serverId));
      }
    } catch (e) {
      message.error((e as Error).message);
    }
    setModalOpen(true);
  };

  useEffect(() => {
    load();
  }, [repoId, serverId]);

  const handleAdd = async () => {
    let values: { user_id: string; role: string };
    try {
      values = await form.validateFields();
    } catch {
      return;
    }
    setAdding(true);
    try {
      await repositorySettingsApi.addMember(serverId, repoId, { user_id: values.user_id, role: values.role });
      message.success(t('app.repositorySettings.collaboratorsTab.added'));
      setModalOpen(false);
      form.resetFields();
      load();
    } catch (e) {
      message.error((e as Error).message);
    } finally {
      setAdding(false);
    }
  };

  const handleRoleChange = async (member: RepoMember, role: string) => {
    try {
      await repositorySettingsApi.updateMemberRole(serverId, repoId, member.user_id, role);
      message.success(t('app.repositorySettings.collaboratorsTab.roleUpdated'));
      load();
    } catch (e) {
      message.error((e as Error).message);
    }
  };

  const handleRemove = async (member: RepoMember) => {
    try {
      await repositorySettingsApi.removeMember(serverId, repoId, member.user_id);
      message.success(t('app.repositorySettings.collaboratorsTab.removed'));
      load();
    } catch (e) {
      message.error((e as Error).message);
    }
  };

  const userOptions = users
    .filter((u) => !members.some((m) => m.user_id === u.id))
    .map((u) => ({
      value: u.id,
      label: u.full_name ? `${u.username} (${u.full_name})` : u.username,
    }));

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', padding: '8px 0', flexShrink: 0 }}>
        <Button type="primary" icon={<PlusOutlined style={{ fontSize: 14 }} />} style={{ background: bluePrimary, borderColor: bluePrimary, borderRadius: 8 }} onClick={openAdd}>
          {t('app.repositorySettings.collaboratorsTab.add')}
        </Button>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', minHeight: 0 }}>
        {members.length === 0 ? (
          <div style={{ padding: 40, textAlign: 'center', color: textTertiary }}>{t('app.repositorySettings.collaboratorsTab.empty')}</div>
        ) : (
          members.map((m) => (
            <div key={m.id} style={{ display: 'flex', gap: 12, padding: '10px 4px', borderBottom: `1px solid ${borderColor}`, alignItems: 'center' }}>
              <Avatar size={32} style={{ background: 'linear-gradient(135deg, #58a6ff, #1f6feb)', fontSize: 12, fontWeight: 600, flexShrink: 0 }} icon={<UserOutlined />}>
                {m.user?.username?.charAt(0).toUpperCase()}
              </Avatar>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 13, fontWeight: 600, color: textPrimary }}>
                  {m.user?.full_name || m.user?.username || 'Unknown'}
                </div>
                <div style={{ fontSize: 12, color: textTertiary }}>@{m.user?.username || '—'}</div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
                {m.is_active ? (
                  <Select
                    size="small"
                    value={m.role}
                    style={{ minWidth: 110 }}
                    onChange={(role) => handleRoleChange(m, role)}
                    options={ROLES.map((r) => ({ value: r, label: t(`app.repositorySettings.roles.${r}`) }))}
                  />
                ) : (
                  <Tag color="default">{t('app.repositorySettings.webhooksTab.inactive')}</Tag>
                )}
                <Tag color={roleColor[m.role] || 'default'} style={{ margin: 0 }}>{t(`app.repositorySettings.roles.${m.role}`)}</Tag>
                <Popconfirm
                  title={t('app.repositorySettings.collaboratorsTab.removeConfirm')}
                  onConfirm={() => handleRemove(m)}
                  okText={t('app.repositorySettings.collaboratorsTab.confirmRemove')}
                  cancelText={t('app.repositorySettings.collaboratorsTab.cancel')}
                  okButtonProps={{ danger: true }}
                >
                  <Button size="small" danger icon={<DeleteOutlined />} />
                </Popconfirm>
              </div>
            </div>
          ))
        )}
      </div>

      <Modal
        title={t('app.repositorySettings.collaboratorsTab.addTitle')}
        open={modalOpen}
        onOk={handleAdd}
        onCancel={() => setModalOpen(false)}
        okText={t('app.repositorySettings.collaboratorsTab.addButton')}
        cancelText={t('app.repositorySettings.collaboratorsTab.cancel')}
        confirmLoading={adding}
      >
        <Form form={form} layout="vertical" initialValues={{ role: 'developer' }}>
          <Form.Item name="user_id" label={t('app.repositorySettings.collaboratorsTab.selectUser')} rules={[{ required: true }]}>
            <Select
              showSearch
              optionFilterProp="label"
              placeholder={t('app.repositorySettings.collaboratorsTab.selectUser')}
              options={userOptions}
            />
          </Form.Item>
          <Form.Item name="role" label={t('app.repositorySettings.collaboratorsTab.selectRole')} rules={[{ required: true }]}>
            <Select options={ROLES.map((r) => ({ value: r, label: t(`app.repositorySettings.roles.${r}`) }))} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}