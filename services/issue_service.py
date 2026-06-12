"""
Issue 服务层

处理 Issue 相关的所有业务逻辑
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select, func

from models import Issue, Label, IssueComment
from core.exception import ValidationException, NotFoundException
from utils.permission_utils import check_resource_author_or_admin
from utils.response_builder import (
    build_issue_response,
    build_issue_comment_response,
    build_label_response,
    build_pagination_response
)
from utils.db_utils import paginate, get_next_sequence_number, get_issue_or_404


async def list_issues(
    db: AsyncSession,
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
        db: 异步数据库会话
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
    stmt = select(Issue).filter(Issue.repository_id == repository_id)

    if status:
        stmt = stmt.filter(Issue.status == status)

    if assignee_id:
        stmt = stmt.filter(Issue.assignee_id == assignee_id)

    if author_id:
        stmt = stmt.filter(Issue.author_id == author_id)

    if label:
        stmt = stmt.join(Issue.labels).filter(Label.name == label)

    stmt = stmt.order_by(Issue.created_at.desc())
    issues, total = await paginate(db, stmt, page, limit)

    return build_pagination_response(
        items=[build_issue_response(issue) for issue in issues],
        total=total,
        page=page,
        limit=limit
    )


async def get_issue(
    db: AsyncSession,
    repository_id: int,
    issue_number: int,
    include_details: bool = False
) -> dict:
    """
    获取 Issue 详情

    Args:
        db: 异步数据库会话
        repository_id: 仓库ID
        issue_number: Issue 编号
        include_details: 是否包含详细信息

    Returns:
        dict: Issue 详情
    """
    # 使用 selectinload 预加载关联数据，避免 N+1 查询
    # selectinload 在异步会话中比 joinedload 更可靠
    stmt = select(Issue).filter(
        Issue.repository_id == repository_id,
        Issue.issue_number == issue_number
    )

    # 预加载关联数据
    stmt = stmt.options(
        selectinload(Issue.author),
        selectinload(Issue.assignee),
        selectinload(Issue.labels),
        selectinload(Issue.closer)
    )

    if include_details:
        stmt = stmt.options(
            selectinload(Issue.comments).selectinload(IssueComment.author)
        )

    result = await db.execute(stmt)
    issue = result.scalar_one_or_none()

    if not issue:
        raise NotFoundException(detail="Issue not found")

    return build_issue_response(issue, include_details=include_details)


async def create_issue(
    db: AsyncSession,
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
        db: 异步数据库会话
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
    issue_number = await get_next_sequence_number(
        db, Issue, "issue_number", {"repository_id": repository_id}
    )

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
        result = await db.execute(select(Label).filter(Label.id.in_(label_ids)))
        labels = result.scalars().all()
        issue.labels = labels

    db.add(issue)
    await db.commit()
    await db.refresh(issue)

    # 重新查询 Issue 并预加载关联数据
    result = await db.execute(
        select(Issue)
        .filter(Issue.id == issue.id)
        .options(
            selectinload(Issue.author),
            selectinload(Issue.assignee),
            selectinload(Issue.labels),
            selectinload(Issue.closer)
        )
    )
    issue = result.scalar_one()

    return build_issue_response(issue)


# ==================== F-025: Issue 高级筛选 ====================

async def filter_issues(
    db: AsyncSession,
    repository_id: int,
    filters: Optional[Dict[str, Any]] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    page: int = 1,
    per_page: int = 20,
    label_match_all: bool = False
) -> Dict[str, Any]:
    """
    高级筛选 Issue

    Args:
        db: 异步数据库会话
        repository_id: 仓库ID
        filters: 筛选条件字典
            - statuses: List[str] - 状态列表
            - priorities: List[str] - 优先级列表
            - assignee_ids: List[int] - 指派人ID列表
            - author_ids: List[int] - 作者ID列表
            - label_ids: List[int] - 标签ID列表
            - search: str - 搜索关键词（标题和描述）
        sort_by: 排序字段 (created_at, updated_at, priority)
        sort_order: 排序方向 (asc, desc)
        page: 页码
        per_page: 每页数量
        label_match_all: 标签匹配模式（True=AND, False=OR）

    Returns:
        dict: 包含 Issue 列表和分页信息
    """
    from sqlalchemy import or_, and_

    filters = filters or {}

    # 基础查询
    stmt = select(Issue).filter(Issue.repository_id == repository_id)

    # 预加载关联数据
    stmt = stmt.options(
        selectinload(Issue.author),
        selectinload(Issue.assignee),
        selectinload(Issue.labels),
        selectinload(Issue.closer)
    )

    # 状态筛选
    if filters.get("statuses"):
        stmt = stmt.filter(Issue.status.in_(filters["statuses"]))

    # 优先级筛选
    if filters.get("priorities"):
        stmt = stmt.filter(Issue.priority.in_(filters["priorities"]))

    # 指派人筛选
    if filters.get("assignee_ids"):
        stmt = stmt.filter(Issue.assignee_id.in_(filters["assignee_ids"]))

    # 作者筛选
    if filters.get("author_ids"):
        stmt = stmt.filter(Issue.author_id.in_(filters["author_ids"]))

    # 标签筛选
    if filters.get("label_ids"):
        if label_match_all:
            # AND 模式：Issue 必须包含所有指定标签
            for label_id in filters["label_ids"]:
                stmt = stmt.filter(Issue.labels.any(Label.id == label_id))
        else:
            # OR 模式：Issue 包含任意一个指定标签
            stmt = stmt.join(Issue.labels).filter(Label.id.in_(filters["label_ids"])).distinct()

    # 搜索关键词
    if filters.get("search"):
        search_term = f"%{filters['search']}%"
        stmt = stmt.filter(
            or_(
                Issue.title.ilike(search_term),
                Issue.description.ilike(search_term)
            )
        )

    # 排序
    if sort_by == "priority":
        # 优先级排序需要自定义顺序
        priority_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        from sqlalchemy import case
        stmt = stmt.order_by(
            case(priority_order, value=Issue.priority).desc() if sort_order == "desc"
            else case(priority_order, value=Issue.priority).asc()
        )
    elif sort_by == "updated_at":
        stmt = stmt.order_by(Issue.updated_at.desc() if sort_order == "desc" else Issue.updated_at.asc())
    else:  # 默认按创建时间
        stmt = stmt.order_by(Issue.created_at.desc() if sort_order == "desc" else Issue.created_at.asc())

    # 分页
    issues, total = await paginate(db, stmt, page, per_page)

    return build_pagination_response(
        items=[build_issue_response(issue) for issue in issues],
        total=total,
        page=page,
        limit=per_page
    )


# ==================== F-027: Issue 批量操作 ====================

async def batch_update_issues(
    db: AsyncSession,
    repository_id: int,
    user_id: int,
    issue_numbers: List[int],
    updates: Dict[str, Any]
) -> Dict[str, Any]:
    """
    批量更新 Issue

    Args:
        db: 异步数据库会话
        repository_id: 仓库ID
        user_id: 当前用户ID
        issue_numbers: Issue 编号列表
        updates: 更新字段字典
            - status: str - 状态
            - priority: str - 优先级
            - assignee_id: int - 指派人ID
            - label_ids: List[int] - 标签ID列表

    Returns:
        dict: 操作结果统计
    """
    updated_count = 0
    failed_count = 0
    errors = []

    for issue_number in issue_numbers:
        try:
            # 获取 Issue
            issue = await get_issue_or_404(db, repository_id, issue_number)

            # 检查权限
            await check_resource_author_or_admin(
                db, issue.author_id, user_id, repository_id, f"update issue #{issue_number}"
            )

            # 更新字段
            if "status" in updates:
                issue.status = updates["status"]
                if updates["status"] == "closed" and issue.status != "closed":
                    issue.closed_by = user_id
                elif updates["status"] == "open":
                    issue.closed_by = None

            if "priority" in updates:
                if updates["priority"] not in ["low", "medium", "high", "critical"]:
                    raise ValidationException(detail=f"Invalid priority: {updates['priority']}")
                issue.priority = updates["priority"]

            if "assignee_id" in updates:
                issue.assignee_id = updates["assignee_id"]

            if "label_ids" in updates:
                result = await db.execute(select(Label).filter(Label.id.in_(updates["label_ids"])))
                labels = result.scalars().all()
                issue.labels = labels

            updated_count += 1

        except (NotFoundException, ValidationException) as e:
            failed_count += 1
            errors.append({"issue_number": issue_number, "error": str(e)})
        except Exception as e:
            failed_count += 1
            errors.append({"issue_number": issue_number, "error": str(e)})

    await db.commit()

    return {
        "updated_count": updated_count,
        "failed_count": failed_count,
        "errors": errors if errors else None
    }


async def batch_close_issues(
    db: AsyncSession,
    repository_id: int,
    user_id: int,
    issue_numbers: List[int]
) -> Dict[str, Any]:
    """
    批量关闭 Issue

    Args:
        db: 异步数据库会话
        repository_id: 仓库ID
        user_id: 当前用户ID
        issue_numbers: Issue 编号列表

    Returns:
        dict: 操作结果统计
    """
    closed_count = 0
    skipped_count = 0
    errors = []

    for issue_number in issue_numbers:
        try:
            issue = await get_issue_or_404(db, repository_id, issue_number)

            if issue.status == "closed":
                skipped_count += 1
                continue

            await check_resource_author_or_admin(
                db, issue.author_id, user_id, repository_id, f"close issue #{issue_number}"
            )

            issue.status = "closed"
            issue.closed_by = user_id
            closed_count += 1

        except Exception as e:
            errors.append({"issue_number": issue_number, "error": str(e)})

    await db.commit()

    return {
        "closed_count": closed_count,
        "skipped_count": skipped_count,
        "errors": errors if errors else None
    }


async def batch_reopen_issues(
    db: AsyncSession,
    repository_id: int,
    user_id: int,
    issue_numbers: List[int]
) -> Dict[str, Any]:
    """
    批量重新打开 Issue

    Args:
        db: 异步数据库会话
        repository_id: 仓库ID
        user_id: 当前用户ID
        issue_numbers: Issue 编号列表

    Returns:
        dict: 操作结果统计
    """
    reopened_count = 0
    skipped_count = 0
    errors = []

    for issue_number in issue_numbers:
        try:
            issue = await get_issue_or_404(db, repository_id, issue_number)

            if issue.status == "open":
                skipped_count += 1
                continue

            await check_resource_author_or_admin(
                db, issue.author_id, user_id, repository_id, f"reopen issue #{issue_number}"
            )

            issue.status = "open"
            issue.closed_by = None
            reopened_count += 1

        except Exception as e:
            errors.append({"issue_number": issue_number, "error": str(e)})

    await db.commit()

    return {
        "reopened_count": reopened_count,
        "skipped_count": skipped_count,
        "errors": errors if errors else None
    }


async def batch_add_labels(
    db: AsyncSession,
    repository_id: int,
    user_id: int,
    issue_numbers: List[int],
    label_ids: List[int]
) -> Dict[str, Any]:
    """
    批量为 Issue 添加标签

    Args:
        db: 异步数据库会话
        repository_id: 仓库ID
        user_id: 当前用户ID
        issue_numbers: Issue 编号列表
        label_ids: 标签ID列表

    Returns:
        dict: 操作结果统计
    """
    updated_count = 0
    errors = []

    # 获取所有标签
    result = await db.execute(
        select(Label).filter(Label.id.in_(label_ids), Label.repository_id == repository_id)
    )
    labels = result.scalars().all()
    label_map = {label.id: label for label in labels}

    for issue_number in issue_numbers:
        try:
            issue = await get_issue_or_404(db, repository_id, issue_number)

            await check_resource_author_or_admin(
                db, issue.author_id, user_id, repository_id, f"modify issue #{issue_number}"
            )

            # 添加标签（避免重复）
            for label_id in label_ids:
                if label_id in label_map and label_map[label_id] not in issue.labels:
                    issue.labels.append(label_map[label_id])

            updated_count += 1

        except Exception as e:
            errors.append({"issue_number": issue_number, "error": str(e)})

    await db.commit()

    return {
        "updated_count": updated_count,
        "errors": errors if errors else None
    }


async def batch_remove_labels(
    db: AsyncSession,
    repository_id: int,
    user_id: int,
    issue_numbers: List[int],
    label_ids: List[int]
) -> Dict[str, Any]:
    """
    批量从 Issue 移除标签

    Args:
        db: 异步数据库会话
        repository_id: 仓库ID
        user_id: 当前用户ID
        issue_numbers: Issue 编号列表
        label_ids: 标签ID列表

    Returns:
        dict: 操作结果统计
    """
    updated_count = 0
    errors = []

    # 获取所有标签
    result = await db.execute(
        select(Label).filter(Label.id.in_(label_ids), Label.repository_id == repository_id)
    )
    labels = result.scalars().all()
    label_map = {label.id: label for label in labels}

    for issue_number in issue_numbers:
        try:
            issue = await get_issue_or_404(db, repository_id, issue_number)

            await check_resource_author_or_admin(
                db, issue.author_id, user_id, repository_id, f"modify issue #{issue_number}"
            )

            # 移除标签
            for label_id in label_ids:
                if label_id in label_map and label_map[label_id] in issue.labels:
                    issue.labels.remove(label_map[label_id])

            updated_count += 1

        except Exception as e:
            errors.append({"issue_number": issue_number, "error": str(e)})

    await db.commit()

    return {
        "updated_count": updated_count,
        "errors": errors if errors else None
    }


async def update_issue(
    db: AsyncSession,
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
        db: 异步数据库会话
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
        result = await db.execute(select(Label).filter(Label.id.in_(label_ids)))
        labels = result.scalars().all()
        issue.labels = labels

    await db.commit()
    await db.refresh(issue)

    return build_issue_response(issue)


async def close_issue(
    db: AsyncSession,
    repository_id: int,
    issue_number: int,
    user_id: int
) -> dict:
    """
    关闭 Issue

    Args:
        db: 异步数据库会话
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

    await db.commit()

    # 重新查询 Issue 并预加载关联数据
    result = await db.execute(
        select(Issue)
        .filter(Issue.id == issue.id)
        .options(
            selectinload(Issue.author),
            selectinload(Issue.assignee),
            selectinload(Issue.labels),
            selectinload(Issue.closer)
        )
    )
    issue = result.scalar_one()

    return build_issue_response(issue)


