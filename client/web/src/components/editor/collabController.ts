import {
  collab,
  getSyncedVersion,
  receiveUpdates,
  sendableUpdates,
} from '@codemirror/collab';
import {
  ChangeSet,
  Compartment,
  StateEffect,
  StateField,
  Transaction,
} from '@codemirror/state';
import { Decoration, EditorView, WidgetType } from '@codemirror/view';
import type { DecorationSet } from '@codemirror/view';
import {
  collabSocket,
  type CollabParticipant,
  type CollabSavedMsg,
  type CollabSocketStatus,
} from '../../api/collabSocket';

/** 光标/选区配色 (与编辑器页面 avatarColors 保持一致) */
const PEER_COLORS = ['#1f6feb', '#3fb950', '#58a6ff', '#bc8cff', '#d29922', '#f85149', '#f0883e', '#7956d9'];

function peerColor(name: string): string {
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash);
  return PEER_COLORS[Math.abs(hash) % PEER_COLORS.length];
}

function generateClientID(): string {
  return `web-${Math.random().toString(36).slice(2, 10)}${Date.now().toString(36)}`;
}

// ==================== 远端光标/选区渲染 ====================

class RemoteCursorWidget extends WidgetType {
  private color: string;
  private name: string;

  constructor(color: string, name: string) {
    super();
    this.color = color;
    this.name = name;
  }

  eq(other: RemoteCursorWidget): boolean {
    return other.color === this.color && other.name === this.name;
  }

  toDOM(): HTMLElement {
    const wrap = document.createElement('span');
    wrap.style.cssText = 'position:relative; display:inline-block; width:0; height:0;';
    const caret = document.createElement('span');
    caret.style.cssText = `position:absolute; left:-1px; top:0; width:2px; height:1.15em; background:${this.color}; border-radius:1px;`;
    const label = document.createElement('span');
    label.textContent = this.name;
    label.style.cssText = `position:absolute; left:-1px; top:-1.05em; font-size:10px; line-height:1.3; padding:0 4px; border-radius:3px 3px 3px 0; color:#fff; background:${this.color}; white-space:nowrap; pointer-events:none; z-index:20;`;
    wrap.append(caret, label);
    return wrap;
  }

  ignoreEvent(): boolean {
    return true;
  }
}

const setRemoteDecorations = StateEffect.define<DecorationSet>();

const remoteCursorsField = StateField.define<DecorationSet>({
  create: () => Decoration.none,
  update(value, tr) {
    let next = tr.changes.empty ? value : value.map(tr.changes);
    for (const effect of tr.effects) {
      if (effect.is(setRemoteDecorations)) next = effect.value;
    }
    return next;
  },
  provide: (field) => EditorView.decorations.from(field),
});

// ==================== 协作控制器 ====================

export interface CollabControllerOptions {
  docKey: string;
  repositoryId: string;
  branch: string;
  path: string;
  onStatus?: (status: CollabSocketStatus) => void;
  onParticipants?: (peers: CollabParticipant[]) => void;
  onSaved?: (msg: CollabSavedMsg) => void;
  onError?: (error: string) => void;
}

interface PeerState {
  username: string;
  user_id: string;
  from: number;
  to: number;
}

/**
 * 单个文档的协作会话控制器
 *
 * - attach() 后加入服务端会话, collab 扩展经 Compartment 延迟装配
 *   (初始化文本以服务端权威内容为准)
 * - 同步: 定时 push 本地未确认变更 / pull 远端版本; push 版本过期时
 *   依据 collab_reject 中的缺失变更 rebase 后自动重发
 * - 光标: 本地选区变化上报 (附带同步版本号), 远端位置经服务端变更日志
 *   与本地未确认变更两级映射后渲染
 */
export class CollabController {
  readonly clientID = generateClientID();

  private opts: CollabControllerOptions;
  private view: EditorView | null = null;
  private compartment: Compartment | null = null;
  private joined = false;
  private pushTimer: ReturnType<typeof setInterval> | null = null;
  private pendingCursor: { anchor: number; head: number } | null = null;
  private lastCursorSent = 0;
  /** 已应用的远端变更 (fromVersion -> changeset), 用于远端光标位置映射 */
  private serverChanges: { fromVersion: number; changes: ChangeSet }[] = [];
  private peers = new Map<string, PeerState>();

  constructor(opts: CollabControllerOptions) {
    this.opts = opts;
  }

  get status(): CollabSocketStatus {
    return collabSocket.isConnected ? 'connected' : 'disconnected';
  }

