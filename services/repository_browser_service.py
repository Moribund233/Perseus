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

from client.utils.git_utils import repo_exists


class RepositoryBrowserError(Exception):
    """仓库浏览错误"""
    pass


def _get_repo(repo_path: str) -> pygit2.Repository:
    """
    获取仓库对象
    
    Args:
        repo_path: 仓库物理路径
        
    Returns:
        pygit2.Repository: 仓库对象
        
    Raises:
        RepositoryBrowserError: 仓库不存在或无法打开
    """
    if not repo_exists(repo_path):
        raise RepositoryBrowserError(f"Repository not found: {repo_path}")
    
    try:
        return pygit2.Repository(repo_path)
    except Exception as e:
        raise RepositoryBrowserError(f"Failed to open repository: {e}")


def _resolve_ref(repo: pygit2.Repository, ref: str) -> pygit2.Commit:
    """
    解析引用为提交对象
    
    Args:
        repo: 仓库对象
        ref: 分支名或提交SHA
        
    Returns:
        pygit2.Commit: 提交对象
        
    Raises:
        RepositoryBrowserError: 引用不存在
    """
    try:
        # 尝试直接解析为 OID
        try:
            oid = pygit2.Oid(hex=ref)
            commit = repo.get(oid)
            if commit:
                return commit
        except (ValueError, KeyError):
            pass
        
        # 尝试作为分支名解析
        try:
            branch_ref = repo.lookup_reference_dwim(ref)
            return repo.get(branch_ref.target)
        except KeyError:
            pass
        
        # 尝试作为完整引用名
        try:
            ref_obj = repo.lookup_reference(ref)
            return repo.get(ref_obj.target)
        except KeyError:
            pass
        
        raise RepositoryBrowserError(f"Ref not found: {ref}")
        
    except RepositoryBrowserError:
        raise
    except Exception as e:
        raise RepositoryBrowserError(f"Ref not found: {ref}")


def _get_entry_type(entry) -> str:
    """
    获取条目类型字符串
    
    Args:
        entry: 树条目对象
        
    Returns:
        str: "tree" 或 "blob"
    """
    # pygit2 中 entry.type 返回整数
    # entry.type == 3 -> repo.get() 返回 Blob（文件）
    # entry.type == 2 -> repo.get() 返回 Tree（目录）
    if entry.type == 3:
        return "blob"
    elif entry.type == 2:
        return "tree"
    return "unknown"


def _get_tree(repo: pygit2.Repository, commit: pygit2.Commit, path: str = "") -> pygit2.Tree:
    """
    获取指定路径的树对象
    
    Args:
        repo: 仓库对象
        commit: 提交对象
        path: 路径（空字符串表示根目录）
        
    Returns:
        pygit2.Tree: 树对象
        
    Raises:
        RepositoryBrowserError: 路径不存在
    """
    tree = commit.tree
    
    if not path:
        return tree
    
    # 解析路径
    parts = [p for p in path.split("/") if p]
    
    for part in parts:
        try:
            entry = tree[part]
            entry_type = _get_entry_type(entry)
            if entry_type != "tree":
                raise RepositoryBrowserError(f"'{path}' is not a directory")
            tree = repo.get(entry.id)
        except KeyError:
            raise RepositoryBrowserError(f"Path not found: {path}")
    
    return tree


def get_tree_entries(repo_path: str, ref: str = "HEAD", path: str = "") -> Dict[str, Any]:
    """
    获取文件树条目
    
    Args:
        repo_path: 仓库物理路径
        ref: 分支名或提交SHA，默认 HEAD
        path: 子目录路径，默认根目录
        
    Returns:
        dict: 文件树数据
        {
            "path": str,
            "ref": str,
            "entries": [
                {
                    "name": str,
                    "type": "tree" | "blob",
                    "mode": str,
                    "sha": str,
                    "size": int (仅 blob)
                }
            ]
        }
        
    Raises:
        RepositoryBrowserError: 仓库或路径不存在
    """
    repo = _get_repo(repo_path)
    
    try:
        commit = _resolve_ref(repo, ref)
        tree = _get_tree(repo, commit, path)
        
        entries = []
        for entry in tree:
            entry_type = _get_entry_type(entry)
            entry_data = {
                "name": entry.name,
                "type": entry_type,
                "mode": f"{entry.filemode:06o}",
                "sha": str(entry.id),
            }
            
            if entry_type == "blob":
                blob = repo.get(entry.id)
                if blob and isinstance(blob, pygit2.Blob):
                    entry_data["size"] = blob.size
                else:
                    entry_data["size"] = 0
            
            entries.append(entry_data)
        
        # 排序：目录在前，文件在后，按名称排序
        entries.sort(key=lambda e: (0 if e["type"] == "tree" else 1, e["name"]))
        
        return {
            "path": path,
            "ref": ref,
            "entries": entries
        }
        
    except RepositoryBrowserError:
        raise
    except Exception as e:
        raise RepositoryBrowserError(f"Failed to get tree entries: {e}")
    finally:
        repo.free()


