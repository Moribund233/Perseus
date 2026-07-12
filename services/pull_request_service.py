"""
Pull Request 服务层

处理 Pull Request 相关的所有业务逻辑
"""
import os
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from sqlalchemy import select

from models import PullRequest, PRComment, PRReview, User
from core.exception import ValidationException, NotFoundException, AuthorizationException
from utils.permission_utils import check_resource_author_or_admin, check_repository_permission
from utils.response_builder import (
    build_pr_response,
    build_pr_comment_response,
    build_pr_review_response,
    build_pagination_response
)
from utils.db_utils import paginate, get_next_sequence_number, get_pull_request_or_404
from utils.git_utils import GitService
from services.realtime.event_service import (
    broadcast_pr_opened, broadcast_pr_merged, broadcast_pr_closed,
    broadcast_pr_comment_added, broadcast_pr_review_submitted,
)
from services.realtime.room_service import RoomService
import logging

logger = logging.getLogger(__name__)


async def list_pull_requests(
    db: AsyncSession,
    repository_id: int,
    status: Optional[str] = None,
    author_id: Optional[int] = None,
    page: int = 1,
    limit: int = 20
) -> Dict[str, Any]:
    """
    获取 PR 列表

    Args:
        db: 异步数据库会话
        repository_id: 仓库ID
        status: 状态筛选（open/merged/closed）
        author_id: 作者ID筛选
        page: 页码
        limit: 每页数量

    Returns:
        dict: 包含 PR 列表和分页信息
    """
    stmt = select(PullRequest).filter(PullRequest.repository_id == repository_id)

    if status:
        stmt = stmt.filter(PullRequest.status == status)

    if author_id:
        stmt = stmt.filter(PullRequest.author_id == author_id)

    stmt = stmt.order_by(PullRequest.created_at.desc())
    prs, total = await paginate(db, stmt, page, limit)

    return build_pagination_response(
        items=[build_pr_response(pr) for pr in prs],
        total=total,
        page=page,
        limit=limit
    )


async def get_pull_request(
    db: AsyncSession,
    repository_id: int,
    pr_number: int,
    include_details: bool = False
) -> dict:
    """
    获取 PR 详情

    Args:
        db: 异步数据库会话
        repository_id: 仓库ID
        pr_number: PR 编号
        include_details: 是否包含详细信息

    Returns:
        dict: PR 详情

    Raises:
        NotFoundException: PR 不存在
    """
    # 使用 joinedload 预加载关联数据，避免 N+1 查询
    stmt = select(PullRequest).filter(
        PullRequest.repository_id == repository_id,
        PullRequest.pr_number == pr_number
    )

    # 预加载关联数据
    stmt = stmt.options(
        joinedload(PullRequest.author),
        joinedload(PullRequest.merger)
    )

    if include_details:
        stmt = stmt.options(
            joinedload(PullRequest.comments).joinedload(PRComment.author),
            joinedload(PullRequest.reviews).joinedload(PRReview.reviewer)
        )

    result = await db.execute(stmt)
    pr = result.unique().scalar_one_or_none()

    if not pr:
        raise NotFoundException(detail="Pull request not found")

    return build_pr_response(pr, include_details=include_details)


async def create_pull_request(
    db: AsyncSession,
    repository_id: int,
    author_id: int,
    title: str,
    description: Optional[str],
    source_branch: str,
    target_branch: str
) -> dict:
    """
    创建 Pull Request

    Args:
        db: 异步数据库会话
        repository_id: 仓库ID
        author_id: 作者ID
        title: 标题
        description: 描述
        source_branch: 源分支
        target_branch: 目标分支

    Returns:
        dict: 创建的 PR 数据

    Raises:
        ValidationException: 参数验证失败
    """
    # 验证参数
    if not title or not title.strip():
        raise ValidationException(detail="Title is required")

    if source_branch == target_branch:
        raise ValidationException(detail="Source and target branches cannot be the same")

    # 生成 PR 编号
    pr_number = await get_next_sequence_number(
        db, PullRequest, "pr_number", {"repository_id": repository_id}
    )

    # 创建 PR
    pr = PullRequest(
        repository_id=repository_id,
        pr_number=pr_number,
        title=title.strip(),
        description=description,
        source_branch=source_branch,
        target_branch=target_branch,
        author_id=author_id,
        status="open"
    )

    db.add(pr)
    await db.commit()
    await db.refresh(pr)

    try:
        room = await RoomService.get_repository_room(db, repository_id)
        if room:
            result = await db.execute(select(User).filter(User.id == author_id))
            author = result.scalar_one_or_none()
            author_username = author.username if author else "unknown"
            await broadcast_pr_opened(
                room_id=room.id, pr_id=pr.id, title=pr.title,
                opener_id=author_id, opener_username=author_username,
            )
    except Exception as e:
        logger.warning("Failed to broadcast PR opened event: %s", e)

    return build_pr_response(pr)


