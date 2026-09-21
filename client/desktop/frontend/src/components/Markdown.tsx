import { memo, useEffect, useRef, useState, type ComponentPropsWithoutRef } from 'react';
import ReactMarkdown, { type Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useTranslation } from 'react-i18next';

const markdownColors = {
  text: '#e6edf3',
  textSecondary: '#8b949e',
  border: '#21262d',
  bgCode: '#1c2128',
  bgBlockquote: '#161b22',
  link: '#58a6ff',
};

const codeFont = "'JetBrains Mono', 'Fira Code', 'Consolas', monospace";
const CODE_MAX_HEIGHT = 300;

type PreProps = ComponentPropsWithoutRef<'pre'> & { node?: unknown };

/** 代码块：超过上限高度时折叠，内部独立滚动，并可展开/收起 */
function CollapsiblePre({ node, children, ...props }: PreProps) {
  const { t } = useTranslation();
  void node; // react-markdown 注入, 不透传到 DOM
  const ref = useRef<HTMLPreElement>(null);
  const [overflows, setOverflows] = useState(false);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const measure = () => setOverflows(el.scrollHeight > el.clientHeight + 4);
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  return (
    <div className="md-pre-wrap">
      <pre
        ref={ref}
        {...props}
        style={{ ...(props.style ?? {}), maxHeight: expanded ? undefined : CODE_MAX_HEIGHT, overflowY: 'auto' }}
      >
        {children}
      </pre>
      {(overflows || expanded) && (
        <button type="button" className="md-pre-toggle" onClick={() => setExpanded((v) => !v)}>
          {expanded
            ? t('common.collapse', { defaultValue: '收起' })
            : t('common.expand', { defaultValue: '展开' })}
        </button>
      )}
    </div>
  );
}

const collapsibleComponents: Components = { pre: CollapsiblePre };

/**
 * 共享 Markdown 渲染组件（拷贝移植自 web 端 components/Markdown.tsx）

 * - react-markdown 默认不渲染原始 HTML, 天然防 XSS（聊天消息共用）
 * - remark-gfm 支持表格、删除线、任务列表、自动链接
 * - collapsibleCode: 代码块超高折叠 + 独立滚动（聊天消息片段预览用）
 */
function MarkdownInner({ children, collapsibleCode = false }: { children: string; collapsibleCode?: boolean }) {
  return (
    <div className="md-body">
      <style>{`
        .md-body { color: ${markdownColors.text}; font-size: 14px; line-height: 1.6; word-break: break-word; }
        .md-body > :first-child { margin-top: 0; }
        .md-body > :last-child { margin-bottom: 0; }
        .md-body p { margin: 0 0 8px; }
        .md-body h1, .md-body h2, .md-body h3, .md-body h4, .md-body h5, .md-body h6 {
          color: ${markdownColors.text};
          margin: 16px 0 8px;
          line-height: 1.3;
          font-weight: 600;
        }
        .md-body h1 { font-size: 1.5em; padding-bottom: 6px; border-bottom: 1px solid ${markdownColors.border}; }
        .md-body h2 { font-size: 1.3em; padding-bottom: 5px; border-bottom: 1px solid ${markdownColors.border}; }
        .md-body h3 { font-size: 1.15em; }
        .md-body h4 { font-size: 1em; }
        .md-body a { color: ${markdownColors.link}; text-decoration: none; }
        .md-body a:hover { text-decoration: underline; }
        .md-body ul, .md-body ol { margin: 0 0 8px; padding-left: 22px; }
        .md-body li { margin: 2px 0; }
        .md-body li > input[type="checkbox"] { margin-right: 6px; accent-color: #1f6feb; }
        .md-body code {
          background: ${markdownColors.bgCode};
          padding: 1px 5px;
          border-radius: 4px;
          font-family: ${codeFont};
          font-size: 85%;
          color: #79c0ff;
        }
        .md-body pre {
          background: ${markdownColors.bgCode};
          border: 1px solid ${markdownColors.border};
          border-radius: 6px;
          padding: 10px 12px;
          overflow-x: auto;
          margin: 0 0 8px;
        }
        .md-body pre code { background: transparent; padding: 0; color: ${markdownColors.text}; font-size: 12.5px; }
        .md-body blockquote {
          margin: 0 0 8px;
          padding: 2px 12px;
          border-left: 3px solid ${markdownColors.border};
          background: ${markdownColors.bgBlockquote};
          color: ${markdownColors.textSecondary};
        }
        .md-body table { border-collapse: collapse; margin: 0 0 8px; display: block; overflow-x: auto; }
        .md-body th, .md-body td { border: 1px solid ${markdownColors.border}; padding: 5px 10px; font-size: 13px; }
        .md-body th { background: ${markdownColors.bgBlockquote}; font-weight: 600; }
        .md-body img { max-width: min(360px, 100%); max-height: 280px; border-radius: 6px; display: block; margin: 4px 0; }
        .md-body hr { border: none; border-top: 1px solid ${markdownColors.border}; margin: 12px 0; }
        .md-body del { color: ${markdownColors.textSecondary}; }
        .md-pre-wrap { position: relative; }
        .md-pre-toggle {
          position: absolute;
          top: 6px;
          right: 8px;
          background: rgba(13,17,23,0.85);
          border: 1px solid ${markdownColors.border};
          border-radius: 5px;
          color: ${markdownColors.textSecondary};
          font-size: 11px;
          line-height: 1;
          padding: 4px 8px;
          cursor: pointer;
        }
        .md-pre-toggle:hover { color: ${markdownColors.text}; border-color: #30363d; }
      `}</style>
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={collapsibleCode ? collapsibleComponents : undefined}>
        {children}
      </ReactMarkdown>
    </div>
  );
}

export const Markdown = memo(MarkdownInner);
export default Markdown;
