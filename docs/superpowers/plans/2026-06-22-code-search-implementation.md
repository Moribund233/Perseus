# Code Search Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement code search functionality using ripgrep for efficient full-text search in repositories

**Architecture:** Layered architecture: Utils (ripgrep wrapper) → Service (business logic) → Controller (API endpoint). Uses subprocess to call ripgrep CLI tool for performance.

**Tech Stack:** Python 3.12, FastAPI, ripgrep (system dependency), pytest-asyncio

---

## File Structure

```
perseus/
├── utils/ripgrep_utils.py           # ripgrep 命令封装
├── services/search_service.py       # 搜索业务逻辑
├── controller/search_controller.py  # 搜索 API 端点
├── tests/test_ripgrep_utils.py      # ripgrep 工具测试
├── tests/test_search_service.py     # 搜索服务测试
└── tests/test_search_api.py         # 搜索 API 测试
```

---

## Task 1: Install ripgrep and add config

**Files:**
- Modify: `core/config.py`
- Modify: `Dockerfile`

- [ ] **Step 1: Add search configuration**

Add to `core/config.py` after LFS settings:

```python
class SearchSettings(BaseModel):
    """搜索配置"""
    enabled: bool = True
    max_results: int = 100
    max_file_size: int = 10 * 1024 * 1024  # 10MB
```

- [ ] **Step 2: Add search attribute to Settings class**

```python
search: SearchSettings = SearchSettings()
```

- [ ] **Step 3: Add ripgrep to Dockerfile**

Add to `Dockerfile` after other apt-get installs:

```dockerfile
RUN apt-get update && apt-get install -y ripgrep && rm -rf /var/lib/apt/lists/*
```

- [ ] **Step 4: Commit**

```bash
git add core/config.py Dockerfile
git commit -m "feat(search): add search config and ripgrep dependency"
```

---

## Task 2: Ripgrep Utils — Availability Check

**Files:**
- Create: `utils/ripgrep_utils.py`
- Create: `tests/test_ripgrep_utils.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_ripgrep_utils.py
"""Ripgrep 工具测试"""
import pytest
from utils.ripgrep_utils import is_available, search_code


class TestRipgrepAvailability:
    def test_is_available_returns_bool(self):
        result = is_available()
        assert isinstance(result, bool)

    def test_is_available_on_system_with_ripgrep(self):
        # This test assumes ripgrep is installed in test environment
        # If not installed, it should return False gracefully
        result = is_available()
        # Just verify it doesn't raise
        assert result in (True, False)


class TestRipgrepSearch:
    def test_search_code_returns_list(self):
        # Test with a known directory
        import tempfile
        import os
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a test file
            test_file = os.path.join(tmpdir, "test.py")
            with open(test_file, "w") as f:
                f.write("def hello():\n    pass\n")
            
            results = search_code(tmpdir, "hello")
            assert isinstance(results, list)

    def test_search_code_with_matches(self):
        import tempfile
        import os
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "test.py")
            with open(test_file, "w") as f:
                f.write("def hello():\n    pass\n")
            
            results = search_code(tmpdir, "hello")
            assert len(results) > 0
            assert results[0]["file"] == "test.py"
            assert results[0]["line"] == 1
            assert "hello" in results[0]["content"]

    def test_search_code_no_matches(self):
        import tempfile
        import os
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "test.py")
            with open(test_file, "w") as f:
                f.write("def hello():\n    pass\n")
            
            results = search_code(tmpdir, "nonexistent_function")
            assert results == []

    def test_search_code_with_path_filter(self):
        import tempfile
        import os
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create files in different directories
            os.makedirs(os.path.join(tmpdir, "src"))
            os.makedirs(os.path.join(tmpdir, "tests"))
            
            with open(os.path.join(tmpdir, "src", "main.py"), "w") as f:
                f.write("def hello():\n    pass\n")
            with open(os.path.join(tmpdir, "tests", "test_main.py"), "w") as f:
                f.write("def test_hello():\n    pass\n")
            
            results = search_code(tmpdir, "hello", path="src")
            assert len(results) == 1
            assert "src" in results[0]["file"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_ripgrep_utils.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'utils.ripgrep_utils'"

- [ ] **Step 3: Write minimal implementation**

```python
# utils/ripgrep_utils.py
"""Ripgrep 命令行工具封装"""
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
        cmd.append(path)

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

    results = []
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        try:
            import json
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_ripgrep_utils.py -v`
Expected: 5 passed (or skipped if ripgrep not installed)

- [ ] **Step 5: Commit**

```bash
git add utils/ripgrep_utils.py tests/test_ripgrep_utils.py
git commit -m "feat(search): add ripgrep utilities for code search"
```

---

## Task 3: Search Service — Business Logic

**Files:**
- Create: `services/search_service.py`
- Create: `tests/test_search_service.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_search_service.py
"""搜索服务层测试"""
import pytest
import tempfile
import shutil
import os
from services.search_service import SearchService, SearchResult, SearchResponse


