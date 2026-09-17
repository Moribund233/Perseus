import { Compartment } from '@codemirror/state';
import { yCollab } from 'y-codemirror.next';
import { HocuspocusProvider } from '@hocuspocus/provider';
import { useAuthStore } from '../../stores/auth';

/** 协作连接状态 */
export type CollabSocketStatus = 'connecting' | 'connected' | 'disconnected';

/** 会话参与者 (来自 awareness) */
export interface CollabParticipant {
  clientID: string;
  user_id: string;
  username: string;
  cursor: { anchor: number; head: number } | null;
}

/** 网关广播的协作保存结果 (collab-gateway onStateless)
 *  私密性收紧: 仅含提交标识, 不携带 saved_by/branch/path/message 等元数据 */
export interface CollabSavedMsg {
  docKey: string;
  commit_id: string;
}

export interface CollabControllerOptions {
  docKey: string;
  repositoryId: string;
  branch: string;
  path: string;
  /** 邀请链接访客 token (可选): 无仓库角色者凭此获得会话级临时权限 */
  inviteToken?: string;
  onStatus?: (status: CollabSocketStatus) => void;
  onParticipants?: (peers: CollabParticipant[]) => void;
  onSaved?: (msg: CollabSavedMsg) => void;
  onError?: (error: string) => void;
}

/** 光标/选区配色 (与编辑器页面 avatarColors 保持一致) */
const PEER_COLORS = ['#1f6feb', '#3fb950', '#58a6ff', '#bc8cff', '#d29922', '#f85149', '#f0883e', '#7956d9'];

function peerColor(name: string): string {
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash);
  return PEER_COLORS[Math.abs(hash) % PEER_COLORS.length];
}

/**
 * Yjs 协作会话控制器 (web 端, CM6)
 *
 * 底座: collab-gateway (Hocuspocus) + y-codemirror.next
 * - 同步/远端光标渲染/断线重连缓冲全部由 CRDT 底座承担, 无需自研协议
 * - 断线期间本地编辑保留在内存文档中, 重连后自动 rebase 同步
 *   (替代旧 F-204 的 "重连整篇覆盖", 见 collab-f204-vs-cwm.md 3.6 方案 B)
 * - 显式保存: sendStateless("collab-save") → 网关回调 app 提交 Git →
 *   全员广播 collab-saved (commit_id), 语义与旧 F-204 一致
 */
export class CollabController {
  private opts: CollabControllerOptions;
  private view: import('@codemirror/view').EditorView | null = null;
  private compartment: Compartment | null = null;
  private provider: HocuspocusProvider | null = null;
  private lastStatus: CollabSocketStatus = 'disconnected';
  private configured = false;

  constructor(opts: CollabControllerOptions) {
    this.opts = opts;
  }

  get status(): CollabSocketStatus {
    return this.lastStatus;
  }

  get isActive(): boolean {
    return this.provider !== null && this.provider.synced && this.lastStatus === 'connected';
  }

  attach(view: import('@codemirror/view').EditorView, compartment: Compartment): void {
    this.view = view;
    this.compartment = compartment;

    const token = useAuthStore.getState().accessToken ?? '';
    const username = useAuthStore.getState().user?.username ?? 'guest';
    const userId = useAuthStore.getState().user?.id ?? '';
    // 邀请链接访客: 以 JSON 承载 access + invite 双凭证, 网关解析后转发给 app
    const connectionToken = this.opts.inviteToken
      ? JSON.stringify({ access_token: token, invite_token: this.opts.inviteToken })
      : token;

    const provider = new HocuspocusProvider({
      url: this.resolveWsUrl(),
      name: this.opts.docKey,
      token: connectionToken,
      onStatus: ({ status }) => {
        this.lastStatus = status === 'connected' ? 'connected' : status === 'connecting' ? 'connecting' : 'disconnected';
        if (this.lastStatus === 'disconnected') this.opts.onParticipants?.([]);
        this.opts.onStatus?.(this.lastStatus);
      },
      onSynced: () => this.configure(),
      onStateless: ({ payload }) => this.handleStateless(payload),
      onAuthenticationFailed: ({ reason }) => this.opts.onError?.(reason || '协作认证失败'),
    });
    this.provider = provider;

    // awareness 用户信息: 远端光标标签 + 参与者列表
    provider.awareness?.setLocalStateField('user', {
      name: username,
      color: peerColor(username),
      user_id: userId,
    });
    provider.awareness?.on('update', () => this.emitParticipants());
    this.emitParticipants();
  }

  detach(): void {
    this.provider?.destroy();
    this.provider = null;
    this.view = null;
    this.compartment = null;
    this.configured = false;
  }

  save(message: string): void {
    this.provider?.sendStateless(JSON.stringify({ type: 'collab-save', message }));
  }

  /** 本地是否仍有未同步到服务端的变更 (断线缓冲期间为 true) */
  hasPendingChanges(): boolean {
    return this.provider ? this.provider.hasUnsyncedChanges : false;
  }

  private resolveWsUrl(): string {
    const base = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000';
    // VITE_API_URL 为空字符串 = 与页面同源 (走网关)
    if (base === '') {
      const proto = location.protocol === 'https:' ? 'wss' : 'ws';
      return `${proto}://${location.host}/ws/collab`;
    }
    return `${base.replace(/^http/, 'ws')}/ws/collab`;
  }

  /** 同步完成后装配 yCollab 扩展 (以网关从 Git 加载的权威内容为准) */
  private configure(): void {
    const view = this.view;
    const provider = this.provider;
    const awareness = provider?.awareness;
    if (!view || !this.compartment || !provider || !awareness || this.configured) return;

    view.dispatch({
      effects: this.compartment.reconfigure([
        yCollab(provider.document.getText('content'), awareness),
      ]),
    });
    this.configured = true;
    this.emitParticipants();
  }

  private handleStateless(payload: string): void {
    let msg: { type?: string; docKey?: string; error?: string };
    try {
      msg = JSON.parse(payload);
    } catch {
      return;
    }
    if (msg.type === 'collab-saved') {
      if (msg.docKey === this.opts.docKey) this.opts.onSaved?.(msg as unknown as CollabSavedMsg);
    } else if (msg.type === 'collab-save-error') {
      if (msg.docKey === this.opts.docKey) this.opts.onError?.(msg.error || '保存失败');
    }
  }

  private emitParticipants(): void {
    const awareness = this.provider?.awareness;
    if (!awareness) {
      this.opts.onParticipants?.([]);
      return;
    }
    const peers: CollabParticipant[] = [];
    for (const [clientID, state] of awareness.getStates()) {
      const user = state.user as { name?: string; user_id?: string } | undefined;
      peers.push({
        clientID: String(clientID),
        user_id: user?.user_id ?? '',
        username: user?.name ?? '',
        cursor: null,
      });
    }
    this.opts.onParticipants?.(peers);
  }
}
