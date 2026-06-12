"""
仓库代码浏览服务测试

F-022: 代码查看器后端
- 文件树浏览
- 文件内容查看
- 提交历史
- 代码对比
"""

import pytest
import os
import tempfile
import pygit2
from unittest.mock import patch

from services.repository_browser_service import (
    get_tree_entries,
    get_blob_content,
    get_commits,
    get_diff,
    _get_repo,
    _resolve_ref,
    _get_tree,
)
from core.exception import (
    NotFoundException,
    ValidationException,
    RepositoryNotFoundException,
    PathNotFoundException,
    InvalidPathException
)


# ============ 辅助函数 ============

def create_test_repository(tmpdir: str) -> str:
    """创建测试 Git 仓库"""
    repo_path = os.path.join(tmpdir, "test_repo.git")
    os.makedirs(repo_path, exist_ok=True)

    # 初始化 bare 仓库
    repo = pygit2.init_repository(repo_path, bare=True)

    # 创建初始提交
    author = pygit2.Signature("Test User", "test@example.com")
    committer = pygit2.Signature("Test User", "test@example.com")

    # 创建文件树
    tree_builder = repo.TreeBuilder()

    # 添加 README.md
    readme_oid = repo.create_blob(b"# Test Repository\n\nThis is a test.")
    tree_builder.insert("README.md", readme_oid, pygit2.GIT_FILEMODE_BLOB)

    # 添加 src 目录和 main.py
    src_builder = repo.TreeBuilder()
    main_oid = repo.create_blob(b"def main():\n    print('Hello, World!')\n")
    src_builder.insert("main.py", main_oid, pygit2.GIT_FILEMODE_BLOB)
    tree_builder.insert("src", src_builder.write(), pygit2.GIT_FILEMODE_TREE)

    # 添加空目录 marker
    empty_dir_builder = repo.TreeBuilder()
    tree_builder.insert("empty_dir", empty_dir_builder.write(), pygit2.GIT_FILEMODE_TREE)

    tree_oid = tree_builder.write()

    # 创建提交 (不指定 ref，稍后手动创建)
    commit_oid = repo.create_commit(
        None,  # 不自动更新任何引用
        author,
        committer,
        "Initial commit",
        tree_oid,
        []
    )

    # 创建 master 分支
    repo.create_reference("refs/heads/master", commit_oid)

    # 创建第二个提交
    tree_builder2 = repo.TreeBuilder(tree_oid)
    utils_oid = repo.create_blob(b"def helper():\n    pass\n")
    src_builder2 = repo.TreeBuilder(repo[src_builder.write()])
    src_builder2.insert("utils.py", utils_oid, pygit2.GIT_FILEMODE_BLOB)
    tree_builder2.insert("src", src_builder2.write(), pygit2.GIT_FILEMODE_TREE)

    tree_oid2 = tree_builder2.write()

    commit_oid2 = repo.create_commit(
        None,  # 不自动更新任何引用
        author,
        committer,
        "Add utils.py",
        tree_oid2,
        [commit_oid]
    )

    # 更新 master 分支指向新提交
    repo.references["refs/heads/master"].set_target(commit_oid2)

    # 设置 HEAD 指向 master
    repo.set_head("refs/heads/master")

    return repo_path


def create_empty_repository(tmpdir: str) -> str:
    """创建空 Git 仓库"""
    repo_path = os.path.join(tmpdir, "empty_repo.git")
    os.makedirs(repo_path, exist_ok=True)
    pygit2.init_repository(repo_path, bare=True)
    return repo_path


# ============ _get_repo 测试 ============

def test_get_repo_success():
    """测试成功获取仓库对象"""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = create_test_repository(tmpdir)
        repo = _get_repo(repo_path)
        assert repo is not None
        assert not repo.is_empty


def test_get_repo_not_found():
    """测试获取不存在的仓库"""
    with pytest.raises(RepositoryNotFoundException):
        _get_repo("/non/existent/path")


