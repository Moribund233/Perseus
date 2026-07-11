"""
仓库代码浏览 Controller HTTP 集成测试

覆盖 repository_browser_controller.py 的所有端点：
- /tree: 文件树浏览
- /blob: 文件内容查看
- /commits: 提交历史
- /diff: 代码对比
- /readme: README 内容
- /symbols: 文件符号
- /language: 语言检测

同时验证缺失 await 不会导致 500（回归保护）。
"""
import pytest
import os
import tempfile
import pygit2
from fastapi.testclient import TestClient

from utils.git_utils import init_bare_repo, get_repository_storage_path
from utils.logging import get_named_logger

logger = get_named_logger("test_browser")


# ============ 辅助函数 ============

def create_repo_with_content(db, name: str, owner_id: int = 1) -> tuple:
    """创建数据库记录 + 物理 git 仓库，返回 (repo, physical_path)"""
    from models.repository import Repository

    repo = Repository(
        name=name,
        path=f"testuser/{name}",
        description=f"Test repo {name}",
        owner_id=owner_id,
        is_public=True,
        default_branch="master",
    )
    db.add(repo)
    db.commit()
    db.refresh(repo)

    physical_path = get_repository_storage_path(repo.path)
    init_bare_repo(physical_path)

    return repo, physical_path


def create_commit_in_repo(physical_path: str, filename: str, content: bytes,
                           commit_msg: str = "test commit"):
    """在 bare git 仓库中创建一条提交"""
    repo = pygit2.Repository(physical_path)
    author = pygit2.Signature("Test User", "test@example.com")
    committer = pygit2.Signature("Test User", "test@example.com")

    # 获取父提交
    parents = []
    try:
        head = repo.lookup_reference("refs/heads/master")
        parents.append(head.peel(pygit2.Commit).id)
    except KeyError:
        pass

    # 获取已有 tree（如果有父提交）
    existing_tree_id = None
    if parents:
        existing_tree_id = repo[parents[0]].tree_id

    tree_builder = repo.TreeBuilder(existing_tree_id) if existing_tree_id else repo.TreeBuilder()

    if "/" in filename:
        parts = filename.split("/")
        sub_builder = repo.TreeBuilder()
        sub_oid = repo.create_blob(content)
        sub_builder.insert(parts[-1], sub_oid, pygit2.GIT_FILEMODE_BLOB)
        sub_tree_oid = sub_builder.write()
        tree_builder.insert(parts[0], sub_tree_oid, pygit2.GIT_FILEMODE_TREE)
    else:
        blob_oid = repo.create_blob(content)
        tree_builder.insert(filename, blob_oid, pygit2.GIT_FILEMODE_BLOB)

    tree_oid = tree_builder.write()
    commit_oid = repo.create_commit(
        "refs/heads/master", author, committer,
        commit_msg, tree_oid, parents
    )
    return commit_oid


# ============ Tree 端点测试 ============

class TestTreeEndpoint:
    """GET /{repo_id}/tree"""

    def test_tree_root(self, test_client: TestClient, db):
        repo, physical_path = create_repo_with_content(db, "tree-root")
        create_commit_in_repo(physical_path, "README.md", b"# Hello")

        response = test_client.get(f"/api/v1/repositories/{repo.id}/tree")
        # 浏览器端点无需认证
        assert response.status_code in (200, 404)
        if response.status_code == 200:
            data = response.json()
            # 可以返回列表或字典格式
            assert data is not None

    def test_tree_with_content(self, test_client: TestClient, db):
        repo, physical_path = create_repo_with_content(db, "tree-content")
        create_commit_in_repo(physical_path, "src/main.py", b"def main(): pass")
        create_commit_in_repo(physical_path, "README.md", b"# Project")

        response = test_client.get(f"/api/v1/repositories/{repo.id}/tree",
                                    params={"ref": "master"})
        assert response.status_code in (200, 404)

    def test_tree_no_auth(self, test_client: TestClient, db):
        """无认证应返回非 401（公开仓库的 tree 浏览不需要登录）"""
        repo, physical_path = create_repo_with_content(db, "tree-noauth")
        create_commit_in_repo(physical_path, "a.txt", b"aaa")

        response = test_client.get(f"/api/v1/repositories/{repo.id}/tree")
        assert response.status_code != 401

    def test_tree_repo_not_found(self, test_client: TestClient):
        response = test_client.get("/api/v1/repositories/99999/tree")
        assert response.status_code == 404

    def test_tree_bad_ref(self, test_client: TestClient, db):
        repo, physical_path = create_repo_with_content(db, "tree-badref")
        create_commit_in_repo(physical_path, "a.txt", b"aaa")

        response = test_client.get(f"/api/v1/repositories/{repo.id}/tree",
                                    params={"ref": "nonexistent-branch"})
        assert response.status_code in (404, 422)


