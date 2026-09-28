import { useCallback, useEffect, useState } from 'react';
import { Button, Spin, Empty, Popconfirm, Tag, message } from 'antd';
import { BranchesOutlined, SafetyCertificateOutlined, SafetyOutlined, DeleteOutlined, StarOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { repositoriesApi } from '../../api/repositories';
import type { RepoBranch } from '../../api/repositories';

const borderColor = '#21262d';
const hoverBg = '#1c2333';
const textPrimary = '#e6edf3';
const textSecondary = '#8b949e';
const textTertiary = '#6e7681';
const bgSecondary = '#161b22';
const blue = '#58a6ff';
const amber = '#d29922';

export default function BranchesTab({ repoId }: { repoId: string }) {
  const { t } = useTranslation();
  const [branches, setBranches] = useState<RepoBranch[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setBranches(await repositoriesApi.getBranches(repoId));
    } catch {
      setBranches([]);
    } finally {
      setLoading(false);
    }
  }, [repoId]);

  useEffect(() => {
    Promise.resolve().then(load);
  }, [load]);

  const handleToggleProtect = async (branch: RepoBranch) => {
    setBusy(branch.name);
    try {
      if (branch.is_protected) {
        await repositoriesApi.unprotectBranch(repoId, branch.name);
      } else {
        await repositoriesApi.protectBranch(repoId, branch.name);
      }
      await load();
    } catch (e) {
      message.error((e as Error).message || t('app.repositories.gitBrowser.actionFailed'));
    } finally {
      setBusy(null);
    }
  };

  const handleSetDefault = async (branch: RepoBranch) => {
    setBusy(branch.name);
    try {
      await repositoriesApi.setDefaultBranch(repoId, branch.name);
      message.success(t('app.repositories.gitBrowser.defaultSet', { name: branch.name }));
      await load();
    } catch (e) {
      message.error((e as Error).message || t('app.repositories.gitBrowser.actionFailed'));
    } finally {
      setBusy(null);
    }
  };

  const handleDelete = async (branch: RepoBranch) => {
    setBusy(branch.name);
    try {
      await repositoriesApi.deleteBranch(repoId, branch.name);
      message.success(t('app.repositories.gitBrowser.branchDeleted', { name: branch.name }));
      await load();
    } catch (e) {
      message.error((e as Error).message || t('app.repositories.gitBrowser.actionFailed'));
    } finally {
      setBusy(null);
    }
  };

  return (
    <div>
      <h3 style={{ fontSize: 16, fontWeight: 600, margin: '0 0 16px', color: textPrimary, display: 'flex', alignItems: 'center', gap: 8 }}>
        <BranchesOutlined style={{ color: blue }} />
        {t('app.repositories.gitBrowser.branchesTitle', { count: branches.length })}
      </h3>

      {loading && branches.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 48 }}><Spin /></div>
      ) : branches.length === 0 ? (
        <div style={{ border: `1px solid ${borderColor}`, borderRadius: 12, background: bgSecondary }}>
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={<span style={{ color: textSecondary }}>{t('app.repositories.gitBrowser.noBranches')}</span>} style={{ padding: 40 }} />
        </div>
      ) : (
        <div style={{ border: `1px solid ${borderColor}`, borderRadius: 12, overflow: 'hidden', background: bgSecondary }}>
          {branches.map((b, i) => (
            <div
              key={b.id || b.name}
              style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '11px 16px', borderBottom: i === branches.length - 1 ? 'none' : `1px solid ${borderColor}`, fontSize: 13 }}
              onMouseEnter={(e) => { e.currentTarget.style.background = hoverBg; }}
              onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
            >
              <BranchesOutlined style={{ color: textTertiary, flexShrink: 0 }} />
              <span style={{ color: textPrimary, fontWeight: 600, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{b.name}</span>
              {b.is_default && (
                <Tag style={{ color: amber, borderColor: `${amber}66`, background: 'transparent', fontSize: 11 }}>{t('app.repositories.gitBrowser.default')}</Tag>
              )}
              {b.is_protected && (
                <Tag style={{ color: blue, borderColor: `${blue}66`, background: 'transparent', fontSize: 11 }}>{t('app.repositories.gitBrowser.protected')}</Tag>
              )}
              <span style={{ fontFamily: 'monospace', color: textTertiary, fontSize: 12, marginLeft: 'auto', flexShrink: 0 }}>{b.commit_hash?.slice(0, 7)}</span>
              <div style={{ display: 'flex', gap: 4, flexShrink: 0 }}>
                <Button
                  size="small"
                  type="text"
                  loading={busy === b.name}
                  icon={b.is_protected ? <SafetyCertificateOutlined style={{ color: blue }} /> : <SafetyOutlined />}
                  title={b.is_protected ? t('app.repositories.gitBrowser.unprotect') : t('app.repositories.gitBrowser.protect')}
                  onClick={() => handleToggleProtect(b)}
                />
                <Button
                  size="small"
                  type="text"
                  disabled={b.is_default || busy === b.name}
                  icon={<StarOutlined />}
                  title={t('app.repositories.gitBrowser.setDefault')}
                  onClick={() => handleSetDefault(b)}
                />
                <Popconfirm
                  title={t('app.repositories.gitBrowser.deleteBranchConfirm', { name: b.name })}
                  onConfirm={() => handleDelete(b)}
                  disabled={b.is_default}
                >
                  <Button size="small" type="text" danger disabled={b.is_default || busy === b.name} icon={<DeleteOutlined />} />
                </Popconfirm>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
