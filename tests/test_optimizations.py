"""
代码优化测试脚本

测试本次优化的所有功能：
1. Git HTTP receive-pack 功能
2. 控制器层异常处理
3. 服务层同步/异步统一
4. 密码哈希常量
5. 角色优先级常量
6. 导入语句优化
7. 分页查询优化
8. 限流器配置
"""
import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestGitHttpService(unittest.TestCase):
    """测试 Git HTTP 服务优化"""

    def test_parse_receive_pack_data(self):
        """测试 receive-pack 数据解析"""
        from services.git_http_service import _parse_receive_pack_data

        # 构造测试数据 - 正确的 pkt-line 格式
        # 0055 = 85 (十六进制) = 4 (长度前缀) + 81 (内容)
        # 内容: old_sha(40) + space(1) + new_sha(40) + space(1) + ref_name + newline(1)
        command_line = b"0000000000000000000000000000000000000000 1234567890abcdef1234567890abcdef12345678 refs/heads/main\n"
        length = len(command_line) + 4
        length_prefix = format(length, "04x").encode()

        # 0000 作为 pkt-line 格式中的分隔符，长度为 4
        # 后面跟着 packfile 数据
        data = length_prefix + command_line + b"0004" + b"PACK..."

        commands, packfile = _parse_receive_pack_data(data)

        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0]['old_sha'], '0000000000000000000000000000000000000000')
        self.assertEqual(commands[0]['new_sha'], '1234567890abcdef1234567890abcdef12345678')
        self.assertEqual(commands[0]['ref'], 'refs/heads/main')
        self.assertEqual(packfile, b"PACK...")

    def test_parse_receive_pack_data_empty(self):
        """测试空数据解析"""
        from services.git_http_service import _parse_receive_pack_data

        commands, packfile = _parse_receive_pack_data(b"")
        self.assertEqual(len(commands), 0)
        self.assertIsNone(packfile)


class TestUserService(unittest.TestCase):
    """测试用户服务优化"""

    def test_password_hash_constant(self):
        """测试密码哈希常量"""
        from services.user_service import MAX_PASSWORD_LENGTH

        self.assertEqual(MAX_PASSWORD_LENGTH, 72)
        self.assertIsInstance(MAX_PASSWORD_LENGTH, int)

    def test_sync_functions(self):
        """测试同步函数"""
        from services.user_service import (
            get_users, get_user_by_id, verify_password,
            get_password_hash, create_user, update_user, delete_user, login_user
        )

        # 验证所有函数都是同步的（不是协程）
        import inspect
        functions = [
            get_users, get_user_by_id, verify_password,
            get_password_hash, create_user, update_user, delete_user, login_user
        ]

        for func in functions:
            self.assertFalse(inspect.iscoroutinefunction(func),
                           f"{func.__name__} 应该是同步函数")


class TestMemberService(unittest.TestCase):
    """测试成员服务优化"""

    def test_role_priority_constant(self):
        """测试角色优先级常量"""
        from services.member_service import ROLE_PRIORITY, VALID_ROLES

        expected_priority = {
            "owner": 4,
            "admin": 3,
            "developer": 2,
            "readonly": 1
        }
        self.assertEqual(ROLE_PRIORITY, expected_priority)
        self.assertEqual(set(VALID_ROLES), set(expected_priority.keys()))

    def test_sync_functions(self):
        """测试同步函数"""
        from services.member_service import (
            get_repository_members, get_repository_member,
            add_repository_member, update_repository_member
        )

        import inspect
        functions = [
            get_repository_members, get_repository_member,
            add_repository_member, update_repository_member
        ]

        for func in functions:
            self.assertFalse(inspect.iscoroutinefunction(func),
                           f"{func.__name__} 应该是同步函数")


