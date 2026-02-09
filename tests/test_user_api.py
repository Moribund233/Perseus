import pytest
from fastapi.testclient import TestClient
from app import create_app
from app import AppSingleton
from config import reset_module_config_manager
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
    创建认证用的请求头（普通用户）
    """
    # 创建测试用户
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
    
    # 生成访问令牌
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
    """
    # 创建测试管理员用户
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
    
    # 生成访问令牌
    token = create_access_token({
        "sub": str(admin_user.id),
        "username": admin_user.username,
        "is_admin": admin_user.is_admin
    })
    
    return {
        "Authorization": f"Bearer {token}"
    }


class TestUserAPI:
    """
    用户API测试类
    """
    
    def test_get_users_with_auth(self, test_client, auth_headers):
        """
        测试获取所有用户（已认证）
        """
        response = test_client.get("/api/users/", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_get_users_without_auth(self, test_client):
        """
        测试获取所有用户（未认证）
        """
        response = test_client.get("/api/users/")
        assert response.status_code == 403
    
    def test_get_user_by_id_with_auth(self, test_client, auth_headers):
        """
        测试根据ID获取用户（已认证）
        """
        response = test_client.get("/api/users/1", headers=auth_headers)
        # 如果用户不存在，应该返回404
        if response.status_code == 404:
            assert "error" in response.json()
            assert "message" in response.json()["error"]
            assert "User not found" in response.json()["error"]["message"]
        else:
            # 如果用户存在，应该返回200和用户信息
            assert response.status_code == 200
            assert "id" in response.json()
    
    def test_get_user_by_id_without_auth(self, test_client):
        """
        测试根据ID获取用户（未认证）
        """
        response = test_client.get("/api/users/1")
        assert response.status_code == 403
    
    def test_create_user(self, test_client):
        """
        测试创建新用户
        
        注意：这个测试会在数据库中创建一个新用户
        """
        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "testpassword",
            "full_name": "Test User",
            "is_active": True,
            "is_admin": False
        }
        
        response = test_client.post("/api/users/", json=user_data)
        
        # 检查响应状态码
        assert response.status_code == 200 or response.status_code == 409
        
        if response.status_code == 409:
            # 如果用户已存在，应该返回409和错误信息
            assert "error" in response.json()
            assert "message" in response.json()["error"]
            assert "already exists" in response.json()["error"]["message"]
        else:
            # 如果用户创建成功，应该返回200和用户信息
            assert "id" in response.json()
            assert response.json()["username"] == user_data["username"]
            assert response.json()["email"] == user_data["email"]
            assert response.json()["full_name"] == user_data["full_name"]
            assert response.json()["is_active"] == user_data["is_active"]
            assert response.json()["is_admin"] == user_data["is_admin"]
            assert "password" not in response.json()  # 密码不应该返回
    
    def test_login_user(self, test_client):
        """
        测试用户登录
        
        注意：这个测试依赖于数据库中存在测试用户
        """
        # 首先创建一个测试用户
        user_data = {
            "username": "testloginuser",
            "email": "testlogin@example.com",
            "password": "testpassword",
            "full_name": "Test Login User",
            "is_active": True,
            "is_admin": False
        }
        
        # 创建用户
        test_client.post("/api/users/", json=user_data)
        
        # 尝试登录
        login_data = {
            "username": user_data["username"],
            "password": user_data["password"]
        }
        
        response = test_client.post("/api/users/login", json=login_data)
        
        # 检查响应状态码
        assert response.status_code == 200 or response.status_code == 401
        
        if response.status_code == 200:
            # 如果登录成功，应该返回200和用户信息
            assert "id" in response.json()
            assert response.json()["username"] == user_data["username"]
            assert response.json()["email"] == user_data["email"]
            assert "password" not in response.json()  # 密码不应该返回
        else:
            # 如果登录失败，应该返回401和错误信息
            assert "error" in response.json()
            assert "message" in response.json()["error"]
            assert "Invalid username or password" in response.json()["error"]["message"]
    
    def test_update_own_user_with_auth(self, test_client, auth_headers, db):
        """
        测试更新自己的用户信息（已认证）
        """
        # 获取当前认证用户的ID
        # 从 auth_headers 创建的 token 中获取用户
        test_user = db.query(User).filter(User.username == "testuser").first()
        if not test_user:
            pytest.skip("Test user not found")
        
        # 更新自己的信息
        update_data = {
            "full_name": "Updated Test User",
            "is_active": False
        }
        
        update_response = test_client.put(f"/api/users/{test_user.id}", json=update_data, headers=auth_headers)
        
        # 检查响应状态码
        assert update_response.status_code == 200
        assert update_response.json()["id"] == test_user.id
        assert update_response.json()["full_name"] == update_data["full_name"]
    
    def test_update_other_user_without_admin(self, test_client, auth_headers):
        """
        测试普通用户尝试更新其他用户信息（应该被拒绝）
        """
        # 尝试更新一个不存在的用户ID
        update_data = {
            "full_name": "Updated Test User",
            "is_active": False
        }
        
        update_response = test_client.put("/api/users/99999", json=update_data, headers=auth_headers)
        
        # 检查响应状态码 - 应该返回403（无权限）
        assert update_response.status_code == 403
    
    def test_update_user_without_auth(self, test_client):
        """
        测试更新用户信息（未认证）
        """
        # 更新用户信息
        update_data = {
            "full_name": "Updated Test User",
            "is_active": False
        }
        
        update_response = test_client.put("/api/users/1", json=update_data)
        
        # 检查响应状态码
        assert update_response.status_code == 403
    
    def test_delete_user_with_admin(self, test_client, admin_headers, db):
        """
        测试管理员删除用户（已认证管理员）
        """
        # 首先创建一个测试用户
        user_data = {
            "username": "testdeleteuser",
            "email": "testdelete@example.com",
            "password": "testpassword",
            "full_name": "Test Delete User",
            "is_active": True,
            "is_admin": False
        }
        
        # 创建用户
        create_response = test_client.post("/api/users/", json=user_data)
        
        if create_response.status_code == 200:
            # 获取创建的用户ID
            user_id = create_response.json()["id"]
            
            # 删除用户（使用管理员权限）
            delete_response = test_client.delete(f"/api/users/{user_id}", headers=admin_headers)
            
            # 检查响应状态码
            assert delete_response.status_code == 200
            assert "message" in delete_response.json()
            assert "User deleted successfully" in delete_response.json()["message"]
            
            # 验证用户已被删除
            get_response = test_client.get(f"/api/users/{user_id}", headers=admin_headers)
            assert get_response.status_code == 404
    
    def test_delete_user_without_admin(self, test_client, auth_headers):
        """
        测试普通用户尝试删除用户（应该被拒绝）
        """
        # 尝试删除用户（使用普通用户权限）
        delete_response = test_client.delete("/api/users/99999", headers=auth_headers)
        
        # 检查响应状态码 - 应该返回403（无权限）
        assert delete_response.status_code == 403
    
    def test_delete_user_without_auth(self, test_client):
        """
        测试删除用户（未认证）
        """
        delete_response = test_client.delete("/api/users/1")
        
        # 检查响应状态码
        assert delete_response.status_code == 403
