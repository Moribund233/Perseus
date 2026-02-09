"""
测试代码重构后的核心功能

验证以下模块是否正常工作：
1. utils/response_builder.py - 响应构建器
2. utils/db_utils.py - 数据库工具
3. utils/permission_utils.py - 权限工具
4. utils/git_utils.py - Git工具
5. utils/security_utils.py - 安全工具
"""
import pytest
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestResponseBuilder:
    """测试响应构建器"""

    def test_build_user_info(self):
        """测试用户信息构建"""
        from utils.response_builder import build_user_info

        # 模拟用户对象
        class MockUser:
            def __init__(self):
                self.id = 1
                self.username = "testuser"
                self.email = "test@example.com"
                self.full_name = "Test User"

        user = MockUser()
        result = build_user_info(user)

        # 默认字段是 id, username, full_name
        assert result["id"] == 1
        assert result["username"] == "testuser"
        assert result["full_name"] == "Test User"
        assert "email" not in result  # email 不在默认字段中

    def test_build_user_info_with_fields(self):
        """测试带字段过滤的用户信息构建"""
        from utils.response_builder import build_user_info

        class MockUser:
            def __init__(self):
                self.id = 1
                self.username = "testuser"
                self.email = "test@example.com"

        user = MockUser()
        result = build_user_info(user, fields=["id", "username"])

        assert result["id"] == 1
        assert result["username"] == "testuser"
        assert "email" not in result

    def test_build_user_info_none(self):
        """测试 None 用户"""
        from utils.response_builder import build_user_info

        result = build_user_info(None)
        assert result is None

    def test_build_label_response(self):
        """测试标签响应构建"""
        from utils.response_builder import build_label_response

        class MockLabel:
            def __init__(self):
                self.id = 1
                self.name = "bug"
                self.color = "#ff0000"
                self.description = "Bug label"

        label = MockLabel()
        result = build_label_response(label)

        assert result["id"] == 1
        assert result["name"] == "bug"
        assert result["color"] == "#ff0000"
        assert result["description"] == "Bug label"

    def test_format_datetime(self):
        """测试日期时间格式化"""
        from utils.response_builder import format_datetime
        from datetime import datetime

        dt = datetime(2024, 1, 15, 10, 30, 0)
        result = format_datetime(dt)
        assert result == "2024-01-15T10:30:00"

    def test_format_datetime_none(self):
        """测试 None 日期时间"""
        from utils.response_builder import format_datetime

        result = format_datetime(None)
        assert result is None

    def test_build_pagination_response(self):
        """测试分页响应构建"""
        from utils.response_builder import build_pagination_response

        items = [{"id": 1}, {"id": 2}]
        result = build_pagination_response(items, 10, 1, 5)

        assert result["items"] == items
        assert result["total"] == 10
        assert result["page"] == 1
        assert result["limit"] == 5  # 使用 limit 而不是 per_page
        assert result["pages"] == 2


class TestSecurityUtils:
    """测试安全工具"""

    def test_filter_sensitive_data(self):
        """测试敏感数据过滤"""
        from utils.security_utils import filter_sensitive_data

        data = {
            "username": "test",
            "password": "secret123",
            "token": "abc123",
            "nested": {
                "api_key": "key123",
                "value": "normal"
            }
        }

        result = filter_sensitive_data(data)

        assert result["username"] == "test"
        assert result["password"] == "***"
        assert result["token"] == "***"
        assert result["nested"]["api_key"] == "***"
        assert result["nested"]["value"] == "normal"

    def test_mask_string(self):
        """测试字符串遮罩"""
        from utils.security_utils import mask_string

        result = mask_string("abcdefghij", visible_start=2, visible_end=2)
        assert result == "ab******ij"

    def test_is_sensitive_field(self):
        """测试敏感字段检测"""
        from utils.security_utils import is_sensitive_field

        assert is_sensitive_field("password") is True
        assert is_sensitive_field("api_key") is True
        assert is_sensitive_field("username") is False

    def test_sanitize_headers(self):
        """测试 HTTP 头清理"""
        from utils.security_utils import sanitize_headers

        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer token123",
            "X-Custom": "value"
        }

        result = sanitize_headers(headers)

        assert result["Content-Type"] == "application/json"
        assert result["Authorization"] == "***"
        assert result["X-Custom"] == "value"

    def test_validate_password_strength(self):
        """测试密码强度验证"""
        from utils.security_utils import validate_password_strength

        # 强密码
        result = validate_password_strength("StrongP@ss123")
        assert result["is_valid"] is True
        assert result["score"] == 5

        # 弱密码
        result = validate_password_strength("weak")
        assert result["is_valid"] is False
        assert len(result["errors"]) > 0


class TestDbUtils:
    """测试数据库工具"""

    def test_exists(self):
        """测试 exists 函数"""
        from utils.db_utils import exists

        # 模拟查询
        class MockDB:
            def query(self, model):
                return MockQuery()

        class MockQuery:
            def filter(self, *args):
                return self

            def first(self):
                return {"id": 1}  # 返回存在的记录

        db = MockDB()

        # 测试存在的情况
        result = exists(db, MockModel, {"id": 1})
        assert result is True


class MockModel:
    """模拟模型类"""
    id = 1


class TestGitUtils:
    """测试 Git 工具"""

    def test_git_service_class_exists(self):
        """测试 GitService 类存在"""
        from utils.git_utils import GitService
        assert GitService is not None


class TestPermissionUtils:
    """测试权限工具"""

    def test_check_repository_permission_sync(self):
        """测试同步检查仓库权限"""
        from utils.permission_utils import check_repository_permission_sync

        # 模拟数据库查询
        class MockDB:
            def query(self, model):
                return MockQuery()

        class MockQuery:
            def filter(self, *args):
                return self

            def first(self):
                # 返回模拟的用户
                class MockUser:
                    is_admin = True
                return MockUser()

        db = MockDB()
        result = check_repository_permission_sync(db, 1, 1)
        assert result is True  # admin 用户应该通过


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