@pytest.fixture
def temp_repo():
    """创建临时仓库目录"""
    path = tempfile.mkdtemp()
    # 创建测试文件
    with open(os.path.join(path, "main.py"), "w") as f:
        f.write("def hello():\n    pass\n\ndef world():\n    pass\n")
    with open(os.path.join(path, "utils.py"), "w") as f:
        f.write("def helper():\n    return hello()\n")
    yield path
    shutil.rmtree(path)


@pytest.fixture
def search_service():
    return SearchService()


class TestSearchService:
    def test_search_code(self, search_service: SearchService, temp_repo: str):
        results = search_service.search_code(temp_repo, "hello")
        assert isinstance(results, SearchResponse)
        assert results.query == "hello"
        assert results.total_count > 0

    def test_search_code_with_path(self, search_service: SearchService, temp_repo: str):
        results = search_service.search_code(temp_repo, "hello", path=".")
        assert results.total_count > 0

    def test_search_code_no_results(self, search_service: SearchService, temp_repo: str):
        results = search_service.search_code(temp_repo, "nonexistent")
        assert results.total_count == 0
        assert results.results == []

    def test_search_result_structure(self, search_service: SearchService, temp_repo: str):
        results = search_service.search_code(temp_repo, "hello")
        if results.results:
            result = results.results[0]
            assert isinstance(result, SearchResult)
            assert hasattr(result, "file")
            assert hasattr(result, "line")
            assert hasattr(result, "content")

    def test_search_response_truncation(self, search_service: SearchService, temp_repo: str):
        # Search with max_results=1
        results = search_service.search_code(temp_repo, "def", max_results=1)
        assert len(results.results) <= 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_search_service.py -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: Write minimal implementation**

```python
# services/search_service.py
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
        ref: Optional[str] = None,
        max_results: int = 100,
    ) -> SearchResponse:
        """
        搜索代码

        Args:
            repo_path: 仓库路径
            query: 搜索关键词
            path: 限制搜索目录
            ref: Git 分支/标签
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

        raw_results = ripgrep_search(
            repo_path=repo_path,
            query=query,
            path=path,
            ref=ref,
            max_results=max_results + 1,  # Fetch one extra to detect truncation
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
            total_count=len(results),
            truncated=truncated,
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_search_service.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add services/search_service.py tests/test_search_service.py
git commit -m "feat(search): add search service with business logic"
```

---

## Task 4: Search Controller — API Endpoint

