"""
Git 操作工具模块 - 使用 pygit2

提供 Git 仓库的创建和管理功能
"""
import os
from pathlib import Path
from typing import Optional, List, Dict, Any

import pygit2


class GitError(Exception):
    """Git 操作错误"""
    pass


def init_bare_repo(repo_path: str) -> bool:
    """
    初始化一个 bare Git 仓库

    Args:
        repo_path: 仓库目录路径

    Returns:
        bool: 是否成功创建（True=新创建，False=已存在）

    Raises:
        GitError: 创建失败
    """
    try:
        # 确保父目录存在
        parent_dir = os.path.dirname(repo_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)

        # 如果已是仓库，返回 False
        if os.path.exists(os.path.join(repo_path, "HEAD")):
            return False

        # 创建 bare 仓库
        pygit2.init_repository(repo_path, bare=True)

        return True

    except Exception as e:
        raise GitError(f"Failed to create bare repository: {e}")


def repo_exists(repo_path: str) -> bool:
    """
    检查路径是否是有效的 Git 仓库

    Args:
        repo_path: 仓库路径

    Returns:
        bool: 是否是有效仓库
    """
    try:
        pygit2.Repository(repo_path)
        return True
    except Exception:
        return False


def get_repo_info(repo_path: str) -> Dict[str, Any]:
    """
    获取仓库基本信息

    Args:
        repo_path: 仓库路径

    Returns:
        dict: 仓库信息
    """
    try:
        repo = pygit2.Repository(repo_path)

        # 获取分支列表
        branches = list(repo.branches.local)

        # 获取 HEAD
        try:
            head = repo.head
            head_commit = str(head.target) if not repo.head_is_unborn else None
        except Exception:
            head_commit = None

        return {
            "branches": branches,
            "head_commit": head_commit,
            "is_bare": repo.is_bare
        }

    except Exception as e:
        raise GitError(f"Failed to get repo info: {e}")


def get_repository_storage_path(repo_path: str, repo_root: Optional[str] = None) -> str:
    """
    获取仓库的物理存储路径

    Args:
        repo_path: 仓库的逻辑路径（如 /repos/test-repo）
        repo_root: 仓库根目录，如果为None则从配置读取

    Returns:
        str: 物理存储路径
    """
    if repo_root is None:
        # 从配置读取
        from client.utils.config_manager import get_client_config_manager
        config_manager = get_client_config_manager()
        repo_root = config_manager.get("storage.repo_root", "./repositories")

    # 将 repo_path 中的 / 转换为系统路径分隔符，并移除开头的分隔符
    # 使用 normpath 处理路径中的多余分隔符
    normalized_path = os.path.normpath(repo_path)
    clean_path = normalized_path.lstrip(os.sep)
    return os.path.join(repo_root, clean_path)


def ensure_repository_root(repo_root: Optional[str] = None) -> str:
    """
    确保仓库根目录存在

    Args:
        repo_root: 仓库根目录，如果为None则从配置读取

    Returns:
        str: 仓库根目录路径
    """
    if repo_root is None:
        # 从配置读取
        from client.utils.config_manager import get_client_config_manager
        config_manager = get_client_config_manager()
        repo_root = config_manager.get("storage.repo_root", "./repositories")

    # 转换为绝对路径
    repo_root = os.path.abspath(repo_root)

    # 确保目录存在
    os.makedirs(repo_root, exist_ok=True)

    return repo_root
