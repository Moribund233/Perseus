"""
用户服务层

处理与用户相关的所有业务逻辑
"""
import os
import shutil
import logging
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import User
from core.exception import ValidationException, NotFoundException, ConflictException, AuthenticationException
from services.token_service import create_token_pair
from utils.password_utils import verify_password, get_password_hash
from utils.response_builder import build_user_response

# 日志记录器
logger = logging.getLogger(__name__)

# 头像存储目录
AVATAR_UPLOAD_DIR = Path("./data/uploads/avatars").resolve()
AVATAR_MAX_SIZE = 5 * 1024 * 1024  # 5MB
AVATAR_ALLOWED_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
}


def user_to_dict(user: User) -> dict:
    """
    将用户对象转换为字典（排除敏感字段）

    使用 response_builder.build_user_response 统一构建响应。

    Args:
        user: User 模型对象

    Returns:
        dict: 用户数据字典（不包含密码）
    """
    return build_user_response(user)


async def get_users(db: AsyncSession):
    """
    获取所有用户

    Args:
        db: 异步数据库会话

    Returns:
        list[dict]: 用户列表（不包含密码）
    """
    result = await db.execute(select(User))
    users = result.scalars().all()
    return [user_to_dict(user) for user in users]


async def get_user_by_id(user_id: int, db: AsyncSession):
    """
    根据ID获取用户

    Args:
        user_id: 用户ID
        db: 异步数据库会话

    Returns:
        dict: 用户信息（不包含密码）

    Raises:
        NotFoundException: 用户不存在时抛出404异常
    """
    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise NotFoundException(detail="User not found")
    return user_to_dict(user)


async def create_user(user_data: dict, db: AsyncSession):
    """
    创建新用户

    Args:
        user_data: 用户信息
        db: 异步数据库会话

    Returns:
        dict: 创建的用户信息

    Raises:
        ConflictException: 用户名或邮箱已存在时抛出409异常
    """
    # 检查用户名是否已存在
    result = await db.execute(select(User).filter(User.username == user_data["username"]))
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise ConflictException(detail="Username already exists")

    # 检查邮箱是否已存在
    result = await db.execute(select(User).filter(User.email == user_data["email"]))
    existing_email = result.scalar_one_or_none()
    if existing_email:
        raise ConflictException(detail="Email already exists")

    # 创建新用户
    db_user = User(
        username=user_data["username"],
        email=user_data["email"],
        password=get_password_hash(user_data["password"]),
        full_name=user_data.get("full_name"),
        is_active=user_data.get("is_active", True),
        is_admin=user_data.get("is_admin", False)
    )

    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)

    return user_to_dict(db_user)


async def update_user(user_id: int, user_data: dict, db: AsyncSession, current_user: User = None):
    """
    更新用户信息

    权限规则：
    - 普通用户只能更新自己的信息
    - 管理员可以更新任何用户的信息

    Args:
        user_id: 用户ID
        user_data: 更新的用户信息
        db: 异步数据库会话
        current_user: 当前认证用户，用于权限检查

    Returns:
        dict: 更新后的用户信息

    Raises:
        NotFoundException: 用户不存在时抛出404异常
        AuthorizationException: 无权限时抛出403异常
    """
    from core.exception import AuthorizationException

    result = await db.execute(select(User).filter(User.id == user_id))
    db_user = result.scalar_one_or_none()
    if db_user is None:
        raise NotFoundException(detail="User not found")

    # 权限检查：只能更新自己的信息，或管理员可以更新任何用户
    if current_user and current_user.id != user_id and not current_user.is_admin:
        raise AuthorizationException(detail="You don't have permission to update this user")

    # 更新用户信息（排除敏感字段）
    for key, value in user_data.items():
        if key == "password":
            # 如果更新密码，需要哈希处理
            value = get_password_hash(value)
        if hasattr(db_user, key):
            setattr(db_user, key, value)

    await db.commit()
    await db.refresh(db_user)

    return user_to_dict(db_user)


async def delete_user(user_id: int, db: AsyncSession):
    """
    删除用户

    Args:
        user_id: 用户ID
        db: 异步数据库会话

    Returns:
        dict: 成功消息

    Raises:
        NotFoundException: 用户不存在时抛出404异常
    """
    result = await db.execute(select(User).filter(User.id == user_id))
    db_user = result.scalar_one_or_none()
    if db_user is None:
        raise NotFoundException(detail="User not found")

    await db.delete(db_user)
    await db.commit()

    return {"message": "User deleted successfully"}


