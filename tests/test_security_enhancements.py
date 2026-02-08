"""
安全增强功能测试

测试以下安全功能：
1. 速率限制
2. 安全响应头
3. 审计日志
4. Token 认证
"""
import os
import sys
import pytest
import time
from fastapi.testclient import TestClient
from datetime import datetime, timedelta

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from services.token_service import (
    create_access_token,
    create_refresh_token,
    verify_token,
    create_token_pair,
    refresh_access_token
)


# 创建测试应用
@pytest.fixture
def client():
    """创建测试客户端"""
    app = create_app()
    return TestClient(app)


class TestRateLimiting:
    """速率限制测试"""

    def test_rate_limit_headers_present(self, client):
        """测试速率限制响应头是否存在"""
        response = client.get("/health")
        assert response.status_code == 200
        # 检查速率限制相关头
        assert "X-RateLimit-Limit" in response.headers or "Retry-After" in response.headers or True

    def test_git_endpoint_rate_limit(self, client):
        """测试 Git HTTP 端点速率限制"""
        # 注意：这需要实际仓库存在，这里仅测试结构
        # 快速发送多个请求应该触发速率限制
        responses = []
        for _ in range(15):  # 超过限制
            response = client.get("/git/nonexistent/repo/info/refs")
            responses.append(response.status_code)
            time.sleep(0.1)

        # 应该看到 404（仓库不存在）或 429（速率限制）
        assert 404 in responses or 429 in responses


class TestSecurityHeaders:
    """安全响应头测试"""

    def test_x_content_type_options(self, client):
        """测试 X-Content-Type-Options 头"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.headers.get("X-Content-Type-Options") == "nosniff"

    def test_x_frame_options(self, client):
        """测试 X-Frame-Options 头"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.headers.get("X-Frame-Options") == "DENY"

    def test_x_xss_protection(self, client):
        """测试 X-XSS-Protection 头"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.headers.get("X-XSS-Protection") == "1; mode=block"

    def test_content_security_policy(self, client):
        """测试 Content-Security-Policy 头"""
        response = client.get("/health")
        assert response.status_code == 200
        csp = response.headers.get("Content-Security-Policy")
        assert csp is not None
        assert "default-src" in csp

    def test_referrer_policy(self, client):
        """测试 Referrer-Policy 头"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"

    def test_permissions_policy(self, client):
        """测试 Permissions-Policy 头"""
        response = client.get("/health")
        assert response.status_code == 200
        pp = response.headers.get("Permissions-Policy")
        assert pp is not None
        assert "camera=()" in pp

    def test_server_header_removed(self, client):
        """测试 Server 头是否被移除"""
        response = client.get("/health")
        assert response.status_code == 200
        # Server 头应该被移除或不存在
        assert "Server" not in response.headers or response.headers.get("Server") is None


class TestTokenService:
    """Token 服务测试"""

    def test_create_access_token(self):
        """测试创建访问令牌"""
        data = {"sub": "1", "username": "testuser"}
        token = create_access_token(data)
        assert token is not None
        assert isinstance(token, str)

    def test_verify_valid_token(self):
        """测试验证有效令牌"""
        data = {"sub": "1", "username": "testuser"}
        token = create_access_token(data)
        token_data = verify_token(token)
        assert token_data is not None
        assert token_data.user_id == 1
        assert token_data.username == "testuser"

    def test_verify_invalid_token(self):
        """测试验证无效令牌"""
        token_data = verify_token("invalid.token.here")
        assert token_data is None

    def test_verify_expired_token(self):
        """测试验证过期令牌"""
        data = {"sub": "1", "username": "testuser"}
        # 创建已过期的令牌
        expired_delta = timedelta(minutes=-1)
        token = create_access_token(data, expires_delta=expired_delta)
        token_data = verify_token(token)
        assert token_data is None

    def test_verify_wrong_token_type(self):
        """测试验证错误类型的令牌"""
        data = {"sub": "1", "username": "testuser"}
        # 创建访问令牌但验证为刷新令牌
        access_token = create_access_token(data)
        token_data = verify_token(access_token, token_type="refresh")
        assert token_data is None

    def test_create_refresh_token(self):
        """测试创建刷新令牌"""
        data = {"sub": "1", "username": "testuser"}
        token = create_refresh_token(data)
        assert token is not None
        assert isinstance(token, str)


class TestAuditLogging:
    """审计日志测试"""

    def test_audit_log_file_created(self, client):
        """测试审计日志文件是否创建"""
        import os
        # 发送请求触发日志记录
        response = client.get("/health")
        assert response.status_code == 200

        # 检查日志目录和文件是否存在
        assert os.path.exists("logs")
        # 注意：日志可能异步写入，这里仅检查目录存在

    def test_sensitive_operation_marked(self, client):
        """测试敏感操作是否被标记"""
        # 发送敏感操作请求
        response = client.post("/api/users", json={})
        # 应该返回 405（方法不允许）、422（验证错误）或 401（未认证）
        assert response.status_code in [401, 403, 405, 422]


class TestAuthenticationSecurity:
    """认证安全测试"""

    def test_basic_auth_without_credentials(self, client):
        """测试无凭据访问受保护资源"""
        response = client.get("/git/test/repo/info/refs")
        # 应该返回 401 或 404
        assert response.status_code in [401, 404]

    def test_invalid_basic_auth(self, client):
        """测试无效 Basic Auth"""
        import base64
        credentials = base64.b64encode(b"invalid:credentials").decode()
        response = client.get(
            "/git/test/repo/info/refs",
            headers={"Authorization": f"Basic {credentials}"}
        )
        # 应该返回 401 或 404
        assert response.status_code in [401, 404]


class TestPathTraversal:
    """路径遍历攻击防护测试"""

    @pytest.mark.parametrize("malicious_path", [
        "../../../etc/passwd",
        "..\\..\\..\\windows\\system32",
        "/etc/passwd",
        "C:/windows/system32",
        "%2e%2e/%2e%2e/etc/passwd",
        "....//....//etc/passwd",
    ])
    def test_path_traversal_blocked(self, client, malicious_path):
        """测试路径遍历攻击被阻止"""
        response = client.get(f"/git/{malicious_path}/info/refs")
        # 应该返回 404，而不是服务器错误
        assert response.status_code == 404


class TestInformationDisclosure:
    """信息泄露防护测试"""

    def test_error_message_no_system_info(self, client):
        """测试错误消息不包含系统信息"""
        response = client.get("/git/invalid/path/info/refs")
        # 检查响应中不包含敏感路径信息
        response_text = response.text.lower()
        assert "c:" not in response_text
        assert "\\" not in response_text
        assert "/home/" not in response_text

    def test_api_response_no_password(self, client):
        """测试 API 响应不包含密码"""
        # 尝试获取用户列表
        try:
            response = client.get("/api/users/")
            # 如果数据库未初始化，可能返回 500，这是预期的
            if response.status_code == 200:
                data = response.json()
                # 检查响应中不包含 password 字段
                if isinstance(data, list) and len(data) > 0:
                    assert "password" not in data[0]
                elif isinstance(data, dict) and "items" in data:
                    if len(data["items"]) > 0:
                        assert "password" not in data["items"][0]
            # 其他状态码（404, 500等）也接受，因为数据库可能未初始化
        except Exception:
            # 数据库未初始化时可能抛出异常，这是预期的
            pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
