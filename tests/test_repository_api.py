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


class TestRepositoryAPI:
    """
    仓库API测试类
    """
    
    def test_get_repositories(self, test_client):
        """
        测试获取所有仓库
        """
        response = test_client.get("/api/repositories/")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_get_public_repositories(self, test_client):
        """
        测试获取所有公开仓库
        """
        response = test_client.get("/api/repositories/public")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_get_repository_by_id(self, test_client):
        """
        测试根据ID获取仓库
        """
        response = test_client.get("/api/repositories/1")
        # 如果仓库不存在，应该返回404
        if response.status_code == 404:
            assert "error" in response.json()
            assert "message" in response.json()["error"]
            assert "Repository not found" in response.json()["error"]["message"]
        else:
            # 如果仓库存在，应该返回200和仓库信息
            assert response.status_code == 200
            assert "id" in response.json()
            assert response.json()["id"] == 1
    
    def test_create_repository(self, test_client):
        """
        测试创建新仓库
        """
        # 首先创建一个测试用户
        user_data = {
            "username": "testowner",
            "email": "testowner@example.com",
            "password": "testpassword",
            "full_name": "Test Owner",
            "is_active": True,
            "is_admin": False
        }
        user_response = test_client.post("/api/users/", json=user_data)
        assert user_response.status_code == 200
        user_id = user_response.json()["id"]
        
        repo_data = {
            "name": "test-repo",
            "path": "/repos/test-repo",
            "description": "Test repository",
            "is_public": True,
            "owner_id": user_id,
            "default_branch": "master"
        }
        
        response = test_client.post("/api/repositories/", json=repo_data)
        
        # 检查响应状态码
        assert response.status_code == 200 or response.status_code == 409
        
        if response.status_code == 409:
            # 如果仓库路径已存在，应该返回409和错误信息
            assert "error" in response.json()
            assert "message" in response.json()["error"]
            assert "already exists" in response.json()["error"]["message"]
        else:
            # 如果仓库创建成功，应该返回200和仓库信息
            assert response.status_code == 200
            assert "id" in response.json()
            assert response.json()["name"] == repo_data["name"]
            assert response.json()["path"] == repo_data["path"]
            assert response.json()["is_public"] == repo_data["is_public"]
            assert response.json()["owner_id"] == repo_data["owner_id"]
            assert response.json()["default_branch"] == repo_data["default_branch"]
    
    def test_update_repository(self, test_client):
        """
        测试更新仓库信息
        """
        # 首先创建一个测试用户
        user_data = {
            "username": "testupdateowner",
            "email": "testupdateowner@example.com",
            "password": "testpassword",
            "full_name": "Test Update Owner",
            "is_active": True,
            "is_admin": False
        }
        user_response = test_client.post("/api/users/", json=user_data)
        assert user_response.status_code == 200
        user_id = user_response.json()["id"]
        
        # 创建测试仓库
        repo_data = {
            "name": "test-update-repo",
            "path": "/repos/test-update-repo",
            "description": "Test repository for update",
            "is_public": True,
            "owner_id": user_id,
            "default_branch": "master"
        }
        
        create_response = test_client.post("/api/repositories/", json=repo_data)
        assert create_response.status_code == 200
        repo_id = create_response.json()["id"]
        
        # 更新仓库信息
        update_data = {
            "description": "Updated test repository",
            "is_public": False
        }
        
        update_response = test_client.put(f"/api/repositories/{repo_id}", json=update_data)
        
        # 检查响应状态码
        assert update_response.status_code == 200
        assert update_response.json()["id"] == repo_id
        assert update_response.json()["description"] == update_data["description"]
        assert update_response.json()["is_public"] == update_data["is_public"]
    
    def test_delete_repository(self, test_client):
        """
        测试删除仓库
        """
        # 首先创建一个测试用户
        user_data = {
            "username": "testdeleteowner",
            "email": "testdeleteowner@example.com",
            "password": "testpassword",
            "full_name": "Test Delete Owner",
            "is_active": True,
            "is_admin": False
        }
        user_response = test_client.post("/api/users/", json=user_data)
        assert user_response.status_code == 200
        user_id = user_response.json()["id"]
        
        # 创建测试仓库
        repo_data = {
            "name": "test-delete-repo",
            "path": "/repos/test-delete-repo",
            "description": "Test repository for deletion",
            "is_public": True,
            "owner_id": user_id,
            "default_branch": "master"
        }
        
        create_response = test_client.post("/api/repositories/", json=repo_data)
        assert create_response.status_code == 200
        repo_id = create_response.json()["id"]
        
        # 删除仓库
        delete_response = test_client.delete(f"/api/repositories/{repo_id}")
        
        # 检查响应状态码
        assert delete_response.status_code == 200
        assert "message" in delete_response.json()
        assert "Repository deleted successfully" in delete_response.json()["message"]
        
        # 验证仓库已被删除
        get_response = test_client.get(f"/api/repositories/{repo_id}")
        assert get_response.status_code == 404
    
    def test_check_repository_access(self, test_client):
        """
        测试检查仓库访问权限
        """
        # 首先创建一个测试用户和仓库
        user_data = {
            "username": "testaccessuser",
            "email": "testaccessuser@example.com",
            "password": "testpassword",
            "full_name": "Test Access User",
            "is_active": True,
            "is_admin": False
        }
        user_response = test_client.post("/api/users/", json=user_data)
        assert user_response.status_code == 200
        user_id = user_response.json()["id"]
        
        # 创建测试仓库
        repo_data = {
            "name": "test-access-repo",
            "path": "/repos/test-access-repo",
            "description": "Test repository for access check",
            "is_public": True,
            "owner_id": user_id,
            "default_branch": "master"
        }
        repo_response = test_client.post("/api/repositories/", json=repo_data)
        assert repo_response.status_code == 200
        repo_id = repo_response.json()["id"]
        
        response = test_client.get(f"/api/repositories/{repo_id}/access?user_id={user_id}")
        # 检查响应状态码
        assert response.status_code == 200
        assert "has_access" in response.json()
        assert isinstance(response.json()["has_access"], bool)