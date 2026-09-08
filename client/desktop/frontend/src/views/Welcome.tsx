import { useState } from 'react';
import { App as AntApp, Input, Modal, Tooltip } from 'antd';
import { useTranslation } from 'react-i18next';
import {
  CloudServerOutlined,
  DownloadOutlined,
  FolderOpenOutlined,
  FolderOutlined,
  KeyOutlined,
  NodeIndexOutlined,
} from '@ant-design/icons';
import { createWorkspace, listWorkspaces, Workspace } from '../api/workspaces';
import { useWorkspaceStore } from '../stores/workspace';
import { useServersStore } from '../stores/servers';
import { useGatewayStore } from '../stores/gateway';
import { useNavigationStore } from '../stores/navigation';
import { timeAgo } from '../utils/time';
import Brand from '../components/Brand';

function gatewayHost(baseURL: string | undefined): string {
  return (baseURL ?? '').replace(/^https?:\/\//, '').replace(/\/$/, '');
}

export default function Welcome() {
  const { t } = useTranslation();
  const { message } = AntApp.useApp();
  const workspaces = useWorkspaceStore((s) => s.workspaces);
  const setWorkspaces = useWorkspaceStore((s) => s.setWorkspaces);
  const setCurrent = useWorkspaceStore((s) => s.setCurrent);
  const touch = useWorkspaceStore((s) => s.touch);
  const servers = useServersStore((s) => s.servers);
  const setCurrentServer = useServersStore((s) => s.setCurrent);
  const config = useGatewayStore((s) => s.config);
  const navigate = useNavigationStore((s) => s.navigate);

  const [url, setUrl] = useState('');
  const [token, setToken] = useState('');
  const [cloneOpen, setCloneOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const recent = [...workspaces]
    .sort((a, b) => (b.last_opened_at ?? '').localeCompare(a.last_opened_at ?? '') || 0);

  const openFolder = async () => {
    const dir = await window.go?.main.App.OpenFolderDialog();
    if (!dir) return;
    setBusy(true);
    try {
      await createWorkspace({ name: dir.split(/[\\/]/).pop() ?? 'ws', path: dir });
      setWorkspaces(await listWorkspaces());
      message.success(dir);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };

  const openWorkspace = (ws: Workspace) => {
    touch(ws.id);
    setCurrent(ws);
  };

  const openServer = (id: string) => {
    setCurrentServer(id);
    navigate('repositories');
  };

  const clone = async () => {
    if (!url.trim()) return;
    setBusy(true);
    try {
      const name = url.split('/').pop()?.replace(/\.git$/, '') ?? 'repo';
      await createWorkspace({
        name,
        path: '',
        url: url.trim(),
        clone: true,
        credential: token.trim() ? { type: 'token', token: token.trim() } : undefined,
      });
      setWorkspaces(await listWorkspaces());
      setUrl('');
      setToken('');
      setCloneOpen(false);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };

  const icons = {
    servers: <CloudServerOutlined />,
    folder: <FolderOpenOutlined />,
    clone: <DownloadOutlined />,
  };

  return (
    <div className="welcome-body scroll">
      <div className="welcome-grid">
        <div className="welcome-brand">
          <Brand size={56} />
          <h1>Perseus Desktop</h1>
          <p className="wb-tagline">
            {t('desktop.welcome.tagline')}
            <br />
            {t('desktop.welcome.tagline2')}
          </p>
          <div className="wb-meta">
            <span className="pill blue">v0.4.0</span>
            <span className="pill">Windows</span>
            <span className="pill mono">Wails v2</span>
            <span className="pill green">{t('desktop.welcome.gatewayStatus')}</span>
          </div>
          <div className="wb-actions">
            <button className="wb-action" onClick={() => navigate('servers')}>
              {icons.servers}
              <b>{t('desktop.welcome.actions.connect')}</b>
              <span>{t('desktop.welcome.actions.connectDesc')}</span>
            </button>
            <button className="wb-action" onClick={openFolder} disabled={busy}>
              {icons.folder}
              <b>{t('desktop.welcome.actions.openLocal')}</b>
              <span>{t('desktop.welcome.actions.openLocalDesc')}</span>
            </button>
            <button className="wb-action" onClick={() => { setError(null); setCloneOpen(true); }}>
              {icons.clone}
              <b>{t('desktop.welcome.actions.clone')}</b>
              <span>{t('desktop.welcome.actions.cloneDesc')}</span>
            </button>
          </div>
          <div className="wb-hint">
            <span className="keys"><kbd>Ctrl</kbd><kbd>K</kbd> <span>{t('desktop.welcome.hints.commandPalette')}</span></span>
            <span className="hb-sep">·</span>
            <span className="keys"><kbd>Ctrl</kbd><kbd>S</kbd> <span>{t('desktop.welcome.hints.save')}</span></span>
            <span className="hb-sep">·</span>
            <span className="keys"><kbd>Ctrl</kbd><kbd>B</kbd> <span>{t('desktop.welcome.hints.sidebar')}</span></span>
            <span className="hb-sep">·</span>
            <span className="keys"><kbd>Ctrl</kbd><kbd>`</kbd> <span>{t('desktop.welcome.hints.terminal')}</span></span>
          </div>
        </div>

        <div className="welcome-side">
          <div className="card">
            <div className="card-h">
              <b>{t('desktop.welcome.recent')}</b>
              <button className="btn sm ghost" onClick={() => message.info(t('desktop.portal.phase2'))}>
                {t('desktop.welcome.viewAll')}
              </button>
            </div>
            {recent.length === 0 ? (
              <div className="empty-row">{t('desktop.welcome.noWorkspaces')}</div>
            ) : (
              recent.map((ws) => (
                <div className="ws-row" key={ws.id}>
                  <span className="ic"><FolderOutlined /></span>
                  <div className="ws-main">
                    <b>{ws.name}</b>
                    <span className="mono">{ws.path || ws.remote_url || ''}</span>
                  </div>
                  <div className="ws-side">
                    {ws.branch ? (
                      <span className="pill"><NodeIndexOutlined className="pill-ic" />{t('desktop.welcome.recentUpdated', { branch: ws.branch, time: timeAgo(ws.last_opened_at, t) })}</span>
                    ) : (
                      <span className="pill">{timeAgo(ws.last_opened_at, t)}</span>
                    )}
                    <button className="btn sm primary" onClick={() => openWorkspace(ws)}>{t('desktop.welcome.open')}</button>
                  </div>
                </div>
              ))
            )}
          </div>

          <div className="card">
            <div className="card-h">
              <b>{t('desktop.welcome.servers')}</b>
              <button className="btn sm ghost" onClick={() => navigate('servers')}>
                {t('desktop.welcome.serverRowManage')}
              </button>
            </div>
            {servers.length === 0 ? (
              <div className="empty-row">{t('desktop.servers.empty')}</div>
            ) : (
              servers.map((s) => (
                <div className="ws-row clickable" key={s.id} onClick={() => openServer(s.id)}>
                  <span className={`dot ${s.health}`} />
                  <div className="ws-main">
                    <b>{s.name}</b>
                    <span className="mono">
                      {s.base_url.replace(/^https?:\/\//, '')}
                      {s.id === (useServersStore.getState().currentServerId) ? ` · ${t('desktop.welcome.serverRowCurrent')}` : s.health === 'offline' ? ` · ${t('desktop.welcome.serverRowOffline')}` : ''}
                    </span>
                  </div>
                  <div className="ws-side"><span className="chev">{'\u203A'}</span></div>
                </div>
              ))
            )}
          </div>

          <div className="wb-status">
            <span className="dot on" />
            {t('desktop.welcome.gatewayStatus')}
            <span className="hb-sep">·</span>
            <span className="mono">{gatewayHost(config?.baseURL)}</span>
          </div>
        </div>
      </div>

      <Modal
        open={cloneOpen}
        title={t('desktop.welcome.actions.clone')}
        okText={t('desktop.welcome.clone')}
        confirmLoading={busy}
        onCancel={() => setCloneOpen(false)}
        onOk={clone}
      >
        <div className="field">
          <label>{t('desktop.welcome.cloneTitle')}</label>
          <Input
            placeholder={t('desktop.welcome.clonePlaceholder')}
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            onPressEnter={clone}
          />
        </div>
        <div className="field">
          <label>{t('desktop.welcome.cloneCredential')}</label>
          <Input.Password
            prefix={<KeyOutlined />}
            placeholder={t('desktop.welcome.cloneCredentialPh')}
            value={token}
            onChange={(e) => setToken(e.target.value)}
          />
        </div>
        {error && <div className="error-text">{error}</div>}
        <div className="hint">
          <Tooltip title={t('desktop.welcome.actions.cloneDesc')}>
            <DownloadOutlined className="hint-ic" />
          </Tooltip>
          {t('desktop.welcome.actions.cloneDesc')}
        </div>
      </Modal>
    </div>
  );
}