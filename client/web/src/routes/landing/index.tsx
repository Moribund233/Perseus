import { useState } from 'react';
import {
  FolderOutlined,
  MessageOutlined,
  CodeOutlined,
  ClockCircleOutlined,
  QuestionCircleOutlined,
  ArrowDownOutlined,
  CheckOutlined,
  TranslationOutlined,
} from '@ant-design/icons';
import { useTranslation, Trans } from 'react-i18next';
import { useAuthStore } from '../../stores/auth';
import AuthModal from './AuthModal';
import './landing.css';

const featureBase = [
  {
    key: 'codeHosting',
    icon: <FolderOutlined style={{ fontSize: 22 }} />,
    bg: 'rgba(31,111,235,0.12)',
    color: '#58a6ff',
  },
  {
    key: 'teamChat',
    icon: <MessageOutlined style={{ fontSize: 22 }} />,
    bg: 'rgba(63,185,80,0.12)',
    color: '#3fb950',
  },
  {
    key: 'codeReview',
    icon: <CodeOutlined style={{ fontSize: 22 }} />,
    bg: 'rgba(188,140,255,0.12)',
    color: '#bc8cff',
  },
  {
    key: 'realtimeEditing',
    icon: <ClockCircleOutlined style={{ fontSize: 22 }} />,
    bg: 'rgba(210,153,34,0.12)',
    color: '#d29922',
  },
  {
    key: 'issueTracking',
    icon: <QuestionCircleOutlined style={{ fontSize: 22 }} />,
    bg: 'rgba(248,81,73,0.12)',
    color: '#f85149',
  },
  {
    key: 'releaseManagement',
    icon: <ArrowDownOutlined style={{ fontSize: 22 }} />,
    bg: 'rgba(31,111,235,0.12)',
    color: '#58a6ff',
  },
];

