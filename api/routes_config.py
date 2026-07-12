"""
API 路由配置与注册模块

集中管理所有 API 路由的：
1. 路由前缀配置
2. 路由注册顺序
3. 路由依赖关系
"""
from fastapi import APIRouter

# API 版本前缀配置
API_V1_PREFIX = "/api/v1"


def create_api_router() -> APIRouter:
    """
    创建并配置 API v1 路由主路由器

    按照特定顺序注册所有 controller 路由：
    1. app_controller - 根路由和健康检查（最先注册）
    2. repository_browser - 需在 repository 之前注册
    3. 其他业务路由
    4. debug 路由
    5. error 和 websocket 路由

    Returns:
        APIRouter: 配置好的 API 路由器
    """
    api_v1_router = APIRouter(tags=["api-v1"])

    # 1. 应用管理路由（根路由 "/" 需要最先注册）
    from controller.app_controller import router as app_router
    api_v1_router.include_router(app_router)

    # 2. 仓库浏览器（需在 repository 之前注册，避免路由冲突）
    from controller.repository_browser_controller import router as repository_browser_router
    api_v1_router.include_router(repository_browser_router)

    # 3. 认证路由
    from controller.auth_controller import router as auth_router
    api_v1_router.include_router(auth_router)

    # 3b. OAuth 认证路由
    from controller.oauth_controller import router as oauth_router
    api_v1_router.include_router(oauth_router)

    # 3c. OAuth 账号管理路由
    from controller.oauth_controller import account_router
    api_v1_router.include_router(account_router)

    # 4. 用户管理路由
    from controller.user_controller import router as user_router
    api_v1_router.include_router(user_router)

    # 5. 仓库管理路由
    from controller.repository_controller import router as repository_router
    api_v1_router.include_router(repository_router)

    # 6. 仓库成员路由
    from controller.repository_member_controller import router as repository_member_router
    api_v1_router.include_router(repository_member_router)

    # 6b. Fork 管理路由（需在仓库路由之后，分支路由之前）
    from controller.fork_controller import router as fork_router
    api_v1_router.include_router(fork_router)

    # 6c. Star 管理路由
    from controller.star_controller import router as star_router
    api_v1_router.include_router(star_router)

    # 6d. Repo Label 管理路由
    from controller.label_controller import router as label_router
    api_v1_router.include_router(label_router)

    # 6e. LFS 管理路由
    from controller.lfs_controller import router as lfs_router
    api_v1_router.include_router(lfs_router)

    # 7. 分支管理路由
    from controller.branch_controller import router as branch_router
    api_v1_router.include_router(branch_router)

    # 8. 提交管理路由
    from controller.commit_controller import router as commit_router
    api_v1_router.include_router(commit_router)

    # 9. Pull Request 路由
    from controller.pull_request_controller import router as pull_request_router
    api_v1_router.include_router(pull_request_router)

    # 9c. PR Label 路由
    from controller.pr_label_controller import router as pr_label_router
    api_v1_router.include_router(pr_label_router)

    # 9b. Release 管理路由（需在 Pull Request 之后）
    from controller.release_controller import router as release_router
    api_v1_router.include_router(release_router)

    # 10. Issue 管理路由
    from controller.issue_controller import router as issue_router
    api_v1_router.include_router(issue_router)

    # 11. SSH Key 管理路由
    from controller.key_controller import router as key_router
    api_v1_router.include_router(key_router)

    # 11b. Webhook 管理路由
    from controller.webhook_controller import router as webhook_router
    api_v1_router.include_router(webhook_router)

    # 11c. Stats 路由
    from controller.stats_controller import router as stats_router
    api_v1_router.include_router(stats_router)

    # 11d. Activity 路由
    from controller.activity_controller import router as activity_router
    api_v1_router.include_router(activity_router)

    # 11f. Notification 路由
    from controller.notification_controller import router as notification_router
    api_v1_router.include_router(notification_router)

    # 11g. Room 路由
    from controller.room_controller import router as room_router
    api_v1_router.include_router(room_router)

    # 11h. Chat 路由
    from controller.chat_controller import router as chat_router
    api_v1_router.include_router(chat_router)

    # 11e. Search 路由
    from controller.search_controller import router as search_router
    api_v1_router.include_router(search_router)

    # 11f. Build 路由
    from controller.build_controller import router as build_router
    api_v1_router.include_router(build_router)

    # 12. Debug 路由（仅在调试模式下可用）
    from controller.debug_controller import router as debug_router
    api_v1_router.include_router(debug_router)

    # 12. 错误处理路由
    from api.error import router as error_router
    api_v1_router.include_router(error_router)

    # 13. WebSocket 路由（单独处理，因为 WebSocket 使用不同的协议）
    from api.websocket import router as websocket_router
    api_v1_router.include_router(websocket_router)

    return api_v1_router


# 各模块路由前缀配置
# 用于 controller 中定义 router 时的 prefix 参数
ROUTES = {
    # 根路由（无前缀）
    "root": "",

    # 认证相关
    "auth": f"{API_V1_PREFIX}/auth",

    # 用户管理
    "users": f"{API_V1_PREFIX}/users",

    # 仓库管理
    "repositories": f"{API_V1_PREFIX}/repositories",

    # 仓库浏览器（需在仓库路由之前注册）
    "repository_browser": f"{API_V1_PREFIX}/repositories",

    # 分支管理
    "branches": f"{API_V1_PREFIX}/repositories",

    # 提交管理
    "commits": f"{API_V1_PREFIX}/repositories",

    # Pull Request
    "pull_requests": f"{API_V1_PREFIX}/repositories",

    # Issue 管理
    "issues": f"{API_V1_PREFIX}/repositories",

    # 仓库成员
    "repository_members": f"{API_V1_PREFIX}/repositories",

    # SSH Key 管理
    "keys": f"{API_V1_PREFIX}/keys",

    # Webhook 管理（需要仓库ID前缀）
    "webhooks": f"{API_V1_PREFIX}/repositories",

    # 构建管理（需要仓库ID前缀）
    "builds": f"{API_V1_PREFIX}/repositories",

    # 通知管理
    "notifications": f"{API_V1_PREFIX}/notifications",

    # 调试接口
    "debug": f"{API_V1_PREFIX}/debug",

    # WebSocket（独立的 /ws 前缀，不由 API_V1 统一管理，避免循环依赖）
    "websocket": "/ws",

    # 错误处理
    "error": f"{API_V1_PREFIX}/errors",
}


def get_route_prefix(module_name: str) -> str:
    """
    获取指定模块的路由前缀

    Args:
        module_name: 模块名称，对应 ROUTES 中的 key

    Returns:
        str: 路由前缀

    Example:
        >>> get_route_prefix("auth")
        '/api/v1/auth'
    """
    return ROUTES.get(module_name, API_V1_PREFIX)


def get_api_version() -> str:
    """
    获取当前 API 版本

    Returns:
        str: API 版本号，如 "v1"
    """
    return API_V1_PREFIX.split("/")[-1]


# 向后兼容：保留 api_v1_router 导出
api_v1_router = create_api_router()
