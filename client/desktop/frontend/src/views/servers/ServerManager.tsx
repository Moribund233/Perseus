import { useEffect, useState } from 'react';
import { Button, Empty, Form, Input, Modal, Popconfirm, Radio } from 'antd';
import {
  PlusOutlined,
  ReloadOutlined,
  DeleteOutlined,
  EditOutlined,
  CloudServerOutlined,
  LinkOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { serversApi, type RegisterServerInput, type ServerRecord } from '../../api/servers';
import { useServersStore } from '../../stores/servers';
import { useNavigationStore } from '../../stores/navigation';
import { timeAgo } from '../../utils/time';

type AuthMethod = 'password' | 'token';

const healthClass: Record<ServerRecord['health'], string> = {
  online: 'green',
  offline: '',
  unknown: '',
};

export default function ServerManager() {
  const { t } = useTranslation();
  const servers = useServersStore((s) => s.servers);
  const setServers = useServersStore((s) => s.setServers);
  const upsert = useServersStore((s) => s.upsert);
  const remove = useServersStore((s) => s.remove);
  const setCurrent = useServersStore((s) => s.setCurrent);
  const currentServerId = useServersStore((s) => s.currentServerId);
  const navigate = useNavigationStore((s) => s.navigate);
  const [modal, setModal] = useState(false);
  const [authMethod, setAuthMethod] = useState<AuthMethod>('password');
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form] = Form.useForm();
  const [editing, setEditing] = useState<ServerRecord | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    serversApi.list().then(setServers).catch((e) => setError(String(e)));
  }, [setServers]);

  const openForm = () => {
    setAuthMethod('password');
    setError(null);
    form.resetFields();
    setEditing(null);
    setModal(true);
  };

  const openEdit = (s: ServerRecord) => {
    setAuthMethod(s.auth_method);
    setError(null);
    form.setFieldsValue({ name: s.name, base_url: s.base_url, username: s.username, password: '', token: '' });
    setEditing(s);
    setModal(true);
  };

  const doUpdate = async (values: Record<string, unknown>) => {
    if (!editing) return;
    setSaving(true);
    setError(null);
    try {
      const input: { name?: string; base_url?: string; username?: string; password?: string; token?: string } = {
        name: String(values.name ?? ''),
      };
      const baseUrl = String(values.base_url ?? '');
      const urlChanged = baseUrl !== editing.base_url;
      if (baseUrl) input.base_url = baseUrl;
      if (authMethod === 'password') {
        const password = String(values.password ?? '');
        if (password) input.password = password;
        if (values.username) input.username = String(values.username);
        if (urlChanged && !password) {
          setError(t('desktop.servers.updateCredRequired'));
          return;
        }
      } else {
        const token = String(values.token ?? '');
        if (token) input.token = token;
        if (urlChanged && !token) {
          setError(t('desktop.servers.updateCredRequiredToken'));
          return;
        }
      }
      const updated = await serversApi.update(editing.id, input);
      upsert(updated);
      setModal(false);
      setEditing(null);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const doRegister = async (values: Record<string, unknown>) => {
    setAdding(true);
    setError(null);
    try {
      const input: RegisterServerInput = {
        name: String(values.name ?? ''),
        base_url: String(values.base_url ?? ''),
      };
      if (authMethod === 'password') {
        input.username = String(values.username ?? '');
        input.password = String(values.password ?? '');
      } else {
        input.token = String(values.token ?? '');
      }
      const created = await serversApi.register(input);
      upsert(created);
      setModal(false);
      const hasReal = useServersStore.getState().servers.some((x) => x.id === useServersStore.getState().currentServerId);
      if (!hasReal) setCurrent(created.id);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setAdding(false);
    }
  };

  const refresh = async (id: string) => {
    await useServersStore.getState().refreshHealth(id);
  };

  const connect = (id: string) => {
    setCurrent(id);
    navigate('repositories');
  };

  return (
    <div className="page">
      <div className="page-head">
        <h2>{t('desktop.servers.title')}</h2>
        <span className="sub">{t('desktop.servers.sub', { count: servers.length })}</span>
        <div className="right">
          <Button type="primary" icon={<PlusOutlined />} onClick={openForm}>
            {t('desktop.servers.add')}
          </Button>
        </div>
      </div>

      {error && <div className="error-text" style={{ marginBottom: 12 }}>{error}</div>}

      {servers.length === 0 ? (
        <Empty description={t('desktop.servers.empty')}>
          <Button type="primary" icon={<PlusOutlined />} onClick={openForm}>
            {t('desktop.servers.add')}
          </Button>
        </Empty>
      ) : (
        <div className="srv-wrap scroll">
          {servers.map((s) => (
            <div className={`srv-card ${s.id === currentServerId ? 'current' : ''}`} key={s.id}>
              <div className={`srv-st ${s.health === 'online' ? 'on' : 'off'}`}>
                <CloudServerOutlined />
              </div>
              <div className="srv-main">
                <div className="r1">
                  <b>{s.name}</b>
                  <span className={`pill ${healthClass[s.health]}`}>{t(`desktop.servers.health.${s.health}`)}</span>
                  {s.id === currentServerId && <span className="current-chip">{t('desktop.welcome.serverRowCurrent')}</span>}
                </div>
                <div className="url mono">{s.base_url.replace(/^https?:\/\//, '')}</div>
                <div className="meta">
                  <span>{t('desktop.servers.metaAuth', { method: t(`desktop.servers.auth.${s.auth_method}`) })}</span>
                  <span>{t('desktop.servers.metaLast', { time: timeAgo(s.last_success, t) })}</span>
                  {s.health === 'offline' && <span className="cached">{t('desktop.servers.metaOffline')}</span>}
                </div>
              </div>
              <div className="srv-actions">
                {s.id !== currentServerId && (
                  <Button className="srv-act" size="small" onClick={() => connect(s.id)}>
                    <LinkOutlined />
                    {t('desktop.servers.connect')}
                  </Button>
                )}
                <Button className="srv-act" size="small" icon={<ReloadOutlined />} onClick={() => refresh(s.id)}>
                  {t('desktop.servers.refresh')}
                </Button>
                <Button className="srv-act" size="small" icon={<EditOutlined />} onClick={() => openEdit(s)}>
                  {t('desktop.servers.edit')}
                </Button>
                <Popconfirm title={t('desktop.servers.deleteConfirm', { name: s.name })} onConfirm={() => remove(s.id)}>
                  <Button className="srv-act" size="small" danger icon={<DeleteOutlined />} />
                </Popconfirm>
              </div>
            </div>
          ))}

          <div className="card lan-hint">
            <InfoCircleOutlined className="hint-ic" />
            <div>
              <b>{t('desktop.servers.lanTitle')}</b>
              <span>
                {t('desktop.servers.lanDesc', {
                  mdns: <span className="mono">_perseus._tcp</span>,
                })}
              </span>
            </div>
          </div>
        </div>
      )}

      <Modal
        open={modal}
        title={editing ? t('desktop.servers.editTitle', { name: editing.name }) : t('desktop.servers.add')}
        onCancel={() => { setModal(false); setEditing(null); }}
        onOk={() => form.submit()}
        confirmLoading={adding || saving}
        okText={editing ? t('desktop.servers.save') : t('desktop.servers.add')}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={editing ? doUpdate : doRegister}
        >
          <Form.Item name="name" label={t('desktop.servers.name')} rules={[{ required: true, message: t('desktop.servers.nameRequired') }]}>
            <Input placeholder={t('desktop.servers.namePlaceholder')} />
          </Form.Item>
          <Form.Item name="base_url" label={t('desktop.servers.baseUrl')} rules={[{ required: true, message: t('desktop.servers.baseUrlRequired') }]} extra={editing ? t('desktop.servers.baseUrlEditHint') : undefined}>
            <Input placeholder="http://127.0.0.1:8080" />
          </Form.Item>
          {!editing && (
            <Form.Item label={t('desktop.servers.authMethod')}>
              <Radio.Group value={authMethod} onChange={(e) => setAuthMethod(e.target.value as AuthMethod)}>
                <Radio value="password">{t('desktop.servers.auth.password')}</Radio>
                <Radio value="token">{t('desktop.servers.auth.token')}</Radio>
              </Radio.Group>
            </Form.Item>
          )}
          {authMethod === 'password' ? (
            <>
              <Form.Item name="username" label={t('desktop.servers.username')} rules={editing ? [] : [{ required: true, message: t('desktop.servers.usernameRequired') }]}>
                <Input autoComplete="off" />
              </Form.Item>
              <Form.Item name="password" label={editing ? t('desktop.servers.newPassword') : t('desktop.servers.password')} rules={editing ? [] : [{ required: true, message: t('desktop.servers.passwordRequired') }]}>
                <Input.Password />
              </Form.Item>
            </>
          ) : (
            <Form.Item name="token" label={editing ? t('desktop.servers.newToken') : t('desktop.servers.token')} rules={editing ? [] : [{ required: true, message: t('desktop.servers.tokenRequired') }]}>
              <Input.Password />
            </Form.Item>
          )}
          {error && <div className="error-text">{error}</div>}
        </Form>
      </Modal>
    </div>
  );
}