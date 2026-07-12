import { useState, useEffect, type ReactNode } from 'react';
import { Layout, Card, Form, Input, Button, Switch, Select, Avatar, Divider, Radio } from 'antd';
import {
  UserOutlined,
  LockOutlined,
  GlobalOutlined,
  BgColorsOutlined,
  BellOutlined,
  SafetyOutlined,
  MailOutlined,
  CheckOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useAuthStore } from '../../stores/auth';
import SettingsSkeleton from '../../components/skeleton/SettingsSkeleton';

const { Sider, Content } = Layout;

const borderColor = '#21262d';
const hoverBg = '#1c2333';
const activeBg = '#1a2332';
const textSecondary = '#8b949e';
const textPrimary = '#e6edf3';
const textTertiary = '#6e7681';
const blueLight = '#58a6ff';
const bluePrimary = '#1f6feb';
const bgSecondary = '#161b22';
const bgTertiary = '#1c2128';
const green = '#3fb950';

type SettingsTab = 'profile' | 'account' | 'appearance' | 'notifications';

interface MenuItem {
  key: SettingsTab;
  icon: ReactNode;
  label: string;
}

function SectionTitle({ title, description }: { title: string; description?: string }) {
  return (
    <div style={{ marginBottom: 20 }}>
      <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 4, color: textPrimary }}>{title}</h2>
      {description && <p style={{ fontSize: 13, color: textSecondary, margin: 0 }}>{description}</p>}
    </div>
  );
}

function FormFieldLabel({ label }: { label: string }) {
  return <span style={{ color: textPrimary, fontSize: 13, fontWeight: 500 }}>{label}</span>;
}

