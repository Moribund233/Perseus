"""
Pytest配置文件

添加项目根目录到Python路径，使测试能够导入项目模块
提供测试用的共享fixture
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
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import create_app, AppSingleton
from core.config import reset_module_config_manager
from models import Base, init_engine, get_engine, SessionLocal
from models.user import User
from services.token_service import create_access_token


# 测试数据库URL（使用内存SQLite）
TEST_DATABASE_URL = "sqlite:///./test_perseus.db"


@pytest.fixture(scope="session")
def test_engine():
    """
    创建测试数据库引擎（会话级别）
    
    Yields:
        Engine: SQLAlchemy引擎实例
    """
    # 设置测试数据库URL环境变量
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL
    os.environ["PERSEUS_STRESS_TEST"] = "false"
    
    # 重置配置管理器
    reset_module_config_manager()
    
    # 初始化引擎
    engine = init_engine()
    
    # 创建所有表
    Base.metadata.create_all(bind=engine)
    
    yield engine
    
    # 清理：删除所有表
    Base.metadata.drop_all(bind=engine)
    
    # 清理测试数据库文件
    if os.path.exists("./test_perseus.db"):
        os.remove("./test_perseus.db")


@pytest.fixture
def db(test_engine):
    """
    创建数据库会话
    
    Args:
        test_engine: 测试数据库引擎
        
    Yields:
        Session: 数据库会话
    """
    # 创建新的会话
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestSessionLocal()
    
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def test_client(test_engine):
    """
    创建测试客户端
    
    Args:
        test_engine: 测试数据库引擎
        
    Yields:
        TestClient: FastAPI测试客户端
    """
    # 重置应用单例和配置管理器
    app_singleton = AppSingleton()
    app_singleton.reset()
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
    # 创建测试用户
    test_user = User(
        username="testuser",
        email="test@example.com",
        password="hashed_password_string",  # 直接设置密码字段
        full_name="Test User",
        is_active=True,
        is_admin=False
    )
    
    db.add(test_user)
    db.commit()
    db.refresh(test_user)
    
    # 生成访问令牌 - 包含所有必要字段
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
    
    创建一个测试管理员用户并生成访问令牌
    
    Args:
        db: 数据库会话
        
    Returns:
        dict: 包含Authorization头的字典
    """
    # 创建测试管理员用户
    admin_user = User(
        username="adminuser",
        email="admin@example.com",
        password="hashed_admin_password",  # 直接设置密码字段
        full_name="Admin User",
        is_active=True,
        is_admin=True
    )
    
    db.add(admin_user)
    db.commit()
    db.refresh(admin_user)
    
    # 生成访问令牌 - 包含所有必要字段
    token = create_access_token({
        "sub": str(admin_user.id),
        "username": admin_user.username,
        "is_admin": admin_user.is_admin
    })
    
    return {
        "Authorization": f"Bearer {token}"
    }


@pytest_asyncio.fixture
async def async_db():
    """
    创建异步数据库会话（用于异步服务测试）
    
    Yields:
        AsyncSession: 异步数据库会话
    """
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    
    # 使用内存数据库进行异步测试
    async_engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
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
    
    # 创建所有表
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with async_session() as session:
        yield session
    
    # 清理
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await async_engine.dispose()