async def reopen_issue(
    db: AsyncSession,
    repository_id: int,
    issue_number: int,
    user_id: int
) -> dict:
    """
    重新打开 Issue

    Args:
        db: 异步数据库会话
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

    await db.commit()

    # 重新查询 Issue 并预加载关联数据
    result = await db.execute(
        select(Issue)
        .filter(Issue.id == issue.id)
        .options(
            selectinload(Issue.author),
            selectinload(Issue.assignee),
            selectinload(Issue.labels),
            selectinload(Issue.closer)
        )
    )
    issue = result.scalar_one()

    return build_issue_response(issue)


async def create_issue_comment(
    db: AsyncSession,
    repository_id: int,
    issue_number: int,
    author_id: int,
    content: str
) -> dict:
    """
    创建 Issue 评论

    Args:
        db: 异步数据库会话
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
    await db.commit()
    await db.refresh(comment)

    return build_issue_comment_response(comment)


async def list_issue_comments(
    db: AsyncSession,
    repository_id: int,
    issue_number: int
) -> List[dict]:
    """
    获取 Issue 评论列表

    Args:
        db: 异步数据库会话
        repository_id: 仓库ID
        issue_number: Issue 编号

    Returns:
        list: 评论列表
    """
    # 使用工具函数获取 Issue，不存在则抛出 404
    issue = await get_issue_or_404(db, repository_id, issue_number)

    # 使用 selectinload 预加载作者信息，避免 N+1 查询
    result = await db.execute(
        select(IssueComment)
        .filter(IssueComment.issue_id == issue.id)
        .options(selectinload(IssueComment.author))
        .order_by(IssueComment.created_at.asc())
    )
    comments = result.scalars().all()

    return [build_issue_comment_response(c) for c in comments]


