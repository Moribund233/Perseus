/**
 * 会话 TTL 延迟销毁扩展 (collab-f204-vs-cwm 3.2 中期方案)
 *
 * 最后一名协作者离开后, 不立即卸载内存中的 Y.Doc, 而是保留至多 ttlMs:
 *   - 窗口内有人重新 join → 直接复用内存 Y.Doc, 现场(未保存编辑/光标)不丢,
 *     也无需再从 Git 重新加载播种。
 *   - 窗口内无人回来 → 到期调用 unloadDocument, 释放内存;
 *     下次 join 由 onLoadDocument 重新从 app 播种。
 *
 * 落地方式 (Hocuspocus v4 无内建 TTL):
 *   - onDisconnect 且连接数归零 → 登记 "保留" 并启动 TTL 定时器;
 *   - 包装 instance.shouldUnloadDocument: 内置卸载路径(断开/unloadImmediately)
 *     在保留窗口内一律拒绝, 改由 TTL 到期自行卸载;
 *   - onConnect → 取消保留 (有人回来, 复用现场)。
 *
 * 注意: Server.destroy() 会等待所有文档卸载后才触发 onDestroy, 因此关闭前必须
 * 调用 releaseAll() 解除保留, 否则进程无法退出 (见 startGateway().close)。
 */

export const DEFAULT_SESSION_TTL_MS = 10 * 60 * 1000;

/**
 * @param {object} [options]
 * @param {number} [options.ttlMs]  保留时长 (<=0 表示禁用, 恢复 "断开即卸载")
 * @param {(msg: string) => void} [options.log]
 * @param {() => number} [options.now]
 * @param {typeof setTimeout} [options.setTimer]
 * @param {typeof clearTimeout} [options.clearTimer]
 */
export function createSessionTtlExtension({
  ttlMs = DEFAULT_SESSION_TTL_MS,
  log = () => {},
  now = Date.now,
  setTimer = setTimeout,
  clearTimer = clearTimeout,
} = {}) {
  /** documentName -> { document, timer, emptySince } */
  const holds = new Map();
  let instance = null;
  let released = false;

  function cancel(documentName) {
    const hold = holds.get(documentName);
    if (!hold) return;
    if (hold.timer) clearTimer(hold.timer);
    holds.delete(documentName);
    log(`session resumed doc=${documentName} after ${now() - hold.emptySince}ms (warm doc reused)`);
  }

  function tryUnload(documentName, document, { force = false } = {}) {
    if (!force && released) return;
    // 先解除保留, 再走内置卸载 (否则 shouldUnloadDocument 仍拒绝)
    holds.delete(documentName);
    if (document.getConnectionsCount() > 0) return; // 恰好有人回来, 交给 onConnect 处理
    if (!force && !instance?.shouldUnloadDocument(document)) {
      schedule(documentName, document); // 仍有 debounce 中的落盘工作, 稍后重试
      return;
    }
    log(`session doc=${documentName} unloading${force ? " (shutdown)" : " (TTL expired)"}`);
    Promise.resolve(instance.unloadDocument(document)).catch((err) =>
      log(`unload failed doc=${documentName}: ${err?.message ?? err}`)
    );
  }

  function schedule(documentName, document) {
    if (released || ttlMs <= 0) return;
    let hold = holds.get(documentName);
    if (!hold) {
      hold = { document, timer: null, emptySince: now() };
      holds.set(documentName, hold);
    }
    if (hold.timer) return;
    hold.document = document;
    hold.timer = setTimer(() => {
      hold.timer = null;
      tryUnload(documentName, document, { force: false });
    }, ttlMs);
    hold.timer?.unref?.();
    log(`session empty doc=${documentName}, holding up to ${ttlMs}ms`);
  }

  return {
    async onConfigure({ instance: hocuspocus }) {
      instance = hocuspocus;
      const original = hocuspocus.shouldUnloadDocument.bind(hocuspocus);
      hocuspocus.shouldUnloadDocument = (document) => {
        if (original(document) === false) return false;
        if (holds.has(document.name)) {
          schedule(document.name, document); // 内置卸载被拦截, 兜底确保定时器存在
          return false;
        }
        return true;
      };
    },

    async onConnect({ documentName }) {
      cancel(documentName);
    },

    async onDisconnect({ document, documentName }) {
      if (document.getConnectionsCount() === 0) schedule(documentName, document);
    },

    async onDestroy() {
      released = true;
      for (const hold of holds.values()) if (hold.timer) clearTimer(hold.timer);
      holds.clear();
    },

    /** 关闭前解除全部保留并卸载无人持有的文档, 让 Server.destroy() 能正常退出 */
    releaseAll() {
      released = true;
      const held = [...holds.entries()];
      for (const hold of holds.values()) if (hold.timer) clearTimer(hold.timer);
      holds.clear();
      // 未被任何连接持有且仅靠 TTL 保留的文档: 此刻主动卸载, 否则 destroy() 会挂起
      for (const [documentName, hold] of held) {
        if (hold.document) tryUnload(documentName, hold.document, { force: true });
      }
    },

    /** 保留中的文档名 (诊断/测试) */
    heldDocuments() {
      return [...holds.keys()];
    },
  };
}
