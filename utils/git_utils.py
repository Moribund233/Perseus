"""
Git 操作工具模块

提供统一的 Git 操作封装，避免在多个服务中重复实现
"""
import os
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, Optional, Tuple, List, cast
import uuid
import pygit2
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.exception import NotFoundException, ValidationException
from models import Repository
import uuid

logger = logging.getLogger(__name__)

# 创建线程池用于执行同步IO操作
_git_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="git_utils")


class GitError(Exception):
    """Git 操作错误"""
    pass


def create_signature(name: str, email: str) -> pygit2.Signature:
    """创建 Git 签名 (模块级便捷封装)"""
    return pygit2.Signature(name, email)


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
    async def from_repository_id(cls, db: AsyncSession, repository_id: uuid.UUID) -> "GitService":
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

        repo_path = get_repository_storage_path(repo.path)
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

            # 检查是否有冲突 - pygit2 Index 对象通过 conflicts 属性检查
            # 如果存在冲突，index.conflicts 会包含冲突条目
            try:
                # 尝试访问冲突，如果有冲突会返回冲突迭代器
                if index.conflicts is None:
                    return False
                conflicts = list(index.conflicts)
                return len(conflicts) > 0
            except (AttributeError, KeyError, TypeError):
                # 如果没有冲突属性或 KeyError，说明没有冲突
                return False

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

            # 检查是否有冲突
            has_conflicts = False
            try:
                if index.conflicts is not None:
                    conflicts = list(index.conflicts)
                    has_conflicts = len(conflicts) > 0
            except (AttributeError, KeyError, TypeError):
                has_conflicts = False

            if has_conflicts:
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

    def squash_branches(
        self,
        source_branch: str,
        target_branch: str,
        signature: pygit2.Signature,
        message: str
    ) -> str:
        """
        执行 squash 合并

        将源分支的所有提交压缩为单个提交合并到目标分支。
        与 merge 不同，squash 不会保留源分支的提交历史。

        Args:
            source_branch: 源分支名称
            target_branch: 目标分支名称
            signature: Git 签名
            message: 提交信息

        Returns:
            str: 新提交的哈希

        Raises:
            ValidationException: 合并失败或有冲突
        """
        try:
            source_ref_name = f"refs/heads/{source_branch}"
            target_ref_name = f"refs/heads/{target_branch}"

            source_commit = self.repo.references[source_ref_name].peel(pygit2.Commit)
            target_commit = self.repo.references[target_ref_name].peel(pygit2.Commit)

            # 执行合并获取合并后的树
            index = self.repo.merge_commits(target_commit, source_commit)

            # 检查是否有冲突
            has_conflicts = False
            try:
                if index.conflicts is not None:
                    conflicts = list(index.conflicts)
                    has_conflicts = len(conflicts) > 0
            except (AttributeError, KeyError, TypeError):
                has_conflicts = False

            if has_conflicts:
                raise ValidationException(detail="Merge conflicts detected")

            # 写入树对象
            tree_oid = index.write_tree(self.repo)

            # 创建单个提交（只有一个父提交）
            parents = [target_commit.id]  # 只有目标分支作为父提交
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
            raise ValidationException(detail=f"Squash merge failed: {str(e)}")

    def rebase_branches(
        self,
        source_branch: str,
        target_branch: str,
        signature: pygit2.Signature
    ) -> str:
        """
        执行 rebase 合并

        将源分支的提交逐个重放到目标分支的最新提交之上。
        这会重写提交历史，使提交历史保持线性。

        Args:
            source_branch: 源分支名称
            target_branch: 目标分支名称
            signature: Git 签名（用于重写提交）

        Returns:
            str: 最后一个新提交的哈希

        Raises:
            ValidationException: rebase 失败或有冲突
        """
        try:
            source_ref_name = f"refs/heads/{source_branch}"
            target_ref_name = f"refs/heads/{target_branch}"

            source_commit = self.repo.references[source_ref_name].peel(pygit2.Commit)
            target_commit = self.repo.references[target_ref_name].peel(pygit2.Commit)

            # 找到源分支和目标分支的共同祖先
            merge_base = self.repo.merge_base(target_commit.id, source_commit.id)
            if not merge_base:
                raise ValidationException(detail="Cannot find merge base for rebase")

            # 获取源分支上需要重放的提交列表（从旧到新）
            commits_to_replay: List[pygit2.Commit] = []
            current: pygit2.Commit | None = source_commit
            while current is not None and current.id != merge_base:
                commits_to_replay.insert(0, current)  # 插入到开头，保持顺序
                if len(current.parents) == 0:
                    break
                # parents[0] 返回的是 Commit 对象，需要获取其 id
                parent_commit = current.parents[0]
                obj = self.repo.get(parent_commit.id)
                if obj is None or not isinstance(obj, pygit2.Commit):
                    raise ValidationException(detail="Cannot resolve parent commit for rebase")
                current = obj

            if not commits_to_replay:
                # 没有需要重放的提交，直接返回目标分支
                return str(target_commit.id)

            # 逐个重放提交
            parent_commit = target_commit
            last_commit_oid = None

            for commit in commits_to_replay:
                # 创建新的提交，父提交是当前目标分支的最新提交
                # 使用 commit.tree_id 获取树对象的 OID
                commit_oid = self.repo.create_commit(
                    target_ref_name,  # 更新目标分支引用
                    commit.author,    # 保留原作者
                    signature,        # 使用新的提交者
                    commit.message,   # 保留原提交信息
                    commit.tree_id,   # 使用提交中的树 ID
                    [parent_commit.id]
                )

                last_commit_oid = commit_oid
                obj = self.repo.get(commit_oid)
                if obj is None or not isinstance(obj, pygit2.Commit):
                    raise ValidationException(detail="Failed to resolve replayed commit")
                parent_commit = obj

            return str(last_commit_oid)

        except ValidationException:
            raise
        except Exception as e:
            raise ValidationException(detail=f"Rebase merge failed: {str(e)}")

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


