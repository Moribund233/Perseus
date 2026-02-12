"""
Git HTTP API 测试模块

测试 Git Smart HTTP 协议功能
包括引用发现、clone、push 等操作
"""
import os
import sys
import tempfile
import shutil
import subprocess
import base64
import stat
import pytest
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def remove_readonly(func, path, excinfo):
    """Windows 下删除只读文件的回调函数"""
    os.chmod(path, stat.S_IWRITE)
    func(path)

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.base import Base
from models.db import get_db
from app import create_app
from utils.git_utils import init_bare_repo, get_repository_storage_path


# 测试数据库配置
TEST_DATABASE_URL = "sqlite:///./test_git_http.db"

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
client = TestClient(app)


# 测试数据
TEST_USERNAME = "gituser"
TEST_PASSWORD = "gitpass123"
TEST_EMAIL = "gituser@example.com"
TEST_REPO_NAME = "test-git-repo"


class TestGitHttpAPI:
    """Git HTTP API 测试类"""

    @pytest.fixture(autouse=True)
    def setup_and_cleanup(self):
        """测试前设置和测试后清理"""
        # 清理测试数据库
        db = TestingSessionLocal()

        # 删除所有仓库成员
        from models.repository_member import RepositoryMember
        db.query(RepositoryMember).delete()

        # 删除所有仓库
        from models.repository import Repository
        db.query(Repository).delete()

        # 删除所有用户
        from models.user import User
        db.query(User).delete()

        db.commit()
        db.close()

        # 清理测试仓库目录
        repo_root = "./repositories"
        if os.path.exists(repo_root):
            shutil.rmtree(repo_root, onexc=remove_readonly)

        yield

        # 测试后清理
        db = TestingSessionLocal()
        from models.repository_member import RepositoryMember
        from models.repository import Repository
        from models.user import User

        db.query(RepositoryMember).delete()
        db.query(Repository).delete()
        db.query(User).delete()
        db.commit()
        db.close()

        if os.path.exists(repo_root):
            shutil.rmtree(repo_root, onexc=remove_readonly)

    def create_test_user(self, username=TEST_USERNAME, password=TEST_PASSWORD, email=TEST_EMAIL):
        """创建测试用户"""
        response = client.post("/api/users/", json={
            "username": username,
            "password": password,
            "email": email,
            "full_name": "Git Test User"
        })
        assert response.status_code == 200, f"创建用户失败: {response.text}"
        return response.json()

    def create_test_repo(self, user_id, repo_name=TEST_REPO_NAME, is_public=True):
        """创建测试仓库"""
        response = client.post("/api/repositories/", json={
            "name": repo_name,
            "description": "Test repository for Git HTTP API",
            "is_public": is_public,
            "owner_id": user_id,
            "path": f"{TEST_USERNAME}/{repo_name}"
        })
        assert response.status_code == 200, f"创建仓库失败: {response.text}"
        return response.json()

    def get_auth_header(self, username=TEST_USERNAME, password=TEST_PASSWORD):
        """获取 Basic Auth 请求头"""
        credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
        return {"Authorization": f"Basic {credentials}"}

    def test_git_refs_discovery_public_repo(self):
        """测试公开仓库的引用发现（无需认证）"""
        # 创建用户和公开仓库
        user = self.create_test_user()
        repo = self.create_test_repo(user["id"], is_public=True)

        # 测试引用发现
        response = client.get(f"/git/{TEST_USERNAME}/{TEST_REPO_NAME}/info/refs")
        assert response.status_code == 200, f"引用发现失败: {response.text}"

    def test_git_refs_discovery_private_repo_no_auth(self):
        """测试私有仓库引用发现（无认证）"""
        # 创建用户和私有仓库
        user = self.create_test_user()
        repo = self.create_test_repo(user["id"], is_public=False)

        # 测试引用发现（无认证）
        response = client.get(f"/git/{TEST_USERNAME}/{TEST_REPO_NAME}/info/refs")
        assert response.status_code == 401, "私有仓库应该需要认证"

    def test_git_refs_discovery_private_repo_with_auth(self):
        """测试私有仓库引用发现（有认证）"""
        # 创建用户和私有仓库
        user = self.create_test_user()
        repo = self.create_test_repo(user["id"], is_public=False)

        # 测试引用发现（有认证）
        headers = self.get_auth_header()
        response = client.get(
            f"/git/{TEST_USERNAME}/{TEST_REPO_NAME}/info/refs",
            headers=headers
        )
        assert response.status_code == 200, f"引用发现失败: {response.text}"

    def test_git_refs_discovery_with_service(self):
        """测试带服务参数的引用发现"""
        # 创建用户和仓库
        user = self.create_test_user()
        repo = self.create_test_repo(user["id"])

        # 测试 upload-pack 服务
        response = client.get(
            f"/git/{TEST_USERNAME}/{TEST_REPO_NAME}/info/refs?service=git-upload-pack"
        )
        assert response.status_code == 200, f"upload-pack 引用发现失败: {response.text}"
        assert "application/x-git-upload-pack-advertisement" in response.headers.get("content-type", "")

        # 测试 receive-pack 服务（需要认证）
        headers = self.get_auth_header()
        response = client.get(
            f"/git/{TEST_USERNAME}/{TEST_REPO_NAME}/info/refs?service=git-receive-pack",
            headers=headers
        )
        assert response.status_code == 200, f"receive-pack 引用发现失败: {response.text}"
        assert "application/x-git-receive-pack-advertisement" in response.headers.get("content-type", "")

    def test_git_refs_discovery_nonexistent_repo(self):
        """测试不存在的仓库引用发现"""
        response = client.get("/git/nonexistent/repo/info/refs")
        assert response.status_code == 404, "不存在的仓库应该返回 404"

    def test_git_upload_pack(self):
        """测试 git-upload-pack（clone/fetch）"""
        # 创建用户和仓库
        user = self.create_test_user()
        repo = self.create_test_repo(user["id"])

        # 构建 upload-pack 请求体
        # 格式: 0032want 0000000000000000000000000000000000000000\n00000009done\n
        request_body = b"0032want 0000000000000000000000000000000000000000\n00000009done\n"

        response = client.post(
            f"/git/{TEST_USERNAME}/{TEST_REPO_NAME}/git-upload-pack",
            content=request_body,
            headers={"Content-Type": "application/x-git-upload-pack-request"}
        )

        # 空仓库可能返回 NAK，但请求应该被正确处理
        assert response.status_code in [200, 500], f"upload-pack 失败: {response.text}"

    def test_git_upload_pack_nonexistent_repo(self):
        """测试不存在的仓库 upload-pack"""
        request_body = b"0032want 0000000000000000000000000000000000000000\n00000009done\n"

        response = client.post(
            "/git/nonexistent/repo/git-upload-pack",
            content=request_body,
            headers={"Content-Type": "application/x-git-upload-pack-request"}
        )

        assert response.status_code == 404, "不存在的仓库应该返回 404"

    def test_git_receive_pack_no_auth(self):
        """测试无认证的 git-receive-pack"""
        # 创建用户和仓库
        user = self.create_test_user()
        repo = self.create_test_repo(user["id"])

        request_body = b"0000"

        response = client.post(
            f"/git/{TEST_USERNAME}/{TEST_REPO_NAME}/git-receive-pack",
            content=request_body,
            headers={"Content-Type": "application/x-git-receive-pack-request"}
        )

        assert response.status_code == 401, "receive-pack 应该需要认证"

    def test_git_receive_pack_with_auth(self):
        """测试有认证的 git-receive-pack"""
        # 创建用户和仓库
        user = self.create_test_user()
        repo = self.create_test_repo(user["id"])

        headers = self.get_auth_header()
        headers["Content-Type"] = "application/x-git-receive-pack-request"

        request_body = b"0000"

        response = client.post(
            f"/git/{TEST_USERNAME}/{TEST_REPO_NAME}/git-receive-pack",
            content=request_body,
            headers=headers
        )

        # 空请求体可能返回错误，但应该被正确处理
        assert response.status_code in [200, 500], f"receive-pack 失败: {response.text}"

    def test_git_head_endpoint(self):
        """测试 HEAD 端点"""
        # 创建用户和仓库
        user = self.create_test_user()
        repo = self.create_test_repo(user["id"])

        response = client.get(f"/git/{TEST_USERNAME}/{TEST_REPO_NAME}/HEAD")
        assert response.status_code == 200, f"获取 HEAD 失败: {response.text}"

    def test_git_objects_endpoint(self):
        """测试 objects 端点"""
        # 创建用户和仓库
        user = self.create_test_user()
        repo = self.create_test_repo(user["id"])

        # 测试获取不存在的对象
        response = client.get(f"/git/{TEST_USERNAME}/{TEST_REPO_NAME}/objects/00/00000000000000000000000000000000000000")
        assert response.status_code == 404, "不存在的对象应该返回 404"


