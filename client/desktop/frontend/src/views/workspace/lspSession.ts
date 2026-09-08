import { lspClient } from '../../api/lsp';
import { useLspStore } from '../../stores/lsp';
import { applyPublishDiagnostics, useProblemsStore } from '../../stores/problems';
import { logLsp } from '../../stores/logs';
import * as monaco from 'monaco-editor';

// lspSession：按 工作区+语言 管理单一 LSP 会话，驱动 didOpen/Change/Save/Close，
// 并把 publishDiagnostics 落到 problems store（→ 面板 + Monaco markers）。
// 只允许一个连接的会话；切换工作区时由 IdeShell 调用的 lspShutdown 重建。

const LANG_BY_EXT: Record<string, string> = {
  '.py': 'python',
  '.ts': 'typescript',
  '.tsx': 'typescript',
  '.js': 'typescript',
  '.jsx': 'typescript',
  '.mts': 'typescript',
  '.cts': 'typescript',
  '.mjs': 'typescript',
  '.cjs': 'typescript',
};

export function langForPath(path: string): string | null {
  const dot = path.lastIndexOf('.');
  return dot < 0 ? null : (LANG_BY_EXT[path.slice(dot).toLowerCase()] ?? null);
}

// file://… URI（Monaco model 与 LSP 共用）。
export function fileUri(rootPath: string, rel: string): string {
  const root = rootPath.replace(/[\\/]+$/, '').replace(/\\/g, '/');
  return 'file:///' + encodeURI(`${root}/${rel}`);
}

export function uriToAbs(uri: string): string {
  return decodeURIComponent(uri.replace(/^file:\/\//i, ''));
}

let root = '';

// 宽松比较：Windows 大写盘符 / 分隔符差异视为同一文件。
function sameFile(a: string, b: string): boolean {
  const n = (s: string) => s.replace(/\\/g, '/').toLowerCase();
  return n(a) === n(b);
}

export function toMonacoSeverity(sev: number): monaco.MarkerSeverity {
  switch (sev) {
    case 1: return monaco.MarkerSeverity.Error;
    case 2: return monaco.MarkerSeverity.Warning;
    case 3: return monaco.MarkerSeverity.Info;
    default: return monaco.MarkerSeverity.Hint;
  }
}

interface OpenDoc {
  lang: string;
  uri: string;
  getText: () => string;
}

const openDocs = new Map<string, OpenDoc>();
let wsId = '';
let sessionLang: string | null = null;
let starting: Promise<void> | null = null;

function connectOnce(workspaceId: string, lang: string): Promise<void> {
  if (starting && wsId === workspaceId && sessionLang === lang) return starting;
  return (starting = (async () => {
    // 换语言/换工作区：先撤旧会话，避免双进程并存。
    const prevLang = sessionLang;
    wsId = workspaceId;
    sessionLang = lang;
    if (prevLang && lspClient.isConnected) {
      try { await lspClient.gracefulClose(); } catch { /* 忽略 */ }
    }
    useLspStore.setState({ lang, status: 'connecting' });
    lspClient.onNotification = (method, params) => {
      if (method === 'textDocument/publishDiagnostics') {
        applyPublishDiagnostics(params);
      } else if (method === 'window/logMessage') {
        const p = (params ?? {}) as { message?: string; type?: number };
        if (p.message) logLsp(p.message);
      }
    };
    try {
      await lspClient.connect(workspaceId, lang);
      const rootUri = 'file:///' + (root.replace(/[\\/]+$/, '').replace(/\\/g, '/'));
      useLspStore.getState().setError(null);
      await lspClient.initialize({
        processId: null,
        rootUri,
        capabilities: {
          textDocument: {
            synchronization: { didSave: true },
            publishDiagnostics: { relatedInformation: true },
          },
          workspace: { workspaceFolders: true },
        },
      });
      lspClient.notifyInitialized();
      useLspStore.setState({ status: 'connected' });
      for (const doc of openDocs.values()) {
        if (doc.lang === lang) lspClient.didOpen(doc.uri, doc.lang, doc.getText);
      }
      logLsp(`${lang} 语言服务器已启动`);
    } catch (e) {
      sessionLang = null;
      starting = null;
      useLspStore.setState({ status: 'disconnected', error: (e as Error).message });
      logLsp(`LSP 启动失败(${lang}): ${(e as Error).message}`);
    }
  })());
}

export function lspOpen(workspaceId: string, rootPath: string, rel: string, getText: () => string): void {
  const lang = langForPath(rel);
  if (!lang) return;
  root = rootPath;
  openDocs.set(rel, { lang, uri: fileUri(rootPath, rel), getText });
  void connectOnce(workspaceId, lang).then(() => {
    const doc = openDocs.get(rel);
    if (doc && lspClient.isConnected) lspClient.didOpen(doc.uri, doc.lang, doc.getText);
    else if (doc) logLsp(`LSP ${lang} 未就绪，跳过 ${rel} 的 didOpen`);
  });
}

let changeTimer: ReturnType<typeof setTimeout> | null = null;
export function lspChange(rel: string): void {
  if (changeTimer) clearTimeout(changeTimer);
  changeTimer = setTimeout(() => {
    const doc = openDocs.get(rel);
    if (doc && lspClient.isConnected) lspClient.didChange(doc.uri, doc.getText);
  }, 300);
}

export function lspSave(rel: string): void {
  const doc = openDocs.get(rel);
  if (doc && lspClient.isConnected) lspClient.didSave(doc.uri);
}

export function lspClose(rel: string): void {
  const doc = openDocs.get(rel);
  if (doc) {
    if (lspClient.isConnected) lspClient.didClose(doc.uri);
    openDocs.delete(rel);
  }
}

export function isLspReady(): boolean {
  return sessionLang !== null && lspClient.isConnected;
}

// 把 problems store 中属于该 model 的诊断落到 Monaco markers。
export function applyModelDiagnostics(model: monaco.editor.ITextModel | null): void {
  if (!model) return;
  const modelAbs = uriToAbs(model.uri.toString());
  const diagnostics = useProblemsStore.getState().diagnostics;
  const markers: monaco.editor.IMarkerData[] = diagnostics
    .filter((d) => sameFile(uriToAbs(d.uri), modelAbs))
    .map((d) => ({
      severity: toMonacoSeverity(d.severity),
      message: d.message,
      startLineNumber: d.range.start.line + 1,
      startColumn: d.range.start.character + 1,
      endLineNumber: d.range.end.line + 1,
      endColumn: Math.max(d.range.end.character + 1, d.range.start.character + 2),
      source: d.source,
    }));
  monaco.editor.setModelMarkers(model, 'perseus', markers);
}

export function lspShutdown(): void {
  if (changeTimer) {
    clearTimeout(changeTimer);
    changeTimer = null;
  }
  openDocs.clear();
  starting = null;
  if (sessionLang && lspClient.isConnected) {
    void lspClient.gracefulClose();
  }
  sessionLang = null;
  wsId = '';
  root = '';
  useLspStore.setState({ status: 'idle', lang: null, error: null });
}