# ==================== Label 管理 ====================

async def list_labels(
    db: AsyncSession,
    repository_id: int
) -> List[dict]:
    """
    获取仓库标签列表

    Args:
        db: 异步数据库会话
        repository_id: 仓库ID

    Returns:
        list: 标签列表
    """
    result = await db.execute(select(Label).filter(Label.repository_id == repository_id))
    labels = result.scalars().all()
    return [build_label_response(label) for label in labels]


async def create_label(
    db: AsyncSession,
    repository_id: int,
    name: str,
    color: str,
    description: Optional[str] = None
) -> dict:
    """
    创建标签

    Args:
        db: 异步数据库会话
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
    result = await db.execute(
        select(Label).filter(
            Label.repository_id == repository_id,
            Label.name == name.strip()
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        raise ValidationException(detail="Label already exists")

    label = Label(
        repository_id=repository_id,
        name=name.strip(),
        color=color,
        description=description
    )

    db.add(label)
    await db.commit()
    await db.refresh(label)

    return build_label_response(label)


async def update_label(
    db: AsyncSession,
    repository_id: int,
    label_id: int,
    name: Optional[str] = None,
    color: Optional[str] = None,
    description: Optional[str] = None
) -> dict:
    """
    更新标签

    Args:
        db: 异步数据库会话
        repository_id: 仓库ID
        label_id: 标签ID
        name: 新名称
        color: 新颜色
        description: 新描述

    Returns:
        dict: 更新后的标签数据
    """
    result = await db.execute(
        select(Label).filter(
            Label.id == label_id,
            Label.repository_id == repository_id
        )
    )
    label = result.scalar_one_or_none()

    if not label:
        raise NotFoundException(detail="Label not found")

    if name is not None:
        label.name = name.strip()

    if color is not None:
        label.color = color

    if description is not None:
        label.description = description

    await db.commit()
    await db.refresh(label)

    return build_label_response(label)


async def delete_label(
    db: AsyncSession,
    repository_id: int,
    label_id: int
) -> None:
    """
    删除标签

    Args:
        db: 异步数据库会话
        repository_id: 仓库ID
        label_id: 标签ID
    """
    result = await db.execute(
        select(Label).filter(
            Label.id == label_id,
            Label.repository_id == repository_id
        )
    )
    label = result.scalar_one_or_none()

    if not label:
        raise NotFoundException(detail="Label not found")

    await db.delete(label)
    await db.commit()


async def add_label_to_issue(
    db: AsyncSession,
    repository_id: int,
    issue_number: int,
    label_id: int,
    user_id: int
) -> dict:
    """
    为 Issue 添加标签

    Args:
        db: 异步数据库会话
        repository_id: 仓库ID
        issue_number: Issue 编号
        label_id: 标签ID
        user_id: 当前用户ID

    Returns:
        dict: 更新后的 Issue 数据

    Raises:
        NotFoundException: Issue 或标签不存在时抛出
        ValidationException: 标签已存在时抛出
    """
    from utils.permission_utils import check_resource_author_or_admin
    from sqlalchemy.orm import selectinload

    # 获取 Issue
    issue = await get_issue_or_404(db, repository_id, issue_number)

    # 检查权限
    await check_resource_author_or_admin(
        db, issue.author_id, user_id, repository_id, "modify this issue"
    )

    # 获取标签
    result = await db.execute(
        select(Label).filter(
            Label.id == label_id,
            Label.repository_id == repository_id
        )
    )
    label = result.scalar_one_or_none()

    if not label:
        raise NotFoundException(detail="Label not found")

    # 检查标签是否已存在
    if label in issue.labels:
        raise ValidationException(detail="Label already added to this issue")

    # 添加标签
    issue.labels.append(label)
    await db.commit()

    # 重新查询 Issue 并预加载关联数据
    result = await db.execute(
        select(Issue)
        .filter(Issue.id == issue.id)
        .options(
            selectinload(Issue.author),
            selectinload(Issue.assignee),
            selectinload(Issue.labels),
            selectinload(Issue.closer)
        )
    )
    issue = result.scalar_one()

    return build_issue_response(issue)


async def remove_label_from_issue(
    db: AsyncSession,
    repository_id: int,
    issue_number: int,
    label_id: int,
    user_id: int
) -> dict:
    """
    从 Issue 移除标签

    Args:
        db: 异步数据库会话
        repository_id: 仓库ID
        issue_number: Issue 编号
        label_id: 标签ID
        user_id: 当前用户ID

    Returns:
        dict: 更新后的 Issue 数据

    Raises:
        NotFoundException: Issue 或标签不存在时抛出
        ValidationException: 标签不存在于 Issue 时抛出
    """
    from utils.permission_utils import check_resource_author_or_admin
    from sqlalchemy.orm import selectinload

    # 获取 Issue
    issue = await get_issue_or_404(db, repository_id, issue_number)

    # 检查权限
    await check_resource_author_or_admin(
        db, issue.author_id, user_id, repository_id, "modify this issue"
    )

    # 获取标签
    result = await db.execute(
        select(Label).filter(
            Label.id == label_id,
            Label.repository_id == repository_id
        )
    )
    label = result.scalar_one_or_none()

    if not label:
        raise NotFoundException(detail="Label not found")

    # 检查标签是否存在于 Issue
    if label not in issue.labels:
        raise ValidationException(detail="Label not found in this issue")

    # 移除标签
    issue.labels.remove(label)
    await db.commit()

    # 重新查询 Issue 并预加载关联数据
    result = await db.execute(
        select(Issue)
        .filter(Issue.id == issue.id)
        .options(
            selectinload(Issue.author),
            selectinload(Issue.assignee),
            selectinload(Issue.labels),
            selectinload(Issue.closer)
        )
    )
    issue = result.scalar_one()

    return build_issue_response(issue)
