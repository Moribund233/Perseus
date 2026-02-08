"""
Issue 服务层

处理 Issue 相关的所有业务逻辑
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from models import Issue, Label, IssueComment, Repository
from exception import ValidationException, NotFoundException, AuthorizationException
from utils.permission_utils import check_resource_author_or_admin
from utils.query_utils import get_issue_or_404


def _build_issue_response(issue: Issue, include_details: bool = False) -> dict:
    """
    构建 Issue 响应数据
    
    Args:
        issue: Issue 模型对象
        include_details: 是否包含详细信息
    
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
        "author": {
            "id": issue.author.id,
            "username": issue.author.username,
            "full_name": issue.author.full_name
        } if issue.author else None,
        "assignee": {
            "id": issue.assignee.id,
            "username": issue.assignee.username,
            "full_name": issue.assignee.full_name
        } if issue.assignee else None,
        "labels": [
            {
                "id": label.id,
                "name": label.name,
                "color": label.color
            } for label in issue.labels
        ],
        "created_at": issue.created_at.isoformat() if issue.created_at else None,
        "updated_at": issue.updated_at.isoformat() if issue.updated_at else None,
    }
    
    if issue.status == "closed":
        if issue.closer:
            data["closed_by"] = {
                "id": issue.closer.id,
                "username": issue.closer.username
            }
        else:
            data["closed_by"] = None
    
    if include_details:
        data["comments"] = [_build_issue_comment_response(c) for c in issue.comments]
    
    return data


def _build_issue_comment_response(comment: IssueComment) -> dict:
    """构建 Issue 评论响应数据"""
    return {
        "id": comment.id,
        "content": comment.content,
        "author": {
            "id": comment.author.id,
            "username": comment.author.username,
            "full_name": comment.author.full_name
        } if comment.author else None,
        "created_at": comment.created_at.isoformat() if comment.created_at else None
    }


def _build_label_response(label: Label) -> dict:
    """构建标签响应数据"""
    return {
        "id": label.id,
        "name": label.name,
        "color": label.color,
        "description": label.description
    }


def list_issues(
    db: Session,
    repository_id: int,
    status: Optional[str] = None,
    label: Optional[str] = None,
    assignee_id: Optional[int] = None,
    author_id: Optional[int] = None,
    page: int = 1,
    limit: int = 20
) -> Dict[str, Any]:
    """
    获取 Issue 列表
    
    Args:
        db: 数据库会话
        repository_id: 仓库ID
        status: 状态筛选
        label: 标签名称筛选
        assignee_id: 指派人ID筛选
        author_id: 作者ID筛选
        page: 页码
        limit: 每页数量
    
    Returns:
        dict: 包含 Issue 列表和分页信息
    """
    query = db.query(Issue).filter(Issue.repository_id == repository_id)
    
    if status:
        query = query.filter(Issue.status == status)
    
    if assignee_id:
        query = query.filter(Issue.assignee_id == assignee_id)
    
    if author_id:
        query = query.filter(Issue.author_id == author_id)
    
    if label:
        query = query.join(Issue.labels).filter(Label.name == label)
    
    total = query.count()
    issues = query.order_by(Issue.created_at.desc()).offset((page - 1) * limit).limit(limit).all()
    
    return {
        "items": [_build_issue_response(issue) for issue in issues],
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit
    }


def get_issue(
    db: Session,
    repository_id: int,
    issue_number: int,
    include_details: bool = False
) -> dict:
    """
    获取 Issue 详情

    Args:
        db: 数据库会话
        repository_id: 仓库ID
        issue_number: Issue 编号
        include_details: 是否包含详细信息

    Returns:
        dict: Issue 详情
    """
    # 使用 joinedload 预加载关联数据，避免 N+1 查询
    query = db.query(Issue).filter(
        Issue.repository_id == repository_id,
        Issue.issue_number == issue_number
    )

    # 预加载关联数据
    query = query.options(
        joinedload(Issue.author),
        joinedload(Issue.assignee),
        joinedload(Issue.labels),
        joinedload(Issue.closer)
    )

    if include_details:
        query = query.options(
            joinedload(Issue.comments).joinedload(IssueComment.author)
        )

    issue = query.first()

    if not issue:
        raise NotFoundException(detail="Issue not found")

    return _build_issue_response(issue, include_details=include_details)


