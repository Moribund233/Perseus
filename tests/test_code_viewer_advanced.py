"""
代码查看器高级功能测试

F-023: 文件内容语法高亮支持
F-024: 文件导航功能
"""

import pytest
import os
import tempfile
import pygit2

from services.repository_browser_service import (
    get_blob_content,
    get_tree_entries,
    detect_file_language,
    get_readme_content,
    get_file_symbols
)
from core.exception import (
    PathNotFoundException,
    InvalidPathException
)


# ============ 辅助函数 ============

def create_test_repository_with_various_files(tmpdir: str) -> str:
    """创建包含各种文件类型的测试 Git 仓库"""
    repo_path = os.path.join(tmpdir, "test_repo.git")
    os.makedirs(repo_path, exist_ok=True)

    # 初始化 bare 仓库
    repo = pygit2.init_repository(repo_path, bare=True)

    # 创建各种文件
    files_content = {
        "README.md": b"# Test Repository\n\nThis is a test repository.",
        "main.py": b"def main():\n    print('Hello, World!')\n\nif __name__ == '__main__':\n    main()",
        "utils.py": b"def helper():\n    pass\n\ndef another_function():\n    return 42",
        "app.js": b"function init() {\n    console.log('App initialized');\n}\n\nmodule.exports = { init };",
        "styles.css": b"body {\n    margin: 0;\n    padding: 20px;\n}",
        "index.html": b"<!DOCTYPE html>\n<html>\n<head><title>Test</title></head>\n<body></body></html>",
        "config.json": b'{"name": "test", "version": "1.0.0"}',
        "Makefile": b".PHONY: all\nall:\n\techo 'Building...'",
        "Dockerfile": b"FROM python:3.9\nWORKDIR /app",
        "main.go": b"package main\n\nimport \"fmt\"\n\nfunc main() {\n    fmt.Println('Hello')\n}",
        "lib.rs": b"pub fn add(a: i32, b: i32) -> i32 {\n    a + b\n}",
        "Main.java": b"public class Main {\n    public static void main(String[] args) {\n        System.out.println('Hello');\n    }\n}",
    }

    # 创建文件树
    tree_builder = repo.TreeBuilder()

    for filename, content in files_content.items():
        blob_oid = repo.create_blob(content)
        filemode = pygit2.GIT_FILEMODE_BLOB
        # 检查是否是可执行文件
        if filename in ["Makefile"]:
            filemode = pygit2.GIT_FILEMODE_BLOB_EXECUTABLE
        tree_builder.insert(filename, blob_oid, filemode)

    # 创建 src 目录
    src_builder = repo.TreeBuilder()
    src_content = b"# Source module\n"
    src_blob = repo.create_blob(src_content)
    src_builder.insert("__init__.py", src_blob, pygit2.GIT_FILEMODE_BLOB)
    tree_builder.insert("src", src_builder.write(), pygit2.GIT_FILEMODE_TREE)

    tree_oid = tree_builder.write()

    # 创建提交
    author = pygit2.Signature("Test User", "test@example.com")
    commit_oid = repo.create_commit(
        None,
        author, author,
        "Initial commit with various files",
        tree_oid,
        []
    )

    # 创建 master 分支
    repo.create_reference("refs/heads/master", commit_oid)
    repo.set_head("refs/heads/master")

    return repo_path


# ============ F-023: 文件语言检测测试 ============

def test_detect_file_language_python():
    """测试检测 Python 文件语言"""
    assert detect_file_language("main.py") == "python"
    assert detect_file_language("utils.py") == "python"
    assert detect_file_language("script.pyw") == "python"


def test_detect_file_language_javascript():
    """测试检测 JavaScript 文件语言"""
    assert detect_file_language("app.js") == "javascript"
    assert detect_file_language("main.mjs") == "javascript"


def test_detect_file_language_typescript():
    """测试检测 TypeScript 文件语言"""
    assert detect_file_language("app.ts") == "typescript"
    assert detect_file_language("component.tsx") == "typescript"


def test_detect_file_language_html():
    """测试检测 HTML 文件语言"""
    assert detect_file_language("index.html") == "html"
    assert detect_file_language("page.htm") == "html"