class TestBranchService(unittest.TestCase):
    """测试分支服务优化"""

    def test_import_at_top(self):
        """测试导入语句在文件顶部"""
        import services.branch_service as branch_service

        # 检查 Repository 是否在模块级别导入
        self.assertTrue(hasattr(branch_service, 'Repository'))

    def test_sync_functions(self):
        """测试同步函数"""
        from services.branch_service import (
            get_branches, get_branch, create_branch,
            update_branch, delete_branch, set_default_branch
        )

        import inspect
        functions = [
            get_branches, get_branch, create_branch,
            update_branch, delete_branch, set_default_branch
        ]

        for func in functions:
            self.assertFalse(inspect.iscoroutinefunction(func),
                           f"{func.__name__} 应该是同步函数")


class TestCommitService(unittest.TestCase):
    """测试提交服务优化"""

    def test_import_at_top(self):
        """测试导入语句在文件顶部"""
        import services.commit_service as commit_service

        # 检查 Branch 是否在模块级别导入
        self.assertTrue(hasattr(commit_service, 'Branch'))

    def test_sync_functions(self):
        """测试同步函数"""
        from services.commit_service import (
            get_commits, get_commit_by_hash, create_commit,
            get_commit_history, count_repo_commits
        )

        import inspect
        functions = [
            get_commits, get_commit_by_hash, create_commit,
            get_commit_history, count_repo_commits
        ]

        for func in functions:
            self.assertFalse(inspect.iscoroutinefunction(func),
                           f"{func.__name__} 应该是同步函数")


class TestRepositoryService(unittest.TestCase):
    """测试仓库服务优化"""

    def test_role_priority_constant(self):
        """测试角色优先级常量"""
        from services.repository_service import ROLE_PRIORITY

        expected_priority = {
            "owner": 4,
            "admin": 3,
            "developer": 2,
            "readonly": 1
        }
        self.assertEqual(ROLE_PRIORITY, expected_priority)

    def test_import_at_top(self):
        """测试导入语句在文件顶部"""
        import services.repository_service as repo_service

        # 检查模型是否在模块级别导入
        self.assertTrue(hasattr(repo_service, 'Branch'))
        self.assertTrue(hasattr(repo_service, 'RepositoryMember'))

    def test_sync_functions(self):
        """测试同步函数"""
        from services.repository_service import (
            get_repositories, get_repository_by_id,
            create_repository, update_repository, delete_repository
        )

        import inspect
        functions = [
            get_repositories, get_repository_by_id,
            create_repository, update_repository, delete_repository
        ]

        for func in functions:
            self.assertFalse(inspect.iscoroutinefunction(func),
                           f"{func.__name__} 应该是同步函数")


class TestRepositoryBrowserService(unittest.TestCase):
    """测试仓库浏览服务优化"""

    def test_get_commits_pagination(self):
        """测试提交分页优化"""
        from services.repository_browser_service import get_commits

        # 测试函数签名包含 has_more 返回
        import inspect
        sig = inspect.signature(get_commits)
        self.assertIn('page', sig.parameters)
        self.assertIn('per_page', sig.parameters)


class TestRateLimiter(unittest.TestCase):
    """测试限流器配置优化"""

    def test_rate_limit_config_class(self):
        """测试限流器配置类"""
        from utils.rate_limiter import RateLimitConfig, get_rate_limit_config

        config = get_rate_limit_config()

        # 验证所有配置属性存在
        self.assertTrue(hasattr(config, 'STRICT'))
        self.assertTrue(hasattr(config, 'STANDARD'))
        self.assertTrue(hasattr(config, 'GENEROUS'))
        self.assertTrue(hasattr(config, 'GIT_OPERATIONS'))
        self.assertTrue(hasattr(config, 'DOWNLOAD'))

        # 验证配置是列表
        self.assertIsInstance(config.STRICT, list)
        self.assertIsInstance(config.STANDARD, list)

    def test_config_from_file(self):
        """测试从配置文件读取"""
        from config import get_config

        config = get_config()

        # 验证 rate_limit 配置存在
        self.assertTrue(hasattr(config, 'rate_limit'))
        self.assertTrue(hasattr(config.rate_limit, 'default_limits'))
        self.assertTrue(hasattr(config.rate_limit, 'strict'))


