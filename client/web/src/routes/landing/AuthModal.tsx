import { useState } from 'react';
import { Modal, Form, Input, App } from 'antd';
import {
  CloseOutlined,
  GithubOutlined,
  GitlabOutlined,
  LockOutlined,
  MailOutlined,
  RightOutlined,
  SafetyOutlined,
  UserOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useAuthStore } from '../../stores/auth';
import Logo from '../../components/brand/Logo';
import { useNavigate } from 'react-router-dom';

interface AuthModalProps {
  open: boolean;
  defaultTab?: 'login' | 'register';
  onClose: () => void;
}

export default function AuthModal({ open, defaultTab = 'login', onClose }: AuthModalProps) {
  const [tab, setTab] = useState<'login' | 'register'>(defaultTab);
  const [loading, setLoading] = useState(false);
  const { login, register } = useAuthStore();
  const navigate = useNavigate();
  const { message: msg } = App.useApp();
  const { t } = useTranslation();

  const [loginForm] = Form.useForm();
  const [registerForm] = Form.useForm();

  // 组件常驻：打开时同步到调用方指定的 Tab（渲染期同步，避免 effect 级联渲染）
  const [wasOpen, setWasOpen] = useState(open);
  if (open !== wasOpen) {
    setWasOpen(open);
    if (open) setTab(defaultTab);
  }

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

  const oauthRow = (mode: 'login' | 'register') => (
    <div className="auth-oauth-row">
      <button className="auth-oauth" type="button">
        <GithubOutlined />
        <span>{mode === 'login' ? t('auth.signInWithGitHub') : t('auth.signUpWithGitHub')}</span>
        <RightOutlined className="chev" />
      </button>
      <button className="auth-oauth" type="button">
        <GitlabOutlined />
        <span>{mode === 'login' ? t('auth.signInWithGitLab') : t('auth.signUpWithGitLab')}</span>
        <RightOutlined className="chev" />
      </button>
    </div>
  );

  return (
    <Modal
      open={open}
      onCancel={onClose}
      footer={null}
      width={432}
      centered
      closable={false}
      className="perseus-auth-modal"
      styles={{ mask: { background: 'rgba(1,4,9,0.72)', backdropFilter: 'blur(10px)' } }}
      afterClose={() => {
        loginForm.resetFields();
        registerForm.resetFields();
      }}
    >
      <div className="auth-inner">
        {/* Header */}
        <div className="auth-head">
          <div className="auth-brand">
            <div className="auth-brand-mark">
              <Logo size={24} variant="reverse" />
            </div>
            <div>
              <div className="auth-brand-name">Perseus</div>
              <div className="auth-brand-sub">
                {tab === 'register'
                  ? t('auth.brandSubtitleRegister')
                  : t('auth.brandSubtitleLogin')}
              </div>
            </div>
          </div>
          <button className="auth-close" type="button" onClick={onClose} aria-label="Close dialog">
            <CloseOutlined />
          </button>
        </div>

        {/* Tabs */}
        <div className={`auth-tabs${tab === 'register' ? ' register' : ''}`} role="tablist">
          <div className="auth-tab-ind" />
          <button
            className={`auth-tab${tab === 'login' ? ' active' : ''}`}
            type="button"
            role="tab"
            aria-selected={tab === 'login'}
            onClick={() => setTab('login')}
          >
            {t('auth.signIn')}
          </button>
          <button
            className={`auth-tab${tab === 'register' ? ' active' : ''}`}
            type="button"
            role="tab"
            aria-selected={tab === 'register'}
            onClick={() => setTab('register')}
          >
            {t('auth.createAccount')}
          </button>
        </div>

        <div className="auth-body">
          {tab === 'login' ? (
            <div className="auth-pane" key="login">
              {oauthRow('login')}
              <div className="auth-divider">
                <span>{t('auth.orContinueWithEmail')}</span>
              </div>
              <Form
                form={loginForm}
                layout="vertical"
                onFinish={handleLogin}
                requiredMark={false}
                disabled={loading}
              >
                <Form.Item
                  name="username"
                  label={t('auth.username')}
                  rules={[{ required: true, message: t('auth.rules.usernameRequired') }]}
                >
                  <Input prefix={<UserOutlined />} placeholder={t('auth.placeholders.username')} autoComplete="username" autoFocus />
                </Form.Item>
                <Form.Item
                  name="password"
                  label={t('auth.password')}
                  rules={[{ required: true, message: t('auth.rules.passwordRequired') }]}
                >
                  <Input.Password prefix={<LockOutlined />} placeholder={t('auth.placeholders.password')} autoComplete="current-password" />
                </Form.Item>
                <Form.Item style={{ marginBottom: 16 }}>
                  <div className="auth-row-between">
                    <label className="auth-check">
                      <input type="checkbox" defaultChecked />
                      <span>{t('auth.rememberMe')}</span>
                    </label>
                    <a className="auth-link">{t('auth.forgotPassword')}</a>
                  </div>
                </Form.Item>
                <button className="auth-submit" type="submit" disabled={loading}>
                  {loading && <span className="spin" />}
                  <span>{t('auth.signIn')}</span>
                </button>
              </Form>
              <div className="auth-foot">
                {t('auth.newToPerseus')}{' '}
                <a className="auth-link" onClick={() => setTab('register')}>{t('auth.createOne')}</a>
              </div>
            </div>
          ) : (
            <div className="auth-pane" key="register">
              {oauthRow('register')}
              <div className="auth-divider">
                <span>{t('auth.orCreateWithEmail')}</span>
              </div>
              <Form
                form={registerForm}
                layout="vertical"
                onFinish={handleRegister}
                requiredMark={false}
                disabled={loading}
              >
                <Form.Item
                  name="full_name"
                  label={t('auth.fullName')}
                  rules={[{ required: true, message: t('auth.rules.usernameRequiredRegister') }]}
                >
                  <Input prefix={<UserOutlined />} placeholder={t('auth.placeholders.fullName')} autoComplete="name" />
                </Form.Item>
                <Form.Item
                  name="username"
                  label={t('auth.username')}
                  rules={[
                    { required: true, message: t('auth.rules.usernameRequiredRegister') },
                    { min: 3, message: t('auth.rules.usernameMin') },
                  ]}
                >
                  <Input prefix={<UserOutlined />} placeholder={t('auth.placeholders.username')} autoComplete="username" />
                </Form.Item>
                <Form.Item
                  name="email"
                  label={t('auth.email')}
                  rules={[
                    { required: true, message: t('auth.rules.emailRequired') },
                    { type: 'email', message: t('auth.rules.emailInvalid') },
                  ]}
                >
                  <Input prefix={<MailOutlined />} placeholder={t('auth.placeholders.email')} autoComplete="email" />
                </Form.Item>
                <Form.Item
                  name="password"
                  label={t('auth.password')}
                  rules={[
                    { required: true, message: t('auth.rules.passwordRequiredRegister') },
                    { min: 6, message: t('auth.rules.passwordMin') },
                  ]}
                >
                  <Input.Password prefix={<LockOutlined />} placeholder={t('auth.rules.passwordMin')} autoComplete="new-password" />
                </Form.Item>
                <Form.Item
                  name="confirm"
                  label={t('auth.confirmPassword')}
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
                  <Input.Password prefix={<SafetyOutlined />} placeholder={t('auth.placeholders.confirmPassword')} autoComplete="new-password" />
                </Form.Item>
                <button className="auth-submit" type="submit" disabled={loading}>
                  {loading && <span className="spin" />}
                  <span>{t('auth.createAccount')}</span>
                </button>
              </Form>
              <div className="auth-foot">
                {t('auth.alreadyHave')}{' '}
                <a className="auth-link" onClick={() => setTab('login')}>{t('auth.signInLink')}</a>
              </div>
            </div>
          )}
        </div>
      </div>
    </Modal>
  );
}
