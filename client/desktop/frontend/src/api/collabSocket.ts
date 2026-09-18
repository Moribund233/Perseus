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
  /** 该参与者正在跟随的 clientID (follow.target), 未跟随时为 null */
  following: string | null;
  /** 是否为本地客户端 */
  isSelf: boolean;
}

/** 跟随模式状态 (Follow me) */
export interface FollowState {
  /** 本地正在跟随的 clientID */
  following: string | null;
  /** 被跟随者用户名 (用于展示) */
  followingName: string | null;
  /** 正在跟随本地客户端的其他客户端数量 */
  followerCount: number;
  /** 本地是否已发起"跟我来" */
  spotlightOn: boolean;
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
  onFollowChange?: (state: FollowState) => void;
  onSaved?: (msg: CollabSavedMsg) => void;
  onError?: (error: string) => void;
}

const PEER_COLORS = ['#1f6feb', '#3fb950', '#58a6ff', '#bc8cff', '#d29922', '#f85149', '#f0883e', '#7956d9'];

/** 视口位置广播节流 (ms): 仅在存在跟随者时按需推送 */
const VIEWPORT_THROTTLE_MS = 120;

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
 *
 * F-607 跟随模式与 web 协议一致：viewport/follow 落 awareness（网关盖章校验），
 * "跟我来"走 stateless collab-spotlight。viewport.anchor 采用文档字符偏移
 * （顶部可视行首 offset），与 web(CM6 block.from) 同单位，跨运行时可互相跟随。
 */
export class CollabSession {
  private opts: CollabSessionOptions;
  private provider: HocuspocusProvider | null = null;
  private binding: MonacoBinding | null = null;
  private editor: monaco.editor.IStandaloneCodeEditor | null = null;
  private status: CollabStatus = 'disconnected';
  private followTarget: string | null = null;
  private lastAppliedAnchor: number | null = null;
  private lastBroadcastAnchor: number | null = null;
  private spotlightOn = false;
  private followers = new Set<string>();
  private viewportTimer: ReturnType<typeof setTimeout> | null = null;
  private scrollCleanup: (() => void) | null = null;

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
    this.editor = editor;
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

