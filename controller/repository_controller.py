"""
仓库控制器层

处理与仓库相关的HTTP请求，调用服务层方法并返回响应
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from models.db import get_db
from services.repository_service import (
    get_repositories as service_get_repositories,
    get_repository_by_id as service_get_repository_by_id,
    get_repositories_by_user as service_get_repositories_by_user,
    create_repository as service_create_repository,
    update_repository as service_update_repository,
    delete_repository as service_delete_repository,
    get_public_repositories as service_get_public_repositories,
    check_repository_access as service_check_repository_access
)

# 创建路由实例
router = APIRouter(prefix="/api/repositories", tags=["repositories"])


@router.get("")
@router.get("/")
async def get_repositories(db: Session = Depends(get_db)):
    """
    获取所有仓库
    
    Args:
        db: 数据库会话
    
    Returns:
        list[Repository]: 仓库列表
    """
    return await service_get_repositories(db)


@router.get("/public")
async def get_public_repositories(db: Session = Depends(get_db)):
    """
    获取所有公开仓库
    
    Args:
        db: 数据库会话
    
    Returns:
        list[Repository]: 公开仓库列表
    """
    return await service_get_public_repositories(db)


@router.get("/user/{user_id}")
async def get_repositories_by_user(user_id: int, db: Session = Depends(get_db)):
    """
    根据用户ID获取仓库列表
    
    Args:
        user_id: 用户ID
        db: 数据库会话
    
    Returns:
        list[Repository]: 用户的仓库列表
    """
    return await service_get_repositories_by_user(user_id, db)


@router.get("/{repo_id}")
async def get_repository(repo_id: int, db: Session = Depends(get_db)):
    """
    根据ID获取仓库
    
    Args:
        repo_id: 仓库ID
        db: 数据库会话
    
    Returns:
        Repository: 仓库信息
    
    Raises:
        NotFoundException: 仓库不存在时抛出404异常
    """
    return await service_get_repository_by_id(repo_id, db)


@router.post("/")
async def create_repository(repo: dict, db: Session = Depends(get_db)):
    """
    创建新仓库
    
    Args:
        repo: 仓库信息
        db: 数据库会话
    
    Returns:
        Repository: 创建的仓库信息
    
    Raises:
        ValidationException: 请求参数不完整时抛出422异常
        ConflictException: 仓库路径已存在时抛出409异常
    """
    return await service_create_repository(repo, db)


@router.put("/{repo_id}")
async def update_repository(repo_id: int, repo: dict, db: Session = Depends(get_db)):
    """
    更新仓库信息
    
    Args:
        repo_id: 仓库ID
        repo: 更新的仓库信息
        db: 数据库会话
    
    Returns:
        Repository: 更新后的仓库信息
    
    Raises:
        NotFoundException: 仓库不存在时抛出404异常
        ConflictException: 仓库路径已存在时抛出409异常
    """
    return await service_update_repository(repo_id, repo, db)


@router.delete("/{repo_id}")
async def delete_repository(repo_id: int, db: Session = Depends(get_db)):
    """
    删除仓库
    
    Args:
        repo_id: 仓库ID
        db: 数据库会话
    
    Returns:
        dict: 成功消息
    
    Raises:
        NotFoundException: 仓库不存在时抛出404异常
    """
    return await service_delete_repository(repo_id, db)


@router.get("/{repo_id}/access")
async def check_repository_access(repo_id: int, user_id: int, db: Session = Depends(get_db)):
    """
    检查用户对仓库的访问权限
    
    Args:
        repo_id: 仓库ID
        user_id: 用户ID
        db: 数据库会话
    
    Returns:
        dict: 访问权限检查结果
    
    Raises:
        NotFoundException: 仓库不存在时抛出404异常
    """
    has_access = await service_check_repository_access(repo_id, user_id, db)
    return {"has_access": has_access}