# ============ _resolve_ref 测试 ============

def test_resolve_ref_head():
    """测试解析 HEAD"""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = create_test_repository(tmpdir)
        repo = pygit2.Repository(repo_path)
        commit = _resolve_ref(repo, "HEAD")
        assert commit is not None


def test_resolve_ref_branch():
    """测试解析分支名"""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = create_test_repository(tmpdir)
        repo = pygit2.Repository(repo_path)
        commit = _resolve_ref(repo, "master")
        assert commit is not None


def test_resolve_ref_commit_sha():
    """测试解析提交 SHA"""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = create_test_repository(tmpdir)
        repo = pygit2.Repository(repo_path)
        head_commit = repo.head.target
        commit = _resolve_ref(repo, str(head_commit))
        assert commit is not None
        assert str(commit.id) == str(head_commit)


def test_resolve_ref_not_found():
    """测试解析不存在的引用"""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = create_test_repository(tmpdir)
        repo = pygit2.Repository(repo_path)
        with pytest.raises(PathNotFoundException):
            _resolve_ref(repo, "non-existent-branch")


def test_resolve_ref_empty_repo():
    """测试解析空仓库的引用"""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = create_empty_repository(tmpdir)
        repo = pygit2.Repository(repo_path)
        commit = _resolve_ref(repo, "HEAD")
        assert commit is None


# ============ _get_tree 测试 ============

def test_get_tree_root():
    """测试获取根目录树"""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = create_test_repository(tmpdir)
        repo = pygit2.Repository(repo_path)
        commit = repo.head.peel(pygit2.Commit)
        tree = _get_tree(repo, commit, "")
        assert tree is not None
        assert len(list(tree)) > 0


def test_get_tree_subdirectory():
    """测试获取子目录树"""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = create_test_repository(tmpdir)
        repo = pygit2.Repository(repo_path)
        commit = repo.head.peel(pygit2.Commit)
        tree = _get_tree(repo, commit, "src")
        assert tree is not None
        assert len(list(tree)) > 0


def test_get_tree_not_found():
    """测试获取不存在的路径"""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = create_test_repository(tmpdir)
        repo = pygit2.Repository(repo_path)
        commit = repo.head.peel(pygit2.Commit)
        with pytest.raises(PathNotFoundException):
            _get_tree(repo, commit, "non-existent-path")


def test_get_tree_is_file():
    """测试获取文件路径（应该是目录）"""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = create_test_repository(tmpdir)
        repo = pygit2.Repository(repo_path)
        commit = repo.head.peel(pygit2.Commit)
        with pytest.raises(InvalidPathException) as exc_info:
            _get_tree(repo, commit, "README.md")
        assert "not a directory" in str(exc_info.value)


# ============ get_tree_entries 测试 ============

@pytest.mark.asyncio
async def test_get_tree_entries_root():
    """测试获取根目录条目"""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = create_test_repository(tmpdir)
        result = await get_tree_entries(repo_path, ref="HEAD", path="")

        assert result["path"] == ""
        assert result["ref"] == "HEAD"
        assert "entries" in result
        assert len(result["entries"]) > 0

        # 检查 README.md
        readme_entry = next((e for e in result["entries"] if e["name"] == "README.md"), None)
        assert readme_entry is not None
        assert readme_entry["type"] == "blob"
        assert "size" in readme_entry

        # 检查 src 目录
        src_entry = next((e for e in result["entries"] if e["name"] == "src"), None)
        assert src_entry is not None
        assert src_entry["type"] == "tree"


@pytest.mark.asyncio
async def test_get_tree_entries_subdirectory():
    """测试获取子目录条目"""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = create_test_repository(tmpdir)
        result = await get_tree_entries(repo_path, ref="HEAD", path="src")

        assert result["path"] == "src"
        assert len(result["entries"]) > 0

        # 检查 main.py
        main_entry = next((e for e in result["entries"] if e["name"] == "main.py"), None)
        assert main_entry is not None
        assert main_entry["type"] == "blob"


