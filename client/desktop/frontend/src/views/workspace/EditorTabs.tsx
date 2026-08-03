import { useEffect, useMemo, useState } from 'react';
import Editor from '@monaco-editor/react';
import { readFile, writeFile, FileContent } from '../../api/workspaces';

export default function EditorTabs({ workspaceId, openPath }: { workspaceId: string; openPath: string | null }) {
  const [current, setCurrent] = useState<string | null>(null);
  const [content, setContent] = useState<FileContent | null>(null);
  const [dirty, setDirty] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!openPath) return;
    setCurrent(openPath);
    readFile(workspaceId, openPath)
      .then((fc) => {
        setContent(fc);
        setDirty(false);
      })
      .catch((e) => setError(String(e)));
  }, [workspaceId, openPath]);

  const language = useMemo(() => guessLang(current ?? ''), [current]);

  const save = async () => {
    if (!current || !content || content.binary) return;
    try {
      await writeFile(workspaceId, current, content.content);
      setDirty(false);
    } catch (e) {
      setError(String(e));
    }
  };

  if (error) return <div className="error-text">{error}</div>;
  if (!current || !content) return <div className="empty-editor">选择左侧文件开始编辑</div>;

  if (content.binary) {
    return <div className="empty-editor">二进制文件（{content.size} bytes）不可编辑</div>;
  }

  return (
    <div className="editor-tab">
      <div className="tab-bar">
        <span className="tab-title">{current}{dirty ? ' ●' : ''}</span>
        <span className="tab-actions">
          {content.truncated && <span className="warn">文件过大，仅读入前 2MB</span>}
          <button disabled={!dirty} onClick={save}>保存</button>
        </span>
      </div>
      <Editor
        height="100%"
        language={language}
        value={content.content}
        onChange={(v) => {
          setContent((c) => (c ? { ...c, content: v ?? '' } : c));
          setDirty(true);
        }}
        options={{ readOnly: content.truncated, automaticLayout: true }}
      />
    </div>
  );
}

function guessLang(path: string): string {
  const ext = path.split('.').pop()?.toLowerCase() ?? '';
  const map: Record<string, string> = {
    ts: 'typescript', tsx: 'typescript', js: 'javascript', jsx: 'javascript',
    py: 'python', json: 'json', md: 'markdown', css: 'css', html: 'html',
  };
  return map[ext] ?? 'plaintext';
}
