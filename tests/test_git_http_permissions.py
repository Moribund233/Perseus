"""
Git HTTP 权限边界测试模块

测试各种权限场景下的 Git HTTP 访问控制:
1. 匿名用户访问公开/私有仓库
2. 只读成员权限测试
3. 开发者权限测试
4. 管理员权限测试
5. 跨仓库访问测试
"""
import os
import sys
import shutil
import base64
import stat
import pytest

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
from models.repository_member import RepositoryMember
from app import create_app
from services.token_service import create_access_token

TEST_DATABASE_URL = "sqlite:///./test_git_http_permissions.db"
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


class TestGitHttpPermissionBoundaries:
    """Git HTTP 权限边界测试类"""

    @pytest.fixture(autouse=True)
    def setup_and_cleanup(self):
        """测试前设置和测试后清理"""
        db = TestingSessionLocal()
        db.query(RepositoryMember).delete()
        db.query(Repository).delete()
        db.query(User).delete()
        db.commit()
        db.close()

        repo_root = "./repositories"
        if os.path.exists(repo_root):
            shutil.rmtree(repo_root, onexc=remove_readonly)

        yield

        db = TestingSessionLocal()
        db.query(RepositoryMember).delete()
        db.query(Repository).delete()
        db.query(User).delete()
        db.commit()
        db.close()

        if os.path.exists(repo_root):
            shutil.rmtree(repo_root, onexc=remove_readonly)

    def create_user(self, username, email, password="testpass123", is_admin=False):
        """创建测试用户"""
        db = TestingSessionLocal()
        try:
            user = User(
                username=username,
                email=email,
                password=password,
                full_name=f"Test {username}",
                is_active=True,
                is_admin=is_admin
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            return user
        finally:
            db.close()

    def create_repo(self, owner_id, name, is_public=True):
        """创建测试仓库"""
        db = TestingSessionLocal()
        try:
            owner = db.query(User).filter(User.id == owner_id).first()
            repo = Repository(
                name=name,
                description=f"Test repo {name}",
                is_public=is_public,
                owner_id=owner_id,
                path=f"{owner.username}/{name}"
            )
            db.add(repo)
            db.commit()
            db.refresh(repo)
            return repo
        finally:
            db.close()

    def add_member(self, repo_id, user_id, role):
        """添加仓库成员"""
        db = TestingSessionLocal()
        try:
            member = RepositoryMember(
                repository_id=repo_id,
                user_id=user_id,
                role=role
            )
            db.add(member)
            db.commit()
            return member
        finally:
            db.close()

    def get_basic_auth_header(self, username, password):
        """获取 Basic Auth 请求头"""
        credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
        return {"Authorization": f"Basic {credentials}"}

    def get_bearer_auth_header(self, user_id, username, is_admin=False):
        """获取 Bearer Token 请求头"""
        token = create_access_token({
            "sub": str(user_id),
            "username": username,
            "is_admin": is_admin
        })
        return {"Authorization": f"Bearer {token}"}

    # ==================== 匿名用户访问测试 ====================

    def test_anonymous_access_public_repo_read(self):
        """测试匿名用户读取公开仓库 - 应该允许"""
        owner = self.create_user("owner1", "owner1@test.com")
        repo = self.create_repo(owner.id, "public-repo", is_public=True)

        response = client.get(f"/git/owner1/public-repo/info/refs")
        assert response.status_code == 200, "匿名用户应该能读取公开仓库"

    def test_anonymous_access_private_repo_read(self):
        """测试匿名用户读取私有仓库 - 应该拒绝"""
        owner = self.create_user("owner2", "owner2@test.com")
        repo = self.create_repo(owner.id, "private-repo", is_public=False)

        response = client.get(f"/git/owner2/private-repo/info/refs")
        assert response.status_code == 401, "匿名用户不应该能读取私有仓库"

    def test_anonymous_push_to_public_repo(self):
        """测试匿名用户推送到公开仓库 - 应该拒绝"""
        owner = self.create_user("owner3", "owner3@test.com")
        repo = self.create_repo(owner.id, "public-repo-push", is_public=True)

        response = client.post(
            f"/git/owner3/public-repo-push/git-receive-pack",
            content=b"0000",
            headers={"Content-Type": "application/x-git-receive-pack-request"}
        )
        assert response.status_code == 401, "匿名用户不应该能推送"

    # ==================== 只读成员权限测试 ====================

    def test_readonly_member_can_clone(self):
        """测试只读成员可以克隆仓库"""
        owner = self.create_user("owner4", "owner4@test.com")
        repo = self.create_repo(owner.id, "repo-readonly", is_public=False)
        readonly_user = self.create_user("readonly", "readonly@test.com")
        self.add_member(repo.id, readonly_user.id, "readonly")

        headers = self.get_basic_auth_header("readonly", "testpass123")
        response = client.get(
            f"/git/owner4/repo-readonly/info/refs?service=git-upload-pack",
            headers=headers
        )
        assert response.status_code == 200, "只读成员应该能克隆"

    def test_readonly_member_cannot_push(self):
        """测试只读成员不能推送"""
        owner = self.create_user("owner5", "owner5@test.com")
        repo = self.create_repo(owner.id, "repo-no-push", is_public=False)
        readonly_user = self.create_user("readonly2", "readonly2@test.com")
        self.add_member(repo.id, readonly_user.id, "readonly")

        headers = self.get_basic_auth_header("readonly2", "testpass123")
        headers["Content-Type"] = "application/x-git-receive-pack-request"

        response = client.post(
            f"/git/owner5/repo-no-push/git-receive-pack",
            content=b"0000",
            headers=headers
        )
        assert response.status_code == 403, "只读成员不应该能推送"

    # ==================== 开发者权限测试 ====================

    def test_developer_can_clone(self):
        """测试开发者可以克隆仓库"""
        owner = self.create_user("owner6", "owner6@test.com")
        repo = self.create_repo(owner.id, "repo-dev", is_public=False)
        dev_user = self.create_user("developer", "dev@test.com")
        self.add_member(repo.id, dev_user.id, "developer")

        headers = self.get_basic_auth_header("developer", "testpass123")
        response = client.get(
            f"/git/owner6/repo-dev/info/refs?service=git-upload-pack",
            headers=headers
        )
        assert response.status_code == 200, "开发者应该能克隆"

    def test_developer_can_push(self):
        """测试开发者可以推送"""
        owner = self.create_user("owner7", "owner7@test.com")
        repo = self.create_repo(owner.id, "repo-dev-push", is_public=False)
        dev_user = self.create_user("developer2", "dev2@test.com")
        self.add_member(repo.id, dev_user.id, "developer")

        headers = self.get_basic_auth_header("developer2", "testpass123")
        headers["Content-Type"] = "application/x-git-receive-pack-request"

        response = client.post(
            f"/git/owner7/repo-dev-push/git-receive-pack",
            content=b"0000",
            headers=headers
        )
        # 空内容可能返回500，但不应该返回401/403
        assert response.status_code != 401 and response.status_code != 403, "开发者应该能推送"

    # ==================== 管理员权限测试 ====================

    def test_admin_can_clone_any_repo(self):
        """测试管理员可以克隆任何仓库"""
        owner = self.create_user("owner8", "owner8@test.com")
        repo = self.create_repo(owner.id, "repo-admin", is_public=False)
        admin_user = self.create_user("admin", "admin@test.com", is_admin=True)

        headers = self.get_basic_auth_header("admin", "testpass123")
        response = client.get(
            f"/git/owner8/repo-admin/info/refs?service=git-upload-pack",
            headers=headers
        )
        assert response.status_code == 200, "管理员应该能克隆任何仓库"

    def test_admin_can_push_to_any_repo(self):
        """测试管理员可以推送到任何仓库"""
        owner = self.create_user("owner9", "owner9@test.com")
        repo = self.create_repo(owner.id, "repo-admin-push", is_public=False)
        admin_user = self.create_user("admin2", "admin2@test.com", is_admin=True)

        headers = self.get_basic_auth_header("admin2", "testpass123")
        headers["Content-Type"] = "application/x-git-receive-pack-request"

        response = client.post(
            f"/git/owner9/repo-admin-push/git-receive-pack",
            content=b"0000",
            headers=headers
        )
        # 空内容可能返回500，但不应该返回401/403
        assert response.status_code != 401 and response.status_code != 403, "管理员应该能推送到任何仓库"

    # ==================== 跨仓库访问测试 ====================

    def test_user_cannot_access_other_private_repo(self):
        """测试用户不能访问其他用户的私有仓库"""
        owner = self.create_user("owner10", "owner10@test.com")
        repo = self.create_repo(owner.id, "private-others", is_public=False)
        other_user = self.create_user("other", "other@test.com")

        headers = self.get_basic_auth_header("other", "testpass123")
        response = client.get(
            f"/git/owner10/private-others/info/refs",
            headers=headers
        )
        assert response.status_code == 403, "用户不应该能访问其他用户的私有仓库"

    def test_non_member_cannot_push_to_public_repo(self):
        """测试非成员不能推送到公开仓库"""
        owner = self.create_user("owner11", "owner11@test.com")
        repo = self.create_repo(owner.id, "public-no-push", is_public=True)
        non_member = self.create_user("nonmember", "nonmember@test.com")

        headers = self.get_basic_auth_header("nonmember", "testpass123")
        headers["Content-Type"] = "application/x-git-receive-pack-request"

        response = client.post(
            f"/git/owner11/public-no-push/git-receive-pack",
            content=b"0000",
            headers=headers
        )
        assert response.status_code == 403, "非成员不应该能推送到公开仓库"

    # ==================== 认证方式测试 ====================

    def test_bearer_token_auth_for_clone(self):
        """测试 Bearer Token 认证用于克隆"""
        owner = self.create_user("owner12", "owner12@test.com")
        repo = self.create_repo(owner.id, "repo-bearer", is_public=False)

        headers = self.get_bearer_auth_header(owner.id, "owner12")
        response = client.get(
            f"/git/owner12/repo-bearer/info/refs?service=git-upload-pack",
            headers=headers
        )
        assert response.status_code == 200, "Bearer Token 应该能用于克隆"

    def test_invalid_basic_auth(self):
        """测试无效的 Basic 认证"""
        owner = self.create_user("owner13", "owner13@test.com")
        repo = self.create_repo(owner.id, "repo-invalid", is_public=False)

        headers = self.get_basic_auth_header("owner13", "wrongpassword")
        response = client.get(
            f"/git/owner13/repo-invalid/info/refs",
            headers=headers
        )
        assert response.status_code == 401, "无效密码应该返回 401"

    def test_malformed_auth_header(self):
        """测试格式错误的认证头"""
        owner = self.create_user("owner14", "owner14@test.com")
        repo = self.create_repo(owner.id, "repo-malformed", is_public=False)

        headers = {"Authorization": "InvalidFormat token123"}
        response = client.get(
            f"/git/owner14/repo-malformed/info/refs",
            headers=headers
        )
        # 应该返回 401 或 403，而不是 500
        assert response.status_code in [401, 403], "格式错误的认证头应该返回 401/403"
