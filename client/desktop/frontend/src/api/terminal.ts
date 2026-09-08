import { base64ToBytes, bytesToBase64, wsUrl } from './wsUrl';

export type TerminalStatus = 'connecting' | 'connected' | 'disconnected';

export interface TerminalHandlers {
  onOutput?: (data: Uint8Array) => void;
  onExit?: (code: number) => void;
  onStatusChange?: (status: TerminalStatus) => void;
  onError?: (message: string) => void;
}

interface TerminalMessage {
  type: 'output' | 'exit' | 'input' | 'resize';
  data?: string;
  code?: number;
  cols?: number;
  rows?: number;
}

/**
 * 本地终端 WS 客户端（网关 ConPTY 桥）。
 * 协议：客户端→服务器 {"type":"input|resize"}；服务器→客户端 {"type":"output|exit"}。
 * 负载一律 base64（二元安全）。
 */
export class TerminalClient {
  private ws: WebSocket | null = null;
  private handlers: TerminalHandlers = {};

  setHandlers(handlers: TerminalHandlers) {
    this.handlers = handlers;
  }

  // connect 建立到工作区终端 WS 的连接并发送初始 resize。
  connect(workspaceId: string, cols = 120, rows = 30) {
    if (this.ws?.readyState === WebSocket.OPEN) return;
    this.handlers.onStatusChange?.('connecting');
    const ws = new WebSocket(wsUrl(`/api/local/workspaces/${workspaceId}/terminal`));
    this.ws = ws;

    ws.onopen = () => {
      this.handlers.onStatusChange?.('connected');
      this.resize(cols, rows);
    };
    ws.onmessage = (ev) => this.dispatch(ev.data as string);
    ws.onclose = () => {
      if (this.ws !== ws) return;
      this.ws = null;
      this.handlers.onStatusChange?.('disconnected');
    };
    ws.onerror = () => {
      if (this.ws === ws) ws.close();
    };
  }

  write(bytes: Uint8Array) {
    this.send({ type: 'input', data: bytesToBase64(bytes) });
  }

  // writeText 按 UTF-8 编码发送命令文本。
  writeText(text: string) {
    this.write(new TextEncoder().encode(text));
  }

  resize(cols: number, rows: number) {
    this.send({ type: 'resize', cols, rows });
  }

  close() {
    this.ws?.close();
    this.ws = null;
  }

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  private send(msg: TerminalMessage) {
    if (this.ws?.readyState !== WebSocket.OPEN) return;
    this.ws.send(JSON.stringify(msg));
  }

  private dispatch(raw: string) {
    let msg: TerminalMessage;
    try {
      msg = JSON.parse(raw) as TerminalMessage;
    } catch {
      return;
    }
    switch (msg.type) {
      case 'output':
        if (msg.data != null) {
          this.handlers.onOutput?.(base64ToBytes(msg.data));
        }
        break;
      case 'exit':
        this.handlers.onExit?.(msg.code ?? -1);
        this.close();
        break;
    }
  }
}

export const terminalClient = new TerminalClient();