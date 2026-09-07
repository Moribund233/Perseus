"""
F-204 协作文本编辑 WebSocket 消息处理

专用端点 /ws/collab (见 api/websocket/router.py), 协议:

    C->S  collab_join   {repository_id, branch, path, clientID}
    S->C  collab_init   {docKey, doc, version, participants}
    S->C  collab_peer_joined {docKey, clientID, user_id, username}

    C->S  collab_push   {docKey, version, changes, clientID}
    S->C  collab_update {docKey, changes[], clientID, version}  (全员广播, 含发送者:
                          发送者按 clientID 识别自身更新并确认版本; changes 为
                          ChangeSet JSON 数组, 每项占一个版本号)
    S->C  collab_reject {docKey, version, changes, resync}      (版本落后时, changes 为
                          错过的日志条目 [{changes, clientID}], 客户端 rebase 后重发)

    C->S  collab_pull   {docKey, version}
    S->C  collab_update {docKey, changes[], clientID: null, version} | collab_resync
                          (pull 响应的 changes 与 push 广播同构, 为 ChangeSet JSON 数组)

    C->S  collab_cursor {docKey, anchor, head}
    S->C  collab_cursor {docKey, clientID, user_id, anchor, head}

    C->S  collab_save   {docKey, message}
    S->C  collab_save_ack {docKey, commit_id, ...}  (提交者回执)
    S->C  collab_saved   {docKey, commit_id, ...}  (其他协作者)

    C->S  collab_leave  {docKey}
    S->C  collab_peer_left   {docKey, user_id}

权限模型: join 时一次性校验读/写权限并缓存到会话参与者 (can_write),
push/save 直接查缓存; 仓库角色变更在重新 join 后生效。
"""
from typing import Any, Dict, List, Optional
from uuid import UUID

import logging

from api.websocket.manager import Connection, ConnectionManager
from core.exception import NotFoundException, ValidationException
from services.realtime.collab_service import (
    ChangeSetError,
    CollabStaleError,
    collab_service,
)

logger = logging.getLogger(__name__)

# 读权限角色 (浏览/加入会话)
READ_ROLES = ["owner", "admin", "developer", "viewer"]
# 写权限角色 (push 变更 / 保存提交)
WRITE_ROLES = ["owner", "admin", "developer"]


def _parse_uuid(value: Any) -> Optional[UUID]:
    if value is None:
        return None
    try:
        return value if isinstance(value, UUID) else UUID(str(value))
    except (ValueError, AttributeError, TypeError):
        return None


def _get_manager() -> ConnectionManager:
    return ConnectionManager()


async def _get_repo_path(repository_id: UUID) -> str:
    """解析仓库物理路径 (与 repository_browser_controller 保持一致)"""
    from sqlalchemy import select

    from models import Repository
    from models.async_db import get_async_db_context
    from utils.git_utils import get_repository_storage_path

    async with get_async_db_context() as db:
        result = await db.execute(select(Repository).filter(Repository.id == repository_id))
        repo = result.scalar_one_or_none()
        if not repo:
            raise NotFoundException(detail="Repository not found")
        return get_repository_storage_path(repo.path)


async def _check_permission(repository_id: UUID, user_id: UUID, roles: List[str]) -> bool:
    from utils.permission_utils import check_repository_permission

    from models.async_db import get_async_db_context

    async with get_async_db_context() as db:
        return await check_repository_permission(db, repository_id, user_id, roles)


def _session_participants(session) -> List[Dict[str, Any]]:
    """会话参与者快照 (含光标), 供 collab_init 使用"""
    users = []
    for participant in session.participants.values():
        users.append({
            "clientID": participant["clientID"],
            "user_id": str(participant["user_id"]),
            "username": participant["username"],
            "cursor": participant["cursor"],
        })
    return users


