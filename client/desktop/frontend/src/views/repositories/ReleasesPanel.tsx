import { useCallback, useEffect, useRef, useState } from 'react';
import {
  Button, Modal, Form, Input, Switch, Tag, Empty, Spin, Popconfirm, Pagination, App as AntApp,
} from 'antd';
import { RocketOutlined, EditOutlined, DeleteOutlined, PaperClipOutlined, UploadOutlined, DownloadOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { releasesApi, type Release, type CreateReleaseRequest } from '../../api/releases';
import { useServersStore } from '../../stores/servers';
import Markdown from '../../components/Markdown';

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}

const textPrimary = '#e6edf3';
const textSecondary = '#8b949e';
const textTertiary = '#6e7681';
const borderColor = '#21262d';
const bgSecondary = '#161b22';
const amber = '#d29922';
const blue = '#58a6ff';

interface FormValues {
  tag_name: string;
  name: string;
  description?: string;
  commit_hash?: string;
  is_draft: boolean;
  is_prerelease: boolean;
  create_git_tag: boolean;
}

// ReleasesPanel：仓库 Release 列表 + 创建/编辑/删除（移植自 web 端 ReleasesTab）。
export default function ReleasesPanel({ repoId }: { repoId: string }) {
  const { t } = useTranslation();
  const { message } = AntApp.useApp();
  const serverId = useServersStore((s) => s.currentServerId);
  const [releases, setReleases] = useState<Release[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [limit] = useState(10);
  const [showDrafts, setShowDrafts] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Release | null>(null);
  const [saving, setSaving] = useState(false);
  const [uploadingFor, setUploadingFor] = useState<number | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [form] = Form.useForm<FormValues>();

  const load = useCallback(async (targetPage = page, withDrafts = showDrafts) => {
    if (!serverId) { setReleases([]); setTotal(0); setLoading(false); return; }
    try {
      const res = await releasesApi.list(serverId, repoId, {
        include_drafts: withDrafts,
        include_prereleases: true,
        page: targetPage,
        limit,
      });
      setReleases(res.items ?? []);
      setTotal(res.total ?? 0);
    } catch {
      setReleases([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [serverId, repoId, page, showDrafts, limit]);

  useEffect(() => {
    // 微任务延迟, 避免在 effect 同步体中触发级联渲染
    Promise.resolve().then(() => load());
  }, [load]);

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    form.setFieldsValue({ is_draft: false, is_prerelease: false, create_git_tag: true });
    setModalOpen(true);
  };

  const openEdit = (rel: Release) => {
    setEditing(rel);
    form.setFieldsValue({
      tag_name: rel.tag_name,
      name: rel.name,
      description: rel.description,
      commit_hash: rel.commit_hash,
      is_draft: rel.is_draft,
      is_prerelease: rel.is_prerelease,
      create_git_tag: false,
    });
    setModalOpen(true);
  };

  const handleSubmit = async () => {
    if (!serverId) return;
    const values = await form.validateFields();
    setSaving(true);
    try {
      if (editing) {
        await releasesApi.update(serverId, repoId, editing.release_number, {
          name: values.name,
          description: values.description,
          is_draft: values.is_draft,
          is_prerelease: values.is_prerelease,
        });
      } else {
        const payload: CreateReleaseRequest = {
          tag_name: values.tag_name,
          name: values.name,
          description: values.description,
          commit_hash: values.commit_hash || undefined,
          is_draft: values.is_draft,
          is_prerelease: values.is_prerelease,
          create_git_tag: values.create_git_tag,
        };
        await releasesApi.create(serverId, repoId, payload);
      }
      message.success(editing ? t('app.repositories.releases.updated') : t('app.repositories.releases.created'));
      setModalOpen(false);
      load(1, showDrafts);
    } catch (e) {
      message.error((e as Error).message || t('app.repositories.releases.failed'));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (rel: Release) => {
    if (!serverId) return;
    try {
      await releasesApi.delete(serverId, repoId, rel.release_number);
      message.success(t('app.repositories.releases.deleted'));
      load(1, showDrafts);
    } catch (e) {
      message.error((e as Error).message || t('app.repositories.releases.deleteFailed'));
    }
  };

  const toggleDrafts = (val: boolean) => {
    setShowDrafts(val);
    setPage(1);
    load(1, val);
  };

  const handleUploadClick = (releaseNumber: number) => {
    setUploadingFor(releaseNumber);
    fileInputRef.current?.click();
  };

  const handleUploadFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    const num = uploadingFor;
    e.target.value = '';
    if (!file || !num || !serverId) return;
    try {
      await releasesApi.uploadAsset(serverId, repoId, num, file);
      message.success(t('app.repositories.releases.assetUploaded'));
      load(page, showDrafts);
    } catch (err) {
      message.error((err as Error).message || t('app.repositories.releases.assetUploadFailed'));
    } finally {
      setUploadingFor(null);
    }
  };

  const handleDeleteAsset = async (rel: Release, assetId: string) => {
    if (!serverId) return;
    try {
      await releasesApi.deleteAsset(serverId, repoId, rel.release_number, assetId);
      message.success(t('app.repositories.releases.assetDeleted'));
      load(page, showDrafts);
    } catch (err) {
      message.error((err as Error).message || t('app.repositories.releases.assetDeleteFailed'));
    }
  };

  const handleDownloadAsset = async (rel: Release, assetId: string, filename: string) => {
    if (!serverId) return;
    try {
      await releasesApi.downloadAsset(serverId, repoId, rel.release_number, assetId, filename);
    } catch (err) {
      message.error((err as Error).message || t('app.repositories.releases.assetDownloadFailed'));
    }
  };

  return (
    <div style={{ flex: 1, minWidth: 0 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
        <h3 style={{ fontSize: 16, fontWeight: 600, margin: 0, color: textPrimary, display: 'flex', alignItems: 'center', gap: 8 }}>
          <RocketOutlined style={{ color: blue }} />
          {t('app.repositories.releases.title')}
        </h3>
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 12 }}>
          <label style={{ fontSize: 13, color: textSecondary, display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer' }}>
            <input type="checkbox" checked={showDrafts} onChange={(e) => toggleDrafts(e.target.checked)} />
            {t('app.repositories.releases.showDrafts')}
          </label>
          <Button type="primary" icon={<RocketOutlined />} onClick={openCreate}>
            {t('app.repositories.releases.new')}
          </Button>
        </div>
      </div>

      <input ref={fileInputRef} type="file" style={{ display: 'none' }} onChange={handleUploadFile} />

      {loading && releases.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 48 }}><Spin /></div>
      ) : releases.length === 0 ? (
        <div style={{ border: `1px solid ${borderColor}`, borderRadius: 12, background: bgSecondary }}>
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description={<span style={{ color: textSecondary }}>{t('app.repositories.releases.empty')}</span>}
            style={{ padding: 40 }}
          />
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {releases.map((rel) => (
            <div
              key={rel.id}
              style={{
                border: `1px solid ${borderColor}`,
                borderRadius: 12,
                background: bgSecondary,
                padding: '16px 20px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
                <span style={{ fontSize: 13, fontWeight: 700, color: blue }}>
                  {rel.tag_name}
                </span>
                <span style={{ fontSize: 14, fontWeight: 600, color: textPrimary }}>{rel.name}</span>
                {rel.is_draft && (
                  <Tag color="default" style={{ color: amber, borderColor: amber, background: 'transparent' }}>
                    {t('app.repositories.releases.badgeDraft')}
                  </Tag>
                )}
                {rel.is_prerelease && (
                  <Tag color="default" style={{ color: amber, borderColor: amber, background: 'transparent' }}>
                    {t('app.repositories.releases.badgePrerelease')}
                  </Tag>
                )}
                <div style={{ marginLeft: 'auto', display: 'flex', gap: 6 }}>
                  <Button size="small" icon={<UploadOutlined />} loading={uploadingFor === rel.release_number} onClick={() => handleUploadClick(rel.release_number)} title={t('app.repositories.releases.assetUpload')} />
                  <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(rel)} />
                  <Popconfirm
                    title={t('app.repositories.releases.deleteConfirm')}
                    onConfirm={() => handleDelete(rel)}
                  >
                    <Button size="small" danger icon={<DeleteOutlined />} />
                  </Popconfirm>
                </div>
              </div>
              <div style={{ marginTop: 6, fontSize: 12, color: textTertiary, display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
                <span>{t('app.repositories.releases.by')} {rel.author?.username ?? '—'}</span>
                {rel.commit_hash && (
                  <span style={{ fontFamily: 'monospace' }}>
                    {t('app.repositories.releases.commit')} {rel.commit_hash.slice(0, 7)}
                  </span>
                )}
                <span>{new Date(rel.created_at).toLocaleDateString()}</span>
              </div>
              {rel.description && (
                <div style={{ marginTop: 12, paddingTop: 12, borderTop: `1px solid ${borderColor}`, color: textSecondary }}>
                  <Markdown>{rel.description}</Markdown>
                </div>
              )}
              {!!rel.assets?.length && (
                <div style={{ marginTop: 12, paddingTop: 12, borderTop: `1px solid ${borderColor}`, display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {rel.assets.map((a) => (
                    <div key={a.id} style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 13 }}>
                      <PaperClipOutlined style={{ color: textTertiary }} />
                      <span
                        style={{ color: blue, cursor: 'pointer' }}
                        onClick={() => handleDownloadAsset(rel, a.id, a.name)}
                      >
                        {a.name} <DownloadOutlined style={{ fontSize: 11 }} />
                      </span>
                      <span style={{ color: textTertiary, fontSize: 12 }}>
                        {formatBytes(a.file_size)} · {t('app.repositories.releases.downloads', { count: a.download_count ?? 0 })}
                      </span>
                      <span style={{ flex: 1 }} />
                      <Popconfirm
                        title={t('app.repositories.releases.assetDeleteConfirm')}
                        onConfirm={() => handleDeleteAsset(rel, a.id)}
                      >
                        <Button size="small" type="text" danger icon={<DeleteOutlined />} />
                      </Popconfirm>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {total > limit && (
        <div style={{ display: 'flex', justifyContent: 'center', marginTop: 20 }}>
          <Pagination
            current={page}
            pageSize={limit}
            total={total}
            onChange={(p) => { setPage(p); load(p, showDrafts); }}
          />
        </div>
      )}

      <Modal
        title={editing ? t('app.repositories.releases.edit') : t('app.repositories.releases.new')}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => setModalOpen(false)}
        confirmLoading={saving}
        okText={t('app.repositories.releases.save')}
        cancelText={t('app.repositories.releases.cancel')}
      >
        <Form form={form} layout="vertical">
          {!editing && (
            <>
              <Form.Item
                name="tag_name"
                label={t('app.repositories.releases.tagName')}
                rules={[{ required: true, message: t('app.repositories.releases.required') }]}
              >
                <Input placeholder="v1.0.0" />
              </Form.Item>
              <Form.Item name="commit_hash" label={t('app.repositories.releases.commitHash')}>
                <Input placeholder={t('app.repositories.releases.commitHashPlaceholder')} />
              </Form.Item>
            </>
          )}
          <Form.Item
            name="name"
            label={t('app.repositories.releases.name')}
            rules={[{ required: true, message: t('app.repositories.releases.required') }]}
          >
            <Input />
          </Form.Item>
          <Form.Item name="description" label={t('app.repositories.releases.description')}>
            <Input.TextArea rows={4} placeholder={t('app.repositories.releases.descriptionPlaceholder')} />
          </Form.Item>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <Form.Item name="is_prerelease" valuePropName="checked" style={{ marginBottom: 0 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <Switch />
                <span style={{ fontSize: 13, color: textSecondary }}>{t('app.repositories.releases.prerelease')}</span>
              </div>
            </Form.Item>
            {editing ? null : (
              <Form.Item name="create_git_tag" valuePropName="checked" style={{ marginBottom: 0 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <Switch />
                  <span style={{ fontSize: 13, color: textSecondary }}>{t('app.repositories.releases.createTag')}</span>
                </div>
              </Form.Item>
            )}
            <Form.Item name="is_draft" valuePropName="checked" style={{ marginBottom: 0 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <Switch />
                <span style={{ fontSize: 13, color: textSecondary }}>{t('app.repositories.releases.draft')}</span>
              </div>
            </Form.Item>
          </div>
        </Form>
      </Modal>
    </div>
  );
}
