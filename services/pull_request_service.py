"""
Pull Request 服务层

处理 Pull Request 相关的所有业务逻辑
"""
import os
import tempfile
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
import pygit2

from models import PullRequest, PRComment, PRReview, Repository, User
from exception import ValidationException, NotFoundException, ConflictException, AuthorizationException
from utils.permission_utils import check_resource_author_or_admin, check_repository_permission
from utils.query_utils import get_pull_request_or_404


def _build_pr_response(pr: PullRequest, include_details: bool = False) -> dict:
    """
    构建 PR 响应数据
    
    Args:
        pr: PullRequest 模型对象
        include_details: 是否包含详细信息（评论、审查等）
    
    Returns:
        dict: PR 数据
    """
    data = {
        "id": pr.id,
        "pr_number": pr.pr_number,
        "title": pr.title,
        "description": pr.description,
        "source_branch": pr.source_branch,
        "target_branch": pr.target_branch,
        "status": pr.status,
        "repository_id": pr.repository_id,
        "author": {
            "id": pr.author.id,
            "username": pr.author.username,
            "full_name": pr.author.full_name
        } if pr.author else None,
        "created_at": pr.created_at.isoformat() if pr.created_at else None,
        "updated_at": pr.updated_at.isoformat() if pr.updated_at else None,
    }
    
    if pr.status == "merged":
        data["merged_by"] = {
            "id": pr.merger.id,
            "username": pr.merger.username
        } if pr.merger else None
        data["merged_commit_hash"] = pr.merged_commit_hash
    
    if include_details:
        data["comments"] = [_build_pr_comment_response(c) for c in pr.comments]
        data["reviews"] = [_build_pr_review_response(r) for r in pr.reviews]
    
    return data


def _build_pr_comment_response(comment: PRComment) -> dict:
    """构建 PR 评论响应数据"""
    return {
        "id": comment.id,
        "content": comment.content,
        "file_path": comment.file_path,
        "line_number": comment.line_number,
        "commit_hash": comment.commit_hash,
        "author": {
            "id": comment.author.id,
            "username": comment.author.username,
            "full_name": comment.author.full_name
        } if comment.author else None,
        "created_at": comment.created_at.isoformat() if comment.created_at else None,
        "parent_id": comment.parent_id
    }


def _build_pr_review_response(review: PRReview) -> dict:
    """构建 PR 审查响应数据"""
    return {
        "id": review.id,
        "status": review.status,
        "comment": review.comment,
        "reviewer": {
            "id": review.reviewer.id,
            "username": review.reviewer.username,
            "full_name": review.reviewer.full_name
        } if review.reviewer else None,
        "created_at": review.created_at.isoformat() if review.created_at else None
    }


async def list_pull_requests(
    db: Session,
    repository_id: int,
    status: Optional[str] = None,
    author_id: Optional[int] = None,
    page: int = 1,
    limit: int = 20
) -> Dict[str, Any]:
    """
    获取 PR 列表
    
    Args:
        db: 数据库会话
        repository_id: 仓库ID
        status: 状态筛选（open/merged/closed）
        author_id: 作者ID筛选
        page: 页码
        limit: 每页数量
    
    Returns:
        dict: 包含 PR 列表和分页信息
    """
    query = db.query(PullRequest).filter(PullRequest.repository_id == repository_id)
    
    if status:
        query = query.filter(PullRequest.status == status)
    
    if author_id:
        query = query.filter(PullRequest.author_id == author_id)
    
    total = query.count()
    prs = query.order_by(PullRequest.created_at.desc()).offset((page - 1) * limit).limit(limit).all()
    
    return {
        "items": [_build_pr_response(pr) for pr in prs],
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit
    }


async def get_pull_request(
    db: Session,
    repository_id: int,
    pr_number: int,
    include_details: bool = False
) -> dict:
    """
    获取 PR 详情

    Args:
        db: 数据库会话
        repository_id: 仓库ID
        pr_number: PR 编号
        include_details: 是否包含详细信息

    Returns:
        dict: PR 详情

    Raises:
        NotFoundException: PR 不存在
    """
    # 使用 joinedload 预加载关联数据，避免 N+1 查询
    query = db.query(PullRequest).filter(
        PullRequest.repository_id == repository_id,
        PullRequest.pr_number == pr_number
    )

    # 预加载关联数据
    query = query.options(
        joinedload(PullRequest.author),
        joinedload(PullRequest.merger)
    )

    if include_details:
        query = query.options(
            joinedload(PullRequest.comments).joinedload(PRComment.author),
            joinedload(PullRequest.reviews).joinedload(PRReview.reviewer)
        )

    pr = query.first()

    if not pr:
        raise NotFoundException(detail="Pull request not found")

    return _build_pr_response(pr, include_details=include_details)