async def _require_session(connection: Connection, message: Dict[str, Any]):
    """校验认证 + 会话存在; 失败时向客户端发送 error 并返回 None"""
    doc_key = message.get("docKey")
    session = collab_service.get_session(doc_key or "")
    if session is None:
        await connection.send({
            "type": "error",
            "error": "协作会话不存在或已结束",
            "original_type": message.get("type"),
        })
        return None
    if connection.connection_id not in session.participants:
        await connection.send({
            "type": "error",
            "error": "尚未加入该协作会话",
            "original_type": message.get("type"),
        })
        return None
    return session


async def handle_collab_join(connection: Connection, message: Dict[str, Any]) -> None:
    user_id = connection.user_id
    if user_id is None:
        await connection.send({
            "type": "error", "error": "需要认证才能协作编辑",
            "original_type": "collab_join",
        })
        return

    repository_id = _parse_uuid(message.get("repository_id"))
    branch = str(message.get("branch") or "").strip()
    path = str(message.get("path") or "").strip().lstrip("/")
    client_id = str(message.get("clientID") or "").strip()

    if repository_id is None or not branch or not path or not client_id:
        await connection.send({
            "type": "error",
            "error": "缺少必要字段: repository_id, branch, path, clientID",
            "original_type": "collab_join",
        })
        return

    doc_key = collab_service.make_doc_key(str(repository_id), branch, path)
    mgr = _get_manager()

    try:
        # 读权限 (浏览/加入会话), 无论会话是否已存在
        if not await _check_permission(repository_id, user_id, READ_ROLES):
            await connection.send({
                "type": "error", "error": "没有该仓库的访问权限",
                "original_type": "collab_join",
            })
            return

        if collab_service.get_session(doc_key) is None:
            # 会话不存在: 从 Git 加载文件内容创建
            repo_path = await _get_repo_path(repository_id)
            from services.repository_browser_service import get_blob_content

            blob = await get_blob_content(repo_path, ref=branch, path=path)
            if blob.get("is_binary"):
                await connection.send({
                    "type": "error", "error": "不支持协作编辑二进制文件",
                    "original_type": "collab_join",
                })
                return

            await collab_service.create_session(
                doc_key, repository_id, branch, path, blob.get("content", "") or ""
            )

        # 写权限: join 时校验一次并缓存, push/save 不再逐次查库
        can_write = await _check_permission(repository_id, user_id, WRITE_ROLES)
        session = await collab_service.join(
            doc_key, connection.connection_id, client_id, user_id,
            connection.username or "", can_write=can_write,
        )
        if session is None:
            # 并发窗口内会话被销毁 (最后一人恰好离开), 让客户端重试
            await connection.send({
                "type": "error", "error": "协作会话不存在或已结束",
                "original_type": "collab_join",
            })
            return

        await connection.send({
            "type": "collab_init",
            "docKey": doc_key,
            "doc": session.text,
            "version": session.version,
            "participants": _session_participants(session),
        })

        await mgr.send_to_connection_list(
            [cid for cid in session.participants if cid != connection.connection_id],
            {
                "type": "collab_peer_joined",
                "docKey": doc_key,
                "clientID": client_id,
                "user_id": str(user_id),
                "username": connection.username,
            },
        )
        logger.info(f"协作会话加入 doc={doc_key} user={connection.username}")
    except (NotFoundException, ValidationException) as e:
        await connection.send({
            "type": "error", "error": str(e.detail), "original_type": "collab_join",
        })
    except Exception as e:
        logger.exception(f"collab_join 处理失败: {e}")
        await connection.send({
            "type": "error", "error": "加入协作会话失败", "original_type": "collab_join",
        })


