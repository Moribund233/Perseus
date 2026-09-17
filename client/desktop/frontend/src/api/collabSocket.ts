import { HocuspocusProvider } from '@hocuspocus/provider';
import { MonacoBinding } from 'y-monaco';
import * as monaco from 'monaco-editor';
import { useGatewayStore } from '../stores/gateway';
import { useServersStore } from '../stores/servers';
import { useIdentityStore } from '../stores/identity';

export type CollabStatus = 'connecting' | 'connected' | 'disconnected';

export interface CollabParticipant {
  clientID: string;
  user_id: string;
  username: string;
  color: string;
}

/** 网关广播的协作保存结果; 私密性收紧后仅含提交标识 */
export interface CollabSavedMsg {
  docKey: string;
  commit_id: string;
}

export interface CollabSessionOptions {
  serverId: string;
  docKey: string;
  onStatus?: (status: CollabStatus) => void;
  onParticipants?: (peers: CollabParticipant[]) => void;
  onSaved?: (msg: CollabSavedMsg) => void;
  onError?: (error: string) => void;
}

const PEER_COLORS = ['#1f6feb', '#3fb950', '#58a6ff', '#bc8cff', '#d29922', '#f85149', '#f0883e', '#7956d9'];

function peerColor(name: string): string {
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash);
  return PEER_COLORS[Math.abs(hash) % PEER_COLORS.length];
}

/**
 * Yjs 协作会话（desktop, Monaco）
 *
 * 底座与 web 一致：collab-gateway (Hocuspocus) + Yjs（共享文本 'content'，awareness
 * 字段 name/color/user_id 与 web 对齐）。差异仅在连接路径：
 *  - ws 地址为本地网关 /api/local/proxy/{serverId}/collab
 *  - provider token 传网关 token，Go 侧截获首帧 AuthenticationMessage 改写为
 *    密钥库 app access token 后转发（见 internal/gateway/handlers_collab.go）
 *  - 断线重连由 provider 驱动：网关关闭客户端连接 → provider 重拨 → 重发认证帧
 */
export class CollabSession {
  private opts: CollabSessionOptions;
  private provider: HocuspocusProvider | null = null;
  private binding: MonacoBinding | null = null;
  private status: CollabStatus = 'disconnected';

  constructor(opts: CollabSessionOptions) {
    this.opts = opts;
  }

  isActive(): boolean {
    return this.provider != null && this.binding != null;
  }

  hasPendingChanges(): boolean {
    return this.provider?.hasUnsyncedChanges ?? false;
  }

  /** 接入编辑器：建立 provider，onSynced 后以网关从 Git 加载的权威内容装配绑定。 */
  attach(editor: monaco.editor.IStandaloneCodeEditor): void {
    const me = useIdentityStore.getState().me;
    const username = me?.username ?? 'guest';
    const userId = me?.id ?? '';
    const { config } = useGatewayStore.getState();
    const base = config?.baseURL ?? '';
    const url = `${base.replace(/^http/, 'ws')}/api/local/proxy/${this.opts.serverId}/collab?_token=${encodeURIComponent(config?.gatewayToken ?? '')}`;

    const provider = new HocuspocusProvider({
      url,
      name: this.opts.docKey,
      token: config?.gatewayToken ?? '',
      onStatus: ({ status }) => {
        this.status = status as CollabStatus;
        if (this.status !== 'connected') this.opts.onParticipants?.([]);
        this.opts.onStatus?.(this.status);
      },
      onSynced: () => {
        const model = editor.getModel();
        const awareness = provider.awareness;
        if (!model || !awareness || this.binding) return;
        this.binding = new MonacoBinding(
          provider.document.getText('content'),
          model,
          new Set([editor]),
          awareness,
        );
        this.opts.onStatus?.('connected');
      },
      onStateless: ({ payload }) => this.handleStateless(payload),
      onAuthenticationFailed: ({ reason }) => this.opts.onError?.(reason || '协作认证失败'),
    });
    this.provider = provider;

    provider.awareness?.setLocalStateField('user', {
      name: username,
      color: peerColor(username),
      user_id: userId,
    });
    provider.awareness?.on('update', () => this.emitParticipants());
  }

  detach(): void {
    this.binding?.destroy();
    this.binding = null;
    this.provider?.destroy();
    this.provider = null;
    this.status = 'disconnected';
    this.opts.onParticipants?.([]);
    this.opts.onStatus?.('disconnected');
  }

  /** 显式保存：stateless → 网关回调 app 提交 Git → 全员广播 collab-saved。 */
  save(message: string): void {
    this.provider?.sendStateless(JSON.stringify({ type: 'collab-save', message }));
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
      const user = state.user as { name?: string; user_id?: string; color?: string } | undefined;
      peers.push({
        clientID: String(clientID),
        user_id: user?.user_id ?? '',
        username: user?.name ?? '',
        color: user?.color ?? peerColor(user?.name ?? '?'),
      });
    }
    this.opts.onParticipants?.(peers);
  }
}
