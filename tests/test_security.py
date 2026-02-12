"""
服务安全性测试模块

测试各种安全隐患，包括：
1. 路径遍历攻击防护
2. 目录穿越攻击防护
3. 敏感信息泄露防护
4. 权限绕过防护
5. SQL 注入防护
6. 命令注入防护
7. 物理仓库路径安全

使用方法:
    python -m pytest tests/test_security.py -v
"""
import os
import sys
import pytest
import base64
import shutil
import stat
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
from utils.git_utils import get_repository_storage_path, init_bare_repo


# 测试数据库配置
TEST_DATABASE_URL = "sqlite:///./test_security.db"

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
TEST_USERNAME = "securityuser"
TEST_PASSWORD = "securepass123"
TEST_EMAIL = "security@example.com"
TEST_REPO_NAME = "security-test-repo"


class TestPathTraversalSecurity:
    """路径遍历攻击安全测试"""

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

    def create_test_user(self, username=TEST_USERNAME, password=TEST_PASSWORD, email=TEST_EMAIL):
        """创建测试用户"""
        response = client.post("/api/users/", json={
            "username": username,
            "password": password,
            "email": email,
            "full_name": "Security Test User"
        })
        if response.status_code == 200:
            return response.json()
        return None

    def create_test_repo(self, user_id, repo_name=TEST_REPO_NAME, is_public=True):
        """创建测试仓库"""
        response = client.post("/api/repositories/", json={
            "name": repo_name,
            "description": "Security test repository",
            "is_public": is_public,
            "owner_id": user_id,
            "path": f"{TEST_USERNAME}/{repo_name}"
        })
        if response.status_code == 200:
            return response.json()
        return None

    def test_path_traversal_dotdot(self):
        """测试目录穿越攻击防护 (../)"""
        malicious_paths = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "user/../admin/repo",
            "user/..\\..\\other/repo",
            "./../etc/hosts",
            "user/repo/../../../etc/shadow",
        ]

        for path in malicious_paths:
            # 测试引用发现端点
            response = client.get(f"/git/{path}/info/refs")
            # 应该返回 404 而不是暴露文件系统结构
            assert response.status_code in [404, 400], \
                f"路径遍历攻击未防护: {path}, 返回: {response.status_code}"

            # 测试 upload-pack 端点
            response = client.post(f"/git/{path}/git-upload-pack", content=b"0000")
            assert response.status_code in [404, 400], \
                f"路径遍历攻击未防护 (upload-pack): {path}"

            # 测试 receive-pack 端点
            response = client.post(f"/git/{path}/git-receive-pack", content=b"0000")
            assert response.status_code in [404, 400], \
                f"路径遍历攻击未防护 (receive-pack): {path}"

    def test_path_traversal_null_byte(self):
        """测试空字节注入攻击防护"""
        # 注意：httpx 测试客户端会在发送请求前拒绝包含空字节的 URL
        # 这是客户端行为，不是服务器防护
        # 实际服务器应该通过输入验证来防护空字节注入

        # 测试 URL 编码的空字节
        path = "user/repo%00/../../etc/passwd"
        response = client.get(f"/git/{path}/info/refs")
        # 应该返回 400 错误（无效路径）或 404
        assert response.status_code in [400, 404, 422], \
            f"空字节注入攻击未防护: {path}"

    def test_path_traversal_absolute_path(self):
        """测试绝对路径攻击防护"""
        malicious_paths = [
            "/etc/passwd",
            "/windows/system32/config/sam",
            "C:/windows/system32/config/sam",
            "C:\\windows\\system32\\config\\sam",
            "/root/.ssh/id_rsa",
        ]

        for path in malicious_paths:
            response = client.get(f"/git/{path}/info/refs")
            assert response.status_code in [404, 400], \
                f"绝对路径攻击未防护: {path}"

    def test_path_traversal_special_chars(self):
        """测试特殊字符路径攻击防护"""
        malicious_paths = [
            "user/repo/.git/config",
            "user/repo/.git/hooks/post-checkout",
            "user/repo/..%2f..%2f..%2fetc%2fpasswd",  # URL 编码的 ../
            "user/repo/%2e%2e/%2e%2e/%2e%2e/etc/passwd",
        ]

        for path in malicious_paths:
            response = client.get(f"/git/{path}/info/refs")
            # 不应该成功访问系统文件
            assert response.status_code in [404, 400], \
                f"特殊字符路径攻击未防护: {path}"