async def handle_collab_push(connection: Connection, message: Dict[str, Any]) -> None:
    session = await _require_session(connection, message)
    if session is None:
        return

    doc_key = message.get("docKey")
    client_id = str(message.get("clientID") or "")
    version = message.get("version")
    changes = message.get("changes")
    # changes: 单个变更集或变更集数组 (客户端一次 push 多个本地未确认更新)
    if changes and isinstance(changes, list) and not isinstance(changes[0], list):
        changesets = [changes]
    elif isinstance(changes, list):
        changesets = changes
    else:
        changesets = None
    if not isinstance(version, int) or not changesets or any(
        not isinstance(cs, list) for cs in changesets
    ):
        await connection.send({
            "type": "error", "error": "缺少必要字段: version(int), changes(非空list)",
            "original_type": "collab_push",
        })
        return

    # 写权限 (join 时缓存的会话级权限, 角色变更重新 join 后生效)
    participant = session.participants.get(connection.connection_id)
    if participant is None or not participant.get("can_write"):
        await connection.send({
            "type": "error", "error": "没有该仓库的写入权限",
            "original_type": "collab_push",
        })
        return

    try:
        new_version = session.push(client_id, version, changesets)
    except CollabStaleError as e:
        # 版本落后: 返回错过的变更, 客户端 rebase 本地未确认变更后重发
        missed = session.missed_changes(version)
        await connection.send({
            "type": "collab_reject",
            "docKey": doc_key,
            "version": e.server_version,
            "changes": missed if missed is not None else [],
            "resync": missed is None,
        })
        return
    except ChangeSetError as e:
        await connection.send({
            "type": "error", "error": f"非法变更集: {e}", "original_type": "collab_push",
        })
        return

    # 广播给全部参与者 (含发送者): collab 扩展按 clientID 识别自身更新并推进版本
    mgr = _get_manager()
    await mgr.send_to_connection_list(
        list(session.participants.keys()),
        {
            "type": "collab_update",
            "docKey": doc_key,
            "changes": changesets,
            "clientID": client_id,
            "version": new_version,
        },
    )


async def handle_collab_pull(connection: Connection, message: Dict[str, Any]) -> None:
    session = await _require_session(connection, message)
    if session is None:
        return

    version = message.get("version")
    if not isinstance(version, int):
        await connection.send({
            "type": "error", "error": "缺少必要字段: version(int)",
            "original_type": "collab_pull",
        })
        return

    try:
        changes = session.pull(version)
    except CollabStaleError:
        await connection.send({
            "type": "collab_resync", "docKey": message.get("docKey"),
        })
        return

    if changes is None:
        await connection.send({
            "type": "collab_resync", "docKey": message.get("docKey"),
        })
        return

    # 与 push 广播同构: changes 为 ChangeSet JSON 数组
    await connection.send({
        "type": "collab_update",
        "docKey": message.get("docKey"),
        "changes": [entry["changes"] for entry in changes],
        "clientID": None,
        "version": session.version,
    })


async def handle_collab_cursor(connection: Connection, message: Dict[str, Any]) -> None:
    session = await _require_session(connection, message)
    if session is None:
        return

    anchor = message.get("anchor")
    head = message.get("head")
    version = message.get("version")
    if not isinstance(anchor, int) or not isinstance(head, int):
        return

    participant = session.participants.get(connection.connection_id)
    if participant is None:
        return
    session.set_cursor(connection.connection_id, anchor, head)

    mgr = _get_manager()
    await mgr.send_to_connection_list(
        [cid for cid in session.participants if cid != connection.connection_id],
        {
            "type": "collab_cursor",
            "docKey": message.get("docKey"),
            "clientID": participant["clientID"],
            "user_id": str(participant["user_id"]),
            "username": participant["username"],
            "anchor": anchor,
            "head": head,
            "version": version if isinstance(version, int) else None,
        },
    )


