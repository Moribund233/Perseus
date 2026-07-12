"""F-203 Business Events Push — broadcast business events to room subscribers"""
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from api.websocket.manager import ConnectionManager
from services.search_service import SearchService
import logging

logger = logging.getLogger(__name__)


def _get_manager() -> ConnectionManager:
    return ConnectionManager()


async def broadcast_event(
    room_id: int,
    event_type: str,
    event_data: Dict[str, Any],
    exclude_user_id: Optional[int] = None,
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
    room_id: int,
    pr_id: int,
    title: str,
    opener_id: int,
    opener_username: str,
) -> int:
    """Broadcast PR opened event"""
    return await broadcast_event(room_id, "pr_opened", {
        "pr_id": pr_id,
        "title": title,
        "opener": {"id": opener_id, "username": opener_username},
    }, exclude_user_id=opener_id)


async def broadcast_pr_merged(
    room_id: int,
    pr_id: int,
    title: str,
    merger_id: int,
    merger_username: str,
) -> int:
    """Broadcast PR merged event"""
    return await broadcast_event(room_id, "pr_merged", {
        "pr_id": pr_id,
        "title": title,
        "merger": {"id": merger_id, "username": merger_username},
    }, exclude_user_id=merger_id)


async def broadcast_issue_created(
    room_id: int,
    issue_id: int,
    title: str,
    creator_id: int,
    creator_username: str,
) -> int:
    """Broadcast issue created event"""
    return await broadcast_event(room_id, "issue_created", {
        "issue_id": issue_id,
        "title": title,
        "creator": {"id": creator_id, "username": creator_username},
    }, exclude_user_id=creator_id)


async def broadcast_pr_closed(
    room_id: int,
    pr_id: int,
    title: str,
    closer_id: int,
    closer_username: str,
) -> int:
    """Broadcast PR closed event"""
    return await broadcast_event(room_id, "pr_closed", {
        "pr_id": pr_id,
        "title": title,
        "closer": {"id": closer_id, "username": closer_username},
    }, exclude_user_id=closer_id)


async def broadcast_pr_reopened(
    room_id: int,
    pr_id: int,
    title: str,
    reopens_id: int,
    reopens_username: str,
) -> int:
    """Broadcast PR reopened event"""
    return await broadcast_event(room_id, "pr_reopened", {
        "pr_id": pr_id,
        "title": title,
        "reopens": {"id": reopens_id, "username": reopens_username},
    }, exclude_user_id=reopens_id)


async def broadcast_pr_comment_added(
    room_id: int,
    pr_id: int,
    comment_id: int,
    commenter_id: int,
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
    room_id: int,
    pr_id: int,
    review_id: int,
    reviewer_id: int,
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
    room_id: int,
    branch: str,
    commit_count: int,
    pusher_id: int,
    pusher_username: str,
    repo_path: Optional[str] = None,
) -> int:
    """Broadcast push event — also triggers search index rebuild"""
    result = await broadcast_event(room_id, "push", {
        "branch": branch,
        "commit_count": commit_count,
        "pusher": {"id": pusher_id, "username": pusher_username},
    }, exclude_user_id=pusher_id)

    if repo_path:
        try:
            SearchService.rebuild_index(repo_path)
        except Exception as e:
            logger.warning("Search index rebuild failed: %s", e)

    return result