class TestSensitiveInformationLeakage:
    """敏感信息泄露测试"""

    @pytest.fixture(autouse=True)
    def setup_and_cleanup(self):
        """测试前设置和测试后清理"""
        db = TestingSessionLocal()
        from models.repository_member import RepositoryMember
        from models.repository import Repository
        from models.user import User

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

    def test_user_password_not_in_response(self):
        """测试用户密码不在 API 响应中"""
        # 创建用户
        response = client.post("/api/users/", json={
            "username": "testuser123",
            "password": "secretpassword123",
            "email": "test123@example.com",
            "full_name": "Test User"
        })

        assert response.status_code == 200
        user_data = response.json()

        # 检查响应中不包含密码
        assert "password" not in user_data, \
            "用户创建响应中不应该包含密码字段"

        # 获取用户列表
        response = client.get("/api/users/")
        assert response.status_code == 200
        users = response.json()

        for user in users:
            assert "password" not in user, \
                f"用户列表响应中不应该包含密码字段: {user}"

        # 获取单个用户
        response = client.get(f"/api/users/{user_data['id']}")
        assert response.status_code == 200
        user = response.json()

        assert "password" not in user, \
            "用户详情响应中不应该包含密码字段"

    def test_error_messages_not_leak_info(self):
        """测试错误消息不泄露敏感信息"""
        # 测试不存在的仓库
        response = client.get("/git/nonexistent/repo/info/refs")
        assert response.status_code == 404

        error_data = response.json()
        # 错误消息不应该包含物理路径信息
        if "detail" in error_data:
            assert "repositories" not in str(error_data["detail"]).lower(), \
                "错误消息不应该包含物理路径信息"
            assert "\\" not in str(error_data["detail"]), \
                "错误消息不应该包含 Windows 路径分隔符"

    def test_repository_physical_path_not_exposed(self):
        """测试仓库物理路径不暴露给客户端"""
        # 创建用户和仓库
        response = client.post("/api/users/", json={
            "username": "pathtest",
            "password": "testpass123",
            "email": "pathtest@example.com"
        })
        assert response.status_code == 200
        user = response.json()

        response = client.post("/api/repositories/", json={
            "name": "path-test-repo",
            "description": "Test repo",
            "is_public": True,
            "owner_id": user["id"],
            "path": f"pathtest/path-test-repo"
        })
        assert response.status_code == 200
        repo = response.json()

        # 检查响应中不包含敏感路径信息
        repo_str = str(repo)

        # 不应该包含物理路径相关的敏感信息
        assert "repositories" not in repo_str.lower(), \
            "API 响应不应该暴露物理存储路径 (repositories)"

        # 不应该包含 Windows 路径分隔符（暴露服务器是 Windows）
        assert "\\\\" not in repo_str, \
            "API 响应不应该包含 Windows 路径分隔符"

        # 不应该包含 Unix 绝对路径
        assert "./repositories" not in repo_str, \
            "API 响应不应该包含相对物理路径"

        # 应该使用安全的 status 字段替代 physical
        assert "status" in repo, \
            "API 响应应该包含 status 字段"
        assert "initialized" in repo.get("status", {}), \
            "status 字段应该包含 initialized 状态"