def create_issue(
    db: Session,
    repository_id: int,
    author_id: int,
    title: str,
    description: Optional[str] = None,
    priority: str = "medium",
    assignee_id: Optional[int] = None,
    label_ids: Optional[List[int]] = None
) -> dict:
    """
    创建 Issue
    
    Args:
        db: 数据库会话
        repository_id: 仓库ID
        author_id: 作者ID
        title: 标题
        description: 描述
        priority: 优先级
        assignee_id: 指派人ID
        label_ids: 标签ID列表
    
    Returns:
        dict: 创建的 Issue 数据
    """
    if not title or not title.strip():
        raise ValidationException(detail="Title is required")
    
    if priority not in ["low", "medium", "high", "critical"]:
        raise ValidationException(detail="Invalid priority")
    
    # 生成 Issue 编号
    max_issue_number = db.query(func.max(Issue.issue_number)).filter(
        Issue.repository_id == repository_id
    ).scalar()
    issue_number = (max_issue_number or 0) + 1
    
    # 创建 Issue
    issue = Issue(
        repository_id=repository_id,
        issue_number=issue_number,
        title=title.strip(),
        description=description,
        author_id=author_id,
        priority=priority,
        assignee_id=assignee_id,
        status="open"
    )
    
    # 添加标签
    if label_ids:
        labels = db.query(Label).filter(Label.id.in_(label_ids)).all()
        issue.labels = labels
    
    db.add(issue)
    db.commit()
    db.refresh(issue)
    
    return _build_issue_response(issue)


async def update_issue(
    db: Session,
    repository_id: int,
    issue_number: int,
    user_id: int,
    title: Optional[str] = None,
    description: Optional[str] = None,
    priority: Optional[str] = None,
    assignee_id: Optional[int] = None,
    label_ids: Optional[List[int]] = None
) -> dict:
    """
    更新 Issue

    Args:
        db: 数据库会话
        repository_id: 仓库ID
        issue_number: Issue 编号
        user_id: 当前用户ID
        title: 新标题
        description: 新描述
        priority: 新优先级
        assignee_id: 新指派人
        label_ids: 新标签列表

    Returns:
        dict: 更新后的 Issue 数据
    """
    # 使用工具函数获取 Issue，不存在则抛出 404
    issue = await get_issue_or_404(db, repository_id, issue_number)

    # 使用工具函数检查权限（作者或管理员）
    await check_resource_author_or_admin(
        db, issue.author_id, user_id, repository_id, "update this issue"
    )

    if title is not None:
        issue.title = title.strip()

    if description is not None:
        issue.description = description

    if priority is not None:
        if priority not in ["low", "medium", "high", "critical"]:
            raise ValidationException(detail="Invalid priority")
        issue.priority = priority

    if assignee_id is not None:
        issue.assignee_id = assignee_id

    if label_ids is not None:
        labels = db.query(Label).filter(Label.id.in_(label_ids)).all()
        issue.labels = labels

    db.commit()
    db.refresh(issue)

    return _build_issue_response(issue)


async def close_issue(
    db: Session,
    repository_id: int,
    issue_number: int,
    user_id: int
) -> dict:
    """
    关闭 Issue

    Args:
        db: 数据库会话
        repository_id: 仓库ID
        issue_number: Issue 编号
        user_id: 当前用户ID

    Returns:
        dict: 更新后的 Issue 数据
    """
    # 使用工具函数获取 Issue，不存在则抛出 404
    issue = await get_issue_or_404(db, repository_id, issue_number)

    # 使用工具函数检查权限（作者或管理员）
    await check_resource_author_or_admin(
        db, issue.author_id, user_id, repository_id, "close this issue"
    )

    if issue.status != "open":
        raise ValidationException(detail="Issue is already closed")

    issue.status = "closed"
    issue.closed_by = user_id

    db.commit()
    db.refresh(issue)

    return _build_issue_response(issue)


async def reopen_issue(
    db: Session,
    repository_id: int,
    issue_number: int,
    user_id: int
) -> dict:
    """
    重新打开 Issue

    Args:
        db: 数据库会话
        repository_id: 仓库ID
        issue_number: Issue 编号
        user_id: 当前用户ID

    Returns:
        dict: 更新后的 Issue 数据
    """
    # 使用工具函数获取 Issue，不存在则抛出 404
    issue = await get_issue_or_404(db, repository_id, issue_number)

    # 使用工具函数检查权限（作者或管理员）
    await check_resource_author_or_admin(
        db, issue.author_id, user_id, repository_id, "reopen this issue"
    )

    if issue.status != "closed":
        raise ValidationException(detail="Issue is already open")

    issue.status = "open"
    issue.closed_by = None

    db.commit()
    db.refresh(issue)

    return _build_issue_response(issue)


