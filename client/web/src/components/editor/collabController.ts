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
  /** 正在跟随本地客户端的其他 clientID 列表 */
  followers: string[];
  /** 本地是否已发起"跟我来" */
  spotlightOn: boolean;
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
  onFollowChange?: (state: FollowState) => void;
  onSaved?: (msg: CollabSavedMsg) => void;
  onError?: (error: string) => void;
}

/** 光标/选区配色 (与编辑器页面 avatarColors 保持一致) */
const PEER_COLORS = ['#1f6feb', '#3fb950', '#58a6ff', '#bc8cff', '#d29922', '#f85149', '#f0883e', '#7956d9'];

/** 视口位置广播节流 (ms): 仅在存在跟随者时按需推送 */
const VIEWPORT_THROTTLE_MS = 120;

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
 *   全员广播 collab-saved (commit_id), 语义与旧 F-204 一致;
 *   draft=true 时 app 落到 collab/draft-{branch} 草稿分支 (F-606 空闲自动落盘)
 * - 跟随模式 (F-607, 2026-09-17 后端就绪): 跟随关系落 awareness
 *   (viewport 视口锚点 + follow.target), "跟我来"走 stateless collab-spotlight
 */
export class CollabController {
  private opts: CollabControllerOptions;
  private view: import('@codemirror/view').EditorView | null = null;
  private compartment: Compartment | null = null;
  private provider: HocuspocusProvider | null = null;
  private lastStatus: CollabSocketStatus = 'disconnected';
  private configured = false;

  // 跟随模式状态
  private followTarget: string | null = null;
  private spotlightOn = false;
  private followers = new Set<string>();
  private lastAppliedAnchor: number | null = null;
  private lastBroadcastAnchor: number | null = null;
  private viewportTimer: ReturnType<typeof setTimeout> | null = null;
  private scrollCleanup: (() => void) | null = null;

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
        if (this.lastStatus === 'disconnected') {
          this.followers = new Set();
          this.opts.onParticipants?.([]);
          this.emitFollow([]);
        }
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

    // 用户主动滚动/输入即退出跟随 (wheel/touch 手势 + 键盘)
    const dom = view.scrollDOM;
    const onUserIntent = (e: Event) => {
      if (e instanceof KeyboardEvent && (e.ctrlKey || e.metaKey || e.altKey)) return;
      if (this.followTarget) this.follow(null);
    };
    // 视口变化时按需广播 (仅当有跟随者)
    const onScroll = () => {
      if (this.followers.size > 0) this.scheduleViewportBroadcast();
    };
    dom.addEventListener('wheel', onUserIntent, { passive: true });
    dom.addEventListener('touchstart', onUserIntent, { passive: true });
    dom.addEventListener('pointerdown', onUserIntent);
    dom.addEventListener('scroll', onScroll, { passive: true });
    view.contentDOM.addEventListener('keydown', onUserIntent);
    this.scrollCleanup = () => {
      dom.removeEventListener('wheel', onUserIntent);
      dom.removeEventListener('touchstart', onUserIntent);
      dom.removeEventListener('pointerdown', onUserIntent);
      dom.removeEventListener('scroll', onScroll);
      view.contentDOM.removeEventListener('keydown', onUserIntent);
    };