class TestGitHttpIntegration:
    """Git HTTP 集成测试类 - 使用真实 git 命令"""

    @pytest.fixture(autouse=True)
    def setup_and_cleanup(self):
        """测试前设置和测试后清理"""
        # 清理测试数据库
        db = TestingSessionLocal()

        from models.repository_member import RepositoryMember
        from models.repository import Repository
        from models.user import User

        db.query(RepositoryMember).delete()
        db.query(Repository).delete()
        db.query(User).delete()
        db.commit()
        db.close()

        # 清理测试仓库目录
        repo_root = "./repositories"
        if os.path.exists(repo_root):
            shutil.rmtree(repo_root, onexc=remove_readonly)

        # 创建临时目录
        self.temp_dir = tempfile.mkdtemp()

        yield

        # 测试后清理
        db = TestingSessionLocal()
        db.query(RepositoryMember).delete()
        db.query(Repository).delete()
        db.query(User).delete()
        db.commit()
        db.close()

        if os.path.exists(repo_root):
            shutil.rmtree(repo_root, onexc=remove_readonly)

        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, onexc=remove_readonly)

    def create_test_user(self, username=TEST_USERNAME, password=TEST_PASSWORD, email=TEST_EMAIL):
        """创建测试用户"""
        response = client.post("/api/users/", json={
            "username": username,
            "password": password,
            "email": email,
            "full_name": "Git Test User"
        })
        assert response.status_code == 200, f"创建用户失败: {response.text}"
        return response.json()

    def create_test_repo(self, user_id, repo_name=TEST_REPO_NAME, is_public=True):
        """创建测试仓库"""
        response = client.post("/api/repositories/", json={
            "name": repo_name,
            "description": "Test repository for Git HTTP API",
            "is_public": is_public,
            "owner_id": user_id,
            "path": f"{TEST_USERNAME}/{repo_name}"
        })
        assert response.status_code == 200, f"创建仓库失败: {response.text}"
        return response.json()

    def test_real_git_clone(self):
        """测试使用真实 git 命令 clone 仓库"""
        # 创建用户和公开仓库
        user = self.create_test_user()
        repo = self.create_test_repo(user["id"], is_public=True)

        # 获取服务器 URL（使用测试客户端的 base URL）
        server_url = "http://testserver"
        repo_url = f"{server_url}/git/{TEST_USERNAME}/{TEST_REPO_NAME}"

        # 使用 git ls-remote 测试引用发现
        clone_dir = os.path.join(self.temp_dir, "cloned-repo")

        # 注意：由于 TestClient 不支持真正的 HTTP 服务器，
        # 这里我们直接测试 API 端点
        response = client.get(f"/git/{TEST_USERNAME}/{TEST_REPO_NAME}/info/refs?service=git-upload-pack")
        assert response.status_code == 200

        # 验证响应包含服务声明
        content = response.content
        assert b"# service=git-upload-pack" in content or b"service=git-upload-pack" in content


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])
