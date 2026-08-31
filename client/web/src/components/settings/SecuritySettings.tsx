import { useEffect, useState } from 'react';
import { Card, Input, Button, Popconfirm, message } from 'antd';
import { KeyOutlined, DeleteOutlined, PlusOutlined, LinkOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { settingsApi, type SSHKey, type OAuthAccount } from '../../api/settings';

const borderColor = '#21262d';
const textSecondary = '#8b949e';
const textPrimary = '#e6edf3';
const textTertiary = '#6e7681';
const bluePrimary = '#1f6feb';
const bgSecondary = '#161b22';
const bgTertiary = '#1c2128';
const danger = '#f85149';

export default function SecuritySettings() {
  const { t } = useTranslation();
  const [keys, setKeys] = useState<SSHKey[]>([]);
  const [accounts, setAccounts] = useState<OAuthAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [name, setName] = useState('');
  const [publicKey, setPublicKey] = useState('');
  const [adding, setAdding] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [unlinking, setUnlinking] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const [keyList, accList] = await Promise.all([
          settingsApi.listSSHKeys(),
          settingsApi.listOAuthAccounts(),
        ]);
        if (!cancelled) {
          setKeys(keyList);
          setAccounts(accList);
        }
      } catch {
        // 加载失败保持空态
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    Promise.resolve().then(() => load());
    return () => { cancelled = true; };
  }, []);

  const handleAddKey = async () => {
    const trimmedName = name.trim();
    const trimmedKey = publicKey.trim();
    if (!trimmedName || !trimmedKey) return;
    setAdding(true);
    try {
      const key = await settingsApi.addSSHKey({ name: trimmedName, public_key: trimmedKey });
      setKeys((prev) => [...prev, key]);
      setName('');
      setPublicKey('');
      message.success(t('app.settings.keyAdded'));
    } catch (err) {
      message.error((err as Error).message || t('app.settings.keyAddFailed'));
    } finally {
      setAdding(false);
    }
  };

  const handleDeleteKey = async (keyId: string) => {
    setDeletingId(keyId);
    try {
      await settingsApi.deleteSSHKey(keyId);
      setKeys((prev) => prev.filter((k) => k.id !== keyId));
      message.success(t('app.settings.keyDeleted'));
    } catch (err) {
      message.error((err as Error).message || t('app.settings.keyDeleteFailed'));
    } finally {
      setDeletingId(null);
    }
  };

  const handleUnlink = async (provider: string) => {
    setUnlinking(provider);
    try {
      await settingsApi.unlinkOAuth(provider);
      setAccounts((prev) => prev.filter((a) => a.provider !== provider));
      message.success(t('app.settings.oauthUnlinked'));
    } catch (err) {
      message.error((err as Error).message || t('app.settings.oauthUnlinkFailed'));
    } finally {
      setUnlinking(null);
    }
  };

  const providerLabel = (provider: string) =>
    provider.charAt(0).toUpperCase() + provider.slice(1);

  return (
    <Card
      style={{ border: `1px solid ${borderColor}`, background: bgSecondary }}
      styles={{ body: { padding: 24 } }}
    >
      <div style={{ marginBottom: 20 }}>
        <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 4, color: textPrimary }}>
          {t('app.settings.security')}
        </h2>
        <p style={{ fontSize: 13, color: textSecondary, margin: 0 }}>
          {t('app.settings.securityDesc')}
        </p>
      </div>

      {/* SSH Keys */}
      <div style={{ marginBottom: 12 }}>
        <h3 style={{ fontSize: 15, fontWeight: 600, color: textPrimary, marginBottom: 4 }}>
          {t('app.settings.sshKeys')}
        </h3>
        <p style={{ fontSize: 13, color: textSecondary, margin: 0 }}>
          {t('app.settings.sshKeysDesc')}
        </p>
      </div>

      <Input
        placeholder={t('app.settings.sshKeyName')}
        value={name}
        onChange={(e) => setName(e.target.value)}
        maxLength={100}
        style={{ background: bgTertiary, borderColor, color: textPrimary, marginBottom: 8 }}
      />
      <Input.TextArea
        placeholder={t('app.settings.sshPublicKey')}
        value={publicKey}
        onChange={(e) => setPublicKey(e.target.value)}
        rows={4}
        autoSize={{ minRows: 4, maxRows: 8 }}
        style={{ background: bgTertiary, borderColor, color: textPrimary, fontFamily: 'monospace', fontSize: 12 }}
      />
      <div style={{ display: 'flex', gap: 8, marginTop: 8, marginBottom: 20 }}>
        <Button
          type="primary"
          icon={<PlusOutlined style={{ fontSize: 12 }} />}
          loading={adding}
          disabled={!name.trim() || !publicKey.trim()}
          onClick={handleAddKey}
          style={{ background: bluePrimary, borderColor: bluePrimary, borderRadius: 8, fontSize: 13, height: 34 }}
        >
          {t('app.settings.addKey')}
        </Button>
      </div>

      {loading ? null : keys.length === 0 ? (
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '14px 0', color: textTertiary, fontSize: 13, borderBottom: `1px solid ${borderColor}` }}>
          <KeyOutlined /> {t('app.settings.noKeys')}
        </div>
      ) : (
        <div style={{ marginBottom: 28 }}>
          {keys.map((key) => (
            <div
              key={key.id}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 12,
                padding: '12px 0',
                borderBottom: `1px solid ${borderColor}`,
              }}
            >
              <KeyOutlined style={{ fontSize: 16, color: textSecondary, flexShrink: 0 }} />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 13, fontWeight: 600, color: textPrimary }}>{key.name}</div>
                <div
                  style={{
                    fontSize: 12,
                    color: textTertiary,
                    fontFamily: 'monospace',
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                  }}
                >
                  {key.fingerprint}
                </div>
                <div style={{ fontSize: 11, color: textTertiary }}>
                  {t('app.settings.keyAddedAt', { time: new Date(key.created_at).toLocaleString() })}
                </div>
              </div>
              <Popconfirm
                title={t('app.settings.keyDeleteConfirm')}
                okText={t('common.confirm')}
                cancelText={t('common.cancel')}
                okButtonProps={{ style: { background: danger } }}
                onConfirm={() => handleDeleteKey(key.id)}
              >
                <Button
                  type="text"
                  loading={deletingId === key.id}
                  icon={<DeleteOutlined style={{ color: danger }} />}
                  style={{ borderRadius: 6 }}
                />
              </Popconfirm>
            </div>
          ))}
        </div>
      )}

      {/* OAuth accounts */}
      <div style={{ marginBottom: 12 }}>
        <h3 style={{ fontSize: 15, fontWeight: 600, color: textPrimary, marginBottom: 4 }}>
          {t('app.settings.oauthAccounts')}
        </h3>
        <p style={{ fontSize: 13, color: textSecondary, margin: 0 }}>
          {t('app.settings.oauthAccountsDesc')}
        </p>
      </div>

      {loading ? null : accounts.length === 0 ? (
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '14px 0', color: textTertiary, fontSize: 13 }}>
          <LinkOutlined /> {t('app.settings.noOauthAccounts')}
        </div>
      ) : (
        <div>
          {accounts.map((acc) => (
            <div
              key={acc.provider}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 12,
                padding: '12px 0',
                borderBottom: `1px solid ${borderColor}`,
              }}
            >
              <LinkOutlined style={{ fontSize: 16, color: textSecondary, flexShrink: 0 }} />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 13, fontWeight: 600, color: textPrimary }}>
                  {providerLabel(acc.provider)}
                </div>
                <div style={{ fontSize: 12, color: textTertiary }}>@{acc.provider_username}</div>
                <div style={{ fontSize: 11, color: textTertiary }}>
                  {t('app.settings.keyAddedAt', { time: new Date(acc.created_at).toLocaleString() })}
                </div>
              </div>
              <Popconfirm
                title={t('app.settings.oauthUnlinkConfirm', { provider: providerLabel(acc.provider) })}
                okText={t('common.confirm')}
                cancelText={t('common.cancel')}
                okButtonProps={{ style: { background: danger } }}
                onConfirm={() => handleUnlink(acc.provider)}
              >
                <Button
                  type="text"
                  loading={unlinking === acc.provider}
                  style={{ color: textSecondary, fontSize: 13, height: 30 }}
                >
                  {t('app.settings.oauthUnlink')}
                </Button>
              </Popconfirm>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}