export default function SettingsPage() {
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<SettingsTab>('profile');
  const [form] = Form.useForm();
  const { user } = useAuthStore();
  const { t, i18n } = useTranslation();

  useEffect(() => {
    const timer = setTimeout(() => setLoading(false), 600);
    return () => clearTimeout(timer);
  }, []);

  useEffect(() => {
    form.setFieldsValue({
      username: user?.username || 'zhang-lei',
      name: user?.full_name || 'Zhang Lei',
      email: user?.email || 'zhang.lei@example.com',
      bio: '',
      company: 'Perseus Labs',
      location: 'Shanghai, China',
      website: 'https://github.com/zhang-lei',
      language: i18n.language || 'en',
      theme: 'dark',
      emailNotifications: true,
      pushNotifications: false,
    });
  }, [user, i18n.language, form]);

  if (loading) return <SettingsSkeleton />;

  const menuItems: MenuItem[] = [
    { key: 'profile', icon: <UserOutlined style={{ fontSize: 14 }} />, label: t('app.settings.profile') },
    { key: 'account', icon: <SafetyOutlined style={{ fontSize: 14 }} />, label: t('app.settings.account') },
    { key: 'appearance', icon: <BgColorsOutlined style={{ fontSize: 14 }} />, label: t('app.settings.appearance') },
    { key: 'notifications', icon: <BellOutlined style={{ fontSize: 14 }} />, label: t('app.settings.notifications') },
  ];

  return (
    <Layout style={{ height: '100%', background: 'transparent' }}>
      <Sider
        width={260}
        style={{
          background: 'transparent',
          borderRight: `1px solid ${borderColor}`,
          flexShrink: 0,
        }}
      >
        <div style={{ padding: '24px 16px' }}>
          <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 20, color: textPrimary, paddingLeft: 8 }}>
            {t('app.settings.title')}
          </h1>
          <nav style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            {menuItems.map((item) => {
              const isActive = activeTab === item.key;
              return (
                <div
                  key={item.key}
                  onClick={() => setActiveTab(item.key)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 10,
                    padding: '8px 12px',
                    borderRadius: 8,
                    cursor: 'pointer',
                    color: isActive ? textPrimary : textSecondary,
                    background: isActive ? activeBg : 'transparent',
                    fontSize: 13,
                    fontWeight: 500,
                    transition: 'all 0.15s',
                  }}
                  onMouseEnter={(e) => {
                    if (!isActive) {
                      e.currentTarget.style.background = hoverBg;
                      e.currentTarget.style.color = textPrimary;
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!isActive) {
                      e.currentTarget.style.background = 'transparent';
                      e.currentTarget.style.color = textSecondary;
                    }
                  }}
                >
                  {item.icon}
                  {item.label}
                </div>
              );
            })}
          </nav>
        </div>
      </Sider>

      <Content style={{ padding: '24px 32px', overflowY: 'auto' }}>
        <Form form={form} layout="vertical" style={{ maxWidth: 720 }}>
          {activeTab === 'profile' && (
            <Card
              style={{ border: `1px solid ${borderColor}`, background: bgSecondary }}
              styles={{ body: { padding: 24 } }}
            >
              <SectionTitle
                title={t('app.settings.publicProfile')}
                description={t('app.settings.publicProfileDesc')}
              />

              <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 24 }}>
                <Avatar
                  size={80}
                  style={{
                    background: 'linear-gradient(135deg, #1f6feb, #bc8cff)',
                    fontSize: 28,
                    fontWeight: 700,
                  }}
                >
                  {user?.full_name?.slice(0, 2).toUpperCase() || user?.username?.slice(0, 2).toUpperCase() || 'ZL'}
                </Avatar>
                <div>
                  <Button
                    type="primary"
                    style={{
                      background: bluePrimary,
                      borderColor: bluePrimary,
                      borderRadius: 8,
                      fontSize: 13,
                      height: 32,
                      marginBottom: 6,
                    }}
                  >
                    {t('app.settings.changeAvatar')}
                  </Button>
                  <p style={{ fontSize: 12, color: textTertiary, margin: 0 }}>JPG, GIF or PNG. Max size 2MB.</p>
                </div>
              </div>

              <Form.Item name="name" label={<FormFieldLabel label={t('app.settings.name')} />}>
                <Input style={{ background: bgTertiary, borderColor: borderColor, color: textPrimary }} />
              </Form.Item>
              <Form.Item name="bio" label={<FormFieldLabel label={t('app.settings.bio')} />}>
                <Input.TextArea
                  rows={3}
                  placeholder={t('app.settings.bioPlaceholder')}
                  style={{ background: bgTertiary, borderColor: borderColor, color: textPrimary, resize: 'none' }}
                />
              </Form.Item>
              <Form.Item name="company" label={<FormFieldLabel label={t('app.settings.company')} />}>
                <Input style={{ background: bgTertiary, borderColor: borderColor, color: textPrimary }} />
              </Form.Item>
              <Form.Item name="location" label={<FormFieldLabel label={t('app.settings.location')} />}>
                <Input style={{ background: bgTertiary, borderColor: borderColor, color: textPrimary }} />
              </Form.Item>
              <Form.Item name="website" label={<FormFieldLabel label={t('app.settings.website')} />}>
                <Input style={{ background: bgTertiary, borderColor: borderColor, color: textPrimary }} />
              </Form.Item>

              <div style={{ display: 'flex', justifyContent: 'flex-start', gap: 12, marginTop: 8 }}>
                <Button
                  type="primary"
                  icon={<CheckOutlined style={{ fontSize: 14 }} />}
                  style={{ background: bluePrimary, borderColor: bluePrimary, borderRadius: 8, fontSize: 13, height: 34 }}
                >
                  {t('app.settings.saveChanges')}
                </Button>
                <Button style={{ background: bgTertiary, borderColor: borderColor, color: textSecondary, borderRadius: 8, fontSize: 13, height: 34 }}>
                  {t('app.settings.cancel')}
                </Button>
              </div>
            </Card>
          )}

          {activeTab === 'account' && (
            <Card
              style={{ border: `1px solid ${borderColor}`, background: bgSecondary }}
              styles={{ body: { padding: 24 } }}
            >
              <SectionTitle
                title={t('app.settings.accountSettings')}
                description={t('app.settings.accountSettingsDesc')}
              />

              <Form.Item name="username" label={<FormFieldLabel label={t('auth.username')} />}>
                <Input
                  prefix={<UserOutlined style={{ color: textTertiary }} />}
                  style={{ background: bgTertiary, borderColor: borderColor, color: textPrimary }}
                />
              </Form.Item>
              <Form.Item name="email" label={<FormFieldLabel label={t('auth.email')} />}>
                <Input
                  prefix={<MailOutlined style={{ color: textTertiary }} />}
                  style={{ background: bgTertiary, borderColor: borderColor, color: textPrimary }}
                />
              </Form.Item>

              <Divider style={{ borderColor: borderColor, margin: '24px 0' }} />

              <h3 style={{ fontSize: 15, fontWeight: 600, color: textPrimary, marginBottom: 12 }}>{t('app.settings.changePassword')}</h3>
              <Form.Item name="currentPassword" label={<FormFieldLabel label={t('app.settings.currentPassword')} />}>
                <Input.Password
                  prefix={<LockOutlined style={{ color: textTertiary }} />}
                  placeholder="••••••••"
                  style={{ background: bgTertiary, borderColor: borderColor, color: textPrimary }}
                />
              </Form.Item>
              <Form.Item name="newPassword" label={<FormFieldLabel label={t('app.settings.newPassword')} />}>
                <Input.Password
                  prefix={<LockOutlined style={{ color: textTertiary }} />}
                  style={{ background: bgTertiary, borderColor: borderColor, color: textPrimary }}
                />
              </Form.Item>
              <Form.Item name="confirmNewPassword" label={<FormFieldLabel label={t('app.settings.confirmNewPassword')} />}>
                <Input.Password
                  prefix={<LockOutlined style={{ color: textTertiary }} />}
                  style={{ background: bgTertiary, borderColor: borderColor, color: textPrimary }}
                />
              </Form.Item>

              <div style={{ display: 'flex', justifyContent: 'flex-start', gap: 12, marginTop: 8 }}>
                <Button
                  type="primary"
                  icon={<CheckOutlined style={{ fontSize: 14 }} />}
                  style={{ background: bluePrimary, borderColor: bluePrimary, borderRadius: 8, fontSize: 13, height: 34 }}
                >
                  {t('app.settings.saveChanges')}
                </Button>
                <Button style={{ background: bgTertiary, borderColor: borderColor, color: textSecondary, borderRadius: 8, fontSize: 13, height: 34 }}>
                  {t('app.settings.cancel')}
                </Button>
              </div>
            </Card>
          )}

          {activeTab === 'appearance' && (
            <Card
              style={{ border: `1px solid ${borderColor}`, background: bgSecondary }}
              styles={{ body: { padding: 24 } }}
            >
              <SectionTitle
                title={t('app.settings.appearanceSettings')}
                description={t('app.settings.appearanceSettingsDesc')}
              />

              <Form.Item label={<FormFieldLabel label={t('app.settings.theme')} />}>
                <Radio.Group defaultValue="dark" buttonStyle="solid">
                  <Radio.Button
                    value="dark"
                    style={{
                      background: bgTertiary,
                      borderColor: borderColor,
                      color: textPrimary,
                    }}
                  >
                    {t('app.settings.dark')}
                  </Radio.Button>
                  <Radio.Button
                    value="light"
                    style={{
                      background: bgTertiary,
                      borderColor: borderColor,
                      color: textPrimary,
                    }}
                  >
                    {t('app.settings.light')}
                  </Radio.Button>
                  <Radio.Button
                    value="system"
                    style={{
                      background: bgTertiary,
                      borderColor: borderColor,
                      color: textPrimary,
                    }}
                  >
                    {t('app.settings.system')}
                  </Radio.Button>
                </Radio.Group>
              </Form.Item>

              <Form.Item name="language" label={<FormFieldLabel label={t('app.settings.language')} />}>
                <Select
                  onChange={(val) => i18n.changeLanguage(val)}
                  options={[
                    { label: t('common.english'), value: 'en' },
                    { label: t('common.chinese'), value: 'zh' },
                  ]}
                  style={{ width: 200 }}
                />
              </Form.Item>

              <div style={{ display: 'flex', justifyContent: 'flex-start', gap: 12, marginTop: 8 }}>
                <Button
                  type="primary"
                  icon={<CheckOutlined style={{ fontSize: 14 }} />}
                  style={{ background: bluePrimary, borderColor: bluePrimary, borderRadius: 8, fontSize: 13, height: 34 }}
                >
                  {t('app.settings.saveChanges')}
                </Button>
              </div>
            </Card>
          )}

          {activeTab === 'notifications' && (
            <Card
              style={{ border: `1px solid ${borderColor}`, background: bgSecondary }}
              styles={{ body: { padding: 24 } }}
            >
              <SectionTitle
                title={t('app.settings.notificationsSettings')}
                description={t('app.settings.notificationsSettingsDesc')}
              />

              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '14px 0',
                  borderBottom: `1px solid ${borderColor}`,
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <MailOutlined style={{ fontSize: 18, color: blueLight }} />
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 600, color: textPrimary }}>{t('app.settings.emailNotifications')}</div>
                    <div style={{ fontSize: 12, color: textTertiary }}>{t('app.settings.emailNotificationsDesc')}</div>
                  </div>
                </div>
                <Form.Item name="emailNotifications" valuePropName="checked" noStyle>
                  <Switch
                    checkedChildren={<CheckOutlined style={{ fontSize: 10 }} />}
                    style={{ background: green }}
                  />
                </Form.Item>
              </div>

              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '14px 0',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <GlobalOutlined style={{ fontSize: 18, color: blueLight }} />
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 600, color: textPrimary }}>{t('app.settings.pushNotifications')}</div>
                    <div style={{ fontSize: 12, color: textTertiary }}>{t('app.settings.pushNotificationsDesc')}</div>
                  </div>
                </div>
                <Form.Item name="pushNotifications" valuePropName="checked" noStyle>
                  <Switch checkedChildren={<CheckOutlined style={{ fontSize: 10 }} />} />
                </Form.Item>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-start', gap: 12, marginTop: 16 }}>
                <Button
                  type="primary"
                  icon={<CheckOutlined style={{ fontSize: 14 }} />}
                  style={{ background: bluePrimary, borderColor: bluePrimary, borderRadius: 8, fontSize: 13, height: 34 }}
                >
                  {t('app.settings.saveChanges')}
                </Button>
              </div>
            </Card>
          )}
        </Form>
      </Content>
    </Layout>
  );
}
