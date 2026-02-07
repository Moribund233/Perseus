"""
仓库服务层

处理与Git仓库相关的所有业务逻辑
"""
from sqlalchemy.orm import Session
from models import Repository
from exception import ValidationException, NotFoundException, ConflictException


async def get_repositories(db: Session):
    """
    获取所有仓库
    
    Args:
        db: 数据库会话
    
    Returns:
        list[dict]: 仓库列表
    """
    repos = db.query(Repository).all()
    # 返回字典列表而不是SQLAlchemy模型对象列表，避免循环引用问题
    return [{
        "id": repo.id,
        "name": repo.name,
        "path": repo.path,
        "description": repo.description,
        "is_public": repo.is_public,
        "owner_id": repo.owner_id,
        "default_branch": repo.default_branch,
        "created_at": repo.created_at,
        "updated_at": repo.updated_at
    } for repo in repos]


async def get_repository_by_id(repo_id: int, db: Session):
    """
    根据ID获取仓库
    
    Args:
        repo_id: 仓库ID
        db: 数据库会话
    
    Returns:
        dict: 仓库信息
    
    Raises:
        NotFoundException: 仓库不存在时抛出404异常
    """
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if repo is None:
        raise NotFoundException(detail="Repository not found")
    # 返回字典而不是SQLAlchemy模型对象，避免循环引用问题
    return {
        "id": repo.id,
        "name": repo.name,
        "path": repo.path,
        "description": repo.description,
        "is_public": repo.is_public,
        "owner_id": repo.owner_id,
        "default_branch": repo.default_branch,
        "created_at": repo.created_at,
        "updated_at": repo.updated_at
    }


async def get_repositories_by_user(user_id: int, db: Session):
    """
    根据用户ID获取仓库列表
    
    Args:
        user_id: 用户ID
        db: 数据库会话
    
    Returns:
        list[dict]: 仓库列表
    """
    # 查询用户拥有的仓库
    owned_repos = db.query(Repository).filter(Repository.owner_id == user_id).all()
    
    # 查询用户参与的仓库（通过repository_members表）
    from models.repository_member import RepositoryMember
    member_repos = db.query(Repository).join(RepositoryMember).filter(RepositoryMember.user_id == user_id).all()
    
    # 合并结果，去重
    all_repos = list(set(owned_repos + member_repos))
    
    # 返回字典列表而不是SQLAlchemy模型对象列表，避免循环引用问题
    return [{
        "id": repo.id,
        "name": repo.name,
        "path": repo.path,
        "description": repo.description,
        "is_public": repo.is_public,
        "owner_id": repo.owner_id,
        "default_branch": repo.default_branch,
        "created_at": repo.created_at,
        "updated_at": repo.updated_at
    } for repo in all_repos]


async def create_repository(repo_data: dict, db: Session):
    """
    创建新仓库
    
    Args:
        repo_data: 仓库信息
        db: 数据库会话
    
    Returns:
        dict: 创建的仓库信息
    
    Raises:
        ValidationException: 请求参数不完整时抛出422异常
        ConflictException: 仓库路径已存在时抛出409异常
    """
    # 验证请求参数
    if "name" not in repo_data or "path" not in repo_data or "owner_id" not in repo_data:
        raise ValidationException(detail="Name, path and owner_id are required")
    
    # 检查路径是否已存在
    existing_repo = db.query(Repository).filter(Repository.path == repo_data["path"]).first()
    if existing_repo:
        raise ConflictException(detail="Repository path already exists")
    
    # 创建新仓库
    db_repo = Repository(
        name=repo_data["name"],
        path=repo_data["path"],
        description=repo_data.get("description"),
        is_public=repo_data.get("is_public", True),
        owner_id=repo_data["owner_id"],
        default_branch=repo_data.get("default_branch", "master")
    )
    
    db.add(db_repo)
    db.commit()
    db.refresh(db_repo)
    
    # 为仓库创建默认分支
    from models.branch import Branch
    default_branch = Branch(
        name=db_repo.default_branch,
        repository_id=db_repo.id,
        is_protected=True,
        is_default=True
    )
    db.add(default_branch)
    db.commit()
    
    # 添加仓库所有者为成员
    from models.repository_member import RepositoryMember
    owner_member = RepositoryMember(
        repository_id=db_repo.id,
        user_id=db_repo.owner_id,
        role="owner"
    )
    db.add(owner_member)
    db.commit()
    
    # 返回字典而不是SQLAlchemy模型对象，避免循环引用问题
    return {
        "id": db_repo.id,
        "name": db_repo.name,
        "path": db_repo.path,
        "description": db_repo.description,
        "is_public": db_repo.is_public,
        "owner_id": db_repo.owner_id,
        "default_branch": db_repo.default_branch,
        "created_at": db_repo.created_at,
        "updated_at": db_repo.updated_at
    }


