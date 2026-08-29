import { useCallback, useEffect, useState, type CSSProperties, type ReactNode } from 'react';
import {
  Button, Input, Select, Switch, Modal, Tag, Popconfirm, Empty, Spin, message,
} from 'antd';
import {
  SettingOutlined, TeamOutlined, ApiOutlined, UserAddOutlined, DeleteOutlined,
  ExperimentOutlined, HistoryOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { repositoriesApi, type Repository, type RepoMember, type RepoBranch } from '../../api/repositories';
import { webhooksApi, type Webhook, type WebhookDelivery } from '../../api/webhooks';
import { useAuthStore } from '../../stores/auth';
import { useRepositoriesStore } from '../../stores/repositories';

const textPrimary = '#e6edf3';
const textSecondary = '#8b949e';
const textTertiary = '#6e7681';
const borderColor = '#21262d';
const bgSecondary = '#161b22';
const bgTertiary = '#1c2128';
const blue = '#58a6ff';
const green = '#3fb950';

const SECTION_GAP: CSSProperties = {
  border: `1px solid ${borderColor}`,
  borderRadius: 12,
  background: bgSecondary,
  marginBottom: 16,
  overflow: 'hidden',
};

function SectionHeader({ icon, title, extra }: { icon: ReactNode; title: string; extra?: ReactNode }) {
  return (
    <div
      style={{
        padding: '12px 16px',
        background: bgTertiary,
        borderBottom: `1px solid ${borderColor}`,
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        fontSize: 14,
        fontWeight: 600,
        color: textPrimary,
      }}
    >
      <span style={{ color: blue, display: 'flex', alignItems: 'center' }}>{icon}</span>
      {title}
      <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 8 }}>{extra}</div>
    </div>
  );
}

const villageEvents = [
  'push', 'pull_request', 'pull_request_review', 'issues', 'issue_comment',
  'release', 'star', 'fork', 'build',
];

