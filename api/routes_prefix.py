"""API 路由前缀常量模块

独立于 routes_config，供各 controller 导入前缀配置。
单独拆分是为了打破循环导入：routes_config 在模块导入时会急切构建全量
api_v1_router（include 所有 controller），若 controller 反向依赖 routes_config，
则任何"先 import controller"的场景（脚本/工具/测试）都会触发循环导入失败。
本模块无任何项目内依赖，controller 一律从这里导入前缀，不再 import routes_config。
"""
# API 版本前缀配置
API_V1_PREFIX = "/api/v1"

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
        str: 当前 API 版本号，如 "v1"
    """
    return API_V1_PREFIX.split("/")[-1]