async def create_pull_request(
    db: Session,
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
        db: 数据库会话
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
        ConflictException: 分支相同或 PR 已存在
    """
    # 验证参数
    if not title or not title.strip():
        raise ValidationException(detail="Title is required")
    
    if source_branch == target_branch:
        raise ValidationException(detail="Source and target branches cannot be the same")
    
    # 生成 PR 编号
    max_pr_number = db.query(func.max(PullRequest.pr_number)).filter(
        PullRequest.repository_id == repository_id
    ).scalar()
    pr_number = (max_pr_number or 0) + 1
    
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
    db.commit()
    db.refresh(pr)
    
    return _build_pr_response(pr)


async def update_pull_request(
    db: Session,
    repository_id: int,
    pr_number: int,
    user_id: int,
    title: Optional[str] = None,
    description: Optional[str] = None
) -> dict:
    """
    更新 Pull Request

    Args:
        db: 数据库会话
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

    db.commit()
    db.refresh(pr)

    return _build_pr_response(pr)


async def close_pull_request(
    db: Session,
    repository_id: int,
    pr_number: int,
    user_id: int
) -> dict:
    """
    关闭 Pull Request

    Args:
        db: 数据库会话
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
    db.commit()
    db.refresh(pr)

    return _build_pr_response(pr)


async def _get_repo_path(db: Session, repository_id: int) -> str:
    """
    获取仓库的物理路径

    Args:
        db: 数据库会话
        repository_id: 仓库ID

    Returns:
        str: 仓库物理路径
    """
    repo = db.query(Repository).filter(Repository.id == repository_id).first()
    if not repo:
        raise NotFoundException(detail="Repository not found")

    # 从配置获取仓库根目录
    from config import get_config
    config = get_config()
    repo_root = config.storage.repo_root

    return os.path.join(repo_root, repo.path)


async def _check_merge_conflicts(
    repo_path: str,
    source_branch: str,
    target_branch: str
) -> bool:
    """
    检查分支之间是否有合并冲突

    Args:
        repo_path: 仓库路径
        source_branch: 源分支
        target_branch: 目标分支

    Returns:
        bool: 是否有冲突
    """
    try:
        repo = pygit2.Repository(repo_path)

        # 获取分支引用
        source_ref = f"refs/heads/{source_branch}"
        target_ref = f"refs/heads/{target_branch}"

        # 检查分支是否存在
        if source_ref not in repo.references or target_ref not in repo.references:
            return True  # 分支不存在视为有冲突

        # 获取提交
        source_commit = repo.references[source_ref].peel(pygit2.Commit)
        target_commit = repo.references[target_ref].peel(pygit2.Commit)

        # 创建临时索引进行合并测试
        index = repo.merge_commits(target_commit, source_commit)

        # 检查是否有冲突
        return index.has_conflicts

    except Exception as e:
        raise ValidationException(detail=f"Failed to check merge conflicts: {str(e)}")


async def _perform_git_merge(
    repo_path: str,
    source_branch: str,
    target_branch: str,
    merger_name: str,
    merger_email: str,
    message: str
) -> str:
    """
    执行实际的 Git 合并操作

    Args:
        repo_path: 仓库路径
        source_branch: 源分支
        target_branch: 目标分支
        merger_name: 合并者名称
        merger_email: 合并者邮箱
        message: 合并提交信息

    Returns:
        str: 合并后的提交哈希
    """
    try:
        repo = pygit2.Repository(repo_path)

        # 获取分支引用
        source_ref_name = f"refs/heads/{source_branch}"
        target_ref_name = f"refs/heads/{target_branch}"

        source_commit = repo.references[source_ref_name].peel(pygit2.Commit)
        target_commit = repo.references[target_ref_name].peel(pygit2.Commit)

        # 创建签名
        signature = pygit2.Signature(merger_name, merger_email)

        # 执行合并
        index = repo.merge_commits(target_commit, source_commit)

        if index.has_conflicts:
            raise ValidationException(detail="Merge conflicts detected")

        # 写入树对象
        tree_oid = index.write_tree(repo)

        # 创建合并提交
        parents = [target_commit.id, source_commit.id]
        commit_oid = repo.create_commit(
            target_ref_name,  # 更新目标分支
            signature,  # 作者
            signature,  # 提交者
            message,
            tree_oid,
            parents
        )

        return str(commit_oid)

    except ValidationException:
        raise
    except Exception as e:
        raise ValidationException(detail=f"Merge failed: {str(e)}")


async def merge_pull_request(
    db: Session,
    repository_id: int,
    pr_number: int,
    merger_id: int,
    merge_method: str = "merge"
) -> dict:
    """
    合并 Pull Request

    Args:
        db: 数据库会话
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
    merger = db.query(User).filter(User.id == merger_id).first()
    if not merger:
        raise NotFoundException(detail="Merger not found")

    # 检查合并权限（需要仓库写权限）
    has_permission = check_repository_permission(
        db, repository_id, merger_id, ["owner", "admin", "developer"]
    )
    if not has_permission:
        raise AuthorizationException(detail="You don't have permission to merge this pull request")

    # 获取仓库路径
    repo_path = await _get_repo_path(db, repository_id)

    if not os.path.exists(repo_path):
        raise NotFoundException(detail="Repository not found on disk")

    # 检查是否有冲突
    has_conflicts = await _check_merge_conflicts(
        repo_path,
        pr.source_branch,
        pr.target_branch
    )

    if has_conflicts:
        raise ValidationException(detail="Merge conflicts detected. Please resolve conflicts before merging.")

    # 构建合并提交信息
    merge_message = f"Merge pull request #{pr_number}\n\n{pr.title}"
    if pr.description:
        merge_message += f"\n\n{pr.description}"

    # 执行实际合并
    try:
        merged_commit_hash = await _perform_git_merge(
            repo_path,
            pr.source_branch,
            pr.target_branch,
            merger.full_name or merger.username,
            merger.email or f"{merger.username}@localhost",
            merge_message
        )
    except ValidationException:
        raise
    except Exception as e:
        raise ValidationException(detail=f"Merge operation failed: {str(e)}")

    # 更新 PR 状态
    pr.status = "merged"
    pr.merged_by = merger_id
    pr.merged_commit_hash = merged_commit_hash

    db.commit()
    db.refresh(pr)

    return _build_pr_response(pr)


async def create_pr_comment(
    db: Session,
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
        db: 数据库会话
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
        parent = db.query(PRComment).filter(PRComment.id == parent_id).first()
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
    db.commit()
    db.refresh(comment)

    return _build_pr_comment_response(comment)


async def create_pr_review(
    db: Session,
    repository_id: int,
    pr_number: int,
    reviewer_id: int,
    status: str,
    comment: Optional[str] = None
) -> dict:
    """
    创建 PR 审查

    Args:
        db: 数据库会话
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
    existing_review = db.query(PRReview).filter(
        PRReview.pull_request_id == pr.id,
        PRReview.reviewer_id == reviewer_id
    ).first()

    if existing_review:
        # 更新现有审查
        existing_review.status = status
        existing_review.comment = comment
        db.commit()
        db.refresh(existing_review)
        return _build_pr_review_response(existing_review)

    # 创建新审查
    review = PRReview(
        pull_request_id=pr.id,
        reviewer_id=reviewer_id,
        status=status,
        comment=comment
    )

    db.add(review)
    db.commit()
    db.refresh(review)

    return _build_pr_review_response(review)


async def list_pr_comments(
    db: Session,
    repository_id: int,
    pr_number: int
) -> List[dict]:
    """
    获取 PR 评论列表

    Args:
        db: 数据库会话
        repository_id: 仓库ID
        pr_number: PR 编号

    Returns:
        list: 评论列表
    """
    # 使用工具函数获取 PR，不存在则抛出 404
    pr = await get_pull_request_or_404(db, repository_id, pr_number)

    # 使用 joinedload 预加载作者信息，避免 N+1 查询
    comments = db.query(PRComment).filter(
        PRComment.pull_request_id == pr.id
    ).options(
        joinedload(PRComment.author)
    ).order_by(PRComment.created_at.asc()).all()

    return [_build_pr_comment_response(c) for c in comments]
