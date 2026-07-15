"""
Member Service 异步测试

测试仓库成员服务层的所有功能
"""
import uuid
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from models.repository_member import RepositoryMember
from models.repository import Repository
from models.user import User
from services import member_service
from core.exception import NotFoundException, ValidationException, ConflictException, AuthorizationException


@pytest_asyncio.fixture
async def test_member(async_db: AsyncSession, async_test_repo: Repository, async_test_user2: User):
    """创建测试成员"""
    member = RepositoryMember(
        repository_id=async_test_repo.id,
        user_id=async_test_user2.id,
        role="developer",
        is_active=True
    )
    async_db.add(member)
    await async_db.commit()
    await async_db.refresh(member)
    return member


@pytest.mark.asyncio
async def test_get_repository_members(async_db: AsyncSession, async_test_repo: Repository, test_member: RepositoryMember):
    """测试获取仓库成员列表"""
    members = await member_service.get_repository_members(async_test_repo.id, async_db)
    assert len(members) == 1
    assert members[0].user_id == test_member.user_id


@pytest.mark.asyncio
async def test_get_repository_members_empty(async_db: AsyncSession, async_test_repo: Repository):
    """测试获取空成员列表"""
    members = await member_service.get_repository_members(async_test_repo.id, async_db)
    assert len(members) == 0


@pytest.mark.asyncio
async def test_get_repository_member(async_db: AsyncSession, async_test_repo: Repository, test_member: RepositoryMember):
    """测试获取特定成员"""
    member = await member_service.get_repository_member(async_test_repo.id, test_member.user_id, async_db)
    assert member.user_id == test_member.user_id
    assert member.role == test_member.role


@pytest.mark.asyncio
async def test_get_repository_member_not_found(async_db: AsyncSession, async_test_repo: Repository):
    """测试获取不存在的成员"""
    with pytest.raises(NotFoundException):
        await member_service.get_repository_member(async_test_repo.id, uuid.uuid4(), async_db)


@pytest.mark.asyncio
async def test_add_repository_member(async_db: AsyncSession, async_test_repo: Repository, async_test_user2: User):
    """测试添加成员"""
    member_data = {
        "user_id": async_test_user2.id,
        "role": "developer",
        "is_active": True
    }
    member = await member_service.add_repository_member(async_test_repo.id, member_data, async_db)
    assert member.user_id == async_test_user2.id
    assert member.role == "developer"


@pytest.mark.asyncio
async def test_add_repository_member_missing_user_id(async_db: AsyncSession, async_test_repo: Repository):
    """测试添加成员缺少 user_id"""
    with pytest.raises(ValidationException):
        await member_service.add_repository_member(async_test_repo.id, {"role": "developer"}, async_db)


@pytest.mark.asyncio
async def test_add_repository_member_user_not_found(async_db: AsyncSession, async_test_repo: Repository):
    """测试添加不存在的用户"""
    with pytest.raises(NotFoundException):
        await member_service.add_repository_member(async_test_repo.id, {"user_id": uuid.uuid4()}, async_db)


@pytest.mark.asyncio
async def test_add_repository_member_already_exists(async_db: AsyncSession, async_test_repo: Repository, test_member: RepositoryMember):
    """测试添加已存在的成员"""
    with pytest.raises(ConflictException):
        await member_service.add_repository_member(
            async_test_repo.id,
            {"user_id": test_member.user_id, "role": "developer"},
            async_db
        )


@pytest.mark.asyncio
async def test_update_repository_member(async_db: AsyncSession, async_test_repo: Repository, test_member: RepositoryMember):
    """测试更新成员"""
    updated = await member_service.update_repository_member(
        async_test_repo.id, test_member.user_id,
        {"role": "admin", "is_active": True},
        async_db
    )
    assert updated.role == "admin"


@pytest.mark.asyncio
async def test_update_repository_member_not_found(async_db: AsyncSession, async_test_repo: Repository):
    """测试更新不存在的成员"""
    with pytest.raises(NotFoundException):
        await member_service.update_repository_member(
            async_test_repo.id, uuid.uuid4(), {"role": "admin"}, async_db
        )


