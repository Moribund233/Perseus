"""搜索服务层测试 — 包含 F-039 搜索索引维护"""
import pytest
import tempfile
import shutil
import os
from unittest.mock import patch
from services.search_service import SearchService, SearchResult, SearchResponse, SearchIndex


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
        assert results.truncated is True
        assert results.total_count == -1

    def test_search_runtime_error(self, search_service: SearchService, temp_repo: str):
        with patch("services.search_service.ripgrep_search", side_effect=RuntimeError("test error")):
            results = search_service.search_code(temp_repo, "hello")
            assert results.total_count == 0
            assert results.results == []
            assert results.truncated is False

    def test_search_ref_removed(self, search_service: SearchService, temp_repo: str):
        # ref parameter is no longer accepted
        results = search_service.search_code(temp_repo, "hello")
        assert isinstance(results, SearchResponse)


class TestSearchIndex:

    def test_build_index_creates_fts_table(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, "src"))
            with open(os.path.join(tmpdir, "src", "main.py"), "w") as f:
                f.write("def hello():\n    print('hello world')\n")
            with open(os.path.join(tmpdir, "README.md"), "w") as f:
                f.write("# Test Project\nThis is a test.\n")

            index = SearchIndex(tmpdir)
            index.build()
            assert index.exists()

    def test_search_returns_results_from_index(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, "src"))
            with open(os.path.join(tmpdir, "src", "main.py"), "w") as f:
                f.write("def hello():\n    print('hello world')\n")

            index = SearchIndex(tmpdir)
            index.build()

            results = index.search("hello")
            assert len(results) > 0
            assert any("hello" in r.content for r in results)

    def test_update_index_adds_new_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, "src"))
            with open(os.path.join(tmpdir, "src", "main.py"), "w") as f:
                f.write("def hello():\n    pass\n")

            index = SearchIndex(tmpdir)
            index.build()

            with open(os.path.join(tmpdir, "src", "utils.py"), "w") as f:
                f.write("def helper():\n    return 42\n")

            index.update(["src/utils.py"])

            results = index.search("helper")
            assert len(results) > 0
            assert any("helper" in r.content for r in results)

    def test_search_index_returns_empty_for_no_match(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "test.py"), "w") as f:
                f.write("hello world\n")

            index = SearchIndex(tmpdir)
            index.build()

            results = index.search("nonexistent")
            assert len(results) == 0


class TestSearchIndexIntegration:

    def test_rebuild_index_static_method(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, "src"))
            with open(os.path.join(tmpdir, "src", "main.py"), "w") as f:
                f.write("def hello():\n    pass\n")
            count = SearchService.rebuild_index(tmpdir)
            assert count > 0
            index = SearchIndex(tmpdir)
            assert index.exists()
            results = index.search("hello")
            assert len(results) > 0
