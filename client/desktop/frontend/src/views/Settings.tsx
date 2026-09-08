import { useState } from 'react';
import { App as AntApp, Select, Tooltip } from 'antd';
import { useTranslation } from 'react-i18next';
import {
  CloudServerOutlined,
  GlobalOutlined,
  EditOutlined,
  KeyOutlined,
  InfoCircleOutlined,
  CopyOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { useGatewayStore } from '../stores/gateway';
import { useServersStore } from '../stores/servers';
import { useWorkspaceStore } from '../stores/workspace';
import { useNavigationStore } from '../stores/navigation';
import Brand from '../components/Brand';

const LANGUAGES = [
  { value: 'zh', label: '中文（简体）' },
  { value: 'en', label: 'English' },
];

type Section = 'gateway' | 'appearance' | 'editor' | 'keys' | 'about';

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