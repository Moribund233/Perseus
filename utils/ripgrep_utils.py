"""Ripgrep 命令行工具封装"""
import json
import os
import subprocess
import shutil
from typing import Optional


def is_available() -> bool:
    """
    检查 ripgrep 是否可用

    Returns:
        bool: ripgrep 是否安装
    """
    return shutil.which("rg") is not None


def search_code(
    repo_path: str,
    query: str,
    path: Optional[str] = None,
    ref: Optional[str] = None,
    max_results: int = 100,
) -> list[dict]:
    """
    使用 ripgrep 搜索代码

    Args:
        repo_path: 仓库路径
        query: 搜索关键词
        path: 限制搜索目录
        ref: Git 分支/标签（暂未实现）
        max_results: 最大结果数

    Returns:
        list[dict]: 搜索结果列表
    """
    if not is_available():
        raise RuntimeError("ripgrep is not installed")

    cmd = ["rg", "--json", "--max-count", str(max_results), query]

    if path:
        cmd.append(os.path.join(repo_path, path))
    else:
        cmd.append(repo_path)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError("Search timed out")

    if result.returncode not in (0, 1):
        raise RuntimeError(f"ripgrep failed with exit code {result.returncode}: {result.stderr}")

    results = []
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        try:
            data = json.loads(line)
            if data.get("type") == "match":
                match = data["data"]
                results.append({
                    "file": match["path"]["text"].replace(repo_path + "/", ""),
                    "line": match["line_number"],
                    "content": match["lines"]["text"].rstrip("\n"),
                })
        except (json.JSONDecodeError, KeyError):
            continue

    return results