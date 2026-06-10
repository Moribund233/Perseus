"""
Git 操作工具模块

提供统一的 Git 操作封装，避免在多个服务中重复实现
"""
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, Optional, Tuple
import pygit2
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.exception import NotFoundException, ValidationException
from models import Repository

# 创建线程池用于执行同步IO操作
_git_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="git_utils")


class GitError(Exception):
    """Git 操作错误"""
    pass


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
    async def from_repository_id(cls, db: AsyncSession, repository_id: int) -> "GitService":
        """
        从仓库 ID 创建 Git 服务实例

        Args:
            db: 异步数据库会话
            repository_id: 仓库ID

        Returns:
            GitService: Git 服务实例

        Raises:
            NotFoundException: 仓库不存在
        """
        result = await db.execute(
            select(Repository).filter(Repository.id == repository_id)
        )
        repo = result.scalar_one_or_none()
        if not repo:
            raise NotFoundException(detail="Repository not found")

        # 从配置获取仓库根目录
        from core.config import get_config
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


async def get_repository_path(db: AsyncSession, repository_id: int) -> str:
    """
    获取仓库的物理路径

    Args:
        db: 异步数据库会话
        repository_id: 仓库ID

    Returns:
        str: 仓库物理路径

    Raises:
        NotFoundException: 仓库不存在
    """
    result = await db.execute(
        select(Repository).filter(Repository.id == repository_id)
    )
    repo = result.scalar_one_or_none()
    if not repo:
        raise NotFoundException(detail="Repository not found")

    # 从配置获取仓库根目录
    from core.config import get_config
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


def init_bare_repo(repo_path: str) -> bool:
    """
    初始化一个 bare Git 仓库（空仓库，无初始提交）

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

        # 创建 bare 仓库（空仓库，无初始提交）
        pygit2.init_repository(repo_path, bare=True)

        return True

    except Exception as e:
        raise GitError(f"Failed to create bare repository: {e}")


def repo_exists(repo_path: str) -> bool:
    """
    检查路径是否是有效的 Git 仓库（同步版本）

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


async def repo_exists_async(repo_path: str) -> bool:
    """
    检查路径是否是有效的 Git 仓库（异步版本）

    使用线程池将同步IO操作转为异步，避免阻塞事件循环

    Args:
        repo_path: 仓库路径

    Returns:
        bool: 是否是有效仓库
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_git_executor, repo_exists, repo_path)


def get_repo_info(repo_path: str) -> Dict[str, Any]:
    """
    获取仓库基本信息

    Args:
        repo_path: 仓库路径

    Returns:
        Dict[str, Any]: 仓库信息，包含分支列表、HEAD提交、是否bare等

    Raises:
        GitError: 获取信息失败
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
        from core.config import get_config
        config = get_config()
        repo_root = config.storage.repo_root if hasattr(config, 'storage') else "./repositories"

    # 将 repo_path 中的 / 转换为系统路径分隔符，并移除开头的分隔符
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
        from core.config import get_config
        config = get_config()
        repo_root = config.storage.repo_root if hasattr(config, 'storage') else "./repositories"

    # 转换为绝对路径
    repo_root = os.path.abspath(repo_root)

    # 确保目录存在
    os.makedirs(repo_root, exist_ok=True)

    return repo_root


# =============================================================================
# PR Diff 相关功能
# =============================================================================

class DiffFileStatus:
    """文件变更状态"""
    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"


