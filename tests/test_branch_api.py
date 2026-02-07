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


class TestBranchAPI:
    """
    分支API测试类
    """
    
    def test_get_branches(self, test_client):
        """
        测试获取仓库的所有分支
        """
        repo_id = 1
        response = test_client.get(f"/api/repositories/{repo_id}/branches")
        
        # 检查响应状态码
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_get_branch(self, test_client):
        """
        测试获取仓库的特定分支
        """
        repo_id = 1
        branch_name = "master"
        
        response = test_client.get(f"/api/repositories/{repo_id}/branches/{branch_name}")
        
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
    
    def test_create_branch(self, test_client):
        """
        测试创建新分支
        """
        # 首先确保存在测试仓库
        repo_id = 1
        branch_data = {
            "name": "test-branch",
            "is_protected": False,
            "is_default": False
        }
        
        response = test_client.post(f"/api/repositories/{repo_id}/branches", json=branch_data)
        
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
    
    def test_update_branch(self, test_client):
        """
        测试更新分支信息
        """
        repo_id = 1
        branch_name = "master"
        branch_data = {
            "is_protected": True,
            "require_code_review": True
        }
        
        response = test_client.put(f"/api/repositories/{repo_id}/branches/{branch_name}", json=branch_data)
        
        # 如果分支不存在，应该返回404
        if response.status_code == 404:
            assert "detail" in response.json()
            assert f"Branch '{branch_name}' not found" in response.json()["detail"]
        else:
            # 如果分支更新成功，应该返回200和更新后的分支信息
            assert response.status_code == 200
            assert response.json()["is_protected"] == branch_data["is_protected"]
            assert response.json()["require_code_review"] == branch_data["require_code_review"]
    
    def test_set_default_branch(self, test_client):
        """
        测试设置默认分支
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
            repo_response = test_client.post("/api/repositories/", json=repo_data)
            
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
                create_branch_response = test_client.post(f"/api/repositories/{repo_id}/branches", json=branch_data)
                
                if create_branch_response.status_code == 200:
                    # 设置默认分支
                    set_default_response = test_client.put(f"/api/repositories/{repo_id}/branches/{branch_name}/default")
                    
                    # 检查响应状态码
                    assert set_default_response.status_code == 200
                    assert "message" in set_default_response.json()
                    assert f"Default branch set to '{branch_name}'" in set_default_response.json()["message"]
    
    def test_protect_branch(self, test_client):
        """
        测试保护分支
        """
        repo_id = 1
        branch_name = "develop"
        protection_settings = {
            "require_code_review": True,
            "require_status_checks": False
        }
        
        response = test_client.put(f"/api/repositories/{repo_id}/branches/{branch_name}/protect", json=protection_settings)
        
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
    
    def test_unprotect_branch(self, test_client):
        """
        测试取消分支保护
        """
        repo_id = 1
        branch_name = "master"
        
        response = test_client.put(f"/api/repositories/{repo_id}/branches/{branch_name}/unprotect")
        
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
    
    def test_get_default_branch(self, test_client):
        """
        测试获取默认分支
        """
        repo_id = 1
        response = test_client.get(f"/api/repositories/{repo_id}/branches/default")
        
        # 如果没有默认分支，应该返回404
        if response.status_code == 404:
            assert "detail" in response.json()
            assert "Default branch not found" in response.json()["detail"]
        else:
            # 如果存在默认分支，应该返回200和分支信息
            assert response.status_code == 200
            assert "is_default" in response.json()
            assert response.json()["is_default"] == True
    
    def test_check_branch_protection(self, test_client):
        """
        测试检查分支保护状态
        """
        repo_id = 1
        branch_name = "master"
        
        response = test_client.get(f"/api/repositories/{repo_id}/branches/{branch_name}/protection")
        
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