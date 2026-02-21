"""
Member Service 异步测试

测试仓库成员服务层的所有功能
"""
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from models import BaseModel
from models.repository_member import RepositoryMember
from models.repository import Repository
from models.user import User
from services import member_service
from exception import NotFoundException, ValidationException, ConflictException, AuthorizationException

# 使用内存数据库进行测试
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def db():
    """创建测试数据库会话"""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.create_all)

    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def test_user(db: AsyncSession):
    """创建测试用户"""
    user = User(
        username="testuser",
        email="test@example.com",
        password="hashed_password",
        full_name="Test User",
        is_active=True
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_user2(db: AsyncSession):
    """创建第二个测试用户"""
    user = User(
        username="testuser2",
        email="test2@example.com",
        password="hashed_password2",
        full_name="Test User 2",
        is_active=True
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_repo(db: AsyncSession, test_user: User):
    """创建测试仓库"""
    repo = Repository(
        name="test-repo",
        description="Test repository",
        owner_id=test_user.id,
        is_public=True,
        path="testuser/test-repo"
    )
    db.add(repo)
    await db.commit()
    await db.refresh(repo)
    return repo


@pytest_asyncio.fixture
async def test_member(db: AsyncSession, test_repo: Repository, test_user2: User):
    """创建测试成员"""
    member = RepositoryMember(
        repository_id=test_repo.id,
        user_id=test_user2.id,
        role="developer",
        is_active=True
    )
    db.add(member)
    await db.commit()
    await db.refresh(member)
    return member


@pytest.mark.asyncio
async def test_get_repository_members(db: AsyncSession, test_repo: Repository, test_member: RepositoryMember):
    """测试获取仓库成员列表"""
    members = await member_service.get_repository_members(test_repo.id, db)
    assert len(members) == 1
    assert members[0].user_id == test_member.user_id


@pytest.mark.asyncio
async def test_get_repository_members_empty(db: AsyncSession, test_repo: Repository):
    """测试获取空成员列表"""
    members = await member_service.get_repository_members(test_repo.id, db)
    assert len(members) == 0


@pytest.mark.asyncio
async def test_get_repository_member(db: AsyncSession, test_repo: Repository, test_member: RepositoryMember):
    """测试获取特定成员"""
    member = await member_service.get_repository_member(test_repo.id, test_member.user_id, db)
    assert member.user_id == test_member.user_id
    assert member.role == test_member.role


@pytest.mark.asyncio
async def test_get_repository_member_not_found(db: AsyncSession, test_repo: Repository):
    """测试获取不存在的成员"""
    with pytest.raises(NotFoundException):
        await member_service.get_repository_member(test_repo.id, 999, db)


@pytest.mark.asyncio
async def test_add_repository_member(db: AsyncSession, test_repo: Repository, test_user2: User):
    """测试添加成员"""
    member_data = {
        "user_id": test_user2.id,
        "role": "developer",
        "is_active": True
    }
    member = await member_service.add_repository_member(test_repo.id, member_data, db)
    assert member.user_id == test_user2.id
    assert member.role == "developer"


@pytest.mark.asyncio
async def test_add_repository_member_missing_user_id(db: AsyncSession, test_repo: Repository):
    """测试添加成员缺少 user_id"""
    with pytest.raises(ValidationException):
        await member_service.add_repository_member(test_repo.id, {"role": "developer"}, db)


@pytest.mark.asyncio
async def test_add_repository_member_user_not_found(db: AsyncSession, test_repo: Repository):
    """测试添加不存在的用户"""
    with pytest.raises(NotFoundException):
        await member_service.add_repository_member(test_repo.id, {"user_id": 999}, db)


@pytest.mark.asyncio
async def test_add_repository_member_already_exists(db: AsyncSession, test_repo: Repository, test_member: RepositoryMember):
    """测试添加已存在的成员"""
    with pytest.raises(ConflictException):
        await member_service.add_repository_member(
            test_repo.id,
            {"user_id": test_member.user_id, "role": "developer"},
            db
        )


@pytest.mark.asyncio
async def test_update_repository_member(db: AsyncSession, test_repo: Repository, test_member: RepositoryMember):
    """测试更新成员"""
    updated = await member_service.update_repository_member(
        test_repo.id, test_member.user_id,
        {"role": "admin", "is_active": True},
        db
    )
    assert updated.role == "admin"


@pytest.mark.asyncio
async def test_update_repository_member_not_found(db: AsyncSession, test_repo: Repository):
    """测试更新不存在的成员"""
    with pytest.raises(NotFoundException):
        await member_service.update_repository_member(
            test_repo.id, 999, {"role": "admin"}, db
        )


@pytest.mark.asyncio
async def test_remove_repository_member(db: AsyncSession, test_repo: Repository, test_member: RepositoryMember):
    """测试删除成员"""
    result = await member_service.remove_repository_member(
        test_repo.id, test_member.user_id, db
    )
    assert result == {"message": "Member removed successfully"}


@pytest.mark.asyncio
async def test_remove_repository_member_not_found(db: AsyncSession, test_repo: Repository):
    """测试删除不存在的成员"""
    with pytest.raises(NotFoundException):
        await member_service.remove_repository_member(test_repo.id, 999, db)


@pytest.mark.asyncio
async def test_update_member_role(db: AsyncSession, test_repo: Repository, test_member: RepositoryMember):
    """测试更新成员角色"""
    updated = await member_service.update_member_role(
        test_repo.id, test_member.user_id, "admin", db
    )
    assert updated.role == "admin"


@pytest.mark.asyncio
async def test_update_member_role_invalid(db: AsyncSession, test_repo: Repository, test_member: RepositoryMember):
    """测试更新无效角色"""
    with pytest.raises(ValidationException):
        await member_service.update_member_role(
            test_repo.id, test_member.user_id, "invalid_role", db
        )


@pytest.mark.asyncio
async def test_check_member_permission_owner(db: AsyncSession, test_repo: Repository, test_user: User):
    """测试检查所有者权限"""
    result = await member_service.check_member_permission(
        test_repo.id, test_user.id, "owner", db
    )
    assert result is True


@pytest.mark.asyncio
async def test_check_member_permission_member(db: AsyncSession, test_repo: Repository, test_member: RepositoryMember):
    """测试检查成员权限"""
    result = await member_service.check_member_permission(
        test_repo.id, test_member.user_id, "readonly", db
    )
    assert result is True


@pytest.mark.asyncio
async def test_check_member_permission_no_member(db: AsyncSession, test_repo: Repository):
    """测试检查非成员权限"""
    result = await member_service.check_member_permission(
        test_repo.id, 999, "readonly", db
    )
    assert result is False


@pytest.mark.asyncio
async def test_check_member_permission_repo_not_found(db: AsyncSession):
    """测试检查不存在仓库的权限"""
    with pytest.raises(NotFoundException):
        await member_service.check_member_permission(999, 1, "readonly", db)


@pytest.mark.asyncio
async def test_get_user_repositories(db: AsyncSession, test_repo: Repository, test_member: RepositoryMember):
    """测试获取用户参与的仓库"""
    repos = await member_service.get_user_repositories(test_member.user_id, db)
    assert len(repos) == 1
    assert repos[0].id == test_repo.id


@pytest.mark.asyncio
async def test_activate_repository_member(db: AsyncSession, test_repo: Repository, test_member: RepositoryMember):
    """测试激活成员"""
    # 先停用
    await member_service.deactivate_repository_member(test_repo.id, test_member.user_id, db)
    # 再激活
    activated = await member_service.activate_repository_member(
        test_repo.id, test_member.user_id, db
    )
    assert activated.is_active is True


@pytest.mark.asyncio
async def test_deactivate_repository_member(db: AsyncSession, test_repo: Repository, test_member: RepositoryMember):
    """测试停用成员"""
    deactivated = await member_service.deactivate_repository_member(
        test_repo.id, test_member.user_id, db
    )
    assert deactivated.is_active is False


@pytest.mark.asyncio
async def test_deactivate_repository_member_owner(db: AsyncSession, test_repo: Repository, test_user: User):
    """测试停用所有者（应该失败）"""
    # 创建 owner 角色成员
    member = RepositoryMember(
        repository_id=test_repo.id,
        user_id=test_user.id,
        role="owner",
        is_active=True
    )
    db.add(member)
    await db.commit()

    with pytest.raises(AuthorizationException):
        await member_service.deactivate_repository_member(test_repo.id, test_user.id, db)