async def publish_draft(repo_id: int, pr_number: int, user_id: int, db: AsyncSession) -> dict:
    """发布草稿 PR 为正式 PR"""
    from utils.db_utils import get_pull_request_or_404
    from utils.permission_utils import check_resource_author_or_admin

    pr = await get_pull_request_or_404(db, repo_id, pr_number)
    if not pr.is_draft:
        raise ValidationException(detail="Pull request is not a draft")

    await check_resource_author_or_admin(db, pr.author_id, user_id, "publish this draft")
    pr.is_draft = False
    await db.commit()
    await db.refresh(pr)

    try:
        room = await RoomService.get_repository_room(db, repository_id)
        if room:
            merger_username = merger.username if merger else "unknown"
            await broadcast_pr_merged(
                room_id=room.id, pr_id=pr.id, title=pr.title,
                merger_id=merger_id, merger_username=merger_username,
            )
    except Exception as e:
        logger.warning("Failed to broadcast PR merged event: %s", e)

    return build_pr_response(pr)


async def update_pull_request(
    db: AsyncSession,
    repository_id: int,
    pr_number: int,
    user_id: int,
    title: Optional[str] = None,
    description: Optional[str] = None
) -> dict:
    """
    更新 Pull Request

    Args:
        db: 异步数据库会话
        repository_id: 仓库ID
        pr_number: PR 编号
        user_id: 当前用户ID
        title: 新标题
        description: 新描述

    Returns:
        dict: 更新后的 PR 数据

    Raises:
        NotFoundException: PR 不存在
        ForbiddenException: 无权限修改
    """
    # 使用工具函数获取 PR，不存在则抛出 404
    pr = await get_pull_request_or_404(db, repository_id, pr_number)

    # 使用工具函数检查权限（作者或管理员）
    await check_resource_author_or_admin(
        db, pr.author_id, user_id, repository_id, "update this pull request"
    )

    # 已合并或关闭的 PR 不能修改
    if pr.status != "open":
        raise ValidationException(detail=f"Cannot update {pr.status} pull request")

    if title is not None:
        pr.title = title.strip()

    if description is not None:
        pr.description = description

    await db.commit()
    await db.refresh(pr)

    return build_pr_response(pr)


async def close_pull_request(
    db: AsyncSession,
    repository_id: int,
    pr_number: int,
    user_id: int
) -> dict:
    """
    关闭 Pull Request

    Args:
        db: 异步数据库会话
        repository_id: 仓库ID
        pr_number: PR 编号
        user_id: 当前用户ID

    Returns:
        dict: 更新后的 PR 数据
    """
    # 使用工具函数获取 PR，不存在则抛出 404
    pr = await get_pull_request_or_404(db, repository_id, pr_number)

    # 使用工具函数检查权限（作者或管理员）
    await check_resource_author_or_admin(
        db, pr.author_id, user_id, repository_id, "close this pull request"
    )

    if pr.status != "open":
        raise ValidationException(detail=f"Pull request is already {pr.status}")

    pr.status = "closed"
    await db.commit()
    await db.refresh(pr)

    try:
        room = await RoomService.get_repository_room(db, repository_id)
        if room:
            closer_result = await db.execute(select(User).filter(User.id == user_id))
            closer = closer_result.scalar_one_or_none()
            await broadcast_pr_closed(
                room_id=room.id, pr_id=pr.id, title=pr.title,
                closer_id=user_id, closer_username=closer.username if closer else "unknown",
            )
    except Exception as e:
        logger.warning("Failed to broadcast PR closed event: %s", e)

    return build_pr_response(pr)


