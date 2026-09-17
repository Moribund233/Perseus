"""F-203 Business Events Push — broadcast business events to room subscribers"""
import asyncio
import uuid
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from api.websocket.manager import ConnectionManager
from services.search_service import SearchService
import logging

logger = logging.getLogger(__name__)


def _get_manager() -> ConnectionManager:
    return ConnectionManager()


async def broadcast_event(
    room_id: uuid.UUID,
    event_type: str,
    event_data: Dict[str, Any],
    exclude_user_id: Optional[uuid.UUID] = None,
) -> int:
    """Generic event broadcast to a room"""
    mgr = _get_manager()
    payload = {
        "type": "event",
        "event": event_type,
        "room_id": room_id,
        "data": event_data,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    count = await mgr.send_to_room(room_id, payload, exclude_user_id=exclude_user_id)
    logger.info("Event broadcast room=%s event=%s recipients=%d", room_id, event_type, count)
    return count


async def broadcast_pr_opened(
    room_id: uuid.UUID,
    pr_id: uuid.UUID,
    title: str,
    opener_id: uuid.UUID,
    opener_username: str,
) -> int:
    """Broadcast PR opened event"""
    return await broadcast_event(room_id, "pr_opened", {
        "pr_id": pr_id,
        "title": title,
        "opener": {"id": opener_id, "username": opener_username},
    }, exclude_user_id=opener_id)


async def broadcast_pr_merged(
    room_id: uuid.UUID,
    pr_id: uuid.UUID,
    title: str,
    merger_id: uuid.UUID,
    merger_username: str,
) -> int:
    """Broadcast PR merged event"""
    return await broadcast_event(room_id, "pr_merged", {
        "pr_id": pr_id,
        "title": title,
        "merger": {"id": merger_id, "username": merger_username},
    }, exclude_user_id=merger_id)


async def broadcast_issue_created(
    room_id: uuid.UUID,
    issue_id: uuid.UUID,
    title: str,
    creator_id: uuid.UUID,
    creator_username: str,
) -> int:
    """Broadcast issue created event"""
    return await broadcast_event(room_id, "issue_created", {
        "issue_id": issue_id,
        "title": title,
        "creator": {"id": creator_id, "username": creator_username},
    }, exclude_user_id=creator_id)


async def broadcast_pr_closed(
    room_id: uuid.UUID,
    pr_id: uuid.UUID,
    title: str,
    closer_id: uuid.UUID,
    closer_username: str,
) -> int:
    """Broadcast PR closed event"""
    return await broadcast_event(room_id, "pr_closed", {
        "pr_id": pr_id,
        "title": title,
        "closer": {"id": closer_id, "username": closer_username},
    }, exclude_user_id=closer_id)


async def broadcast_pr_reopened(
    room_id: uuid.UUID,
    pr_id: uuid.UUID,
    title: str,
    reopens_id: uuid.UUID,
    reopens_username: str,
) -> int:
    """Broadcast PR reopened event"""
    return await broadcast_event(room_id, "pr_reopened", {
        "pr_id": pr_id,
        "title": title,
        "reopens": {"id": reopens_id, "username": reopens_username},
    }, exclude_user_id=reopens_id)


async def broadcast_pr_comment_added(
    room_id: uuid.UUID,
    pr_id: uuid.UUID,
    comment_id: uuid.UUID,
    commenter_id: uuid.UUID,
    commenter_username: str,
    content: str,
) -> int:
    """Broadcast PR comment added event"""
    return await broadcast_event(room_id, "pr_comment_added", {
        "pr_id": pr_id,
        "comment_id": comment_id,
        "commenter": {"id": commenter_id, "username": commenter_username},
        "content": content[:500],
    }, exclude_user_id=commenter_id)


async def broadcast_pr_review_submitted(
    room_id: uuid.UUID,
    pr_id: uuid.UUID,
    review_id: uuid.UUID,
    reviewer_id: uuid.UUID,
    reviewer_username: str,
    state: str,
) -> int:
    """Broadcast PR review submitted event"""
    return await broadcast_event(room_id, "pr_review_submitted", {
        "pr_id": pr_id,
        "review_id": review_id,
        "reviewer": {"id": reviewer_id, "username": reviewer_username},
        "state": state,
    }, exclude_user_id=reviewer_id)


async def broadcast_push(
    room_id: uuid.UUID,
    branch: str,
    commit_count: int,
    pusher_id: uuid.UUID,
    pusher_username: str,
    repo_path: Optional[str] = None,
    db=None,
    commit_sha: Optional[str] = None,
    commit_message: Optional[str] = None,
    old_sha: Optional[str] = None,
) -> int:
    """Broadcast push event — also triggers search index update and pending build creation"""
    result = await broadcast_event(room_id, "push", {
        "branch": branch,
        "commit_count": commit_count,
        "pusher": {"id": pusher_id, "username": pusher_username},
    }, exclude_user_id=pusher_id)

    if repo_path:
        try:
            # 有 old_sha 时按 diff 只增量重索引变更文件; 无法计算 diff 时回退全量重建。
            # 索引为 CPU/IO 密集操作, 一律放线程池避免阻塞事件循环 (F-039)。
            changed = None
            if old_sha and commit_sha:
                changed = SearchService.diff_changed_files(repo_path, old_sha, commit_sha)
            if changed is not None:
                await asyncio.to_thread(SearchService.update_files, repo_path, changed)
            else:
                await asyncio.to_thread(SearchService.rebuild_index, repo_path)
        except Exception as e:
            logger.warning("Search index update failed: %s", e)

    # push 触发生成 pending build (F-046): 按 (repo, branch, commit) 去重, 避免与 PR merge 重复
    if db is not None and commit_sha:
        build = await _create_build_for_push(
            db=db,
            room_id=room_id,
            branch=branch,
            commit_sha=commit_sha,
            commit_message=commit_message,
            pusher_id=pusher_id,
        )
        if build is not None:
            result += await broadcast_event(room_id, "build", {
                "build_id": str(build.id),
                "repo_id": str(build.repo_id),
                "branch": build.branch,
                "commit_sha": build.commit_sha,
                "status": build.status,
            }, exclude_user_id=pusher_id)

    return result


async def _create_build_for_push(
    db,
    room_id: uuid.UUID,
    branch: str,
    commit_sha: str,
    commit_message: Optional[str],
    pusher_id: uuid.UUID,
):
    """将 push 解析到仓库并去重建 build; room 不存在时静默跳过"""
    from services.realtime.room_service import RoomService
    from services.build_service import BuildService

    room = await RoomService.get_room(db, room_id)
    if not room:
        logger.warning("Push build skipped: room %s not found", room_id)
        return None

    return await BuildService.ensure_build_for_commit(
        db=db,
        repo_id=room.repository_id,
        branch=branch,
        commit_sha=commit_sha,
        triggered_by=pusher_id,
        commit_message=commit_message,
    )
