"""
行内评论服务（Editor Discussions / 文件+行号锚定）

评论锚定到仓库内文件的具体行（可选分支/提交），支持回复、解决/重新打开、删除。
"""
import uuid
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from models.file_comment import FileComment
from models.user import User
from core.exception import ValidationException, NotFoundException
from utils.permission_utils import check_repository_permission, check_resource_author_or_admin

READ_ROLES = ["owner", "admin", "developer", "viewer"]
MAX_COMMENT_LENGTH = 10000


async def _ensure_repo_read_access(db: AsyncSession, repository_id: uuid.UUID, user_id: uuid.UUID) -> None:
    from models.repository import Repository

    result = await db.execute(select(Repository).filter(Repository.id == repository_id))
    repo = result.scalar_one_or_none()
    if repo is None:
        raise NotFoundException("仓库不存在", error_code="repository_not_found")
    if repo.is_public:
        return
    if not await check_repository_permission(db, repository_id, user_id, READ_ROLES):
        raise ValidationException("你没有该仓库的访问权限", error_code="repository_access_denied")


def build_file_comment_response(comment: FileComment, author_username: Optional[str] = None) -> Dict[str, Any]:
    if author_username is None and comment.author is not None:
        author_username = comment.author.username
    return {
        "id": comment.id,
        "repository_id": comment.repository_id,
        "author_id": comment.author_id,
        "author_username": author_username or "unknown",
        "content": comment.content,
        "file_path": comment.file_path,
        "line_number": comment.line_number,
        "branch": comment.branch,
        "commit_hash": comment.commit_hash,
        "parent_id": comment.parent_id,
        "resolved": comment.resolved,
        "created_at": comment.created_at.isoformat() if comment.created_at else None,
        "updated_at": comment.updated_at.isoformat() if comment.updated_at else None,
    }


async def create_file_comment(
    db: AsyncSession,
    repository_id: uuid.UUID,
    author_id: uuid.UUID,
    content: str,
    file_path: str,
    line_number: Optional[int] = None,
    branch: Optional[str] = None,
    commit_hash: Optional[str] = None,
    parent_id: Optional[uuid.UUID] = None,
) -> Dict[str, Any]:
    """创建行内评论（支持对已有评论回复）."""
    await _ensure_repo_read_access(db, repository_id, author_id)

    if not content or not content.strip():
        raise ValidationException("评论内容不能为空", error_code="comment_content_required")
    file_path = (file_path or "").strip()
    if not file_path:
        raise ValidationException("文件路径不能为空", error_code="comment_file_path_required")

    if parent_id:
        result = await db.execute(
            select(FileComment).filter(
                FileComment.id == parent_id,
                FileComment.repository_id == repository_id,
            )
        )
        parent = result.scalar_one_or_none()
        if parent is None:
            raise ValidationException("父评论不存在", error_code="comment_invalid_parent")

    comment = FileComment(
        repository_id=repository_id,
        author_id=author_id,
        content=content.strip()[:MAX_COMMENT_LENGTH],
        file_path=file_path[:500],
        line_number=line_number,
        branch=branch,
        commit_hash=commit_hash,
        parent_id=parent_id,
    )
    db.add(comment)
    await db.commit()
    await db.refresh(comment)

    author_result = await db.execute(select(User).filter(User.id == author_id))
    author = author_result.scalar_one_or_none()
    return build_file_comment_response(comment, author.username if author else None)


async def list_file_comments(
    db: AsyncSession,
    repository_id: uuid.UUID,
    user_id: uuid.UUID,
    file_path: Optional[str] = None,
    branch: Optional[str] = None,
    line_number: Optional[int] = None,
    include_resolved: bool = True,
) -> List[Dict[str, Any]]:
    """列出仓库内文件评论（默认含已解决，flat 列表按 parent_id 构建线程）."""
    await _ensure_repo_read_access(db, repository_id, user_id)

    query = (
        select(FileComment)
        .options(selectinload(FileComment.author))
        .filter(FileComment.repository_id == repository_id)
    )
    if file_path:
        query = query.filter(FileComment.file_path == file_path)
    if branch:
        query = query.filter(FileComment.branch == branch)
    if line_number is not None:
        query = query.filter(FileComment.line_number == line_number)
    if not include_resolved:
        query = query.filter(FileComment.resolved.is_(False))

    query = query.order_by(FileComment.created_at.asc())
    result = await db.execute(query)
    comments = result.scalars().all()
    return [build_file_comment_response(c, c.author.username if c.author else None) for c in comments]


async def _get_repo_comment_or_raise(
    db: AsyncSession,
    repository_id: uuid.UUID,
    comment_id: uuid.UUID,
) -> FileComment:
    result = await db.execute(
        select(FileComment).options(selectinload(FileComment.author)).filter(
            FileComment.id == comment_id,
            FileComment.repository_id == repository_id,
        )
    )
    comment = result.scalar_one_or_none()
    if comment is None:
        raise NotFoundException("评论不存在", error_code="comment_not_found")
    return comment


async def set_file_comment_resolved(
    db: AsyncSession,
    repository_id: uuid.UUID,
    comment_id: uuid.UUID,
    user_id: uuid.UUID,
    resolved: bool,
) -> Dict[str, Any]:
    """解决/重新打开评论：仅作者或仓库负责人可操作."""
    comment = await _get_repo_comment_or_raise(db, repository_id, comment_id)
    await check_resource_author_or_admin(
        db,
        comment.author_id,
        user_id,
        repository_id,
        action_description="resolve this comment",
    )
    comment.resolved = bool(resolved)
    await db.commit()
    await db.refresh(comment)
    return build_file_comment_response(comment, comment.author.username if comment.author else None)


async def delete_file_comment(
    db: AsyncSession,
    repository_id: uuid.UUID,
    comment_id: uuid.UUID,
    user_id: uuid.UUID,
) -> bool:
    """删除评论（含回复）：仅作者或仓库负责人可操作."""
    comment = await _get_repo_comment_or_raise(db, repository_id, comment_id)
    await check_resource_author_or_admin(
        db,
        comment.author_id,
        user_id,
        repository_id,
        action_description="delete this comment",
    )
    # 先删回复, 再删父评论, 避免自关联外键约束
    replies_result = await db.execute(
        select(FileComment).filter(FileComment.parent_id == comment_id)
    )
    for reply in replies_result.scalars().all():
        await db.delete(reply)
    await db.delete(comment)
    await db.commit()
    return True