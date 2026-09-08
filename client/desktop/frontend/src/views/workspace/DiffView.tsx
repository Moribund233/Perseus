import { useEffect, useState } from 'react';
import { DiffEditor } from '@monaco-editor/react';
import { useTranslation } from 'react-i18next';
import { readFile, gitShow } from '../../api/workspaces';

interface Props {
  workspaceId: string;
  workspacePath: string;
  path: string;
  onClose: () => void;
}

// DiffView：Monaco DiffEditor，original = git show HEAD:<path>（新文件为空），modified = 工作区当前内容。
export default function DiffView({ workspaceId, workspacePath, path, onClose }: Props) {
  const { t } = useTranslation();
  const [original, setOriginal] = useState('');
  const [modified, setModified] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    setError(null);
    Promise.all([
      gitShow(workspaceId, path)
        .then((r) => r.content)
        .catch(() => ''),
      readFile(workspaceId, path)
        .then((fc) => (fc.binary ? `(binary) ${fc.size} bytes` : fc.content))
        .catch((e) => {
          setError(String(e));
          return '';
        }),
    ])
      .then(([o, m]) => {
        setOriginal(o);
        setModified(m);
        setLoading(false);
      })
      .catch((e) => {
        setError(String(e));
        setLoading(false);
      });
  }, [workspaceId, path]);

  if (error) {
    return (
      <div className="empty-editor">
        {error}
        <div style={{ marginTop: 12 }}>
          <button className="btn sm" onClick={onClose}>
            {t('desktop.diff.back', { defaultValue: '返回' })}
          </button>
        </div>
      </div>
    );
  }

  if (loading) return <div className="empty-editor">{t('desktop.git.loading')}</div>;

  return (
    <div className="editor-tab">
      <div className="crumbs">
        <span className="crumb-path">
          <span className="cru diff">diff</span>
          <span className="cru">/</span>
          <span className="cru-leaf">{path}</span>
        </span>
        <span className="right">
          <span className="cursor-info">{t('desktop.diff.headNote', { defaultValue: 'HEAD → 工作区' })}</span>
          <button className="btn sm" style={{ marginLeft: 10 }} onClick={onClose}>
            {t('desktop.diff.back', { defaultValue: '返回编辑器' })}
          </button>
        </span>
      </div>
      <DiffEditor
        theme="vs-dark"
        language={guessLang(path)}
        original={original}
        modified={modified}
        options={{
          readOnly: true,
          automaticLayout: true,
          fontFamily: "'JetBrains Mono', 'Fira Code', 'Consolas', monospace",
          fontSize: 12.5,
          minimap: { enabled: false },
          renderSideBySide: true,
          scrollBeyondLastLine: false,
          renderLineHighlight: 'none',
        }}
      />
    </div>
  );
}

function guessLang(path: string): string {
  const ext = path.split('.').pop()?.toLowerCase() ?? '';
  const map: Record<string, string> = {
    ts: 'typescript', tsx: 'typescript', js: 'javascript', jsx: 'javascript',
    py: 'python', json: 'json', md: 'markdown', css: 'css', html: 'html', go: 'go',
  };
  return map[ext] ?? 'plaintext';
}