import { useState } from 'react';
import { Modal, Tabs, Form, Input, Button, Divider, App } from 'antd';
import {
  GithubOutlined,
  GitlabOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useAuthStore } from '../../stores/auth';
import { useNavigate } from 'react-router-dom';

interface AuthModalProps {
  open: boolean;
  defaultTab?: 'login' | 'register';
  onClose: () => void;
}

export default function AuthModal({ open, defaultTab = 'login', onClose }: AuthModalProps) {
  const [tab, setTab] = useState<string>(defaultTab);
  const [loading, setLoading] = useState(false);
  const { login, register } = useAuthStore();
  const navigate = useNavigate();
  const { message: msg } = App.useApp();
  const { t } = useTranslation();

  const [loginForm] = Form.useForm();
  const [registerForm] = Form.useForm();

  const handleLogin = async (values: { username: string; password: string }) => {
    setLoading(true);
    try {
      await login(values);
      msg.success(t('auth.messages.welcomeBack'));
      onClose();
      navigate('/dashboard');
    } catch (e: unknown) {
      const err = e as { status?: number; message?: string };
      msg.error(err?.message || t('auth.messages.invalidCredentials'));
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (values: {
    username: string;
    email: string;
    password: string;
    confirm: string;
    full_name: string;
  }) => {
    if (values.password !== values.confirm) {
      msg.error(t('auth.rules.passwordMismatch'));
      return;
    }
    setLoading(true);
    try {
      await register({
        username: values.username,
        email: values.email,
        password: values.password,
        full_name: values.full_name || undefined,
      });
      msg.success(t('auth.messages.accountCreated'));
      onClose();
      navigate('/dashboard');
    } catch (e: unknown) {
      const err = e as { status?: number; message?: string };
      msg.error(err?.message || t('auth.messages.registrationFailed'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      open={open}
      onCancel={onClose}
      footer={null}
      width={420}
      centered
      afterClose={() => {
        loginForm.resetFields();
        registerForm.resetFields();
      }}
      styles={{ body: { padding: '24px 0 0' } }}
    >
      <div style={{ textAlign: 'center', marginBottom: 24 }}>
        <img src="/logo-orbit-compact.svg" width={28} height={28} alt="Perseus" style={{ verticalAlign: 'middle' }} />
        <span style={{ fontSize: 20, fontWeight: 700, color: '#e6edf3', marginLeft: 8, verticalAlign: 'middle' }}>
          Perseus
        </span>
      </div>

      <Tabs
        activeKey={tab}
        onChange={setTab}
        centered
        items={[
          {
            key: 'login',
            label: t('auth.signIn'),
            children: (
              <>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 18 }}>
                  <Button icon={<GithubOutlined />} block style={{ textAlign: 'left' }}>
                    {t('auth.signInWithGitHub')}
                  </Button>
                  <Button icon={<GitlabOutlined />} block style={{ textAlign: 'left' }}>
                    {t('auth.signInWithGitLab')}
                  </Button>
                </div>
                <Divider style={{ fontSize: 12, color: '#6e7681', borderColor: '#21262d' }}>
                  {t('auth.orContinueWithEmail')}
                </Divider>
                <Form
                  form={loginForm}
                  layout="vertical"
                  onFinish={handleLogin}
                  requiredMark={false}
                >
                  <Form.Item
                    name="username"
                    label={<span style={{ color: '#8b949e', fontSize: 13 }}>{t('auth.username')}</span>}
                    rules={[{ required: true, message: t('auth.rules.usernameRequired') }]}
                  >
                    <Input placeholder={t('auth.placeholders.username')} />
                  </Form.Item>
                  <Form.Item
                    name="password"
                    label={<span style={{ color: '#8b949e', fontSize: 13 }}>{t('auth.password')}</span>}
                    rules={[{ required: true, message: t('auth.rules.passwordRequired') }]}
                  >
                    <Input.Password placeholder={t('auth.placeholders.password')} />
                  </Form.Item>
                  <Form.Item style={{ marginBottom: 16 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <label style={{ color: '#8b949e', fontSize: 13, cursor: 'pointer' }}>
                        <input type="checkbox" defaultChecked style={{ accentColor: '#1f6feb', marginRight: 8 }} />
                        {t('auth.rememberMe')}
                      </label>
                      <a style={{ color: '#58a6ff', fontSize: 13, cursor: 'pointer' }}>{t('auth.forgotPassword')}</a>
                    </div>
                  </Form.Item>
                  <Button type="primary" htmlType="submit" block loading={loading} size="large">
                    {t('auth.signIn')}
                  </Button>
                </Form>
              </>
            ),
          },
          {
            key: 'register',
            label: t('auth.createAccount'),
            children: (
              <>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 18 }}>
                  <Button icon={<GithubOutlined />} block style={{ textAlign: 'left' }}>
                    {t('auth.signUpWithGitHub')}
                  </Button>
                  <Button icon={<GitlabOutlined />} block style={{ textAlign: 'left' }}>
                    {t('auth.signUpWithGitLab')}
                  </Button>
                </div>
                <Divider style={{ fontSize: 12, color: '#6e7681', borderColor: '#21262d' }}>
                  {t('auth.orCreateWithEmail')}
                </Divider>
                <Form
                  form={registerForm}
                  layout="vertical"
                  onFinish={handleRegister}
                  requiredMark={false}
                >
                  <div style={{ display: 'flex', gap: 12 }}>
                    <Form.Item
                      name="full_name"
                      label={<span style={{ color: '#8b949e', fontSize: 13 }}>{t('auth.fullName')}</span>}
                      rules={[{ required: true, message: t('auth.rules.usernameRequiredRegister') }]}
                      style={{ flex: 1 }}
                    >
                      <Input placeholder={t('auth.placeholders.fullName')} />
                    </Form.Item>
                  </div>
                  <Form.Item
                    name="username"
                    label={<span style={{ color: '#8b949e', fontSize: 13 }}>{t('auth.username')}</span>}
                    rules={[
                      { required: true, message: t('auth.rules.usernameRequiredRegister') },
                      { min: 3, message: t('auth.rules.usernameMin') },
                    ]}
                  >
                    <Input placeholder={t('auth.placeholders.username')} />
                  </Form.Item>
                  <Form.Item
                    name="email"
                    label={<span style={{ color: '#8b949e', fontSize: 13 }}>{t('auth.email')}</span>}
                    rules={[
                      { required: true, message: t('auth.rules.emailRequired') },
                      { type: 'email', message: t('auth.rules.emailInvalid') },
                    ]}
                  >
                    <Input placeholder={t('auth.placeholders.email')} />
                  </Form.Item>
                  <Form.Item
                    name="password"
                    label={<span style={{ color: '#8b949e', fontSize: 13 }}>{t('auth.password')}</span>}
                    rules={[
                      { required: true, message: t('auth.rules.passwordRequiredRegister') },
                      { min: 6, message: t('auth.rules.passwordMin') },
                    ]}
                  >
                    <Input.Password placeholder={t('auth.rules.passwordMin')} />
                  </Form.Item>
                  <Form.Item
                    name="confirm"
                    label={<span style={{ color: '#8b949e', fontSize: 13 }}>{t('auth.confirmPassword')}</span>}
                    dependencies={['password']}
                    rules={[
                      { required: true, message: t('auth.rules.confirmRequired') },
                      ({ getFieldValue }) => ({
                        validator(_, value) {
                          if (!value || getFieldValue('password') === value) {
                            return Promise.resolve();
                          }
                          return Promise.reject(new Error(t('auth.rules.passwordMismatch')));
                        },
                      }),
                    ]}
                  >
                    <Input.Password placeholder={t('auth.placeholders.confirmPassword')} />
                  </Form.Item>
                  <Button type="primary" htmlType="submit" block loading={loading} size="large">
                    {t('auth.createAccount')}
                  </Button>
                </Form>
              </>
            ),
          },
        ]}
      />
    </Modal>
  );
}
