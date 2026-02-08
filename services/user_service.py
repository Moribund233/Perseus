"""
用户服务层

处理与用户相关的所有业务逻辑
"""
from sqlalchemy.orm import Session
from models import User
from exception import ValidationException, NotFoundException, ConflictException, AuthenticationException
from passlib.context import CryptContext

# 密码哈希上下文
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


def user_to_dict(user: User) -> dict:
    """
    将用户对象转换为字典（排除敏感字段）

    Args:
        user: User 模型对象

    Returns:
        dict: 用户数据字典（不包含密码）
    """
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "is_active": user.is_active,
        "is_admin": user.is_admin,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "updated_at": user.updated_at.isoformat() if user.updated_at else None
    }


async def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证密码是否匹配
    
    Args:
        plain_password: 明文密码
        hashed_password: 哈希密码
    
    Returns:
        bool: 密码是否匹配
    """
    try:
        # 限制密码长度，避免bcrypt错误
        return pwd_context.verify(plain_password[:72], hashed_password)
    except Exception as e:
        print(f"密码验证失败: {e}")
        return False


async def get_password_hash(password: str) -> str:
    """
    获取密码的哈希值
    
    Args:
        password: 明文密码
    
    Returns:
        str: 哈希后的密码
    """
    try:
        # 限制密码长度，避免bcrypt错误
        return pwd_context.hash(password[:72])
    except Exception as e:
        print(f"密码哈希生成失败: {e}")
        raise


async def get_users(db: Session):
    """
    获取所有用户

    Args:
        db: 数据库会话

    Returns:
        list[dict]: 用户列表（不包含密码）
    """
    users = db.query(User).all()
    return [user_to_dict(user) for user in users]


async def get_user_by_id(user_id: int, db: Session):
    """
    根据ID获取用户

    Args:
        user_id: 用户ID
        db: 数据库会话

    Returns:
        dict: 用户信息（不包含密码）

    Raises:
        NotFoundException: 用户不存在时抛出404异常
    """
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise NotFoundException(detail="User not found")
    return user_to_dict(user)


async def create_user(user_data: dict, db: Session):
    """
    创建新用户
    
    Args:
        user_data: 用户信息
        db: 数据库会话
    
    Returns:
        User: 创建的用户信息
    
    Raises:
        ConflictException: 用户名或邮箱已存在时抛出409异常
    """
    # 检查用户名是否已存在
    existing_user = db.query(User).filter(User.username == user_data["username"]).first()
    if existing_user:
        raise ConflictException(detail="Username already exists")
    
    # 检查邮箱是否已存在
    existing_email = db.query(User).filter(User.email == user_data["email"]).first()
    if existing_email:
        raise ConflictException(detail="Email already exists")
    
    # 创建新用户
    db_user = User(
        username=user_data["username"],
        email=user_data["email"],
        password=await get_password_hash(user_data["password"][:72]),  # 限制密码长度
        full_name=user_data.get("full_name"),
        is_active=user_data.get("is_active", True),
        is_admin=user_data.get("is_admin", False)
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return user_to_dict(db_user)


async def update_user(user_id: int, user_data: dict, db: Session):
    """
    更新用户信息
    
    Args:
        user_id: 用户ID
        user_data: 更新的用户信息
        db: 数据库会话
    
    Returns:
        User: 更新后的用户信息
    
    Raises:
        NotFoundException: 用户不存在时抛出404异常
    """
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user is None:
        raise NotFoundException(detail="User not found")
    
    # 更新用户信息（排除敏感字段）
    for key, value in user_data.items():
        if key == "password":
            # 如果更新密码，需要哈希处理
            value = await get_password_hash(value[:72])
        if hasattr(db_user, key):
            setattr(db_user, key, value)

    db.commit()
    db.refresh(db_user)

    return user_to_dict(db_user)


async def delete_user(user_id: int, db: Session):
    """
    删除用户
    
    Args:
        user_id: 用户ID
        db: 数据库会话
    
    Returns:
        dict: 成功消息
    
    Raises:
        NotFoundException: 用户不存在时抛出404异常
    """
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user is None:
        raise NotFoundException(detail="User not found")
    
    db.delete(db_user)
    db.commit()
    
    return {"message": "User deleted successfully"}


async def login_user(credentials: dict, db: Session):
    """
    用户登录
    
    Args:
        credentials: 登录凭证，包含用户名和密码
        db: 数据库会话
    
    Returns:
        dict: 登录成功后的用户信息
    
    Raises:
        ValidationException: 请求参数不完整时抛出422异常
        AuthenticationException: 认证失败时抛出401异常
    """
    # 验证请求参数
    if "username" not in credentials or "password" not in credentials:
        raise ValidationException(detail="Username and password are required")
    
    # 查找用户
    user = db.query(User).filter(User.username == credentials["username"]).first()
    
    # 验证用户是否存在以及密码是否正确
    if not user or not await verify_password(credentials["password"], user.password):
        raise AuthenticationException(detail="Invalid username or password")
    
    # 登录成功，返回用户信息（不包含密码）
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "is_active": user.is_active,
        "is_admin": user.is_admin
    }


def authenticate_user(username: str, password: str, db: Session) -> User | None:
    """
    验证用户凭据

    同步版本的认证函数，用于 Git HTTP 协议认证

    Args:
        username: 用户名
        password: 密码
        db: 数据库会话

    Returns:
        User | None: 认证成功返回用户对象，失败返回 None
    """
    # 查找用户
    user = db.query(User).filter(User.username == username).first()

    if not user:
        return None

    # 同步验证密码
    try:
        # 限制密码长度，避免bcrypt错误
        if pwd_context.verify(password[:72], user.password):
            return user
    except Exception:
        pass

    return None
