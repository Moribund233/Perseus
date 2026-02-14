"""
审计日志中间件测试

测试审计日志中间件的功能
"""
import pytest
import json
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from fastapi import Request, Response
from starlette.datastructures import Headers

from middleware.audit_logger import AuditLoggerMiddleware


class MockRequest:
    """模拟 FastAPI 请求对象"""
    def __init__(self, method="GET", path="/test", query="", headers=None, client_host="127.0.0.1"):
        self.method = method
        self.url = Mock()
        self.url.path = path
        self.url.query = query
        self.query_params = query
        self.headers = Headers(headers or {})
        self.client = Mock()
        self.client.host = client_host
        self.state = Mock()
        # 设置默认的 Mock 返回值
        self.state.user = None

    async def body(self):
        return b'{"test": "data"}'


class MockResponse:
    """模拟 FastAPI 响应对象"""
    def __init__(self, status_code=200):
        self.status_code = status_code


@pytest.fixture
def audit_middleware():
    """创建审计日志中间件实例"""
    app = Mock()
    return AuditLoggerMiddleware(app)


class TestAuditLoggerMiddleware:
    """测试审计日志中间件"""

    def test_should_log(self, audit_middleware):
        """测试日志记录判断"""
        # 应该记录的路径
        assert audit_middleware._should_log("/api/users") is True
        assert audit_middleware._should_log("/api/repositories") is True

        # 应该排除的路径
        assert audit_middleware._should_log("/health") is False
        assert audit_middleware._should_log("/docs") is False
        assert audit_middleware._should_log("/openapi.json") is False

    def test_is_sensitive_operation(self, audit_middleware):
        """测试敏感操作判断"""
        # 敏感方法
        assert audit_middleware._is_sensitive_operation("POST", "/api/users") is True
        assert audit_middleware._is_sensitive_operation("DELETE", "/api/repos") is True
        assert audit_middleware._is_sensitive_operation("PUT", "/api/data") is True

        # 敏感路径 - GET 方法但路径敏感（/api/users 在敏感路径列表中）
        assert audit_middleware._is_sensitive_operation("GET", "/git/repo/info") is True
        assert audit_middleware._is_sensitive_operation("GET", "/login") is True
        assert audit_middleware._is_sensitive_operation("POST", "/auth/token") is True
        # /api/users 在 SENSITIVE_PATHS 中，所以 GET 也是敏感的
        assert audit_middleware._is_sensitive_operation("GET", "/api/users") is True

        # 非敏感操作 - GET 非敏感路径
        assert audit_middleware._is_sensitive_operation("GET", "/health") is False
        assert audit_middleware._is_sensitive_operation("GET", "/api/other") is False

    def test_get_client_ip(self, audit_middleware):
        """测试获取客户端 IP"""
        # 从 X-Forwarded-For 获取
        request = MockRequest(headers={"X-Forwarded-For": "192.168.1.1, 10.0.0.1"})
        assert audit_middleware._get_client_ip(request) == "192.168.1.1"

        # 从 X-Real-IP 获取
        request = MockRequest(headers={"X-Real-IP": "192.168.1.2"})
        assert audit_middleware._get_client_ip(request) == "192.168.1.2"

        # 从 client.host 获取
        request = MockRequest(client_host="192.168.1.3")
        assert audit_middleware._get_client_ip(request) == "192.168.1.3"

        # 未知 IP
        request = MockRequest()
        request.client = None
        assert audit_middleware._get_client_ip(request) == "unknown"

    def test_get_user_info_no_auth(self, audit_middleware):
        """测试获取用户信息 - 无认证"""
        request = MockRequest()
        # 创建一个没有 user 属性的 state 对象
        request.state = Mock(spec=[])
        user_info = audit_middleware._get_user_info(request)

        assert user_info["user_id"] is None
        assert user_info["username"] is None
        assert user_info["auth_type"] is None

    def test_get_user_info_basic_auth(self, audit_middleware):
        """测试获取用户信息 - Basic Auth"""
        request = MockRequest(headers={"Authorization": "Basic dXNlcjpwYXNz"})
        user_info = audit_middleware._get_user_info(request)

        assert user_info["auth_type"] == "basic"

    def test_get_user_info_bearer_auth(self, audit_middleware):
        """测试获取用户信息 - Bearer Token"""
        request = MockRequest(headers={"Authorization": "Bearer token123"})
        user_info = audit_middleware._get_user_info(request)

        assert user_info["auth_type"] == "bearer"

    def test_get_user_info_with_state_user(self, audit_middleware):
        """测试获取用户信息 - 从 state 获取"""
        request = MockRequest()
        request.state.user = Mock()
        request.state.user.id = 123
        request.state.user.username = "testuser"

        user_info = audit_middleware._get_user_info(request)

        assert user_info["user_id"] == 123
        assert user_info["username"] == "testuser"
        assert user_info["auth_type"] == "token"

    @pytest.mark.asyncio
    async def test_dispatch_excluded_path(self, audit_middleware):
        """测试排除路径不记录日志"""
        request = MockRequest(path="/health")
        call_next = AsyncMock(return_value=MockResponse())

        with patch.object(audit_middleware._audit_logger, 'info') as mock_log:
            response = await audit_middleware.dispatch(request, call_next)

        mock_log.assert_not_called()
        call_next.assert_called_once()

    @pytest.mark.asyncio
    async def test_dispatch_logs_request(self, audit_middleware):
        """测试正常请求记录日志"""
        request = MockRequest(method="GET", path="/api/test")
        call_next = AsyncMock(return_value=MockResponse(200))

        with patch.object(audit_middleware._audit_logger, 'info') as mock_log:
            response = await audit_middleware.dispatch(request, call_next)

        mock_log.assert_called_once()
        log_call = mock_log.call_args[0][0]
        assert "GET" in log_call
        assert "/api/test" in log_call
        assert '"status_code": 200' in log_call

    @pytest.mark.asyncio
    async def test_dispatch_logs_sensitive_operation(self, audit_middleware):
        """测试敏感操作记录日志"""
        request = MockRequest(method="POST", path="/api/users")
        call_next = AsyncMock(return_value=MockResponse(201))

        with patch.object(audit_middleware._audit_logger, 'info') as mock_log:
            response = await audit_middleware.dispatch(request, call_next)

        mock_log.assert_called_once()
        log_call = mock_log.call_args[0][0]
        assert "[SENSITIVE]" in log_call
        assert '"is_sensitive": true' in log_call

    @pytest.mark.asyncio
    async def test_dispatch_logs_error_status(self, audit_middleware):
        """测试错误状态码记录日志"""
        request = MockRequest(method="GET", path="/api/test")
        call_next = AsyncMock(return_value=MockResponse(404))

        with patch.object(audit_middleware._audit_logger, 'warning') as mock_log:
            response = await audit_middleware.dispatch(request, call_next)

        mock_log.assert_called_once()
        log_call = mock_log.call_args[0][0]
        assert '"status_code": 404' in log_call

    @pytest.mark.asyncio
    async def test_dispatch_logs_server_error(self, audit_middleware):
        """测试服务器错误记录日志"""
        request = MockRequest(method="GET", path="/api/test")
        call_next = AsyncMock(return_value=MockResponse(500))

        with patch.object(audit_middleware._audit_logger, 'error') as mock_log:
            response = await audit_middleware.dispatch(request, call_next)

        mock_log.assert_called_once()
        log_call = mock_log.call_args[0][0]
        assert '"status_code": 500' in log_call

    @pytest.mark.asyncio
    async def test_dispatch_request_id_set(self, audit_middleware):
        """测试请求 ID 被设置到 state"""
        request = MockRequest(path="/api/test")
        call_next = AsyncMock(return_value=MockResponse(200))

        with patch.object(audit_middleware._audit_logger, 'info'):
            response = await audit_middleware.dispatch(request, call_next)

        assert hasattr(request.state, 'request_id')
        assert len(request.state.request_id) == 8

    def test_audit_entry_structure(self, audit_middleware):
        """测试审计日志条目结构"""
        # 验证中间件配置
        assert audit_middleware.enabled is True
        assert "/health" in audit_middleware.exclude_paths
        assert "/docs" in audit_middleware.exclude_paths

        # 验证敏感路径配置
        assert "/git/" in audit_middleware.SENSITIVE_PATHS
        assert "/api/users" in audit_middleware.SENSITIVE_PATHS
        assert "/login" in audit_middleware.SENSITIVE_PATHS

        # 验证敏感方法配置
        assert "POST" in audit_middleware.SENSITIVE_METHODS
        assert "DELETE" in audit_middleware.SENSITIVE_METHODS