export default function LandingPage() {
  const [authOpen, setAuthOpen] = useState(false);
  const [authTab, setAuthTab] = useState<'login' | 'register'>('login');
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const { t, i18n } = useTranslation();

  const openAuth = (tab: 'login' | 'register') => {
    setAuthTab(tab);
    setAuthOpen(true);
  };

  const toggleLanguage = () => {
    const next = i18n.language.startsWith('zh') ? 'en' : 'zh';
    i18n.changeLanguage(next);
  };

  const featureTexts = t('landing.features', { returnObjects: true }) as Record<
    string,
    { title: string; desc: string }
  >;
  const features = featureBase.map((f) => ({
    ...f,
    title: featureTexts[f.key].title,
    desc: featureTexts[f.key].desc,
  }));

  const collabItems = t('landing.collab.items', { returnObjects: true }) as string[];

  return (
    <div className="landing">
      <nav className="l-nav">
        <a className="l-nav-logo" href="/">
          <img src="/logo-orbit-compact.svg" width={28} height={28} alt="Perseus" />
          Perseus
        </a>
        <div className="l-nav-links">
          <a href="#features">{t('landing.nav.features')}</a>
          <a href="#collab">{t('landing.nav.collaboration')}</a>
          <a>{t('landing.nav.docs')}</a>
        </div>
        <div className="l-nav-actions">
          <button className="l-nav-btn" onClick={toggleLanguage}>
            <TranslationOutlined style={{ marginRight: 6 }} />
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
      </nav>

      <section className="l-hero">
        <div className="l-hero-bg">
          <div className="l-hero-g1" />
          <div className="l-hero-g2" />
          <div className="l-hero-grid" />
        </div>
        <div className="l-hero-content">
          <div className="l-hero-badge">
            <ClockCircleOutlined style={{ fontSize: 14 }} />
            {t('landing.hero.badge')}
          </div>
          <h1>
            <Trans i18nKey="landing.hero.title" components={{ 1: <span className="hl" /> }}>
              Code. <span className="hl">Collaborate.</span> Ship.
            </Trans>
          </h1>
          <p>{t('landing.hero.description')}</p>
          <div className="l-hero-actions">
            <button className="l-btn-hero-primary" onClick={() => openAuth('register')}>{t('landing.hero.getStartedFree')}</button>
            <button className="l-btn-hero-secondary" onClick={() => document.getElementById('features')?.scrollIntoView({ behavior: 'smooth' })}>{t('landing.hero.learnMore')}</button>
          </div>
          <div className="l-hero-stats">
            <div className="l-hero-stat"><div className="num">24</div><div className="label">{t('landing.hero.stats.repositories')}</div></div>
            <div className="l-hero-stat"><div className="num">1.8K</div><div className="label">{t('landing.hero.stats.commits')}</div></div>
            <div className="l-hero-stat"><div className="num">8</div><div className="label">{t('landing.hero.stats.teamMembers')}</div></div>
            <div className="l-hero-stat"><div className="num">99.9%</div><div className="label">{t('landing.hero.stats.uptime')}</div></div>
          </div>
        </div>
      </section>

      <section className="l-features" id="features">
        <div className="l-features-header">
          <h2>{t('landing.features.title')}</h2>
          <p>{t('landing.features.subtitle')}</p>
        </div>
        <div className="l-features-grid">
          {features.map((f, i) => (
            <div className="l-feature-card" key={i}>
              <div className="l-feature-icon" style={{ background: f.bg, color: f.color }}>{f.icon}</div>
              <h3>{f.title}</h3>
              <p>{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="l-collab" id="collab">
        <div className="l-collab-inner">
          <div className="l-collab-text">
            <h2>{t('landing.collab.title')}</h2>
            <p>{t('landing.collab.description')}</p>
            <ul>
              {collabItems.map((item, i) => (
                <li key={i}><CheckOutlined /> {item}</li>
              ))}
            </ul>
          </div>
          <div className="l-collab-visual">
            <div className="mh">
              <div className="mh-dot" style={{ background: '#ff5f56' }} />
              <div className="mh-dot" style={{ background: '#ffbd2e' }} />
              <div className="mh-dot" style={{ background: '#27c93f' }} />
              <span style={{ fontSize: 12, color: '#6e7681', marginLeft: 8 }}>websocket-client.ts — Perseus</span>
            </div>
            <div className="ml" style={{ width: '60%' }} />
            <div className="ml" style={{ width: '45%' }} />
            <div className="ml" style={{ width: '75%' }} />
            <div className="ml" style={{ width: '30%' }} />
            <div className="ml" style={{ background: '#1f6feb', width: '55%' }} />
            <div className="ml" style={{ width: '65%' }} />
            <div className="ml" style={{ width: '40%' }} />
            <div className="ml" style={{ background: 'rgba(63,185,80,0.3)', width: '50%' }} />
            <div className="ml" style={{ width: '70%' }} />
            <div className="ml" style={{ width: '35%' }} />
            <div className="l-collab-avatar" style={{ right: 24, border: '2px solid #3fb950', background: 'linear-gradient(135deg, #3fb950, #238636)' }}>LW</div>
            <div className="l-collab-avatar" style={{ right: 64, border: '2px solid #58a6ff', background: 'linear-gradient(135deg, #58a6ff, #1f6feb)' }}>CM</div>
            <div className="l-collab-cursor" style={{ left: '45%', top: '108px' }} />
            <div className="l-collab-label" style={{ left: '45%', top: '90px', background: '#58a6ff' }}>CM</div>
            <div className="l-collab-cursor" style={{ left: '55%', top: '170px', background: '#3fb950' }} />
            <div className="l-collab-label" style={{ left: '55%', top: '152px', background: '#3fb950' }}>LW</div>
          </div>
        </div>
      </section>

      <footer className="l-footer">
        <div className="l-footer-inner">
          <div className="l-footer-copy">{t('landing.footer.copyright')}</div>
          <div className="l-footer-links">
            <a>{t('landing.footer.about')}</a>
            <a>{t('landing.footer.privacy')}</a>
            <a>{t('landing.footer.terms')}</a>
            <a>{t('landing.footer.github')}</a>
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
