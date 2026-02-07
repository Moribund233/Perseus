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


class TestCommitAPI:
    """
    提交API测试类
    """
    
    def test_get_latest_commit(self, test_client):
        """
        测试获取仓库的最新提交
        """
        repo_id = 1
        response = test_client.get(f"/api/repositories/{repo_id}/commits/latest")
        
        # 如果没有提交记录，应该返回404
        if response.status_code == 404:
            assert "error" in response.json()
            assert "No commits found" in response.json()["error"]["message"]
        else:
            # 如果有提交记录，应该返回200和最新提交信息
            assert response.status_code == 200
            assert "hash" in response.json()
            assert "author_name" in response.json()
            assert "commit_message" in response.json()
    
    def test_get_commit_history(self, test_client):
        """
        测试获取仓库的提交历史树
        """
        repo_id = 1
        response = test_client.get(f"/api/repositories/{repo_id}/commits/history")
        
        # 检查响应状态码
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_count_repo_commits(self, test_client):
        """
        测试统计仓库的提交数量
        """
        repo_id = 1
        response = test_client.get(f"/api/repositories/{repo_id}/commits/count")
        
        # 检查响应状态码
        assert response.status_code == 200
        assert "count" in response.json()
        assert isinstance(response.json()["count"], int)
    
    def test_get_latest_commit(self, test_client):
        """
        测试获取仓库的最新提交
        """
        repo_id = 1
        response = test_client.get(f"/api/repositories/{repo_id}/commits/latest")
        
        # 如果没有提交记录，应该返回404
        if response.status_code == 404:
            assert "error" in response.json()
            assert "No commits found" in response.json()["error"]["message"]
        else:
            # 如果有提交记录，应该返回200和最新提交信息
            assert response.status_code == 200
            assert "hash" in response.json()
            assert "author_name" in response.json()
            assert "commit_message" in response.json()
    
    def test_get_commit_by_hash(self, test_client):
        """
        测试根据提交哈希获取提交详情
        """
        repo_id = 1
        commit_hash = "a" * 40  # 模拟sha1哈希
        
        response = test_client.get(f"/api/repositories/{repo_id}/commits/{commit_hash}")
        
        # 如果提交不存在，应该返回404
        if response.status_code == 404:
            assert "error" in response.json()
            assert "not found" in response.json()["error"]["message"].lower()
        else:
            # 如果提交存在，应该返回200和提交详情
            assert response.status_code == 200
            assert "hash" in response.json()
            assert response.json()["hash"] == commit_hash
    
    def test_create_commit(self, test_client):
        """
        测试创建提交记录
        """
        # 首先确保存在测试仓库和分支
        repo_id = 1
        
        # 获取测试仓库的默认分支
        branch_response = test_client.get(f"/api/repositories/{repo_id}/branches/default")
        
        if branch_response.status_code == 200:
            branch_id = branch_response.json()["id"]
            
            # 创建提交记录
            commit_data = {
                "hash": "b" * 40,  # 模拟sha1哈希
                "repository_id": repo_id,
                "branch_id": branch_id,
                "author_name": "Test Author",
                "author_email": "test@example.com",
                "commit_message": "Test commit message",
                "parent_hashes": ""
            }
            
            response = test_client.post(f"/api/repositories/{repo_id}/commits", json=commit_data)
            
            # 检查响应状态码
            assert response.status_code == 200 or response.status_code == 409
            
            if response.status_code == 409:
                # 如果提交哈希已存在，应该返回409和错误信息
                assert "detail" in response.json()
                assert "already exists" in response.json()["detail"]
            else:
                # 如果提交创建成功，应该返回200和提交信息
                assert response.status_code == 200
                assert "hash" in response.json()
                assert response.json()["hash"] == commit_data["hash"]
    
    def test_search_commits(self, test_client):
        """
        测试搜索提交记录
        """
        repo_id = 1
        query = "initial"
        response = test_client.get(f"/api/repositories/{repo_id}/commits/search?query={query}")
        
        # 检查响应状态码
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_get_commits_by_author(self, test_client):
        """
        测试根据作者邮箱获取提交记录
        """
        repo_id = 1
        author_email = "admin@example.com"
        response = test_client.get(f"/api/repositories/{repo_id}/commits/author?author_email={author_email}")
        
        # 检查响应状态码
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_count_branch_commits(self, test_client):
        """
        测试统计分支的提交数量
        """
        repo_id = 1
        branch_name = "master"
        response = test_client.get(f"/api/repositories/{repo_id}/branches/{branch_name}/commits/count")
        
        # 如果分支不存在，应该返回404
        if response.status_code == 404:
            assert "error" in response.json()
            assert "not found" in response.json()["error"]["message"].lower()
        else:
            # 如果分支存在，应该返回200和提交数量
            assert response.status_code == 200
            assert "count" in response.json()
            assert isinstance(response.json()["count"], int)
    
    def test_get_commits_by_branch(self, test_client):
        """
        测试获取特定分支的提交记录
        """
        repo_id = 1
        branch_name = "master"
        response = test_client.get(f"/api/repositories/{repo_id}/commits?branch_name={branch_name}")
        
        # 如果分支不存在，应该返回404
        if response.status_code == 404:
            assert "error" in response.json()
            assert "not found" in response.json()["error"]["message"].lower()
        else:
            # 如果分支存在，应该返回200和提交记录列表
            assert response.status_code == 200
            assert isinstance(response.json(), list)