export default function RepoSettingsTab({ repoId }: { repoId: string }) {
  const { t } = useTranslation();
  const currentUser = useAuthStore((s) => s.user);
  const updateRepository = useRepositoriesStore((s) => s.updateRepository);

  // ---- Repo info ----
  const [repo, setRepo] = useState<Repository | null>(null);
  const [branches, setBranches] = useState<RepoBranch[]>([]);
  const [savingInfo, setSavingInfo] = useState(false);
  const [description, setDescription] = useState('');
  const [isPublic, setIsPublic] = useState(true);
  const [defaultBranch, setDefaultBranch] = useState('');

  // ---- Members ----
  const [members, setMembers] = useState<RepoMember[]>([]);
  const [membersLoading, setMembersLoading] = useState(true);
  const [addModal, setAddModal] = useState(false);
  const [memberUserId, setMemberUserId] = useState('');
  const [memberRole, setMemberRole] = useState('developer');
  const [savingMember, setSavingMember] = useState(false);

  // ---- Webhooks ----
  const [webhooks, setWebhooks] = useState<Webhook[]>([]);
  const [whLoading, setWhLoading] = useState(true);
  const [whModal, setWhModal] = useState(false);
  const [whEditing, setWhEditing] = useState<Webhook | null>(null);
  const [savingWh, setSavingWh] = useState(false);
  const [whUrl, setWhUrl] = useState('');
  const [whEvents, setWhEvents] = useState<string[]>(['push']);
  const [whSecret, setWhSecret] = useState('');
  const [whActive, setWhActive] = useState(true);
  // deliveries
  const [deliveries, setDeliveries] = useState<WebhookDelivery[]>([]);
  const [deliveriesOpen, setDeliveriesOpen] = useState(false);
  const [deliveriesFor, setDeliveriesFor] = useState<Webhook | null>(null);
  const [deliveriesLoading, setDeliveriesLoading] = useState(false);

  const loadRepo = useCallback(async () => {
    try {
      const data = await repositoriesApi.get(repoId);
      setRepo(data);
      setDescription(data.description);
      setIsPublic(data.is_public);
      setDefaultBranch(data.default_branch);
    } catch { /* noop */ }
  }, [repoId]);

  const loadBranches = useCallback(async () => {
    try {
      setBranches(await repositoriesApi.getBranches(repoId));
    } catch { /* noop */ }
  }, [repoId]);

  const loadMembers = useCallback(async () => {
    try {
      setMembers(await repositoriesApi.getMembers(repoId));
    } catch { /* noop */ } finally {
      setMembersLoading(false);
    }
  }, [repoId]);

  const loadWebhooks = useCallback(async () => {
    try {
      setWebhooks(await webhooksApi.list(repoId));
    } catch { /* noop */ } finally {
      setWhLoading(false);
    }
  }, [repoId]);

  useEffect(() => {
    // 微任务延迟, 避免在 effect 同步体中触发级联渲染
    Promise.resolve().then(loadRepo);
    Promise.resolve().then(loadBranches);
    Promise.resolve().then(loadMembers);
    Promise.resolve().then(loadWebhooks);
  }, [loadRepo, loadBranches, loadMembers, loadWebhooks]);

  const saveRepo = async () => {
    setSavingInfo(true);
    try {
      await updateRepository(repoId, { description, is_public: isPublic, default_branch: defaultBranch });
      message.success(t('app.repositories.settings.general.saved'));
      loadRepo();
    } catch {
      message.error(t('app.repositories.settings.general.saveFailed'));
    } finally {
      setSavingInfo(false);
    }
  };

  const addMember = async () => {
    if (!memberUserId) return;
    setSavingMember(true);
    try {
      await repositoriesApi.addMember(repoId, { user_id: memberUserId, role: memberRole });
      message.success(t('app.repositories.settings.members.added'));
      setAddModal(false);
      setMemberUserId('');
      loadMembers();
    } catch {
      message.error(t('app.repositories.settings.members.addFailed'));
    } finally {
      setSavingMember(false);
    }
  };

  const changeMemberRole = async (userId: string, role: string) => {
    try {
      await repositoriesApi.updateMember(repoId, userId, { role });
      message.success(t('app.repositories.settings.members.updated'));
      loadMembers();
    } catch {
      message.error(t('app.repositories.settings.members.updateFailed'));
    }
  };

  const removeMember = async (userId: string) => {
    try {
      await repositoriesApi.removeMember(repoId, userId);
      message.success(t('app.repositories.settings.members.removed'));
      loadMembers();
    } catch {
      message.error(t('app.repositories.settings.members.removeFailed'));
    }
  };

  const openCreateWebhook = () => {
    setWhEditing(null);
    setWhUrl('');
    setWhEvents(['push']);
    setWhSecret('');
    setWhActive(true);
    setWhModal(true);
  };

  const openEditWebhook = (wh: Webhook) => {
    setWhEditing(wh);
    setWhUrl(wh.url);
    setWhEvents(wh.events);
    setWhSecret(wh.secret);
    setWhActive(wh.is_active);
    setWhModal(true);
  };

  const saveWebhook = async () => {
    if (!whUrl) return;
    setSavingWh(true);
    try {
      if (whEditing) {
        await webhooksApi.update(repoId, whEditing.id, {
          url: whUrl, events: whEvents, secret: whSecret || undefined, is_active: whActive,
        });
      } else {
        await webhooksApi.create(repoId, { url: whUrl, events: whEvents, secret: whSecret || undefined, is_active: whActive });
      }
      message.success(t('app.repositories.settings.webhooks.saved'));
      setWhModal(false);
      loadWebhooks();
    } catch {
      message.error(t('app.repositories.settings.webhooks.saveFailed'));
    } finally {
      setSavingWh(false);
    }
  };

  const deleteWebhook = async (wh: Webhook) => {
    try {
      await webhooksApi.delete(repoId, wh.id);
      message.success(t('app.repositories.settings.webhooks.deleted'));
      loadWebhooks();
    } catch {
      message.error(t('app.repositories.settings.webhooks.deleteFailed'));
    }
  };

  const testWebhook = async (wh: Webhook) => {
    try {
      const res = await webhooksApi.test(repoId, wh.id);
      message.success(`${t('app.repositories.settings.webhooks.tested')} (${res.status_code ?? '—'})`);
    } catch {
      message.error(t('app.repositories.settings.webhooks.testFailed'));
    }
  };

  const openDeliveries = async (wh: Webhook) => {
    setDeliveriesFor(wh);
    setDeliveriesOpen(true);
    setDeliveriesLoading(true);
    setDeliveries([]);
    try {
      setDeliveries(await webhooksApi.listDeliveries(repoId, wh.id));
    } catch { /* noop */ } finally {
      setDeliveriesLoading(false);
    }
  };

  const isOwnerOrAdmin =
    currentUser && repo && (repo.owner_id === currentUser.id ||
      members.some((m) => m.user_id === currentUser.id && (m.role === 'owner' || m.role === 'admin')));

  return (
    <div>
      {!repo ? (
        <div style={{ textAlign: 'center', padding: 48 }}><Spin /></div>
      ) : (
        <div style={{ maxWidth: 760 }}>
          {/* General */}
          <div style={SECTION_GAP}>
            <SectionHeader icon={<SettingOutlined />} title={t('app.repositories.settings.general.title')} />
            <div style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 16 }}>
              <div>
                <label style={{ fontSize: 13, color: textSecondary, marginBottom: 6, display: 'block' }}>{t('app.repositories.settings.general.description')}</label>
                <Input.TextArea
                  rows={3}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder={t('app.repositories.settings.general.descriptionPlaceholder')}
                />
              </div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16 }}>
                <div>
                  <div style={{ fontSize: 13, color: textSecondary }}>{t('app.repositories.settings.general.visibility')}</div>
                  <div style={{ fontSize: 12, color: textTertiary }}>{t('app.repositories.settings.general.visibilityHint')}</div>
                </div>
                <Switch checked={isPublic} onChange={setIsPublic} checkedChildren={t('app.repositories.visibility.public')} unCheckedChildren={t('app.repositories.visibility.private')} />
              </div>
              <div>
                <label style={{ fontSize: 13, color: textSecondary, marginBottom: 6, display: 'block' }}>{t('app.repositories.settings.general.defaultBranch')}</label>
                <Select
                  value={defaultBranch}
                  onChange={setDefaultBranch}
                  style={{ width: 260 }}
                  options={branches.map((b) => ({ value: b.name, label: b.name }))}
                  placeholder={t('app.repositories.settings.general.defaultBranch')}
                />
              </div>
              <div>
                <Button type="primary" loading={savingInfo} onClick={saveRepo}>
                  {t('app.repositories.settings.general.save')}
                </Button>
              </div>
            </div>
          </div>

          {/* Collaborators */}
          <div style={SECTION_GAP}>
            <SectionHeader
              icon={<TeamOutlined />}
              title={t('app.repositories.settings.members.title')}
              extra={<Button size="small" type="primary" icon={<UserAddOutlined />} disabled={!isOwnerOrAdmin} onClick={() => setAddModal(true)}>{t('app.repositories.settings.members.add')}</Button>}
            />
            <div style={{ padding: 8 }}>
              {membersLoading ? (
                <div style={{ textAlign: 'center', padding: 24 }}><Spin /></div>
              ) : members.length === 0 ? (
                <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={<span style={{ color: textSecondary }}>{t('app.repositories.settings.members.empty')}</span>} style={{ padding: 24 }} />
              ) : (
                members.map((m) => (
                  <div
                    key={m.user_id}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 12,
                      padding: '10px 12px',
                      borderRadius: 8,
                    }}
                    onMouseEnter={(e) => { e.currentTarget.style.background = '#1c2333'; }}
                    onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
                  >
                    <span style={{ width: 28, height: 28, borderRadius: '50%', background: 'linear-gradient(135deg,#58a6ff,#1f6feb)', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12, fontWeight: 600, flexShrink: 0 }}>
                      {(m.user?.username ?? '?').charAt(0).toUpperCase()}
                    </span>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: 13, color: textPrimary, fontWeight: 500 }}>{m.user?.username ?? m.user_id}</div>
                      <div style={{ fontSize: 12, color: textTertiary }}>{m.user?.full_name}</div>
                    </div>
                    <Select
                      size="small"
                      value={m.role}
                      disabled={!isOwnerOrAdmin}
                      onChange={(role) => changeMemberRole(m.user_id, role)}
                      style={{ width: 120 }}
                      options={[
                        { value: 'owner', label: 'Owner' },
                        { value: 'admin', label: 'Admin' },
                        { value: 'developer', label: 'Developer' },
                        { value: 'viewer', label: 'Viewer' },
                      ]}
                    />
                    <Popconfirm title={t('app.repositories.settings.members.removeConfirm')} onConfirm={() => removeMember(m.user_id)}>
                      <Button size="small" danger icon={<DeleteOutlined />} disabled={!isOwnerOrAdmin} />
                    </Popconfirm>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Webhooks */}
          <div style={SECTION_GAP}>
            <SectionHeader
              icon={<ApiOutlined />}
              title={t('app.repositories.settings.webhooks.title')}
              extra={<Button size="small" type="primary" disabled={!isOwnerOrAdmin} onClick={openCreateWebhook}>{t('app.repositories.settings.webhooks.add')}</Button>}
            />
            <div style={{ padding: 8 }}>
              {whLoading ? (
                <div style={{ textAlign: 'center', padding: 24 }}><Spin /></div>
              ) : webhooks.length === 0 ? (
                <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={<span style={{ color: textSecondary }}>{t('app.repositories.settings.webhooks.empty')}</span>} style={{ padding: 24 }} />
              ) : (
                webhooks.map((wh) => (
                  <div
                    key={wh.id}
                    style={{ padding: '12px 14px', borderBottom: `1px solid ${borderColor}`, display: 'flex', alignItems: 'center', gap: 12 }}
                  >
                    <span style={{ width: 28, height: 28, borderRadius: 8, background: 'rgba(88,166,255,0.15)', color: blue, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                      <ApiOutlined />
                    </span>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: 13, color: textPrimary, fontFamily: 'monospace', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{wh.url}</div>
                      <div style={{ fontSize: 12, color: textTertiary }}>
                        {wh.events.map((e) => <Tag key={e} style={{ fontSize: 11, marginRight: 4 }}>{e}</Tag>)}
                        <span style={{ color: wh.is_active ? green : textTertiary }}>
                          {wh.is_active ? t('app.repositories.settings.webhooks.active') : t('app.repositories.settings.webhooks.inactive')}
                        </span>
                      </div>
                    </div>
                    <Button size="small" icon={<HistoryOutlined />} title={t('app.repositories.settings.webhooks.deliveries')} onClick={() => openDeliveries(wh)} />
                    <Button size="small" icon={<ExperimentOutlined />} title={t('app.repositories.settings.webhooks.test')} onClick={() => testWebhook(wh)} />
                    <Button size="small" onClick={() => openEditWebhook(wh)}>{t('app.repositories.settings.webhooks.editBtn')}</Button>
                    <Popconfirm title={t('app.repositories.settings.webhooks.deleteConfirm')} onConfirm={() => deleteWebhook(wh)}>
                      <Button size="small" danger icon={<DeleteOutlined />} />
                    </Popconfirm>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}

      {/* Add member modal */}
      <Modal
        title={t('app.repositories.settings.members.add')}
        open={addModal}
        onOk={addMember}
        onCancel={() => setAddModal(false)}
        confirmLoading={savingMember}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16, paddingTop: 8 }}>
          <div>
            <label style={{ fontSize: 13, color: textSecondary, marginBottom: 6, display: 'block' }}>{t('app.repositories.settings.members.userId')}</label>
            <Input value={memberUserId} onChange={(e) => setMemberUserId(e.target.value)} placeholder="user-id" />
          </div>
          <div>
            <label style={{ fontSize: 13, color: textSecondary, marginBottom: 6, display: 'block' }}>{t('app.repositories.settings.members.role')}</label>
            <Select
              value={memberRole}
              onChange={setMemberRole}
              style={{ width: '100%' }}
              options={[
                { value: 'owner', label: 'Owner' },
                { value: 'admin', label: 'Admin' },
                { value: 'developer', label: 'Developer' },
                { value: 'viewer', label: 'Viewer' },
              ]}
            />
          </div>
        </div>
      </Modal>

      {/* Webhook create/edit modal */}
      <Modal
        title={whEditing ? t('app.repositories.settings.webhooks.edit') : t('app.repositories.settings.webhooks.add')}
        open={whModal}
        onOk={saveWebhook}
        onCancel={() => setWhModal(false)}
        confirmLoading={savingWh}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16, paddingTop: 8 }}>
          <div>
            <label style={{ fontSize: 13, color: textSecondary, marginBottom: 6, display: 'block' }}>{t('app.repositories.settings.webhooks.url')}</label>
            <Input value={whUrl} onChange={(e) => setWhUrl(e.target.value)} placeholder="https://example.com/hook" />
          </div>
          <div>
            <label style={{ fontSize: 13, color: textSecondary, marginBottom: 6, display: 'block' }}>{t('app.repositories.settings.webhooks.events')}</label>
            <Select
              mode="multiple"
              value={whEvents}
              onChange={setWhEvents}
              style={{ width: '100%' }}
              options={villageEvents.map((e) => ({ value: e, label: e }))}
            />
          </div>
          <div>
            <label style={{ fontSize: 13, color: textSecondary, marginBottom: 6, display: 'block' }}>{t('app.repositories.settings.webhooks.secret')}</label>
            <Input.Password value={whSecret} onChange={(e) => setWhSecret(e.target.value)} placeholder={t('app.repositories.settings.webhooks.secretPlaceholder')} />
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Switch checked={whActive} onChange={setWhActive} />
            <span style={{ fontSize: 13, color: textSecondary }}>{t('app.repositories.settings.webhooks.active')}</span>
          </div>
        </div>
      </Modal>

      {/* Deliveries modal */}
      <Modal
        title={<span style={{ color: textPrimary }}>{t('app.repositories.settings.webhooks.deliveries')} · {deliveriesFor?.url}</span>}
        open={deliveriesOpen}
        onCancel={() => setDeliveriesOpen(false)}
        footer={null}
        width={720}
      >
        {deliveriesLoading ? (
          <div style={{ textAlign: 'center', padding: 32 }}><Spin /></div>
        ) : deliveries.length === 0 ? (
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={<span style={{ color: textSecondary }}>{t('app.repositories.settings.webhooks.noDeliveries')}</span>} style={{ padding: 24 }} />
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {deliveries.map((d) => (
              <div key={d.id} style={{ border: `1px solid ${borderColor}`, borderRadius: 8, padding: '10px 12px', background: '#0d1117' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
                  <Tag color="default" style={{ color: d.status_code && d.status_code < 300 ? green : '#f85149' }}>
                    {d.status_code}
                  </Tag>
                  <span style={{ fontSize: 13, color: textPrimary }}>{d.event}</span>
                  <span style={{ fontSize: 12, color: textTertiary, marginLeft: 'auto' }}>
                    {new Date(d.triggered_at).toLocaleString()}
                  </span>
                </div>
                <div style={{ fontSize: 12, color: textSecondary, marginTop: 6 }}>
                  {d.status} · {d.duration_ms != null ? `${d.duration_ms}ms` : '—'}
                </div>
              </div>
            ))}
          </div>
        )}
      </Modal>
    </div>
  );
}