async def handle_collab_save(connection: Connection, message: Dict[str, Any]) -> None:
    """协作保存: 以服务端权威文本提交 Git commit, 全员广播结果"""
    session = await _require_session(connection, message)
    if session is None:
        return

    if connection.user_id is None:
        await connection.send({
            "type": "error", "error": "需要认证才能保存",
            "original_type": "collab_save",
        })
        return

    # 写权限 (join 时缓存的会话级权限)
    participant = session.participants.get(connection.connection_id)
    if participant is None or not participant.get("can_write"):
        await connection.send({
            "type": "error", "error": "没有该仓库的写入权限",
            "original_type": "collab_save",
        })
        return

    commit_message = str(message.get("message") or f"Update {session.path}").strip() or f"Update {session.path}"

    try:
        from sqlalchemy import select

        from models.async_db import get_async_db_context
        from models.user import User
        from services.repository_browser_service import commit_file

        async with get_async_db_context() as db:
            result = await db.execute(select(User).filter(User.id == connection.user_id))
            user = result.scalar_one_or_none()
        if user is None:
            await connection.send({
                "type": "error", "error": "用户不存在", "original_type": "collab_save",
            })
            return

        repo_path = await _get_repo_path(session.repository_id)
        commit = await commit_file(
            repo_path,
            session.branch,
            session.path,
            session.text,
            user.full_name or user.username,
            user.email,
            commit_message,
        )
    except (NotFoundException, ValidationException) as e:
        await connection.send({
            "type": "error", "error": str(e.detail), "original_type": "collab_save",
        })
        return
    except Exception as e:
        logger.exception(f"协作保存失败 doc={session.doc_key}: {e}")
        await connection.send({
            "type": "error", "error": "保存失败", "original_type": "collab_save",
        })
        return

    saved_msg = {
        "type": "collab_saved",
        "docKey": session.doc_key,
        "commit_id": str(commit.get("commit_id", "")),
        "path": session.path,
        "branch": session.branch,
        "saved_by": connection.username,
        "message": commit_message,
    }
    mgr = _get_manager()
    await connection.send({**saved_msg, "type": "collab_save_ack"})
    await mgr.send_to_connection_list(
        [cid for cid in session.participants if cid != connection.connection_id],
        saved_msg,
    )


async def handle_collab_leave(connection: Connection, message: Dict[str, Any]) -> None:
    doc_key = message.get("docKey")
    if not doc_key:
        return
    session, destroyed = await collab_service.leave(doc_key, connection.connection_id)
    if session is None or destroyed:
        return

    mgr = _get_manager()
    await mgr.send_to_connection_list(
        list(session.participants.keys()),
        {
            "type": "collab_peer_left",
            "docKey": doc_key,
            "user_id": str(connection.user_id) if connection.user_id else None,
        },
    )


async def cleanup_connection_docs(connection_id: str) -> None:
    """连接断开: 退出所有会话并广播 peer_left"""
    for session, doc_key, departed_user_id in collab_service.leave_all(connection_id):
        try:
            mgr = _get_manager()
            await mgr.send_to_connection_list(
                list(session.participants.keys()),
                {
                    "type": "collab_peer_left",
                    "docKey": doc_key,
                    "user_id": str(departed_user_id) if departed_user_id else None,
                },
            )
        except Exception as e:
            logger.warning(f"广播 peer_left 失败 doc={doc_key}: {e}")


# 消息类型分发 (专用端点直接调用, 不走通用 handler 注册)
COLLAB_HANDLERS = {
    "collab_join": handle_collab_join,
    "collab_push": handle_collab_push,
    "collab_pull": handle_collab_pull,
    "collab_cursor": handle_collab_cursor,
    "collab_save": handle_collab_save,
    "collab_leave": handle_collab_leave,
}


async def handle_collab_message(connection: Connection, message: Dict[str, Any]) -> None:
    msg_type = message.get("type")
    handler = COLLAB_HANDLERS.get(msg_type or "")
    if handler is None:
        await connection.send({
            "type": "error",
            "error": f"未知的协作消息类型: {msg_type}",
            "supported_types": list(COLLAB_HANDLERS.keys()),
        })
        return
    await handler(connection, message)
