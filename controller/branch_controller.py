"""
分支控制器层

处理与分支相关的HTTP请求，调用服务层方法并返回响应
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from models.db import get_db
from services.branch_service import (
    get_branches as service_get_branches,
    get_branch as service_get_branch,
    create_branch as service_create_branch,
    update_branch as service_update_branch,
    delete_branch as service_delete_branch,
    set_default_branch as service_set_default_branch,
    protect_branch as service_protect_branch,
    unprotect_branch as service_unprotect_branch,
    get_default_branch as service_get_default_branch,
    check_branch_protection as service_check_branch_protection
)

# 创建路由实例
router = APIRouter(prefix="/api/repositories", tags=["branches"])


@router.get("/{repo_id}/branches")
@router.get("/{repo_id}/branches/")
def get_branches(repo_id: int, db: Session = Depends(get_db)):
    """
    获取仓库的所有分支
    
    Args:
        repo_id: 仓库ID
        db: 数据库会话
    
    Returns:
        list[Branch]: 分支列表
    """
    return service_get_branches(repo_id, db)


@router.get("/{repo_id}/branches/default")
def get_default_branch(repo_id: int, db: Session = Depends(get_db)):
    """
    获取默认分支
    
    Args:
        repo_id: 仓库ID
        db: 数据库会话
    
    Returns:
        Branch: 默认分支信息
    
    Raises:
        NotFoundException: 没有默认分支时抛出404异常
    """
    return service_get_default_branch(repo_id, db)


@router.get("/{repo_id}/branches/{branch_name}")
def get_branch(repo_id: int, branch_name: str, db: Session = Depends(get_db)):
    """
    获取仓库的特定分支
    
    Args:
        repo_id: 仓库ID
        branch_name: 分支名称
        db: 数据库会话
    
    Returns:
        Branch: 分支信息
    
    Raises:
        NotFoundException: 分支不存在时抛出404异常
    """
    return service_get_branch(repo_id, branch_name, db)


@router.post("/{repo_id}/branches")
def create_branch(repo_id: int, branch_data: dict, db: Session = Depends(get_db)):
    """
    创建新分支
    
    Args:
        repo_id: 仓库ID
        branch_data: 分支信息
        db: 数据库会话
    
    Returns:
        Branch: 创建的分支信息
    
    Raises:
        ValidationException: 请求参数不完整时抛出422异常
        ConflictException: 分支名称已存在时抛出409异常
    """
    return service_create_branch(repo_id, branch_data, db)


@router.put("/{repo_id}/branches/{branch_name}")
def update_branch(repo_id: int, branch_name: str, branch_data: dict, db: Session = Depends(get_db)):
    """
    更新分支信息
    
    Args:
        repo_id: 仓库ID
        branch_name: 分支名称
        branch_data: 更新的分支信息
        db: 数据库会话
    
    Returns:
        Branch: 更新后的分支信息
    
    Raises:
        NotFoundException: 分支不存在时抛出404异常
    """
    return service_update_branch(repo_id, branch_name, branch_data, db)


@router.delete("/{repo_id}/branches/{branch_name}")
def delete_branch(repo_id: int, branch_name: str, db: Session = Depends(get_db)):
    """
    删除分支
    
    Args:
        repo_id: 仓库ID
        branch_name: 分支名称
        db: 数据库会话
    
    Returns:
        dict: 删除成功消息
    
    Raises:
        NotFoundException: 分支不存在时抛出404异常
        ConflictException: 尝试删除默认分支时抛出409异常
    """
    return service_delete_branch(repo_id, branch_name, db)


@router.put("/{repo_id}/branches/{branch_name}/default")
def set_default_branch(repo_id: int, branch_name: str, db: Session = Depends(get_db)):
    """
    设置默认分支
    
    Args:
        repo_id: 仓库ID
        branch_name: 分支名称
        db: 数据库会话
    
    Returns:
        dict: 设置成功消息
    
    Raises:
        NotFoundException: 分支不存在时抛出404异常
    """
    return service_set_default_branch(repo_id, branch_name, db)


@router.put("/{repo_id}/branches/{branch_name}/protect")
def protect_branch(
    repo_id: int,
    branch_name: str,
    protection_settings: dict = None,
    db: Session = Depends(get_db)
):
    """
    保护分支

    Args:
        repo_id: 仓库ID
        branch_name: 分支名称
        protection_settings: 保护设置（可选）
        db: 数据库会话

    Returns:
        Branch: 更新后的分支信息

    Raises:
        NotFoundException: 分支不存在时抛出404异常
    """
    if protection_settings is None:
        protection_settings = {}
    return service_protect_branch(repo_id, branch_name, protection_settings, db)


@router.put("/{repo_id}/branches/{branch_name}/unprotect")
def unprotect_branch(repo_id: int, branch_name: str, db: Session = Depends(get_db)):
    """
    取消分支保护
    
    Args:
        repo_id: 仓库ID
        branch_name: 分支名称
        db: 数据库会话
    
    Returns:
        Branch: 更新后的分支信息
    
    Raises:
        NotFoundException: 分支不存在时抛出404异常
    """
    return service_unprotect_branch(repo_id, branch_name, db)


@router.get("/{repo_id}/branches/{branch_name}/protection")
def check_branch_protection(repo_id: int, branch_name: str, db: Session = Depends(get_db)):
    """
    检查分支是否受保护
    
    Args:
        repo_id: 仓库ID
        branch_name: 分支名称
        db: 数据库会话
    
    Returns:
        dict: 分支保护状态
    
    Raises:
        NotFoundException: 分支不存在时抛出404异常
    """
    return service_check_branch_protection(repo_id, branch_name, db)