  get isActive(): boolean {
    return this.joined && collabSocket.isConnected;
  }

  attach(view: EditorView, compartment: Compartment): void {
    this.view = view;
    this.compartment = compartment;

    collabSocket.setHandlers({
      onStatusChange: (status) => {
        if (status === 'disconnected') {
          // 断线后服务端已将本连接移出会话, 必须重置状态并在重连后重新 join,
          // 否则旧版本号的 push 会一直被拒 (会话可能已被服务端重建)
          this.joined = false;
          this.peers.clear();
          this.serverChanges = [];
          this.emitDecorations();
        }
        if (status === 'connected' && !this.joined) this.join();
        this.opts.onStatus?.(status);
      },
      onInit: (msg) => this.handleInit(msg),
      onUpdate: (msg) => this.handleUpdate(msg),
      onReject: (msg) => this.handleReject(msg),
      onCursor: (msg) => this.handleCursor(msg),
      onPeerJoined: (msg) => this.handlePeerJoined(msg),
      onPeerLeft: (msg) => this.handlePeerLeft(msg),
      onSaved: (msg) => {
        if (msg.docKey === this.docKey()) this.opts.onSaved?.(msg);
      },
      onResync: (docKey) => {
        if (docKey === this.docKey()) {
          this.joined = false;
          this.join();
        }
      },
      onError: (error) => this.opts.onError?.(error),
    });
    collabSocket.start();
    if (collabSocket.isConnected) this.join();

    this.pushTimer = setInterval(() => this.tick(), 250);
  }

  detach(): void {
    if (this.pushTimer) {
      clearInterval(this.pushTimer);
      this.pushTimer = null;
    }
    if (this.joined) collabSocket.leaveDoc(this.docKey());
    this.joined = false;
    this.view = null;
    this.compartment = null;
    this.peers.clear();
    this.serverChanges = [];
  }

  save(message: string): void {
    collabSocket.saveDoc(this.docKey(), message);
  }

  /** 本地是否仍有未确认 (未同步到服务端) 的变更 */
  hasPendingChanges(): boolean {
    return this.view ? sendableUpdates(this.view.state).length > 0 : false;
  }

  private docKey(): string {
    return this.opts.docKey;
  }

  private join(): void {
    collabSocket.joinDoc(this.docKey(), this.opts.repositoryId, this.opts.branch, this.opts.path, this.clientID);
  }

  /** 周期任务: 推送本地未确认变更 + 上报光标 */
  private tick(): void {
    const view = this.view;
    if (!view || !this.joined || !collabSocket.isConnected) return;

    const updates = sendableUpdates(view.state);
    if (updates.length > 0) {
      const version = getSyncedVersion(view.state);
      const changes = updates.map((u) => u.changes.toJSON());
      collabSocket.push(this.docKey(), version, changes, this.clientID);
    }

    const now = Date.now();
    if (this.pendingCursor && now - this.lastCursorSent >= 200) {
      const sel = view.state.selection.main;
      collabSocket.sendCursor(this.docKey(), sel.anchor, sel.head, getSyncedVersion(view.state));
      this.pendingCursor = null;
      this.lastCursorSent = now;
    }
  }

  private handleInit(msg: {
    docKey: string;
    doc: string;
    version: number;
    participants: CollabParticipant[];
  }): void {
    const view = this.view;
    if (msg.docKey !== this.docKey() || !view || !this.compartment) return;
    this.joined = true;

    // 装配 collab 扩展 (以服务端版本为起点)
    view.dispatch({
      effects: this.compartment.reconfigure([
        remoteCursorsField,
        collab({ startVersion: msg.version, clientID: this.clientID }),
        EditorView.updateListener.of((update) => this.onLocalUpdate(update)),
      ]),
    });

    // 以服务端权威文本为准 (标记 remote, 不计入本地未确认变更)
    const serverDoc = msg.doc;
    if (view.state.doc.toString() !== serverDoc) {
      view.dispatch({
        changes: { from: 0, to: view.state.doc.length, insert: serverDoc },
        annotations: [Transaction.remote.of(true)],
        filter: false,
      });
    }

    this.peers.clear();
    for (const p of msg.participants) {
      if (p.clientID === this.clientID) continue;
      this.peers.set(p.clientID, {
        username: p.username,
        user_id: p.user_id,
        from: p.cursor ? p.cursor.anchor : -1,
        to: p.cursor ? p.cursor.head : -1,
      });
    }
    this.emitDecorations();
    this.opts.onParticipants?.(msg.participants);
  }

