"""
Pytest配置文件

添加项目根目录到Python路径，使测试能够导入项目模块
提供测试用的共享fixture

架构说明：
- 统一使用文件型 SQLite 数据库（test_perseus.db）
- 同步和异步测试共享同一数据库，确保数据一致性
- 使用 aiosqlite 驱动支持异步操作
"""
import sys
import os

# 将项目根目录添加到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import create_app, AppCache
from core.config import reset_module_config_manager
from models import Base
from services.token_service import create_access_token
from services.repository_service import _repo_exists_cache


# 统一测试数据库URL - 使用文件型 SQLite，同步和异步共享
TEST_DATABASE_URL = "sqlite:///./test_perseus.db"
TEST_ASYNC_URL = "sqlite+aiosqlite:///./test_perseus.db"


@pytest.fixture(scope="session")
def test_engine():
    """
    创建测试数据库引擎（会话级别）

    使用文件型 SQLite，确保同步和异步连接可以访问同一数据。

    Yields:
        Engine: SQLAlchemy引擎实例
    """
    # 设置测试数据库URL环境变量
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL
    os.environ["PERSEUS_STRESS_TEST"] = "false"

    # 重置配置管理器
    reset_module_config_manager()

    # 创建引擎 - 使用 StaticPool 避免连接池问题
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False
    )

    # 创建所有表
    Base.metadata.create_all(bind=engine)

    yield engine

    # 清理：删除所有表
    Base.metadata.drop_all(bind=engine)

    # 清理测试数据库文件（Windows 下 SQLite 文件锁可能导致删除失败，忽略即可）
    if os.path.exists("./test_perseus.db"):
        try:
            os.remove("./test_perseus.db")
        except PermissionError:
            pass  # Windows 文件锁释放延迟，下次运行会自动覆盖


@pytest.fixture
def db(test_engine):
    """
    创建同步数据库会话

    每次测试后自动清理数据，确保测试隔离。

    Args:
        test_engine: 测试数据库引擎

    Yields:
        Session: 数据库会话
    """
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestSessionLocal()

    try:
        yield session
    finally:
        session.rollback()
        # 清理：使用同一会话删除所有表中的数据
        from models import Base
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()
        session.close()
        # 清理物理仓库目录（测试间隔离）
        import shutil
        from utils.git_utils import get_repository_storage_path
        repo_root = get_repository_storage_path("")
        if repo_root and os.path.exists(repo_root):
            for item in os.listdir(repo_root):
                item_path = os.path.join(repo_root, item)
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                else:
                    os.remove(item_path)
        # 清理物理仓库存在状态缓存
        _repo_exists_cache.clear()


@pytest_asyncio.fixture
async def async_db(test_engine):
    """
    创建异步数据库会话

    使用与同步测试相同的数据库文件，确保数据一致性。
    每次测试后自动清理数据，确保测试隔离。

    Args:
        test_engine: 测试数据库引擎

    Yields:
        AsyncSession: 异步数据库会话
    """
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

    # 创建异步引擎，指向同一数据库文件
    async_engine = create_async_engine(
        TEST_ASYNC_URL,
        echo=False,
        future=True
    )

    async_session = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False
    )

    async with async_session() as session:
        yield session
        # 回滚任何未提交的更改
        await session.rollback()

        # 清理：使用同一会话删除所有表中的数据，确保测试隔离
        from models import Base
        for table in reversed(Base.metadata.sorted_tables):
            await session.execute(table.delete())
        await session.commit()

    await async_engine.dispose()

    # 清理物理仓库目录（测试间隔离）
    import shutil
    from utils.git_utils import get_repository_storage_path
    repo_root = get_repository_storage_path("")
    if repo_root and os.path.exists(repo_root):
        for item in os.listdir(repo_root):
            item_path = os.path.join(repo_root, item)
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
            else:
                os.remove(item_path)

    # 清理物理仓库存在状态缓存
    _repo_exists_cache.clear()


@pytest.fixture
def test_client(test_engine):
    """
    创建测试客户端

    Args:
        test_engine: 测试数据库引擎

    Yields:
        TestClient: FastAPI测试客户端
    """
    # 重置应用缓存和配置管理器
    AppCache.reset()
    reset_module_config_manager()

    # 创建应用和测试客户端
    app = create_app()
    client = TestClient(app)

    yield client


@pytest.fixture
def auth_headers(db):
    """
    创建认证用的请求头

    创建一个测试用户并生成访问令牌

    Args:
        db: 数据库会话

    Returns:
        dict: 包含Authorization头的字典
    """
    from models.user import User

    test_user = User(
        username="testuser",
        email="test@example.com",
        password="hashed_password_string",
        full_name="Test User",
        is_active=True,
        is_admin=False
    )

    db.add(test_user)
    db.commit()
    db.refresh(test_user)

    token = create_access_token({
        "sub": str(test_user.id),
        "username": test_user.username,
        "is_admin": test_user.is_admin
    })

    return {
        "Authorization": f"Bearer {token}"
    }


@pytest.fixture
def admin_headers(db):
    """
    创建管理员认证用的请求头

    Args:
        db: 数据库会话

    Returns:
        dict: 包含Authorization头的字典
    """
    from models.user import User

    admin_user = User(
        username="adminuser",
        email="admin@example.com",
        password="hashed_admin_password",
        full_name="Admin User",
        is_active=True,
        is_admin=True
    )

    db.add(admin_user)
    db.commit()
    db.refresh(admin_user)

    token = create_access_token({
        "sub": str(admin_user.id),
        "username": admin_user.username,
        "is_admin": admin_user.is_admin
    })

    return {
        "Authorization": f"Bearer {token}"
    }


# ============ 异步测试 Fixtures ============

@pytest_asyncio.fixture
async def async_test_user(async_db):
    """
    创建异步测试用户

    Args:
        async_db: 异步数据库会话

    Returns:
        User: 测试用户实例
    """
    from models.user import User

    user = User(
        username="async_testuser",
        email="async_test@example.com",
        password="hashed_password",
        full_name="Async Test User",
        is_active=True
    )
    async_db.add(user)
    await async_db.commit()
    await async_db.refresh(user)
    return user


@pytest_asyncio.fixture
async def async_test_user2(async_db):
    """创建第二个异步测试用户"""
    from models.user import User

    user = User(
        username="async_testuser2",
        email="async_test2@example.com",
        password="hashed_password",
        full_name="Async Test User 2",
        is_active=True
    )
    async_db.add(user)
    await async_db.commit()
    await async_db.refresh(user)
    return user


@pytest_asyncio.fixture
async def async_another_user(async_db):
    """创建另一个异步测试用户（用于权限测试）"""
    from models.user import User

    user = User(
        username="async_another",
        email="async_another@example.com",
        password="hashed_password",
        full_name="Another User",
        is_active=True
    )
    async_db.add(user)
    await async_db.commit()
    await async_db.refresh(user)
    return user


@pytest_asyncio.fixture
async def async_test_repo(async_db, async_test_user):
    """
    创建异步测试仓库

    Args:
        async_db: 异步数据库会话
        async_test_user: 异步测试用户

    Returns:
        Repository: 测试仓库实例
    """
    from models.repository import Repository

    repo = Repository(
        name="async-test-repo",
        description="Async Test repository",
        owner_id=async_test_user.id,
        is_public=True,
        path=f"{async_test_user.username}/async-test-repo"
    )
    async_db.add(repo)
    await async_db.commit()
    await async_db.refresh(repo)
    return repo
