"""搜索业务逻辑层

设计（PostgreSQL 为核心设施）：

- 搜索内容一律来自 **Git 对象**（pygit2 读取 ref 的 tree/blob）——Perseus 存的是
  bare 仓库，没有工作树，不能扫文件系统。
- 索引持久化到**主库** `repo_search_files`（每文件一行）：PostgreSQL 侧由迁移
  创建 `pg_trgm` GIN 索引，`content ILIKE '%q%'` 走索引；SQLite（dev）退化为
  LIKE 扫描。查询使用可移植 SQL，dev/prod 同一套代码。
- 维护：默认分支随 push/PR merge/协作保存增量更新（按 git diff 变更文件）；
  首次或陈旧时在查询路径上懒重建 / 增量补齐。
- 兜底 / 任意 ref：进程内扫描 Git tree（子串匹配），永远正确、无外部依赖。
"""
import asyncio
import os
from dataclasses import dataclass, field
from typing import Iterable, List, Optional, Tuple

import pygit2
from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.repo_search import RepoSearchFile, RepoSearchState
from models.uuid7 import generate_uuid7

MAX_FILE_BYTES = 2 * 1024 * 1024
SCAN_FILE_LIMIT = 200

TEXT_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".rs", ".go", ".java",
    ".c", ".cpp", ".h", ".hpp", ".css", ".scss", ".html", ".md",
    ".json", ".yaml", ".yml", ".toml", ".sql", ".sh", ".rb",
    ".php", ".swift", ".kt", ".vue", ".svelte", ".txt", ".xml",
    ".ini", ".cfg", ".env",
}


@dataclass
class SearchResult:
    """搜索结果"""
    file: str
    line: int
    content: str


@dataclass
class SearchResponse:
    """搜索响应"""
    query: str
    results: list[SearchResult] = field(default_factory=list)
    total_count: int = 0
    truncated: bool = False


# =============================================================================
# Git 对象读取（内容来源）
# =============================================================================

def _head_commit(repo: pygit2.Repository) -> Optional[pygit2.Commit]:
    if repo.head_is_unborn:
        return None
    try:
        return repo.head.peel(pygit2.Commit)
    except Exception:
        return None


def _default_branch(repo_path: str) -> str:
    try:
        repo = pygit2.Repository(repo_path)
        if not repo.head_is_unborn:
            return repo.head.shorthand
    except Exception:
        pass
    return "main"


def _is_text_path(path: str) -> bool:
    _, ext = os.path.splitext(path)
    return ext.lower() in TEXT_EXTENSIONS


def _iter_text_blobs(
    repo: pygit2.Repository, tree: pygit2.Tree, prefix: str = ""
) -> Iterable[Tuple[str, str]]:
    """递归遍历 tree，产出 (路径, 文本内容)；跳过二进制 / 超大 / 非文本文件"""
    for entry in tree:
        path = f"{prefix}{entry.name}"
        if entry.type == pygit2.GIT_OBJECT_TREE:
            yield from _iter_text_blobs(repo, repo[entry.id], path + "/")
        elif entry.type == pygit2.GIT_OBJECT_BLOB and _is_text_path(path):
            blob = repo[entry.id]
            if blob.size > MAX_FILE_BYTES:
                continue
            data = blob.data
            if b"\x00" in data:
                continue
            yield path, data.decode("utf-8", "replace")


def _extract_all(repo_path: str) -> Tuple[Optional[str], List[Tuple[str, str]]]:
    """读取默认分支 HEAD 的全部文本文件（供全量重建）"""
    try:
        repo = pygit2.Repository(repo_path)
    except Exception:
        return None, []
    commit = _head_commit(repo)
    if commit is None:
        return None, []
    return str(commit.id), list(_iter_text_blobs(repo, commit.tree))


def _extract_changed(
    repo_path: str, changed_files: List[str]
) -> Tuple[Optional[str], List[Tuple[str, str]]]:
    """从默认分支 HEAD 读取指定路径的内容（供增量更新）"""
    try:
        repo = pygit2.Repository(repo_path)
    except Exception:
        return None, []
    commit = _head_commit(repo)
    if commit is None:
        return None, []
    out: List[Tuple[str, str]] = []
    for path in changed_files:
        if not _is_text_path(path):
            continue
        try:
            entry = commit.tree[path]
        except KeyError:
            continue
        if entry.type != pygit2.GIT_OBJECT_BLOB:
            continue
        blob = repo[entry.id]
        if blob.size > MAX_FILE_BYTES or b"\x00" in blob.data:
            continue
        out.append((path, blob.data.decode("utf-8", "replace")))
    return str(commit.id), out


