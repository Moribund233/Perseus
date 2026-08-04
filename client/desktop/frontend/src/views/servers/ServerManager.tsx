import { useEffect, useState } from 'react';
import { Button, Card, Empty, Form, Input, Modal, Popconfirm, Radio, Space, Tag, message } from 'antd';
import { PlusOutlined, ReloadOutlined, DeleteOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { serversApi, type RegisterServerInput, type ServerRecord } from '../../api/servers';
import { useServersStore } from '../../stores/servers';

type AuthMethod = 'password' | 'token';

const healthColor: Record<ServerRecord['health'], string> = {
  online: 'success',
  offline: 'error',
  unknown: 'default',
};

export default function ServerManager() {
  const { t } = useTranslation();
  const servers = useServersStore((s) => s.servers);
  const setServers = useServersStore((s) => s.setServers);
  const upsert = useServersStore((s) => s.upsert);
  const remove = useServersStore((s) => s.remove);
  const setCurrent = useServersStore((s) => s.setCurrent);
  const [modal, setModal] = useState(false);
  const [authMethod, setAuthMethod] = useState<AuthMethod>('password');
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form] = Form.useForm();

  useEffect(() => {
    serversApi.list().then(setServers).catch((e) => setError(String(e)));
  }, [setServers]);

  const openForm = () => {
    setAuthMethod('password');
    setError(null);
    form.resetFields();
    setModal(true);
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
      message.success(t('desktop.servers.added', { name: created.name }));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setAdding(false);
    }
  };

  const refresh = async (id: string) => {
    try {
      const updated = await useServersStore.getState().refreshHealth(id);
      if (updated) message.success(t('desktop.servers.healthTag', { health: t(`desktop.servers.health.${updated.health}`) }));
    } catch { /* 已置离线 */ }
  };

  return (
    <div style={{ padding: 24, maxWidth: 760, margin: '0 auto', width: '100%' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
        <h2 style={{ margin: 0, fontSize: 20 }}>{t('desktop.servers.title')}</h2>
        <Button type="primary" icon={<PlusOutlined />} onClick={openForm}>
          {t('desktop.servers.add')}
        </Button>
      </div>

      {error && <div className="error-text" style={{ marginBottom: 12 }}>{error}</div>}

      {servers.length === 0 ? (
        <Empty description={t('desktop.servers.empty')}>
          <Button type="primary" icon={<PlusOutlined />} onClick={openForm}>
            {t('desktop.servers.add')}
          </Button>
        </Empty>
      ) : (
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          {servers.map((s) => (
            <Card key={s.id} size="small">
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <Tag color={healthColor[s.health]}>{t(`desktop.servers.health.${s.health}`)}</Tag>
                <strong style={{ flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{s.name}</strong>
                <span className="muted" style={{ maxWidth: 240, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{s.base_url}</span>
                <Button
                  size="small"
                  icon={<ReloadOutlined />}
                  onClick={() => refresh(s.id)}
                  disabled={s.health === 'offline'}
                >
                  {t('desktop.servers.refresh')}
                </Button>
                <Popconfirm title={t('desktop.servers.deleteConfirm', { name: s.name })} onConfirm={() => remove(s.id)}>
                  <Button size="small" danger icon={<DeleteOutlined />} />
                </Popconfirm>
              </div>
            </Card>
          ))}
        </Space>
      )}

      <Modal
        open={modal}
        title={t('desktop.servers.add')}
        onCancel={() => setModal(false)}
        onOk={() => form.submit()}
        confirmLoading={adding}
        okText={t('desktop.servers.add')}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={doRegister}
          initialValues={{ authMethod }}
        >
          <Form.Item name="name" label={t('desktop.servers.name')} rules={[{ required: true, message: t('desktop.servers.nameRequired') }]}>
            <Input placeholder={t('desktop.servers.namePlaceholder')} />
          </Form.Item>
          <Form.Item name="base_url" label={t('desktop.servers.baseUrl')} rules={[{ required: true, message: t('desktop.servers.baseUrlRequired') }]}>
            <Input placeholder="http://127.0.0.1:8080" />
          </Form.Item>
          <Form.Item label={t('desktop.servers.authMethod')}>
            <Radio.Group value={authMethod} onChange={(e) => setAuthMethod(e.target.value as AuthMethod)}>
              <Radio value="password">{t('desktop.servers.auth.password')}</Radio>
              <Radio value="token">{t('desktop.servers.auth.token')}</Radio>
            </Radio.Group>
          </Form.Item>
          {authMethod === 'password' ? (
            <>
              <Form.Item name="username" label={t('desktop.servers.username')} rules={[{ required: true, message: t('desktop.servers.usernameRequired') }]}>
                <Input autoComplete="off" />
              </Form.Item>
              <Form.Item name="password" label={t('desktop.servers.password')} rules={[{ required: true, message: t('desktop.servers.passwordRequired') }]}>
                <Input.Password />
              </Form.Item>
            </>
          ) : (
            <Form.Item name="token" label={t('desktop.servers.token')} rules={[{ required: true, message: t('desktop.servers.tokenRequired') }]}>
              <Input.Password />
            </Form.Item>
          )}
          {error && <div className="error-text">{t('desktop.servers.loginFailed', { error })}</div>}
        </Form>
      </Modal>
    </div>
  );
}