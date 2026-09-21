"""搜索服务层测试 — 内容来自 Git 对象，索引持久化到主库（SQLite 测试库）"""
import os
import shutil
import subprocess
import tempfile

import pytest
from sqlalchemy import func, select

from models.repo_search import RepoSearchFile, RepoSearchState
from services.search_service import SearchResponse, SearchResult, SearchService


def _git(*args, cwd=None):
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True,
    )


def _make_bare_repo(files: dict, extra_branch: dict | None = None):
    """创建带提交的 bare 仓库（模拟 Perseus 存储形态），返回 (tmpdir, bare, work)"""
    tmp = tempfile.mkdtemp()
    work = os.path.join(tmp, "work")
    _git("init", "--initial-branch=main", work)
    _git("config", "user.email", "t@example.com", cwd=work)
    _git("config", "user.name", "T", cwd=work)

    def write(name, content):
        full = os.path.join(work, name)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as f:
            f.write(content)

    for name, content in files.items():
        write(name, content)
    _git("add", "-A", cwd=work)
    _git("commit", "-m", "init", cwd=work)

    if extra_branch:
        _git("checkout", "-b", "feature", cwd=work)
        for name, content in extra_branch.items():
            write(name, content)
        _git("add", "-A", cwd=work)
        _git("commit", "-m", "feature", cwd=work)
        _git("checkout", "main", cwd=work)

    bare = os.path.join(tmp, "repo.git")
    _git("clone", "--bare", work, bare)
    _git("remote", "add", "origin", bare, cwd=work)
    return tmp, bare, work


def _build_worktree_repo():
    """带三个变更 (修改/新增/删除) 的 non-bare 仓库，返回 (repo_path, old_sha, new_sha)"""
    tmpdir = tempfile.mkdtemp()
    repo_path = os.path.join(tmpdir, "repo")
    _git("init", "--initial-branch=main", repo_path)
    _git("config", "user.email", "t@example.com", cwd=repo_path)
    _git("config", "user.name", "T", cwd=repo_path)

    def write(name, content):
        with open(os.path.join(repo_path, name), "w", encoding="utf-8") as f:
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
def search_service():
    return SearchService()


class TestSearchService:
    @pytest.mark.asyncio
    async def test_search_code(self, async_db, async_test_repo, search_service):
        tmp, bare, _ = _make_bare_repo({"main.py": "def hello():\n    pass\n"})
        try:
            res = await search_service.search_code(async_db, async_test_repo.id, bare, "hello")
            assert isinstance(res, SearchResponse)
            assert res.total_count > 0
            assert res.results[0].file == "main.py"
            assert res.results[0].line == 1
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_search_code_with_path(self, async_db, async_test_repo, search_service):
        tmp, bare, _ = _make_bare_repo({"src/a.py": "hello\n", "other.py": "hello\n"})
        try:
            res = await search_service.search_code(async_db, async_test_repo.id, bare, "hello", path="src")
            assert len(res.results) == 1
            assert res.results[0].file == "src/a.py"
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_search_code_no_results(self, async_db, async_test_repo, search_service):
        tmp, bare, _ = _make_bare_repo({"main.py": "def hello():\n"})
        try:
            res = await search_service.search_code(async_db, async_test_repo.id, bare, "nonexistent")
            assert res.total_count == 0
            assert res.results == []
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_search_result_structure(self, async_db, async_test_repo, search_service):
        tmp, bare, _ = _make_bare_repo({"main.py": "def hello():\n"})
        try:
            res = await search_service.search_code(async_db, async_test_repo.id, bare, "hello")
            assert res.results
            result = res.results[0]
            assert isinstance(result, SearchResult)
            assert hasattr(result, "file") and hasattr(result, "line") and hasattr(result, "content")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_search_response_truncation(self, async_db, async_test_repo, search_service):
        tmp, bare, _ = _make_bare_repo({"a.py": "def a():\n", "b.py": "def b():\n"})
        try:
            res = await search_service.search_code(async_db, async_test_repo.id, bare, "def", max_results=1)
            assert len(res.results) <= 1
            assert res.truncated is True
            assert res.total_count == -1
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_search_ref_branch(self, async_db, async_test_repo, search_service):
        """非默认 ref 走进程内 Git tree 扫描"""
        tmp, bare, _ = _make_bare_repo(
            {"main.py": "def hello():\n"},
            extra_branch={"feature.py": "def feature_only():\n"},
        )
        try:
            assert (await search_service.search_code(async_db, async_test_repo.id, bare, "feature_only")).total_count == 0
            res = await search_service.search_code(async_db, async_test_repo.id, bare, "feature_only", ref="feature")
            assert res.total_count > 0
            assert res.results[0].file == "feature.py"
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestSearchIndexPersistence:
    @pytest.mark.asyncio
    async def test_index_rows_in_db(self, async_db, async_test_repo, search_service):
        tmp, bare, _ = _make_bare_repo({"src/main.py": "def hello():\n", "README.md": "# Test\n"})
        try:
            count = await search_service.rebuild_index(async_db, async_test_repo.id, bare)
            assert count == 2
            rows = (await async_db.execute(
                select(func.count()).select_from(RepoSearchFile).where(
                    RepoSearchFile.repository_id == async_test_repo.id
                )
            )).scalar_one()
            assert rows == 2
            state = (await async_db.execute(
                select(RepoSearchState).where(RepoSearchState.repository_id == async_test_repo.id)
            )).scalar_one()
            assert state.indexed_commit
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_update_files_reindexes(self, async_db, async_test_repo, search_service):
        tmp, bare, work = _make_bare_repo(
            {"src/keep.py": "def keep():\n", "src/change.py": "def old():\n"}
        )
        try:
            await search_service.rebuild_index(async_db, async_test_repo.id, bare)
            with open(os.path.join(work, "src", "change.py"), "w", encoding="utf-8") as f:
                f.write("def changed_func():\n")
            _git("add", "-A", cwd=work)
            _git("commit", "-m", "change", cwd=work)
            _git("push", "origin", "main", cwd=work)

            await search_service.update_files(async_db, async_test_repo.id, bare, ["src/change.py"])
            res = await search_service.search_code(async_db, async_test_repo.id, bare, "changed_func")
            assert res.total_count > 0
            keep = await search_service.search_code(async_db, async_test_repo.id, bare, "keep")
            assert keep.total_count > 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_cleanup_index(self, async_db, async_test_repo, search_service):
        tmp, bare, _ = _make_bare_repo({"a.py": "def a():\n"})
        try:
            await search_service.rebuild_index(async_db, async_test_repo.id, bare)
            await search_service.cleanup_index(async_db, async_test_repo.id)
            rows = (await async_db.execute(
                select(func.count()).select_from(RepoSearchFile).where(
                    RepoSearchFile.repository_id == async_test_repo.id
                )
            )).scalar_one()
            assert rows == 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_update_files_noop_for_empty_list(self, async_db, async_test_repo, search_service):
        tmp, bare, _ = _make_bare_repo({"a.py": "def a():\n"})
        try:
            await search_service.rebuild_index(async_db, async_test_repo.id, bare)
            await search_service.update_files(async_db, async_test_repo.id, bare, [])
            rows = (await async_db.execute(
                select(func.count()).select_from(RepoSearchFile).where(
                    RepoSearchFile.repository_id == async_test_repo.id
                )
            )).scalar_one()
            assert rows == 1
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


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
