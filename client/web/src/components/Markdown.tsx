import { memo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const markdownColors = {
  text: '#e6edf3',
  textSecondary: '#8b949e',
  border: '#21262d',
  bgCode: '#1c2128',
  bgBlockquote: '#161b22',
  link: '#58a6ff',
};

const codeFont = "'JetBrains Mono', 'Fira Code', 'Consolas', monospace";

/**
 * 共享 Markdown 渲染组件

 * - react-markdown 默认不渲染原始 HTML, 天然防 XSS（聊天消息/README/预览共用）
 * - remark-gfm 支持表格、删除线、任务列表、自动链接
 */
function MarkdownInner({ children }: { children: string }) {
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
      `}</style>
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{children}</ReactMarkdown>
    </div>
  );
}

export const Markdown = memo(MarkdownInner);
export default Markdown;
