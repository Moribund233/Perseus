"""
仓库成员控制器层

处理与仓库成员相关的HTTP请求，调用服务层方法并返回响应
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.routes_config import get_route_prefix
from models.async_db import get_async_db
from services.member_service import (
    get_repository_members as service_get_repository_members,
    get_repository_member as service_get_repository_member,
    add_repository_member as service_add_repository_member,
    update_repository_member as service_update_repository_member,
    remove_repository_member as service_remove_repository_member,
    update_member_role as service_update_member_role,
    activate_repository_member as service_activate_repository_member,
    deactivate_repository_member as service_deactivate_repository_member,
    check_member_permission as service_check_member_permission
)

# 创建路由实例
router = APIRouter(prefix=get_route_prefix("repository_members"), tags=["repository_members"])


@router.get("/{repo_id}/members")
async def get_repository_members(repo_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    获取仓库的所有成员
    
    Args:
        repo_id: 仓库ID
        db: 数据库会话
    
    Returns:
        list[RepositoryMember]: 仓库成员列表
    """
    return await service_get_repository_members(repo_id, db)


@router.get("/{repo_id}/members/{user_id}")
async def get_repository_member(repo_id: int, user_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    获取仓库的特定成员
    
    Args:
        repo_id: 仓库ID
        user_id: 用户ID
        db: 数据库会话
    
    Returns:
        RepositoryMember: 仓库成员信息
    
    Raises:
        NotFoundException: 成员不存在时抛出404异常
    """
    return await service_get_repository_member(repo_id, user_id, db)


@router.post("/{repo_id}/members")
async def add_repository_member(repo_id: int, member_data: dict, db: AsyncSession = Depends(get_async_db)):
    """
    添加仓库成员
    
    Args:
        repo_id: 仓库ID
        member_data: 成员信息
        db: 数据库会话
    
    Returns:
        RepositoryMember: 添加的成员信息
    
    Raises:
        ValidationException: 请求参数不完整时抛出422异常
        ConflictException: 成员已存在时抛出409异常
        NotFoundException: 用户不存在时抛出404异常
    """
    return await service_add_repository_member(repo_id, member_data, db)


@router.put("/{repo_id}/members/{user_id}")
async def update_repository_member(repo_id: int, user_id: int, member_data: dict, db: AsyncSession = Depends(get_async_db)):
    """
    更新仓库成员信息
    
    Args:
        repo_id: 仓库ID
        user_id: 用户ID
        member_data: 更新的成员信息
        db: 数据库会话
    
    Returns:
        RepositoryMember: 更新后的成员信息
    
    Raises:
        NotFoundException: 成员不存在时抛出404异常
    """
    return await service_update_repository_member(repo_id, user_id, member_data, db)


@router.delete("/{repo_id}/members/{user_id}")
async def remove_repository_member(repo_id: int, user_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    移除仓库成员
    
    Args:
        repo_id: 仓库ID
        user_id: 用户ID
        db: 数据库会话
    
    Returns:
        dict: 移除成功消息
    
    Raises:
        NotFoundException: 成员不存在时抛出404异常
    """
    return await service_remove_repository_member(repo_id, user_id, db)


@router.put("/{repo_id}/members/{user_id}/role")
async def update_member_role(repo_id: int, user_id: int, role_data: dict, db: AsyncSession = Depends(get_async_db)):
    """
    更新成员角色

    Args:
        repo_id: 仓库ID
        user_id: 用户ID
        role_data: 角色信息
        db: 数据库会话

    Returns:
        RepositoryMember: 更新后的成员信息

    Raises:
        NotFoundException: 成员不存在时抛出404异常
        ValidationException: 角色无效时抛出422异常
    """
    role = role_data.get("role")
    return await service_update_member_role(repo_id, user_id, role, db)


@router.put("/{repo_id}/members/{user_id}/activate")
async def activate_repository_member(repo_id: int, user_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    激活仓库成员
    
    Args:
        repo_id: 仓库ID
        user_id: 用户ID
        db: 数据库会话
    
    Returns:
        RepositoryMember: 更新后的成员信息
    
    Raises:
        NotFoundException: 成员不存在时抛出404异常
    """
    return await service_activate_repository_member(repo_id, user_id, db)


@router.put("/{repo_id}/members/{user_id}/deactivate")
async def deactivate_repository_member(repo_id: int, user_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    停用仓库成员
    
    Args:
        repo_id: 仓库ID
        user_id: 用户ID
        db: 数据库会话
    
    Returns:
        RepositoryMember: 更新后的成员信息
    
    Raises:
        NotFoundException: 成员不存在时抛出404异常
    """
    return await service_deactivate_repository_member(repo_id, user_id, db)


@router.get("/{repo_id}/members/{user_id}/permission")
async def check_member_permission(repo_id: int, user_id: int, permission: str, db: AsyncSession = Depends(get_async_db)):
    """
    检查成员权限
    
    Args:
        repo_id: 仓库ID
        user_id: 用户ID
        permission: 权限名称
        db: 数据库会话
    
    Returns:
        dict: 权限检查结果
    
    Raises:
        NotFoundException: 成员不存在时抛出404异常
    """
    return await service_check_member_permission(repo_id, user_id, permission, db)