    this.emitParticipants();
  }

  detach(): void {
    if (this.viewportTimer != null) {
      clearTimeout(this.viewportTimer);
      this.viewportTimer = null;
    }
    this.scrollCleanup?.();
    this.scrollCleanup = null;
    this.provider?.destroy();
    this.provider = null;
    this.view = null;
    this.compartment = null;
    this.configured = false;
    this.followTarget = null;
    this.spotlightOn = false;
    this.followers = new Set();
    this.lastAppliedAnchor = null;
    this.lastBroadcastAnchor = null;
  }

  save(message: string, opts?: { draft?: boolean }): void {
    this.provider?.sendStateless(JSON.stringify({ type: 'collab-save', message, draft: opts?.draft === true }));
  }

  /** 本地是否仍有未同步到服务端的变更 (断线缓冲期间为 true) */
  hasPendingChanges(): boolean {
    return this.provider ? this.provider.hasUnsyncedChanges : false;
  }

  /** 开始/停止跟随指定参与者 (clientID); null 表示停止跟随 */
  follow(clientID: string | null): void {
    const awareness = this.provider?.awareness;
    if (!awareness) return;
    this.followTarget = clientID;
    this.lastAppliedAnchor = null;
    awareness.setLocalStateField('follow', clientID == null ? null : { target: Number(clientID) });
    // 立即同步一次目标视口, 避免等待其下一次滚动
    if (clientID != null) this.applyTargetViewport(awareness, clientID);
    this.emitParticipants();
  }

  /** 发起/结束"跟我来" (spotlight): 网关校验写权限并全员广播 */
  setSpotlight(on: boolean): void {
    this.provider?.sendStateless(JSON.stringify({ type: 'collab-spotlight', on }));
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
    let msg: {
      type?: string;
      docKey?: string;
      error?: string;
      on?: boolean;
      from?: { user_id?: string; username?: string };
    };
    try {
      msg = JSON.parse(payload);
    } catch {
      return;
    }
    if (msg.docKey !== this.opts.docKey) return;
    if (msg.type === 'collab-saved') {
      this.opts.onSaved?.(msg as unknown as CollabSavedMsg);
    } else if (msg.type === 'collab-save-error') {
      this.opts.onError?.(msg.error || '保存失败');
    } else if (msg.type === 'collab-spotlight-error') {
      this.opts.onError?.(msg.error || '无法发起跟随');
    } else if (msg.type === 'collab-spotlight') {
      this.handleSpotlight(!!msg.on, msg.from?.user_id);
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

  private applyTargetViewport(awareness: NonNullable<HocuspocusProvider['awareness']>, targetId: string): void {
    const state = awareness.getStates().get(Number(targetId));
    const viewport = state?.viewport as { anchor?: number } | undefined;
    if (viewport?.anchor != null && viewport.anchor !== this.lastAppliedAnchor) {
      this.lastAppliedAnchor = viewport.anchor;
      this.scrollToAnchor(viewport.anchor);
    }
  }

  private scrollToAnchor(anchor: number): void {
    const view = this.view;
    if (!view) return;
    const pos = Math.max(0, Math.min(anchor, view.state.doc.length));
    const block = view.lineBlockAt(pos);
    view.scrollDOM.scrollTo({ top: block.top, behavior: 'smooth' });
  }

  /** 有跟随者时按需广播本地视口位置 (节流) */
  private scheduleViewportBroadcast(): void {
    if (this.viewportTimer != null) return;
    this.viewportTimer = setTimeout(() => {
      this.viewportTimer = null;
      const view = this.view;
      const awareness = this.provider?.awareness;
      if (!view || !awareness) return;
      const block = view.lineBlockAtHeight(view.scrollDOM.scrollTop);
      // 视口未变则不重复广播, 避免 awareness 更新自触发循环
      if (block.from === this.lastBroadcastAnchor) return;
      this.lastBroadcastAnchor = block.from;
      awareness.setLocalStateField('viewport', { anchor: block.from });
    }, VIEWPORT_THROTTLE_MS);
  }

  private emitFollow(peers: CollabParticipant[]): void {
    const followingName = this.followTarget
      ? peers.find((p) => p.clientID === this.followTarget)?.username ?? null
      : null;
    this.opts.onFollowChange?.({
      following: this.followTarget,
      followingName,
      followers: [...this.followers],
      spotlightOn: this.spotlightOn,
    });
  }

  private emitParticipants(): void {
    const awareness = this.provider?.awareness;
    if (!awareness) {
      this.opts.onParticipants?.([]);
      this.emitFollow([]);
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
    let targetAnchor: number | null = null;
    for (const [clientID, state] of awareness.getStates()) {
      const id = String(clientID);
      const user = state.user as { name?: string; user_id?: string } | undefined;
      const follow = state.follow as { target?: number | null } | undefined;
      const viewport = state.viewport as { anchor?: number } | undefined;
      const following = follow?.target != null ? String(follow.target) : null;
      peers.push({
        clientID: id,
        user_id: user?.user_id ?? '',
        username: user?.name ?? '',
        cursor: null,
        following,
        isSelf: id === myId,
      });
      if (following != null && following === myId) followers.add(id);
      if (id === this.followTarget && viewport?.anchor != null) targetAnchor = viewport.anchor;
    }
    this.followers = followers;

    this.opts.onParticipants?.(peers);
    this.emitFollow(peers);

    if (this.followTarget && targetAnchor != null && targetAnchor !== this.lastAppliedAnchor) {
      this.lastAppliedAnchor = targetAnchor;
      this.scrollToAnchor(targetAnchor);
    }
    // 存在跟随者时推送本地视口, 让其初次跟随即对齐当前位置
    if (followers.size > 0) this.scheduleViewportBroadcast();
  }
}