  private handleUpdate(msg: {
    docKey: string;
    changes: unknown[][];
    clientID: string | null;
    version: number;
  }): void {
    const view = this.view;
    if (msg.docKey !== this.docKey() || !view) return;

    const fromVersion = msg.version - msg.changes.length;
    for (let i = 0; i < msg.changes.length; i++) {
      this.serverChanges.push({
        fromVersion: fromVersion + i,
        changes: ChangeSet.fromJSON(msg.changes[i]),
      });
    }
    if (this.serverChanges.length > 4000) {
      this.serverChanges = this.serverChanges.slice(-4000);
    }

    const updates = msg.changes.map((c) => ({
      changes: ChangeSet.fromJSON(c),
      clientID: msg.clientID ?? 'server',
    }));
    view.dispatch(receiveUpdates(view.state, updates));
  }

  private handleReject(msg: {
    docKey: string;
    version: number;
    changes: { changes: unknown[]; clientID: string }[];
    resync: boolean;
  }): void {
    const view = this.view;
    if (msg.docKey !== this.docKey() || !view) return;

    if (msg.resync) {
      this.joined = false;
      this.join();
      return;
    }

    // 应用缺失变更, collab 扩展自动 rebase 本地未确认变更; 下个 tick 重发
    const updates = msg.changes.map((c) => ({
      changes: ChangeSet.fromJSON(c.changes),
      clientID: c.clientID,
    }));
    view.dispatch(receiveUpdates(view.state, updates));
  }

  private handleCursor(msg: {
    docKey: string;
    clientID: string;
    user_id: string;
    username: string;
    anchor: number;
    head: number;
    version: number | null;
  }): void {
    if (msg.docKey !== this.docKey() || !this.view || msg.clientID === this.clientID) return;

    const base = msg.version ?? 0;
    this.peers.set(msg.clientID, {
      username: msg.username,
      user_id: msg.user_id,
      from: this.mapToCurrent(msg.anchor, base),
      to: this.mapToCurrent(msg.head, base),
    });
    this.emitDecorations();
  }

  private handlePeerJoined(msg: {
    docKey: string;
    clientID: string;
    user_id: string;
    username: string;
  }): void {
    if (msg.docKey !== this.docKey() || msg.clientID === this.clientID) return;
    this.peers.set(msg.clientID, { username: msg.username, user_id: msg.user_id, from: -1, to: -1 });
  }

  private handlePeerLeft(msg: { docKey: string; user_id: string | null }): void {
    if (msg.docKey !== this.docKey()) return;
    for (const [cid, peer] of this.peers) {
      if (peer.user_id === msg.user_id) this.peers.delete(cid);
    }
    this.emitDecorations();
  }

  /** 将发送端版本号下的位置映射到本地当前文档坐标 */
  private mapToCurrent(pos: number, senderVersion: number): number {
    let p = pos;
    for (const rec of this.serverChanges) {
      if (rec.fromVersion >= senderVersion) {
        const mapped = rec.changes.mapPos(p, 1);
        if (mapped < 0) return -1;
        p = mapped;
      }
    }
    if (this.view) {
      for (const update of sendableUpdates(this.view.state)) {
        const mapped = update.changes.mapPos(p, 1);
        if (mapped < 0) return -1;
        p = mapped;
      }
    }
    return p;
  }

  private onLocalUpdate(update: Parameters<Parameters<typeof EditorView.updateListener.of>[0]>[0]): void {
    if (update.selectionSet) {
      const sel = update.state.selection.main;
      this.pendingCursor = { anchor: sel.anchor, head: sel.head };
    }
  }

  private emitDecorations(): void {
    const view = this.view;
    if (!view) return;

    const ranges = [];
    for (const peer of this.peers.values()) {
      if (peer.from < 0) continue;
      const color = peerColor(peer.username);
      if (peer.to <= peer.from) {
        ranges.push(Decoration.widget({ widget: new RemoteCursorWidget(color, peer.username), side: 1 }).range(peer.from));
      } else {
        ranges.push(
          Decoration.mark({
            attributes: { style: `background:${color}33; box-shadow: inset 0 0 0 1px ${color}66; border-radius:2px;` },
          }).range(peer.from, peer.to),
        );
        ranges.push(Decoration.widget({ widget: new RemoteCursorWidget(color, peer.username), side: 1 }).range(peer.to));
      }
    }
    view.dispatch({ effects: setRemoteDecorations.of(Decoration.set(ranges, true)) });
  }
}
