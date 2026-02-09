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


class TestBranchAPI:
    """
    分支API测试类
    """
    
    def test_get_branches_with_auth(self, test_client, auth_headers):
        """
        测试获取仓库的所有分支（已认证）
        """
        repo_id = 1
        response = test_client.get(f"/api/repositories/{repo_id}/branches", headers=auth_headers)
        
        # 检查响应状态码
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_get_branches_without_auth(self, test_client):
        """
        测试获取仓库的所有分支（未认证）
        """
        repo_id = 1
        response = test_client.get(f"/api/repositories/{repo_id}/branches")
        
        # 检查响应状态码 - 应该返回403
        assert response.status_code == 403
    
    def test_get_branch_with_auth(self, test_client, auth_headers):
        """
        测试获取仓库的特定分支（已认证）
        """
        repo_id = 1
        branch_name = "master"
        
        response = test_client.get(f"/api/repositories/{repo_id}/branches/{branch_name}", headers=auth_headers)
        
        # 如果分支不存在，应该返回404
        if response.status_code == 404:
            assert "detail" in response.json()
            assert f"Branch '{branch_name}' not found" in response.json()["detail"]
        else:
            # 如果分支存在，应该返回200和分支信息
            assert response.status_code == 200
            assert "name" in response.json()
            assert response.json()["name"] == branch_name
            assert response.json()["repository_id"] == repo_id
    
    def test_get_branch_without_auth(self, test_client):
        """
        测试获取仓库的特定分支（未认证）
        
        注意：此端点不需要认证，但如果分支不存在会返回404
        """
        repo_id = 1
        branch_name = "master"
        
        response = test_client.get(f"/api/repositories/{repo_id}/branches/{branch_name}")
        
        # 此端点不需要认证，返回404表示分支不存在
        assert response.status_code == 404
    
    def test_create_branch_with_auth(self, test_client, auth_headers):
        """
        测试创建新分支（已认证）
        """
        # 首先确保存在测试仓库
        repo_id = 1
        branch_data = {
            "name": "test-branch",
            "is_protected": False,
            "is_default": False
        }
        
        response = test_client.post(f"/api/repositories/{repo_id}/branches", json=branch_data, headers=auth_headers)
        
        # 检查响应状态码
        assert response.status_code == 200 or response.status_code == 409
        
        if response.status_code == 409:
            # 如果分支名称已存在，应该返回409和错误信息
            assert "detail" in response.json()
            assert "already exists" in response.json()["detail"]
        else:
            # 如果分支创建成功，应该返回200和分支信息
            assert response.status_code == 200
            assert "name" in response.json()
            assert response.json()["name"] == branch_data["name"]
            assert response.json()["repository_id"] == repo_id
    
    def test_create_branch_without_auth(self, test_client):
        """
        测试创建新分支（未认证）
        """
        repo_id = 1
        branch_data = {
            "name": "test-branch",
            "is_protected": False,
            "is_default": False
        }
        
        response = test_client.post(f"/api/repositories/{repo_id}/branches", json=branch_data)
        
        # 检查响应状态码 - 应该返回403
        assert response.status_code == 403
    
    def test_update_branch_with_auth(self, test_client, auth_headers):
        """
        测试更新分支信息（已认证）
        """
        repo_id = 1
        branch_name = "master"
        branch_data = {
            "is_protected": True,
            "require_code_review": True
        }
        
        response = test_client.put(f"/api/repositories/{repo_id}/branches/{branch_name}", json=branch_data, headers=auth_headers)
        
        # 如果分支不存在，应该返回404
        if response.status_code == 404:
            assert "detail" in response.json()
            assert f"Branch '{branch_name}' not found" in response.json()["detail"]
        else:
            # 如果分支更新成功，应该返回200和更新后的分支信息
            assert response.status_code == 200
            assert response.json()["is_protected"] == branch_data["is_protected"]
            assert response.json()["require_code_review"] == branch_data["require_code_review"]
    
    def test_update_branch_without_auth(self, test_client):
        """
        测试更新分支信息（未认证）
        """
        repo_id = 1
        branch_name = "master"
        branch_data = {
            "is_protected": True,
            "require_code_review": True
        }
        
        response = test_client.put(f"/api/repositories/{repo_id}/branches/{branch_name}", json=branch_data)
        
        # 检查响应状态码 - 应该返回403
        assert response.status_code == 403
    
    def test_set_default_branch_with_auth(self, test_client, auth_headers):
        """
        测试设置默认分支（已认证）
        """
        import uuid
        unique_suffix = str(uuid.uuid4())[:8]
        
        # 创建测试用户
        user_data = {
            "username": f"testdefaultbranch-{unique_suffix}",
            "email": f"testdefaultbranch-{unique_suffix}@example.com",
            "password": "testpassword",
            "full_name": f"Test Default Branch User {unique_suffix}",
            "is_active": True,
            "is_admin": False
        }
        user_response = test_client.post("/api/users/", json=user_data)
        
        if user_response.status_code == 200:
            user_id = user_response.json()["id"]
            
            # 创建测试仓库
            repo_data = {
                "name": f"test-repo-default-{unique_suffix}",
                "path": f"/repos/test-repo-default-{unique_suffix}",
                "description": "Test repository for default branch",
                "is_public": True,
                "owner_id": user_id,
                "default_branch": "master"
            }
            repo_response = test_client.post("/api/repositories/", json=repo_data, headers=auth_headers)
            
            if repo_response.status_code == 200:
                repo_id = repo_response.json()["id"]
                
                # 创建测试分支
                branch_name = "master"
                branch_data = {
                    "name": branch_name,
                    "is_protected": False,
                    "require_code_review": False,
                    "require_status_checks": False
                }
                create_branch_response = test_client.post(f"/api/repositories/{repo_id}/branches", json=branch_data, headers=auth_headers)
                
                if create_branch_response.status_code == 200:
                    # 设置默认分支
                    set_default_response = test_client.put(f"/api/repositories/{repo_id}/branches/{branch_name}/default", headers=auth_headers)
                    
                    # 检查响应状态码
                    assert set_default_response.status_code == 200
                    assert "message" in set_default_response.json()
                    assert f"Default branch set to '{branch_name}'" in set_default_response.json()["message"]
    
    def test_set_default_branch_without_auth(self, test_client):
        """
        测试设置默认分支（未认证）
        """
        repo_id = 1
        branch_name = "master"
        
        response = test_client.put(f"/api/repositories/{repo_id}/branches/{branch_name}/default")
        
        # 检查响应状态码 - 应该返回403
        assert response.status_code == 403
    
    def test_protect_branch_with_auth(self, test_client, auth_headers):
        """
        测试保护分支（已认证）
        """
        repo_id = 1
        branch_name = "develop"
        protection_settings = {
            "require_code_review": True,
            "require_status_checks": False
        }
        
        response = test_client.put(f"/api/repositories/{repo_id}/branches/{branch_name}/protect", json=protection_settings, headers=auth_headers)
        
        # 如果分支不存在，应该返回404
        if response.status_code == 404:
            assert "detail" in response.json()
            assert f"Branch '{branch_name}' not found" in response.json()["detail"]
        else:
            # 如果分支保护成功，应该返回200和更新后的分支信息
            assert response.status_code == 200
            assert response.json()["is_protected"] == True
            assert response.json()["require_code_review"] == protection_settings["require_code_review"]
            assert response.json()["require_status_checks"] == protection_settings["require_status_checks"]
    
    def test_protect_branch_without_auth(self, test_client):
        """
        测试保护分支（未认证）
        """
        repo_id = 1
        branch_name = "develop"
        protection_settings = {
            "require_code_review": True,
            "require_status_checks": False
        }
        
        response = test_client.put(f"/api/repositories/{repo_id}/branches/{branch_name}/protect", json=protection_settings)
        
        # 检查响应状态码 - 应该返回403
        assert response.status_code == 403
    
    def test_unprotect_branch_with_auth(self, test_client, auth_headers):
        """
        测试取消分支保护（已认证）
        """
        repo_id = 1
        branch_name = "master"
        
        response = test_client.put(f"/api/repositories/{repo_id}/branches/{branch_name}/unprotect", headers=auth_headers)
        
        # 如果分支不存在，应该返回404
        if response.status_code == 404:
            assert "detail" in response.json()
            assert f"Branch '{branch_name}' not found" in response.json()["detail"]
        else:
            # 如果取消分支保护成功，应该返回200和更新后的分支信息
            assert response.status_code == 200
            assert response.json()["is_protected"] == False
            assert response.json()["require_code_review"] == False
            assert response.json()["require_status_checks"] == False
    
    def test_unprotect_branch_without_auth(self, test_client):
        """
        测试取消分支保护（未认证）
        """
        repo_id = 1
        branch_name = "master"
        
        response = test_client.put(f"/api/repositories/{repo_id}/branches/{branch_name}/unprotect")
        
        # 检查响应状态码 - 应该返回403
        assert response.status_code == 403
    
    def test_get_default_branch_with_auth(self, test_client, auth_headers):
        """
        测试获取默认分支（已认证）
        """
        repo_id = 1
        response = test_client.get(f"/api/repositories/{repo_id}/branches/default", headers=auth_headers)
        
        # 如果没有默认分支，应该返回404
        if response.status_code == 404:
            assert "detail" in response.json()
            assert "Default branch not found" in response.json()["detail"]
        else:
            # 如果存在默认分支，应该返回200和分支信息
            assert response.status_code == 200
            assert "is_default" in response.json()
            assert response.json()["is_default"] == True
    
    def test_get_default_branch_without_auth(self, test_client):
        """
        测试获取默认分支（未认证）
        
        注意：此端点不需要认证，但如果默认分支不存在会返回404
        """
        repo_id = 1
        response = test_client.get(f"/api/repositories/{repo_id}/branches/default")
        
        # 此端点不需要认证，返回404表示默认分支不存在
        assert response.status_code == 404
    
    def test_check_branch_protection_with_auth(self, test_client, auth_headers):
        """
        测试检查分支保护状态（已认证）
        """
        repo_id = 1
        branch_name = "master"
        
        response = test_client.get(f"/api/repositories/{repo_id}/branches/{branch_name}/protection", headers=auth_headers)
        
        # 如果分支不存在，应该返回404
        if response.status_code == 404:
            assert "detail" in response.json()
            assert f"Branch '{branch_name}' not found" in response.json()["detail"]
        else:
            # 如果分支存在，应该返回200和保护状态信息
            assert response.status_code == 200
            assert "is_protected" in response.json()
            assert "require_code_review" in response.json()
            assert "require_status_checks" in response.json()
    
    def test_check_branch_protection_without_auth(self, test_client):
        """
        测试检查分支保护状态（未认证）
        """
        repo_id = 1
        branch_name = "master"
        
        response = test_client.get(f"/api/repositories/{repo_id}/branches/{branch_name}/protection")
        
        # 此端点需要认证，返回403
        assert response.status_code == 403
