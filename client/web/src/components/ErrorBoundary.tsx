import { Component, useState, type ErrorInfo, type ReactNode } from 'react';
import { useTranslation } from 'react-i18next';

export interface ErrorFallbackArgs {
  error: Error | null;
  info: ErrorInfo | null;
  reset: () => void;
}

interface Props {
  children: ReactNode;
  /** 自定义回退 UI；未提供时使用内置的详细错误页 */
  fallback?: (args: ErrorFallbackArgs) => ReactNode;
  /** 错误上报钩子（如接入 Sentry） */
  onError?: (error: Error, info: ErrorInfo) => void;
  /** 任一 key 变化时自动重置（用于路由切换后自动恢复） */
  resetKeys?: readonly unknown[];
}

interface State {
  hasError: boolean;
  error: Error | null;
  info: ErrorInfo | null;
}

/** 汇总可复制的诊断信息（错误、组件栈、环境） */
function formatErrorDetails(error: Error | null, info: ErrorInfo | null): string {
  const parts: string[] = [];
  if (error) {
    parts.push(`[${error.name}] ${error.message}`);
    if (error.stack) parts.push(error.stack);
  }
  if (info?.componentStack) parts.push(`Component stack:${info.componentStack}`);
  if (typeof window !== 'undefined') parts.push(`URL: ${window.location.href}`);
  if (typeof navigator !== 'undefined') parts.push(`UA: ${navigator.userAgent}`);
  parts.push(`Time: ${new Date().toISOString()}`);
  return parts.join('\n\n');
}

/** 内置回退：概要 + 可展开/复制的堆栈 + 重试/刷新 */
function DefaultErrorFallback({ error, info, reset }: ErrorFallbackArgs) {
  const { t } = useTranslation();
  const [copied, setCopied] = useState(false);
  const details = formatErrorDetails(error, info);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(details);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      /* 剪贴板不可用时忽略 */
    }
  };

  const btn = (primary?: boolean): React.CSSProperties => ({
    padding: '7px 16px',
    borderRadius: 6,
    border: `1px solid ${primary ? '#1f6feb' : '#30363d'}`,
    background: primary ? '#1f6feb' : '#21262d',
    color: primary ? '#fff' : '#e6edf3',
    cursor: 'pointer',
    fontSize: 13,
    fontWeight: 500,
  });

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '60vh',
        padding: 32,
        color: '#e6edf3',
      }}
    >
      <div
        style={{
          width: 56,
          height: 56,
          borderRadius: '50%',
          background: 'rgba(248,81,73,0.12)',
          color: '#f85149',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: 28,
          fontWeight: 700,
          marginBottom: 16,
        }}
      >
        !
      </div>
      <h2 style={{ fontSize: 20, fontWeight: 700, margin: '0 0 8px', color: '#e6edf3' }}>
        {t('app.errorBoundary.title')}
      </h2>
      <p style={{ color: '#8b949e', textAlign: 'center', maxWidth: 560, margin: '0 0 20px', lineHeight: 1.6 }}>
        {error?.message || t('app.errorBoundary.unknown')}
      </p>

      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', justifyContent: 'center' }}>
        <button style={btn(true)} onClick={reset}>{t('app.errorBoundary.retry')}</button>
        <button style={btn()} onClick={() => window.location.reload()}>{t('app.errorBoundary.reload')}</button>
        <button style={btn()} onClick={copy}>{copied ? t('app.errorBoundary.copied') : t('app.errorBoundary.copy')}</button>
      </div>

      <details style={{ marginTop: 24, width: '100%', maxWidth: 720 }}>
        <summary style={{ cursor: 'pointer', color: '#8b949e', fontSize: 13, textAlign: 'center' }}>
          {t('app.errorBoundary.details')}
        </summary>
        <pre
          style={{
            marginTop: 12,
            padding: 14,
            borderRadius: 8,
            border: '1px solid #21262d',
            background: '#0d1117',
            color: '#8b949e',
            fontSize: 12,
            lineHeight: 1.5,
            maxHeight: 280,
            overflow: 'auto',
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-all',
            fontFamily: "'JetBrains Mono', 'Fira Code', 'Consolas', monospace",
          }}
        >
          {details}
        </pre>
      </details>
    </div>
  );
}

/**
 * 错误边界：捕获子树渲染/生命周期错误，展示可诊断的回退页。
 *
 * - `resetKeys`：键变化时自动重置（路由级边界传入 pathname，切页即恢复）。
 * - `onError`：错误上报钩子。
 * - `fallback`：自定义回退 UI。
 */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null, info: null };

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('[ErrorBoundary]', error, info.componentStack);
    this.setState({ info });
    this.props.onError?.(error, info);
  }

  componentDidUpdate(prevProps: Props) {
    if (!this.state.hasError) return;
    const { resetKeys } = this.props;
    const prevKeys = prevProps.resetKeys;
    if (!resetKeys || !prevKeys) return;
    if (resetKeys.length !== prevKeys.length || resetKeys.some((key, i) => !Object.is(key, prevKeys[i]))) {
      this.reset();
    }
  }

  reset = () => {
    this.setState({ hasError: false, error: null, info: null });
  };

  render() {
    if (this.state.hasError) {
      const args: ErrorFallbackArgs = { error: this.state.error, info: this.state.info, reset: this.reset };
      if (this.props.fallback) return this.props.fallback(args);
      return <DefaultErrorFallback {...args} />;
    }
    return this.props.children;
  }
}
