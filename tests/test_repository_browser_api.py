"""
仓库代码浏览 API 测试

测试范围:
1. 文件树浏览 API - GET /api/repositories/{repo_id}/tree
2. 文件内容查看 API - GET /api/repositories/{repo_id}/blob
3. 提交历史 API - GET /api/repositories/{repo_id}/commits
4. 代码对比 API - GET /api/repositories/{repo_id}/diff
"""
import pytest
import os
import tempfile
import shutil
from datetime import datetime

import pygit2
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.base import Base
from models.db import get_db
from models import Repository, User
from app import create_app
from client.utils.git_utils import init_bare_repo, get_repository_storage_path


# 测试数据库配置
TEST_DATABASE_URL = "sqlite:///./test_browser_api.db"

# 创建测试数据库引擎
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建测试数据库表
Base.metadata.create_all(bind=engine)


def override_get_db():
    """覆盖数据库依赖，使用测试数据库"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


# 创建测试应用
app = create_app(config_path="config.toml")
app.dependency_overrides[get_db] = override_get_db


# ==================== Fixtures ====================

@pytest.fixture
def client():
    """创建测试客户端"""
    return TestClient(app)


@pytest.fixture
def test_user():
    """创建测试用户"""
    db = TestingSessionLocal()
    user = User(
        username="testuser",
        email="test@example.com",
        password="hashed_password"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    yield user
    db.delete(user)
    db.commit()
    db.close()


@pytest.fixture
def test_repository(test_user):
    """创建测试仓库"""
    db = TestingSessionLocal()
    
    # 使用固定的 repositories 目录
    repo_root = "./repositories"
    os.makedirs(repo_root, exist_ok=True)
    
    repo_path = f"testuser/test-repo-browser"
    physical_path = os.path.join(repo_root, repo_path)
    
    # 如果已存在，先删除
    if os.path.exists(physical_path):
        shutil.rmtree(physical_path, ignore_errors=True)
    
    # 初始化 bare 仓库
    init_bare_repo(physical_path)
    
    # 创建一些文件
    work_dir = tempfile.mkdtemp()
    try:
        repo = pygit2.clone_repository(physical_path, work_dir, bare=False)
        
        os.makedirs(os.path.join(work_dir, "src"), exist_ok=True)
        with open(os.path.join(work_dir, "README.md"), "w") as f:
            f.write("# Test Repository\n")
        with open(os.path.join(work_dir, "src", "app.py"), "w") as f:
            f.write("def main():\n    pass\n")
        
        signature = pygit2.Signature("Test User", "test@example.com", int(datetime.now().timestamp()), 0)
        index = repo.index
        index.add_all()
        index.write()
        tree = index.write_tree()
        repo.create_commit("HEAD", signature, signature, "Initial commit", tree, [])
        
        remote = repo.remotes["origin"]
        remote.push(["refs/heads/master:refs/heads/master"])
        
        repo.free()
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
    
    # 检查是否已存在同名仓库记录
    existing = db.query(Repository).filter(Repository.path == repo_path).first()
    if existing:
        db.delete(existing)
        db.commit()
    
    # 创建数据库记录
    repository = Repository(
        name="test-repo-browser",
        path=repo_path,
        description="Test repository for browser API",
        is_public=True,
        owner_id=test_user.id,
        default_branch="master"
    )
    db.add(repository)
    db.commit()
    db.refresh(repository)
    
    yield repository
    
    # 清理
    db.delete(repository)
    db.commit()
    db.close()
    if os.path.exists(physical_path):
        shutil.rmtree(physical_path, ignore_errors=True)


# ==================== 文件树浏览 API 测试 ====================

class TestGetTreeApi:
    """测试文件树浏览 API"""
    
    def test_get_tree_success(self, client, test_repository):
        """测试获取文件树成功"""
        response = client.get(f"/api/repositories/{test_repository.id}/tree")
        
        assert response.status_code == 200
        data = response.json()
        assert "path" in data
        assert "ref" in data
        assert "entries" in data
        assert isinstance(data["entries"], list)
    
    def test_get_tree_with_ref(self, client, test_repository):
        """测试指定分支获取文件树"""
        response = client.get(f"/api/repositories/{test_repository.id}/tree?ref=master")
        
        assert response.status_code == 200
        data = response.json()
        assert data["ref"] == "master"
    
    def test_get_tree_with_path(self, client, test_repository):
        """测试获取子目录文件树"""
        response = client.get(f"/api/repositories/{test_repository.id}/tree?path=src")
        
        assert response.status_code == 200
        data = response.json()
        assert data["path"] == "src"
        assert len(data["entries"]) >= 1
    
    def test_get_tree_not_found(self, client):
        """测试仓库不存在"""
        response = client.get("/api/repositories/99999/tree")
        
        assert response.status_code == 404
    
    def test_get_tree_invalid_path(self, client, test_repository):
        """测试无效路径"""
        response = client.get(f"/api/repositories/{test_repository.id}/tree?path=nonexistent")
        
        assert response.status_code == 404


# ==================== 文件内容查看 API 测试 ====================

class TestGetBlobApi:
    """测试文件内容查看 API"""
    
    def test_get_blob_success(self, client, test_repository):
        """测试获取文件内容成功"""
        response = client.get(f"/api/repositories/{test_repository.id}/blob?path=README.md")
        
        assert response.status_code == 200
        data = response.json()
        assert "path" in data
        assert "content" in data
        assert "sha" in data
        assert "size" in data
        assert data["is_binary"] is False
    
    def test_get_blob_with_ref(self, client, test_repository):
        """测试指定分支获取文件内容"""
        response = client.get(f"/api/repositories/{test_repository.id}/blob?path=README.md&ref=master")
        
        assert response.status_code == 200
        data = response.json()
        assert "# Test Repository" in data["content"]
    
    def test_get_blob_not_found(self, client, test_repository):
        """测试文件不存在"""
        response = client.get(f"/api/repositories/{test_repository.id}/blob?path=nonexistent.py")
        
        assert response.status_code == 404
    
    def test_get_blob_missing_path(self, client, test_repository):
        """测试缺少路径参数"""
        response = client.get(f"/api/repositories/{test_repository.id}/blob")
        
        assert response.status_code == 422
    
    def test_get_blob_directory(self, client, test_repository):
        """测试获取目录内容"""
        response = client.get(f"/api/repositories/{test_repository.id}/blob?path=src")
        
        assert response.status_code == 400


# ==================== 提交历史 API 测试 ====================

class TestGetCommitsApi:
    """测试提交历史 API"""
    
    def test_get_commits_success(self, client, test_repository):
        """测试获取提交历史成功"""
        response = client.get(f"/api/repositories/{test_repository.id}/commits")
        
        assert response.status_code == 200
        data = response.json()
        assert "commits" in data
        assert "pagination" in data
        assert isinstance(data["commits"], list)
    
    def test_get_commits_with_pagination(self, client, test_repository):
        """测试分页获取提交"""
        response = client.get(f"/api/repositories/{test_repository.id}/commits?page=1&per_page=10")
        
        assert response.status_code == 200
        data = response.json()
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["per_page"] == 10
    
    def test_get_commits_not_found(self, client):
        """测试仓库不存在"""
        response = client.get("/api/repositories/99999/commits")
        
        assert response.status_code == 404


# ==================== 代码对比 API 测试 ====================

class TestGetDiffApi:
    """测试代码对比 API"""
    
    def test_get_diff_success(self, client, test_repository):
        """测试获取代码差异成功"""
        # 首先获取提交列表
        commits_response = client.get(f"/api/repositories/{test_repository.id}/commits")
        commits_data = commits_response.json()
        
        if len(commits_data["commits"]) > 0:
            head = commits_data["commits"][0]["sha"]
            response = client.get(f"/api/repositories/{test_repository.id}/diff?head={head}")
            
            assert response.status_code == 200
            data = response.json()
            assert "files" in data
    
    def test_get_diff_missing_head(self, client, test_repository):
        """测试缺少 head 参数"""
        response = client.get(f"/api/repositories/{test_repository.id}/diff")
        
        assert response.status_code == 422
    
    def test_get_diff_not_found(self, client):
        """测试仓库不存在"""
        response = client.get("/api/repositories/99999/diff?head=abc123")
        
        assert response.status_code == 404