async def create_issue_comment(
    db: Session,
    repository_id: int,
    issue_number: int,
    author_id: int,
    content: str
) -> dict:
    """
    创建 Issue 评论

    Args:
        db: 数据库会话
        repository_id: 仓库ID
        issue_number: Issue 编号
        author_id: 作者ID
        content: 评论内容

    Returns:
        dict: 创建的评论数据
    """
    # 使用工具函数获取 Issue，不存在则抛出 404
    issue = await get_issue_or_404(db, repository_id, issue_number)

    if not content or not content.strip():
        raise ValidationException(detail="Comment content is required")

    comment = IssueComment(
        issue_id=issue.id,
        author_id=author_id,
        content=content.strip()
    )

    db.add(comment)
    db.commit()
    db.refresh(comment)

    return _build_issue_comment_response(comment)


async def list_issue_comments(
    db: Session,
    repository_id: int,
    issue_number: int
) -> List[dict]:
    """
    获取 Issue 评论列表

    Args:
        db: 数据库会话
        repository_id: 仓库ID
        issue_number: Issue 编号

    Returns:
        list: 评论列表
    """
    # 使用工具函数获取 Issue，不存在则抛出 404
    issue = await get_issue_or_404(db, repository_id, issue_number)

    # 使用 joinedload 预加载作者信息，避免 N+1 查询
    comments = db.query(IssueComment).filter(
        IssueComment.issue_id == issue.id
    ).options(
        joinedload(IssueComment.author)
    ).order_by(IssueComment.created_at.asc()).all()

    return [_build_issue_comment_response(c) for c in comments]


# ==================== Label 管理 ====================

def list_labels(
    db: Session,
    repository_id: int
) -> List[dict]:
    """
    获取仓库标签列表
    
    Args:
        db: 数据库会话
        repository_id: 仓库ID
    
    Returns:
        list: 标签列表
    """
    labels = db.query(Label).filter(Label.repository_id == repository_id).all()
    return [_build_label_response(label) for label in labels]


def create_label(
    db: Session,
    repository_id: int,
    name: str,
    color: str,
    description: Optional[str] = None
) -> dict:
    """
    创建标签
    
    Args:
        db: 数据库会话
        repository_id: 仓库ID
        name: 标签名称
        color: 标签颜色（十六进制）
        description: 标签描述
    
    Returns:
        dict: 创建的标签数据
    """
    if not name or not name.strip():
        raise ValidationException(detail="Label name is required")
    
    if not color or not color.startswith("#"):
        raise ValidationException(detail="Invalid color format")
    
    # 检查是否已存在
    existing = db.query(Label).filter(
        Label.repository_id == repository_id,
        Label.name == name.strip()
    ).first()
    
    if existing:
        raise ValidationException(detail="Label already exists")
    
    label = Label(
        repository_id=repository_id,
        name=name.strip(),
        color=color,
        description=description
    )
    
    db.add(label)
    db.commit()
    db.refresh(label)
    
    return _build_label_response(label)


def update_label(
    db: Session,
    repository_id: int,
    label_id: int,
    name: Optional[str] = None,
    color: Optional[str] = None,
    description: Optional[str] = None
) -> dict:
    """
    更新标签
    
    Args:
        db: 数据库会话
        repository_id: 仓库ID
        label_id: 标签ID
        name: 新名称
        color: 新颜色
        description: 新描述
    
    Returns:
        dict: 更新后的标签数据
    """
    label = db.query(Label).filter(
        Label.id == label_id,
        Label.repository_id == repository_id
    ).first()
    
    if not label:
        raise NotFoundException(detail="Label not found")
    
    if name is not None:
        label.name = name.strip()
    
    if color is not None:
        label.color = color
    
    if description is not None:
        label.description = description
    
    db.commit()
    db.refresh(label)
    
    return _build_label_response(label)


def delete_label(
    db: Session,
    repository_id: int,
    label_id: int
) -> None:
    """
    删除标签
    
    Args:
        db: 数据库会话
        repository_id: 仓库ID
        label_id: 标签ID
    """
    label = db.query(Label).filter(
        Label.id == label_id,
        Label.repository_id == repository_id
    ).first()
    
    if not label:
        raise NotFoundException(detail="Label not found")
    
    db.delete(label)
    db.commit()