class TestAuthenticationSecurity:
    """认证安全测试"""

    @pytest.fixture(autouse=True)
    def setup_and_cleanup(self):
        """测试前设置和测试后清理"""
        db = TestingSessionLocal()
        from models.repository_member import RepositoryMember
        from models.repository import Repository
        from models.user import User

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

    def test_private_repo_requires_auth(self):
        """测试私有仓库需要认证"""
        # 创建用户和私有仓库
        response = client.post("/api/users/", json={
            "username": "privateuser",
            "password": "privatepass123",
            "email": "private@example.com"
        })
        assert response.status_code == 200
        user = response.json()

        response = client.post("/api/repositories/", json={
            "name": "private-repo",
            "description": "Private test repo",
            "is_public": False,
            "owner_id": user["id"],
            "path": f"privateuser/private-repo"
        })
        assert response.status_code == 200

        # 未认证访问应该返回 401
        response = client.get("/git/privateuser/private-repo/info/refs")
        assert response.status_code == 401, \
            "私有仓库应该要求认证"

        # 错误的认证信息应该返回 401
        wrong_auth = base64.b64encode(b"wronguser:wrongpass").decode()
        response = client.get(
            "/git/privateuser/private-repo/info/refs",
            headers={"Authorization": f"Basic {wrong_auth}"}
        )
        assert response.status_code == 401, \
            "错误的认证信息应该返回 401"

    def test_receive_pack_requires_write_permission(self):
        """测试 receive-pack 需要写权限"""
        # 创建用户和公开仓库
        response = client.post("/api/users/", json={
            "username": "writeuser",
            "password": "writepass123",
            "email": "write@example.com"
        })
        assert response.status_code == 200
        user = response.json()

        response = client.post("/api/repositories/", json={
            "name": "write-test-repo",
            "description": "Write test repo",
            "is_public": True,
            "owner_id": user["id"],
            "path": f"writeuser/write-test-repo"
        })
        assert response.status_code == 200

        # 未认证的 receive-pack 应该返回 401
        response = client.post(
            "/git/writeuser/write-test-repo/git-receive-pack",
            content=b"0000"
        )
        assert response.status_code == 401, \
            "receive-pack 应该要求认证"

    def test_sql_injection_in_username(self):
        """测试用户名 SQL 注入防护"""
        malicious_usernames = [
            "user' OR '1'='1",
            "user'; DROP TABLE users; --",
            "user' UNION SELECT * FROM users --",
            "user\" OR \"1\"=\"1",
        ]

        for username in malicious_usernames:
            response = client.post("/api/users/", json={
                "username": username,
                "password": "testpass123",
                "email": f"{username.replace(' ', '_')}@example.com"
            })
            # 应该返回 200（创建成功）或 409（用户名已存在）或 422（验证错误）
            # 不应该返回 500（服务器错误）
            assert response.status_code in [200, 409, 422], \
                f"SQL 注入攻击可能导致服务器错误: {username}"


class TestRepositoryStorageSecurity:
    """仓库存储安全测试"""

    @pytest.fixture(autouse=True)
    def setup_and_cleanup(self):
        """测试前设置和测试后清理"""
        db = TestingSessionLocal()
        from models.repository_member import RepositoryMember
        from models.repository import Repository
        from models.user import User

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

    def test_repository_path_normalization(self):
        """测试仓库路径规范化"""
        from utils.git_utils import get_repository_storage_path

        # 测试正常路径
        normal_path = get_repository_storage_path("user/repo")
        assert ".." not in normal_path, "路径应该被规范化"

        # 测试包含 .. 的路径
        suspicious_path = get_repository_storage_path("user/../other/repo")
        # 应该被规范化，不包含 ..
        assert ".." not in suspicious_path, "路径应该被规范化，移除 .."

    def test_repository_outside_root_not_accessible(self):
        """测试无法访问仓库根目录之外的文件"""
        from utils.git_utils import get_repository_storage_path

        # 获取仓库根目录
        repo_root = "./repositories"
        abs_repo_root = os.path.abspath(repo_root)

        # 尝试构造路径遍历
        malicious_repo_path = "../../../etc/passwd"
        physical_path = get_repository_storage_path(malicious_repo_path)

        # 物理路径应该仍然在仓库根目录内
        abs_physical_path = os.path.abspath(physical_path)

        # 确保路径在仓库根目录内
        assert abs_physical_path.startswith(abs_repo_root) or \
               not os.path.exists(abs_physical_path), \
            f"路径遍历可能导致访问仓库根目录之外的文件: {abs_physical_path}"


class TestGitObjectSecurity:
    """Git 对象安全测试"""

    @pytest.fixture(autouse=True)
    def setup_and_cleanup(self):
        """测试前设置和测试后清理"""
        db = TestingSessionLocal()
        from models.repository_member import RepositoryMember
        from models.repository import Repository
        from models.user import User

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

    def test_git_object_path_validation(self):
        """测试 Git 对象路径验证"""
        # 创建用户和仓库
        response = client.post("/api/users/", json={
            "username": "objuser",
            "password": "objpass123",
            "email": "obj@example.com"
        })
        assert response.status_code == 200
        user = response.json()

        response = client.post("/api/repositories/", json={
            "name": "obj-test-repo",
            "description": "Object test repo",
            "is_public": True,
            "owner_id": user["id"],
            "path": f"objuser/obj-test-repo"
        })
        assert response.status_code == 200

        # 尝试访问恶意对象路径
        malicious_oids = [
            "../../../etc/passwd",
            "..%2f..%2f..%2fetc%2fpasswd",
            ".git/config",
            "hooks/post-checkout",
        ]

        for oid in malicious_oids:
            response = client.get(f"/git/objuser/obj-test-repo/objects/{oid}")
            # 应该返回 404，不应该暴露文件系统信息
            assert response.status_code == 404, \
                f"恶意对象路径应该返回 404: {oid}"


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])