async def change_password(user: User, old_password: str, new_password: str, db: AsyncSession):
    """
    修改当前用户密码

    必须提供正确的旧密码才能设置新密码。

    Args:
        user: 当前用户对象
        old_password: 旧密码
        new_password: 新密码
        db: 异步数据库会话

    Returns:
        dict: 成功消息

    Raises:
        AuthenticationException: 旧密码错误时抛出401异常
        ValidationException: 新密码不符合要求时抛出422异常
    """
    if not old_password or not new_password:
        raise ValidationException(detail="Old password and new password are required")

    if len(new_password) < 6:
        raise ValidationException(detail="New password must be at least 6 characters")

    if not verify_password(old_password, user.password):
        raise AuthenticationException(detail="Invalid old password")

    user.password = get_password_hash(new_password)
    await db.commit()
    await db.refresh(user)

    return {"message": "Password changed successfully"}


async def login_user(credentials: dict, db: AsyncSession):
    """
    用户登录（异步版本）

    Args:
        credentials: 登录凭证，包含用户名和密码
        db: 异步数据库会话

    Returns:
        dict: 登录成功后的用户信息

    Raises:
        ValidationException: 请求参数不完整时抛出422异常
        AuthenticationException: 认证失败时抛出401异常
    """
    # 验证请求参数
    if "username" not in credentials or "password" not in credentials:
        raise ValidationException(detail="Username and password are required")

    # 查找用户（异步）
    result = await db.execute(select(User).filter(User.username == credentials["username"]))
    user = result.scalar_one_or_none()

    # 验证用户是否存在以及密码是否正确
    if not user or not verify_password(credentials["password"], user.password):
        raise AuthenticationException(detail="Invalid username or password")

    # 登录成功，创建令牌对
    tokens = create_token_pair(user)

    # 返回用户信息和令牌
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "is_active": user.is_active,
        "is_admin": user.is_admin,
        "token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"]
    }


async def authenticate_user(username: str, password: str, db: AsyncSession) -> User | None:
    """
    验证用户凭据（异步版本）

    Args:
        username: 用户名
        password: 密码
        db: 异步数据库会话

    Returns:
        User | None: 认证成功返回用户对象，失败返回 None
    """
    from utils.password_utils import verify_password

    # 查找用户（异步）
    result = await db.execute(select(User).filter(User.username == username))
    user = result.scalar_one_or_none()

    if not user:
        return None

    # 验证密码
    if verify_password(password, user.password):
        return user

    return None


def _get_avatar_file_path(user_id: int, ext: str) -> Path:
    """获取头像文件存储路径"""
    AVATAR_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    return AVATAR_UPLOAD_DIR / f"{user_id}{ext}"


def _get_avatar_content_type(file_path: Path) -> str:
    """根据文件扩展名获取 Content-Type"""
    ext = file_path.suffix.lower()
    for content_type, suffix in AVATAR_ALLOWED_CONTENT_TYPES.items():
        if suffix == ext:
            return content_type
    return "application/octet-stream"


async def update_user_avatar(
    user: User,
    filename: str,
    content_type: str,
    file_data: bytes,
    db: AsyncSession
) -> dict:
    """
    更新用户头像

    Args:
        user: 当前用户对象
        filename: 原始文件名
        content_type: HTTP Content-Type
        file_data: 文件二进制内容
        db: 异步数据库会话

    Returns:
        dict: 更新后的用户信息

    Raises:
        ValidationException: 文件类型或大小不符合要求
    """
    if not content_type or content_type not in AVATAR_ALLOWED_CONTENT_TYPES:
        raise ValidationException(
            detail=f"Invalid image format. Allowed: {', '.join(AVATAR_ALLOWED_CONTENT_TYPES.keys())}"
        )

    if len(file_data) > AVATAR_MAX_SIZE:
        raise ValidationException(detail=f"Avatar file too large. Max size: {AVATAR_MAX_SIZE // 1024 // 1024}MB")

    ext = AVATAR_ALLOWED_CONTENT_TYPES[content_type]
    file_path = _get_avatar_file_path(user.id, ext)

    # 删除旧头像文件（如果扩展名不同）
    for old_file in AVATAR_UPLOAD_DIR.glob(f"{user.id}.*"):
        if old_file != file_path:
            try:
                old_file.unlink()
            except OSError:
                pass

    # 保存新头像
    with open(file_path, "wb") as f:
        f.write(file_data)

    # 更新用户头像 URL
    avatar_url = f"/api/v1/users/{user.id}/avatar"
    user.avatar_url = avatar_url
    await db.commit()
    await db.refresh(user)

    return build_user_response(user)


async def get_user_avatar(user_id: int) -> tuple[Path, str]:
    """
    获取用户头像文件

    Args:
        user_id: 用户ID

    Returns:
        tuple[Path, str]: 文件路径和 Content-Type

    Raises:
        NotFoundException: 头像文件不存在
    """
    for ext in AVATAR_ALLOWED_CONTENT_TYPES.values():
        file_path = AVATAR_UPLOAD_DIR / f"{user_id}{ext}"
        if file_path.exists():
            return file_path, _get_avatar_content_type(file_path)

    raise NotFoundException(detail="Avatar not found")
