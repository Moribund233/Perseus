"""
本地认证模块

为 Tauri Client 提供特殊的本地认证机制：
1. 通过环境变量 LANGIT_LOCAL_TOKEN 注入本地管理员 Token
2. 本地 Token 具有最高权限（相当于管理员）
3. 仅在本地访问时有效（通过请求头 X-LanGit-Local: 1 标识）

安全设计：
- 本地 Token 只在服务端启动时通过环境变量传入
- 本地 Token 不存储在数据库中
- 本地 Token 每次启动都会变化
- 需要同时满足：正确的 Token + 本地请求头
"""

import os
from typing import Optional

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from models.user import User

# 本地认证请求头
LOCAL_AUTH_HEADER = "X-LanGit-Local"
LOCAL_AUTH_VALUE = "1"

# 环境变量名
LOCAL_TOKEN_ENV = "LANGIT_LOCAL_TOKEN"


class LocalAuthError(Exception):
    """本地认证错误"""
    pass


def get_local_token() -> Optional[str]:
    """
    获取本地 Token（从环境变量）
    
    Returns:
        Optional[str]: 本地 Token，未设置返回 None
    """
    return os.environ.get(LOCAL_TOKEN_ENV)


def verify_local_token(token: str) -> bool:
    """
    验证本地 Token 是否有效
    
    Args:
        token: 待验证的 Token
        
    Returns:
        bool: 是否有效
    """
    local_token = get_local_token()
    if not local_token:
        return False
    
    return token == local_token


class LocalUser:
    """本地用户对象（模拟管理员用户）"""

    def __init__(self):
        self.id = 0
        self.username = "local_admin"
        self.email = "local@langit.local"
        self.role = "admin"
        self.is_active = True
        self.is_local = True  # 标记为本地用户
        self.is_admin = True  # 本地用户默认为管理员

    def dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "is_active": self.is_active,
            "is_local": self.is_local,
            "is_admin": self.is_admin,
        }


async def get_local_auth_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False))
) -> Optional[LocalUser]:
    """
    获取本地认证用户
    
    验证条件：
    1. 请求头包含 X-LanGit-Local: 1
    2. Authorization 头包含正确的本地 Token
    
    Args:
        request: FastAPI 请求对象
        credentials: HTTP 认证凭证
        
    Returns:
        Optional[LocalUser]: 本地用户对象，验证失败返回 None
    """
    # 检查本地认证请求头
    local_header = request.headers.get(LOCAL_AUTH_HEADER)
    if local_header != LOCAL_AUTH_VALUE:
        return None
    
    # 检查本地 Token
    if not credentials:
        return None
    
    token = credentials.credentials
    if verify_local_token(token):
        return LocalUser()
    
    return None


async def require_local_auth(
    local_user: Optional[LocalUser] = Depends(get_local_auth_user)
) -> LocalUser:
    """
    要求本地认证
    
    用于需要本地管理员权限的接口
    
    Args:
        local_user: 本地用户对象
        
    Returns:
        LocalUser: 本地用户对象
        
    Raises:
        HTTPException: 认证失败时抛出 403 异常
    """
    if not local_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Local authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return local_user


# 组合认证：本地认证 或 JWT 认证（管理员）
async def get_current_user_or_local(
    request: Request,
    local_user: Optional[LocalUser] = Depends(get_local_auth_user)
) -> Optional[User]:
    """
    获取当前用户（本地认证优先）
    
    先尝试本地认证，失败则返回 None（由调用方决定是否继续 JWT 认证）
    
    Args:
        request: FastAPI 请求对象
        local_user: 本地用户对象
        
    Returns:
        Optional[User]: 用户对象
    """
    if local_user:
        # 返回本地用户作为 User 的兼容对象
        return local_user
    return None