async def merge_pull_request(
    db: AsyncSession,
    repository_id: int,
    pr_number: int,
    merger_id: int,
    merge_method: str = "merge"
) -> dict:
    """
    合并 Pull Request

    Args:
        db: 异步数据库会话
        repository_id: 仓库ID
        pr_number: PR 编号
        merger_id: 合并者ID
        merge_method: 合并方式（merge/squash/rebase）

    Returns:
        dict: 更新后的 PR 数据

    Raises:
        ValidationException: 无法合并
    """
    # 使用工具函数获取 PR，不存在则抛出 404
    pr = await get_pull_request_or_404(db, repository_id, pr_number)

    if pr.status != "open":
        raise ValidationException(detail=f"Cannot merge {pr.status} pull request")

    # 获取合并者信息
    result = await db.execute(select(User).filter(User.id == merger_id))
    merger = result.scalar_one_or_none()
    if not merger:
        raise NotFoundException(detail="Merger not found")

    # 检查合并权限（需要仓库写权限）
    has_permission = await check_repository_permission(
        db, repository_id, merger_id, ["owner", "admin", "developer"]
    )
    if not has_permission:
        raise AuthorizationException(detail="You don't have permission to merge this pull request")

    # 使用 GitService 进行 Git 操作
    try:
        git_service = await GitService.from_repository_id(db, repository_id)
    except NotFoundException:
        raise NotFoundException(detail="Repository not found on disk")

    # 检查是否有冲突
    has_conflicts = git_service.check_merge_conflicts(
        pr.source_branch,
        pr.target_branch
    )

    if has_conflicts:
        raise ValidationException(
            detail="Merge conflicts detected. Please resolve conflicts before merging."
        )

    # 验证合并方式
    if merge_method not in ["merge", "squash", "rebase"]:
        raise ValidationException(detail=f"Invalid merge method: {merge_method}")

    # 构建合并提交信息
    if merge_method == "squash":
        merge_message = f"{pr.title}\n\n{pr.description or ''}".strip()
    else:
        merge_message = f"Merge pull request #{pr_number}\n\n{pr.title}"
        if pr.description:
            merge_message += f"\n\n{pr.description}"

    # 执行实际合并
    try:
        signature = git_service.create_signature(
            merger.full_name or merger.username,
            merger.email or f"{merger.username}@localhost"
        )

        if merge_method == "merge":
            merged_commit_hash = git_service.merge_branches(
                pr.source_branch,
                pr.target_branch,
                signature,
                merge_message
            )
        elif merge_method == "squash":
            merged_commit_hash = git_service.squash_branches(
                pr.source_branch,
                pr.target_branch,
                signature,
                merge_message
            )
        else:  # rebase
            merged_commit_hash = git_service.rebase_branches(
                pr.source_branch,
                pr.target_branch,
                signature
            )

    except ValidationException:
        raise
    except Exception as e:
        raise ValidationException(detail=f"Merge operation failed: {str(e)}")

    # 更新 PR 状态
    pr.status = "merged"
    pr.merged_by = merger_id
    pr.merged_commit_hash = merged_commit_hash

    await db.commit()
    await db.refresh(pr)

    return build_pr_response(pr)


async def create_pr_comment(
    db: AsyncSession,
    repository_id: int,
    pr_number: int,
    author_id: int,
    content: str,
    file_path: Optional[str] = None,
    line_number: Optional[int] = None,
    commit_hash: Optional[str] = None,
    parent_id: Optional[int] = None
) -> dict:
    """
    创建 PR 评论

    Args:
        db: 异步数据库会话
        repository_id: 仓库ID
        pr_number: PR 编号
        author_id: 作者ID
        content: 评论内容
        file_path: 文件路径（行级评论）
        line_number: 行号（行级评论）
        commit_hash: 提交哈希（行级评论）
        parent_id: 父评论ID（回复）

    Returns:
        dict: 创建的评论数据
    """
    # 使用工具函数获取 PR，不存在则抛出 404
    pr = await get_pull_request_or_404(db, repository_id, pr_number)

    if not content or not content.strip():
        raise ValidationException(detail="Comment content is required")

    # 验证父评论
    if parent_id:
        result = await db.execute(select(PRComment).filter(PRComment.id == parent_id))
        parent = result.scalar_one_or_none()
        if not parent or parent.pull_request_id != pr.id:
            raise ValidationException(detail="Invalid parent comment")

    comment = PRComment(
        pull_request_id=pr.id,
        author_id=author_id,
        content=content.strip(),
        file_path=file_path,
        line_number=line_number,
        commit_hash=commit_hash,
        parent_id=parent_id
    )

    db.add(comment)
    await db.commit()
    await db.refresh(comment)

    try:
        room = await RoomService.get_repository_room(db, repository_id)
        if room:
            author_result = await db.execute(select(User).filter(User.id == author_id))
            author = author_result.scalar_one_or_none()
            await broadcast_pr_comment_added(
                room_id=room.id, pr_id=pr.id, comment_id=comment.id,
                commenter_id=author_id, commenter_username=author.username if author else "unknown",
                content=content,
            )
    except Exception as e:
        logger.warning("Failed to broadcast PR comment event: %s", e)

    return build_pr_comment_response(comment)


