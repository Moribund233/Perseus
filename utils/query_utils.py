"""
数据库查询工具模块

提供统一的数据库查询辅助函数，避免重复代码
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from core.exception import NotFoundException


async def get_resource_or_404(
    db: AsyncSession,
    model,
    filters: dict,
    error_message: str = "Resource not found"
):
    """
    获取资源，不存在则抛出404异常

    Args:
        db: 异步数据库会话
        model: SQLAlchemy 模型类
        filters: 过滤条件字典，如 {"id": 1, "name": "test"}
        error_message: 错误信息

    Returns:
        查询到的模型实例

    Raises:
        NotFoundException: 资源不存在时抛出
    """
    stmt = select(model)
    for key, value in filters.items():
        stmt = stmt.filter(getattr(model, key) == value)
    result = await db.execute(stmt)
    resource = result.scalar_one_or_none()

    if not resource:
        raise NotFoundException(detail=error_message)

    return resource


async def get_issue_or_404(
    db: AsyncSession,
    repository_id: int,
    issue_number: int
):
    """
    获取 Issue，不存在则抛出404异常

    Args:
        db: 异步数据库会话
        repository_id: 仓库ID
        issue_number: Issue 编号

    Returns:
        Issue 模型实例

    Raises:
        NotFoundException: Issue 不存在时抛出
    """
    from sqlalchemy.orm import selectinload
    from models.issue import Issue

    result = await db.execute(
        select(Issue)
        .filter(
            Issue.repository_id == repository_id,
            Issue.issue_number == issue_number
        )
        .options(
            selectinload(Issue.author),
            selectinload(Issue.assignee),
            selectinload(Issue.labels),
            selectinload(Issue.closer)
        )
    )
    issue = result.scalar_one_or_none()

    if not issue:
        raise NotFoundException(detail=f"Issue #{issue_number} not found")

    return issue


async def get_pull_request_or_404(
    db: AsyncSession,
    repository_id: int,
    pr_number: int
):
    """
    获取 Pull Request，不存在则抛出404异常

    Args:
        db: 异步数据库会话
        repository_id: 仓库ID
        pr_number: PR 编号

    Returns:
        PullRequest 模型实例

    Raises:
        NotFoundException: PR 不存在时抛出
    """
    from models.pull_request import PullRequest

    result = await db.execute(
        select(PullRequest).filter(
            PullRequest.repository_id == repository_id,
            PullRequest.pr_number == pr_number
        )
    )
    pr = result.scalar_one_or_none()

    if not pr:
        raise NotFoundException(detail=f"Pull Request #{pr_number} not found")

    return pr


async def get_repository_or_404(
    db: AsyncSession,
    repository_id: int
):
    """
    获取仓库，不存在则抛出404异常

    Args:
        db: 异步数据库会话
        repository_id: 仓库ID

    Returns:
        Repository 模型实例

    Raises:
        NotFoundException: 仓库不存在时抛出
    """
    from models.repository import Repository

    result = await db.execute(
        select(Repository).filter(Repository.id == repository_id)
    )
    repo = result.scalar_one_or_none()

    if not repo:
        raise NotFoundException(detail=f"Repository not found")

    return repo


async def get_user_or_404(
    db: AsyncSession,
    user_id: int
):
    """
    获取用户，不存在则抛出404异常

    Args:
        db: 异步数据库会话
        user_id: 用户ID

    Returns:
        User 模型实例

    Raises:
        NotFoundException: 用户不存在时抛出
    """
    from models.user import User

    result = await db.execute(
        select(User).filter(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise NotFoundException(detail="User not found")

    return user


async def paginate_query(
    db: AsyncSession,
    stmt,
    page: int = 1,
    limit: int = 20,
    max_limit: int = 100
):
    """
    对查询进行分页

    Args:
        db: 异步数据库会话
        stmt: SQLAlchemy select 语句
        page: 页码，从1开始
        limit: 每页数量
        max_limit: 最大每页数量限制

    Returns:
        tuple: (分页后的结果列表, 总数量)
    """
    from sqlalchemy import func, select

    # 限制每页最大数量
    limit = min(limit, max_limit)

    # 计算偏移量
    offset = (page - 1) * limit

    # 获取总数
    count_stmt = select(func.count()).select_from(stmt.subquery())
    count_result = await db.execute(count_stmt)
    total = count_result.scalar()

    # 分页查询
    paginated_stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(paginated_stmt)
    paginated = result.scalars().all()

    return paginated, total


async def build_pagination_response(
    items: list,
    total: int,
    page: int,
    limit: int
) -> dict:
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
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1
    }
