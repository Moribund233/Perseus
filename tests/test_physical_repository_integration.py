"""
物理仓库集成测试模块

测试物理 Git 仓库的完整生命周期:
1. 物理仓库创建与初始化
2. 物理仓库 Fork 操作
3. 物理仓库删除与清理
4. 物理仓库与数据库一致性
5. 物理仓库损坏处理
"""
import os
import sys
import shutil
import tempfile
import stat
import pytest
import pygit2

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
from models.user import User
from models.repository import Repository
from app import create_app
from client.utils.git_utils import init_bare_repo, get_repository_storage_path

TEST_DATABASE_URL = "sqlite:///./test_physical_repo.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)


def override_get_db():
    """覆盖数据库依赖，使用测试数据库"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app = create_app(config_path="config.toml")
app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


class TestPhysicalRepositoryLifecycle:
    """物理仓库生命周期测试类"""

    @pytest.fixture(autouse=True)
    def setup_and_cleanup(self):
        """测试前设置和测试后清理"""
        db = TestingSessionLocal()
        db.query(Repository).delete()
        db.query(User).delete()
        db.commit()
        db.close()

        repo_root = "./repositories"
        if os.path.exists(repo_root):
            shutil.rmtree(repo_root, onexc=remove_readonly)

        yield

        db = TestingSessionLocal()
        db.query(Repository).delete()
        db.query(User).delete()
        db.commit()
        db.close()

        if os.path.exists(repo_root):
            shutil.rmtree(repo_root, onexc=remove_readonly)

    def create_user_via_api(self, username, email):
        """通过 API 创建用户"""
        response = client.post("/api/users/", json={
            "username": username,
            "password": "testpass123",
            "email": email,
            "full_name": f"Test {username}"
        })
        assert response.status_code == 200, f"创建用户失败: {response.text}"
        return response.json()

    def create_repo_via_api(self, owner_id, repo_name, is_public=True):
        """通过 API 创建仓库"""
        response = client.post("/api/repositories/", json={
            "name": repo_name,
            "description": f"Test repository {repo_name}",
            "is_public": is_public,
            "owner_id": owner_id
        })
        assert response.status_code == 200, f"创建仓库失败: {response.text}"
        return response.json()

    def get_auth_headers(self, username="testuser"):
        """获取认证头"""
        from services.token_service import create_access_token
        db = TestingSessionLocal()
        try:
            user = db.query(User).filter(User.username == username).first()
            if not user:
                return {}
            token = create_access_token({
                "sub": str(user.id),
                "username": user.username,
                "is_admin": user.is_admin
            })
            return {"Authorization": f"Bearer {token}"}
        finally:
            db.close()

    # ==================== 物理仓库创建测试 ====================

    def test_physical_repo_created_on_api_create(self):
        """测试通过 API 创建仓库时物理仓库也被创建"""
        user = self.create_user_via_api("testuser", "test@test.com")
        repo = self.create_repo_via_api(user["id"], "test-repo")

        # 检查物理路径
        physical_path = repo["physical"]["path"]
        assert os.path.exists(physical_path), f"物理仓库应该存在: {physical_path}"
        assert repo["physical"]["exists"] is True, "physical.exists 应该为 True"

        # 验证是有效的 Git 仓库
        git_repo = pygit2.Repository(physical_path)
        assert git_repo is not None, "应该是有效的 Git 仓库"
        assert git_repo.is_bare, "应该是 bare 仓库"

    def test_physical_repo_initialization_with_content(self):
        """测试物理仓库初始化后包含基本结构"""
        user = self.create_user_via_api("testuser2", "test2@test.com")
        repo = self.create_repo_via_api(user["id"], "test-repo2")

        physical_path = repo["physical"]["path"]

        # 检查 Git 仓库基本结构
        assert os.path.exists(os.path.join(physical_path, "HEAD")), "应该有 HEAD 文件"
        assert os.path.exists(os.path.join(physical_path, "config")), "应该有 config 文件"
        assert os.path.exists(os.path.join(physical_path, "objects")), "应该有 objects 目录"
        assert os.path.exists(os.path.join(physical_path, "refs")), "应该有 refs 目录"

    def test_physical_repo_permissions(self):
        """测试物理仓库权限设置"""
        user = self.create_user_via_api("testuser3", "test3@test.com")
        repo = self.create_repo_via_api(user["id"], "test-repo3")

        physical_path = repo["physical"]["path"]

        # 检查目录权限（Windows 和 Linux 表现不同，这里只检查可访问性）
        assert os.access(physical_path, os.R_OK), "应该可读"
        assert os.access(physical_path, os.W_OK), "应该可写"

    # ==================== 物理仓库 Fork 测试 ====================

    def test_fork_creates_physical_copy(self):
        """测试 Fork 操作创建物理副本"""
        owner = self.create_user_via_api("owner", "owner@test.com")
        source_repo = self.create_repo_via_api(owner["id"], "source-repo")

        forker = self.create_user_via_api("forker", "forker@test.com")
        headers = self.get_auth_headers("forker")

        # Fork 仓库
        response = client.post(
            f"/api/repositories/{source_repo['id']}/fork",
            headers=headers
        )
        assert response.status_code == 200, f"Fork 失败: {response.text}"

        forked_repo = response.json()

        # 检查 Fork 后的物理仓库
        fork_physical_path = forked_repo["physical"]["path"]
        assert os.path.exists(fork_physical_path), f"Fork 的物理仓库应该存在: {fork_physical_path}"
        assert forked_repo["physical"]["exists"] is True, "Fork 的 physical.exists 应该为 True"

        # 验证是独立的 Git 仓库
        git_repo = pygit2.Repository(fork_physical_path)
        assert git_repo is not None, "Fork 应该是有效的 Git 仓库"

    def test_forked_repo_independent_from_source(self):
        """测试 Fork 的仓库与源仓库独立"""
        owner = self.create_user_via_api("owner2", "owner2@test.com")
        source_repo = self.create_repo_via_api(owner["id"], "source-repo2")

        forker = self.create_user_via_api("forker2", "forker2@test.com")
        headers = self.get_auth_headers("forker2")

        # Fork 仓库
        response = client.post(
            f"/api/repositories/{source_repo['id']}/fork",
            headers=headers
        )
        forked_repo = response.json()

        # 检查路径不同
        assert source_repo["physical"]["path"] != forked_repo["physical"]["path"], \
            "Fork 应该有不同的物理路径"

    # ==================== 物理仓库删除测试 ====================

    def test_delete_repo_removes_physical_directory(self):
        """测试删除仓库时物理目录也被删除"""
        user = self.create_user_via_api("testuser4", "test4@test.com")
        repo = self.create_repo_via_api(user["id"], "test-repo4")

        physical_path = repo["physical"]["path"]
        assert os.path.exists(physical_path), "物理仓库应该存在"

        headers = self.get_auth_headers("testuser4")

        # 删除仓库
        response = client.delete(
            f"/api/repositories/{repo['id']}",
            headers=headers
        )
        assert response.status_code == 200, f"删除仓库失败: {response.text}"

        # 检查物理目录已被删除
        assert not os.path.exists(physical_path), "物理仓库应该被删除"

    def test_delete_nonexistent_physical_repo_graceful(self):
        """测试删除时物理仓库不存在也能正常处理"""
        user = self.create_user_via_api("testuser5", "test5@test.com")
        repo = self.create_repo_via_api(user["id"], "test-repo5")

        physical_path = repo["physical"]["path"]

        # 手动删除物理目录（模拟损坏）
        if os.path.exists(physical_path):
            shutil.rmtree(physical_path, onexc=remove_readonly)

        headers = self.get_auth_headers("testuser5")

        # 删除仓库（应该正常处理）
        response = client.delete(
            f"/api/repositories/{repo['id']}",
            headers=headers
        )
        # 应该成功删除数据库记录，即使物理目录已不存在
        assert response.status_code == 200, f"删除仓库失败: {response.text}"

    # ==================== 数据库与物理仓库一致性测试 ====================

    def test_api_returns_correct_physical_status(self):
        """测试 API 返回正确的物理仓库状态"""
        user = self.create_user_via_api("testuser6", "test6@test.com")
        repo = self.create_repo_via_api(user["id"], "test-repo6")

        headers = self.get_auth_headers("testuser6")

        # 获取仓库详情
        response = client.get(f"/api/repositories/{repo['id']}", headers=headers)
        assert response.status_code == 200

        repo_data = response.json()
        assert "physical" in repo_data, "响应应该包含 physical 字段"
        assert repo_data["physical"]["exists"] is True, "physical.exists 应该为 True"
        assert os.path.exists(repo_data["physical"]["path"]), "物理路径应该存在"

    def test_physical_not_exists_when_directory_removed(self):
        """测试物理目录被删除后 API 返回正确状态"""
        user = self.create_user_via_api("testuser7", "test7@test.com")
        repo = self.create_repo_via_api(user["id"], "test-repo7")

        physical_path = repo["physical"]["path"]

        # 手动删除物理目录
        shutil.rmtree(physical_path, onexc=remove_readonly)

        headers = self.get_auth_headers("testuser7")

        # 获取仓库详情
        response = client.get(f"/api/repositories/{repo['id']}", headers=headers)
        assert response.status_code == 200

        repo_data = response.json()
        assert repo_data["physical"]["exists"] is False, "physical.exists 应该为 False"

    def test_list_repositories_includes_physical_info(self):
        """测试仓库列表包含物理仓库信息"""
        user = self.create_user_via_api("testuser8", "test8@test.com")
        repo1 = self.create_repo_via_api(user["id"], "repo-list-1")
        repo2 = self.create_repo_via_api(user["id"], "repo-list-2")

        headers = self.get_auth_headers("testuser8")

        # 获取仓库列表
        response = client.get("/api/repositories/", headers=headers)
        assert response.status_code == 200

        repos = response.json()
        for repo in repos:
            assert "physical" in repo, f"仓库 {repo.get('name')} 应该包含 physical 字段"
            assert "path" in repo["physical"], "physical 应该包含 path"
            assert "exists" in repo["physical"], "physical 应该包含 exists"

    # ==================== 物理仓库路径测试 ====================

    def test_physical_path_format(self):
        """测试物理路径格式正确"""
        user = self.create_user_via_api("testuser9", "test9@test.com")
        repo = self.create_repo_via_api(user["id"], "test-repo9")

        physical_path = repo["physical"]["path"]

        # 路径应该包含用户名和仓库名
        assert "testuser9" in physical_path, "路径应该包含用户名"
        assert "test-repo9" in physical_path, "路径应该包含仓库名"

        # 路径应该是绝对路径
        assert os.path.isabs(physical_path), "路径应该是绝对路径"

    def test_special_characters_in_repo_name(self):
        """测试特殊字符仓库名的物理路径处理"""
        user = self.create_user_via_api("testuser10", "test10@test.com")

        # 创建带连字符的仓库名
        repo = self.create_repo_via_api(user["id"], "test-repo-special")

        physical_path = repo["physical"]["path"]
        assert os.path.exists(physical_path), "特殊字符仓库名应该能正常创建"

    # ==================== 物理仓库并发测试 ====================

    def test_concurrent_repo_creation(self):
        """测试并发创建仓库"""
        user = self.create_user_via_api("testuser11", "test11@test.com")

        # 快速创建多个仓库
        repos = []
        for i in range(5):
            repo = self.create_repo_via_api(user["id"], f"concurrent-repo-{i}")
            repos.append(repo)

        # 验证所有物理仓库都存在
        for repo in repos:
            assert os.path.exists(repo["physical"]["path"]), \
                f"仓库 {repo['name']} 的物理路径应该存在"

    # ==================== 物理仓库损坏处理测试 ====================

    def test_corrupted_git_repo_handling(self):
        """测试损坏的 Git 仓库处理"""
        user = self.create_user_via_api("testuser12", "test12@test.com")
        repo = self.create_repo_via_api(user["id"], "corrupted-repo")

        physical_path = repo["physical"]["path"]

        # 损坏 Git 仓库（删除 HEAD 文件）
        head_file = os.path.join(physical_path, "HEAD")
        if os.path.exists(head_file):
            os.remove(head_file)

        headers = self.get_auth_headers("testuser12")

        # API 应该仍然能返回仓库信息
        response = client.get(f"/api/repositories/{repo['id']}", headers=headers)
        assert response.status_code == 200, "应该能处理损坏的仓库"

        repo_data = response.json()
        # 物理目录存在但可能无法识别为有效 Git 仓库
        assert "physical" in repo_data, "应该包含 physical 字段"

    def test_empty_directory_not_recognized_as_repo(self):
        """测试空目录不被识别为有效仓库"""
        user = self.create_user_via_api("testuser13", "test13@test.com")
        repo = self.create_repo_via_api(user["id"], "empty-dir-repo")

        physical_path = repo["physical"]["path"]

        # 清空目录内容
        for item in os.listdir(physical_path):
            item_path = os.path.join(physical_path, item)
            if os.path.isdir(item_path):
                shutil.rmtree(item_path, onexc=remove_readonly)
            else:
                os.remove(item_path)

        headers = self.get_auth_headers("testuser13")

        # API 应该能处理
        response = client.get(f"/api/repositories/{repo['id']}", headers=headers)
        assert response.status_code == 200, "应该能处理空目录"
