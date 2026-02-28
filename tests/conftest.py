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
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import create_app, AppSingleton
from core.config import reset_module_config_manager
from models import Base, engine, SessionLocal
from models.user import User
from services.token_service import create_access_token


@pytest.fixture
def db():
    """
    创建数据库会话
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_client():
    """
    创建测试客户端
    
    Yields:
        TestClient: FastAPI测试客户端
    """
    # 重置应用单例和配置管理器
    app_singleton = AppSingleton()
    app_singleton.reset()
    reset_module_config_manager()
    
    # 创建所有数据库表
    Base.metadata.create_all(bind=engine)
    
    # 创建应用和测试客户端
    app = create_app()
    client = TestClient(app)
    
    yield client
    
    # 清理数据库表
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def auth_headers(db):
    """
    创建认证用的请求头
    
    创建一个测试用户并生成访问令牌
    
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
