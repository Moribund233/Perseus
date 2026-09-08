import { wsUrl } from './wsUrl';

export type LspStatus = 'connecting' | 'connected' | 'disconnected';

export interface LspHandlers {
  onStatusChange?: (status: LspStatus) => void;
  onError?: (message: string) => void;
}

interface Pending {
  resolve: (value: unknown) => void;
  reject: (err: Error) => void;
  timer: ReturnType<typeof setTimeout>;
}

interface OpenDoc {
  uri: string;
  languageId: string;
  version: number;
  getText: () => string;
}

interface LangServerNotification {
  method?: string;
  id?: number;
  result?: unknown;
  error?: { code?: number; message?: string };
  params?: unknown;
}

/**
 * LSP WS 客户端（网关透明 JSON-RPC 桥）。
 * 一条 WS 消息 = 一条完整 LSP 帧正文（JSON-RPC）。协议由本客户端驱动：
 * initialize → initialized → didOpen/didChange/didSave/didClose → shutdown/exit。
 *
 * 崩溃恢复：收到网关注入的 $/perseus/lspRestarted 通知后，自动重新 initialize
 * 并回放当前打开文档（spec §8.2 重启策略的前端实现）。
 */
export class LspClient {
  private ws: WebSocket | null = null;
  private nextId = 1;
  private pending = new Map<number, Pending>();
  private workspaceId = '';
  private lang = '';
  private handlers: LspHandlers = {};
  private initParams: Record<string, unknown> | null = null;
  private openDocs = new Map<string, OpenDoc>();

  setHandlers(handlers: LspHandlers) {
    this.handlers = handlers;
  }

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  // connect 建立 WS 连接；resolve 表示网关已升级连接。
  async connect(workspaceId: string, lang: string): Promise<void> {
    if (this.ws?.readyState === WebSocket.OPEN) return;
    this.workspaceId = workspaceId;
    this.lang = lang;
    this.handlers.onStatusChange?.('connecting');

    return new Promise((resolve, reject) => {
      const ws = new WebSocket(wsUrl(`/api/local/workspaces/${workspaceId}/lsp?lang=${encodeURIComponent(lang)}`));
      this.ws = ws;
      ws.onopen = () => {
        resolve();
        this.handlers.onStatusChange?.('connected');
      };
      ws.onmessage = (ev) => this.dispatch(ev.data as string);
      ws.onerror = () => {
        if (this.ws === ws) {
          reject(new Error(`LSP 连接失败 (${lang})`));
          ws.close();
        }
      };
      ws.onclose = () => {
        if (this.ws !== ws) return;
        this.ws = null;
        this.rejectAll(new Error('LSP 连接已关闭'));
        this.handlers.onStatusChange?.('disconnected');
      };
    });
  }

  // initialize 返回 capabilities。
  async initialize(params: Record<string, unknown>): Promise<unknown> {
    this.initParams = params;
    return this.request('initialize', params);
  }

  notifyInitialized(params: Record<string, unknown> = {}) {
    this.notify('initialized', params);
  }

  // didOpen 注册文档并通知服务器。
  didOpen(uri: string, languageId: string, getText: () => string) {
    const text = getText();
    this.openDocs.set(uri, { uri, languageId, version: 1, getText });
    this.notify('textDocument/didOpen', {
      textDocument: { uri, languageId, version: 1, text },
    });
  }

  didChange(uri: string, getText: () => string) {
    const doc = this.openDocs.get(uri);
    if (!doc) return;
    const version = doc.version + 1;
    doc.version = version;
    doc.getText = getText;
    this.notify('textDocument/didChange', {
      textDocument: { uri, version },
      contentChanges: [{ text: getText() }],
    });
  }

  didSave(uri: string) {
    this.notify('textDocument/didSave', { textDocument: { uri } });
  }

  didClose(uri: string) {
    this.openDocs.delete(uri);
    this.notify('textDocument/didClose', { textDocument: { uri } });
  }

  // request 发送同步请求，按 id 关联响应（默认 15s 超时）。
  request<T = unknown>(method: string, params: Record<string, unknown>, timeoutMs = 15_000): Promise<T> {
    const id = this.nextId++;
    const payload = { jsonrpc: '2.0', id, method, params };
    return new Promise<T>((resolve, reject) => {
      if (this.ws?.readyState !== WebSocket.OPEN) {
        reject(new Error('LSP 未连接'));
        return;
      }
      const timer = setTimeout(() => {
        this.pending.delete(id);
        reject(new Error(`LSP 请求超时: ${method}`));
      }, timeoutMs);
      this.pending.set(id, { resolve: (v) => resolve(v as T), reject, timer });
      this.ws.send(JSON.stringify(payload));
    });
  }

  notify(method: string, params: Record<string, unknown>) {
    if (this.ws?.readyState !== WebSocket.OPEN) return;
    this.ws.send(JSON.stringify({ jsonrpc: '2.0', method, params }));
  }

  // gracefulClose 完成 LSP 生命周期（shutdown → exit）后关闭连接。
  async gracefulClose(): Promise<void> {
    try {
      await this.request('shutdown', {});
    } catch {
      /* 忽略关机失败 */
    }
    this.notify('exit', {});
    this.close();
  }

  close() {
    this.ws?.close();
    this.ws = null;
    this.initParams = null;
    this.openDocs.clear();
  }

  private dispatch(raw: string) {
    let msg: LangServerNotification;
    try {
      msg = JSON.parse(raw) as LangServerNotification;
    } catch {
      return;
    }

    if (msg.id !== undefined && msg.method === undefined) {
      this.resolveResponse(msg);
      return;
    }
    if (!msg.method) return;

    if (msg.method === '$/perseus/lspRestarted') {
      void this.reinit();
      return;
    }
    if (msg.method === 'window/logMessage') {
      const p = (msg.params ?? {}) as { message?: string };
      if (p.message) this.handlers.onError?.(p.message);
      return;
    }
    this.onNotification?.(msg.method, msg.params);
  }

  // onNotification 供上层（Monaco provider）消费服务器通知（publishDiagnostics 等）。
  onNotification?: (method: string, params: unknown) => void;

  private resolveResponse(msg: LangServerNotification) {
    const id = msg.id!;
    const p = this.pending.get(id);
    if (!p) return;
    this.pending.delete(id);
    clearTimeout(p.timer);
    if (msg.error) {
      p.reject(new Error(`LSP 错误(${msg.error.code}): ${msg.error.message}`));
      return;
    }
    p.resolve(msg.result);
  }

  // reinit 崩溃重启后重新握手并回放打开文档。
  private async reinit(): Promise<void> {
    this.rejectAll(new Error('LSP 服务器已重启，协议已重置'));
    if (!this.initParams) return;
    try {
      await this.request('initialize', this.initParams);
    } catch (err) {
      this.handlers.onError?.(`重新初始化失败: ${(err as Error).message}`);
      return;
    }
    this.notifyInitialized();
    for (const doc of this.openDocs.values()) {
      this.notify('textDocument/didOpen', {
        textDocument: { uri: doc.uri, languageId: doc.languageId, version: doc.version, text: doc.getText() },
      });
    }
  }

  private rejectAll(err: Error) {
    for (const [, p] of this.pending) {
      clearTimeout(p.timer);
      p.reject(err);
    }
    this.pending.clear();
  }
}

export const lspClient = new LspClient();