    // 用户主动滚动/点击/键盘输入即退出跟随；程序化滚动 (reveal) 不触发这些事件
    const dom = editor.getDomNode();
    if (dom) {
      const onUserIntent = (e: Event) => {
        if (e instanceof KeyboardEvent && (e.ctrlKey || e.metaKey || e.altKey)) return;
        if (this.followTarget) this.follow(null);
      };
      dom.addEventListener('wheel', onUserIntent, { passive: true });
      dom.addEventListener('touchstart', onUserIntent, { passive: true });
      dom.addEventListener('pointerdown', onUserIntent, { passive: true });
      dom.addEventListener('keydown', onUserIntent);
      this.scrollCleanup = () => {
        dom.removeEventListener('wheel', onUserIntent);
        dom.removeEventListener('touchstart', onUserIntent);
        dom.removeEventListener('pointerdown', onUserIntent);
        dom.removeEventListener('keydown', onUserIntent);
      };
    }
    // 视口变化时按需广播 (仅当有跟随者)
    editor.onDidScrollChange(() => {
      if (this.followers.size > 0) this.scheduleViewportBroadcast();
    });
  }

  detach(): void {
    this.binding?.destroy();
    this.binding = null;
    if (this.viewportTimer) {
      clearTimeout(this.viewportTimer);
      this.viewportTimer = null;
    }
    this.scrollCleanup?.();
    this.scrollCleanup = null;
    this.editor = null;
    this.provider?.destroy();
    this.provider = null;
    this.status = 'disconnected';
    this.followTarget = null;
    this.spotlightOn = false;
    this.followers = new Set();
    this.lastAppliedAnchor = null;
    this.lastBroadcastAnchor = null;
    this.opts.onParticipants?.([]);
    this.opts.onFollowChange?.({ following: null, followingName: null, followerCount: 0, spotlightOn: false });
    this.opts.onStatus?.('disconnected');
  }

  /** 显式保存：stateless → 网关回调 app 提交 Git → 全员广播 collab-saved。 */
  save(message: string): void {
    this.provider?.sendStateless(JSON.stringify({ type: 'collab-save', message }));
  }

  /** 开始/停止跟随指定参与者 (clientID); null 表示停止跟随 */
  follow(clientID: string | null): void {
    const awareness = this.provider?.awareness;
    if (!awareness) return;
    this.followTarget = clientID;
    this.lastAppliedAnchor = null;
    awareness.setLocalStateField('follow', clientID == null ? null : { target: Number(clientID) });
    // 立即同步一次目标视口, 避免等待其下一次滚动
    if (clientID != null) this.applyTargetAnchor(awareness, clientID);
    this.emitParticipants();
  }

  /** 发起/结束"跟我来" (spotlight): 网关校验写权限并全员广播 */
  setSpotlight(on: boolean): void {
    this.provider?.sendStateless(JSON.stringify({ type: 'collab-spotlight', on }));
  }

  private handleStateless(payload: string): void {
    let msg: { type?: string; docKey?: string; error?: string; on?: boolean; from?: { user_id?: string } };
    try {
      msg = JSON.parse(payload);
    } catch {
      return;
    }
    if (msg.type === 'collab-saved') {
      if (msg.docKey === this.opts.docKey) this.opts.onSaved?.(msg as unknown as CollabSavedMsg);
    } else if (msg.type === 'collab-save-error') {
      if (msg.docKey === this.opts.docKey) this.opts.onError?.(msg.error || '保存失败');
    } else if (msg.type === 'collab-spotlight') {
      if (msg.docKey === this.opts.docKey) this.handleSpotlight(msg.on !== false, msg.from?.user_id);
    } else if (msg.type === 'collab-spotlight-error') {
      if (msg.docKey === this.opts.docKey) this.opts.onError?.(msg.error || '无法发起跟随引导');
    }
  }

  /** 收到"跟我来"信令: on 时定位发起者并跟随; off 时若正跟随发起者则停止 */
  private handleSpotlight(on: boolean, fromUserId?: string): void {
    const awareness = this.provider?.awareness;
    if (!awareness || !fromUserId) return;
    const targetId = this.findClientByUserId(fromUserId);
    const isSelf = targetId != null && targetId === String(awareness.clientID);
    if (on) {
      if (isSelf) {
        this.spotlightOn = true;
        this.emitParticipants();
      } else if (targetId) {
        this.follow(targetId);
      }
    } else {
      if (isSelf) this.spotlightOn = false;
      if (targetId && this.followTarget === targetId) this.follow(null);
      else this.emitParticipants();
    }
  }

  private findClientByUserId(userId?: string): string | null {
    const awareness = this.provider?.awareness;
    if (!awareness || !userId) return null;
    for (const [clientID, state] of awareness.getStates()) {
      const user = state.user as { user_id?: string } | undefined;
      if (user?.user_id === userId) return String(clientID);
    }
    return null;
  }

  private applyTargetAnchor(awareness: NonNullable<HocuspocusProvider['awareness']>, targetId: string): void {
    const state = awareness.getStates().get(Number(targetId));
    const viewport = state?.viewport as { anchor?: number } | undefined;
    if (viewport?.anchor != null && viewport.anchor !== this.lastAppliedAnchor) {
      this.lastAppliedAnchor = viewport.anchor;
      this.scrollToOffset(viewport.anchor);
    }
  }

  /** 滚到文档字符偏移对应的可视区 */
  private scrollToOffset(offset: number): void {
    const editor = this.editor;
    const model = editor?.getModel();
    if (!editor || !model) return;
    const pos = model.getPositionAt(Math.max(0, Math.min(offset, model.getValueLength())));
    editor.revealLineInCenter(pos.lineNumber);
  }

  /** 顶部可视行 (scrollTop → 行号) 的字符偏移, 与 web(CM6 block.from) 同单位 */
  private scheduleViewportBroadcast(): void {
    if (this.viewportTimer) return;
    this.viewportTimer = setTimeout(() => {
      this.viewportTimer = null;
      const editor = this.editor;
      const awareness = this.provider?.awareness;
      const model = editor?.getModel();
      if (!editor || !awareness || !model) return;
      const top = editor.getScrollTop();
      let lo = 1;
      let hi = model.getLineCount();
      while (lo < hi) {
        const mid = Math.floor((lo + hi + 1) / 2);
        if (editor.getTopForLineNumber(mid) <= top) lo = mid;
        else hi = mid - 1;
      }
      const offset = model.getOffsetAt({ lineNumber: lo, column: 1 });
      // 视口未变则不重复广播, 避免 awareness 更新自触发循环
      if (offset === this.lastBroadcastAnchor) return;
      this.lastBroadcastAnchor = offset;
      awareness.setLocalStateField('viewport', { anchor: offset });
    }, VIEWPORT_THROTTLE_MS);
  }

  private emitParticipants(): void {
    const awareness = this.provider?.awareness;
    if (!awareness) {
      this.opts.onParticipants?.([]);
      this.opts.onFollowChange?.({ following: null, followingName: null, followerCount: 0, spotlightOn: false });
      return;
    }
    const myId = String(awareness.clientID);

    // 跟随目标已离线 → 自动停止跟随
    if (this.followTarget && !awareness.getStates().has(Number(this.followTarget))) {
      this.followTarget = null;
      this.lastAppliedAnchor = null;
      awareness.setLocalStateField('follow', null);
    }

    const peers: CollabParticipant[] = [];
    const followers = new Set<string>();
    const targetState = this.followTarget ? awareness.getStates().get(Number(this.followTarget)) : undefined;
    const targetAnchor = (targetState?.viewport as { anchor?: number } | undefined)?.anchor ?? null;
    const targetName = (targetState?.user as { name?: string } | undefined)?.name;

    for (const [clientID, state] of awareness.getStates()) {
      const fid = String(clientID);
      const user = state.user as { name?: string; user_id?: string; color?: string } | undefined;
      const follow = state.follow as { target?: number | null } | undefined;
      const following = follow?.target == null ? null : String(follow.target);
      const isSelf = fid === myId;
      if (!isSelf && following === myId) followers.add(fid);
      peers.push({
        clientID: fid,
        user_id: user?.user_id ?? '',
        username: user?.name ?? '',
        color: user?.color ?? peerColor(user?.name ?? '?'),
        following,
        isSelf,
      });
    }

    // 目标视口变化 → 平滑滚动跟随
    if (this.followTarget && targetAnchor != null && targetAnchor !== this.lastAppliedAnchor) {
      this.lastAppliedAnchor = targetAnchor;
      this.scrollToOffset(targetAnchor);
    }

    this.followers = followers;
    this.opts.onParticipants?.(peers);
    this.opts.onFollowChange?.({
      following: this.followTarget,
      followingName: this.followTarget ? targetName ?? '…' : null,
      followerCount: followers.size,
      spotlightOn: this.spotlightOn,
    });

    // 有新的跟随者加入时立即广播当前视口 (否则其需等待后续滚动)
    if (followers.size > 0) this.scheduleViewportBroadcast();
  }
}