@pytest.mark.asyncio
async def test_get_tree_entries_empty_repo():
    """测试获取空仓库的条目"""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = create_empty_repository(tmpdir)
        result = await get_tree_entries(repo_path, ref="HEAD", path="")

        assert result["is_empty"] is True
        assert result["entries"] == []


@pytest.mark.asyncio
async def test_get_tree_entries_not_found():
    """测试获取不存在的路径"""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = create_test_repository(tmpdir)
        with pytest.raises(PathNotFoundException):
            await get_tree_entries(repo_path, ref="HEAD", path="non-existent")


@pytest.mark.asyncio
async def test_get_tree_entries_repo_not_found():
    """测试获取不存在仓库的条目"""
    with pytest.raises(RepositoryNotFoundException):
        await get_tree_entries("/non/existent/repo", ref="HEAD", path="")


@pytest.mark.asyncio
async def test_get_tree_entries_sorting():
    """测试条目排序（目录在前，按名称排序）"""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = create_test_repository(tmpdir)
        result = await get_tree_entries(repo_path, ref="HEAD", path="")

        entries = result["entries"]
        # 目录应该在文件之前
        types = [e["type"] for e in entries]
        tree_indices = [i for i, t in enumerate(types) if t == "tree"]
        blob_indices = [i for i, t in enumerate(types) if t == "blob"]

        if tree_indices and blob_indices:
            assert max(tree_indices) < min(blob_indices)


# ============ get_blob_content 测试 ============

@pytest.mark.asyncio
async def test_get_blob_content_text_file():
    """测试获取文本文件内容"""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = create_test_repository(tmpdir)
        result = await get_blob_content(repo_path, ref="HEAD", path="README.md")

        assert result["name"] == "README.md"
        assert result["path"] == "README.md"
        assert "# Test Repository" in result["content"]
        assert result["is_binary"] is False
        assert result["encoding"] == "utf-8"
        assert "size" in result
        assert "sha" in result


@pytest.mark.asyncio
async def test_get_blob_content_source_file():
    """测试获取源代码文件内容"""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = create_test_repository(tmpdir)
        result = await get_blob_content(repo_path, ref="HEAD", path="src/main.py")

        assert result["name"] == "main.py"
        assert "def main():" in result["content"]
        assert result["is_binary"] is False


@pytest.mark.asyncio
async def test_get_blob_content_no_path():
    """测试不指定路径"""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = create_test_repository(tmpdir)
        with pytest.raises(InvalidPathException) as exc_info:
            await get_blob_content(repo_path, ref="HEAD", path="")
        assert "Path is required" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_blob_content_not_found():
    """测试获取不存在的文件"""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = create_test_repository(tmpdir)
        with pytest.raises(PathNotFoundException):
            await get_blob_content(repo_path, ref="HEAD", path="non-existent.py")


@pytest.mark.asyncio
async def test_get_blob_content_is_directory():
    """测试获取目录（应该是文件）"""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = create_test_repository(tmpdir)
        with pytest.raises(InvalidPathException) as exc_info:
            await get_blob_content(repo_path, ref="HEAD", path="src")
        assert "is a directory" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_blob_content_binary_file():
    """测试获取二进制文件内容"""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = os.path.join(tmpdir, "test_repo.git")
        os.makedirs(repo_path, exist_ok=True)
        repo = pygit2.init_repository(repo_path, bare=True)

        # 创建二进制文件
        binary_data = bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A])  # PNG header
        blob_oid = repo.create_blob(binary_data)

        tree_builder = repo.TreeBuilder()
        tree_builder.insert("image.png", blob_oid, pygit2.GIT_FILEMODE_BLOB)
        tree_oid = tree_builder.write()

        author = pygit2.Signature("Test", "test@example.com")
        commit_oid = repo.create_commit(
            None,  # 不自动更新 HEAD
            author, author,
            "Add binary file",
            tree_oid,
            []
        )
        repo.create_reference("refs/heads/master", commit_oid)
        repo.set_head("refs/heads/master")

        result = await get_blob_content(repo_path, ref="HEAD", path="image.png")

        assert result["name"] == "image.png"
        assert result["is_binary"] is True
        assert result["encoding"] == "hex"