async def get_repository_path(db: AsyncSession, repository_id: uuid.UUID, repo_root: Optional[str] = None) -> str:
    """
    获取仓库的物理路径

    Args:
        db: 异步数据库会话
        repository_id: 仓库ID
        repo_root: 仓库根目录（可选，用于测试）

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

    return get_repository_storage_path(repo.path, repo_root=repo_root)


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


def init_bare_repo(repo_path: str, default_branch: str = "master") -> bool:
    """
    初始化一个 bare Git 仓库（空仓库，无初始提交）

    get_repository_storage_path 已添加 .git 后缀，此处假设传入了含后缀的完整路径。

    Args:
        repo_path: 仓库物理路径（含 .git 后缀，如 /data/repositories/admin/Eridanus.git）
        default_branch: 默认分支名，用于设置 HEAD 符号引用。
                        默认与 libgit2 行为一致 (master)；
                        新仓库创建时应显式传入以与 DB 默认分支对齐，
                        避免用户推送 main 后 HEAD 悬空。

    Returns:
        bool: 是否成功创建（True=新创建，False=已存在）

    Raises:
        GitError: 创建失败
    """
    physical_path = repo_path

    try:
        # 确保父目录存在
        parent_dir = os.path.dirname(physical_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)

        # 如果已是仓库，返回 False
        if os.path.exists(os.path.join(physical_path, "HEAD")):
            return False

        # 创建 bare 仓库（空仓库，无初始提交）
        repo = pygit2.init_repository(physical_path, bare=True)

        # HEAD 对齐默认分支（此时分支尚不存在, HEAD 处于 unborn 状态, 属正常情况）
        if repo and default_branch and default_branch != "master":
            repo.set_head(f"refs/heads/{default_branch}")

        return True

    except Exception as e:
        raise GitError(f"Failed to create bare repository at {physical_path}: {e}")


def get_local_branch_names(repo_path: str) -> list:
    """
    获取仓库所有本地分支名

    Args:
        repo_path: 仓库物理路径

    Returns:
        list[str]: 分支名列表, 仓库不存在时返回空列表
    """
    try:
        repo = pygit2.Repository(repo_path)
    except Exception:
        return []
    return list(repo.branches.local)


def set_head_branch(repo_path: str, branch: str) -> bool:
    """
    设置 bare 仓库 HEAD 符号引用指向指定分支

    Args:
        repo_path: 仓库物理路径
        branch: 分支名

    Returns:
        bool: 是否设置成功
    """
    if not branch or ".." in branch or branch.startswith("/"):
        return False
    try:
        repo = pygit2.Repository(repo_path)
        repo.set_head(f"refs/heads/{branch}")
        return True
    except Exception:
        return False


def enable_receive_pack(repo_path: str) -> None:
    """
    启用仓库的 Git HTTP receive-pack（允许通过 HTTP push）。

    git-http-backend 默认仅启用 upload-pack（clone/fetch），
    receive-pack（push）需要仓库配置 http.receivepack=true。

    Args:
        repo_path: bare 仓库的完整物理路径（含 .git 后缀）
    """
    config_path = os.path.join(repo_path, "config")
    try:
        import subprocess
        result = subprocess.run(
            ["git", "config", "--file", config_path,
             "http.receivepack", "true"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            logger.warning(f"Failed to set http.receivepack for {repo_path}: {result.stderr.strip()}")
        else:
            logger.info(f"Enabled http.receivepack for {repo_path}")
    except Exception as e:
        logger.warning(f"Failed to enable receive-pack for {repo_path}: {e}")





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

    自动添加 .git 后缀以匹配 Git HTTP Smart Protocol 的路径约定。
    git-http-backend 从 URL（如 /admin/repo.git/info/refs）提取带有 .git 后缀的路径，
    因此物理仓库目录需要以 .git 结尾。

    Args:
        repo_path: 仓库的逻辑路径（如 admin/test-repo，不含 .git 后缀）
        repo_root: 仓库根目录，如果为None则从配置读取

    Returns:
        str: 物理存储路径（含 .git 后缀）
    """
    if repo_root is None:
        # 从配置读取
        from core.config import get_config
        config = get_config()
        repo_root = config.storage.repo_root if hasattr(config, 'storage') else "./repositories"

    # 将 repo_path 中的 / 转换为系统路径分隔符，并移除开头的分隔符
    normalized_path = os.path.normpath(repo_path)
    clean_path = normalized_path.lstrip(os.sep)

    # 添加 .git 后缀以兼容 git-http-backend 的路径查找约定
    if clean_path and not clean_path.endswith('.git'):
        clean_path += '.git'

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