@pytest.mark.asyncio
async def test_remove_repository_member(async_db: AsyncSession, async_test_repo: Repository, test_member: RepositoryMember):
    """测试删除成员"""
    result = await member_service.remove_repository_member(
        async_test_repo.id, test_member.user_id, async_db
    )
    assert result == {"message": "Member removed successfully"}


@pytest.mark.asyncio
async def test_remove_repository_member_not_found(async_db: AsyncSession, async_test_repo: Repository):
    """测试删除不存在的成员"""
    with pytest.raises(NotFoundException):
        await member_service.remove_repository_member(async_test_repo.id, uuid.uuid4(), async_db)


@pytest.mark.asyncio
async def test_update_member_role(async_db: AsyncSession, async_test_repo: Repository, test_member: RepositoryMember):
    """测试更新成员角色"""
    updated = await member_service.update_member_role(
        async_test_repo.id, test_member.user_id, "admin", async_db
    )
    assert updated.role == "admin"


@pytest.mark.asyncio
async def test_update_member_role_invalid(async_db: AsyncSession, async_test_repo: Repository, test_member: RepositoryMember):
    """测试更新无效角色"""
    with pytest.raises(ValidationException):
        await member_service.update_member_role(
            async_test_repo.id, test_member.user_id, "invalid_role", async_db
        )


@pytest.mark.asyncio
async def test_check_member_permission_owner(async_db: AsyncSession, async_test_repo: Repository, async_test_user: User):
    """测试检查所有者权限"""
    result = await member_service.check_member_permission(
        async_test_repo.id, async_test_user.id, "owner", async_db
    )
    assert result is True


@pytest.mark.asyncio
async def test_check_member_permission_member(async_db: AsyncSession, async_test_repo: Repository, test_member: RepositoryMember):
    """测试检查成员权限"""
    result = await member_service.check_member_permission(
        async_test_repo.id, test_member.user_id, "readonly", async_db
    )
    assert result is True


@pytest.mark.asyncio
async def test_check_member_permission_no_member(async_db: AsyncSession, async_test_repo: Repository):
    """测试检查非成员权限"""
    result = await member_service.check_member_permission(
        async_test_repo.id, uuid.uuid4(), "readonly", async_db
    )
    assert result is False


@pytest.mark.asyncio
async def test_check_member_permission_repo_not_found(async_db: AsyncSession):
    """测试检查不存在仓库的权限"""
    with pytest.raises(NotFoundException):
        await member_service.check_member_permission(uuid.uuid4(), uuid.uuid4(), "readonly", async_db)


@pytest.mark.asyncio
async def test_get_user_repositories(async_db: AsyncSession, async_test_repo: Repository, test_member: RepositoryMember):
    """测试获取用户参与的仓库"""
    repos = await member_service.get_user_repositories(test_member.user_id, async_db)
    assert len(repos) == 1
    assert repos[0].id == async_test_repo.id


@pytest.mark.asyncio
async def test_activate_repository_member(async_db: AsyncSession, async_test_repo: Repository, test_member: RepositoryMember):
    """测试激活成员"""
    # 先停用
    await member_service.deactivate_repository_member(async_test_repo.id, test_member.user_id, async_db)
    # 再激活
    activated = await member_service.activate_repository_member(
        async_test_repo.id, test_member.user_id, async_db
    )
    assert activated.is_active is True


@pytest.mark.asyncio
async def test_deactivate_repository_member(async_db: AsyncSession, async_test_repo: Repository, test_member: RepositoryMember):
    """测试停用成员"""
    deactivated = await member_service.deactivate_repository_member(
        async_test_repo.id, test_member.user_id, async_db
    )
    assert deactivated.is_active is False


@pytest.mark.asyncio
async def test_deactivate_repository_member_owner(async_db: AsyncSession, async_test_repo: Repository, async_test_user: User):
    """测试停用所有者（应该失败）"""
    # 创建 owner 角色成员
    member = RepositoryMember(
        repository_id=async_test_repo.id,
        user_id=async_test_user.id,
        role="owner",
        is_active=True
    )
    async_db.add(member)
    await async_db.commit()

    with pytest.raises(AuthorizationException):
        await member_service.deactivate_repository_member(async_test_repo.id, async_test_user.id, async_db)
