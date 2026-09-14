import { useEffect, useState } from 'react';
import { App as AntApp, Popconfirm, Select, Switch, Tooltip } from 'antd';
import { useTranslation } from 'react-i18next';
import {
  CloudServerOutlined,
  GlobalOutlined,
  EditOutlined,
  KeyOutlined,
  InfoCircleOutlined,
  CopyOutlined,
  ReloadOutlined,
  BellOutlined,
  UserOutlined,
  PlusOutlined,
  DeleteOutlined,
  LinkOutlined,
} from '@ant-design/icons';
import { useGatewayStore } from '../stores/gateway';
import { useServersStore } from '../stores/servers';
import { useWorkspaceStore } from '../stores/workspace';
import { useNavigationStore } from '../stores/navigation';
import { useNotificationsStore } from '../stores/notifications';
import type { NotificationPreference } from '../api/notifications';
import { accountApi, type SSHKey, type OAuthAccount } from '../api/account';
import Brand from '../components/Brand';

const LANGUAGES = [
  { value: 'zh', label: '中文（简体）' },
  { value: 'en', label: 'English' },
];

type Section = 'gateway' | 'appearance' | 'editor' | 'notifications' | 'account' | 'keys' | 'about';

function gatewayHost(baseURL: string | undefined): string {
  return (baseURL ?? '').replace(/^https?:\/\//, '').replace(/\/$/, '');
}

export default function Settings() {
  const { t, i18n } = useTranslation();
  const { message } = AntApp.useApp();
  const [sec, setSec] = useState<Section>('gateway');
  const config = useGatewayStore((s) => s.config);
  const servers = useServersStore((s) => s.servers);
  const workspaces = useWorkspaceStore((s) => s.workspaces);
  const navigate = useNavigationStore((s) => s.navigate);

  const copyAddr = async () => {
    try {
      await navigator.clipboard.writeText(config?.baseURL ?? '');
      message.success(t('desktop.settings.gateway.addrCopied'));
    } catch { /* 忽略 */ }
  };

  const themeComing = () => message.info(t('desktop.settings.appearance.themeComing'));

  const navItems: Array<{ key: Section; icon: React.ReactNode; label: string }> = [
    { key: 'gateway', icon: <CloudServerOutlined />, label: t('desktop.settings.gateway.title') },
    { key: 'appearance', icon: <GlobalOutlined />, label: t('desktop.settings.appearance.title') },
    { key: 'editor', icon: <EditOutlined />, label: t('desktop.settings.editor.title') },
    { key: 'notifications', icon: <BellOutlined />, label: t('desktop.settings.notifications.title') },
    { key: 'account', icon: <UserOutlined />, label: t('desktop.settings.account.title') },
    { key: 'keys', icon: <KeyOutlined />, label: t('desktop.settings.keys.title') },
    { key: 'about', icon: <InfoCircleOutlined />, label: t('desktop.settings.about.title') },
  ];

  const KBD: Array<{ label: string; keys: string[] }> = [
    { label: t('desktop.settings.keys.cmd'), keys: ['Ctrl', 'K'] },
    { label: t('desktop.settings.keys.save'), keys: ['Ctrl', 'S'] },
    { label: t('desktop.settings.keys.sidebar'), keys: ['Ctrl', 'B'] },
    { label: t('desktop.settings.keys.explorerSearchScm'), keys: ['Ctrl', 'Shift', 'E / F / G'] },
    { label: t('desktop.settings.keys.terminal'), keys: ['Ctrl', '`'] },
    { label: t('desktop.settings.keys.commit'), keys: ['Ctrl', 'Enter'] },
    { label: t('desktop.settings.keys.close'), keys: ['Esc'] },
  ];

  return (
    <div className="set-body">
      <nav className="set-nav">
        <h2>{t('desktop.settings.title')}</h2>
        {navItems.map((it) => (
          <button key={it.key} className={`nav-item ${sec === it.key ? 'on' : ''}`} onClick={() => setSec(it.key)}>
            {it.icon}
            {it.label}
          </button>
        ))}
      </nav>

      <div className="set-content scroll">
        {sec === 'gateway' && (
          <section className="set-sec">
            <h3>{t('desktop.settings.gateway.title')}</h3>
            <p className="desc">{t('desktop.settings.gateway.desc')}</p>
            <div className="card kv-card">
              <div className="kv">
                <span className="k2">{t('desktop.settings.gateway.addr')}</span>
                <span className="v2">
                  <span className="mono">{gatewayHost(config?.baseURL)}</span>
                  <Tooltip title={t('desktop.settings.gateway.addrCopied')}>
                    <button className="icon-btn sm" onClick={copyAddr}><CopyOutlined /></button>
                  </Tooltip>
                  <span className="dot on" />
                  {t('desktop.settings.gateway.running')}
                </span>
              </div>
              <div className="kv">
                <span className="k2">{t('desktop.settings.gateway.tokenLabel')}</span>
                <span className="v2">
                  {config?.gatewayToken ? (
                    <>
                      <span className="pill green">{t('desktop.settings.gateway.tokenGenerated')}</span>
                      <span className="sub-hint">{t('desktop.settings.gateway.tokenProtect')}</span>
                    </>
                  ) : (
                    <span className="pill">{t('desktop.settings.gateway.tokenMissing')}</span>
                  )}
                </span>
              </div>
              <div className="kv">
                <span className="k2">{t('desktop.settings.gateway.workspaces')}</span>
                <span className="v2">{workspaces.length}</span>
              </div>
              <div className="kv">
                <span className="k2">{t('desktop.settings.gateway.servers')}</span>
                <span className="v2">
                  {servers.length}
                  <button className="link-btn" onClick={() => navigate('servers')}>{t('desktop.settings.gateway.manage')}</button>
                </span>
              </div>
              <div className="kv">
                <span className="k2">{t('desktop.settings.gateway.cache')}</span>
                <span className="v2">
                  <span className="pill blue">{t('desktop.settings.gateway.cacheValue')}</span>
                  <span className="sub-hint">{t('desktop.settings.gateway.cacheHint')}</span>
                </span>
              </div>
            </div>
          </section>
        )}

        {sec === 'appearance' && (
          <section className="set-sec">
            <h3>{t('desktop.settings.appearance.title')}</h3>
            <p className="desc">{t('desktop.settings.appearance.desc')}</p>
            <div className="card pad">
              <div className="sec-label">{t('desktop.settings.appearance.theme')}</div>
              <div className="theme-cards">
                <div className="theme-card on"><div className="prev dark" /><span>{t('desktop.settings.appearance.dark')}</span></div>
                <div className="theme-card" onClick={themeComing}><div className="prev light" /><span>{t('desktop.settings.appearance.light')}</span></div>
                <div className="theme-card" onClick={themeComing}><div className="prev auto" /><span>{t('desktop.settings.appearance.system')}</span></div>
              </div>
              <div className="kv" style={{ marginTop: 14 }}>
                <span className="k2">{t('desktop.settings.appearance.language')}</span>
                <span className="v2">
                  <GlobalOutlined />
                  <Select
                    value={i18n.language.startsWith('zh') ? 'zh' : 'en'}
                    options={LANGUAGES}
                    style={{ width: 180 }}
                    onChange={(lng) => void i18n.changeLanguage(lng)}
                  />
                </span>
              </div>
            </div>
          </section>
        )}

        {sec === 'editor' && (
          <section className="set-sec">
            <h3>{t('desktop.settings.editor.title')}</h3>
            <p className="desc">{t('desktop.settings.editor.desc')}</p>
            <div className="card kv-card">
              <div className="kv">
                <span className="k2">{t('desktop.settings.editor.fontSize')}</span>
                <span className="v2">
                  <span className="mono">13px</span>
                  <span className="sub-hint">{t('desktop.settings.editor.fontName')}</span>
                </span>
              </div>
              <div className="kv">
                <span className="k2">{t('desktop.settings.editor.indent')}</span>
                <span className="v2"><span className="pill">{t('desktop.settings.editor.indentValue')}</span></span>
              </div>
              <div className="kv">
                <span className="k2">{t('desktop.settings.editor.autoSave')}</span>
                <span className="v2">
                  <span className="pill green">{t('desktop.settings.editor.autoSaveValue')}</span>
                  <span className="sub-hint">{t('desktop.settings.editor.autoSaveHint')}</span>
                </span>
              </div>
              <div className="kv">
                <span className="k2">{t('desktop.settings.editor.largeFile')}</span>
                <span className="v2">
                  <span className="pill">{t('desktop.settings.editor.largeFileValue')}</span>
                  <span className="sub-hint">{t('desktop.settings.editor.largeFileHint')}</span>
                </span>
              </div>
              <div className="kv">
                <span className="k2">{t('desktop.settings.editor.collab')}</span>
                <span className="v2">
                  <span className="pill blue">{t('desktop.settings.editor.collabValue')}</span>
                  <span className="sub-hint">{t('desktop.settings.editor.collabHint')}</span>
                </span>
              </div>
            </div>
          </section>
        )}

        {sec === 'notifications' && <NotificationsSection />}

        {sec === 'account' && <AccountSection />}

        {sec === 'keys' && (
          <section className="set-sec">
            <h3>{t('desktop.settings.keys.title')}</h3>
            <p className="desc">{t('desktop.settings.keys.desc')}</p>
            <div className="card kv-card">
              <table className="kbd-table">
                <tbody>
                  {KBD.map((row, i) => (
                    <tr key={i}>
                      <td>{row.label}</td>
                      <td>
                        <span className="keys">
                          {row.keys.map((k) => <kbd key={k}>{k}</kbd>)}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}

        {sec === 'about' && (
          <section className="set-sec">
            <h3>{t('desktop.settings.about.title')}</h3>
            <p className="desc">{t('desktop.settings.about.desc')}</p>
            <div className="card about-card">
              <Brand size={44} />
              <div className="about-main">
                <b>Perseus Desktop</b>
                <div className="about-version">{t('desktop.settings.about.version')}</div>
              </div>
              <ButtonGhost onClick={() => message.info(t('desktop.settings.about.latest'))}>
                <ReloadOutlined />
                {t('desktop.settings.about.check')}
              </ButtonGhost>
            </div>
          </section>
        )}
      </div>
    </div>
  );
}

function ButtonGhost({ children, onClick }: { children: React.ReactNode; onClick: () => void }) {
  return (
    <button className="btn ghost" onClick={onClick}>{children}</button>
  );
}

// NotificationsSection：通知偏好设置（与 web 端设置页对齐的八项开关，覆盖后端全部偏好字段）。
// 偏好按服务器维度存储，未连接服务器时引导去服务器管理页。
const PREF_ROWS: Array<{ key: keyof NotificationPreference; label: string; desc: string }> = [
  { key: 'email_on_mention', label: 'emailOnMention', desc: 'emailOnMentionDesc' },
  { key: 'email_on_pr_review', label: 'emailOnPrReview', desc: 'emailOnPrReviewDesc' },
  { key: 'email_on_issue_comment', label: 'emailOnIssueComment', desc: 'emailOnIssueCommentDesc' },
  { key: 'email_on_pr_merge', label: 'emailOnPrMerge', desc: 'emailOnPrMergeDesc' },
  { key: 'email_on_release', label: 'emailOnRelease', desc: 'emailOnReleaseDesc' },
  { key: 'in_app_on_mention', label: 'inAppOnMention', desc: 'inAppOnMentionDesc' },
  { key: 'in_app_on_pr_review', label: 'inAppOnPrReview', desc: 'inAppOnPrReviewDesc' },
  { key: 'in_app_on_issue_comment', label: 'inAppOnIssueComment', desc: 'inAppOnIssueCommentDesc' },
];

function NotificationsSection() {
  const { t } = useTranslation();
  const { message } = AntApp.useApp();
  const currentServerId = useServersStore((s) => s.currentServerId);
  const preferences = useNotificationsStore((s) => s.preferences);
  const isLoading = useNotificationsStore((s) => s.isLoading);
  const error = useNotificationsStore((s) => s.error);
  const fetchPreferences = useNotificationsStore((s) => s.fetchPreferences);
  const updatePreferences = useNotificationsStore((s) => s.updatePreferences);
  const navigate = useNavigationStore((s) => s.navigate);
  const [draft, setDraft] = useState<NotificationPreference | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!currentServerId) return;
    void fetchPreferences();
  }, [currentServerId, fetchPreferences]);

  useEffect(() => {
    setDraft(preferences ? { ...preferences } : null);
  }, [preferences]);

  if (!currentServerId) {
    return (
      <section className="set-sec">
        <h3>{t('desktop.settings.notifications.title')}</h3>
        <p className="desc">{t('desktop.settings.notifications.desc')}</p>
        <div className="card pad">
          <div className="kv">
            <span className="k2">{t('desktop.settings.notifications.noServer')}</span>
            <span className="v2">
              <button className="link-btn" onClick={() => navigate('servers')}>
                {t('desktop.settings.notifications.connect')}
              </button>
            </span>
          </div>
        </div>
      </section>
    );
  }

  if (!draft) {
    return (
      <section className="set-sec">
        <h3>{t('desktop.settings.notifications.title')}</h3>
        <p className="desc">{t('desktop.settings.notifications.desc')}</p>
        <div className="card pad">
          {isLoading ? (
            <span className="sub-hint">{t('desktop.settings.notifications.loading')}</span>
          ) : (
            <>
              <span className="sub-hint">{t('desktop.settings.notifications.unavailable')}</span>
              <button className="link-btn" style={{ marginLeft: 8 }} onClick={() => void fetchPreferences()}>
                {t('desktop.settings.notifications.retry')}
              </button>
              {error ? <div className="sub-hint">{error}</div> : null}
            </>
          )}
        </div>
      </section>
    );
  }

  const save = async () => {
    setSaving(true);
    try {
      await updatePreferences(draft);
      message.success(t('desktop.settings.notifications.saved'));
    } catch (e) {
      message.error((e as Error).message || t('desktop.settings.notifications.saveFailed'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className="set-sec">
      <h3>{t('desktop.settings.notifications.title')}</h3>
      <p className="desc">{t('desktop.settings.notifications.desc')}</p>
      <div className="card kv-card">
        {PREF_ROWS.map((row) => (
          <div className="kv" key={row.key}>
            <span className="k2">{t(`desktop.settings.notifications.${row.label}`)}</span>
            <span className="v2">
              <Switch
                checked={draft[row.key]}
                onChange={(v) => setDraft((prev) => (prev ? { ...prev, [row.key]: v } : prev))}
              />
              <span className="sub-hint">{t(`desktop.settings.notifications.${row.desc}`)}</span>
            </span>
          </div>
        ))}
        <div className="kv">
          <span className="k2" />
          <span className="v2">
            <button className="btn ghost" disabled={saving} onClick={() => void save()}>
              {t('desktop.settings.notifications.save')}
            </button>
          </span>
        </div>
      </div>
    </section>
  );
}
// AccountSection：用户中心（SSH Keys 管理 + OAuth 关联），按当前连接服务器操作。
function AccountSection() {
  const { t } = useTranslation();
  const { message } = AntApp.useApp();
  const currentServerId = useServersStore((s) => s.currentServerId);
  const navigate = useNavigationStore((s) => s.navigate);
  const [keys, setKeys] = useState<SSHKey[] | null>(null);
  const [oauth, setOauth] = useState<OAuthAccount[] | null>(null);
  const [failed, setFailed] = useState(false);
  const [keyName, setKeyName] = useState('');
  const [publicKey, setPublicKey] = useState('');
  const [adding, setAdding] = useState(false);

  const load = async () => {
    if (!currentServerId) return;
    setFailed(false);
    try {
      const [keyList, accList] = await Promise.all([
        accountApi.listSSHKeys(currentServerId),
        accountApi.listOAuthAccounts(currentServerId),
      ]);
      setKeys(keyList ?? []);
      setOauth(accList ?? []);
    } catch (e) {
      setFailed(true);
      message.error((e as Error).message || t('desktop.settings.account.loadFailed'));
    }
  };

  useEffect(() => {
    if (currentServerId) void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentServerId]);

  if (!currentServerId) {
    return (
      <section className="set-sec">
        <h3>{t('desktop.settings.account.title')}</h3>
        <p className="desc">{t('desktop.settings.account.desc')}</p>
        <div className="card pad">
          <div className="kv">
            <span className="k2">{t('desktop.settings.notifications.noServer')}</span>
            <span className="v2">
              <button className="link-btn" onClick={() => navigate('servers')}>
                {t('desktop.settings.notifications.connect')}
              </button>
            </span>
          </div>
        </div>
      </section>
    );
  }

  const handleAddKey = async () => {
    const name = keyName.trim();
    const pk = publicKey.trim();
    if (!name || !pk) return;
    setAdding(true);
    try {
      const created = await accountApi.addSSHKey(currentServerId, { name, public_key: pk });
      setKeys((prev) => [...(prev ?? []), created]);
      setKeyName('');
      setPublicKey('');
      message.success(t('desktop.settings.account.keyAdded'));
    } catch (e) {
      message.error((e as Error).message || t('desktop.settings.account.keyAddFailed'));
    } finally {
      setAdding(false);
    }
  };

  const handleDeleteKey = async (keyId: string) => {
    try {
      await accountApi.deleteSSHKey(currentServerId, keyId);
      setKeys((prev) => (prev ?? []).filter((k) => k.id !== keyId));
      message.success(t('desktop.settings.account.keyDeleted'));
    } catch (e) {
      message.error((e as Error).message || t('desktop.settings.account.keyDeleteFailed'));
    }
  };

  const handleUnlink = async (provider: string) => {
    try {
      await accountApi.unlinkOAuth(currentServerId, provider);
      setOauth((prev) => (prev ?? []).filter((a) => a.provider !== provider));
      message.success(t('desktop.settings.account.oauthUnlinked'));
    } catch (e) {
      message.error((e as Error).message || t('desktop.settings.account.oauthUnlinkFailed'));
    }
  };

  return (
    <section className="set-sec">
      <h3>{t('desktop.settings.account.title')}</h3>
      <p className="desc">{t('desktop.settings.account.desc')}</p>

      <div className="card pad">
        <div className="sec-label">{t('desktop.settings.account.sshKeys')}</div>
        <p className="sub-hint">{t('desktop.settings.account.sshKeysDesc')}</p>
        {failed ? (
          <div className="kv">
            <span className="k2">{t('desktop.settings.account.loadFailed')}</span>
            <span className="v2">
              <button className="link-btn" onClick={() => void load()}>{t('desktop.settings.notifications.retry')}</button>
            </span>
          </div>
        ) : (
          <>
            {(keys ?? []).map((k) => (
              <div className="kv" key={k.id}>
                <span className="k2">
                  <KeyOutlined />
                  <span className="mono">{k.name}</span>
                  <span className="sub-hint">{k.fingerprint}</span>
                </span>
                <span className="v2">
                  <span className="sub-hint">{t('desktop.settings.account.keyAddedAt', { date: k.created_at.slice(0, 10) })}</span>
                  <Popconfirm
                    title={t('desktop.settings.account.keyDeleteConfirm')}
                    okButtonProps={{ danger: true }}
                    onConfirm={() => void handleDeleteKey(k.id)}
                  >
                    <button className="icon-btn sm danger" aria-label={t('desktop.settings.account.keyDeleteConfirm')}>
                      <DeleteOutlined />
                    </button>
                  </Popconfirm>
                </span>
              </div>
            ))}
            {(keys ?? []).length === 0 && (
              <p className="sub-hint">{t('desktop.settings.account.noKeys')}</p>
            )}
          </>
        )}
        <div className="kv" style={{ marginTop: 10 }}>
          <span className="k2">{t('desktop.settings.account.keyName')}</span>
          <span className="v2">
            <input
              className="set-input"
              value={keyName}
              onChange={(e) => setKeyName(e.target.value)}
              placeholder={t('desktop.settings.account.keyNamePh')}
            />
          </span>
        </div>
        <div className="kv">
          <span className="k2">{t('desktop.settings.account.publicKey')}</span>
          <span className="v2">
            <input
              className="set-input mono"
              style={{ minWidth: 320 }}
              value={publicKey}
              onChange={(e) => setPublicKey(e.target.value)}
              placeholder={t('desktop.settings.account.publicKeyPh')}
            />
          </span>
        </div>
        <div className="kv">
          <span className="k2" />
          <span className="v2">
            <button className="btn ghost" disabled={adding || !keyName.trim() || !publicKey.trim()} onClick={() => void handleAddKey()}>
              <PlusOutlined />
              {t('desktop.settings.account.addKey')}
            </button>
          </span>
        </div>
      </div>

      <div className="card pad">
        <div className="sec-label">{t('desktop.settings.account.oauth')}</div>
        <p className="sub-hint">{t('desktop.settings.account.oauthDesc')}</p>
        {(oauth ?? []).map((a) => (
          <div className="kv" key={a.provider}>
            <span className="k2">
              <LinkOutlined />
              <span className="mono">{a.provider}</span>
              <span className="sub-hint">{a.provider_username}</span>
            </span>
            <span className="v2">
              <span className="sub-hint">{t('desktop.settings.account.keyAddedAt', { date: a.created_at.slice(0, 10) })}</span>
              <Popconfirm
                title={t('desktop.settings.account.oauthUnlinkConfirm')}
                okButtonProps={{ danger: true }}
                onConfirm={() => void handleUnlink(a.provider)}
              >
                <button className="icon-btn sm danger">{t('desktop.settings.account.oauthUnlink')}</button>
              </Popconfirm>
            </span>
          </div>
        ))}
        {(oauth ?? []).length === 0 && (
          <p className="sub-hint">{t('desktop.settings.account.noOauth')}</p>
        )}
      </div>
    </section>
  );
}
