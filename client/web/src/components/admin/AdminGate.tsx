import { useState } from 'react';
import { Button, Form, Input } from 'antd';
import { LockOutlined, UserOutlined } from '@ant-design/icons';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuthStore } from '../../stores/auth';
import Logo from '../brand/Logo';

interface LoginValues {
  username: string;
  password: string;
}

/**
 * 控制台独立登录门禁：未认证时展示。
 * 登录成功后校验 is_admin —— 非管理员立即登出并提示，避免进入控制台后处处 403。
 */
export default function AdminGate() {
  const { t } = useTranslation();
  const login = useAuthStore((s) => s.login);
  const logout = useAuthStore((s) => s.logout);
  const [form] = Form.useForm<LoginValues>();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onFinish = async (values: LoginValues) => {
    setLoading(true);
    setError(null);
    try {
      await login(values);
      if (!useAuthStore.getState().user?.is_admin) {
        logout();
        setError(t('app.admin.gate.notAdmin'));
      }
    } catch (err) {
      setError((err as Error).message || t('app.admin.gate.loginFailed'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="admin-gate">
      <div className="admin-gate-card">
        <div className="admin-gate-brand">
          <Logo size={30} />
          <span>Perseus</span>
        </div>
        <div className="admin-gate-title">{t('app.admin.gate.title')}</div>
        <div className="admin-gate-sub">{t('app.admin.gate.subtitle')}</div>
        <Form form={form} layout="vertical" onFinish={onFinish} requiredMark={false} disabled={loading}>
          <Form.Item
            name="username"
            label={t('app.admin.gate.username')}
            rules={[{ required: true, message: t('app.admin.gate.usernameRequired') }]}
          >
            <Input prefix={<UserOutlined />} autoComplete="username" autoFocus />
          </Form.Item>
          <Form.Item
            name="password"
            label={t('app.admin.gate.password')}
            rules={[{ required: true, message: t('app.admin.gate.passwordRequired') }]}
          >
            <Input.Password prefix={<LockOutlined />} autoComplete="current-password" />
          </Form.Item>
          {error && <div className="admin-gate-error" role="alert">{error}</div>}
          <Button type="primary" htmlType="submit" block size="large" loading={loading}>
            {t('app.admin.gate.submit')}
          </Button>
        </Form>
        <Link className="admin-gate-back" to="/">{t('app.admin.gate.backHome')}</Link>
      </div>
    </div>
  );
}
