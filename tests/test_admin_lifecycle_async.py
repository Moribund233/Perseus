"""
管理员生命周期功能测试

覆盖：
- admin_reset_password：管理员重置密码（权限/校验/404）
- update_user 的 is_admin 守卫：非管理员禁止赋值、自降级禁止、晋升/降至生效
- delete_user：禁止删除最后一个管理员
"""
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from models import User
from services import user_service
from core.exception import NotFoundException, ValidationException, AuthorizationException


async def _make_user(db: AsyncSession, **kwargs) -> User:
    """创建用户并返回"""
    defaults = dict(
        username=f"user_{uuid.uuid4().hex[:8]}",
        email=f"{uuid.uuid4().hex[:8]}@example.com",
        password="hashed_password_string",
        is_active=True,
        is_admin=False,
    )
    defaults.update(kwargs)
    user = User(**defaults)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest.mark.asyncio
async def test_admin_reset_password_success(async_db: AsyncSession):
    """管理员重置普通用户密码：新密码立即生效"""
    target = await _make_user(async_db, password=user_service.get_password_hash("old-pass-123"))
    admin = await _make_user(async_db, is_admin=True)

    result = await user_service.admin_reset_password(target.id, "fresh-pass-456", async_db, admin)

    assert result["message"] == "Password reset successfully"
    await async_db.refresh(target)
    assert user_service.verify_password("fresh-pass-456", target.password)
    assert not user_service.verify_password("old-pass-123", target.password)


@pytest.mark.asyncio
async def test_admin_reset_password_requires_admin(async_db: AsyncSession):
    """非管理员调用重置密码接口被拒绝"""
    target = await _make_user(async_db)
    non_admin = await _make_user(async_db)

    with pytest.raises(AuthorizationException) as exc:
        await user_service.admin_reset_password(target.id, "new-pass-123", async_db, non_admin)
    assert exc.value.error_code == "admin_required"


@pytest.mark.asyncio
async def test_admin_reset_password_rejects_short_password(async_db: AsyncSession):
    """新密码过短抛出验证异常"""
    target = await _make_user(async_db)
    admin = await _make_user(async_db, is_admin=True)

    with pytest.raises(ValidationException) as exc:
        await user_service.admin_reset_password(target.id, "12345", async_db, admin)
    assert exc.value.error_code == "user_password_too_short"


@pytest.mark.asyncio
async def test_admin_reset_password_user_not_found(async_db: AsyncSession):
    """目标用户不存在抛出 404"""
    admin = await _make_user(async_db, is_admin=True)

    with pytest.raises(NotFoundException) as exc:
        await user_service.admin_reset_password(uuid.uuid4(), "new-pass-123", async_db, admin)
    assert exc.value.error_code == "user_not_found"


@pytest.mark.asyncio
async def test_update_user_non_admin_cannot_set_admin_role(async_db: AsyncSession):
    """非管理员在自己的资料里携带 is_admin 被拒绝"""
    actor = await _make_user(async_db)

    with pytest.raises(AuthorizationException) as exc:
        await user_service.update_user(
            actor.id, {"is_admin": True}, async_db, actor
        )
    assert exc.value.error_code == "admin_role_forbidden"


@pytest.mark.asyncio
async def test_update_user_admin_can_promote_other_user(async_db: AsyncSession):
    """管理员可将普通用户晋升为管理员"""
    target = await _make_user(async_db, username="promote_me", email="promote@example.com")
    admin = await _make_user(async_db, is_admin=True)

    updated = await user_service.update_user(
        target.id, {"is_admin": True}, async_db, admin
    )

    assert updated["is_admin"] is True
    await async_db.refresh(target)
    assert target.is_admin is True


@pytest.mark.asyncio
async def test_update_user_self_demotion_forbidden(async_db: AsyncSession):
    """管理员不能把自己降级为普通用户"""
    admin = await _make_user(async_db, is_admin=True)

    with pytest.raises(AuthorizationException) as exc:
        await user_service.update_user(
            admin.id, {"is_admin": False}, async_db, admin
        )
    assert exc.value.error_code == "admin_self_demote_forbidden"


@pytest.mark.asyncio
async def test_update_user_admin_can_demote_other_admin(async_db: AsyncSession):
    """存在多个管理员时，可降级其他管理员"""
    admin_a = await _make_user(async_db, is_admin=True)
    admin_b = await _make_user(async_db, is_admin=True)

    updated = await user_service.update_user(
        admin_b.id, {"is_admin": False}, async_db, admin_a
    )

    assert updated["is_admin"] is False
    await async_db.refresh(admin_b)
    assert admin_b.is_admin is False


@pytest.mark.asyncio
async def test_delete_last_admin_forbidden(async_db: AsyncSession):
    """禁止删除系统中最后一个管理员"""
    sole_admin = await _make_user(async_db, is_admin=True)

    with pytest.raises(ValidationException) as exc:
        await user_service.delete_user(sole_admin.id, async_db)
    assert exc.value.error_code == "admin_delete_last_forbidden"


@pytest.mark.asyncio
async def test_update_user_implicit_null_is_admin_is_ignored(async_db: AsyncSession):
    """显式传 null 的 is_admin 不改变管理员状态（不落入 None）"""
    admin = await _make_user(async_db, is_admin=True)
    other = await _make_user(async_db, is_admin=True)

    updated = await user_service.update_user(
        other.id, {"is_admin": None}, async_db, admin
    )

    assert updated["is_admin"] is True
    await async_db.refresh(other)
    assert other.is_admin is True