def test_detect_file_language_css():
    """测试检测 CSS 文件语言"""
    assert detect_file_language("styles.css") == "css"
    assert detect_file_language("theme.scss") == "scss"
    assert detect_file_language("app.sass") == "sass"


def test_detect_file_language_go():
    """测试检测 Go 文件语言"""
    assert detect_file_language("main.go") == "go"


def test_detect_file_language_rust():
    """测试检测 Rust 文件语言"""
    assert detect_file_language("lib.rs") == "rust"


def test_detect_file_language_java():
    """测试检测 Java 文件语言"""
    assert detect_file_language("Main.java") == "java"


def test_detect_file_language_json():
    """测试检测 JSON 文件语言"""
    assert detect_file_language("config.json") == "json"


def test_detect_file_language_markdown():
    """测试检测 Markdown 文件语言"""
    assert detect_file_language("README.md") == "markdown"
    assert detect_file_language("docs.markdown") == "markdown"


def test_detect_file_language_dockerfile():
    """测试检测 Dockerfile"""
    assert detect_file_language("Dockerfile") == "dockerfile"
    assert detect_file_language("dockerfile") == "dockerfile"


def test_detect_file_language_makefile():
    """测试检测 Makefile"""
    assert detect_file_language("Makefile") == "makefile"
    assert detect_file_language("makefile") == "makefile"


def test_detect_file_language_unknown():
    """测试未知文件类型"""
    assert detect_file_language("file.xyz") == "text"
    assert detect_file_language("data.bin") == "binary"


def test_detect_file_language_no_extension():
    """测试无扩展名文件"""
    assert detect_file_language("README") == "text"
    assert detect_file_language("LICENSE") == "text"


# ============ F-023: get_blob_content 语言字段测试 ============

@pytest.mark.asyncio
async def test_get_blob_content_with_language():
    """测试获取文件内容时包含语言信息"""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = create_test_repository_with_various_files(tmpdir)

        # 测试 Python 文件
        result = await get_blob_content(repo_path, ref="HEAD", path="main.py")
        assert result["language"] == "python"
        assert result["name"] == "main.py"

        # 测试 JavaScript 文件
        result = await get_blob_content(repo_path, ref="HEAD", path="app.js")
        assert result["language"] == "javascript"

        # 测试 HTML 文件
        result = await get_blob_content(repo_path, ref="HEAD", path="index.html")
        assert result["language"] == "html"

        # 测试 CSS 文件
        result = await get_blob_content(repo_path, ref="HEAD", path="styles.css")
        assert result["language"] == "css"

        # 测试 Markdown 文件
        result = await get_blob_content(repo_path, ref="HEAD", path="README.md")
        assert result["language"] == "markdown"


@pytest.mark.asyncio
async def test_get_blob_content_binary_with_language():
    """测试二进制文件语言检测"""
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
            None,
            author, author,
            "Add binary file",
            tree_oid,
            []
        )
        repo.create_reference("refs/heads/master", commit_oid)
        repo.set_head("refs/heads/master")

        result = await get_blob_content(repo_path, ref="HEAD", path="image.png")
        assert result["is_binary"] is True
        assert result["language"] == "binary"


# ============ F-024: README 内容获取测试 ============

@pytest.mark.asyncio
async def test_get_readme_content_found():
    """测试获取 README 文件内容"""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = create_test_repository_with_various_files(tmpdir)

        result = await get_readme_content(repo_path, ref="HEAD")

        assert result["found"] is True
        assert result["filename"] == "README.md"
        assert "# Test Repository" in result["content"]
        assert result["language"] == "markdown"