async def create_pr_review(
    db: AsyncSession,
    repository_id: int,
    pr_number: int,
    reviewer_id: int,
    status: str,
    comment: Optional[str] = None
) -> dict:
    """
    创建 PR 审查

    Args:
        db: 异步数据库会话
        repository_id: 仓库ID
        pr_number: PR 编号
        reviewer_id: 审查者ID
        status: 审查状态（approved/changes_requested）
        comment: 审查意见

    Returns:
        dict: 创建的审查数据
    """
    # 使用工具函数获取 PR，不存在则抛出 404
    pr = await get_pull_request_or_404(db, repository_id, pr_number)

    if status not in ["approved", "changes_requested"]:
        raise ValidationException(detail="Invalid review status")

    # 检查是否已存在审查记录
    result = await db.execute(
        select(PRReview).filter(
            PRReview.pull_request_id == pr.id,
            PRReview.reviewer_id == reviewer_id
        )
    )
    existing_review = result.scalar_one_or_none()

    is_new = existing_review is None

    if existing_review:
        existing_review.status = status
        existing_review.comment = comment
        await db.commit()
        await db.refresh(existing_review)
        review_obj = existing_review
    else:
        review = PRReview(
            pull_request_id=pr.id,
            reviewer_id=reviewer_id,
            status=status,
            comment=comment
        )
        db.add(review)
        await db.commit()
        await db.refresh(review)
        review_obj = review

    try:
        room = await RoomService.get_repository_room(db, repository_id)
        if room:
            reviewer_result = await db.execute(select(User).filter(User.id == reviewer_id))
            reviewer = reviewer_result.scalar_one_or_none()
            await broadcast_pr_review_submitted(
                room_id=room.id, pr_id=pr.id, review_id=review_obj.id,
                reviewer_id=reviewer_id, reviewer_username=reviewer.username if reviewer else "unknown",
                state=status,
            )
    except Exception as e:
        logger.warning("Failed to broadcast PR review event: %s", e)

    return build_pr_review_response(review_obj)


async def list_pr_comments(
    db: AsyncSession,
    repository_id: int,
    pr_number: int
) -> List[dict]:
    """
    获取 PR 评论列表

    Args:
        db: 异步数据库会话
        repository_id: 仓库ID
        pr_number: PR 编号

    Returns:
        list: 评论列表
    """
    # 使用工具函数获取 PR，不存在则抛出 404
    pr = await get_pull_request_or_404(db, repository_id, pr_number)

    # 使用 joinedload 预加载作者信息，避免 N+1 查询
    result = await db.execute(
        select(PRComment)
        .filter(PRComment.pull_request_id == pr.id)
        .options(joinedload(PRComment.author))
        .order_by(PRComment.created_at.asc())
    )
    comments = result.scalars().all()

    return [build_pr_comment_response(c) for c in comments]


# =============================================================================
# PR Diff 相关功能
# =============================================================================

async def get_pr_diff(
    db: AsyncSession,
    repository_id: int,
    pr_number: int
) -> dict:
    """
    获取 PR 的 diff 内容

    Args:
        db: 异步数据库会话
        repository_id: 仓库ID
        pr_number: PR 编号

    Returns:
        dict: 包含 diff 内容、文件列表、统计信息

    Raises:
        NotFoundException: PR 不存在
        ValidationException: 获取 diff 失败
    """
    from utils.git_utils import get_pr_diff as _get_pr_diff
    from utils.git_utils import get_pr_files, get_pr_stats

    # 获取 PR
    pr = await get_pull_request_or_404(db, repository_id, pr_number)

    # 获取仓库路径
    from utils.git_utils import get_repository_path
    repo_path = await get_repository_path(db, repository_id)

    try:
        # 获取 diff 内容
        diff_content = _get_pr_diff(
            repo_path,
            pr.base_commit,
            pr.head_commit
        )

        # 获取文件列表
        files = get_pr_files(
            repo_path,
            pr.base_commit,
            pr.head_commit
        )

        # 获取统计信息
        stats = get_pr_stats(
            repo_path,
            pr.base_commit,
            pr.head_commit
        )

        return {
            "diff": diff_content,
            "files": files,
            "stats": stats,
            "base_commit": pr.base_commit,
            "head_commit": pr.head_commit
        }

    except Exception as e:
        raise ValidationException(detail=f"Failed to get PR diff: {str(e)}")


async def get_pr_file_diff(
    db: AsyncSession,
    repository_id: int,
    pr_number: int,
    file_path: str
) -> dict:
    """
    获取 PR 中单个文件的 diff 内容

    Args:
        db: 异步数据库会话
        repository_id: 仓库ID
        pr_number: PR 编号
        file_path: 文件路径

    Returns:
        dict: 包含文件 diff 内容

    Raises:
        NotFoundException: PR 不存在
        ValidationException: 获取 diff 失败
    """
    from utils.git_utils import get_file_diff

    # 获取 PR
    pr = await get_pull_request_or_404(db, repository_id, pr_number)

    # 获取仓库路径
    from utils.git_utils import get_repository_path
    repo_path = await get_repository_path(db, repository_id)

    try:
        # 获取文件 diff
        diff_content = get_file_diff(
            repo_path,
            pr.base_commit,
            pr.head_commit,
            file_path
        )

        return {
            "file_path": file_path,
            "diff": diff_content,
            "base_commit": pr.base_commit,
            "head_commit": pr.head_commit
        }

    except Exception as e:
        raise ValidationException(detail=f"Failed to get file diff: {str(e)}")
