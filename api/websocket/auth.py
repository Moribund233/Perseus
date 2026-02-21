"""
WebSocket认证模块

提供WebSocket连接的认证功能，支持：
- Token验证（通过URL query参数）
- 用户身份绑定
- 权限检查
"""
from typing import Optional, Dict, Any
from fastapi import WebSocket, HTTPException, status
from sqlalchemy import select
import logging

from services.token_service import verify_token as jwt_verify_token
from models.async_db import get_async_db_context
from models.user import User

logger = logging.getLogger(__name__)


class WebSocketAuthError(Exception):
    """WebSocket认证异常"""
    def __init__(self, message: str, code: int = 1008):
        self.message = message
        self.code = code
        super().__init__(message)


async def extract_token_from_query(websocket: WebSocket) -> Optional[str]:
    """
    从WebSocket连接的query参数中提取token
    
    Args:
        websocket: FastAPI WebSocket对象
        
    Returns:
        Optional[str]: token字符串，未找到返回None
    """
    token = websocket.query_params.get("token")
    if token:
        return token
    
    # 也尝试从access_token参数获取
    token = websocket.query_params.get("access_token")
    return token


async def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """
    验证token并返回用户信息

    支持两种认证方式：
    1. JWT Token - 使用JWT Token服务进行验证
    2. 本地Token - 用于Tauri客户端本地访问

    Args:
        token: JWT token 或本地 token

    Returns:
        Optional[Dict]: 用户信息字典，验证失败返回None

        用户信息格式：
        {
            "user_id": int,
            "username": str,
            "is_active": bool,
            "is_admin": bool,
            "is_local": bool  # 标记是否为本地用户
        }
    """
    # 首先尝试验证本地Token（用于Tauri客户端）
    from api.local_auth import verify_local_token
    if verify_local_token(token):
        logger.info("WebSocket local token verification successful")
        return {
            "user_id": 0,
            "username": "local_admin",
            "is_active": True,
            "is_admin": True,
            "is_local": True
        }

    # 使用真实的JWT验证服务
    token_data = jwt_verify_token(token, token_type="access")

    if not token_data:
        logger.warning("WebSocket token verification failed: invalid token")
        return None

    # 从数据库获取完整的用户信息
    try:
        async with get_async_db_context() as db:
            result = await db.execute(select(User).filter(User.id == token_data.user_id))
            user = result.scalar_one_or_none()

            if not user:
                logger.warning(f"WebSocket token valid but user not found: user_id={token_data.user_id}")
                return None

            return {
                "user_id": user.id,
                "username": user.username,
                "is_active": user.is_active,
                "is_admin": user.is_admin,
                "is_local": False
            }
    except Exception as e:
        logger.error(f"WebSocket token verification error: {e}")
        return None


async def authenticate_websocket(websocket: WebSocket) -> Optional[Dict[str, Any]]:
    """
    认证WebSocket连接
    
    完整的认证流程：
    1. 从query参数提取token
    2. 验证token有效性
    3. 返回用户信息
    
    Args:
        websocket: FastAPI WebSocket对象
        
    Returns:
        Optional[Dict]: 用户信息，认证失败返回None
        
    Raises:
        WebSocketAuthError: 认证失败时抛出
    """
    token = await extract_token_from_query(websocket)
    
    if not token:
        logger.warning("WebSocket连接缺少token")
        raise WebSocketAuthError("Missing authentication token", code=1008)
    
    user_info = await verify_token(token)
    
    if not user_info:
        logger.warning(f"WebSocket连接token验证失败: {token[:20]}...")
        raise WebSocketAuthError("Invalid authentication token", code=1008)
    
    if not user_info.get("is_active", True):
        logger.warning(f"WebSocket连接用户未激活: user_id={user_info.get('user_id')}")
        raise WebSocketAuthError("User account is inactive", code=1008)
    
    logger.info(f"WebSocket认证成功: user_id={user_info.get('user_id')}, username={user_info.get('username')}")
    return user_info


async def authenticate_websocket_optional(websocket: WebSocket) -> Optional[Dict[str, Any]]:
    """
    可选认证（允许匿名连接）
    
    用于某些不需要强制登录的场景，如公开仓库的只读通知
    
    Args:
        websocket: FastAPI WebSocket对象
        
    Returns:
        Optional[Dict]: 用户信息，未提供token或验证失败返回None
    """
    try:
        return await authenticate_websocket(websocket)
    except WebSocketAuthError:
        return None


def check_permission(user_info: Dict[str, Any], permission: str) -> bool:
    """
    检查用户权限
    
    Args:
        user_info: 用户信息字典
        permission: 权限标识
        
    Returns:
        bool: 有权限返回True
    """
    if not user_info:
        return False
    
    # 管理员拥有所有权限
    if user_info.get("is_admin", False):
        return True
    
    # TODO: 根据你的权限系统扩展
    # 示例权限检查
    permissions = user_info.get("permissions", [])
    return permission in permissions


# 与现有认证系统的集成建议：
# 
# 1. 如果你有现有的JWT认证，在 verify_token 中调用：
#    from jose import jwt
#    try:
#        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
#        user_id = payload.get("sub")
#        # 查询用户信息...
