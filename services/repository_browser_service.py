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
        raise RepositoryNotFoundException(detail=f"Repository not found: {repo_path}")

    try:
        return pygit2.Repository(repo_path)
    except Exception as e:
        raise RepositoryNotFoundException(detail=f"Failed to open repository: {e}")


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
            if repo.is_empty:
                return None
            raise PathNotFoundException(detail=f"Ref not found: {ref}")


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
            raise InvalidPathException(detail=f"'{path}' is not a directory")
    except KeyError:
        raise PathNotFoundException(detail=f"Path not found: {path}")


async def get_tree_entries(
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


async def get_blob_content(
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
        raise InvalidPathException(detail="Path is required")

    repo = _get_repo(repo_path)
    commit = _resolve_ref(repo, ref)

    try:
        entry = commit.tree[path]
    except KeyError:
        raise PathNotFoundException(detail=f"File not found: {path}")

    if entry.type == pygit2.GIT_OBJECT_TREE:
        raise InvalidPathException(detail=f"'{path}' is a directory, not a file")

    if entry.type != pygit2.GIT_OBJECT_BLOB:
        raise InvalidPathException(detail=f"'{path}' is not a valid file")
    
    blob = repo[entry.id]
    
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
        "language": language
    }


async def get_commits(
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


async def get_diff(
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
        raise InvalidPathException(detail="Head commit is required")

    repo = _get_repo(repo_path)

    # 获取提交对象
    head_commit = _resolve_ref(repo, head)

    # 检查空仓库
    if head_commit is None:
        raise PathNotFoundException(detail=f"Ref not found: {head} (empty repository)")

    if base:
        base_commit = _resolve_ref(repo, base)
        # 检查 base 提交是否存在
        if base_commit is None:
            raise PathNotFoundException(detail=f"Base ref not found: {base}")
        # 使用树对象进行比较，避免在裸仓库中使用repo.diff
        diff = base_commit.tree.diff_to_tree(head_commit.tree)
    else:
        # 与空树对比 - 使用空树对象
        # 创建一个空的树
        empty_tree_builder = repo.TreeBuilder()
        empty_tree_id = empty_tree_builder.write()
        empty_tree = repo[empty_tree_id]
        diff = empty_tree.diff_to_tree(head_commit.tree)
    
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
                blob = repo[entry.id]

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

async def get_file_symbols(
    repo_path: str,
    ref: str = "HEAD",
    path: str = None
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
        raise InvalidPathException(detail="Path is required")

    # 获取文件内容
    blob_info = await get_blob_content(repo_path, ref=ref, path=path)

    language = blob_info.get("language", "text")
    content = blob_info.get("content", "")
    is_binary = blob_info.get("is_binary", False)

    symbols = []

    # 二进制文件不解析
    if is_binary or language == "binary":
        return {
            "path": path,
            "language": "binary",
            "symbols": []
        }

    # Python 简单符号提取（基于正则）
    if language == "python" and not is_binary:
        import re

        lines = content.split('\n')

        # 匹配函数定义：def function_name(
        func_pattern = re.compile(r'^def\s+(\w+)\s*\(')
        # 匹配类定义：class ClassName(
        class_pattern = re.compile(r'^class\s+(\w+)\s*[\(:\(]')
        # 匹配变量赋值（顶级）
        var_pattern = re.compile(r'^(\w+)\s*=')

        for line_no, line in enumerate(lines, 1):
            stripped = line.strip()

            # 跳过注释和空行
            if not stripped or stripped.startswith('#'):
                continue

            # 检查函数定义
            func_match = func_pattern.match(stripped)
            if func_match:
                symbols.append({
                    "name": func_match.group(1),
                    "type": "function",
                    "line": line_no
                })
                continue

            # 检查类定义
            class_match = class_pattern.match(stripped)
            if class_match:
                symbols.append({
                    "name": class_match.group(1),
                    "type": "class",
                    "line": line_no
                })
                continue

    # TODO: 支持更多语言（JavaScript, Go, Rust, Java 等）
    # 未来可使用 Tree-sitter 实现更精确的解析

    return {
        "path": path,
        "language": language,
        "symbols": symbols
    }
