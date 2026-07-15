"""
数据库工具模块

提供统一的数据库查询辅助函数，包括预加载、分页等功能
"""
from typing import Optional, List, Type, TypeVar, Any
from sqlalchemy.orm import joinedload
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.exception import NotFoundException
import uuid

T = TypeVar('T')


async def query_with_eager_load(
    db: AsyncSession,
    model: Type[T],
    filters: dict,
    eager_loads: Optional[List[Any]] = None
) -> Optional[T]:
    """
    执行带预加载的数据库查询

    Args:
        db: 异步数据库会话
        model: SQLAlchemy 模型类
        filters: 过滤条件字典，如 {"id": 1}
        eager_loads: 预加载关系列表，如 [Model.relation1, Model.relation2]

    Returns:
        查询到的模型实例，不存在返回None
    """
    stmt = select(model)

    # 应用过滤条件
    for key, value in filters.items():
        stmt = stmt.filter(getattr(model, key) == value)

    # 应用预加载
    if eager_loads:
        for relation in eager_loads:
            stmt = stmt.options(joinedload(relation))

    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_or_404(
    db: AsyncSession,
    model: Type[T],
    filters: dict,
    error_message: str = "Resource not found",
    eager_loads: Optional[List[Any]] = None
) -> T:
    """
    获取资源，不存在则抛出404异常

    Args:
        db: 异步数据库会话
        model: SQLAlchemy 模型类
        filters: 过滤条件字典
        error_message: 错误信息
        eager_loads: 预加载关系列表

    Returns:
        查询到的模型实例

    Raises:
        NotFoundException: 资源不存在时抛出
    """
    resource = await query_with_eager_load(db, model, filters, eager_loads)

    if not resource:
        raise NotFoundException(detail=error_message)

    return resource


async def paginate(
    db: AsyncSession,
    stmt,
    page: int = 1,
    limit: int = 20,
    max_limit: int = 100
) -> tuple[List[Any], int]:
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
    # 限制每页最大数量
    limit = min(limit, max_limit)

    # 计算偏移量
    offset = (page - 1) * limit

    # 获取总数
    from sqlalchemy import func
    count_stmt = select(func.count()).select_from(stmt.subquery())
    count_result = await db.execute(count_stmt)
    total = count_result.scalar()

    # 分页查询
    paginated_stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(paginated_stmt)
    results = result.scalars().all()

    return results, total


async def get_next_sequence_number(
    db: AsyncSession,
    model: Type[T],
    field_name: str,
    filters: Optional[dict] = None
) -> int:
    """
    获取下一个序列编号（如 Issue 编号、PR 编号）

    Args:
        db: 异步数据库会话
        model: SQLAlchemy 模型类
        field_name: 编号字段名（如 "issue_number"）
        filters: 可选的过滤条件

    Returns:
        int: 下一个序列编号
    """
    from sqlalchemy import func
    stmt = select(func.max(getattr(model, field_name)))

    if filters:
        for key, value in filters.items():
            stmt = stmt.filter(getattr(model, key) == value)

    result = await db.execute(stmt)
    max_number = result.scalar()
    return (max_number or 0) + 1


async def exists(
    db: AsyncSession,
    model: Type[T],
    filters: dict
) -> bool:
    """
    检查资源是否存在（异步版本）

    Args:
        db: 异步数据库会话
        model: SQLAlchemy 模型类
        filters: 过滤条件字典

    Returns:
        bool: 资源是否存在
    """
    stmt = select(model)
    for key, value in filters.items():
        stmt = stmt.filter(getattr(model, key) == value)
    result = await db.execute(stmt)
    return result.scalar_one_or_none() is not None


async def get_list_with_count(
    db: AsyncSession,
    model: Type[T],
    filters: Optional[dict] = None,
    order_by: Optional[Any] = None,
    page: int = 1,
    limit: int = 20
) -> tuple[List[T], int]:
    """
    获取列表并返回总数

    Args:
        db: 异步数据库会话
        model: SQLAlchemy 模型类
        filters: 过滤条件字典
        order_by: 排序字段
        page: 页码
        limit: 每页数量

    Returns:
        tuple: (结果列表, 总数量)
    """
    stmt = select(model)

    if filters:
        for key, value in filters.items():
            if value is not None:
                stmt = stmt.filter(getattr(model, key) == value)

    if order_by is not None:
        stmt = stmt.order_by(order_by)

    return await paginate(db, stmt, page, limit)


async def get_issue_or_404(
    db: AsyncSession,
    repository_id: uuid.UUID,
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
    repository_id: uuid.UUID,
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
