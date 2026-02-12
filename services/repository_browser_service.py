"""
仓库代码浏览服务层

处理与代码浏览相关的业务逻辑：
- 文件树浏览
- 文件内容查看
- 提交历史
- 代码对比
"""
import os
from typing import List, Dict, Any, Optional
from datetime import datetime

import pygit2

from utils.git_utils import repo_exists
from exception import (
    NotFoundException,
    ValidationException,
    RepositoryNotFoundException,
    PathNotFoundException,
    InvalidPathException
)


def _get_repo(repo_path: str) -> pygit2.Repository:
    """
    获取仓库对象
    
    Args:
        repo_path: 仓库物理路径
        
    Returns:
        pygit2.Repository: 仓库对象
        
    Raises:
        RepositoryNotFoundException: 仓库不存在或无法打开
    """
    if not repo_exists(repo_path):
        raise RepositoryNotFoundException(f"Repository not found: {repo_path}")

    try:
        return pygit2.Repository(repo_path)
    except Exception as e:
        raise RepositoryNotFoundException(f"Failed to open repository: {e}")


def _resolve_ref(repo: pygit2.Repository, ref: str) -> pygit2.Commit:
    """
    解析引用为提交对象
    
    Args:
        repo: 仓库对象
        ref: 引用名称（分支名、标签名或提交SHA）
        
    Returns:
        pygit2.Commit: 提交对象
        
    Raises:
        PathNotFoundException: 引用不存在
    """
    try:
        # 尝试直接解析为提交
        return repo.revparse_single(ref).peel(pygit2.Commit)
    except (KeyError, ValueError):
        # 尝试添加 refs/heads/ 前缀
        try:
            return repo.revparse_single(f"refs/heads/{ref}").peel(pygit2.Commit)
        except (KeyError, ValueError):
            raise PathNotFoundException(f"Ref not found: {ref}")


def _get_tree(repo: pygit2.Repository, commit: pygit2.Commit, path: str = "") -> pygit2.Tree:
    """
    获取指定路径的树对象
    
    Args:
        repo: 仓库对象
        commit: 提交对象
        path: 路径（可选）
        
    Returns:
        pygit2.Tree: 树对象
        
    Raises:
        PathNotFoundException: 路径不存在
        InvalidPathException: 路径不是目录
    """
    if not path:
        return commit.tree

    try:
        entry = commit.tree[path]
        if entry.type == pygit2.GIT_OBJECT_TREE:
            return repo[entry.id]
        else:
            raise InvalidPathException(f"'{path}' is not a directory")
    except KeyError:
        raise PathNotFoundException(f"Path not found: {path}")


def get_tree_entries(
    repo_path: str,
    ref: str = "HEAD",
    path: str = ""
) -> Dict[str, Any]:
    """
    获取文件树条目
    
    Args:
        repo_path: 仓库物理路径
        ref: 分支名或提交SHA，默认 HEAD
        path: 子目录路径，默认根目录
        
    Returns:
        dict: 包含路径列表和条目列表的字典
        
    Raises:
        RepositoryNotFoundException: 仓库不存在
        PathNotFoundException: 引用或路径不存在
        InvalidPathException: 路径不是目录
    """
    repo = _get_repo(repo_path)
    commit = _resolve_ref(repo, ref)
    tree = _get_tree(repo, commit, path)
    
    # 构建路径列表
    path_parts = path.split("/") if path else []
    paths = [{"name": "root", "path": ""}]
    current_path = ""
    for part in path_parts:
        current_path = f"{current_path}/{part}" if current_path else part
        paths.append({"name": part, "path": current_path})
    
    # 构建条目列表
    entries = []
    for entry in tree:
        entry_data = {
            "name": entry.name,
            "type": "tree" if entry.type == pygit2.GIT_OBJECT_TREE else "blob",
            "path": f"{path}/{entry.name}" if path else entry.name,
            "sha": str(entry.id),
            "mode": entry.filemode
        }

        # 如果是文件，添加大小信息
        if entry.type == pygit2.GIT_OBJECT_BLOB:
            blob = repo[entry.id]
            entry_data["size"] = blob.size

        entries.append(entry_data)

    # 按类型排序（目录在前）和名称排序
    entries.sort(key=lambda x: (0 if x["type"] == "tree" else 1, x["name"]))

    return {
        "path": path,
        "ref": ref,
        "entries": entries
    }


