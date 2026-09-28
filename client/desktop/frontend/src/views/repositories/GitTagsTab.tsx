import { useCallback, useEffect, useState } from 'react';
import { Button, Modal, Form, Input, Spin, Empty, Popconfirm, App as AntApp } from 'antd';
import { TagOutlined, PlusOutlined, DeleteOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { repositoriesApi } from '../../api/repositories';
import type { RepoTag } from '../../api/repositories';
import { useServersStore } from '../../stores/servers';

const borderColor = '#21262d';
const hoverBg = '#1c2333';
const textPrimary = '#e6edf3';
const textSecondary = '#8b949e';
const textTertiary = '#6e7681';
const bgSecondary = '#161b22';
const blue = '#58a6ff';
const purple = '#bc8cff';

interface TagFormValues { name: string; target?: string; message?: string }

export default function GitTagsTab({ repoId }: { repoId: string }) {
  const { t } = useTranslation();
  const { message } = AntApp.useApp();
  const serverId = useServersStore((s) => s.currentServerId);
  const [tags, setTags] = useState<RepoTag[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm<TagFormValues>();

  const load = useCallback(async () => {
    if (!serverId) return;
    setLoading(true);
    try {
      setTags(await repositoriesApi.listTags(serverId, repoId));
    } catch {
      setTags([]);
    } finally {
      setLoading(false);
    }
  }, [serverId, repoId]);

  useEffect(() => {
    Promise.resolve().then(load);
  }, [load]);

  const openCreate = () => {
    form.resetFields();
    setModalOpen(true);
  };

  const handleSubmit = async () => {
    if (!serverId) return;
    const values = await form.validateFields();
    setSaving(true);
    try {
      await repositoriesApi.createTag(serverId, repoId, {
        name: values.name,
        target: values.target || undefined,
        message: values.message || undefined,
      });
      message.success(t('app.repositories.gitBrowser.tagCreated', { name: values.name }));
      setModalOpen(false);
      await load();
    } catch (e) {
      message.error((e as Error).message || t('app.repositories.gitBrowser.actionFailed'));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (tag: RepoTag) => {
    if (!serverId) return;
    try {
      await repositoriesApi.deleteTag(serverId, repoId, tag.name);
      message.success(t('app.repositories.gitBrowser.tagDeleted', { name: tag.name }));
      await load();
    } catch (e) {
      message.error((e as Error).message || t('app.repositories.gitBrowser.actionFailed'));
    }
  };

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
        <h3 style={{ fontSize: 16, fontWeight: 600, margin: 0, color: textPrimary, display: 'flex', alignItems: 'center', gap: 8 }}>
          <TagOutlined style={{ color: blue }} />
          {t('app.repositories.gitBrowser.tagsTitle', { count: tags.length })}
        </h3>
        <Button type="primary" size="small" icon={<PlusOutlined />} style={{ marginLeft: 'auto' }} onClick={openCreate}>
          {t('app.repositories.gitBrowser.newTag')}
        </Button>
      </div>

      {loading && tags.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 48 }}><Spin /></div>
      ) : tags.length === 0 ? (
        <div style={{ border: `1px solid ${borderColor}`, borderRadius: 12, background: bgSecondary }}>
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={<span style={{ color: textSecondary }}>{t('app.repositories.gitBrowser.noTags')}</span>} style={{ padding: 40 }} />
        </div>
      ) : (
        <div style={{ border: `1px solid ${borderColor}`, borderRadius: 12, overflow: 'hidden', background: bgSecondary }}>
          {tags.map((tag, i) => (
            <div
              key={tag.name}
              style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '11px 16px', borderBottom: i === tags.length - 1 ? 'none' : `1px solid ${borderColor}`, fontSize: 13 }}
              onMouseEnter={(e) => { e.currentTarget.style.background = hoverBg; }}
              onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
            >
              <TagOutlined style={{ color: purple, flexShrink: 0 }} />
              <span style={{ color: purple, fontWeight: 700, flexShrink: 0 }}>{tag.name}</span>
              <span style={{ color: textSecondary, flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{tag.message || '—'}</span>
              <span style={{ fontFamily: 'monospace', color: textTertiary, fontSize: 12, flexShrink: 0 }}>{tag.commit_hash?.slice(0, 7)}</span>
              <Popconfirm title={t('app.repositories.gitBrowser.deleteTagConfirm', { name: tag.name })} onConfirm={() => handleDelete(tag)}>
                <Button size="small" type="text" danger icon={<DeleteOutlined />} />
              </Popconfirm>
            </div>
          ))}
        </div>
      )}

      <Modal
        title={t('app.repositories.gitBrowser.newTag')}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => setModalOpen(false)}
        confirmLoading={saving}
        okText={t('app.repositories.gitBrowser.create')}
        cancelText={t('app.repositories.gitBrowser.cancel')}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label={t('app.repositories.gitBrowser.tagName')} rules={[{ required: true, message: t('app.repositories.gitBrowser.required') }]}>
            <Input placeholder="v1.0.0" />
          </Form.Item>
          <Form.Item name="target" label={t('app.repositories.gitBrowser.tagTarget')}>
            <Input placeholder={t('app.repositories.gitBrowser.tagTargetPlaceholder')} />
          </Form.Item>
          <Form.Item name="message" label={t('app.repositories.gitBrowser.tagMessage')}>
            <Input.TextArea rows={3} placeholder={t('app.repositories.gitBrowser.tagMessagePlaceholder')} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