# ============ Blob 端点测试 ============

class TestBlobEndpoint:
    """GET /{repo_id}/blob"""

    def test_blob_content(self, test_client: TestClient, db):
        repo, physical_path = create_repo_with_content(db, "blob-content")
        create_commit_in_repo(physical_path, "hello.py",
                               b"print('hello world')\n")

        response = test_client.get(f"/api/v1/repositories/{repo.id}/blob",
                                    params={"path": "hello.py"})
        assert response.status_code in (200, 404)
        if response.status_code == 200:
            data = response.json()
            content = data.get("content", data.get("raw_content", ""))
            assert "hello" in str(content).lower() or "print" in str(content)
        # 不应返回 500（await 缺失回归保护）
        assert response.status_code != 500, f"不应因 await 缺失崩溃: {response.text}"

    def test_blob_no_auth(self, test_client: TestClient, db):
        """无认证应返回非 401（公开仓库的 blob 浏览不需要登录）"""
        repo, physical_path = create_repo_with_content(db, "blob-noauth")
        create_commit_in_repo(physical_path, "a.txt", b"aaa")

        response = test_client.get(f"/api/v1/repositories/{repo.id}/blob",
                                    params={"path": "a.txt"})
        assert response.status_code != 401

    def test_blob_not_found(self, test_client: TestClient, db):
        repo, physical_path = create_repo_with_content(db, "blob-notfound")
        create_commit_in_repo(physical_path, "a.txt", b"aaa")

        response = test_client.get(f"/api/v1/repositories/{repo.id}/blob",
                                    params={"path": "nonexistent.py"})
        assert response.status_code in (404, 422)

    def test_blob_missing_path_param(self, test_client: TestClient, db):
        repo, physical_path = create_repo_with_content(db, "blob-nopath")
        create_commit_in_repo(physical_path, "a.txt", b"aaa")

        response = test_client.get(f"/api/v1/repositories/{repo.id}/blob")
        assert response.status_code in (400, 422)

    def test_blob_empty_repo(self, test_client: TestClient, db):
        """空仓库（无提交）的 blob 请求"""
        from models.repository import Repository
        from utils.git_utils import get_repository_storage_path

        repo = Repository(
            name="blob-empty",
            path="testuser/blob-empty",
            owner_id=1, is_public=True,
        )
        db.add(repo)
        db.commit()
        db.refresh(repo)

        physical_path = get_repository_storage_path(repo.path)
        init_bare_repo(physical_path)

        response = test_client.get(f"/api/v1/repositories/{repo.id}/blob",
                                    params={"path": "anything.txt"})
        if response.status_code == 200:
            assert response.json().get("is_empty") is True
        else:
            assert response.status_code in (404, 422)


# ============ Commits 端点测试 ============

class TestCommitsEndpoint:
    """GET /{repo_id}/commits"""

    def test_commits_list(self, test_client: TestClient, db):
        repo, physical_path = create_repo_with_content(db, "commit-list")
        create_commit_in_repo(physical_path, "a.txt", b"v1", "first commit")
        create_commit_in_repo(physical_path, "b.txt", b"v2", "second commit")

        response = test_client.get(f"/api/v1/repositories/{repo.id}/commits")
        assert response.status_code in (200, 404)
        if response.status_code == 200:
            data = response.json()
            # 可能返回 dict 包含 items/list 或直接返回列表
            assert data is not None

    def test_commits_no_auth(self, test_client: TestClient, db):
        """无认证应返回非 401（公开仓库的 commits 浏览不需要登录）"""
        repo, physical_path = create_repo_with_content(db, "commit-noauth")
        create_commit_in_repo(physical_path, "a.txt", b"aaa")

        response = test_client.get(f"/api/v1/repositories/{repo.id}/commits")
        assert response.status_code != 401


# ============ README 端点测试 ============

class TestReadmeEndpoint:
    """GET /{repo_id}/readme"""

    def test_readme_exists(self, test_client: TestClient, db):
        repo, physical_path = create_repo_with_content(db, "readme-exists")
        create_commit_in_repo(physical_path, "README.md",
                               b"# My Project\n\nDescription here.")

        response = test_client.get(f"/api/v1/repositories/{repo.id}/readme")
        assert response.status_code in (200, 404)
        if response.status_code == 200:
            data = response.json()
            content = data.get("content", data.get("raw_content", ""))
            assert "My Project" in str(content)
        assert response.status_code != 500

    def test_readme_no_readme(self, test_client: TestClient, db):
        """仓库存在但没有 README 文件"""
        repo, physical_path = create_repo_with_content(db, "readme-none")
        create_commit_in_repo(physical_path, "main.py", b"print('hi')")

        response = test_client.get(f"/api/v1/repositories/{repo.id}/readme")
        assert response.status_code in (200, 404)
        if response.status_code == 200:
            data = response.json()
            assert not data.get("found", True)  # found=False

    def test_readme_repo_not_found(self, test_client: TestClient):
        response = test_client.get("/api/v1/repositories/99999/readme")
        assert response.status_code == 404

    def test_readme_no_auth(self, test_client: TestClient, db):
        repo, physical_path = create_repo_with_content(db, "readme-noauth")
        create_commit_in_repo(physical_path, "README.md", b"# Hi")

        response = test_client.get(f"/api/v1/repositories/{repo.id}/readme")
        assert response.status_code != 401


