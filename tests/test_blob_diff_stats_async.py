"""
G-010: blob 响应添加 diff_stats 字段

验证 get_blob_content 返回的字典包含 diff_stats 字段。
blob 是查看特定 ref 下的文件内容（无"变更"概念），因此 diff_stats 默认为 None。
"""

import pytest
import tempfile
import os
import pygit2

from services.repository_browser_service import get_blob_content


def _create_repo_with_commit(tmpdir: str) -> str:
    """创建带初始提交的 bare 仓库"""
    repo_path = os.path.join(tmpdir, "test_repo.git")
    os.makedirs(repo_path, exist_ok=True)
    repo = pygit2.init_repository(repo_path, bare=True)

    author = pygit2.Signature("Test User", "test@example.com")
    committer = pygit2.Signature("Test User", "test@example.com")

    tree_builder = repo.TreeBuilder()
    readme_oid = repo.create_blob(b"# Test\n\nHello world.")
    tree_builder.insert("README.md", readme_oid, pygit2.GIT_FILEMODE_BLOB)
    tree_oid = tree_builder.write()

    commit_oid = repo.create_commit(
        None,
        author,
        committer,
        "initial commit",
        tree_oid,
        []
    )
    repo.create_reference("refs/heads/master", commit_oid)
    repo.head.set_target(commit_oid)

    return repo_path


@pytest.mark.asyncio
async def test_blob_includes_diff_stats():
    """验证 blob 响应包含 diff_stats 字段"""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = _create_repo_with_commit(tmpdir)
        result = await get_blob_content(repo_path, ref="master", path="README.md")

        assert "diff_stats" in result
        assert result["diff_stats"] is None


@pytest.mark.asyncio
async def test_blob_diff_stats_is_none_for_source_file():
    """验证源代码文件的 diff_stats 也为 None"""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = _create_repo_with_commit(tmpdir)

        # 添加第二个文件
        repo = pygit2.Repository(repo_path)
        author = pygit2.Signature("Test User", "test@example.com")
        committer = pygit2.Signature("Test User", "test@example.com")

        head_commit = repo.head.peel(pygit2.Commit)
        tree = head_commit.tree
        tree_builder = repo.TreeBuilder(tree)
        py_oid = repo.create_blob(b"print('hello')")
        tree_builder.insert("main.py", py_oid, pygit2.GIT_FILEMODE_BLOB)
        new_tree = tree_builder.write()

        repo.create_commit(
            "HEAD",
            author,
            committer,
            "add main.py",
            new_tree,
            [head_commit.id]
        )

        result = await get_blob_content(repo_path, ref="HEAD", path="main.py")
        assert "diff_stats" in result
        assert result["diff_stats"] is None
