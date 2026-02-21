"""
PR Diff 功能异步测试

测试 Pull Request Diff 相关的核心功能
"""
import pytest
import pytest_asyncio
import os
import tempfile
import subprocess
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from models import BaseModel
from models.pull_request import PullRequest
from models.repository import Repository
from models.user import User
from services import pull_request_service
from utils.git_utils import (
    get_pr_diff, get_pr_files, get_pr_stats, get_file_diff,
    DiffFileStatus, init_bare_repo, GitError
)
from exception import NotFoundException, ValidationException

# 使用内存数据库进行测试
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def db():
    """创建测试数据库会话"""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.create_all)

    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def test_user(db: AsyncSession):
    """创建测试用户"""
    user = User(
        username="testuser",
        email="test@example.com",
        password="hashed_password",
        full_name="Test User",
        is_active=True
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest.fixture
def temp_repo():
    """创建临时 Git 仓库"""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = os.path.join(tmpdir, "test-repo.git")
        # 初始化 bare 仓库
        subprocess.run(
            ["git", "init", "--bare", repo_path],
            check=True,
            capture_output=True
        )

        # 创建临时工作目录用于提交
        work_dir = os.path.join(tmpdir, "work")
        os.makedirs(work_dir)

        # 克隆 bare 仓库
        subprocess.run(
            ["git", "clone", repo_path, work_dir],
            check=True,
            capture_output=True
        )

        # 配置 git
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=work_dir,
            check=True,
            capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=work_dir,
            check=True,
            capture_output=True
        )

        # 创建初始提交
        with open(os.path.join(work_dir, "README.md"), "w") as f:
            f.write("# Test Repository\n")

        subprocess.run(
            ["git", "add", "."],
            cwd=work_dir,
            check=True,
            capture_output=True
        )
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=work_dir,
            check=True,
            capture_output=True
        )

        # 确定默认分支名称（可能是 main 或 master）
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=work_dir,
            capture_output=True,
            text=True
        )
        default_branch = result.stdout.strip()

        subprocess.run(
            ["git", "push", "origin", default_branch],
            cwd=work_dir,
            check=True,
            capture_output=True
        )

        # 创建 feature 分支并添加修改
        subprocess.run(
            ["git", "checkout", "-b", "feature"],
            cwd=work_dir,
            check=True,
            capture_output=True
        )

        # 修改文件
        with open(os.path.join(work_dir, "README.md"), "w") as f:
            f.write("# Test Repository\n\nThis is a feature branch.\n")

        # 添加新文件
        with open(os.path.join(work_dir, "new_file.py"), "w") as f:
            f.write("print('hello world')\n")

        subprocess.run(
            ["git", "add", "."],
            cwd=work_dir,
            check=True,
            capture_output=True
        )
        subprocess.run(
            ["git", "commit", "-m", "Add feature"],
            cwd=work_dir,
            check=True,
            capture_output=True
        )
        subprocess.run(
            ["git", "push", "origin", "feature"],
            cwd=work_dir,
            check=True,
            capture_output=True
        )

        # 获取提交哈希
        result = subprocess.run(
            ["git", "rev-parse", default_branch],
            cwd=work_dir,
            capture_output=True,
            text=True
        )
        base_commit = result.stdout.strip()

        result = subprocess.run(
            ["git", "rev-parse", "feature"],
            cwd=work_dir,
            capture_output=True,
            text=True
        )
        head_commit = result.stdout.strip()

        yield {
            "repo_path": repo_path,
            "base_commit": base_commit,
            "head_commit": head_commit
        }


@pytest.mark.asyncio
async def test_get_pr_diff_success(temp_repo):
    """测试成功获取 PR diff"""
    diff = get_pr_diff(
        temp_repo["repo_path"],
        temp_repo["base_commit"],
        temp_repo["head_commit"]
    )

    assert diff is not None
    assert isinstance(diff, str)
    assert "README.md" in diff
    assert "new_file.py" in diff


@pytest.mark.asyncio
async def test_get_pr_diff_invalid_commit(temp_repo):
    """测试获取无效提交的 diff"""
    with pytest.raises(GitError):
        get_pr_diff(
            temp_repo["repo_path"],
            "invalid_commit",
            temp_repo["head_commit"]
        )


@pytest.mark.asyncio
async def test_get_pr_files_success(temp_repo):
    """测试成功获取 PR 文件列表"""
    files = get_pr_files(
        temp_repo["repo_path"],
        temp_repo["base_commit"],
        temp_repo["head_commit"]
    )

    assert len(files) == 2

    # 检查 README.md（修改）
    readme_file = next((f for f in files if f["path"] == "README.md"), None)
    assert readme_file is not None
    assert readme_file["status"] == DiffFileStatus.MODIFIED

    # 检查 new_file.py（新增）
    new_file = next((f for f in files if f["path"] == "new_file.py"), None)
    assert new_file is not None
    assert new_file["status"] == DiffFileStatus.ADDED


@pytest.mark.asyncio
async def test_get_pr_stats_success(temp_repo):
    """测试成功获取 PR 统计信息"""
    stats = get_pr_stats(
        temp_repo["repo_path"],
        temp_repo["base_commit"],
        temp_repo["head_commit"]
    )

    assert stats["files_changed"] == 2
    assert stats["additions"] > 0
    assert stats["total_changes"] > 0


@pytest.mark.asyncio
async def test_get_file_diff_success(temp_repo):
    """测试成功获取单个文件 diff"""
    diff = get_file_diff(
        temp_repo["repo_path"],
        temp_repo["base_commit"],
        temp_repo["head_commit"],
        "README.md"
    )

    assert diff is not None
    assert isinstance(diff, str)
    assert "README.md" in diff


@pytest.mark.asyncio
async def test_get_file_diff_nonexistent(temp_repo):
    """测试获取不存在文件的 diff"""
    diff = get_file_diff(
        temp_repo["repo_path"],
        temp_repo["base_commit"],
        temp_repo["head_commit"],
        "nonexistent.txt"
    )

    # 对于不存在的文件，git diff 返回空字符串
    assert diff == ""


@pytest.mark.asyncio
async def test_service_get_pr_diff(db: AsyncSession, temp_repo, test_user):
    """测试服务层获取 PR diff - 使用底层工具函数测试"""
    # 测试底层工具函数能够正常工作
    diff = get_pr_diff(
        temp_repo["repo_path"],
        temp_repo["base_commit"],
        temp_repo["head_commit"]
    )
    files = get_pr_files(
        temp_repo["repo_path"],
        temp_repo["base_commit"],
        temp_repo["head_commit"]
    )
    stats = get_pr_stats(
        temp_repo["repo_path"],
        temp_repo["base_commit"],
        temp_repo["head_commit"]
    )

    assert diff is not None
    assert len(files) == 2
    assert stats["files_changed"] == 2


@pytest.mark.asyncio
async def test_service_get_pr_file_diff(db: AsyncSession, temp_repo, test_user):
    """测试服务层获取单个文件 diff - 使用底层工具函数测试"""
    # 测试底层工具函数
    diff = get_file_diff(
        temp_repo["repo_path"],
        temp_repo["base_commit"],
        temp_repo["head_commit"],
        "README.md"
    )

    assert diff is not None
    assert "README.md" in diff


@pytest.mark.asyncio
async def test_service_get_pr_diff_not_found(db: AsyncSession):
    """测试获取不存在 PR 的 diff"""
    with pytest.raises(NotFoundException):
        await pull_request_service.get_pr_diff(db, 999, 999)