def commit_file_changes(
    repo_path: str,
    branch: str,
    file_path: str,
    content: str,
    author_name: str,
    author_email: str,
    message: str,
    encoding: str = "utf-8",
) -> Dict[str, Any]:
    """
    在指定分支创建/更新单个文件并提交 (裸仓库)

    空仓库 (无任何分支) 时会创建初始提交并建立该分支。

    Args:
        repo_path: 仓库物理路径
        branch: 目标分支名 (不存在则创建)
        file_path: 文件在仓库内的路径 (如 "src/main.py")
        content: 文件文本内容
        author_name / author_email: 提交作者
        message: 提交信息
        encoding: 内容编码

    Returns:
        dict: {commit_id, branch, path}
    """
    repo = pygit2.Repository(repo_path)

    file_path = file_path.strip("/")
    if not file_path or ".." in file_path.split("/"):
        raise ValidationException(detail="Invalid file path")
    if not branch or ".." in branch or branch.startswith("/"):
        raise ValidationException(detail="Invalid branch name")

    parts = file_path.split("/")
    ref_name = f"refs/heads/{branch}"

    parent_commit = None
    base_tree = None
    if repo.branches.local.get(branch) is not None:
        # Repository.__getitem__ 仅接受 OID, 引用名需用 lookup_reference 解析
        parent_commit = repo.lookup_reference(ref_name).peel(pygit2.Commit)
        base_tree = parent_commit.tree
    elif not repo.head_is_unborn:
        # 目标分支不存在但仓库已有提交: 基于当前 HEAD fork 新分支,
        # 避免在非空仓库上创建与既有历史无关的孤儿根提交
        parent_commit = repo.head.peel(pygit2.Commit)
        base_tree = parent_commit.tree

    blob_id = repo.create_blob(content.encode(encoding))

    def _upsert(tree: Optional[pygit2.Tree], segments) -> pygit2.Oid:
        # TreeBuilder 不接受显式 None, 缺省调用以获得空 builder
        tb = repo.TreeBuilder(tree) if tree is not None else repo.TreeBuilder()
        name = segments[0]
        if len(segments) == 1:
            tb.insert(name, blob_id, pygit2.GIT_FILEMODE_BLOB)
        else:
            subtree: Optional[pygit2.Tree] = None
            if tree is not None:
                try:
                    entry = tree[name]
                    if entry.type == pygit2.GIT_OBJECT_TREE:
                        subtree = cast(pygit2.Tree, repo[entry.id])
                except KeyError:
                    subtree = None
            child_id = _upsert(subtree, segments[1:])
            tb.insert(name, child_id, pygit2.GIT_FILEMODE_TREE)
        return tb.write()

    tree_id = _upsert(base_tree, parts)

    author = create_signature(author_name, author_email)
    parents = [parent_commit.id] if parent_commit is not None else []
    commit_id = repo.create_commit(ref_name, author, author, message, tree_id, parents)

    return {"commit_id": str(commit_id), "branch": branch, "path": file_path}