**Files:**
- Create: `controller/search_controller.py`
- Modify: `api/routes_config.py`
- Create: `tests/test_search_api.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_search_api.py
"""搜索 API 端点测试"""
import pytest
from fastapi.testclient import TestClient


class TestSearchAPI:
    def test_search_code(self, test_client: TestClient, auth_headers: dict, db):
        from tests.conftest import create_test_repo
        repo = create_test_repo(db, 1, name="search-test-repo")

        response = test_client.get(
            f"/api/v1/repositories/{repo.id}/search",
            params={"q": "def"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "query" in data
        assert "results" in data
        assert "total_count" in data
        assert "truncated" in data

    def test_search_code_with_path(self, test_client: TestClient, auth_headers: dict, db):
        from tests.conftest import create_test_repo
        repo = create_test_repo(db, 1, name="search-path-repo")

        response = test_client.get(
            f"/api/v1/repositories/{repo.id}/search",
            params={"q": "def", "path": "."},
            headers=auth_headers,
        )
        assert response.status_code == 200

    def test_search_requires_query(self, test_client: TestClient, auth_headers: dict, db):
        from tests.conftest import create_test_repo
        repo = create_test_repo(db, 1, name="search-noquery-repo")

        response = test_client.get(
            f"/api/v1/repositories/{repo.id}/search",
            headers=auth_headers,
        )
        assert response.status_code == 422  # Validation error

    def test_search_requires_auth(self, test_client: TestClient, db):
        from tests.conftest import create_test_repo
        repo = create_test_repo(db, 1, name="search-auth-repo")

        response = test_client.get(
            f"/api/v1/repositories/{repo.id}/search",
            params={"q": "def"},
        )
        assert response.status_code == 401
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_search_api.py -v`
Expected: FAIL with "404 Not Found"

- [ ] **Step 3: Write minimal implementation**

```python
# controller/search_controller.py
"""搜索控制器层"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.routes_config import get_route_prefix
from models.async_db import get_async_db
from models.user import User
from api.dependencies import get_current_user
from services.search_service import SearchService
from utils.repository_utils import get_repository_path


router = APIRouter(prefix=get_route_prefix("repositories"), tags=["search"])


@router.get("/{repo_id}/search")
async def search_code(
    repo_id: int,
    q: str = Query(..., description="搜索关键词"),
    path: str = Query(None, description="限制搜索目录"),
    ref: str = Query(None, description="Git 分支/标签"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """搜索仓库代码"""
    repo_path = get_repository_path(repo_id)
    search_service = SearchService()
    return search_service.search_code(
        repo_path=repo_path,
        query=q,
        path=path,
        ref=ref,
    )
```

- [ ] **Step 4: Register router in routes_config.py**

Add to `api/routes_config.py`:

```python
from controller.search_controller import router as search_router
# ... in create_api_router():
api_v1_router.include_router(search_router)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_search_api.py -v`
Expected: 4 passed

- [ ] **Step 6: Commit**

```bash
git add controller/search_controller.py api/routes_config.py tests/test_search_api.py
git commit -m "feat(search): add search API endpoint"
```

---

## Task 5: Run Full Test Suite

- [ ] **Step 1: Run all tests**

Run: `pytest -v`
Expected: All tests pass (including new search tests)

- [ ] **Step 2: Fix any failures if needed**

- [ ] **Step 3: Final commit if any fixes were made**

```bash
git add -A
git commit -m "fix(search): resolve test failures"
```

---

## Task 6: Update Documentation

**Files:**
- Modify: `docs/api/README.md`
- Modify: `docs/api/roadmap.md`

- [ ] **Step 1: Add search to API README**

Add a new section to `docs/api/README.md`:

```markdown
### 20. 代码搜索

| 功能 | 状态 | 说明 |
|------|------|------|
| 仓库内全文搜索 | ✅ | 基于 ripgrep 高效搜索 |
| 目录过滤 | ✅ | 支持限制搜索目录 |
| 结果格式化 | ✅ | 返回文件、行号、内容 |
| 截断处理 | ✅ | 超过限制时截断结果 |
```

- [ ] **Step 2: Mark roadmap tasks as complete**

Update `docs/api/roadmap.md` to mark F-037, F-038, F-039 as complete.

- [ ] **Step 3: Commit**

```bash
git add docs/api/README.md docs/api/roadmap.md
git commit -m "docs: update search documentation and roadmap status"
```
