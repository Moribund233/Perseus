"""
用户API路由

提供用户相关的API端点
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from models import SessionLocal, User
from exception import ValidationException, NotFoundException, ConflictException

# 创建路由实例
router = APIRouter(prefix="/api/users", tags=["users"])

# 数据库依赖
async def get_db():
    """
    获取数据库会话
    
    Yields:
        Session: 数据库会话实例
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/")
async def get_users(db: Session = Depends(get_db)):
    """
    获取所有用户
    
    Args:
        db: 数据库会话
    
    Returns:
        list[User]: 用户列表
    """
    users = db.query(User).all()
    return users


@router.get("/{user_id}")
async def get_user(user_id: int, db: Session = Depends(get_db)):
    """
    根据ID获取用户
    
    Args:
        user_id: 用户ID
        db: 数据库会话
    
    Returns:
        User: 用户信息
    
    Raises:
        NotFoundException: 用户不存在时抛出404异常
    """
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise NotFoundException(detail="User not found")
    return user


@router.post("/")
async def create_user(user: dict, db: Session = Depends(get_db)):
    """
    创建新用户
    
    Args:
        user: 用户信息
        db: 数据库会话
    
    Returns:
        User: 创建的用户信息
    
    Raises:
        ConflictException: 用户名或邮箱已存在时抛出409异常
    """
    # 检查用户名是否已存在
    existing_user = db.query(User).filter(User.username == user["username"]).first()
    if existing_user:
        raise ConflictException(detail="Username already exists")
    
    # 检查邮箱是否已存在
    existing_email = db.query(User).filter(User.email == user["email"]).first()
    if existing_email:
        raise ConflictException(detail="Email already exists")
    
    # 创建新用户
    db_user = User(
        username=user["username"],
        email=user["email"],
        password=user["password"],
        full_name=user.get("full_name"),
        is_active=user.get("is_active", True),
        is_admin=user.get("is_admin", False)
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user


@router.put("/{user_id}")
async def update_user(user_id: int, user: dict, db: Session = Depends(get_db)):
    """
    更新用户信息
    
    Args:
        user_id: 用户ID
        user: 更新的用户信息
        db: 数据库会话
    
    Returns:
        User: 更新后的用户信息
    
    Raises:
        NotFoundException: 用户不存在时抛出404异常
    """
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user is None:
        raise NotFoundException(detail="User not found")
    
    # 更新用户信息
    for key, value in user.items():
        if hasattr(db_user, key):
            setattr(db_user, key, value)
    
    db.commit()
    db.refresh(db_user)
    
    return db_user


@router.delete("/{user_id}")
async def delete_user(user_id: int, db: Session = Depends(get_db)):
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
