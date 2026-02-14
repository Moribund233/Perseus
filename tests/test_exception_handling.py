"""
异常处理测试模块

测试自定义异常类和异常处理器的功能
"""
import pytest
from fastapi import Request
from fastapi.responses import JSONResponse

from exception import (
    BaseException,
    ValidationException,
    AuthenticationException,
    AuthorizationException,
    NotFoundException,
    ConflictException,
    DatabaseException,
    FileException,
    RepositoryBrowserException,
    RepositoryNotFoundException,
    PathNotFoundException,
    InvalidPathException,
)
from utils.exception_handler import (
    global_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)


class MockRequest:
    """模拟请求对象"""
    def __init__(self):
        self.state = type('State', (), {})()


class TestCustomExceptions:
    """测试自定义异常类"""

    def test_validation_exception(self):
        """测试验证异常"""
        exc = ValidationException("参数验证失败")
        assert exc.status_code == 400
        assert exc.detail == "参数验证失败"

    def test_authentication_exception(self):
        """测试认证异常"""
        exc = AuthenticationException("认证失败")
        assert exc.status_code == 401
        assert "WWW-Authenticate" in exc.headers

    def test_authorization_exception(self):
        """测试授权异常"""
        exc = AuthorizationException("权限不足")
        assert exc.status_code == 403
        assert exc.detail == "权限不足"

    def test_not_found_exception(self):
        """测试资源不存在异常"""
        exc = NotFoundException("用户不存在")
        assert exc.status_code == 404
        assert exc.detail == "用户不存在"

    def test_conflict_exception(self):
        """测试资源冲突异常"""
        exc = ConflictException("资源已存在")
        assert exc.status_code == 409
        assert exc.detail == "资源已存在"

    def test_database_exception(self):
        """测试数据库异常"""
        exc = DatabaseException("数据库连接失败")
        assert exc.status_code == 500
        assert exc.detail == "数据库连接失败"

    def test_file_exception(self):
        """测试文件操作异常"""
        exc = FileException("文件读取失败")
        assert exc.status_code == 500
        assert exc.detail == "文件读取失败"

    def test_repository_browser_exceptions(self):
        """测试仓库浏览器异常"""
        exc1 = RepositoryNotFoundException("仓库不存在")
        assert exc1.status_code == 404

        exc2 = PathNotFoundException("路径不存在")
        assert exc2.status_code == 404

        exc3 = InvalidPathException("无效路径")
        assert exc3.status_code == 400


class TestExceptionHandlers:
    """测试异常处理器"""

    @pytest.fixture
    def mock_request(self):
        """创建模拟请求"""
        return MockRequest()

    @pytest.mark.asyncio
    async def test_validation_exception_handler(self, mock_request):
        """测试验证异常处理器"""
        exc = ValidationException("参数错误")
        response = await global_exception_handler(mock_request, exc)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 400
        import json
        data = json.loads(response.body)
        assert data["error"]["code"] == 400
        assert "参数错误" in data["error"]["message"]

    @pytest.mark.asyncio
    async def test_not_found_exception_handler(self, mock_request):
        """测试资源不存在异常处理器"""
        exc = NotFoundException("用户不存在")
        response = await global_exception_handler(mock_request, exc)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 404
        import json
        data = json.loads(response.body)
        assert data["error"]["code"] == 404

    @pytest.mark.asyncio
    async def test_database_exception_handler(self, mock_request):
        """测试数据库异常处理器"""
        exc = DatabaseException("数据库错误")
        response = await global_exception_handler(mock_request, exc)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 500
        import json
        data = json.loads(response.body)
        assert data["error"]["code"] == 500

    @pytest.mark.asyncio
    async def test_generic_exception_handler(self, mock_request):
        """测试通用异常处理器"""
        exc = ValueError("普通错误")
        response = await global_exception_handler(mock_request, exc)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_http_exception_handler(self, mock_request):
        """测试HTTP异常处理器"""
        from fastapi import HTTPException

        exc = HTTPException(status_code=403, detail="禁止访问")
        response = await http_exception_handler(mock_request, exc)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_http_exception_handler_5xx(self, mock_request):
        """测试HTTP 5xx异常处理器"""
        from fastapi import HTTPException

        exc = HTTPException(status_code=503, detail="服务不可用")
        response = await http_exception_handler(mock_request, exc)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 503

    @pytest.mark.asyncio
    async def test_validation_error_handler(self, mock_request):
        """测试Pydantic验证错误处理器"""
        from pydantic import ValidationError

        # 创建一个模拟的验证错误
        exc = ValidationError.from_exception_data(
            "test",
            [
                {
                    "type": "missing",
                    "loc": ("field1",),
                    "msg": "字段缺失",
                    "input": None,
                }
            ],
        )
        response = await validation_exception_handler(mock_request, exc)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 400
        import json
        data = json.loads(response.body)
        assert data["error"]["code"] == 400
        assert "Validation Error" in data["error"]["message"]


class TestExceptionResponseFormat:
    """测试异常响应格式"""

    @pytest.fixture
    def mock_request(self):
        """创建模拟请求"""
        return MockRequest()

    @pytest.mark.asyncio
    async def test_error_response_structure(self, mock_request):
        """测试错误响应结构"""
        exc = ValidationException("测试错误")
        response = await global_exception_handler(mock_request, exc)

        import json
        data = json.loads(response.body)

        # 验证响应结构
        assert "detail" in data
        assert "error" in data
        assert "code" in data["error"]
        assert "message" in data["error"]
        assert "type" in data["error"]

    @pytest.mark.asyncio
    async def test_error_code_consistency(self, mock_request):
        """测试错误码一致性"""
        test_cases = [
            (ValidationException("错误"), 400),
            (AuthenticationException("错误"), 401),
            (AuthorizationException("错误"), 403),
            (NotFoundException("错误"), 404),
            (ConflictException("错误"), 409),
            (DatabaseException("错误"), 500),
            (FileException("错误"), 500),
        ]

        for exc, expected_code in test_cases:
            response = await global_exception_handler(mock_request, exc)
            assert response.status_code == expected_code

            import json
            data = json.loads(response.body)
            assert data["error"]["code"] == expected_code
