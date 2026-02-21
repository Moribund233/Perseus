"""
WebHook 触发工具

在各个服务层中调用，用于触发 WebHook 事件
"""
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from services import webhook_service


async def trigger_push_event(
    db: AsyncSession,
    repository_id: int,
    ref: str,
    before: str,
    after: str,
    commits: list,
    pusher: Dict[str, Any]
) -> None:
    """
    触发 Push 事件

    Args:
        db: 异步数据库会话
        repository_id: 仓库ID
        ref: 分支或标签引用（如 refs/heads/main）
        before: 推送前的 commit hash
        after: 推送后的 commit hash
        commits: 提交列表
        pusher: 推送者信息
    """
    payload = {
        "ref": ref,
        "before": before,
        "after": after,
        "commits": commits,
        "pusher": pusher,
        "repository": await _get_repository_info(db, repository_id)
    }

    await webhook_service.trigger_webhooks(db, repository_id, "push", payload)


async def tag_push_event(
    db: AsyncSession,
    repository_id: int,
    ref: str,
    after: str,
    pusher: Dict[str, Any]
) -> None:
    """
    触发 Tag Push 事件

    Args:
        db: 异步数据库会话
        repository_id: 仓库ID
        ref: 标签引用（如 refs/tags/v1.0.0）
        after: 标签指向的 commit hash
        pusher: 推送者信息
    """
    payload = {
        "ref": ref,
        "after": after,
        "pusher": pusher,
        "repository": await _get_repository_info(db, repository_id)
    }

    await webhook_service.trigger_webhooks(db, repository_id, "tag_push", payload)


async def trigger_pull_request_event(
    db: AsyncSession,
    repository_id: int,
    event: str,  # opened, updated, merged, closed, reopened
    pull_request: Dict[str, Any],
    sender: Dict[str, Any]
) -> None:
    """
    触发 Pull Request 事件

    Args:
        db: 异步数据库会话
        repository_id: 仓库ID
        event: 事件类型
        pull_request: PR 信息
        sender: 触发者信息
    """
    payload = {
        "action": event,
        "number": pull_request.get("number"),
        "pull_request": pull_request,
        "sender": sender,
        "repository": await _get_repository_info(db, repository_id)
    }

    await webhook_service.trigger_webhooks(
        db, repository_id, f"pull_request.{event}", payload
    )


async def trigger_release_event(
    db: AsyncSession,
    repository_id: int,
    event: str,  # created, published, updated, deleted
    release: Dict[str, Any],
    sender: Dict[str, Any]
) -> None:
    """
    触发 Release 事件

    Args:
        db: 异步数据库会话
        repository_id: 仓库ID
        event: 事件类型
        release: Release 信息
        sender: 触发者信息
    """
    payload = {
        "action": event,
        "release": release,
        "sender": sender,
        "repository": await _get_repository_info(db, repository_id)
    }

    await webhook_service.trigger_webhooks(
        db, repository_id, f"release.{event}", payload
    )


async def trigger_issue_event(
    db: AsyncSession,
    repository_id: int,
    event: str,  # opened, closed, reopened, updated
    issue: Dict[str, Any],
    sender: Dict[str, Any]
) -> None:
    """
    触发 Issue 事件

    Args:
        db: 异步数据库会话
        repository_id: 仓库ID
        event: 事件类型
        issue: Issue 信息
        sender: 触发者信息
    """
    payload = {
        "action": event,
        "issue": issue,
        "sender": sender,
        "repository": await _get_repository_info(db, repository_id)
    }

    await webhook_service.trigger_webhooks(
        db, repository_id, f"issue.{event}", payload
    )


async def trigger_repository_event(
    db: AsyncSession,
    repository_id: int,
    event: str,  # created, deleted, forked
    repository: Dict[str, Any],
    sender: Dict[str, Any]
) -> None:
    """
    触发 Repository 事件

    Args:
        db: 异步数据库会话
        repository_id: 仓库ID
        event: 事件类型
        repository: 仓库信息
        sender: 触发者信息
    """
    payload = {
        "action": event,
        "repository": repository,
        "sender": sender
    }

    await webhook_service.trigger_webhooks(
        db, repository_id, f"repository.{event}", payload
    )


async def _get_repository_info(
    db: AsyncSession,
    repository_id: int
) -> Dict[str, Any]:
    """
    获取仓库基本信息

    Args:
        db: 异步数据库会话
        repository_id: 仓库ID

    Returns:
        dict: 仓库信息
    """
    from sqlalchemy import select
    from models import Repository, User

    stmt = select(Repository).filter(Repository.id == repository_id)
    result = await db.execute(stmt)
    repo = result.scalar_one_or_none()

    if not repo:
        return {"id": repository_id}

    # 获取所有者信息
    owner_info = {}
    if repo.owner_id:
        user_stmt = select(User).filter(User.id == repo.owner_id)
        user_result = await db.execute(user_stmt)
        owner = user_result.scalar_one_or_none()
        if owner:
            owner_info = {
                "id": owner.id,
                "username": owner.username
            }

    return {
        "id": repo.id,
        "name": repo.name,
        "path": repo.path,
        "description": repo.description,
        "is_public": repo.is_public,
        "owner": owner_info,
        "created_at": repo.created_at.isoformat() if repo.created_at else None
    }


# 便捷函数：从模型对象构建 sender 信息
def build_sender_info(user) -> Dict[str, Any]:
    """
    构建 sender 信息

    Args:
        user: User 模型实例

    Returns:
        dict: 发送者信息
    """
    if not user:
        return {}

    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name
    }


# 便捷函数：从模型对象构建 PR 信息
def build_pr_info(pr) -> Dict[str, Any]:
    """
    构建 Pull Request 信息

    Args:
        pr: PullRequest 模型实例

    Returns:
        dict: PR 信息
    """
    return {
        "id": pr.id,
        "number": pr.pr_number,
        "title": pr.title,
        "description": pr.description,
        "source_branch": pr.source_branch,
        "target_branch": pr.target_branch,
        "status": pr.status,
        "author": build_sender_info(pr.author) if pr.author else None,
        "created_at": pr.created_at.isoformat() if pr.created_at else None,
        "updated_at": pr.updated_at.isoformat() if pr.updated_at else None
    }


# 便捷函数：从模型对象构建 Release 信息
def build_release_info(release) -> Dict[str, Any]:
    """
    构建 Release 信息

    Args:
        release: Release 模型实例

    Returns:
        dict: Release 信息
    """
    return {
        "id": release.id,
        "release_number": release.release_number,
        "tag_name": release.tag_name,
        "name": release.name,
        "description": release.description,
        "commit_hash": release.commit_hash,
        "is_draft": release.is_draft,
        "is_prerelease": release.is_prerelease,
        "author": build_sender_info(release.author) if release.author else None,
        "created_at": release.created_at.isoformat() if release.created_at else None
    }


# 便捷函数：从模型对象构建 Issue 信息
def build_issue_info(issue) -> Dict[str, Any]:
    """
    构建 Issue 信息

    Args:
        issue: Issue 模型实例

    Returns:
        dict: Issue 信息
    """
    return {
        "id": issue.id,
        "issue_number": issue.issue_number,
        "title": issue.title,
        "description": issue.description,
        "status": issue.status,
        "author": build_sender_info(issue.author) if issue.author else None,
        "created_at": issue.created_at.isoformat() if issue.created_at else None,
        "updated_at": issue.updated_at.isoformat() if issue.updated_at else None
    }
