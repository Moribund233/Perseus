"""
仓库服务层

处理与Git仓库相关的所有业务逻辑
"""
import os
import logging
from sqlalchemy.orm import Session
from models import Repository
from models.branch import Branch
from models.repository_member import RepositoryMember
from exception import ValidationException, NotFoundException, ConflictException
from client.utils.git_utils import init_bare_repo, get_repository_storage_path, repo_exists, GitError

# 日志记录器
logger = logging.getLogger(__name__)

# 常量定义
ROLE_PRIORITY = {
    "owner": 4,
    "admin": 3,
    "developer": 2,
    "readonly": 1
}


def _build_repo_response(repo: Repository) -> dict:
    """
    构建仓库响应数据（不包含敏感物理路径信息）

    Args:
        repo: Repository 模型对象

    Returns:
        dict: 仓库数据（不包含物理路径）
    """
    # 获取物理仓库状态（仅检查是否存在，不暴露路径）
    try:
        physical_path = get_repository_storage_path(repo.path)
        physical_exists = repo_exists(physical_path)
    except Exception:
        physical_exists = False

    return {
        "id": repo.id,
        "name": repo.name,
        "path": repo.path,
        "description": repo.description,
        "is_public": repo.is_public,
        "owner_id": repo.owner_id,
        "default_branch": repo.default_branch,
        "created_at": repo.created_at,
        "updated_at": repo.updated_at,
        "status": {
            "initialized": physical_exists
        }
    }


def get_repositories(db: Session):
    """
    获取所有仓库

    Args:
        db: 数据库会话

    Returns:
        list[dict]: 仓库列表（包含物理仓库信息）
    """
    repos = db.query(Repository).all()
    # 返回包含物理仓库信息的字典列表
    return [_build_repo_response(repo) for repo in repos]


def get_repository_by_id(repo_id: int, db: Session):
    """
    根据ID获取仓库

    Args:
        repo_id: 仓库ID
        db: 数据库会话

    Returns:
        dict: 仓库信息（包含物理仓库信息）

    Raises:
        NotFoundException: 仓库不存在时抛出404异常
    """
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if repo is None:
        raise NotFoundException(detail="Repository not found")
    # 返回包含物理仓库信息的字典
    return _build_repo_response(repo)


def get_repositories_by_user(user_id: int, db: Session):
    """
    根据用户ID获取仓库列表

    Args:
        user_id: 用户ID
        db: 数据库会话

    Returns:
        list[dict]: 仓库列表（包含物理仓库信息）
    """
    # 查询用户拥有的仓库
    owned_repos = db.query(Repository).filter(Repository.owner_id == user_id).all()

    # 查询用户参与的仓库（通过repository_members表）
    member_repos = db.query(Repository).join(RepositoryMember).filter(RepositoryMember.user_id == user_id).all()

    # 合并结果，去重
    all_repos = list(set(owned_repos + member_repos))

    # 返回包含物理仓库信息的字典列表
    return [_build_repo_response(repo) for repo in all_repos]


def create_repository(repo_data: dict, db: Session):
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
    default_branch = Branch(
        name=db_repo.default_branch,
        repository_id=db_repo.id,
        is_protected=True,
        is_default=True
    )
    db.add(default_branch)
    db.commit()

    # 添加仓库所有者为成员
    owner_member = RepositoryMember(
        repository_id=db_repo.id,
        user_id=db_repo.owner_id,
        role="owner"
    )
    db.add(owner_member)
    db.commit()

    # 创建物理 Git 仓库
    try:
        physical_path = get_repository_storage_path(db_repo.path)
        init_bare_repo(physical_path)
    except GitError as e:
        # 物理仓库创建失败，记录错误但不阻止创建
        # 因为数据库记录已经创建，可以后续手动修复
        logger.warning(f"Failed to create physical git repository at {physical_path}: {e}")
    except Exception as e:
        # 其他错误，记录但不阻止
        logger.warning(f"Unexpected error creating git repository: {e}")

    # 返回包含物理仓库信息的字典
    return _build_repo_response(db_repo)


def update_repository(repo_id: int, repo_data: dict, db: Session):
    """
    更新仓库信息

    Args:
        repo_id: 仓库ID
        repo_data: 更新的仓库信息
        db: 数据库会话

    Returns:
        dict: 更新后的仓库信息（包含物理仓库信息）

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

    # 返回包含物理仓库信息的字典
    return _build_repo_response(db_repo)


def delete_repository(repo_id: int, db: Session):
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
    import shutil
    db_repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if db_repo is None:
        raise NotFoundException(detail="Repository not found")

    # 获取物理仓库路径
    try:
        physical_path = get_repository_storage_path(db_repo.path)
        if os.path.exists(physical_path):
            shutil.rmtree(physical_path)
            logger.info(f"物理仓库已删除: {physical_path}")
    except Exception as e:
        # 物理仓库删除失败，记录错误但不阻止数据库删除
        logger.warning(f"Failed to delete physical repository at {physical_path}: {e}")

    db.delete(db_repo)
    db.commit()

    return {"message": "Repository deleted successfully"}


def get_public_repositories(db: Session):
    """
    获取所有公开仓库

    Args:
        db: 数据库会话

    Returns:
        list[dict]: 公开仓库列表（包含物理仓库信息）
    """
    repos = db.query(Repository).filter(Repository.is_public == True).all()
    # 返回包含物理仓库信息的字典列表
    return [_build_repo_response(repo) for repo in repos]


def check_repository_access(repo_id: int, user_id: int, db: Session, required_role: str = None):
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
    repo = get_repository_by_id(repo_id, db)

    # 检查仓库是否公开
    if repo["is_public"] and required_role is None:
        return True

    # 检查用户是否是仓库所有者
    if repo["owner_id"] == user_id:
        return True

    # 检查用户是否是仓库成员
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
        user_role_priority = ROLE_PRIORITY.get(member.role, 0)
        required_role_priority = ROLE_PRIORITY.get(required_role, 0)

        return user_role_priority >= required_role_priority

    return True
