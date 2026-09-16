"""
API 路由配置与注册模块

集中管理所有 API 路由的：
1. 路由注册顺序
2. 路由依赖关系

前缀常量与 get_route_prefix 已拆分至 api/routes_prefix.py（打破循环导入：
controller 只依赖无副作用的 routes_prefix，不再反向 import 本模块）。
"""
from api.routes_prefix import (  # noqa: F401  # re-export 兼容旧导入
    API_V1_PREFIX,
    ROUTES,
    get_api_version,
    get_route_prefix,
)
from fastapi import APIRouter


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
        APIRouter: 配置好的 API v1 路由器
    """
    api_v1_router = APIRouter(tags=["api-v1"])

    # 1. 应用管理路由（根路由 "/" 需要最先注册）
    from controller.app_controller import router as app_router
    api_v1_router.include_router(app_router)

    # 2. 仓库浏览器（需在仓库路由之前注册，避免路由冲突）
    from controller.repository_browser_controller import router as repository_browser_router
    api_v1_router.include_router(repository_browser_router)

    # 3. 认证路由
    from controller.auth_controller import router as auth_router
    api_v1_router.include_router(auth_router)

    # 3a. Git HTTP Smart Protocol 认证路由
    # 用于 Nginx auth_request 子请求验证，必须先于 API 代理路由注册
    from controller.git_auth_controller import router as git_auth_router
    api_v1_router.include_router(git_auth_router, prefix=API_V1_PREFIX)

    # 3a2. 协作编辑内部回调路由（collab-gateway/Hocuspocus 服务间调用）
    from controller.collab_internal_controller import router as collab_internal_router
    api_v1_router.include_router(collab_internal_router, prefix=API_V1_PREFIX)

    # 3b. OAuth 认证路由
    from controller.oauth_controller import router as oauth_router
    api_v1_router.include_router(oauth_router)

    # 3c. OAuth 账号管理路由
    from controller.oauth_controller import account_router
    api_v1_router.include_router(account_router)

    # 4. 用户管理路由
    from controller.user_controller import router as user_router
    api_v1_router.include_router(user_router)

    # 6. 仓库成员路由
    from controller.repository_member_controller import router as repository_member_router
    api_v1_router.include_router(repository_member_router)

    # 6b. Fork 管理路由（需在仓库路由之后，分支路由之前）
    from controller.fork_controller import router as fork_router
    api_v1_router.include_router(fork_router)

    # 6c. Star 管理路由
    from controller.star_controller import router as star_router
    api_v1_router.include_router(star_router)

    # 6c-bis. Watch 管理路由
    from controller.watch_controller import router as watch_router
    api_v1_router.include_router(watch_router)

    # 6c-ter. 协作邀请链接路由
    from controller.collab_invite_controller import router as collab_invite_router
    api_v1_router.include_router(collab_invite_router)

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

    # 11e2. 跨仓库 Search 路由
    from controller.search_controller import global_search_router
    api_v1_router.include_router(global_search_router)

    # 11f. Build 路由
    from controller.build_controller import router as build_router
    api_v1_router.include_router(build_router)

    # 5. 仓库管理路由（含 /{owner}/{repo} 路径查询）
    # 放在其他仓库子路由（issues/pull-requests/builds/search 等）之后注册，
    # 避免 /{owner}/{repo} 过早匹配 /1/issues 这类子路径。
    from controller.repository_controller import router as repository_router
    api_v1_router.include_router(repository_router)

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


# 向后兼容：保留 api_v1_router 导出
api_v1_router = create_api_router()