def get_pr_diff(repo_path: str, base_commit: str, head_commit: str) -> str:
    """
    获取 PR 的 diff 内容

    使用 git diff 命令获取两个提交之间的变更

    Args:
        repo_path: 仓库物理路径
        base_commit: 基础提交（目标分支）
        head_commit: 头部提交（源分支）

    Returns:
        str: diff 内容

    Raises:
        GitError: 获取 diff 失败
    """
    import subprocess

    try:
        # 使用 git diff 获取变更
        # 格式: git diff base_commit..head_commit
        result = subprocess.run(
            ["git", "diff", f"{base_commit}..{head_commit}"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            encoding="utf-8"
        )

        if result.returncode != 0:
            raise GitError(f"Failed to get diff: {result.stderr}")

        return result.stdout

    except subprocess.SubprocessError as e:
        raise GitError(f"Failed to execute git diff: {e}")


def get_pr_files(repo_path: str, base_commit: str, head_commit: str) -> list:
    """
    获取 PR 变更的文件列表

    Args:
        repo_path: 仓库物理路径
        base_commit: 基础提交（目标分支）
        head_commit: 头部提交（源分支）

    Returns:
        list: 文件列表，每个文件包含状态、路径、增删行数等信息

    Raises:
        GitError: 获取文件列表失败
    """
    import subprocess

    try:
        # 使用 git diff --name-status 获取文件状态
        result = subprocess.run(
            ["git", "diff", "--name-status", f"{base_commit}..{head_commit}"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            encoding="utf-8"
        )

        if result.returncode != 0:
            raise GitError(f"Failed to get file list: {result.stderr}")

        files = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue

            parts = line.split("\t")
            status_code = parts[0]

            if status_code.startswith("A"):
                status = DiffFileStatus.ADDED
                file_path = parts[1]
                old_path = None
            elif status_code.startswith("M"):
                status = DiffFileStatus.MODIFIED
                file_path = parts[1]
                old_path = None
            elif status_code.startswith("D"):
                status = DiffFileStatus.DELETED
                file_path = parts[1]
                old_path = None
            elif status_code.startswith("R"):
                status = DiffFileStatus.RENAMED
                old_path = parts[1]
                file_path = parts[2]
            else:
                status = "unknown"
                file_path = parts[1]
                old_path = None

            files.append({
                "status": status,
                "path": file_path,
                "old_path": old_path,
                "status_code": status_code
            })

        return files

    except subprocess.SubprocessError as e:
        raise GitError(f"Failed to execute git diff: {e}")


def get_pr_stats(repo_path: str, base_commit: str, head_commit: str) -> dict:
    """
    获取 PR 的统计信息

    Args:
        repo_path: 仓库物理路径
        base_commit: 基础提交（目标分支）
        head_commit: 头部提交（源分支）

    Returns:
        dict: 统计信息，包含文件数、新增行数、删除行数等

    Raises:
        GitError: 获取统计信息失败
    """
    import subprocess

    try:
        # 使用 git diff --stat 获取统计信息
        result = subprocess.run(
            ["git", "diff", "--stat", f"{base_commit}..{head_commit}"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            encoding="utf-8"
        )

        if result.returncode != 0:
            raise GitError(f"Failed to get stats: {result.stderr}")

        # 解析统计信息
        lines = result.stdout.strip().split("\n")
        if not lines:
            return {
                "files_changed": 0,
                "additions": 0,
                "deletions": 0,
                "total_changes": 0
            }

        # 最后一行包含总计信息
        # 格式: " X files changed, Y insertions(+), Z deletions(-)"
        last_line = lines[-1]

        files_changed = 0
        additions = 0
        deletions = 0

        # 解析文件数
        if "file changed" in last_line or "files changed" in last_line:
            parts = last_line.split(",")
            for part in parts:
                if "file" in part:
                    files_changed = int(part.strip().split()[0])
                elif "insertion" in part or "insertions" in part:
                    additions = int(part.strip().split()[0])
                elif "deletion" in part or "deletions" in part:
                    deletions = int(part.strip().split()[0])

        return {
            "files_changed": files_changed,
            "additions": additions,
            "deletions": deletions,
            "total_changes": additions + deletions
        }

    except subprocess.SubprocessError as e:
        raise GitError(f"Failed to execute git diff: {e}")


def get_file_diff(repo_path: str, base_commit: str, head_commit: str, file_path: str) -> str:
    """
    获取单个文件的 diff 内容

    Args:
        repo_path: 仓库物理路径
        base_commit: 基础提交（目标分支）
        head_commit: 头部提交（源分支）
        file_path: 文件路径

    Returns:
        str: 文件的 diff 内容

    Raises:
        GitError: 获取 diff 失败
    """
    import subprocess

    try:
        result = subprocess.run(
            ["git", "diff", f"{base_commit}..{head_commit}", "--", file_path],
            cwd=repo_path,
            capture_output=True,
            text=True,
            encoding="utf-8"
        )

        if result.returncode != 0:
            raise GitError(f"Failed to get file diff: {result.stderr}")

        return result.stdout

    except subprocess.SubprocessError as e:
        raise GitError(f"Failed to execute git diff: {e}")
