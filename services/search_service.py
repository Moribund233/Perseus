"""搜索业务逻辑层"""
from dataclasses import dataclass, field
from typing import Optional

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


class SearchService:
    """搜索服务"""

    def search_code(
        self,
        repo_path: str,
        query: str,
        path: Optional[str] = None,
        max_results: int = 100,
    ) -> SearchResponse:
        """
        搜索代码

        Args:
            repo_path: 仓库路径
            query: 搜索关键词
            path: 限制搜索目录
            max_results: 最大结果数

        Returns:
            SearchResponse: 搜索响应
        """
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
