"""
F-204 协作文本编辑服务

基于 CodeMirror 6 `@codemirror/collab` 的中心化 OT authority：

- 服务端为每个打开的文档维护权威会话: 权威文本 + 版本号 + 变更日志
- 客户端 push 的变更集必须基于服务端当前版本, 否则拒绝 (乐观并发控制):
  拒绝时返回客户端错过的变更, 客户端 (collab 扩展) 会将本地未确认变更
  rebase 到新版本之上后重发
- 被接受的变更集按序 apply 到权威文本, 因此 apply 只需处理与权威文本
  同基的 ChangeSet, 无需完整双端合并

会话生命周期:
- 首个协作者 join 时从 Git 文件内容创建
- 最后一个协作者离开时销毁 (内存态, 不持久化)

ChangeSet JSON 格式 (见 @codemirror/state ChangeSet.toJSON):
    数字 n          -> 未修改区段 (n 个字符)
    [n]             -> 删除 n 个字符
    [n, 行1, 行2..] -> 用若干行文本替换 n 个字符 (行间以 \n 连接)
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

logger = logging.getLogger(__name__)

# 单会话变更日志上限: 超过后过旧版本无法增量拉取, 需要重新 join 同步
MAX_LOG_ENTRIES = 5000
# 文档大小上限 (字符), 与 WS 消息上限配合防御异常输入
MAX_DOC_CHARS = 2_000_000


class ChangeSetError(ValueError):
    """客户端变更集 JSON 非法"""


def _validate_changeset(changeset: Any) -> None:
    """校验 ChangeSet JSON 结构, 非法时抛出 ChangeSetError"""
    if not isinstance(changeset, list):
        raise ChangeSetError("changes must be a list")
    for part in changeset:
        if isinstance(part, (int, float)):
            if part < 0:
                raise ChangeSetError("negative section length")
        elif isinstance(part, list):
            if not part or not isinstance(part[0], (int, float)) or part[0] < 0:
                raise ChangeSetError("invalid section part")
            for line in part[1:]:
                if not isinstance(line, str):
                    raise ChangeSetError("inserted lines must be strings")
        else:
            raise ChangeSetError("invalid section part")


def apply_changeset(text: str, changeset: List[Any]) -> str:
    """
    将 CM6 ChangeSet JSON 应用到纯文本 (行分隔符 \\n)

    仅用于与权威文本同基的变更集 (push 被接受时), 不做位置映射。
    所有解析错误统一抛出 ChangeSetError。
    """
    try:
        return _apply_changeset(text, changeset)
    except ChangeSetError:
        raise
    except (ValueError, TypeError, IndexError) as e:
        raise ChangeSetError(f"malformed changeset: {e}") from e


def _apply_changeset(text: str, changeset: List[Any]) -> str:
    _validate_changeset(changeset)

    out: List[str] = []
    pos = 0
    text_len = len(text)

    for part in changeset:
        if isinstance(part, (int, float)):
            n = int(part)
            if pos + n > text_len:
                raise ChangeSetError("section beyond end of document")
            out.append(text[pos:pos + n])
            pos += n
        else:
            n = int(part[0])
            ins = "\n".join(part[1:])
            if pos + n > text_len:
                raise ChangeSetError("section beyond end of document")
            pos += n
            out.append(ins)

    out.append(text[pos:])
    return "".join(out)


def changeset_inserted_length(changeset: List[Any]) -> int:
    """变更集净变化字符数 (接受前用于容量校验)"""
    total = 0
    for part in changeset:
        if isinstance(part, (int, float)):
            total -= int(part)
        else:
            total -= int(part[0])
            total += len("\n".join(part[1:]))
    return total


class CollabSession:
    """
    单个文档的协作会话 (权威端状态)

    变更日志第 i 项 (0 起) 将文档从版本 i 变为版本 i+1。
    """

    def __init__(self, doc_key: str, repository_id: UUID, branch: str, path: str, text: str):
        self.doc_key = doc_key
        self.repository_id = repository_id
        self.branch = branch
        self.path = path
        self.text = text
        self.version = 0
        # log[i] 将文档从版本 (log_base + i) 变为 (log_base + i + 1)
        self.log: List[Dict[str, Any]] = []
        self.log_base = 0
        # connection_id -> 参与者信息
        self.participants: Dict[str, Dict[str, Any]] = {}

    @property
    def is_empty(self) -> bool:
        return not self.participants

    def missed_changes(self, version: int) -> List[Dict[str, Any]]:
        """version..当前版本 之间的变更 (客户端缺失的部分); 超出日志窗口返回 None"""
        if version < self.log_base:
            return None
        return self.log[version - self.log_base:]

    def push(self, client_id: str, version: int, changesets: List[List[Any]]) -> int:
        """
        接受一批基于 version 的顺序变更集 (乐观并发: 仅 version == 当前版本时接受)

        客户端一次 push 可携带多个本地未确认变更集 (sendableUpdates),
        它们按序应用; 每个变更集占一个版本号。

        Returns:
            新版本号
        Raises:
            CollabStaleError: version != 当前版本, 需拒绝并让客户端补齐后重试
            ChangeSetError: 变更集非法或超出文档容量
        """
        if version != self.version:
            raise CollabStaleError(self.version)
        total_delta = sum(changeset_inserted_length(cs) for cs in changesets)
        if len(self.text) + total_delta > MAX_DOC_CHARS:
            raise ChangeSetError("document too large")

        for changeset in changesets:
            self.text = apply_changeset(self.text, changeset)
            self.log.append({"changes": changeset, "clientID": client_id})
            self.version += 1
        if len(self.log) > MAX_LOG_ENTRIES:
            # 环形截断: 客户端版本低于窗口起点时只能全量重同步
            drop = len(self.log) - MAX_LOG_ENTRIES
            self.log = self.log[drop:]
            self.log_base += drop
        return self.version

    def pull(self, version: int) -> Optional[List[Dict[str, Any]]]:
        """增量拉取; 版本过旧 (超出日志窗口) 返回 None 表示需要重同步"""
        if version < 0 or version > self.version:
            raise CollabStaleError(self.version)
        return self.missed_changes(version)

    def set_cursor(self, connection_id: str, anchor: int, head: int) -> None:
        participant = self.participants.get(connection_id)
        if participant:
            participant["cursor"] = {"anchor": anchor, "head": head}


class CollabStaleError(Exception):
    """客户端版本落后于服务端, push/pull 需要按当前版本重试"""

    def __init__(self, server_version: int):
        self.server_version = server_version
        super().__init__(f"stale version, server at {server_version}")


class CollabService:
    """
    协作会话注册表 (进程内单例)

    并发模型: 所有会话状态变更在事件循环内同步完成 (无 await 穿透临界区),
    注册表的创建/销毁用锁保护 (创建涉及异步 IO, 在 handler 中完成)。
    """

    def __init__(self):
        self._sessions: Dict[str, CollabSession] = {}
        self._lock = asyncio.Lock()

    @staticmethod
    def make_doc_key(repository_id: str, branch: str, path: str) -> str:
        """文档标识: 仓库:分支:路径"""
        return f"{repository_id}:{branch}:{path}"

    def get_session(self, doc_key: str) -> Optional[CollabSession]:
        return self._sessions.get(doc_key)

    async def create_session(
        self, doc_key: str, repository_id: UUID, branch: str, path: str, text: str
    ) -> CollabSession:
        """注册新会话; 已存在时返回现有会话 (避免并发 join 重复创建)"""
        async with self._lock:
            existing = self._sessions.get(doc_key)
            if existing:
                return existing
            session = CollabSession(doc_key, repository_id, branch, path, text)
            self._sessions[doc_key] = session
            return session

    async def drop_session(self, doc_key: str) -> None:
        async with self._lock:
            self._sessions.pop(doc_key, None)

    async def join(
        self,
        doc_key: str,
        connection_id: str,
        client_id: str,
        user_id: UUID,
        username: str,
        can_write: bool = False,
    ) -> Optional[CollabSession]:
        """
        参与者加入会话; 会话不存在返回 None

        can_write: join 时校验并缓存的写权限, push/save 直接查缓存,
        避免高频编辑下每次操作都查库 (角色变更在重新 join 后生效)
        """
        async with self._lock:
            session = self._sessions.get(doc_key)
            if session is None:
                return None
            session.participants[connection_id] = {
                "clientID": client_id,
                "user_id": user_id,
                "username": username,
                "cursor": None,
                "can_write": can_write,
            }
            return session

    async def leave(self, doc_key: str, connection_id: str) -> Tuple[Optional[CollabSession], bool]:
        """
        参与者离开会话

        Returns:
            (会话, 会话是否已被销毁)
        """
        async with self._lock:
            session = self._sessions.get(doc_key)
            if session is None:
                return None, False
            session.participants.pop(connection_id, None)
            if session.is_empty:
                self._sessions.pop(doc_key, None)
                return session, True
            return session, False

    def leave_all(self, connection_id: str) -> List[Tuple[CollabSession, str, Optional[UUID]]]:
        """
        连接断开时退出其加入的所有会话

        Returns:
            [(会话, doc_key, 离开者 user_id)] — 会话仍有其他参与者 (需要广播 peer_left) 的部分
        """
        affected: List[Tuple[CollabSession, str, Optional[UUID]]] = []
        for doc_key, session in list(self._sessions.items()):
            if connection_id in session.participants:
                departed = session.participants.pop(connection_id)
                if session.is_empty:
                    self._sessions.pop(doc_key, None)
                else:
                    affected.append((session, doc_key, departed["user_id"]))
        return affected

    def stats(self) -> Dict[str, Any]:
        return {
            "active_sessions": len(self._sessions),
            "sessions": {
                key: {
                    "version": s.version,
                    "participants": len(s.participants),
                    "log_entries": len(s.log),
                }
                for key, s in self._sessions.items()
            },
        }


# 进程级单例
collab_service = CollabService()
