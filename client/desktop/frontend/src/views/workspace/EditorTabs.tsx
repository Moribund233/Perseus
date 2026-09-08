import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import Editor from '@monaco-editor/react';
import { Modal } from 'antd';
import { useTranslation } from 'react-i18next';
import { readFile, writeFile, FileContent } from '../../api/workspaces';

interface Tab {
  path: string;
  content: FileContent;
  savedContent: string;
}

/**
 * 多标签编辑器
 *
 * - tabs 状态自包含: 文件树 onOpen 经 openPath prop 触发打开/激活, 重复打开不重复加载
 * - Ctrl+S 保存当前 tab; 关闭未保存 tab 弹确认
 * - dirty 判定: 编辑内容 !== 上次保存内容
 */
export default function EditorTabs({ workspaceId, openPath }: { workspaceId: string; openPath: string | null }) {
  const { t } = useTranslation();
  const [tabs, setTabs] = useState<Tab[]>([]);
  const [active, setActive] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const tabsRef = useRef<Tab[]>([]);
  tabsRef.current = tabs;

  const findTab = (path: string | null) => (path ? tabs.find((tb) => tb.path === path) : undefined);

  const save = useCallback(
    async (path: string | null = active) => {
      const tab = path ? tabsRef.current.find((tb) => tb.path === path) : undefined;
      if (!tab || tab.content.binary) return;
      try {
        await writeFile(workspaceId, tab.path, tab.content.content);
        setTabs((prev) =>
          prev.map((tb) => (tb.path === tab.path ? { ...tb, savedContent: tb.content.content } : tb)),
        );
      } catch (e) {
        setError(String(e));
      }
    },
    [workspaceId, active],
  );

  // Ctrl+S 保存当前 tab
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') {
        e.preventDefault();
        void save();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [save]);

  // 打开/激活文件 (workspaceId 变化时重置)
  useEffect(() => {
    setTabs([]);
    setActive(null);
    setError(null);
  }, [workspaceId]);

  useEffect(() => {
    if (!openPath) return;
    const existing = tabsRef.current.find((tb) => tb.path === openPath);
    if (existing) {
      setActive(openPath);
      return;
    }
    readFile(workspaceId, openPath)
      .then((fc) => {
        setTabs((prev) =>
          prev.some((tb) => tb.path === openPath)
            ? prev
            : [...prev, { path: openPath, content: fc, savedContent: fc.content }],
        );
        setActive(openPath);
      })
      .catch((e) => setError(String(e)));
  }, [workspaceId, openPath]);

  const close = (path: string) => {
    const tab = findTab(path);
    const doClose = () => {
      setTabs((prev) => {
        const idx = prev.findIndex((tb) => tb.path === path);
        const next = prev.filter((tb) => tb.path !== path);
        setActive((cur) => {
          if (cur !== path) return cur;
          return next[Math.min(idx, next.length - 1)]?.path ?? null;
        });
        return next;
      });
    };
    if (tab && tab.content.content !== tab.savedContent) {
      Modal.confirm({
        title: t('desktop.editor.closeConfirmTitle', { defaultValue: '未保存的更改' }),
        content: t('desktop.editor.closeConfirm', { defaultValue: '“{{path}}” 有未保存的更改, 关闭将丢弃。', path }),
        okText: t('desktop.editor.closeDiscard', { defaultValue: '丢弃并关闭' }),
        okButtonProps: { danger: true },
        cancelText: t('desktop.editor.closeCancel', { defaultValue: '取消' }),
        onOk: doClose,
      });
    } else {
      doClose();
    }
  };

  const current = findTab(active);
  const language = useMemo(() => guessLang(active ?? ''), [active]);

  if (error) return <div className="error-text">{error}</div>;
  if (tabs.length === 0 || !current) return <div className="empty-editor">{t('desktop.editor.selectFile')}</div>;

  if (current.content.binary) {
    return <div className="empty-editor">{t('desktop.editor.binary', { size: current.content.size })}</div>;
  }

  const dirty = current.content.content !== current.savedContent;

  return (
    <div className="editor-tab">
      <div className="tab-bar" role="tablist">
        {tabs.map((tb) => {
          const tbDirty = tb.content.content !== tb.savedContent;
          return (
            <span
              key={tb.path}
              role="tab"
              aria-selected={tb.path === active}
              className={`tab-title${tb.path === active ? ' active' : ''}`}
              onClick={() => setActive(tb.path)}
            >
              {tb.path.split(/[\\/]/).pop() ?? tb.path}
              {tbDirty ? ' ●' : ''}
              <button
                className="tab-close"
                aria-label={t('desktop.editor.closeTab', { defaultValue: '关闭' })}
                onClick={(e) => {
                  e.stopPropagation();
                  close(tb.path);
                }}
              >
                ×
              </button>
            </span>
          );
        })}
        <span className="tab-actions">
          {current.content.truncated && <span className="warn">{t('desktop.editor.truncated')}</span>}
          <span className="muted">{current.path}</span>
          <button disabled={!dirty} onClick={() => void save()}>
            {t('desktop.editor.save')}
          </button>
        </span>
      </div>
      <Editor
        height="100%"
        language={language}
        value={current.content.content}
        onChange={(v) => {
          const next = v ?? '';
          setTabs((prev) =>
            prev.map((tb) => (tb.path === active ? { ...tb, content: { ...tb.content, content: next } } : tb)),
          );
        }}
        options={{ readOnly: current.content.truncated, automaticLayout: true }}
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
