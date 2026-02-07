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


class TestRepositoryMemberAPI:
    """
    仓库成员API测试类
    """
    
    def test_get_repository_members(self, test_client):
        """
        测试获取仓库的所有成员
        """
        repo_id = 1
        response = test_client.get(f"/api/repositories/{repo_id}/members")
        
        # 检查响应状态码
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_get_repository_member(self, test_client):
        """
        测试获取仓库的特定成员
        """
        repo_id = 1
        user_id = 1
        
        response = test_client.get(f"/api/repositories/{repo_id}/members/{user_id}")
        
        # 如果成员不存在，应该返回404
        if response.status_code == 404:
            assert "detail" in response.json()
            assert "Member not found" in response.json()["detail"]
        else:
            # 如果成员存在，应该返回200和成员信息
            assert response.status_code == 200
            assert "repository_id" in response.json()
            assert "user_id" in response.json()
            assert response.json()["repository_id"] == repo_id
            assert response.json()["user_id"] == user_id
    
    def test_add_repository_member(self, test_client):
        """
        测试添加仓库成员
        """
        # 首先确保存在测试用户和测试仓库
        # 创建测试用户
        user_data = {
            "username": "testmember",
            "email": "testmember@example.com",
            "password": "testpassword",
            "full_name": "Test Member",
            "is_active": True,
            "is_admin": False
        }
        test_client.post("/api/users/", json=user_data)
        
        # 创建测试仓库
        repo_data = {
            "name": "test-repo-member",
            "path": "/repos/test-repo-member",
            "description": "Test repository for member management",
            "is_public": True,
            "owner_id": 1,
            "default_branch": "master"
        }
        repo_response = test_client.post("/api/repositories/", json=repo_data)
        
        if repo_response.status_code == 200:
            repo_id = repo_response.json()["id"]
            
            # 查找测试用户ID
            users_response = test_client.get("/api/users/")
            test_user_id = None
            for user in users_response.json():
                if user["username"] == "testmember":
                    test_user_id = user["id"]
                    break
            
            if test_user_id:
                # 添加测试用户为仓库成员
                member_data = {
                    "user_id": test_user_id,
                    "role": "developer"
                }
                
                response = test_client.post(f"/api/repositories/{repo_id}/members", json=member_data)
                
                # 检查响应状态码
                assert response.status_code == 200 or response.status_code == 409
                
                if response.status_code == 409:
                    # 如果成员已存在，应该返回409和错误信息
                    assert "detail" in response.json()
                    assert "already a member" in response.json()["detail"]
                else:
                    # 如果成员添加成功，应该返回200和成员信息
                    assert response.status_code == 200
                    assert "repository_id" in response.json()
                    assert "user_id" in response.json()
                    assert response.json()["repository_id"] == repo_id
                    assert response.json()["user_id"] == test_user_id
    
    def test_update_member_role(self, test_client):
        """
        测试更新仓库成员角色
        """
        repo_id = 1
        user_id = 1
        
        role_data = {
            "role": "admin"
        }
        
        response = test_client.put(f"/api/repositories/{repo_id}/members/{user_id}/role", json=role_data)
        
        # 如果成员不存在，应该返回404
        if response.status_code == 404:
            assert "detail" in response.json()
            assert "Member not found" in response.json()["detail"]
        else:
            # 如果更新成功，应该返回200和更新后的成员信息
            assert response.status_code == 200
            assert response.json()["role"] == role_data["role"]
    
    def test_activate_repository_member(self, test_client):
        """
        测试激活仓库成员
        """
        repo_id = 1
        user_id = 1
        
        response = test_client.put(f"/api/repositories/{repo_id}/members/{user_id}/activate")
        
        # 如果成员不存在，应该返回404
        if response.status_code == 404:
            assert "detail" in response.json()
            assert "Member not found" in response.json()["detail"]
        else:
            # 如果激活成功，应该返回200和激活后的成员信息
            assert response.status_code == 200
            assert response.json()["is_active"] == True
    
    def test_deactivate_repository_member(self, test_client):
        """
        测试停用仓库成员
        """
        # 创建一个测试成员用于停用测试
        import uuid
        unique_suffix = str(uuid.uuid4())[:8]
        
        # 首先创建测试用户1作为仓库所有者
        owner_data = {
            "username": f"testowner-{unique_suffix}",
            "email": f"testowner-{unique_suffix}@example.com",
            "password": "testpassword",
            "full_name": f"Test Owner {unique_suffix}",
            "is_active": True,
            "is_admin": False
        }
        owner_response = test_client.post("/api/users/", json=owner_data)
        
        if owner_response.status_code == 200:
            owner_id = owner_response.json()["id"]
            
            # 创建测试用户2作为普通成员
            member_data = {
                "username": f"testmember-{unique_suffix}",
                "email": f"testmember-{unique_suffix}@example.com",
                "password": "testpassword",
                "full_name": f"Test Member {unique_suffix}",
                "is_active": True,
                "is_admin": False
            }
            member_response = test_client.post("/api/users/", json=member_data)
            
            if member_response.status_code == 200:
                member_id = member_response.json()["id"]
                
                # 创建测试仓库，使用用户1作为所有者
                repo_data = {
                    "name": f"test-repo-deactive-{unique_suffix}",
                    "path": f"/repos/test-repo-deactive-{unique_suffix}",
                    "description": "Test repository for deactivate member",
                    "is_public": True,
                    "owner_id": owner_id,
                    "default_branch": "master"
                }
                repo_response = test_client.post("/api/repositories/", json=repo_data)
                
                if repo_response.status_code == 200:
                    repo_id = repo_response.json()["id"]
                    
                    # 添加用户2为仓库成员
                    add_member_data = {
                        "user_id": member_id,
                        "role": "developer"
                    }
                    add_response = test_client.post(f"/api/repositories/{repo_id}/members", json=add_member_data)
                    
                    if add_response.status_code == 200:
                        # 停用测试成员（用户2）
                        deactivate_response = test_client.put(f"/api/repositories/{repo_id}/members/{member_id}/deactivate")
                        
                        # 检查响应状态码
                        assert deactivate_response.status_code == 200
                        assert deactivate_response.json()["is_active"] == False
    
    def test_check_member_permission(self, test_client):
        """
        测试检查成员权限
        """
        import uuid
        unique_suffix = str(uuid.uuid4())[:8]
        
        # 创建测试用户
        user_data = {
            "username": f"testpermission-{unique_suffix}",
            "email": f"testpermission-{unique_suffix}@example.com",
            "password": "testpassword",
            "full_name": f"Test Permission User {unique_suffix}",
            "is_active": True,
            "is_admin": False
        }
        user_response = test_client.post("/api/users/", json=user_data)
        
        if user_response.status_code == 200:
            user_id = user_response.json()["id"]
            
            # 创建测试仓库
            repo_data = {
                "name": f"test-repo-permission-{unique_suffix}",
                "path": f"/repos/test-repo-permission-{unique_suffix}",
                "description": "Test repository for permission check",
                "is_public": True,
                "owner_id": user_id,
                "default_branch": "master"
            }
            repo_response = test_client.post("/api/repositories/", json=repo_data)
            
            if repo_response.status_code == 200:
                repo_id = repo_response.json()["id"]
                
                # 添加用户为仓库成员
                member_data = {
                    "user_id": user_id,
                    "role": "developer"
                }
                add_response = test_client.post(f"/api/repositories/{repo_id}/members", json=member_data)
                
                if add_response.status_code == 200:
                    # 检查成员权限
                    required_role = "developer"
                    response = test_client.get(f"/api/repositories/{repo_id}/members/{user_id}/permission?required_role={required_role}")
                    
                    # 检查响应状态码
                    assert response.status_code == 200
                    assert "has_permission" in response.json()
                    assert isinstance(response.json()["has_permission"], bool)