def _search_git_tree(
    repo_path: str, ref: str, query: str, path: Optional[str], max_results: int
) -> List[SearchResult]:
    """进程内扫描 Git tree（大小写不敏感子串匹配）——兜底与任意 ref"""
    try:
        repo = pygit2.Repository(repo_path)
        commit = repo.revparse_single(ref).peel(pygit2.Commit)
    except Exception:
        return []

    needle = query.lower()
    prefix = None
    if path and path.strip("./"):
        prefix = path.strip("/").rstrip("/") + "/"

    results: List[SearchResult] = []
    for file_path, content in _iter_text_blobs(repo, commit.tree):
        if prefix and not file_path.startswith(prefix):
            continue
        for idx, line in enumerate(content.splitlines(), 1):
            if needle in line.lower():
                results.append(SearchResult(file=file_path, line=idx, content=line))
                if len(results) >= max_results:
                    return results
    return results


# =============================================================================
# 搜索服务（主库持久化）
# =============================================================================

class SearchService:
    """搜索服务"""

    async def search_code(
        self,
        db: AsyncSession,
        repository_id,
        repo_path: str,
        query: str,
        path: Optional[str] = None,
        ref: Optional[str] = None,
        max_results: int = 100,
    ) -> SearchResponse:
        """
        搜索代码（内容来自 Git 对象，索引存于主库）

        Args:
            db: 异步数据库会话
            repository_id: 仓库ID
            repo_path: 仓库物理路径（bare）
            query: 搜索关键词
            path: 限制搜索目录（前缀）
            ref: 分支/标签/提交；缺省为默认分支
            max_results: 最大结果数
        """
        if not query or not query.strip():
            return SearchResponse(query=query, results=[], total_count=0, truncated=False)

        default_ref = await asyncio.to_thread(_default_branch, repo_path)
        target_ref = ref or default_ref

        # 快路径：默认分支走主库索引（懒构建 / 增量补齐）
        if target_ref == default_ref:
            try:
                await self._ensure_index(db, repository_id, repo_path)
                index_results = await self._search_db(
                    db, repository_id, query, path, max_results
                )
                if index_results:
                    truncated = len(index_results) >= max_results
                    return SearchResponse(
                        query=query,
                        results=index_results,
                        total_count=-1 if truncated else len(index_results),
                        truncated=truncated,
                    )
            except Exception:
                # 索引不可用（如迁移未执行）时回滚并退回 Git tree 扫描
                await db.rollback()

        raw_results = await asyncio.to_thread(
            _search_git_tree, repo_path, target_ref, query, path, max_results + 1
        )
        truncated = len(raw_results) > max_results
        results = raw_results[:max_results]
        return SearchResponse(
            query=query,
            results=results,
            total_count=-1 if truncated else len(results),
            truncated=truncated,
        )

    # ---- 索引维护 ----

    async def rebuild_index(self, db: AsyncSession, repository_id, repo_path: str) -> int:
        """全量重建某仓库的搜索索引，返回索引文件数"""
        commit_id, files = await asyncio.to_thread(_extract_all, repo_path)
        await db.execute(
            delete(RepoSearchFile).where(RepoSearchFile.repository_id == repository_id)
        )
        if files:
            rows = [
                {
                    "id": generate_uuid7(),
                    "repository_id": repository_id,
                    "path": p,
                    "content": c,
                    "size": len(c.encode("utf-8")),
                }
                for p, c in files
            ]
            await db.execute(insert(RepoSearchFile.__table__), rows)
        await self._upsert_state(db, repository_id, commit_id)
        await db.commit()
        return len(files)

    async def update_files(
        self, db: AsyncSession, repository_id, repo_path: str, changed_files: List[str]
    ) -> None:
        """增量更新：仅重索引指定路径（取自默认分支 HEAD）"""
        if not changed_files:
            return
        commit_id, files = await asyncio.to_thread(
            _extract_changed, repo_path, changed_files
        )
        await db.execute(
            delete(RepoSearchFile).where(
                RepoSearchFile.repository_id == repository_id,
                RepoSearchFile.path.in_(changed_files),
            )
        )
        if files:
            rows = [
                {
                    "id": generate_uuid7(),
                    "repository_id": repository_id,
                    "path": p,
                    "content": c,
                    "size": len(c.encode("utf-8")),
                }
                for p, c in files
            ]
            await db.execute(insert(RepoSearchFile.__table__), rows)
        await self._upsert_state(db, repository_id, commit_id)
        await db.commit()

    async def cleanup_index(self, db: AsyncSession, repository_id) -> None:
        """删除某仓库的搜索索引（仓库删除后的生命周期清理）"""
        await db.execute(
            delete(RepoSearchFile).where(RepoSearchFile.repository_id == repository_id)
        )
        await db.execute(
            delete(RepoSearchState).where(RepoSearchState.repository_id == repository_id)
        )
        await db.commit()

    @staticmethod
    def diff_changed_files(
        repo_path: str,
        old_ref: Optional[str],
        new_ref: Optional[str],
    ) -> Optional[List[str]]:
        """
        计算两个引用间变更的文件路径列表（用于索引增量更新）

        Returns:
            变更文件路径列表；None 表示无法计算（调用方应回退全量重建）
        """
        if not old_ref or not new_ref:
            return None
        try:
            repo = pygit2.Repository(repo_path)
            old_commit = repo.revparse_single(old_ref).peel(pygit2.Commit)
            new_commit = repo.revparse_single(new_ref).peel(pygit2.Commit)
        except Exception:
            return None
        try:
            diff = repo.diff(old_commit, new_commit)
            changed: List[str] = []
            for patch in diff:
                delta = patch.delta
                if delta.old_file.path:
                    changed.append(delta.old_file.path)
                if delta.new_file.path and delta.new_file.path != delta.old_file.path:
                    changed.append(delta.new_file.path)
            return list(dict.fromkeys(changed))
        except Exception:
            return None

    # ---- 内部 ----

    async def _ensure_index(self, db: AsyncSession, repository_id, repo_path: str) -> None:
        """确保索引存在且与默认分支 HEAD 同步（懒构建 / 按 diff 增量）"""
        commit_id, _ = await asyncio.to_thread(_extract_all_snapshot, repo_path)
        if commit_id is None:
            return
        row = (
            await db.execute(
                select(RepoSearchState).where(
                    RepoSearchState.repository_id == repository_id
                )
            )
        ).scalar_one_or_none()
        indexed = row.indexed_commit if row else None
        if indexed == commit_id:
            return
        if indexed is None:
            await self.rebuild_index(db, repository_id, repo_path)
            return
        changed = await asyncio.to_thread(
            SearchService.diff_changed_files, repo_path, indexed, commit_id
        )
        if changed is None:
            await self.rebuild_index(db, repository_id, repo_path)
        else:
            await self.update_files(db, repository_id, repo_path, changed)

    async def _upsert_state(self, db: AsyncSession, repository_id, commit_id: Optional[str]) -> None:
        row = (
            await db.execute(
                select(RepoSearchState).where(
                    RepoSearchState.repository_id == repository_id
                )
            )
        ).scalar_one_or_none()
        if row is None:
            db.add(RepoSearchState(repository_id=repository_id, indexed_commit=commit_id))
        else:
            row.indexed_commit = commit_id

    async def _search_db(
        self,
        db: AsyncSession,
        repository_id,
        query: str,
        path: Optional[str],
        max_results: int,
    ) -> List[SearchResult]:
        escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{escaped}%"
        stmt = select(RepoSearchFile.path, RepoSearchFile.content).where(
            RepoSearchFile.repository_id == repository_id,
            RepoSearchFile.content.ilike(pattern, escape="\\"),
        )
        if path and path.strip("./"):
            prefix = path.strip("/").rstrip("/") + "/"
            stmt = stmt.where(RepoSearchFile.path.like(prefix + "%"))
        stmt = stmt.limit(SCAN_FILE_LIMIT)

        rows = (await db.execute(stmt)).all()
        needle = query.lower()
        results: List[SearchResult] = []
        for file_path, content in rows:
            for idx, line in enumerate(content.splitlines(), 1):
                if needle in line.lower():
                    results.append(SearchResult(file=file_path, line=idx, content=line))
                    if len(results) >= max_results:
                        return results
        return results


def _extract_all_snapshot(repo_path: str) -> Tuple[Optional[str], int]:
    """仅取默认分支 HEAD 提交与文件数（用于陈旧检测，避免重复读取全部内容）"""
    try:
        repo = pygit2.Repository(repo_path)
    except Exception:
        return None, 0
    commit = _head_commit(repo)
    if commit is None:
        return None, 0
    return str(commit.id), 0
