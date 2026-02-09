"""
响应构建工具模块

提供统一的响应构建函数，避免在多个服务中重复实现
"""
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime


def build_user_info(user, fields: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
    """
    构建用户信息字典

    Args:
        user: 用户模型对象
        fields: 需要包含的字段列表，默认包含 id, username, full_name

    Returns:
        dict: 用户信息字典，用户为None时返回None
    """
    if not user:
        return None

    if fields is None:
        fields = ["id", "username", "full_name"]

    result = {}
    for field in fields:
        if hasattr(user, field):
            result[field] = getattr(user, field)
    return result


def format_datetime(dt: Optional[datetime]) -> Optional[str]:
    """
    格式化日期时间为ISO格式字符串

    Args:
        dt: datetime对象

    Returns:
        str: ISO格式字符串，dt为None时返回None
    """
    return dt.isoformat() if dt else None


def build_label_response(label) -> Dict[str, Any]:
    """
    构建标签响应数据

    Args:
        label: Label 模型对象

    Returns:
        dict: 标签数据
    """
    return {
        "id": label.id,
        "name": label.name,
        "color": label.color,
        "description": label.description
    }


def build_issue_response(issue, include_details: bool = False) -> Dict[str, Any]:
    """
    构建 Issue 响应数据

    Args:
        issue: Issue 模型对象
        include_details: 是否包含详细信息（评论等）

    Returns:
        dict: Issue 数据
    """
    data = {
        "id": issue.id,
        "issue_number": issue.issue_number,
        "title": issue.title,
        "description": issue.description,
        "status": issue.status,
        "priority": issue.priority,
        "repository_id": issue.repository_id,
        "author": build_user_info(issue.author),
        "assignee": build_user_info(issue.assignee),
        "labels": [build_label_response(label) for label in issue.labels],
        "created_at": format_datetime(issue.created_at),
        "updated_at": format_datetime(issue.updated_at),
    }

    if issue.status == "closed":
        data["closed_by"] = build_user_info(issue.closer, ["id", "username"])

    if include_details:
        data["comments"] = [build_issue_comment_response(c) for c in issue.comments]

    return data


def build_issue_comment_response(comment) -> Dict[str, Any]:
    """
    构建 Issue 评论响应数据

    Args:
        comment: IssueComment 模型对象

    Returns:
        dict: 评论数据
    """
    return {
        "id": comment.id,
        "content": comment.content,
        "author": build_user_info(comment.author),
        "created_at": format_datetime(comment.created_at)
    }


def build_pr_response(pr, include_details: bool = False) -> Dict[str, Any]:
    """
    构建 Pull Request 响应数据

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
        "author": build_user_info(pr.author),
        "created_at": format_datetime(pr.created_at),
        "updated_at": format_datetime(pr.updated_at),
    }

    if pr.status == "merged":
        data["merged_by"] = build_user_info(pr.merger, ["id", "username"])
        data["merged_commit_hash"] = pr.merged_commit_hash

    if include_details:
        data["comments"] = [build_pr_comment_response(c) for c in pr.comments]
        data["reviews"] = [build_pr_review_response(r) for r in pr.reviews]

    return data


def build_pr_comment_response(comment) -> Dict[str, Any]:
    """
    构建 PR 评论响应数据

    Args:
        comment: PRComment 模型对象

    Returns:
        dict: 评论数据
    """
    return {
        "id": comment.id,
        "content": comment.content,
        "file_path": comment.file_path,
        "line_number": comment.line_number,
        "commit_hash": comment.commit_hash,
        "author": build_user_info(comment.author),
        "created_at": format_datetime(comment.created_at),
        "parent_id": comment.parent_id
    }


def build_pr_review_response(review) -> Dict[str, Any]:
    """
    构建 PR 审查响应数据

    Args:
        review: PRReview 模型对象

    Returns:
        dict: 审查数据
    """
    return {
        "id": review.id,
        "status": review.status,
        "comment": review.comment,
        "reviewer": build_user_info(review.reviewer),
        "created_at": format_datetime(review.created_at)
    }


def build_repo_response(repo, physical_exists: bool = False) -> Dict[str, Any]:
    """
    构建仓库响应数据

    Args:
        repo: Repository 模型对象
        physical_exists: 物理仓库是否存在

    Returns:
        dict: 仓库数据
    """
    return {
        "id": repo.id,
        "name": repo.name,
        "path": repo.path,
        "description": repo.description,
        "is_public": repo.is_public,
        "owner_id": repo.owner_id,
        "default_branch": repo.default_branch,
        "created_at": repo.created_at,
        "updated_at": repo.updated_at,
        "status": {
            "initialized": physical_exists
        }
    }


def build_pagination_response(
    items: List[Any],
    total: int,
    page: int,
    limit: int
) -> Dict[str, Any]:
    """
    构建分页响应数据

    Args:
        items: 当前页数据列表
        total: 总数量
        page: 当前页码
        limit: 每页数量

    Returns:
        dict: 分页响应数据
    """
    total_pages = (total + limit - 1) // limit if limit > 0 else 0

    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1
    }


def build_list_response(
    items: List[Any],
    builder_func: Callable[[Any], Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    构建列表响应数据

    Args:
        items: 模型对象列表
        builder_func: 单个对象的构建函数

    Returns:
        list: 响应数据列表
    """
    return [builder_func(item) for item in items]