def get_blob_content(
    repo_path: str,
    ref: str = "HEAD",
    path: str = None
) -> Dict[str, Any]:
    """
    获取文件内容
    
    Args:
        repo_path: 仓库物理路径
        ref: 分支名或提交SHA，默认 HEAD
        path: 文件路径（必填）
        
    Returns:
        dict: 包含文件内容的字典
        
    Raises:
        RepositoryNotFoundException: 仓库不存在
        PathNotFoundException: 引用或文件不存在
        InvalidPathException: 路径是目录或不是有效文件
    """
    if not path:
        raise InvalidPathException("Path is required")
    
    repo = _get_repo(repo_path)
    commit = _resolve_ref(repo, ref)
    
    try:
        entry = commit.tree[path]
    except KeyError:
        raise PathNotFoundException(f"File not found: {path}")

    if entry.type == pygit2.GIT_OBJECT_TREE:
        raise InvalidPathException(f"'{path}' is a directory, not a file")

    if entry.type != pygit2.GIT_OBJECT_BLOB:
        raise InvalidPathException(f"'{path}' is not a valid file")
    
    blob = repo[entry.id]
    
    # 尝试解码为文本
    try:
        content = blob.data.decode('utf-8')
        is_binary = False
    except UnicodeDecodeError:
        content = blob.data.hex()
        is_binary = True
    
    return {
        "name": os.path.basename(path),
        "path": path,
        "sha": str(entry.id),
        "ref": ref,
        "content": content,
        "size": blob.size,
        "encoding": "utf-8" if not is_binary else "hex",
        "is_binary": is_binary
    }


def get_commits(
    repo_path: str,
    ref: str = "HEAD",
    path: str = None,
    page: int = 1,
    per_page: int = 30
) -> Dict[str, Any]:
    """
    获取提交历史
    
    Args:
        repo_path: 仓库物理路径
        ref: 分支名或提交SHA，默认 HEAD
        path: 特定文件路径，None 表示所有提交
        page: 页码，默认 1
        per_page: 每页数量，默认 30
        
    Returns:
        dict: 包含提交列表和分页信息的字典
        
    Raises:
        RepositoryNotFoundException: 仓库不存在
        PathNotFoundException: 引用不存在
    """
    repo = _get_repo(repo_path)
    commit = _resolve_ref(repo, ref)
    
    commits = []
    walker = repo.walk(commit.id, pygit2.GIT_SORT_TIME)
    
    # 如果指定了路径，只获取该文件的提交
    if path:
        walker.simplify_first_parent()
    
    # 分页
    skip = (page - 1) * per_page
    for i, commit_obj in enumerate(walker):
        if i < skip:
            continue
        if i >= skip + per_page:
            break
        
        commits.append({
            "sha": str(commit_obj.id),
            "message": commit_obj.message,
            "author": {
                "name": commit_obj.author.name,
                "email": commit_obj.author.email,
                "date": datetime.fromtimestamp(commit_obj.author.time).isoformat()
            },
            "committer": {
                "name": commit_obj.committer.name,
                "email": commit_obj.committer.email,
                "date": datetime.fromtimestamp(commit_obj.committer.time).isoformat()
            },
            "date": datetime.fromtimestamp(commit_obj.commit_time).isoformat(),
            "parents": [str(parent) for parent in commit_obj.parent_ids]
        })
    
    return {
        "commits": commits,
        "pagination": {
            "page": page,
            "per_page": per_page
        }
    }


def get_diff(
    repo_path: str,
    base: str = None,
    head: str = None,
    path: str = None
) -> Dict[str, Any]:
    """
    获取代码差异
    
    Args:
        repo_path: 仓库物理路径
        base: 基准提交SHA，None 表示与空树对比
        head: 对比提交SHA（必填）
        path: 特定文件路径，None 表示所有文件
        
    Returns:
        dict: 包含差异信息的字典
        
    Raises:
        RepositoryNotFoundException: 仓库不存在
        PathNotFoundException: 提交不存在
        InvalidPathException: 无效的提交
    """
    if not head:
        raise InvalidPathException("Head commit is required")
    
    repo = _get_repo(repo_path)
    
    # 获取提交对象
    head_commit = _resolve_ref(repo, head)
    
    if base:
        base_commit = _resolve_ref(repo, base)
        diff = repo.diff(base_commit, head_commit)
    else:
        # 与空树对比
        diff = head_commit.tree.diff_to_tree()
    
    # 如果指定了路径，过滤差异
    if path:
        diff.find_similar()
    
    files = []
    for patch in diff:
        file_data = {
            "old_path": patch.delta.old_file.path,
            "new_path": patch.delta.new_file.path,
            "status": patch.delta.status_char(),
            "additions": patch.line_stats[1],
            "deletions": patch.line_stats[2]
        }

        # 添加 hunks 信息
        if patch.delta.status != pygit2.GIT_DELTA_DELETED:
            hunks = []
            for hunk in patch.hunks:
                hunk_data = {
                    "old_start": hunk.old_start,
                    "old_lines": hunk.old_lines,
                    "new_start": hunk.new_start,
                    "new_lines": hunk.new_lines,
                    "lines": []
                }
                for line in hunk.lines:
                    hunk_data["lines"].append({
                        "origin": line.origin,
                        "content": line.content
                    })
                hunks.append(hunk_data)
            file_data["hunks"] = hunks

        files.append(file_data)

    return {
        "files": files,
        "stats": {
            "files_changed": len(files),
            "additions": sum(f["additions"] for f in files),
            "deletions": sum(f["deletions"] for f in files)
        }
    }
