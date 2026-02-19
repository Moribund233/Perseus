"""
Git HTTP Backend 集成测试

测试 git http-backend 的集成是否正确工作
"""
import os
import sys
import tempfile
import subprocess
import shutil
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import Base
from models.db import get_db
from app import create_app
from services.git_http_service import GitHttpBackendService, get_git_backend_service


# 创建内存数据库用于测试
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """覆盖数据库依赖"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


@pytest.fixture(scope="module")
def test_client():
    """创建测试客户端"""
    # 创建数据库表
    Base.metadata.create_all(bind=engine)
    
    # 创建应用
    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as client:
        yield client
    
    # 清理
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def temp_repo():
    """创建临时 Git 仓库"""
    temp_dir = tempfile.mkdtemp()
    repo_path = os.path.join(temp_dir, "test-repo.git")
    
    try:
        # 初始化裸仓库
        subprocess.run(
            ["git", "init", "--bare", repo_path],
            check=True,
            capture_output=True
        )
        
        # 创建测试提交
        work_dir = os.path.join(temp_dir, "work")
        os.makedirs(work_dir)
        
        subprocess.run(
            ["git", "clone", repo_path, work_dir],
            check=True,
            capture_output=True
        )
        
        # 配置 git
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=work_dir,
            check=True,
            capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=work_dir,
            check=True,
            capture_output=True
        )
        
        # 创建文件并提交
        test_file = os.path.join(work_dir, "README.md")
        with open(test_file, "w") as f:
            f.write("# Test Repository\n")
        
        subprocess.run(
            ["git", "add", "."],
            cwd=work_dir,
            check=True,
            capture_output=True
        )
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=work_dir,
            check=True,
            capture_output=True
        )
        subprocess.run(
            ["git", "push", "origin", "master"],
            cwd=work_dir,
            check=True,
            capture_output=True
        )
        
        yield repo_path
        
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


class TestGitHttpBackendService:
    """测试 GitHttpBackendService"""
    
    def test_find_git_http_backend(self):
        """测试查找 git http-backend"""
        service = GitHttpBackendService()
        assert service._git_backend_path is not None
        print(f"✓ Found git http-backend at: {service._git_backend_path}")
    
    def test_prepare_environment(self):
        """测试环境变量准备"""
        from unittest.mock import MagicMock
        import os
        
        service = GitHttpBackendService()
        
        # 模拟请求
        mock_request = MagicMock()
        mock_request.url.path = "/git/user/repo/info/refs"
        mock_request.url.hostname = "localhost"
        mock_request.url.port = 8000
        mock_request.query_params = "service=git-upload-pack"
        mock_request.method = "GET"
        mock_request.headers = {
            "host": "localhost:8000",
            "user-agent": "git/2.0",
            "accept": "*/*"
        }
        
        # 使用绝对路径
        repo_path = os.path.abspath("repositories/user/repo")
        
        env = service._prepare_environment(
            repo_path,
            mock_request,
            content_length=0,
            remote_user="testuser"
        )
        
        # GIT_PROJECT_ROOT 应该是仓库根目录（repositories）
        assert "repositories" in env["GIT_PROJECT_ROOT"]
        assert env["REQUEST_METHOD"] == "GET"
        assert env["REMOTE_USER"] == "testuser"
        assert env["GIT_HTTP_EXPORT_ALL"] == "1"
        # PATH_INFO 应该包含 /user/repo/...
        assert "/user/repo/" in env["PATH_INFO"]
        print("✓ Environment variables prepared correctly")


class TestGitHttpEndpoints:
    """测试 Git HTTP 端点"""
    
    def test_info_refs_without_auth(self, test_client):
        """测试未认证的 info/refs 请求返回 401"""
        response = test_client.get("/git/test/repo/info/refs")
        # 应该返回 404（仓库不存在）或 401（需要认证）
        assert response.status_code in [401, 404]
        print(f"✓ Info refs without auth: {response.status_code}")
    
    def test_info_refs_with_invalid_repo(self, test_client):
        """测试无效仓库返回 401 或 404"""
        import base64
        
        credentials = base64.b64encode(b"testuser:testpass").decode()
        response = test_client.get(
            "/git/nonexistent/repo/info/refs?service=git-upload-pack",
            headers={"Authorization": f"Basic {credentials}"}
        )
        # 无效仓库应该返回 401（未认证）或 404（已认证但仓库不存在）
        assert response.status_code in [401, 404]
        print(f"✓ Invalid repo returns {response.status_code}")


def test_git_backend_availability():
    """测试 git http-backend 是否可用"""
    try:
        result = subprocess.run(
            ["git", "http-backend"],
            capture_output=True,
            timeout=5
        )
        print(f"✓ git http-backend is available")
        print(f"  Return code: {result.returncode}")
        return True
    except FileNotFoundError:
        print("✗ git command not found in PATH")
        return False
    except subprocess.TimeoutExpired:
        print("✗ git http-backend command timed out")
        return False
    except Exception as e:
        print(f"✗ Error checking git http-backend: {e}")
        return False


def test_cgi_response_parsing():
    """测试 CGI 响应解析"""
    service = GitHttpBackendService()
    
    # 模拟 CGI 响应
    cgi_response = (
        b"Status: 200 OK\r\n"
        b"Content-Type: application/x-git-upload-pack-advertisement\r\n"
        b"Cache-Control: no-cache\r\n"
        b"\r\n"
        b"001e# service=git-upload-pack\n0000"
    )
    
    status_code, headers, body = service._parse_cgi_response(cgi_response)
    
    assert status_code == 200
    assert headers["Content-Type"] == "application/x-git-upload-pack-advertisement"
    assert headers["Cache-Control"] == "no-cache"
    assert b"git-upload-pack" in body
    print("✓ CGI response parsing works correctly")


if __name__ == "__main__":
    print("=" * 60)
    print("Git HTTP Backend 集成测试")
    print("=" * 60)
    
    # 测试 git http-backend 可用性
    print("\n1. 检查 git http-backend 可用性...")
    if not test_git_backend_availability():
        print("\n请确保 Git 已安装并添加到 PATH")
        sys.exit(1)
    
    # 测试 CGI 响应解析
    print("\n2. 测试 CGI 响应解析...")
    try:
        test_cgi_response_parsing()
    except Exception as e:
        print(f"✗ CGI response parsing failed: {e}")
    
    # 运行 pytest 测试
    print("\n3. 运行完整测试套件...")
    pytest.main([__file__, "-v", "--tb=short"])
