"""搜索服务层测试 — 包含 F-039 搜索索引维护"""
import pytest
import tempfile
import shutil
import os
import subprocess
from unittest.mock import patch
from services.search_service import SearchService, SearchResult, SearchResponse, SearchIndex


def _git(*args, cwd=None):
    """执行 git 命令 (供构建真实仓库的测试使用)"""
    return subprocess.run(
        ["git", *args],
        cwd=cwd, check=True, capture_output=True, text=True,
    )


def _build_worktree_repo() -> "tuple[str, str, str]":
    """创建带三个变更 (修改/新增/删除) 的 non-bare 仓库

    Returns:
        (repo_path, old_sha, new_sha)
    """
    tmpdir = tempfile.mkdtemp()
    repo_path = os.path.join(tmpdir, "repo")
    _git("init", "--initial-branch=main", repo_path)
    _git("config", "user.email", "t@example.com", cwd=repo_path)
    _git("config", "user.name", "T", cwd=repo_path)

    def write(name, content):
        with open(os.path.join(repo_path, name), "w") as f:
            f.write(content)

    write("a.py", "def one():\n    pass\n")
    write("b.txt", "hello old\n")
    _git("add", ".", cwd=repo_path)
    _git("commit", "-m", "init", cwd=repo_path)
    old_sha = _git("rev-parse", "HEAD", cwd=repo_path).stdout.strip()

    write("a.py", "def one():\n    pass\n\ndef two():\n    return 2\n")
    write("c.py", "def three():\n    pass\n")
    os.remove(os.path.join(repo_path, "b.txt"))
    _git("add", "-A", cwd=repo_path)
    _git("commit", "-m", "second", cwd=repo_path)
    new_sha = _git("rev-parse", "HEAD", cwd=repo_path).stdout.strip()

    return repo_path, old_sha, new_sha


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

    def test_update_removes_deleted_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, "src"))
            with open(os.path.join(tmpdir, "src", "main.py"), "w") as f:
                f.write("def hello():\n    pass\n")

            index = SearchIndex(tmpdir)
            index.build()
            assert len(index.search("hello")) > 0

            os.remove(os.path.join(tmpdir, "src", "main.py"))
            index.update(["src/main.py"])

            assert index.search("hello") == []

    def test_update_preserves_unchanged_entries(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, "src"))
            with open(os.path.join(tmpdir, "src", "keep.py"), "w") as f:
                f.write("def keep():\n    pass\n")
            with open(os.path.join(tmpdir, "src", "change.py"), "w") as f:
                f.write("def old():\n    pass\n")

            index = SearchIndex(tmpdir)
            index.build()
            assert len(index.search("keep")) > 0

            with open(os.path.join(tmpdir, "src", "change.py"), "w") as f:
                f.write("def new_func():\n    pass\n")
            index.update(["src/change.py"])

            assert any("keep" in r.content for r in index.search("keep"))
            assert any("new_func" in r.content for r in index.search("new_func"))
            assert all(r.content.count("new_func") == 1 for r in index.search("new_func"))


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


class TestIncrementalIndex:

    def test_diff_changed_files_returns_only_changed(self):
        repo_path, old_sha, new_sha = _build_worktree_repo()
        try:
            changed = SearchService.diff_changed_files(repo_path, old_sha, new_sha)
            assert changed is not None
            assert set(changed) == {"a.py", "b.txt", "c.py"}
        finally:
            shutil.rmtree(os.path.dirname(repo_path), ignore_errors=True)

    def test_diff_changed_files_none_for_missing_ref(self):
        repo_path, old_sha, new_sha = _build_worktree_repo()
        try:
            assert SearchService.diff_changed_files(repo_path, "does-not-exist", new_sha) is None
            assert SearchService.diff_changed_files(repo_path, None, new_sha) is None
            assert SearchService.diff_changed_files(repo_path, old_sha, None) is None
        finally:
            shutil.rmtree(os.path.dirname(repo_path), ignore_errors=True)

    def test_diff_changed_files_none_empty_range(self):
        repo_path, old_sha, _ = _build_worktree_repo()
        try:
            assert SearchService.diff_changed_files(repo_path, old_sha, old_sha) == []
        finally:
            shutil.rmtree(os.path.dirname(repo_path), ignore_errors=True)

    def test_update_files_reindexes_only_given_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, "src"))
            with open(os.path.join(tmpdir, "src", "keep.py"), "w") as f:
                f.write("def keep():\n    pass\n")
            with open(os.path.join(tmpdir, "src", "change.py"), "w") as f:
                f.write("def old():\n    pass\n")

            SearchService.rebuild_index(tmpdir)
            with open(os.path.join(tmpdir, "src", "change.py"), "w") as f:
                f.write("def changed_func():\n    pass\n")

            SearchService.update_files(tmpdir, ["src/change.py"])

            index = SearchIndex(tmpdir)
            assert any("keep" in r.content for r in index.search("keep"))
            assert any("changed_func" in r.content for r in index.search("changed_func"))
            assert all("old" not in r.content for r in index.search("changed_func"))

    def test_update_files_noop_for_empty_list(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "a.py"), "w") as f:
                f.write("def a():\n    pass\n")
            SearchService.rebuild_index(tmpdir)
            SearchService.update_files(tmpdir, [])
            assert SearchIndex(tmpdir).exists()

    def test_cleanup_index_removes_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "a.py"), "w") as f:
                f.write("def a():\n    pass\n")
            SearchService.rebuild_index(tmpdir)
            assert os.path.exists(os.path.join(tmpdir, ".perseus_search_index"))
            SearchService.cleanup_index(tmpdir)
            assert not os.path.exists(os.path.join(tmpdir, ".perseus_search_index"))
            assert SearchIndex(tmpdir).exists() is False