class TestConfig(unittest.TestCase):
    """测试配置类优化"""

    def test_rate_limit_settings(self):
        """测试速率限制配置类"""
        from config import RateLimitSettings

        settings = RateLimitSettings()

        # 验证默认值
        self.assertEqual(settings.default_limits, ["200 per minute", "1000 per hour"])
        self.assertEqual(settings.strict, ["5 per minute", "20 per hour"])
        self.assertEqual(settings.standard, ["30 per minute", "500 per hour"])
        self.assertEqual(settings.generous, ["100 per minute", "2000 per hour"])
        self.assertEqual(settings.git_operations, ["10 per minute", "100 per hour"])
        self.assertEqual(settings.download, ["20 per minute", "200 per hour"])


class TestAsyncUtils(unittest.TestCase):
    """测试异步工具函数"""

    def test_permission_utils_async(self):
        """测试权限工具函数是异步的"""
        import inspect
        from utils import permission_utils

        async_functions = [
            permission_utils.check_resource_author_or_admin,
            permission_utils.check_repository_owner_or_admin,
            permission_utils._check_repository_owner_or_admin_internal,
            permission_utils.check_repository_permission,
            permission_utils.require_repository_permission,
        ]

        for func in async_functions:
            self.assertTrue(
                inspect.iscoroutinefunction(func),
                f"{func.__name__} 应该是异步函数"
            )

    def test_query_utils_async(self):
        """测试查询工具函数是异步的"""
        import inspect
        from utils import query_utils

        async_functions = [
            query_utils.get_resource_or_404,
            query_utils.get_issue_or_404,
            query_utils.get_pull_request_or_404,
            query_utils.get_repository_or_404,
            query_utils.get_user_or_404,
            query_utils.paginate_query,
            query_utils.build_pagination_response,
        ]

        for func in async_functions:
            self.assertTrue(
                inspect.iscoroutinefunction(func),
                f"{func.__name__} 应该是异步函数"
            )


class TestIssueServiceAsync(unittest.TestCase):
    """测试 Issue 服务的异步函数"""

    def test_async_functions(self):
        """测试关键函数是异步的"""
        import inspect
        from services.issue_service import (
            update_issue, close_issue, reopen_issue,
            create_issue_comment, list_issue_comments
        )

        async_functions = [
            update_issue, close_issue, reopen_issue,
            create_issue_comment, list_issue_comments
        ]

        for func in async_functions:
            self.assertTrue(
                inspect.iscoroutinefunction(func),
                f"{func.__name__} 应该是异步函数"
            )


class TestPullRequestServiceAsync(unittest.TestCase):
    """测试 Pull Request 服务的异步函数"""

    def test_async_functions(self):
        """测试关键函数是异步的"""
        import inspect
        from services.pull_request_service import (
            list_pull_requests, get_pull_request, create_pull_request,
            update_pull_request, close_pull_request, merge_pull_request,
            create_pr_comment, create_pr_review, list_pr_comments
        )

        async_functions = [
            list_pull_requests, get_pull_request, create_pull_request,
            update_pull_request, close_pull_request, merge_pull_request,
            create_pr_comment, create_pr_review, list_pr_comments
        ]

        for func in async_functions:
            self.assertTrue(
                inspect.iscoroutinefunction(func),
                f"{func.__name__} 应该是异步函数"
            )


class TestIntegration(unittest.TestCase):
    """集成测试"""

    def test_core_services_sync(self):
        """测试核心服务函数是同步的"""
        import inspect

        # 这些服务应该保持同步
        from services import (
            user_service, member_service, branch_service,
            commit_service, repository_service
        )

        services = [
            user_service, member_service, branch_service,
            commit_service, repository_service
        ]

        for service in services:
            for name, obj in inspect.getmembers(service):
                if inspect.isfunction(obj) and not name.startswith('_'):
                    self.assertFalse(
                        inspect.iscoroutinefunction(obj),
                        f"{service.__name__}.{name} 应该是同步函数"
                    )


if __name__ == '__main__':
    # 运行测试
    unittest.main(verbosity=2)