def get_blob_content(repo_path: str, ref: str = "HEAD", path: str = "") -> Dict[str, Any]:
    """
    获取文件内容
    
    Args:
        repo_path: 仓库物理路径
        ref: 分支名或提交SHA，默认 HEAD
        path: 文件路径
        
    Returns:
        dict: 文件内容数据
        {
            "path": str,
            "ref": str,
            "sha": str,
            "size": int,
            "content": str,
            "encoding": str,
            "is_binary": bool
        }
        
    Raises:
        RepositoryBrowserError: 文件不存在或是目录
    """
    repo = _get_repo(repo_path)
    
    try:
        commit = _resolve_ref(repo, ref)
        
        # 获取目录和文件名
        dir_path = os.path.dirname(path)
        file_name = os.path.basename(path)
        
        # 规范化路径：如果 dir_path 是空字符串，使用根目录
        if not dir_path or dir_path == ".":
            dir_path = ""
        
        tree = _get_tree(repo, commit, dir_path)
        
        try:
            entry = tree[file_name]
        except KeyError:
            raise RepositoryBrowserError(f"File not found: {path}")
        
        entry_type = _get_entry_type(entry)
        if entry_type != "blob":
            raise RepositoryBrowserError(f"'{path}' is a directory, not a file")
        
        obj = repo.get(entry.id)
        if not obj or not isinstance(obj, pygit2.Blob):
            raise RepositoryBrowserError(f"'{path}' is not a valid file")
        
        blob = obj
        
        # 检测是否为二进制文件
        is_binary = False
        content = ""
        
        try:
            # 尝试作为文本解码
            content = blob.data.decode("utf-8")
            encoding = "utf-8"
        except UnicodeDecodeError:
            # 可能是二进制文件
            is_binary = True
            encoding = "binary"
            content = ""
        
        return {
            "path": path,
            "ref": ref,
            "sha": str(entry.id),
            "size": blob.size,
            "content": content,
            "encoding": encoding,
            "is_binary": is_binary
        }
        
    except RepositoryBrowserError:
        raise
    except Exception as e:
        raise RepositoryBrowserError(f"Failed to get blob content: {e}")
    finally:
        repo.free()


def get_commits(
    repo_path: str,
    ref: str = "HEAD",
    path: Optional[str] = None,
    page: int = 1,
    per_page: int = 30
) -> Dict[str, Any]:
    """
    获取提交历史
    
    Args:
        repo_path: 仓库物理路径
        ref: 分支名，默认 HEAD
        path: 特定文件的提交历史，None 表示所有提交
        page: 页码，默认 1
        per_page: 每页数量，默认 30
        
    Returns:
        dict: 提交历史数据
        {
            "commits": [
                {
                    "sha": str,
                    "message": str,
                    "author": {
                        "name": str,
                        "email": str
                    },
                    "date": str (ISO format),
                    "parents": [str]
                }
            ],
            "pagination": {
                "page": int,
                "per_page": int,
                "total": int
            }
        }
        
    Raises:
        RepositoryBrowserError: 分支不存在
    """
    repo = _get_repo(repo_path)
    
    try:
        commit = _resolve_ref(repo, ref)
        
        # 遍历提交历史
        commits = []
        walker = repo.walk(commit.id, pygit2.GIT_SORT_TIME)
        
        if path:
            # 简化处理：不过滤特定文件的提交
            # 实际实现需要使用 git log --follow path
            pass
        
        for commit_obj in walker:
            commits.append({
                "sha": str(commit_obj.id),
                "message": commit_obj.message.strip(),
                "author": {
                    "name": commit_obj.author.name,
                    "email": commit_obj.author.email
                },
                "date": datetime.fromtimestamp(commit_obj.author.time).isoformat(),
                "parents": [str(p) for p in commit_obj.parent_ids]
            })
        
        # 分页
        total = len(commits)
        start = (page - 1) * per_page
        end = start + per_page
        paginated_commits = commits[start:end]
        
        return {
            "commits": paginated_commits,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total
            }
        }
        
    except RepositoryBrowserError:
        raise
    except Exception as e:
        raise RepositoryBrowserError(f"Failed to get commits: {e}")
    finally:
        repo.free()


def get_diff(
    repo_path: str,
    base: Optional[str],
    head: str,
    path: Optional[str] = None
) -> Dict[str, Any]:
    """
    获取代码差异
    
    Args:
        repo_path: 仓库物理路径
        base: 基准提交，None 表示与空树对比
        head: 对比提交
        path: 特定文件的差异，None 表示所有文件
        
    Returns:
        dict: 差异数据
        {
            "files": [
                {
                    "path": str,
                    "status": str,
                    "additions": int,
                    "deletions": int,
                    "chunks": [...]
                }
            ]
        }
        
    Raises:
        RepositoryBrowserError: 提交不存在
    """
    repo = _get_repo(repo_path)
    
    try:
        # 解析提交
        head_commit = _resolve_ref(repo, head)
        
        if base:
            base_commit = _resolve_ref(repo, base)
            diff = repo.diff(base_commit, head_commit)
        else:
            # 与空树对比
            diff = head_commit.tree.diff_to_tree(swap=True)
        
        files = []
        for patch in diff:
            file_data = {
                "path": patch.delta.new_file.path or patch.delta.old_file.path,
                "status": patch.delta.status_char(),
                "additions": patch.line_stats[1],
                "deletions": patch.line_stats[2],
                "chunks": []
            }
            
            for hunk in patch.hunks:
                chunk = {
                    "old_start": hunk.old_start,
                    "old_lines": hunk.old_lines,
                    "new_start": hunk.new_start,
                    "new_lines": hunk.new_lines,
                    "lines": []
                }
                
                for line in hunk.lines:
                    line_type = "context"
                    if line.origin == "+":
                        line_type = "addition"
                    elif line.origin == "-":
                        line_type = "deletion"
                    
                    chunk["lines"].append({
                        "type": line_type,
                        "content": line.content.rstrip("\n\r"),
                        "old_lineno": line.old_lineno if line.old_lineno != -1 else None,
                        "new_lineno": line.new_lineno if line.new_lineno != -1 else None
                    })
                
                file_data["chunks"].append(chunk)
            
            files.append(file_data)
        
        return {"files": files}
        
    except RepositoryBrowserError:
        raise
    except Exception as e:
        raise RepositoryBrowserError(f"Failed to get diff: {e}")
    finally:
        repo.free()