@pytest.mark.asyncio
async def test_get_readme_content_not_found():
    """测试仓库没有 README"""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = os.path.join(tmpdir, "test_repo.git")
        os.makedirs(repo_path, exist_ok=True)
        repo = pygit2.init_repository(repo_path, bare=True)

        # 只创建一个普通文件
        blob_oid = repo.create_blob(b"Some content")
        tree_builder = repo.TreeBuilder()
        tree_builder.insert("file.txt", blob_oid, pygit2.GIT_FILEMODE_BLOB)
        tree_oid = tree_builder.write()

        author = pygit2.Signature("Test", "test@example.com")
        commit_oid = repo.create_commit(
            None,
            author, author,
            "Initial commit",
            tree_oid,
            []
        )
        repo.create_reference("refs/heads/master", commit_oid)
        repo.set_head("refs/heads/master")

        result = await get_readme_content(repo_path, ref="HEAD")

        assert result["found"] is False
        assert result["content"] is None


@pytest.mark.asyncio
async def test_get_readme_content_various_names():
    """测试识别不同命名的 README 文件"""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = os.path.join(tmpdir, "test_repo.git")
        os.makedirs(repo_path, exist_ok=True)
        repo = pygit2.init_repository(repo_path, bare=True)

        # 创建 README.rst
        blob_oid = repo.create_blob(b"Test Repository\n================")
        tree_builder = repo.TreeBuilder()
        tree_builder.insert("README.rst", blob_oid, pygit2.GIT_FILEMODE_BLOB)
        tree_oid = tree_builder.write()

        author = pygit2.Signature("Test", "test@example.com")
        commit_oid = repo.create_commit(
            None,
            author, author,
            "Initial commit",
            tree_oid,
            []
        )
        repo.create_reference("refs/heads/master", commit_oid)
        repo.set_head("refs/heads/master")

        result = await get_readme_content(repo_path, ref="HEAD")

        assert result["found"] is True
        assert result["filename"] == "README.rst"


# ============ F-024: 文件符号提取测试 ============

@pytest.mark.asyncio
async def test_get_file_symbols_python():
    """测试提取 Python 文件符号"""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = create_test_repository_with_various_files(tmpdir)

        result = await get_file_symbols(repo_path, ref="HEAD", path="utils.py")

        assert result["language"] == "python"
        assert "symbols" in result
        # 应该检测到函数定义
        function_names = [s["name"] for s in result["symbols"]]
        assert "helper" in function_names
        assert "another_function" in function_names


@pytest.mark.asyncio
async def test_get_file_symbols_unsupported_language():
    """测试不支持的语言返回空符号列表"""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = create_test_repository_with_various_files(tmpdir)

        result = await get_file_symbols(repo_path, ref="HEAD", path="config.json")

        assert result["language"] == "json"
        assert result["symbols"] == []


@pytest.mark.asyncio
async def test_get_file_symbols_binary_file():
    """测试二进制文件无法提取符号"""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = os.path.join(tmpdir, "test_repo.git")
        os.makedirs(repo_path, exist_ok=True)
        repo = pygit2.init_repository(repo_path, bare=True)

        # 创建二进制文件
        binary_data = bytes([0x89, 0x50, 0x4E, 0x47])
        blob_oid = repo.create_blob(binary_data)

        tree_builder = repo.TreeBuilder()
        tree_builder.insert("image.png", blob_oid, pygit2.GIT_FILEMODE_BLOB)
        tree_oid = tree_builder.write()

        author = pygit2.Signature("Test", "test@example.com")
        commit_oid = repo.create_commit(
            None,
            author, author,
            "Add binary file",
            tree_oid,
            []
        )
        repo.create_reference("refs/heads/master", commit_oid)
        repo.set_head("refs/heads/master")

        result = await get_file_symbols(repo_path, ref="HEAD", path="image.png")

        assert result["language"] == "binary"
        assert result["symbols"] == []


@pytest.mark.asyncio
async def test_get_file_symbols_not_found():
    """测试获取不存在的文件符号"""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = create_test_repository_with_various_files(tmpdir)

        with pytest.raises(PathNotFoundException):
            await get_file_symbols(repo_path, ref="HEAD", path="non_existent.py")


@pytest.mark.asyncio
async def test_get_file_symbols_is_directory():
    """测试获取目录的符号"""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = create_test_repository_with_various_files(tmpdir)

        with pytest.raises(InvalidPathException) as exc_info:
            await get_file_symbols(repo_path, ref="HEAD", path="src")

        assert "is a directory" in str(exc_info.value)
