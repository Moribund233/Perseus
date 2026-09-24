import { useEffect, useMemo, useRef, useState } from 'react';
import { App } from 'antd';
import {
  AimOutlined,
  ApiOutlined,
  BookOutlined,
  BranchesOutlined,
  CheckCircleOutlined,
  CloudServerOutlined,
  CodeOutlined,
  ControlOutlined,
  CopyOutlined,
  DashboardOutlined,
  DatabaseOutlined,
  DeploymentUnitOutlined,
  DesktopOutlined,
  DisconnectOutlined,
  DownOutlined,
  ExclamationCircleOutlined,
  FileTextOutlined,
  FolderOpenOutlined,
  GatewayOutlined,
  GithubOutlined,
  HddOutlined,
  HeartOutlined,
  HomeOutlined,
  LaptopOutlined,
  LockOutlined,
  MailOutlined,
  MessageOutlined,
  PullRequestOutlined,
  RiseOutlined,
  RocketOutlined,
  SafetyCertificateOutlined,
  SearchOutlined,
  SettingOutlined,
  SlidersOutlined,
  SwapOutlined,
  TagsOutlined,
  TeamOutlined,
  ThunderboltOutlined,
  TranslationOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useAuthStore } from '../../stores/auth';
import { statsApi, type PlatformStats } from '../../api/stats';
import Logo from '../../components/brand/Logo';
import AuthModal from './AuthModal';
import './landing.css';

