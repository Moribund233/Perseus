"""
协作会话级角色覆盖层服务

发起人（仓库 owner/admin）对某文档内成员的权限覆盖 / 踢出状态进行读写。
覆盖优先于仓库角色与邀请 token（由 collab_internal_controller 强制执行）。
"""
import logging
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.collab_session_override import CollabSessionOverride

logger = logging.getLogger(__name__)

VALID_SCOPES = {"read", "write"}


async def get_override(
    db: AsyncSession, doc_key: str, user_id: UUID
) -> Optional[CollabSessionOverride]:
    """读取 (doc_key, user_id) 的会话覆盖；不存在返回 None。"""
    result = await db.execute(
        select(CollabSessionOverride).filter(
            CollabSessionOverride.doc_key == doc_key,
            CollabSessionOverride.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def _upsert(
    db: AsyncSession, doc_key: str, user_id: UUID, actor_id: Optional[UUID]
) -> CollabSessionOverride:
    override = await get_override(db, doc_key, user_id)
    if override is None:
        override = CollabSessionOverride(
            doc_key=doc_key, user_id=user_id, is_kicked=False
        )
        db.add(override)
    override.created_by = actor_id
    return override


async def set_permission(
    db: AsyncSession,
    doc_key: str,
    user_id: UUID,
    scope: Optional[str],
    actor_id: Optional[UUID] = None,
) -> CollabSessionOverride:
    """
    设置/清空成员的会话级权限覆盖。

    Args:
        scope: "read" | "write" 覆盖档位; None 表示清空权限覆盖（回落到仓库角色）

    Raises:
        ValueError: scope 非法
    """
    if scope is not None and scope not in VALID_SCOPES:
        raise ValueError(f"Invalid scope: {scope}. Valid scopes: {', '.join(sorted(VALID_SCOPES))}")

    override = await _upsert(db, doc_key, user_id, actor_id)
    override.scope = scope
    # 改权限即重新接纳（清掉此前的踢出标记）
    override.is_kicked = False
    await db.commit()
    await db.refresh(override)
    return override


async def kick(
    db: AsyncSession,
    doc_key: str,
    user_id: UUID,
    actor_id: Optional[UUID] = None,
) -> CollabSessionOverride:
    """把成员踢出该会话：清权限覆盖并置 is_kicked。"""
    override = await _upsert(db, doc_key, user_id, actor_id)
    override.scope = None
    override.is_kicked = True
    await db.commit()
    await db.refresh(override)
    return override


async def is_kicked(db: AsyncSession, doc_key: str, user_id: UUID) -> bool:
    """该成员是否已被踢出该会话。"""
    override = await get_override(db, doc_key, user_id)
    return bool(override and override.is_kicked)