def delete_file_changes(
    repo_path: str,
    branch: str,
    file_path: str,
    author_name: str,
    author_email: str,
    message: str,
) -> Dict[str, Any]:
    """
    在指定分支删除单个文件并提交
    """
    repo = pygit2.Repository(repo_path)
    file_path = file_path.strip("/")
    if not file_path or ".." in file_path.split("/"):
        raise ValidationException(detail="Invalid file path")

    ref_name = f"refs/heads/{branch}"
    if repo.branches.local.get(branch) is None:
        raise NotFoundException(detail=f"Branch not found: {branch}")

    parent_commit = repo.lookup_reference(ref_name).peel(pygit2.Commit)

    def _remove(tree: pygit2.Tree, segments) -> pygit2.Oid:
        tb = repo.TreeBuilder(tree)
        name = segments[0]
        if len(segments) == 1:
            # 先确认条目存在 (合成 KeyError → NotFound), 避免 tb.remove 抛 pygit2.GitError 导致 500
            try:
                tree[name]
            except KeyError:
                raise NotFoundException(detail=f"File not found: {file_path}")
            tb.remove(name)
        else:
            try:
                entry = tree[name]
            except KeyError:
                raise NotFoundException(detail=f"File not found: {file_path}")
            if entry.type != pygit2.GIT_OBJECT_TREE:
                raise NotFoundException(detail=f"File not found: {file_path}")
            child_obj = repo[entry.id]
            if not isinstance(child_obj, pygit2.Tree):
                raise NotFoundException(detail=f"File not found: {file_path}")
            child_id = _remove(child_obj, segments[1:])
            # 子树删空后一并移除该目录项 (git 不会保留空目录)
            child_tree = repo[child_id]
            if not isinstance(child_tree, pygit2.Tree):
                raise NotFoundException(detail=f"File not found: {file_path}")
            if len(child_tree) == 0:
                tb.remove(name)
            else:
                tb.insert(name, child_id, pygit2.GIT_FILEMODE_TREE)
        return tb.write()

    tree_id = _remove(parent_commit.tree, file_path.split("/"))
    author = create_signature(author_name, author_email)
    commit_id = repo.create_commit(
        ref_name, author, author, message, tree_id, [parent_commit.id]
    )
    return {"commit_id": str(commit_id), "branch": branch, "path": file_path}
