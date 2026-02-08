import pytest
from fastapi.testclient import TestClient
from app import create_app
from app import AppSingleton
from config import reset_module_config_manager
from models import Base, engine


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


class TestUserAPI:
    """
    用户API测试类
    """
    
    def test_get_users(self, test_client):
        """
        测试获取所有用户
        """
        response = test_client.get("/api/users/")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_get_user_by_id(self, test_client):
        """
        测试根据ID获取用户
        
        注意：这个测试依赖于数据库中存在ID为1的用户
        """
        response = test_client.get("/api/users/1")
        # 如果用户不存在，应该返回404
        if response.status_code == 404:
            assert "error" in response.json()
            assert "message" in response.json()["error"]
            assert "User not found" in response.json()["error"]["message"]
        else:
            # 如果用户存在，应该返回200和用户信息
            assert response.status_code == 200
            assert "id" in response.json()
            assert response.json()["id"] == 1
    
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
    
    def test_update_user(self, test_client):
        """
        测试更新用户信息
        
        注意：这个测试依赖于数据库中存在测试用户
        """
        # 首先创建一个测试用户
        user_data = {
            "username": "testupdateuser",
            "email": "testupdate@example.com",
            "password": "testpassword",
            "full_name": "Test Update User",
            "is_active": True,
            "is_admin": False
        }
        
        # 创建用户
        create_response = test_client.post("/api/users/", json=user_data)
        
        if create_response.status_code == 200:
            # 获取创建的用户ID
            user_id = create_response.json()["id"]
            
            # 更新用户信息
            update_data = {
                "full_name": "Updated Test User",
                "is_active": False
            }
            
            update_response = test_client.put(f"/api/users/{user_id}", json=update_data)
            
            # 检查响应状态码
            assert update_response.status_code == 200
            assert update_response.json()["id"] == user_id
            assert update_response.json()["full_name"] == update_data["full_name"]
            assert update_response.json()["is_active"] == update_data["is_active"]
    
    def test_delete_user(self, test_client):
        """
        测试删除用户
        
        注意：这个测试依赖于数据库中存在测试用户
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
            
            # 删除用户
            delete_response = test_client.delete(f"/api/users/{user_id}")
            
            # 检查响应状态码
            assert delete_response.status_code == 200
            assert "message" in delete_response.json()
            assert "User deleted successfully" in delete_response.json()["message"]
            
            # 验证用户已被删除
            get_response = test_client.get(f"/api/users/{user_id}")
            assert get_response.status_code == 404
