"""
语言聚合服务：统计仓库默认分支的文件语言分布（GitHub 风格）。

通过 pygit2 遍历默认分支 tree，按 detect_file_language 统计各语言文件数，
返回 {语言标识: 文件数}，按数量降序。用于仓库卡片/详情头部的主语言展示。
"""
from __future__ import annotations

import asyncio
import logging
from collections import Counter

logger = logging.getLogger(__name__)


def _count_languages_sync(physical_path: str, branch: str) -> dict[str, int]:
    """
    同步遍历默认分支所有 blob，统计语言分布。

    Args:
        physical_path: 仓库物理路径
        branch: 分支名

    Returns:
        dict[str, int]: {语言标识: 文件数}，降序；失败返回空 dict
    """
    import pygit2
    from services.repository_browser_service import detect_file_language

    try:
        repo = pygit2.Repository(physical_path)
    except Exception:
        return {}

    try:
        branch_ref = repo.branches.local.get(branch) if branch else None
        target = branch_ref if branch_ref is not None else repo.head
        commit = target.peel(pygit2.Commit)
        tree = commit.tree
    except Exception:
        return {}

    counter: Counter[str] = Counter()
    for entry in tree.walk():
        if getattr(entry, "type_str", "") != "blob":
            continue
        name = getattr(entry, "name", "") or ""
        if not name:
            continue
        lang = detect_file_language(name)
        if lang in ("text", "binary"):
            continue
        counter[lang] += 1
    return {k: v for k, v in counter.most_common()}


async def detect_repo_languages(physical_path: str, branch: str) -> dict[str, int]:
    """
    异步统计仓库语言分布。

    Args:
        physical_path: 仓库物理路径
        branch: 分支名

    Returns:
        dict[str, int]: {语言标识: 文件数}，降序；任何失败返回空 dict
    """
    try:
        return await asyncio.to_thread(_count_languages_sync, physical_path, branch)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Failed to detect languages for {physical_path}: {e}")
        return {}