"""
Git 操作工具模块

提供统一的 Git 操作封装，避免在多个服务中重复实现
"""
import os
from typing import Optional, Tuple
import pygit2
from sqlalchemy.orm import Session

from exception import NotFoundException, ValidationException
from models import Repository


class GitService:
    """
    Git 服务类

    封装常用的 Git 操作，提供统一的接口
    """

    def __init__(self, repo_path: str):
        """
        初始化 Git 服务

        Args:
            repo_path: 仓库物理路径

        Raises:
            ValidationException: 仓库路径不存在或不是有效的 Git 仓库
        """
        if not os.path.exists(repo_path):
            raise NotFoundException(detail=f"Repository path not found: {repo_path}")

        try:
            self.repo_path = repo_path
            self.repo = pygit2.Repository(repo_path)
        except Exception as e:
            raise ValidationException(detail=f"Invalid git repository: {str(e)}")

    @classmethod
    def from_repository_id(cls, db: Session, repository_id: int) -> "GitService":
        """
        从仓库 ID 创建 Git 服务实例

        Args:
            db: 数据库会话
            repository_id: 仓库ID

        Returns:
            GitService: Git 服务实例

        Raises:
            NotFoundException: 仓库不存在
        """
        repo = db.query(Repository).filter(Repository.id == repository_id).first()
        if not repo:
            raise NotFoundException(detail="Repository not found")

        # 从配置获取仓库根目录
        from config import get_config
        config = get_config()
        repo_root = config.storage.repo_root

        repo_path = os.path.join(repo_root, repo.path)
        return cls(repo_path)

    def check_merge_conflicts(
        self,
        source_branch: str,
        target_branch: str
    ) -> bool:
        """
        检查分支之间是否有合并冲突

        Args:
            source_branch: 源分支
            target_branch: 目标分支

        Returns:
            bool: 是否有冲突

        Raises:
            ValidationException: 分支不存在或检查失败
        """
        try:
            # 获取分支引用
            source_ref = f"refs/heads/{source_branch}"
            target_ref = f"refs/heads/{target_branch}"

            # 检查分支是否存在
            if source_ref not in self.repo.references or target_ref not in self.repo.references:
                return True  # 分支不存在视为有冲突

            # 获取提交
            source_commit = self.repo.references[source_ref].peel(pygit2.Commit)
            target_commit = self.repo.references[target_ref].peel(pygit2.Commit)

            # 创建临时索引进行合并测试
            index = self.repo.merge_commits(target_commit, source_commit)

            # 检查是否有冲突
            return index.has_conflicts

        except Exception as e:
            raise ValidationException(detail=f"Failed to check merge conflicts: {str(e)}")

    def merge_branches(
        self,
        source_branch: str,
        target_branch: str,
        signature: pygit2.Signature,
        message: str
    ) -> str:
        """
        执行分支合并

        Args:
            source_branch: 源分支
            target_branch: 目标分支
            signature: 提交签名
            message: 合并提交信息

        Returns:
            str: 合并后的提交哈希

        Raises:
            ValidationException: 合并失败或有冲突
        """
        try:
            # 获取分支引用
            source_ref_name = f"refs/heads/{source_branch}"
            target_ref_name = f"refs/heads/{target_branch}"

            source_commit = self.repo.references[source_ref_name].peel(pygit2.Commit)
            target_commit = self.repo.references[target_ref_name].peel(pygit2.Commit)

            # 执行合并
            index = self.repo.merge_commits(target_commit, source_commit)

            if index.has_conflicts:
                raise ValidationException(detail="Merge conflicts detected")

            # 写入树对象
            tree_oid = index.write_tree(self.repo)

            # 创建合并提交
            parents = [target_commit.id, source_commit.id]
            commit_oid = self.repo.create_commit(
                target_ref_name,  # 更新目标分支
                signature,  # 作者
                signature,  # 提交者
                message,
                tree_oid,
                parents
            )

            return str(commit_oid)

        except ValidationException:
            raise
        except Exception as e:
            raise ValidationException(detail=f"Merge failed: {str(e)}")

    def get_branch_commit(self, branch_name: str) -> Optional[pygit2.Commit]:
        """
        获取分支的最新提交

        Args:
            branch_name: 分支名称

        Returns:
            Commit: 最新提交对象，分支不存在返回 None
        """
        ref_name = f"refs/heads/{branch_name}"
        if ref_name not in self.repo.references:
            return None
        return self.repo.references[ref_name].peel(pygit2.Commit)

    def branch_exists(self, branch_name: str) -> bool:
        """
        检查分支是否存在

        Args:
            branch_name: 分支名称

        Returns:
            bool: 分支是否存在
        """
        ref_name = f"refs/heads/{branch_name}"
        return ref_name in self.repo.references

    def create_signature(self, name: str, email: str) -> pygit2.Signature:
        """
        创建 Git 签名

        Args:
            name: 用户名
            email: 邮箱

        Returns:
            Signature: Git 签名对象
        """
        return pygit2.Signature(name, email)


def get_repository_path(db: Session, repository_id: int) -> str:
    """
    获取仓库的物理路径

    Args:
        db: 数据库会话
        repository_id: 仓库ID

    Returns:
        str: 仓库物理路径

    Raises:
        NotFoundException: 仓库不存在
    """
    repo = db.query(Repository).filter(Repository.id == repository_id).first()
    if not repo:
        raise NotFoundException(detail="Repository not found")

    # 从配置获取仓库根目录
    from config import get_config
    config = get_config()
    repo_root = config.storage.repo_root

    return os.path.join(repo_root, repo.path)


def check_merge_conflicts(
    repo_path: str,
    source_branch: str,
    target_branch: str
) -> bool:
    """
    检查分支之间是否有合并冲突（便捷函数）

    Args:
        repo_path: 仓库路径
        source_branch: 源分支
        target_branch: 目标分支

    Returns:
        bool: 是否有冲突
    """
    git_service = GitService(repo_path)
    return git_service.check_merge_conflicts(source_branch, target_branch)


def perform_git_merge(
    repo_path: str,
    source_branch: str,
    target_branch: str,
    merger_name: str,
    merger_email: str,
    message: str
) -> str:
    """
    执行实际的 Git 合并操作（便捷函数）

    Args:
        repo_path: 仓库路径
        source_branch: 源分支
        target_branch: 目标分支
        merger_name: 合并者名称
        merger_email: 合并者邮箱
        message: 合并提交信息

    Returns:
        str: 合并后的提交哈希
    """
    git_service = GitService(repo_path)
    signature = git_service.create_signature(merger_name, merger_email)
    return git_service.merge_branches(source_branch, target_branch, signature, message)
