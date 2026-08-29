import { useState, useEffect, useRef, type ReactNode } from 'react';
import { Layout, Card, Form, Input, Button, Switch, Select, Avatar, Divider, message } from 'antd';
import {
  UserOutlined,
  LockOutlined,
  GlobalOutlined,
  BellOutlined,
  SafetyOutlined,
  MailOutlined,
  CheckOutlined,
  EyeOutlined,
  MessageOutlined,
  PullRequestOutlined,
  TagOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useAuthStore } from '../../stores/auth';
import { settingsApi } from '../../api/settings';
import { notificationsApi, type NotificationPreference } from '../../api/notifications';
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
  const [saving, setSaving] = useState(false);
  const [uploadingAvatar, setUploadingAvatar] = useState(false);
  const [avatarUrl, setAvatarUrl] = useState<string | undefined>(undefined);
  const [preferences, setPreferences] = useState<NotificationPreference | null>(null);
  const [prefSaving, setPrefSaving] = useState(false);
  const [form] = Form.useForm();
  const { user } = useAuthStore();
  const { t, i18n } = useTranslation();
  const avatarInputRef = useRef<HTMLInputElement>(null);

  // 真实加载：通知偏好来自 API（骨架屏等真实请求完成）
  useEffect(() => {
    let cancelled = false;
    notificationsApi.getPreferences()
      .then((prefs) => { if (!cancelled) setPreferences(prefs); })
      .catch(() => { if (!cancelled) setPreferences(null); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    form.setFieldsValue({
      username: user?.username || '',
      name: user?.full_name || '',
      email: user?.email || '',
      language: i18n.language || 'en',
    });
  }, [user, i18n.language, form]);

  const handleSaveProfile = async () => {
    if (!user) return;
    try {
      setSaving(true);
      const values = form.getFieldsValue(['name']);
      await settingsApi.updateProfile(user.id, {
        full_name: values.name,
      });
      message.success(t('app.settings.saveSuccess'));
    } catch {
      message.error(t('app.settings.saveError'));
    } finally {
      setSaving(false);
    }
  };

  const handleAvatarSelected = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = '';
    if (!file) return;
    setUploadingAvatar(true);
    try {
      const updated = await settingsApi.uploadAvatar(file);
      setAvatarUrl(settingsApi.getAvatarUrl(updated.id));
      message.success(t('app.settings.avatarUpdated'));
    } catch (err) {
      message.error((err as Error).message || t('app.settings.saveError'));
    } finally {
      setUploadingAvatar(false);
    }
  };

  const handleSaveAccount = async () => {
    if (!user) return;
    try {
      setSaving(true);
      const values = form.getFieldsValue(['username', 'email', 'currentPassword', 'newPassword', 'confirmNewPassword']);
      await settingsApi.updateProfile(user.id, {
        username: values.username,
        email: values.email,
      });
      if (values.newPassword) {
        if (values.newPassword !== values.confirmNewPassword) {
          message.error(t('app.settings.passwordMismatch'));
          return;
        }
        await settingsApi.changePassword({
          old_password: values.currentPassword,
          new_password: values.newPassword,
        });
      }
      message.success(t('app.settings.saveSuccess'));
    } catch {
      message.error(t('app.settings.saveError'));
    } finally {
      setSaving(false);
    }
  };

  const handleSaveNotifications = async () => {
    if (!preferences) return;
    setPrefSaving(true);
    try {
      const updated = await notificationsApi.updatePreferences(preferences);
      setPreferences(updated);
      message.success(t('app.settings.saveSuccess'));
    } catch {
      message.error(t('app.settings.saveError'));
    } finally {
      setPrefSaving(false);
    }
  };

  const updatePref = (key: keyof NotificationPreference, value: boolean) => {
    setPreferences((prev) => (prev ? { ...prev, [key]: value } : prev));
  };

  if (loading) return <SettingsSkeleton />;

  const menuItems: MenuItem[] = [
    { key: 'profile', icon: <UserOutlined style={{ fontSize: 14 }} />, label: t('app.settings.profile') },
    { key: 'account', icon: <SafetyOutlined style={{ fontSize: 14 }} />, label: t('app.settings.account') },
    { key: 'appearance', icon: <GlobalOutlined style={{ fontSize: 14 }} />, label: t('app.settings.appearance') },
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
                <input
                  ref={avatarInputRef}
                  type="file"
                  accept="image/jpeg,image/png,image/gif,image/webp"
                  style={{ display: 'none' }}
                  onChange={handleAvatarSelected}
                />
                <Avatar
                  size={80}
                  src={avatarUrl ?? (user?.avatar_url ? settingsApi.getAvatarUrl(user.id) : undefined)}
                  style={{
                    background: 'linear-gradient(135deg, #1f6feb, #bc8cff)',
                    fontSize: 28,
                    fontWeight: 700,
                  }}
                >
                  {user?.full_name?.slice(0, 2).toUpperCase() || user?.username?.slice(0, 2).toUpperCase() || ''}
                </Avatar>
                <div>
                  <Button
                    type="primary"
                    loading={uploadingAvatar}
                    onClick={() => avatarInputRef.current?.click()}
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
                  <p style={{ fontSize: 12, color: textTertiary, margin: 0 }}>JPG, GIF, PNG or WebP. Max 5MB.</p>
                </div>
              </div>

              <Form.Item name="name" label={<FormFieldLabel label={t('app.settings.name')} />}>
                <Input style={{ background: bgTertiary, borderColor: borderColor, color: textPrimary }} />
              </Form.Item>

              <div style={{ display: 'flex', justifyContent: 'flex-start', gap: 12, marginTop: 8 }}>
                <Button
                  type="primary"
                  icon={<CheckOutlined style={{ fontSize: 14 }} />}
                  loading={saving}
                  onClick={handleSaveProfile}
                  style={{ background: bluePrimary, borderColor: bluePrimary, borderRadius: 8, fontSize: 13, height: 34 }}
                >
                  {t('app.settings.saveChanges')}
                </Button>
                <Button
                  onClick={() => form.setFieldsValue({ name: user?.full_name || '' })}
                  style={{ background: bgTertiary, borderColor: borderColor, color: textSecondary, borderRadius: 8, fontSize: 13, height: 34 }}
                >
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
                  loading={saving}
                  onClick={handleSaveAccount}
                  style={{ background: bluePrimary, borderColor: bluePrimary, borderRadius: 8, fontSize: 13, height: 34 }}
                >
                  {t('app.settings.saveChanges')}
                </Button>
                <Button
                  onClick={() => form.setFieldsValue({ username: user?.username || '', email: user?.email || '', currentPassword: '', newPassword: '', confirmNewPassword: '' })}
                  style={{ background: bgTertiary, borderColor: borderColor, color: textSecondary, borderRadius: 8, fontSize: 13, height: 34 }}
                >
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

              {preferences ? (
                <>
                  {([
                    {
                      key: 'email_on_mention' as const,
                      icon: <MailOutlined style={{ fontSize: 18, color: blueLight }} />,
                      label: t('app.settings.emailOnMention'),
                      desc: t('app.settings.emailOnMentionDesc'),
                      border: true,
                    },
                    {
                      key: 'email_on_pr_review' as const,
                      icon: <PullRequestOutlined style={{ fontSize: 18, color: blueLight }} />,
                      label: t('app.settings.emailOnPrReview'),
                      desc: t('app.settings.emailOnPrReviewDesc'),
                      border: true,
                    },
                    {
                      key: 'in_app_on_mention' as const,
                      icon: <EyeOutlined style={{ fontSize: 18, color: blueLight }} />,
                      label: t('app.settings.inAppOnMention'),
                      desc: t('app.settings.inAppOnMentionDesc'),
                      border: true,
                    },
                    {
                      key: 'in_app_on_issue_comment' as const,
                      icon: <MessageOutlined style={{ fontSize: 18, color: blueLight }} />,
                      label: t('app.settings.inAppOnIssueComment'),
                      desc: t('app.settings.inAppOnIssueCommentDesc'),
                      border: false,
                    },
                  ]).map((row) => (
                    <div
                      key={row.key}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        padding: '14px 0',
                        borderBottom: row.border ? `1px solid ${borderColor}` : 'none',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                        {row.icon}
                        <div>
                          <div style={{ fontSize: 13, fontWeight: 600, color: textPrimary }}>{row.label}</div>
                          <div style={{ fontSize: 12, color: textTertiary }}>{row.desc}</div>
                        </div>
                      </div>
                      <Switch
                        checked={preferences[row.key]}
                        checkedChildren={<CheckOutlined style={{ fontSize: 10 }} />}
                        onChange={(checked) => updatePref(row.key, checked)}
                        style={preferences[row.key] ? { background: green } : undefined}
                      />
                    </div>
                  ))}
                </>
              ) : (
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '14px 0', color: textTertiary, fontSize: 13 }}>
                  <TagOutlined style={{ color: textTertiary }} />
                  {t('app.settings.preferencesUnavailable')}
                </div>
              )}

              <div style={{ display: 'flex', justifyContent: 'flex-start', gap: 12, marginTop: 16 }}>
                <Button
                  type="primary"
                  icon={<CheckOutlined style={{ fontSize: 14 }} />}
                  loading={prefSaving}
                  disabled={!preferences}
                  onClick={handleSaveNotifications}
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
