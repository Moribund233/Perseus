"""
API v1 路由统一注册模块

集中注册所有 API v1 路由，简化应用启动流程
所有 API 端点使用 /api/v1 前缀
"""
from fastapi import APIRouter

# 创建 v1 路由主路由器
# 注意：各个控制器已经包含 "/api/v1" 前缀，这里不再添加前缀
api_v1_router = APIRouter(tags=["api-v1"])

# 导入并注册各模块路由
# 注意：app_controller 需要最先注册，因为它包含根路由 "/"
from controller.app_controller import router as app_router
api_v1_router.include_router(app_router)

# 注意：repository_browser 需要在 repository 之前注册，避免路由冲突
from controller.repository_browser_controller import router as repository_browser_router
api_v1_router.include_router(repository_browser_router)

from controller.auth_controller import router as auth_router
api_v1_router.include_router(auth_router)

from controller.user_controller import router as user_router
api_v1_router.include_router(user_router)

from controller.repository_controller import router as repository_router
api_v1_router.include_router(repository_router)

from controller.repository_member_controller import router as repository_member_router
api_v1_router.include_router(repository_member_router)

from controller.branch_controller import router as branch_router
api_v1_router.include_router(branch_router)

from controller.commit_controller import router as commit_router
api_v1_router.include_router(commit_router)

from controller.pull_request_controller import router as pull_request_router
api_v1_router.include_router(pull_request_router)

from controller.issue_controller import router as issue_router
api_v1_router.include_router(issue_router)

from controller.migration_controller import router as migration_router
api_v1_router.include_router(migration_router)

# Debug 路由（仅在调试模式下可用）
from controller.debug_controller import router as debug_router
api_v1_router.include_router(debug_router)

# 错误处理路由
from api.error import router as error_router
api_v1_router.include_router(error_router)

# WebSocket 路由（单独处理，因为 WebSocket 使用不同的协议）
from api.websocket import router as websocket_router
api_v1_router.include_router(websocket_router)

# 注意：Git HTTP Smart Protocol 由 Nginx + git-http-backend 处理
# 参见 docker/nginx/nginx.conf 配置

__all__ = ["api_v1_router"]