function formatCount(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

function formatUptime(seconds: number): string {
  const days = Math.floor(seconds / 86400);
  if (days > 0) return `${days}d`;
  const hours = Math.floor(seconds / 3600);
  if (hours > 0) return `${hours}h`;
  const mins = Math.floor(seconds / 60);
  return `${mins}m`;
}

const FEATURES = [
  { key: 'codeHosting', icon: <FolderOpenOutlined />, tone: 'primary' },
  { key: 'pullRequests', icon: <PullRequestOutlined />, tone: 'primary' },
  { key: 'issueTracking', icon: <ExclamationCircleOutlined />, tone: 'accent' },
  { key: 'realtimeCollab', icon: <TeamOutlined />, tone: 'accent' },
  { key: 'codeSearch', icon: <SearchOutlined />, tone: 'primary' },
  { key: 'webhooks', icon: <ApiOutlined />, tone: 'primary' },
  { key: 'releaseManagement', icon: <TagsOutlined />, tone: 'accent' },
  { key: 'adminMonitoring', icon: <SettingOutlined />, tone: 'accent' },
] as const;

const TECH = [
  { key: 'fastapi', mark: 'F', cls: 'fastapi' },
  { key: 'react', mark: 'R', cls: 'react' },
  { key: 'postgres', mark: 'PG', cls: 'postgres round' },
  { key: 'redis', mark: 'R', cls: 'redis' },
  { key: 'docker', mark: 'D', cls: 'docker' },
  { key: 'wails', mark: 'W', cls: 'wails' },
  { key: 'git', mark: 'G', cls: 'git' },
] as const;

const COLLAB_ITEMS = [
  { key: 'liveCursors', icon: <AimOutlined /> },
  { key: 'crdtEngine', icon: <SwapOutlined /> },
  { key: 'chat', icon: <MessageOutlined /> },
] as const;

const DESKTOP_ITEMS = [
  { key: 'wails', icon: <DeploymentUnitOutlined /> },
  { key: 'offline', icon: <DisconnectOutlined /> },
  { key: 'terminal', icon: <CodeOutlined /> },
] as const;

const ARCH_BENEFITS = [
  { key: 'privacy', icon: <SafetyCertificateOutlined /> },
  { key: 'control', icon: <ControlOutlined /> },
  { key: 'deploy', icon: <RocketOutlined /> },
  { key: 'security', icon: <LockOutlined /> },
] as const;

const ADMIN_CHART = [40, 55, 45, 70, 85, 95, 75, 60, 50, 65, 80, 90];

const ADMIN_LOGS = [
  { tag: 'INFO', tagCls: 'tag-info', text: '[api] GET /api/v1/repos — 200 OK (18ms)' },
  { tag: 'WS', tagCls: 'tag-ws', text: '[collab] User alice joined session repo:42:file:app.py' },
  { tag: 'INFO', tagCls: 'tag-info', text: '[git] push refs/heads/main by bob — 3 objects pushed' },
  { tag: 'WARN', tagCls: 'tag-warn', text: '[webhook] Delivery #847 to https://ci.example.com retry 1/3' },
  { tag: 'WS', tagCls: 'tag-ws', text: '[chat] New message in #general from charlie' },
  { tag: 'INFO', tagCls: 'tag-info', text: '[api] POST /api/v1/prs/128/merge — 200 OK (124ms)' },
];

export default function LandingPage() {
  const [authOpen, setAuthOpen] = useState(false);
  const [authTab, setAuthTab] = useState<'login' | 'register'>('login');
  const [platformStats, setPlatformStats] = useState<PlatformStats | null>(null);
  const [scrolled, setScrolled] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const { t, i18n } = useTranslation();
  const { message } = App.useApp();

  useEffect(() => {
    let cancelled = false;
    statsApi
      .getPlatformStats()
      .then((data) => {
        if (!cancelled) setPlatformStats(data);
      })
      .catch(() => {
        // 静默失败，保持占位数据
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 10);
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  // Scroll-reveal: progressively reveal sections as they enter the viewport.
  useEffect(() => {
    const root = rootRef.current;
    if (!root) return;
    const nodes = Array.from(root.querySelectorAll<HTMLElement>('.reveal'));
    if (typeof IntersectionObserver === 'undefined') {
      nodes.forEach((n) => n.classList.add('is-visible'));
      return;
    }
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('is-visible');
            observer.unobserve(entry.target);
          }
        });
      },
      { rootMargin: '0px 0px -10% 0px', threshold: 0.12 },
    );
    nodes.forEach((n) => observer.observe(n));
    return () => observer.disconnect();
  }, []);

  const openAuth = (tab: 'login' | 'register') => {
    setAuthTab(tab);
    setAuthOpen(true);
  };

  const toggleLanguage = () => {
    const next = i18n.language.startsWith('zh') ? 'en' : 'zh';
    i18n.changeLanguage(next);
  };

  const featureTexts = t('landing.features.items', { returnObjects: true }) as Record<
    string,
    { title: string; desc: string }
  >;
  const collabTexts = t('landing.collab.items', { returnObjects: true }) as Record<
    string,
    { title: string; desc: string }
  >;
  const desktopTexts = t('landing.desktop.items', { returnObjects: true }) as Record<
    string,
    { title: string; desc: string }
  >;
  const archTexts = t('landing.architecture.benefits', { returnObjects: true }) as Record<
    string,
    { title: string; desc: string }
  >;

  const heroStats = useMemo(
    () => [
      { num: platformStats ? formatCount(platformStats.repository_count) : '--', label: t('landing.hero.stats.repositories') },
      { num: platformStats ? formatCount(platformStats.commit_count) : '--', label: t('landing.hero.stats.commits') },
      { num: platformStats ? formatCount(platformStats.user_count) : '--', label: t('landing.hero.stats.teamMembers') },
      { num: platformStats ? formatUptime(platformStats.uptime_seconds) : '--', label: t('landing.hero.stats.uptime') },
    ],
    [platformStats, t],
  );

  const copyCommand = () => {
    const cmd = 'git clone https://github.com/perseus/perseus.git && cd perseus && docker compose up -d';
    navigator.clipboard?.writeText(cmd).then(
      () => message.success(t('landing.cta.copy')),
      () => undefined,
    );
  };

  return (
    <div className="landing" ref={rootRef}>
      {/* ===== NAVBAR ===== */}
      <nav className={`l-nav${scrolled ? ' is-scrolled' : ''}`}>
        <div className="l-nav-inner">
          <a className="l-nav-logo" href="/">
            <Logo size={30} />
            Perseus
          </a>
          <div className="l-nav-links">
            <a className="l-nav-link" href="#features">{t('landing.nav.features')}</a>
            <a className="l-nav-link" href="#collab">{t('landing.nav.collaboration')}</a>
            <a className="l-nav-link" href="#desktop">{t('landing.nav.desktop')}</a>
            <a className="l-nav-link" href="#architecture">{t('landing.nav.architecture')}</a>
            <a className="l-nav-link" href="#admin">{t('landing.nav.admin')}</a>
          </div>
          <div className="l-nav-actions">
            <button className="l-nav-btn" onClick={toggleLanguage}>
              <TranslationOutlined />
              {i18n.language.startsWith('zh') ? 'EN' : '中'}
            </button>
            {isAuthenticated ? (
              <a href="/dashboard" className="l-nav-btn primary">{t('landing.nav.goToDashboard')}</a>
            ) : (
              <>
                <button className="l-nav-btn" onClick={() => openAuth('login')}>{t('landing.nav.signIn')}</button>
                <button className="l-nav-btn primary" onClick={() => openAuth('register')}>{t('landing.nav.getStarted')}</button>
              </>
            )}
          </div>
        </div>
      </nav>

      {/* ===== HERO ===== */}
      <section className="l-hero" id="hero">
        <div className="l-hero-grid" />
        <div className="l-hero-glow-1" />
        <div className="l-hero-glow-2" />
        <div className="l-container l-hero-content">
          <div className="l-hero-badge reveal">
            <span className="dot" />
            {t('landing.hero.badge')}
          </div>
          <h1 className="reveal reveal-d1">
            {t('landing.hero.titleLine1')}
            <br />
            <span className="hl">{t('landing.hero.titleLine2')}</span>
          </h1>
          <p className="l-hero-sub reveal reveal-d2">{t('landing.hero.description')}</p>
          <div className="l-hero-actions reveal reveal-d3">
            <button className="l-btn l-btn--primary" onClick={() => openAuth('register')}>
              <RocketOutlined />
              {t('landing.hero.deploy')}
            </button>
            <a
              className="l-btn l-btn--ghost"
              href="https://github.com/perseus/perseus"
              target="_blank"
              rel="noreferrer"
            >
              <GithubOutlined />
              {t('landing.hero.viewGithub')}
            </a>
          </div>

          <div className="l-hero-stats reveal reveal-d4">
            {heroStats.map((s) => (
              <div className="l-hero-stat" key={s.label}>
                <div className="num">{s.num}</div>
                <div className="label">{s.label}</div>
              </div>
            ))}
          </div>

          {/* Editor mockup */}
          <div className="l-editor-wrap reveal">
            <div className="l-editor">
            <div className="l-editor-chrome">
              <div className="l-editor-dots"><span /><span /><span /></div>
              <div className="l-editor-file">
                <span><BranchesOutlined /> {t('landing.hero.editorFile')}</span>
              </div>
              <div style={{ width: 48 }} />
            </div>
            <div className="l-editor-body">
              <div className="l-editor-tree">
                <div className="tree-title">{t('landing.hero.explorer')}</div>
                <div className="l-tree-row"><DownOutlined className="ico" /> perseus</div>
                <div className="l-tree-indent">
                  <div className="l-tree-row"><FolderOpenOutlined className="ico" /> api</div>
                  <div className="l-tree-row"><FolderOpenOutlined className="ico" /> models</div>
                  <div className="l-tree-row file active"><FileTextOutlined className="ico" /> app.py</div>
                  <div className="l-tree-row file"><FileTextOutlined className="ico" /> config.example.toml</div>
                </div>
              </div>
              <div className="l-editor-code">
                <div className="l-code-line"><span className="l-code-gutter">1</span><span className="l-code-src"><span className="c-kw">from</span> <span className="c-mod">fastapi</span> <span className="c-kw">import</span> FastAPI</span></div>
                <div className="l-code-line"><span className="l-code-gutter">2</span><span className="l-code-src"><span className="c-kw">from</span> <span className="c-mod">.core</span> <span className="c-kw">import</span> init_app</span></div>
                <div className="l-code-line"><span className="l-code-gutter">3</span><span className="l-code-src">{' '}</span></div>
                <div className="l-code-line"><span className="l-code-gutter">4</span><span className="l-code-src c-comment"># Perseus - Self-Hosted Git Platform</span></div>
                <div className="l-code-line hl"><span className="l-code-gutter">5</span><span className="l-code-src"><span className="c-mod">app</span> = <span className="c-fn">FastAPI</span>(</span></div>
                <div className="l-code-line"><span className="l-code-gutter">6</span><span className="l-code-src">    <span className="c-param">title</span>=<span className="c-str">&quot;Perseus&quot;</span>,</span></div>
                <div className="l-code-line"><span className="l-code-gutter">7</span><span className="l-code-src">    <span className="c-param">version</span>=<span className="c-str">&quot;1.0.0&quot;</span>,</span></div>
                <div className="l-code-line"><span className="l-code-gutter">8</span><span className="l-code-src">    <span className="c-param">description</span>=<span className="c-str">&quot;Self-hosted Git collaboration&quot;</span>,</span></div>
                <div className="l-code-line"><span className="l-code-gutter">9</span><span className="l-code-src">)</span></div>
                <div className="l-code-line"><span className="l-code-gutter">10</span><span className="l-code-src">{' '}</span></div>
                <div className="l-code-line"><span className="l-code-gutter">11</span><span className="l-code-src"><span className="c-kw">async def</span> <span className="c-fn">lifespan</span>(<span className="c-mod">app</span>: FastAPI):</span></div>
                <div className="l-code-line"><span className="l-code-gutter">12</span><span className="l-code-src">    <span className="c-kw">await</span> init_app.<span className="c-fn">startup</span>(app)</span></div>
                <div className="l-code-line"><span className="l-code-gutter">13</span><span className="l-code-src">    <span className="c-kw">yield</span></span></div>
                <div className="l-code-line"><span className="l-code-gutter">14</span><span className="l-code-src">    <span className="c-kw">await</span> init_app.<span className="c-fn">shutdown</span>(app)</span></div>
              </div>
              <div className="l-editor-presence">
                <div className="l-avatar a">A</div>
                <div className="l-avatar b">B</div>
                <div className="l-avatar c">C</div>
              </div>
            </div>
            <div className="l-editor-status">
              <div className="group">
                <span><BranchesOutlined /> main</span>
                <span className="live"><TeamOutlined /> {t('landing.hero.collaborators')}</span>
              </div>
              <div className="group">
                <span>Python 3.11</span>
                <span>UTF-8</span>
                <span>Ln 13, Col 28</span>
              </div>
            </div>
            </div>
            <div className="l-float-badge top-right">
              <span className="dot" /> {t('landing.hero.liveSync')}
            </div>
            <div className="l-float-badge bottom-left">
              <ThunderboltOutlined style={{ color: 'var(--p-accent)' }} /> {t('landing.hero.crdt')}
            </div>
          </div>
        </div>
      </section>

      {/* ===== TECH BAR ===== */}
      <section className="l-tech">
        <div className="l-container">
          <p className="l-tech-label">{t('landing.tech.label')}</p>
          <div className="l-tech-list">
            {TECH.map((item) => (
              <div className="l-tech-item" key={item.key}>
                <span className={`l-tech-mark ${item.cls}`}>{item.mark}</span>
                {t(`landing.tech.${item.key}`)}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ===== FEATURES ===== */}
      <section className="l-section" id="features">
        <div className="l-container">
          <div className="l-section-head reveal">
            <span className="l-eyebrow">{t('landing.features.eyebrow')}</span>
            <h2>{t('landing.features.title')}</h2>
            <p>{t('landing.features.subtitle')}</p>
          </div>
          <div className="l-features-grid">
            {FEATURES.map((f, i) => (
              <div
                className={`l-feature-card ${f.tone} reveal reveal-d${(i % 4) + 1}`}
                key={f.key}
              >
                <div className={`l-feature-icon ${f.tone}`}>{f.icon}</div>
                <h3>{featureTexts[f.key].title}</h3>
                <p>{featureTexts[f.key].desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ===== COLLAB SPOTLIGHT ===== */}
      <section className="l-section l-section--alt l-spotlight" id="collab">
        <div className="l-container">
          <div className="l-spotlight-grid">
            <div className="l-spotlight-text reveal">
              <span className="l-eyebrow l-eyebrow--accent">{t('landing.collab.eyebrow')}</span>
              <h2>{t('landing.collab.title')}</h2>
              <p>{t('landing.collab.description')}</p>
              <div className="l-spotlight-list">
                {COLLAB_ITEMS.map((item) => (
                  <div className="l-spotlight-item" key={item.key}>
                    <div className="l-spotlight-icon">{item.icon}</div>
                    <div>
                      <h4>{collabTexts[item.key].title}</h4>
                      <p>{collabTexts[item.key].desc}</p>
                    </div>
                  </div>
                ))}
              </div>
              <div className="l-collab-people">
                <div className="l-avatar-stack">
                  <div className="l-avatar a">A</div>
                  <div className="l-avatar b">B</div>
                  <div className="l-avatar c">C</div>
                </div>
                {t('landing.collab.editingNow')}
              </div>
            </div>

            <div className="reveal reveal-d2" style={{ position: 'relative' }}>
              <div className="l-mini-editor">
                <div className="l-mini-head">
                  <div className="file">
                    <CodeOutlined className="ico" />
                    <span style={{ fontFamily: 'var(--p-mono)' }}>auth_controller.py</span>
                    <span className="branch">main</span>
                  </div>
                  <div className="l-mini-avatars">
                    <div className="l-avatar a">A</div>
                    <div className="l-avatar b">B</div>
                    <div className="l-avatar c">C</div>
                  </div>
                </div>
                <div className="l-mini-body">
                  <div className="l-code-line"><span className="l-code-gutter">1</span><span className="l-code-src"><span className="c-kw">from</span> <span className="c-mod">fastapi</span> <span className="c-kw">import</span> APIRouter, Depends</span></div>
                  <div className="l-code-line"><span className="l-code-gutter">2</span><span className="l-code-src"><span className="c-kw">from</span> <span className="c-mod">..models.user</span> <span className="c-kw">import</span> User</span></div>
                  <div className="l-code-line"><span className="l-code-gutter">3</span><span className="l-code-src"><span className="c-kw">from</span> <span className="c-mod">..services.auth</span> <span className="c-kw">import</span> auth_service</span></div>
                  <div className="l-code-line"><span className="l-code-gutter">4</span><span className="l-code-src">{' '}</span></div>
                  <div className="l-code-line"><span className="l-code-gutter">5</span><span className="l-code-src"><span className="c-mod">router</span> = <span className="c-fn">APIRouter</span>(<span className="c-param">prefix</span>=<span className="c-str">&quot;/auth&quot;</span>)</span></div>
                  <div className="l-code-line" style={{ position: 'relative' }}>
                    <span className="l-code-gutter">6</span>
                    <span className="l-code-src"><span className="c-mod">@router.post</span>(<span className="c-str">&quot;/login&quot;</span>)</span>
                    <span className="l-cursor" style={{ left: 250, background: '#f85149' }} />
                    <span className="l-cursor-label" style={{ left: 250, top: 0, background: '#f85149' }}>alice</span>
                  </div>
                  <div className="l-code-line"><span className="l-code-gutter">7</span><span className="l-code-src"><span className="c-kw">async def</span> <span className="c-fn">login</span>(</span></div>
                  <div className="l-code-line"><span className="l-code-gutter">8</span><span className="l-code-src">    <span className="c-mod">credentials</span>: LoginSchema,</span></div>
                  <div className="l-code-line" style={{ position: 'relative', background: 'rgba(63,185,80,0.2)', margin: '0 -20px', padding: '0 20px' }}>
                    <span className="l-code-gutter">9</span>
                    <span className="l-code-src">    <span className="c-mod">session</span>: Session = <span className="c-kw">Depends</span>(get_session),</span>
                    <span className="l-cursor-label" style={{ right: 8, top: 0, background: '#3fb950' }}>bob</span>
                  </div>
                  <div className="l-code-line"><span className="l-code-gutter">10</span><span className="l-code-src">):</span></div>
                  <div className="l-code-line"><span className="l-code-gutter">11</span><span className="l-code-src">    <span className="c-kw">return await</span> auth_service.<span className="c-fn">login</span>(</span></div>
                  <div className="l-code-line"><span className="l-code-gutter">12</span><span className="l-code-src">        <span className="c-mod">credentials</span>,</span></div>
                  <div className="l-code-line" style={{ position: 'relative' }}>
                    <span className="l-code-gutter">13</span>
                    <span className="l-code-src">        <span className="c-mod">session</span></span>
                    <span className="l-cursor" style={{ left: 140, background: '#bc8cff' }} />
                    <span className="l-cursor-label" style={{ left: 140, top: 0, background: '#bc8cff' }}>charlie</span>
                  </div>
                  <div className="l-code-line"><span className="l-code-gutter">14</span><span className="l-code-src">    )</span></div>
                </div>
                <div className="l-mini-status">
                  <span className="live"><ThunderboltOutlined /> {t('landing.collab.liveSynced')}</span>
                  <span>Yjs v15.5.0 · WebSocket connected</span>
                </div>
              </div>
              <div className="l-chat-bubble">
                <div className="l-avatar b">B</div>
                <div>
                  <div className="who">bob <span className="when">{t('landing.collab.justNow')}</span></div>
                  <div className="msg">{t('landing.collab.chatMessage')}</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ===== DESKTOP SPOTLIGHT ===== */}
      <section className="l-section l-spotlight" id="desktop">
        <div className="l-container">
          <div className="l-spotlight-grid reverse">
            <div className="reveal reveal-d2" style={{ position: 'relative' }}>
              <div className="l-desktop-frame">
                <div className="l-desktop-titlebar">
                  <div className="l-editor-dots"><span /><span /><span /></div>
                  <div className="name">Perseus Desktop</div>
                  <div style={{ width: 48 }} />
                </div>
                <div className="l-desktop-body">
                  <div className="l-desktop-side">
                    <div className="rail-item active"><HomeOutlined /></div>
                    <div className="rail-item"><SearchOutlined /></div>
                    <div className="rail-item"><PullRequestOutlined /></div>
                    <div className="rail-item"><ExclamationCircleOutlined /></div>
                    <div style={{ flex: 1 }} />
                    <div className="rail-item"><MessageOutlined /></div>
                    <div className="rail-item"><SettingOutlined /></div>
                  </div>
                  <div className="l-desktop-main">
                    <div className="l-desktop-tabs">
                      <div className="l-desktop-tab active"><CodeOutlined /> app.py</div>
                      <div className="l-desktop-tab"><FileTextOutlined /> README.md</div>
                    </div>
                    <div className="l-desktop-editor">
                      <div className="c-comment"># Perseus Desktop</div>
                      <div style={{ color: 'var(--p-fg2)', marginBottom: 10 }}>Native desktop experience with offline support</div>
                      <div className="l-code-line"><span className="l-code-gutter">1</span><span className="l-code-src"><span className="c-kw">package</span> <span className="c-mod">main</span></span></div>
                      <div className="l-code-line"><span className="l-code-gutter">2</span><span className="l-code-src">{' '}</span></div>
                      <div className="l-code-line"><span className="l-code-gutter">3</span><span className="l-code-src"><span className="c-kw">import</span> <span className="c-str">&quot;github.com/wailsapp/wails/v2&quot;</span></span></div>
                      <div className="l-code-line"><span className="l-code-gutter">4</span><span className="l-code-src">{' '}</span></div>
                      <div className="l-code-line"><span className="l-code-gutter">5</span><span className="l-code-src"><span className="c-kw">func</span> <span className="c-fn">main</span>() {'{'}</span></div>
                      <div className="l-code-line"><span className="l-code-gutter">6</span><span className="l-code-src">    app := <span className="c-fn">NewApp</span>()</span></div>
                      <div className="l-code-line"><span className="l-code-gutter">7</span><span className="l-code-src">    wails.<span className="c-fn">Run</span>(app)</span></div>
                      <div className="l-code-line"><span className="l-code-gutter">8</span><span className="l-code-src">{'}'}</span></div>
                    </div>
                    <div className="l-desktop-term">
                      <div className="tabs"><span>Terminal</span><span>Problems</span><span>Output</span></div>
                      <div><span className="prompt">~/perseus $</span> git status</div>
                      <div style={{ color: 'var(--p-fg2)' }}>On branch main</div>
                      <div className="ok">nothing to commit, working tree clean</div>
                    </div>
                  </div>
                </div>
              </div>
              <div className="l-float-badge top-right" style={{ top: -18, left: -18, right: 'auto' }}>
                <DesktopOutlined style={{ color: 'var(--p-primary-light)' }} /> {t('landing.desktop.nativeBadge')}
              </div>
            </div>

            <div className="l-spotlight-text reveal">
              <span className="l-eyebrow">{t('landing.desktop.eyebrow')}</span>
              <h2>{t('landing.desktop.title')}</h2>
              <p>{t('landing.desktop.description')}</p>
              <div className="l-spotlight-list">
                {DESKTOP_ITEMS.map((item) => (
                  <div className="l-spotlight-item" key={item.key}>
                    <div className="l-spotlight-icon primary">{item.icon}</div>
                    <div>
                      <h4>{desktopTexts[item.key].title}</h4>
                      <p>{desktopTexts[item.key].desc}</p>
                    </div>
                  </div>
                ))}
              </div>
              <div className="l-platforms">
                <div className="l-platform"><DesktopOutlined /> {t('landing.desktop.platforms.windows')}</div>
                <div className="l-platform"><LaptopOutlined /> {t('landing.desktop.platforms.macos')}</div>
                <div className="l-platform"><HddOutlined /> {t('landing.desktop.platforms.linux')}</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ===== ARCHITECTURE ===== */}
      <section className="l-section l-section--alt" id="architecture">
        <div className="l-container">
          <div className="l-section-head reveal">
            <span className="l-eyebrow">{t('landing.architecture.eyebrow')}</span>
            <h2>{t('landing.architecture.title')}</h2>
            <p>{t('landing.architecture.subtitle')}</p>
          </div>
          <div className="l-arch-grid">
            <div className="l-arch-diagram reveal">
              <div className="diagram-title">{t('landing.architecture.diagramTitle')}</div>
              <div className="l-arch-clients">
                <div className="l-arch-node">
                  <DesktopOutlined className="ico" style={{ color: 'var(--p-primary-light)' }} />
                  <div className="name">{t('landing.architecture.webApp')}</div>
                </div>
                <div className="l-arch-node">
                  <LaptopOutlined className="ico" style={{ color: 'var(--p-accent)' }} />
                  <div className="name">{t('landing.architecture.desktop')}</div>
                </div>
                <div className="l-arch-node">
                  <CodeOutlined className="ico" style={{ color: 'var(--p-success)' }} />
                  <div className="name">{t('landing.architecture.gitCli')}</div>
                </div>
              </div>
              <div className="l-arch-arrow">
                <DownOutlined />
                <span className="proto">{t('landing.architecture.transport')}</span>
              </div>
              <div className="l-arch-gateway">
                <div className="title"><GatewayOutlined style={{ color: 'var(--p-primary-light)' }} /> {t('landing.architecture.gateway')}</div>
                <div className="sub">{t('landing.architecture.gatewaySub')}</div>
              </div>
              <div className="l-arch-services">
                <div className="l-arch-service">
                  <CloudServerOutlined className="ico" style={{ color: '#009688' }} />
                  <div className="name">{t('landing.architecture.fastapi')}</div>
                  <div className="sub">{t('landing.architecture.fastapiSub')}</div>
                </div>
                <div className="l-arch-service">
                  <ThunderboltOutlined className="ico" style={{ color: 'var(--p-accent)' }} />
                  <div className="name">{t('landing.architecture.collab')}</div>
                  <div className="sub">{t('landing.architecture.collabSub')}</div>
                </div>
                <div className="l-arch-service">
                  <BranchesOutlined className="ico" style={{ color: '#f05032' }} />
                  <div className="name">{t('landing.architecture.gitCgi')}</div>
                  <div className="sub">{t('landing.architecture.gitCgiSub')}</div>
                </div>
              </div>
              <div className="l-arch-data">
                <div className="l-arch-service">
                  <div className="mark pg">PG</div>
                  <div className="name">{t('landing.architecture.postgres')}</div>
                  <div className="sub">{t('landing.architecture.postgresSub')}</div>
                </div>
                <div className="l-arch-service">
                  <div className="mark redis">R</div>
                  <div className="name">{t('landing.architecture.redis')}</div>
                  <div className="sub">{t('landing.architecture.redisSub')}</div>
                </div>
              </div>
              <div className="l-arch-note">
                <DatabaseOutlined /> {t('landing.architecture.dockerNote')}
              </div>
            </div>

            <div>
              <div className="l-spotlight-list">
                {ARCH_BENEFITS.map((b, i) => (
                  <div className={`l-benefit reveal reveal-d${i + 1}`} key={b.key}>
                    <div className="l-benefit-icon">{b.icon}</div>
                    <div>
                      <h4>{archTexts[b.key].title}</h4>
                      <p>{archTexts[b.key].desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ===== ADMIN ===== */}
      <section className="l-section" id="admin">
        <div className="l-container">
          <div className="l-section-head reveal">
            <span className="l-eyebrow l-eyebrow--accent">{t('landing.admin.eyebrow')}</span>
            <h2>{t('landing.admin.title')}</h2>
            <p>{t('landing.admin.subtitle')}</p>
          </div>

          <div className="l-admin-frame reveal">
            <div className="l-admin-top">
              <div className="left">
                <div className="badge-icon"><SettingOutlined /></div>
                <span className="title">{t('landing.admin.consoleTitle')}</span>
                <span className="l-pill-success">{t('landing.admin.status')}</span>
              </div>
              <div className="updated"><DashboardOutlined /> {t('landing.admin.updated')}</div>
            </div>
            <div className="l-admin-body">
              <div className="l-admin-side">
                <div className="group-label">{t('landing.admin.system')}</div>
                <div className="l-admin-nav active"><DashboardOutlined /> {t('landing.admin.overview')}</div>
                <div className="l-admin-nav"><DatabaseOutlined /> {t('landing.admin.components')}</div>
                <div className="l-admin-nav"><FileTextOutlined /> {t('landing.admin.logs')}</div>
                <div className="l-admin-nav"><SlidersOutlined /> {t('landing.admin.configuration')}</div>
                <div className="group-label">{t('landing.admin.data')}</div>
                <div className="l-admin-nav"><ThunderboltOutlined /> {t('landing.admin.redis')}</div>
                <div className="l-admin-nav"><TeamOutlined /> {t('landing.admin.users')}</div>
                <div className="l-admin-nav"><ApiOutlined /> {t('landing.admin.webhooks')}</div>
              </div>
              <div className="l-admin-main">
                <div className="l-admin-stats">
                  <div className="l-admin-stat">
                    <div className="k">{t('landing.admin.activeUsers')}</div>
                    <div className="v">1,247</div>
                    <div className="d up"><RiseOutlined /> {t('landing.admin.thisWeek', { value: '12.5%' })}</div>
                  </div>
                  <div className="l-admin-stat">
                    <div className="k">{t('landing.admin.repositories')}</div>
                    <div className="v">3,892</div>
                    <div className="d up"><RiseOutlined /> {t('landing.admin.thisWeek', { value: '4.2%' })}</div>
                  </div>
                  <div className="l-admin-stat">
                    <div className="k">{t('landing.admin.collabSessions')}</div>
                    <div className="v">38</div>
                    <div className="d accent"><span className="dot" style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--p-accent)' }} /> {t('landing.admin.liveNow')}</div>
                  </div>
                  <div className="l-admin-stat">
                    <div className="k">{t('landing.admin.apiRequests')}</div>
                    <div className="v">2,847</div>
                    <div className="d muted">{t('landing.admin.avgLatency')}</div>
                  </div>
                </div>

                <div className="l-admin-panels">
                  <div className="l-admin-panel">
                    <div className="panel-head">
                      <span>{t('landing.admin.requestVolume')}</span>
                      <span className="hint">{t('landing.admin.last24h')}</span>
                    </div>
                    <div className="l-chart">
                      {ADMIN_CHART.map((h, i) => (
                        <div
                          key={i}
                          className={`bar${i === ADMIN_CHART.length - 1 ? ' accent' : ''}`}
                          style={{ height: `${h}%`, animationDelay: `${i * 40}ms` }}
                        />
                      ))}
                    </div>
                    <div className="l-chart-axis">
                      <span>00:00</span><span>06:00</span><span>12:00</span><span>18:00</span><span>Now</span>
                    </div>
                  </div>
                  <div className="l-admin-panel">
                    <div className="panel-head"><span>{t('landing.admin.componentHealth')}</span></div>
                    <div className="l-health-row">
                      <span className="name"><span className="status-dot" /> FastAPI Backend</span>
                      <span className="meta">23ms avg</span>
                    </div>
                    <div className="l-health-row">
                      <span className="name"><span className="status-dot" /> PostgreSQL</span>
                      <span className="meta">12 active conns</span>
                    </div>
                    <div className="l-health-row">
                      <span className="name"><span className="status-dot" /> Redis</span>
                      <span className="meta">0.8ms avg</span>
                    </div>
                    <div className="l-health-row">
                      <span className="name"><span className="status-dot" /> Collab Gateway</span>
                      <span className="meta">38 sessions</span>
                    </div>
                    <div className="l-health-row">
                      <span className="name"><span className="status-dot" /> Git CGI</span>
                      <span className="meta">147 ops/min</span>
                    </div>
                  </div>
                </div>

                <div className="l-admin-logs">
                  <div className="logs-head">
                    <span className="left"><CodeOutlined /> {t('landing.admin.realtimeLogs')}</span>
                    <span className="stream"><span className="dot" /> {t('landing.admin.streaming')}</span>
                  </div>
                  {ADMIN_LOGS.map((line, i) => (
                    <div className="l-log-line" key={i}>
                      <span className={line.tagCls}>{line.tag}</span> {line.text}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ===== CTA ===== */}
      <section className="l-cta" id="cta">
        <div className="l-cta-grid" />
        <div className="l-cta-glow" />
        <div className="l-container">
          <h2 className="reveal">{t('landing.cta.title')}</h2>
          <p className="reveal reveal-d1">{t('landing.cta.description')}</p>

          <div className="l-terminal reveal reveal-d2">
            <div className="l-terminal-head">
              <div className="left"><CodeOutlined /> {t('landing.cta.terminal')}</div>
              <button className="l-terminal-copy" onClick={copyCommand}>
                <CopyOutlined /> {t('landing.cta.copy')}
              </button>
            </div>
            <div className="l-terminal-body">
              <div><span className="cmd">git</span> clone https://github.com/perseus/perseus.git</div>
              <div><span className="cmd">cd</span> perseus</div>
              <div><span className="cmd-blue">docker</span> compose up -d</div>
            </div>
          </div>

          <div className="l-cta-actions reveal reveal-d3">
            <button className="l-btn l-btn--primary" onClick={() => openAuth('register')}>
              <RocketOutlined /> {t('landing.cta.getStarted')}
            </button>
            <a className="l-btn l-btn--ghost" href="#features">
              <BookOutlined /> {t('landing.cta.readDocs')}
            </a>
          </div>

          <div className="l-cta-checks reveal reveal-d4">
            <span className="check"><CheckCircleOutlined className="ico" /> {t('landing.cta.openSource')}</span>
            <span className="check"><CheckCircleOutlined className="ico" /> {t('landing.cta.selfHosted')}</span>
            <span className="check"><CheckCircleOutlined className="ico" /> {t('landing.cta.mit')}</span>
          </div>
        </div>
      </section>

      {/* ===== FOOTER ===== */}
      <footer className="l-footer">
        <div className="l-footer-inner">
          <div className="l-footer-grid">
            <div className="l-footer-brand-col">
              <div className="l-footer-brand">
                <Logo size={30} />
                Perseus
              </div>
              <p className="l-footer-tagline">{t('landing.footer.tagline')}</p>
              <div className="l-footer-social">
                <a href="https://github.com/perseus/perseus" target="_blank" rel="noreferrer" aria-label="GitHub"><GithubOutlined /></a>
                <a href="#footer" aria-label="Community"><MessageOutlined /></a>
                <a href="mailto:hello@perseus.dev" aria-label="Email"><MailOutlined /></a>
              </div>
            </div>
            <div className="l-footer-col">
              <h4>{t('landing.footer.product')}</h4>
              <ul>
                <li><a href="#features">{t('landing.footer.features')}</a></li>
                <li><a href="#collab">{t('landing.footer.collaboration')}</a></li>
                <li><a href="#desktop">{t('landing.footer.desktop')}</a></li>
                <li><a href="#architecture">{t('landing.footer.selfHosting')}</a></li>
                <li><a>{t('landing.footer.pricing')}</a></li>
              </ul>
            </div>
            <div className="l-footer-col">
              <h4>{t('landing.footer.resources')}</h4>
              <ul>
                <li><a>{t('landing.footer.docs')}</a></li>
                <li><a>{t('landing.footer.api')}</a></li>
                <li><a>{t('landing.footer.deployment')}</a></li>
                <li><a>{t('landing.footer.changelog')}</a></li>
                <li><a>{t('landing.footer.roadmap')}</a></li>
              </ul>
            </div>
            <div className="l-footer-col">
              <h4>{t('landing.footer.company')}</h4>
              <ul>
                <li><a>{t('landing.footer.about')}</a></li>
                <li><a>{t('landing.footer.blog')}</a></li>
                <li><a>{t('landing.footer.careers')}</a></li>
                <li><a>{t('landing.footer.privacy')}</a></li>
                <li><a>{t('landing.footer.terms')}</a></li>
              </ul>
            </div>
          </div>
          <div className="l-footer-bottom">
            <span>{t('landing.footer.copyright')}</span>
            <span className="made">
              {t('landing.footer.madeWith')} <HeartOutlined className="heart" /> {t('landing.footer.madeWithTail')}
            </span>
          </div>
        </div>
      </footer>

      <AuthModal
        open={authOpen}
        defaultTab={authTab}
        onClose={() => setAuthOpen(false)}
      />
    </div>
  );
}