# ============ get_commits 测试 ============

@pytest.mark.asyncio
async def test_get_commits_basic():
    """测试获取提交历史"""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = create_test_repository(tmpdir)
        result = await get_commits(repo_path, ref="HEAD")

        assert "commits" in result
        assert "pagination" in result
        assert len(result["commits"]) > 0

        # 检查提交结构
        commit = result["commits"][0]
        assert "sha" in commit
        assert "message" in commit
        assert "author" in commit
        assert "committer" in commit
        assert "date" in commit
        assert "parents" in commit


@pytest.mark.asyncio
async def test_get_commits_pagination():
    """测试提交历史分页"""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = create_test_repository(tmpdir)
        result = await get_commits(repo_path, ref="HEAD", page=1, per_page=1)

        assert len(result["commits"]) == 1
        assert result["pagination"]["page"] == 1
        assert result["pagination"]["per_page"] == 1


@pytest.mark.asyncio
async def test_get_commits_empty_repo():
    """测试获取空仓库的提交历史"""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = create_empty_repository(tmpdir)
        result = await get_commits(repo_path, ref="HEAD")

        assert result["is_empty"] is True
        assert result["commits"] == []


@pytest.mark.asyncio
async def test_get_commits_not_found():
    """测试获取不存在的引用"""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = create_test_repository(tmpdir)
        with pytest.raises(PathNotFoundException):
            await get_commits(repo_path, ref="non-existent-branch")


# ============ get_diff 测试 ============

@pytest.mark.asyncio
async def test_get_diff_with_base():
    """测试获取两次提交之间的差异"""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = create_test_repository(tmpdir)
        repo = pygit2.Repository(repo_path)

        # 获取两个提交的 SHA
        commits = list(repo.walk(repo.head.target, pygit2.GIT_SORT_TIME))
        head_sha = str(commits[0].id)
        base_sha = str(commits[1].id)

        result = await get_diff(repo_path, base=base_sha, head=head_sha)

        assert "files" in result
        assert "stats" in result
        assert result["stats"]["files_changed"] > 0


@pytest.mark.asyncio
async def test_get_diff_without_base():
    """测试获取与空树的差异"""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = create_test_repository(tmpdir)
        repo = pygit2.Repository(repo_path)

        # 获取第一个提交
        commits = list(repo.walk(repo.head.target, pygit2.GIT_SORT_TIME))
        first_commit = commits[-1]  # 最早的提交

        result = await get_diff(repo_path, base=None, head=str(first_commit.id))

        assert "files" in result
        assert result["stats"]["files_changed"] > 0


@pytest.mark.asyncio
async def test_get_diff_no_head():
    """测试不提供 head 参数"""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = create_test_repository(tmpdir)
        with pytest.raises(InvalidPathException) as exc_info:
            await get_diff(repo_path, base=None, head=None)
        assert "Head commit is required" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_diff_head_not_found():
    """测试 head 提交不存在"""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = create_test_repository(tmpdir)
        with pytest.raises(PathNotFoundException):
            await get_diff(repo_path, base=None, head="invalid-sha")


@pytest.mark.asyncio
async def test_get_diff_base_not_found():
    """测试 base 提交不存在"""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = create_test_repository(tmpdir)
        repo = pygit2.Repository(repo_path)
        head_sha = str(repo.head.target)
        with pytest.raises(PathNotFoundException):
            await get_diff(repo_path, base="invalid-sha", head=head_sha)
