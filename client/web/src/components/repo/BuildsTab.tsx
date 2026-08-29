import { useCallback, useEffect, useState } from 'react';
import { Button, Empty, Spin, Modal, Dropdown, Tag, message } from 'antd';
import { PlayCircleOutlined, ReloadOutlined, FileTextOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { buildsApi, type Build } from '../../api/builds';

const textPrimary = '#e6edf3';
const textSecondary = '#8b949e';
const textTertiary = '#6e7681';
const borderColor = '#21262d';
const bgSecondary = '#161b22';
const bgTertiary = '#1c2128';

const statusColors: Record<string, string> = {
  pending: '#8b949e',
  running: '#58a6ff',
  success: '#3fb950',
  failure: '#f85149',
  error: '#f85149',
  cancelled: '#6e7681',
};

function statusColor(s: string): string {
  return statusColors[s] ?? textSecondary;
}

export default function BuildsTab({ repoId }: { repoId: string }) {
  const { t } = useTranslation();
  const [builds, setBuilds] = useState<Build[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');
  const [logsOpen, setLogsOpen] = useState(false);
  const [logTarget, setLogTarget] = useState<Build | null>(null);
  const [logs, setLogs] = useState('');
  const [logsLoading, setLogsLoading] = useState(false);

  const load = useCallback(async () => {
    try {
      const data = await buildsApi.list(repoId);
      setBuilds(data);
    } catch {
      setBuilds([]);
    } finally {
      setLoading(false);
    }
  }, [repoId]);

  useEffect(() => {
    // 微任务延迟, 避免在 effect 同步体中触发级联渲染
    Promise.resolve().then(load);
  }, [load]);

  const openLogs = async (build: Build) => {
    setLogTarget(build);
    setLogsOpen(true);
    setLogsLoading(true);
    setLogs('');
    try {
      const res = await buildsApi.getLogs(repoId, build.id);
      setLogs(res.logs || '');
    } catch {
      message.error(t('app.repositories.builds.logsFailed'));
      setLogs('');
    } finally {
      setLogsLoading(false);
    }
  };

  const shown = filter === 'all' ? builds : builds.filter((b) => b.status === filter);

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
        <h3 style={{ fontSize: 16, fontWeight: 600, margin: 0, color: textPrimary, display: 'flex', alignItems: 'center', gap: 8 }}>
          <PlayCircleOutlined style={{ color: '#58a6ff' }} />
          {t('app.repositories.builds.title')}
        </h3>
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 8 }}>
          <Dropdown
            menu={{
              items: [
                { key: 'all', label: t('app.repositories.builds.filterAll') },
                { key: 'success', label: t('app.repositories.builds.success') },
                { key: 'failure', label: t('app.repositories.builds.failure') },
                { key: 'running', label: t('app.repositories.builds.running') },
                { key: 'pending', label: t('app.repositories.builds.pending') },
              ],
              onClick: ({ key }) => setFilter(key),
            }}
          >
            <Button size="small">{t('app.repositories.builds.filter')}: {t(`app.repositories.builds.${filter}`)}</Button>
          </Dropdown>
          <Button size="small" icon={<ReloadOutlined />} onClick={load} />
        </div>
      </div>

      {loading && builds.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 48 }}><Spin /></div>
      ) : shown.length === 0 ? (
        <div style={{ border: `1px solid ${borderColor}`, borderRadius: 12, background: bgSecondary }}>
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description={<span style={{ color: textSecondary }}>{t('app.repositories.builds.empty')}</span>}
            style={{ padding: 40 }}
          />
        </div>
      ) : (
        <div style={{ border: `1px solid ${borderColor}`, borderRadius: 12, overflow: 'hidden', background: bgSecondary }}>
          <div style={{ display: 'grid', gridTemplateColumns: '120px 1fr 120px', padding: '10px 16px', background: bgTertiary, fontSize: 12, color: textTertiary, borderBottom: `1px solid ${borderColor}` }}>
            <span>{t('app.repositories.builds.status')}</span>
            <span>{t('app.repositories.builds.commit')}</span>
            <span style={{ textAlign: 'right' }}>{t('app.repositories.builds.time')}</span>
          </div>
          {shown.map((b) => (
            <div
              key={b.id}
              style={{
                display: 'grid',
                gridTemplateColumns: '120px 1fr 120px',
                padding: '12px 16px',
                borderBottom: `1px solid ${borderColor}`,
                cursor: 'pointer',
                transition: 'background 0.15s',
              }}
              onClick={() => openLogs(b)}
              onMouseEnter={(e) => { e.currentTarget.style.background = '#1c2333'; }}
              onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
            >
              <span>
                <Tag color="default" style={{ color: statusColor(b.status), borderColor: statusColor(b.status), background: 'transparent' }}>
                  {t(`app.repositories.builds.${b.status}`)}
                </Tag>
              </span>
              <span style={{ minWidth: 0 }}>
                <span style={{ fontFamily: 'monospace', color: textPrimary, fontSize: 13 }}>{b.commit_sha.slice(0, 7)}</span>
                <span style={{ color: textSecondary, fontSize: 13, marginLeft: 8, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', display: 'inline-block', maxWidth: '70%', verticalAlign: 'bottom' }}>
                  {b.commit_message}
                </span>
                <span style={{ color: textTertiary, fontSize: 12, marginLeft: 8 }}>{b.branch}</span>
              </span>
              <span style={{ textAlign: 'right', color: textTertiary, fontSize: 12 }}>
                {b.started_at ? new Date(b.started_at).toLocaleString() : '—'}
              </span>
            </div>
          ))}
        </div>
      )}

      <Modal
        title={<span style={{ color: textPrimary }}>{logTarget ? `${t('app.repositories.builds.logs')} · ${logTarget.commit_sha.slice(0, 7)}` : ''}</span>}
        open={logsOpen}
        onCancel={() => setLogsOpen(false)}
        footer={null}
        width={720}
      >
        <div style={{ maxHeight: 420, overflow: 'auto', background: '#0d1117', border: `1px solid ${borderColor}`, borderRadius: 8, padding: 14 }}>
          {logsLoading ? (
            <div style={{ textAlign: 'center', padding: 24 }}><Spin /></div>
          ) : logs ? (
            <pre style={{ margin: 0, fontSize: 12.5, lineHeight: 1.6, color: textPrimary, fontFamily: "'JetBrains Mono','Fira Code','Consolas',monospace", whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
              {logs}
            </pre>
          ) : (
            <div style={{ textAlign: 'center', padding: 24, color: textTertiary }}>
              <FileTextOutlined style={{ fontSize: 24 }} />
              <p style={{ marginTop: 8 }}>{t('app.repositories.builds.noLogs')}</p>
            </div>
          )}
        </div>
      </Modal>
    </div>
  );
}
