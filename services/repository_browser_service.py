"""
仓库代码浏览服务层

处理与代码浏览相关的业务逻辑：
- 文件树浏览
- 文件内容查看
- 提交历史
- 代码对比
"""
import os
import re
from typing import List, Dict, Any, Optional, cast
from datetime import datetime

import pygit2

from utils.git_utils import repo_exists
from core.exception import (
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
        raise RepositoryNotFoundException(detail=f"Repository not found: {repo_path}", error_code="repository_not_found")

    try:
        return pygit2.Repository(repo_path)
    except Exception as e:
        raise RepositoryNotFoundException(detail=f"Failed to open repository: {e}", error_code="repository_open_failed")


def _resolve_ref(repo: pygit2.Repository, ref: str) -> Optional[pygit2.Commit]:
    """
    解析引用为提交对象

    Args:
        repo: 仓库对象
        ref: 引用名称（分支名、标签名或提交SHA）

    Returns:
        pygit2.Commit: 提交对象，如果仓库为空则返回 None

    Raises:
        PathNotFoundException: 引用不存在（非空仓库）
    """
    try:
        # 尝试直接解析为提交
        return repo.revparse_single(ref).peel(pygit2.Commit)
    except (KeyError, ValueError):
        # 尝试添加 refs/heads/ 前缀
        try:
            return repo.revparse_single(f"refs/heads/{ref}").peel(pygit2.Commit)
        except (KeyError, ValueError):
            # 检查仓库是否为空（没有提交）
            # 注意: HEAD 指向 master 以外的 unborn 分支时 libgit2 的
            # is_empty 会误报 False, head_is_unborn 才是可靠判据
            if repo.head_is_unborn or repo.is_empty:
                return None
            raise PathNotFoundException(detail=f"Ref not found: {ref}", error_code="branch_ref_not_found")


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
            return cast(pygit2.Tree, repo[entry.id])
        else:
            raise InvalidPathException(detail=f"'{path}' is not a directory", error_code="path_not_directory")
    except KeyError:
        raise PathNotFoundException(detail=f"Path not found: {path}", error_code="path_not_found")


def _get_file_last_commit(repo: pygit2.Repository, commit: pygit2.Commit, path: str) -> Dict[str, Any] | None:
    """
    获取某文件的最近提交信息（非空仓库）

    仅对文件（blob）有意义；目录返回 None。
    通过 `simplify_first_parent()` 过滤走树历史，只考虑修改过该路径的提交，
    按时间排序取最新的一个，避免遍历整条历史。

    Args:
        repo: 仓库对象
        commit: 起始提交对象（HEAD）
        path: 文件路径

    Returns:
        dict: {"hash", "message", "author", "date"} 或 None（无可定位提交）
    """
    try:
        entry = commit.tree[path]
        if entry.type != pygit2.GIT_OBJECT_BLOB:
            return None
    except KeyError:
        return None

    walker = repo.walk(commit.id, pygit2.enums.SortMode.TIME)
    walker.simplify_first_parent()
    for c in walker:
        return {
            "hash": str(c.id),
            "message": c.message,
            "author": c.author.name,
            "date": datetime.fromtimestamp(c.author.time).isoformat(),
        }
    return None


async def get_tree_entries(
    repo_path: str,
    ref: str = "HEAD",
    path: str = "",
    last_commit: bool = False
) -> Dict[str, Any]:
    """
    获取文件树条目

    Args:
        repo_path: 仓库物理路径
        ref: 分支名或提交SHA，默认 HEAD
        path: 子目录路径，默认根目录
        last_commit: 是否附带每个文件最近提交信息（仅对文件），默认 False

    Returns:
        dict: 包含路径列表和条目列表的字典

    Raises:
        RepositoryNotFoundException: 仓库不存在
        PathNotFoundException: 引用或路径不存在
        InvalidPathException: 路径不是目录
    """
    repo = _get_repo(repo_path)
    commit = _resolve_ref(repo, ref)

    # 空仓库处理
    if commit is None:
        return {
            "path": path,
            "ref": ref,
            "entries": [],
            "is_empty": True
        }

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
        entry_data: Dict[str, Any] = {
            "name": entry.name,
            "type": "tree" if entry.type == pygit2.GIT_OBJECT_TREE else "blob",
            "path": f"{path}/{entry.name}" if path else entry.name,
            "sha": str(entry.id),
            "mode": entry.filemode
        }

        # 如果是文件，添加大小信息
        if entry.type == pygit2.GIT_OBJECT_BLOB:
            blob = cast(pygit2.Blob, repo[entry.id])
            entry_data["size"] = blob.size
            if last_commit:
                full_path: str = f"{path}/{entry.name}" if path else str(entry.name)
                entry_data["last_commit"] = _get_file_last_commit(
                    repo, commit, full_path
                )

        entries.append(entry_data)

    # 按类型排序（目录在前）和名称排序
    entries.sort(key=lambda x: (0 if x["type"] == "tree" else 1, x["name"]))

    return {
        "path": path,
        "ref": ref,
        "entries": entries
    }


async def get_blob_content(
    repo_path: str,
    ref: str = "HEAD",
    path: str | None = None
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
        raise InvalidPathException(detail="Path is required", error_code="path_required")

    repo = _get_repo(repo_path)
    commit = _resolve_ref(repo, ref)

    if commit is None:
        return {
            "name": os.path.basename(path) if path else "",
            "path": path,
            "sha": "",
            "ref": ref,
            "content": "",
            "size": 0,
            "encoding": "utf-8",
            "is_binary": False,
            "language": None,
            "diff_stats": None,
            "is_empty": True
        }

    try:
        entry = commit.tree[path]
    except KeyError:
        raise PathNotFoundException(detail=f"File not found: {path}", error_code="file_not_found")

    if entry.type == pygit2.GIT_OBJECT_TREE:
        raise InvalidPathException(detail=f"'{path}' is a directory, not a file", error_code="path_is_directory")

    if entry.type != pygit2.GIT_OBJECT_BLOB:
        raise InvalidPathException(detail=f"'{path}' is not a valid file", error_code="file_invalid")
    
    blob = cast(pygit2.Blob, repo[entry.id])
    
    # 尝试解码为文本
    try:
        content = blob.data.decode('utf-8')
        is_binary = False
    except UnicodeDecodeError:
        content = blob.data.hex()
        is_binary = True
    
    # 检测文件语言
    language = detect_file_language(path)
    if is_binary:
        language = "binary"

    return {
        "name": os.path.basename(path),
        "path": path,
        "sha": str(entry.id),
        "ref": ref,
        "content": content,
        "size": blob.size,
        "encoding": "utf-8" if not is_binary else "hex",
        "is_binary": is_binary,
        "language": language,
        "diff_stats": None
    }


async def get_commits(
    repo_path: str,
    ref: str = "HEAD",
    path: str | None = None,
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

    # 空仓库处理
    if commit is None:
        return {
            "commits": [],
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": 0
            },
            "is_empty": True
        }

    commits = []
    walker = repo.walk(commit.id, pygit2.enums.SortMode.TIME)
    
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


def _serialize_diff(diff: pygit2.Diff) -> Dict[str, Any]:
    """
    将 pygit2.Diff 序列化为前端可消费的结构（供 diff / compare 复用）

    Args:
        diff: pygit2 差异对象

    Returns:
        dict: {"files": [...], "stats": {...}}
    """
    files = []
    for patch in diff:
        if patch is None:
            continue
        file_data: Dict[str, Any] = {
            "old_path": patch.delta.old_file.path,
            "new_path": patch.delta.new_file.path,
            "status": patch.delta.status_char(),
            "additions": patch.line_stats[1],
            "deletions": patch.line_stats[2]
        }

        # 添加 hunks 信息（删除的文件无新内容）
        if patch.delta.status != pygit2.GIT_DELTA_DELETED:
            hunks = []
            for hunk in patch.hunks:
                hunk_data: Dict[str, Any] = {
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


async def get_diff(
    repo_path: str,
    base: str | None = None,
    head: str | None = None,
    path: str | None = None
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
        raise InvalidPathException(detail="Head commit is required", error_code="head_commit_required")

    repo = _get_repo(repo_path)

    # 获取提交对象
    head_commit = _resolve_ref(repo, head)

    # 检查空仓库
    if head_commit is None:
        raise PathNotFoundException(detail=f"Ref not found: {head} (empty repository)", error_code="branch_ref_not_found")

    if base:
        base_commit = _resolve_ref(repo, base)
        # 检查 base 提交是否存在
        if base_commit is None:
            raise PathNotFoundException(detail=f"Base ref not found: {base}", error_code="base_ref_not_found")
        # 使用树对象进行比较，避免在裸仓库中使用repo.diff
        diff = base_commit.tree.diff_to_tree(head_commit.tree)
    else:
        # 与空树对比 - 使用空树对象
        # 创建一个空的树
        empty_tree_builder = repo.TreeBuilder()
        empty_tree_id = empty_tree_builder.write()
        empty_tree = cast(pygit2.Tree, repo[empty_tree_id])
        diff = empty_tree.diff_to_tree(head_commit.tree)
    
    # 如果指定了路径，过滤差异
    if path:
        diff.find_similar()

    return _serialize_diff(diff)


async def get_blame(
    repo_path: str,
    ref: str = "HEAD",
    path: str | None = None
) -> Dict[str, Any]:
    """
    获取文件的行级追溯（Blame）

    Args:
        repo_path: 仓库物理路径
        ref: 分支名或提交SHA，默认 HEAD
        path: 文件路径（必填）

    Returns:
        dict: {"path", "ref", "hunks": [...]}；空仓库返回 is_empty=True

    Raises:
        RepositoryNotFoundException: 仓库不存在
        PathNotFoundException: 引用或文件不存在
        InvalidPathException: 路径是目录或 blame 失败
    """
    if not path:
        raise InvalidPathException(detail="Path is required", error_code="path_required")

    repo = _get_repo(repo_path)
    commit = _resolve_ref(repo, ref)

    if commit is None:
        return {
            "path": path,
            "ref": ref,
            "hunks": [],
            "is_empty": True
        }

    try:
        entry = commit.tree[path]
    except KeyError:
        raise PathNotFoundException(detail=f"File not found: {path}", error_code="file_not_found")

    if entry.type == pygit2.GIT_OBJECT_TREE:
        raise InvalidPathException(detail=f"'{path}' is a directory, not a file", error_code="path_is_directory")
    if entry.type != pygit2.GIT_OBJECT_BLOB:
        raise InvalidPathException(detail=f"'{path}' is not a valid file", error_code="file_invalid")

    try:
        blame = repo.blame(path, newest_commit=commit.id)
    except Exception as e:
        raise InvalidPathException(detail=f"Failed to blame '{path}': {e}", error_code="blame_failed")

    hunks = []
    for hunk in blame:
        hunk_commit = repo[hunk.final_commit_id]
        hunks.append({
            "final_start_line_number": hunk.final_start_line_number,
            "lines_in_hunk": hunk.lines_in_hunk,
            "orig_start_line_number": hunk.orig_start_line_number,
            "orig_commit_id": str(hunk.orig_commit_id),
            "final_commit_id": str(hunk.final_commit_id),
            "orig_path": hunk.orig_path,
            "boundary": bool(hunk.boundary),
            "commit": {
                "sha": str(hunk_commit.id),
                "summary": hunk_commit.message.splitlines()[0] if hunk_commit.message else "",
                "message": hunk_commit.message,
                "author": {
                    "name": hunk_commit.author.name,
                    "email": hunk_commit.author.email,
                    "date": datetime.fromtimestamp(hunk_commit.author.time).isoformat()
                }
            }
        })

    return {
        "path": path,
        "ref": ref,
        "hunks": hunks
    }


def _commit_to_node(repo: pygit2.Repository, commit: pygit2.Commit, labels: list | None = None) -> Dict[str, Any]:
    """把提交对象序列化为提交图节点"""
    return {
        "sha": str(commit.id),
        "parents": [str(parent) for parent in commit.parent_ids],
        "summary": commit.message.splitlines()[0] if commit.message else "",
        "message": commit.message,
        "author": {
            "name": commit.author.name,
            "email": commit.author.email,
            "date": datetime.fromtimestamp(commit.author.time).isoformat()
        },
        "committer": {
            "name": commit.committer.name,
            "email": commit.committer.email,
            "date": datetime.fromtimestamp(commit.committer.time).isoformat()
        },
        "date": datetime.fromtimestamp(commit.commit_time).isoformat(),
        "labels": labels or [],
        "is_merge": len(commit.parent_ids) > 1
    }


def _collect_commit_labels(repo: pygit2.Repository) -> Dict[str, List[str]]:
    """
    收集指向各提交的引用标签（HEAD / 分支 / 标签）

    Returns:
        dict: {commit_sha: [label, ...]}
    """
    labels: Dict[str, List[str]] = {}

    if not repo.head_is_unborn:
        try:
            head_sha = str(repo.head.peel(pygit2.Commit).id)
            labels.setdefault(head_sha, []).append("HEAD")
        except Exception:
            pass

    for refname in repo.listall_references():
        try:
            target = repo.lookup_reference(refname).peel(pygit2.Commit)
        except Exception:
            continue
        sha = str(target.id)
        if refname.startswith("refs/heads/"):
            labels.setdefault(sha, []).append(refname[len("refs/heads/"):])
        elif refname.startswith("refs/tags/"):
            labels.setdefault(sha, []).append(f"tag: {refname[len('refs/tags/'):]}")

    return labels


async def get_commit_graph(
    repo_path: str,
    ref: str = "HEAD",
    limit: int = 100
) -> Dict[str, Any]:
    """
    获取提交图（拓扑序节点 + 父边 + 引用标签），供前端渲染分支网络

    Args:
        repo_path: 仓库物理路径
        ref: 起始引用，默认 HEAD
        limit: 最大节点数，默认 100

    Returns:
        dict: {"ref", "commits": [...], "is_empty"?}

    Raises:
        RepositoryNotFoundException: 仓库不存在
        PathNotFoundException: 引用不存在
    """
    repo = _get_repo(repo_path)
    commit = _resolve_ref(repo, ref)

    if commit is None:
        return {
            "ref": ref,
            "commits": [],
            "is_empty": True
        }

    labels = _collect_commit_labels(repo)
    walker = repo.walk(commit.id, pygit2.enums.SortMode.TOPOLOGICAL)

    commits = []
    for i, commit_obj in enumerate(walker):
        if i >= limit:
            break
        commits.append(_commit_to_node(repo, commit_obj, labels.get(str(commit_obj.id), [])))

    return {
        "ref": ref,
        "commits": commits
    }


async def compare(
    repo_path: str,
    base: str,
    head: str,
    path: str | None = None
) -> Dict[str, Any]:
    """
    对比两个引用/提交（GitHub 风格 base...head）

    Args:
        repo_path: 仓库物理路径
        base: 基准引用（分支名/标签/提交SHA）
        head: 目标引用
        path: 特定文件路径，None 表示所有文件

    Returns:
        dict: {"base", "head", "merge_base", "ahead_by", "commits", "files", "stats"}

    Raises:
        RepositoryNotFoundException: 仓库不存在
        PathNotFoundException: 引用不存在
    """
    repo = _get_repo(repo_path)
    base_commit = _resolve_ref(repo, base)
    head_commit = _resolve_ref(repo, head)

    if base_commit is None:
        raise PathNotFoundException(detail=f"Base ref not found: {base}", error_code="base_ref_not_found")
    if head_commit is None:
        raise PathNotFoundException(detail=f"Ref not found: {head}", error_code="branch_ref_not_found")

    try:
        merge_base_id = repo.merge_base(base_commit.id, head_commit.id)
    except Exception:
        merge_base_id = None

    diff = base_commit.tree.diff_to_tree(head_commit.tree)
    if path:
        diff.find_similar()
    result = _serialize_diff(diff)

    labels = _collect_commit_labels(repo)
    walker = repo.walk(head_commit.id, pygit2.enums.SortMode.TIME)
    walker.hide(base_commit.id)

    commits = []
    for commit_obj in walker:
        commits.append(_commit_to_node(repo, commit_obj, labels.get(str(commit_obj.id), [])))

    result.update({
        "base": str(base_commit.id),
        "head": str(head_commit.id),
        "merge_base": str(merge_base_id) if merge_base_id is not None else None,
        "ahead_by": len(commits),
        "commits": commits
    })
    return result


# ============ F-023: 文件语言检测 ============

# 文件扩展名到语言映射
LANGUAGE_MAP = {
    # Python
    ".py": "python",
    ".pyw": "python",
    ".pyi": "python",
    # JavaScript
    ".js": "javascript",
    ".mjs": "javascript",
    ".jsx": "javascript",
    # TypeScript
    ".ts": "typescript",
    ".tsx": "typescript",
    # HTML
    ".html": "html",
    ".htm": "html",
    ".xhtml": "html",
    # CSS
    ".css": "css",
    ".scss": "scss",
    ".sass": "sass",
    ".less": "less",
    # Go
    ".go": "go",
    # Rust
    ".rs": "rust",
    # Java
    ".java": "java",
    # JSON
    ".json": "json",
    ".jsonc": "json",
    # Markdown
    ".md": "markdown",
    ".markdown": "markdown",
    ".mdown": "markdown",
    ".mkd": "markdown",
    # YAML
    ".yml": "yaml",
    ".yaml": "yaml",
    # XML
    ".xml": "xml",
    # Shell
    ".sh": "bash",
    ".bash": "bash",
    ".zsh": "bash",
    # PowerShell
    ".ps1": "powershell",
    ".psm1": "powershell",
    # C/C++
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".hpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    # C#
    ".cs": "csharp",
    # Ruby
    ".rb": "ruby",
    # PHP
    ".php": "php",
    # Swift
    ".swift": "swift",
    # Kotlin
    ".kt": "kotlin",
    ".kts": "kotlin",
    # Scala
    ".scala": "scala",
    # R
    ".r": "r",
    ".R": "r",
    # SQL
    ".sql": "sql",
    # Dockerfile
    ".dockerfile": "dockerfile",
    # Makefile (无扩展名，特殊处理)
    # Vue
    ".vue": "vue",
    # Svelte
    ".svelte": "svelte",
    # GraphQL
    ".graphql": "graphql",
    ".gql": "graphql",
    # TOML
    ".toml": "toml",
    # INI/Config
    ".ini": "ini",
    ".cfg": "ini",
    ".conf": "ini",
    # Lua
    ".lua": "lua",
    # Perl
    ".pl": "perl",
    ".pm": "perl",
    # Haskell
    ".hs": "haskell",
    # Erlang
    ".erl": "erlang",
    # Elixir
    ".ex": "elixir",
    ".exs": "elixir",
    # Dart
    ".dart": "dart",
    # Julia
    ".jl": "julia",
    # Clojure
    ".clj": "clojure",
    ".cljs": "clojure",
    # F#
    ".fs": "fsharp",
    ".fsx": "fsharp",
    # OCaml
    ".ml": "ocaml",
    ".mli": "ocaml",
    # Groovy
    ".groovy": "groovy",
    # Objective-C
    ".m": "objectivec",
    ".mm": "objectivec",
    # Assembly
    ".asm": "asm",
    ".s": "asm",
    # Vim
    ".vim": "vim",
    # Emacs Lisp
    ".el": "elisp",
    ".elc": "elisp",
}

# 特殊文件名到语言映射
SPECIAL_FILENAMES = {
    "dockerfile": "dockerfile",
    "dockerfile.dev": "dockerfile",
    "dockerfile.prod": "dockerfile",
    "makefile": "makefile",
    "gnumakefile": "makefile",
    "cmakelists.txt": "cmake",
    "readme": "text",
    "license": "text",
    "copying": "text",
    "authors": "text",
    "contributors": "text",
    "changelog": "text",
    "changes": "text",
    "news": "text",
    "todo": "text",
    ".gitignore": "gitignore",
    ".gitattributes": "gitattributes",
    ".dockerignore": "dockerignore",
    ".editorconfig": "editorconfig",
    ".eslintignore": "gitignore",
    ".prettierignore": "gitignore",
}

# 二进制文件扩展名
BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".webp", ".svg",
    ".mp3", ".mp4", ".wav", ".ogg", ".flac", ".aac",
    ".avi", ".mov", ".wmv", ".flv", ".mkv",
    ".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".exe", ".dll", ".so", ".dylib", ".bin",
    ".ttf", ".otf", ".woff", ".woff2", ".eot",
    ".sqlite", ".db", ".mdb",
    ".class", ".jar", ".war", ".ear",
    ".o", ".obj", ".a", ".lib",
    ".pyc", ".pyo",
    ".min.js", ".min.css",
}


def detect_file_language(filename: str) -> str:
    """
    检测文件语言类型（用于语法高亮）

    Args:
        filename: 文件名

    Returns:
        str: 语言标识符，如 "python", "javascript" 等
             未知类型返回 "text" 或 "binary"
    """
    if not filename:
        return "text"

    # 转换为小写进行匹配
    filename_lower = filename.lower()

    # 检查是否是二进制文件
    for ext in BINARY_EXTENSIONS:
        if filename_lower.endswith(ext):
            return "binary"

    # 检查特殊文件名（无扩展名或完整匹配）
    basename = os.path.basename(filename_lower)
    if basename in SPECIAL_FILENAMES:
        return SPECIAL_FILENAMES[basename]

    # 移除可能的后缀（如 .min.js）
    for suffix in [".min"]:
        if basename.endswith(suffix):
            basename = basename[:-len(suffix)]

    # 检查扩展名
    _, ext = os.path.splitext(basename)
    if ext in LANGUAGE_MAP:
        return LANGUAGE_MAP[ext]

    # 无扩展名文件
    if not ext:
        return "text"

    return "text"


# ============ F-024: README 内容获取 ============

async def get_readme_content(
    repo_path: str,
    ref: str = "HEAD"
) -> Dict[str, Any]:
    """
    获取 README 文件内容

    自动查找常见的 README 文件名：README.md, README.rst, README.txt, README

    Args:
        repo_path: 仓库物理路径
        ref: 分支名或提交SHA，默认 HEAD

    Returns:
        dict: 包含 README 信息的字典
        {
            "found": bool,
            "filename": str or None,
            "content": str or None,
            "language": str,
            "encoding": str
        }
    """
    repo = _get_repo(repo_path)
    commit = _resolve_ref(repo, ref)

    # 空仓库处理
    if commit is None:
        return {
            "found": False,
            "filename": None,
            "content": None,
            "language": "text",
            "encoding": "utf-8"
        }

    # 常见的 README 文件名（按优先级排序）
    readme_names = [
        "README.md", "readme.md", "Readme.md",
        "README.rst", "readme.rst",
        "README.txt", "readme.txt",
        "README", "readme", "Readme",
        "README.markdown", "readme.markdown",
        "README.mdown", "readme.mdown",
    ]

    tree = commit.tree

    for name in readme_names:
        try:
            entry = tree[name]
            if entry.type == pygit2.GIT_OBJECT_BLOB:
                blob = cast(pygit2.Blob, repo[entry.id])

                # 尝试解码为文本
                try:
                    content = blob.data.decode('utf-8')
                    encoding = "utf-8"
                except UnicodeDecodeError:
                    content = blob.data.hex()
                    encoding = "hex"

                return {
                    "found": True,
                    "filename": name,
                    "content": content,
                    "language": detect_file_language(name),
                    "encoding": encoding
                }
        except KeyError:
            continue

    # 未找到 README
    return {
        "found": False,
        "filename": None,
        "content": None,
        "language": "text",
        "encoding": "utf-8"
    }


# ============ F-024: 文件符号提取 ============

# 各语言符号提取正则（作用于去除首尾空白后的行）
# 每项: (编译后的正则, 符号类型)；按顺序匹配，命中即止。
# 覆盖语言与 LANGUAGE_MAP 的标识符一致；未收录语言返回空符号表。
_SYMBOL_PATTERNS: Dict[str, List[tuple]] = {
    "python": [
        (re.compile(r"^async\s+def\s+(\w+)\s*\("), "function"),
        (re.compile(r"^def\s+(\w+)\s*\("), "function"),
        (re.compile(r"^class\s+(\w+)"), "class"),
    ],
    "javascript": [
        (re.compile(r"^(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s+(\w+)\s*\("), "function"),
        (re.compile(r"^(?:export\s+)?(?:default\s+)?class\s+(\w+)"), "class"),
        (re.compile(r"^(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?(?:\([^)]*\)|\w+)\s*=>"), "function"),
        (re.compile(r"^(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?function\b"), "function"),
    ],
    "typescript": [
        (re.compile(r"^(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s+(\w+)\s*[<(]"), "function"),
        (re.compile(r"^(?:export\s+)?(?:default\s+)?(?:abstract\s+)?class\s+(\w+)"), "class"),
        (re.compile(r"^(?:export\s+)?interface\s+(\w+)"), "interface"),
        (re.compile(r"^(?:export\s+)?type\s+(\w+)\s*[<=]"), "type"),
        (re.compile(r"^(?:export\s+)?enum\s+(\w+)"), "enum"),
        (re.compile(r"^(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?(?:\([^)]*\)|\w+)\s*=>"), "function"),
    ],
    "go": [
        (re.compile(r"^func\s+(?:\([^)]*\)\s*)?(\w+)\s*\("), "function"),
        (re.compile(r"^type\s+(\w+)\s+struct\b"), "class"),
        (re.compile(r"^type\s+(\w+)\s+interface\b"), "interface"),
    ],
    "rust": [
        (re.compile(r"^(?:pub(?:\([^)]*\))?\s+)?(?:async\s+)?(?:unsafe\s+)?fn\s+(\w+)"), "function"),
        (re.compile(r"^(?:pub(?:\([^)]*\))?\s+)?struct\s+(\w+)"), "class"),
        (re.compile(r"^(?:pub(?:\([^)]*\))?\s+)?enum\s+(\w+)"), "enum"),
        (re.compile(r"^(?:pub(?:\([^)]*\))?\s+)?trait\s+(\w+)"), "interface"),
        (re.compile(r"^impl(?:<[^>]*>)?\s+(\w+)"), "class"),
    ],
    "java": [
        (re.compile(r"^(?:public\s+|private\s+|protected\s+)?(?:static\s+)?(?:final\s+)?(?:abstract\s+)?class\s+(\w+)"), "class"),
        (re.compile(r"^(?:public\s+|private\s+|protected\s+)?(?:abstract\s+)?interface\s+(\w+)"), "interface"),
        (re.compile(r"^(?:public\s+|private\s+|protected\s+)?enum\s+(\w+)"), "enum"),
        (re.compile(r"^(?:public|private|protected)\s+(?:static\s+)?(?:final\s+)?[\w<>\[\],.\s]+\s+(\w+)\s*\([^;]*\)\s*\{"), "function"),
    ],
    "c": [
        (re.compile(r"^(?:typedef\s+)?(?:struct|union)\s+(\w+)"), "class"),
        (re.compile(r"^(?:typedef\s+)?enum\s+(\w+)"), "enum"),
        (re.compile(r"^(?:static\s+)?(?:inline\s+)?[\w\*]+\s+(\w+)\s*\([^;]*\)\s*\{"), "function"),
    ],
    "cpp": [
        (re.compile(r"^(?:template\s*<[^>]*>\s*)?(?:class|struct)\s+(\w+)"), "class"),
        (re.compile(r"^namespace\s+(\w+)"), "namespace"),
        (re.compile(r"^(?:typedef\s+)?enum(?:\s+class)?\s+(\w+)"), "enum"),
        (re.compile(r"^(?:[\w:<>,\*&\s]+)\s+(\w+)\s*\([^;]*\)\s*(?:const\s*)?\{" ), "function"),
    ],
    "csharp": [
        (re.compile(r"^(?:public\s+|private\s+|protected\s+|internal\s+)?(?:static\s+|abstract\s+|sealed\s+|partial\s+)*(?:class|struct)\s+(\w+)"), "class"),
        (re.compile(r"^(?:public\s+|private\s+|protected\s+|internal\s+)?interface\s+(\w+)"), "interface"),
        (re.compile(r"^(?:public\s+|private\s+|protected\s+|internal\s+)?enum\s+(\w+)"), "enum"),
        (re.compile(r"^(?:public|private|protected|internal)\s+(?:static\s+|virtual\s+|override\s+|async\s+)*[\w<>\[\],.?]+\s+(\w+)\s*\([^;]*\)\s*\{"), "function"),
    ],
    "ruby": [
        (re.compile(r"^def\s+(\w+)"), "function"),
        (re.compile(r"^class\s+(\w+)"), "class"),
        (re.compile(r"^module\s+(\w+)"), "class"),
    ],
    "php": [
        (re.compile(r"^(?:public\s+|private\s+|protected\s+)?(?:static\s+)?function\s+(\w+)"), "function"),
        (re.compile(r"^(?:final\s+|abstract\s+)?class\s+(\w+)"), "class"),
        (re.compile(r"^interface\s+(\w+)"), "interface"),
        (re.compile(r"^trait\s+(\w+)"), "class"),
    ],
    "swift": [
        (re.compile(r"^(?:public\s+|private\s+|internal\s+|open\s+|fileprivate\s+)?(?:static\s+|class\s+)?func\s+(\w+)"), "function"),
        (re.compile(r"^(?:public\s+|private\s+|internal\s+|open\s+)?(?:final\s+)?(?:class|struct)\s+(\w+)"), "class"),
        (re.compile(r"^(?:public\s+|private\s+|internal\s+)?enum\s+(\w+)"), "enum"),
        (re.compile(r"^(?:public\s+|private\s+|internal\s+)?protocol\s+(\w+)"), "interface"),
    ],
    "kotlin": [
        (re.compile(r"^(?:public\s+|private\s+|internal\s+|protected\s+)?(?:suspend\s+)?fun\s+(\w+)"), "function"),
        (re.compile(r"^(?:public\s+|private\s+|internal\s+|open\s+|data\s+|sealed\s+|abstract\s+)*(?:class|object)\s+(\w+)"), "class"),
        (re.compile(r"^interface\s+(\w+)"), "interface"),
        (re.compile(r"^enum\s+class\s+(\w+)"), "enum"),
    ],
    "scala": [
        (re.compile(r"^(?:private\s+|protected\s+|override\s+|final\s+)?def\s+(\w+)"), "function"),
        (re.compile(r"^(?:private\s+|protected\s+|final\s+|abstract\s+|sealed\s+)?(?:case\s+)?(?:class|object)\s+(\w+)"), "class"),
        (re.compile(r"^trait\s+(\w+)"), "interface"),
    ],
}

# 解析时需跳过的注释行前缀
_COMMENT_PREFIXES = ("#", "//", "/*", "*", "*/")


def _extract_symbols(content: str, language: str) -> List[Dict[str, Any]]:
    """
    从源码内容中提取符号（函数/类/接口等）。

    基于各语言正则（见 `_SYMBOL_PATTERNS`）做轻量级提取；未收录语言返回空列表。

    Args:
        content: 文件文本内容
        language: 语言标识符（同 LANGUAGE_MAP 的值）

    Returns:
        list: [{"name": str, "type": str, "line": int}, ...]
    """
    patterns = _SYMBOL_PATTERNS.get(language)
    if not patterns:
        return []

    symbols: List[Dict[str, Any]] = []
    for line_no, line in enumerate(content.split("\n"), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith(_COMMENT_PREFIXES):
            continue
        for pattern, symbol_type in patterns:
            match = pattern.match(stripped)
            if match:
                symbols.append({
                    "name": match.group(1),
                    "type": symbol_type,
                    "line": line_no,
                })
                break
    return symbols


async def get_file_symbols(
    repo_path: str,
    ref: str = "HEAD",
    path: str | None = None
) -> Dict[str, Any]:
    """
    获取文件中的符号（函数、类、变量等）

    目前支持：Python（简单正则提取）
    未来可扩展：Tree-sitter 等更精确的解析

    Args:
        repo_path: 仓库物理路径
        ref: 分支名或提交SHA，默认 HEAD
        path: 文件路径（必填）

    Returns:
        dict: 包含符号列表的字典
        {
            "path": str,
            "language": str,
            "symbols": [
                {
                    "name": str,
                    "type": str,  # "function", "class", "variable"
                    "line": int
                }
            ]
        }

    Raises:
        PathNotFoundException: 文件不存在
        InvalidPathException: 路径是目录或无效
    """
    if not path:
        raise InvalidPathException(detail="Path is required", error_code="path_required")

    # 获取文件内容
    blob_info = await get_blob_content(repo_path, ref=ref, path=path)

    language = blob_info.get("language", "text")
    content = blob_info.get("content", "")
    is_binary = blob_info.get("is_binary", False)

    # 二进制文件不解析
    if is_binary or language == "binary":
        return {
            "path": path,
            "language": "binary",
            "symbols": []
        }

    # 多语言符号提取（基于正则，见 _extract_symbols / _SYMBOL_PATTERNS）
    symbols = _extract_symbols(content, language)

    return {
        "path": path,
        "language": language,
        "symbols": symbols
    }


async def commit_file(
    repo_path: str,
    branch: str,
    file_path: str,
    content: str,
    author_name: str,
    author_email: str,
    message: str,
) -> Dict[str, Any]:
    """
    在指定分支创建/更新文件并提交

    同步 pygit2 操作放线程池执行, 避免阻塞事件循环

    Raises:
        RepositoryNotFoundException: 仓库不存在
        ValidationException: 路径或分支名非法
    """
    if not repo_exists(repo_path):
        raise RepositoryNotFoundException(detail=f"Repository not found: {repo_path}", error_code="repository_not_found")

    import asyncio
    from utils import git_utils

    return await asyncio.to_thread(
        git_utils.commit_file_changes,
        repo_path,
        branch,
        file_path,
        content,
        author_name,
        author_email,
        message,
    )


async def remove_file(
    repo_path: str,
    branch: str,
    file_path: str,
    author_name: str,
    author_email: str,
    message: str,
) -> Dict[str, Any]:
    """
    在指定分支删除文件并提交
    """
    if not repo_exists(repo_path):
        raise RepositoryNotFoundException(detail=f"Repository not found: {repo_path}", error_code="repository_not_found")

    import asyncio
    from utils import git_utils

    return await asyncio.to_thread(
        git_utils.delete_file_changes,
        repo_path,
        branch,
        file_path,
        author_name,
        author_email,
        message,
    )


async def move_file(
    repo_path: str,
    branch: str,
    source_path: str,
    dest_path: str,
    author_name: str,
    author_email: str,
    message: str,
) -> Dict[str, Any]:
    """
    在指定分支重命名/移动文件并提交 (单次提交内 copy+delete)

    Raises:
        RepositoryNotFoundException: 仓库不存在
        NotFoundException: 分支或源文件不存在
        ValidationException: 路径非法、源为目录或源/目标相同
        ConflictException: 目标路径已存在
    """
    if not repo_exists(repo_path):
        raise RepositoryNotFoundException(detail=f"Repository not found: {repo_path}", error_code="repository_not_found")

    import asyncio
    from utils import git_utils

    return await asyncio.to_thread(
        git_utils.move_file_changes,
        repo_path,
        branch,
        source_path,
        dest_path,
        author_name,
        author_email,
        message,
    )