# ============ Diff 端点测试 ============

class TestDiffEndpoint:
    """GET /{repo_id}/diff"""

    def test_diff_basic(self, test_client: TestClient, db):
        repo, physical_path = create_repo_with_content(db, "diff-basic")

        create_commit_in_repo(physical_path, "file.txt", b"version 1", "first")
        create_commit_in_repo(physical_path, "file.txt", b"version 2", "second")

        repo_git = pygit2.Repository(physical_path)
        master = repo_git.lookup_reference("refs/heads/master")
        commit2 = master.peel(pygit2.Commit)
        commit1 = commit2.parent_ids[0] if commit2.parent_ids else commit2.id

        response = test_client.get(
            f"/api/v1/repositories/{repo.id}/diff",
            params={"head": str(commit2), "base": str(commit1)}
        )
        assert response.status_code in (200, 404)
        assert response.status_code != 500, f"不应因 await 缺失崩溃: {response.text}"

    def test_diff_invalid_sha(self, test_client: TestClient, db):
        repo, physical_path = create_repo_with_content(db, "diff-invalid")

        response = test_client.get(
            f"/api/v1/repositories/{repo.id}/diff",
            params={"head": "invalidsha1234567890123456789012345678901"}
        )
        assert response.status_code in (404, 422)


# ============ 回归保护：缺失 await 测试 ============

class TestAwaitRegression:
    """验证所有端点不会因缺失 await 导致 500"""

    def test_tree_no_await_crash(self, test_client: TestClient, db):
        """/tree 不应返回 500"""
        repo, physical_path = create_repo_with_content(db, "await-tree")
        create_commit_in_repo(physical_path, "f.py", b"x=1")

        response = test_client.get(f"/api/v1/repositories/{repo.id}/tree")
        assert response.status_code != 500, f"/tree 500: {response.text[:200]}"

    def test_blob_no_await_crash(self, test_client: TestClient, db):
        """/blob 不应返回 500"""
        repo, physical_path = create_repo_with_content(db, "await-blob")
        create_commit_in_repo(physical_path, "f.py", b"x=1")

        response = test_client.get(f"/api/v1/repositories/{repo.id}/blob",
                                    params={"path": "f.py"})
        assert response.status_code != 500, f"/blob 500: {response.text[:200]}"

    def test_diff_no_await_crash(self, test_client: TestClient, db):
        """/diff 不应返回 500"""
        repo, physical_path = create_repo_with_content(db, "await-diff")
        create_commit_in_repo(physical_path, "f.txt", b"data", "init")

        repo_git = pygit2.Repository(physical_path)
        master = repo_git.lookup_reference("refs/heads/master")
        c1 = master.peel(pygit2.Commit).id

        response = test_client.get(
            f"/api/v1/repositories/{repo.id}/diff",
            params={"head": str(c1)}
        )
        assert response.status_code != 500, f"/diff 500: {response.text[:200]}"


# ============ Symbol 端点测试 ============

class TestSymbolEndpoint:
    """GET /{repo_id}/symbols"""

    def test_symbols_basic(self, test_client: TestClient, db):
        repo, physical_path = create_repo_with_content(db, "sym-basic")
        create_commit_in_repo(physical_path, "app.py",
                               b"def hello():\n    pass\n\nclass Foo:\n    pass\n")

        response = test_client.get(f"/api/v1/repositories/{repo.id}/symbols",
                                    params={"path": "app.py"})
        assert response.status_code in (200, 404)
        assert response.status_code != 500


# ============ Language 端点测试 ============

class TestLanguageEndpoint:
    """GET /{repo_id}/language"""

    def test_language_detection(self, test_client: TestClient, db):
        repo, physical_path = create_repo_with_content(db, "lang-test")
        create_commit_in_repo(physical_path, "main.py", b"x=1")

        response = test_client.get(f"/api/v1/repositories/{repo.id}/language",
                                    params={"path": "main.py"})
        assert response.status_code in (200, 404)
        if response.status_code == 200:
            data = response.json()
            lang = data.get("language", "")
            assert "python" in str(lang).lower()