async def update_repository(repo_id: int, repo_data: dict, db: Session):
    """
    更新仓库信息
    
    Args:
        repo_id: 仓库ID
        repo_data: 更新的仓库信息
        db: 数据库会话
    
    Returns:
        dict: 更新后的仓库信息
    
    Raises:
        NotFoundException: 仓库不存在时抛出404异常
        ConflictException: 仓库路径已存在时抛出409异常
    """
    db_repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if db_repo is None:
        raise NotFoundException(detail="Repository not found")
    
    # 检查路径是否已存在（如果更新了路径）
    if "path" in repo_data and repo_data["path"] != db_repo.path:
        existing_repo = db.query(Repository).filter(Repository.path == repo_data["path"]).first()
        if existing_repo:
            raise ConflictException(detail="Repository path already exists")
    
    # 更新仓库信息
    for key, value in repo_data.items():
        if hasattr(db_repo, key):
            setattr(db_repo, key, value)
    
    db.commit()
    db.refresh(db_repo)
    
    # 返回字典而不是SQLAlchemy模型对象，避免循环引用问题
    return {
        "id": db_repo.id,
        "name": db_repo.name,
        "path": db_repo.path,
        "description": db_repo.description,
        "is_public": db_repo.is_public,
        "owner_id": db_repo.owner_id,
        "default_branch": db_repo.default_branch,
        "created_at": db_repo.created_at,
        "updated_at": db_repo.updated_at
    }


async def delete_repository(repo_id: int, db: Session):
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
    db_repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if db_repo is None:
        raise NotFoundException(detail="Repository not found")
    
    db.delete(db_repo)
    db.commit()
    
    return {"message": "Repository deleted successfully"}


async def get_public_repositories(db: Session):
    """
    获取所有公开仓库
    
    Args:
        db: 数据库会话
    
    Returns:
        list[dict]: 公开仓库列表
    """
    repos = db.query(Repository).filter(Repository.is_public == True).all()
    # 返回字典列表而不是SQLAlchemy模型对象列表，避免循环引用问题
    return [{
        "id": repo.id,
        "name": repo.name,
        "path": repo.path,
        "description": repo.description,
        "is_public": repo.is_public,
        "owner_id": repo.owner_id,
        "default_branch": repo.default_branch,
        "created_at": repo.created_at,
        "updated_at": repo.updated_at
    } for repo in repos]


async def check_repository_access(repo_id: int, user_id: int, db: Session, required_role: str = None):
    """
    检查用户对仓库的访问权限
    
    Args:
        repo_id: 仓库ID
        user_id: 用户ID
        db: 数据库会话
        required_role: 所需的最低权限角色（可选）
    
    Returns:
        bool: 是否有访问权限
    
    Raises:
        NotFoundException: 仓库不存在时抛出404异常
    """
    repo = await get_repository_by_id(repo_id, db)
    
    # 检查仓库是否公开
    if repo["is_public"] and required_role is None:
        return True
    
    # 检查用户是否是仓库所有者
    if repo["owner_id"] == user_id:
        return True
    
    # 检查用户是否是仓库成员
    from models.repository_member import RepositoryMember
    member = db.query(RepositoryMember).filter(
        RepositoryMember.repository_id == repo_id,
        RepositoryMember.user_id == user_id,
        RepositoryMember.is_active == True
    ).first()
    
    if not member:
        return False
    
    # 如果需要特定角色，检查角色权限
    if required_role:
        # 角色优先级：owner > admin > developer > readonly
        role_priority = {
            "owner": 4,
            "admin": 3,
            "developer": 2,
            "readonly": 1
        }
        
        user_role_priority = role_priority.get(member.role, 0)
        required_role_priority = role_priority.get(required_role, 0)
        
        return user_role_priority >= required_role_priority
    
    return True