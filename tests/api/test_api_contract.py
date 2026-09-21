"""API 契约测试

验证后端注册的路由与前端的 API 调用约定保持一致。
这些测试不依赖数据库，只检查 FastAPI 应用的路由表和请求签名。
"""
import pytest
from fastapi import FastAPI


@pytest.fixture
def app() -> FastAPI:
    """加载主 FastAPI 应用（入口为 app.py, 模块级 app 实例）"""
    from app import app as main_app

    return main_app


_HTTP_METHODS = {"get", "post", "put", "delete", "patch", "head", "options", "trace"}


def _route_paths(app: FastAPI) -> set:
    """提取应用中所有已注册的路由路径（仅 HTTP 路由）

    新版 FastAPI 的 include_router 采用懒加载 _IncludedRouter，
    遍历 app.routes 无法展开子路由；改用公开的 OpenAPI schema
    生成完整路由表（与前端调用的路径一一对应）。
    """
    schema = app.openapi()
    paths = set()
    for path, methods in schema.get("paths", {}).items():
        for method in methods:
            if method.lower() in _HTTP_METHODS:
                paths.add((method.upper(), path))
    return paths


def _assert_route(app: FastAPI, method: str, path: str) -> None:
    """断言指定路由存在"""
    assert (method.upper(), path) in _route_paths(app), (
        f"路由 {method.upper()} {path} 未注册"
    )


class TestPullRequestLabelRoutes:
    """PR 标签路由契约"""

    def test_add_label_to_pr_route(self, app: FastAPI):
        """必须为 /api/v1/repositories/{repo_id}/pull-requests/{pr_number}/labels/{label_id}"""
        _assert_route(app, "POST", "/api/v1/repositories/{repo_id}/pull-requests/{pr_number}/labels/{label_id}")

    def test_remove_label_from_pr_route(self, app: FastAPI):
        _assert_route(app, "DELETE", "/api/v1/repositories/{repo_id}/pull-requests/{pr_number}/labels/{label_id}")


class TestRepositoryAccessRoutes:
    """仓库访问权限路由契约"""

    def test_check_access_route(self, app: FastAPI):
        _assert_route(app, "GET", "/api/v1/repositories/{repo_id}/access")


class TestRepositoryMemberRoutes:
    """仓库成员路由契约"""

    def test_check_member_permission_route(self, app: FastAPI):
        _assert_route(app, "GET", "/api/v1/repositories/{repo_id}/members/{user_id}/permission")


class TestListPaginationRoutes:
    """列表类接口应保持分页返回"""

    def test_issue_list_route(self, app: FastAPI):
        _assert_route(app, "GET", "/api/v1/repositories/{repo_id}/issues")

    def test_issue_filter_route(self, app: FastAPI):
        _assert_route(app, "POST", "/api/v1/repositories/{repo_id}/issues/filter")

    def test_pull_request_list_route(self, app: FastAPI):
        _assert_route(app, "GET", "/api/v1/repositories/{repo_id}/pull-requests")

    def test_release_list_route(self, app: FastAPI):
        _assert_route(app, "GET", "/api/v1/repositories/{repo_id}/releases")

    def test_build_list_route(self, app: FastAPI):
        _assert_route(app, "GET", "/api/v1/repositories/{repo_id}/builds")


class TestNotificationRoutes:
    """通知路由契约"""

    def test_notification_list_route(self, app: FastAPI):
        _assert_route(app, "GET", "/api/v1/notifications")

    def test_notification_preferences_route(self, app: FastAPI):
        _assert_route(app, "GET", "/api/v1/notifications/preferences")
        _assert_route(app, "PUT", "/api/v1/notifications/preferences")


class TestBuildLogRoute:
    """构建日志路由契约"""

    def test_build_logs_route(self, app: FastAPI):
        _assert_route(app, "GET", "/api/v1/repositories/{repo_id}/builds/{build_id}/logs")


class TestSearchRoute:
    """代码搜索路由契约"""

    def test_repository_search_route(self, app: FastAPI):
        _assert_route(app, "GET", "/api/v1/repositories/{repo_id}/search")


class TestAppManagementRoutes:
    """应用管理（admin/app）路由契约"""

    def test_root_and_health(self, app: FastAPI):
        _assert_route(app, "GET", "/")
        _assert_route(app, "GET", "/health")

    def test_status_and_platform_stats(self, app: FastAPI):
        _assert_route(app, "GET", "/api/app/status")
        _assert_route(app, "GET", "/api/v1/stats/platform")

    def test_metrics_timeseries_route(self, app: FastAPI):
        _assert_route(app, "GET", "/api/app/metrics/timeseries")

    def test_components_route(self, app: FastAPI):
        _assert_route(app, "GET", "/api/app/components")

    def test_config_routes(self, app: FastAPI):
        _assert_route(app, "GET", "/api/app/config")
        _assert_route(app, "POST", "/api/app/config")
        _assert_route(app, "POST", "/api/app/config/reset")
        _assert_route(app, "POST", "/api/app/config/validate")

    def test_log_routes(self, app: FastAPI):
        _assert_route(app, "GET", "/api/app/logs")
        _assert_route(app, "GET", "/api/app/logs/content")
        _assert_route(app, "POST", "/api/app/logs/cleanup")

    def test_operation_routes(self, app: FastAPI):
        _assert_route(app, "POST", "/api/app/shutdown")
        _assert_route(app, "POST", "/api/app/restart")


class TestDebugRoutes:
    """调试工具路由契约"""

    def test_debug_routes(self, app: FastAPI):
        _assert_route(app, "GET", "/api/v1/debug/status")
        _assert_route(app, "POST", "/api/v1/debug/initdb")
        _assert_route(app, "POST", "/api/v1/debug/initconf")
