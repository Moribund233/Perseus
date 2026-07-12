"""搜索业务逻辑层"""
import hashlib
import sqlite3
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from utils.ripgrep_utils import search_code as ripgrep_search, is_available


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


class SearchIndex:
    """SQLite FTS5-based search index for a repository (F-039)"""

    INDEX_DIR = ".perseus_search_index"

    def __init__(self, repo_path: str):
        self.repo_path = repo_path
        self.index_path = os.path.join(repo_path, self.INDEX_DIR, "fts.db")
        self._ensure_dir()

    def _ensure_dir(self):
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.index_path)
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_schema(self, conn: sqlite3.Connection):
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS file_index USING fts5(
                path, content, tokenize='porter unicode61'
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS file_hashes (
                path TEXT PRIMARY KEY,
                hash TEXT NOT NULL,
                mtime REAL NOT NULL
            )
        """)

    def exists(self) -> bool:
        return os.path.exists(self.index_path)

    def build(self):
        """Full index rebuild — scan all files in repo_path"""
        conn = self._get_conn()
        try:
            self._init_schema(conn)
            conn.execute("DELETE FROM file_index")
            conn.execute("DELETE FROM file_hashes")

            for file_path in self._iter_files():
                self._index_file(conn, file_path)
            conn.commit()
        finally:
            conn.close()

    def update(self, changed_files: List[str]):
        """Incremental update — reindex specified files"""
        conn = self._get_conn()
        try:
            self._init_schema(conn)
            for rel_path in changed_files:
                full_path = os.path.join(self.repo_path, rel_path)
                if os.path.isfile(full_path):
                    self._index_file(conn, rel_path)
                else:
                    conn.execute("DELETE FROM file_index WHERE path = ?", (rel_path,))
                    conn.execute("DELETE FROM file_hashes WHERE path = ?", (rel_path,))
            conn.commit()
        finally:
            conn.close()

    def search(self, query: str, max_results: int = 100) -> List[SearchResult]:
        """Search indexed files using FTS5"""
        if not self.exists():
            return []

        conn = self._get_conn()
        try:
            self._init_schema(conn)
            cursor = conn.execute(
                """SELECT path, snippet(file_index, 1, '<mark>', '</mark>', '...', 64)
                   FROM file_index WHERE file_index MATCH ? ORDER BY rank
                   LIMIT ?""",
                (query, max_results),
            )
            results = []
            for row in cursor:
                results.append(SearchResult(file=row[0], line=0, content=row[1]))
            return results
        except sqlite3.OperationalError:
            return []
        finally:
            conn.close()

    def _iter_files(self) -> List[str]:
        """Iterate over all source files in the repo"""
        skip_dirs = {'.git', '__pycache__', 'node_modules', '.venv', '.perseus_search_index'}
        extensions = {'.py', '.js', '.ts', '.jsx', '.tsx', '.rs', '.go', '.java',
                      '.c', '.cpp', '.h', '.hpp', '.css', '.scss', '.html', '.md',
                      '.json', '.yaml', '.yml', '.toml', '.sql', '.sh', '.rb',
                      '.php', '.swift', '.kt', '.vue', '.svelte', '.txt'}
        files = []
        for root, dirs, names in os.walk(self.repo_path):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            for name in names:
                ext = os.path.splitext(name)[1].lower()
                if ext in extensions:
                    rel_path = os.path.relpath(os.path.join(root, name), self.repo_path)
                    files.append(rel_path)
        return files

    def _index_file(self, conn: sqlite3.Connection, rel_path: str):
        """Index a single file"""
        full_path = os.path.join(self.repo_path, rel_path)
        if not os.path.isfile(full_path):
            return
        try:
            with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
        except Exception:
            return

        stat = os.stat(full_path)
        file_hash = hashlib.md5(content.encode('utf-8')).hexdigest()

        conn.execute("DELETE FROM file_index WHERE path = ?", (rel_path,))
        conn.execute("DELETE FROM file_hashes WHERE path = ?", (rel_path,))

        conn.execute(
            "INSERT INTO file_index (path, content) VALUES (?, ?)",
            (rel_path, content),
        )
        conn.execute(
            "INSERT INTO file_hashes (path, hash, mtime) VALUES (?, ?, ?)",
            (rel_path, file_hash, stat.st_mtime),
        )


class SearchService:
    """搜索服务"""

    def search_code(
        self,
        repo_path: str,
        query: str,
        path: Optional[str] = None,
        max_results: int = 100,
        use_index: bool = True,
    ) -> SearchResponse:
        """
        搜索代码

        Args:
            repo_path: 仓库路径
            query: 搜索关键词
            path: 限制搜索目录
            max_results: 最大结果数
            use_index: 是否尝试使用搜索索引

        Returns:
            SearchResponse: 搜索响应
        """
        if use_index:
            try:
                index = SearchIndex(repo_path)
                if index.exists():
                    index_results = index.search(query, max_results)
                    if index_results:
                        return SearchResponse(
                            query=query,
                            results=index_results,
                            total_count=len(index_results),
                            truncated=len(index_results) >= max_results,
                        )
            except Exception:
                pass

        if not is_available():
            return SearchResponse(
                query=query,
                results=[],
                total_count=0,
                truncated=False,
            )

        try:
            raw_results = ripgrep_search(
                repo_path=repo_path,
                query=query,
                path=path,
                max_results=max_results + 1,
            )
        except RuntimeError:
            return SearchResponse(
                query=query,
                results=[],
                total_count=0,
                truncated=False,
            )

        truncated = len(raw_results) > max_results
        results = [
            SearchResult(
                file=r["file"],
                line=r["line"],
                content=r["content"],
            )
            for r in raw_results[:max_results]
        ]

        return SearchResponse(
            query=query,
            results=results,
            total_count=-1 if truncated else len(results),
            truncated=truncated,
        )

    @staticmethod
    def rebuild_index(repo_path: str) -> int:
        """Rebuild search index for a repository. Returns file count."""
        index = SearchIndex(repo_path)
        index.build()
        return len(index._iter_files())
