"""
Pull Request Service 异步测试

测试 Pull Request 服务层的所有功能
"""
import pytest
import pytest_asyncio
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from models.pull_request import PullRequest, PRComment, PRReview
from services import pull_request_service
from core.exception import NotFoundException, ValidationException
from utils.git_utils import get_repository_storage_path


@pytest_asyncio.fixture
async def test_pr(async_db: AsyncSession, async_test_repo, async_test_user):
    """创建测试 Pull Request"""
    pr = PullRequest(
        repository_id=async_test_repo.id,
        pr_number=1,
        title="Test PR",
        description="This is a test PR",
        source_branch="feature",
        target_branch="main",
        author_id=async_test_user.id,
        status="open"
    )
    async_db.add(pr)
    await async_db.commit()
    await async_db.refresh(pr)
    return pr


@pytest.mark.asyncio
async def test_list_pull_requests(async_db: AsyncSession, async_test_repo, test_pr: PullRequest):
    """测试获取 PR 列表"""
    result = await pull_request_service.list_pull_requests(async_db, async_test_repo.id)
    assert result["total"] == 1
    assert len(result["items"]) == 1
    assert result["items"][0]["title"] == test_pr.title


@pytest.mark.asyncio
async def test_list_pull_requests_with_status_filter(async_db: AsyncSession, async_test_repo, test_pr: PullRequest):
    """测试按状态过滤 PR"""
    result = await pull_request_service.list_pull_requests(async_db, async_test_repo.id, status="open")
    assert result["total"] == 1

    result = await pull_request_service.list_pull_requests(async_db, async_test_repo.id, status="closed")
    assert result["total"] == 0


@pytest.mark.asyncio
async def test_get_pull_request(async_db: AsyncSession, async_test_repo, test_pr: PullRequest):
    """测试获取 PR 详情"""
    pr = await pull_request_service.get_pull_request(async_db, async_test_repo.id, test_pr.pr_number)
    assert pr["title"] == test_pr.title
    assert pr["status"] == test_pr.status


@pytest.mark.asyncio
async def test_get_pull_request_not_found(async_db: AsyncSession, async_test_repo):
    """测试获取不存在的 PR"""
    with pytest.raises(NotFoundException):
        await pull_request_service.get_pull_request(async_db, async_test_repo.id, 999)


@pytest.mark.asyncio
async def test_create_pull_request(async_db: AsyncSession, async_test_repo, async_test_user):
    """测试创建 PR"""
    pr = await pull_request_service.create_pull_request(
        async_db, async_test_repo.id, async_test_user.id,
        title="New PR",
        description="New description",
        source_branch="feature-branch",
        target_branch="main"
    )
    assert pr["title"] == "New PR"
    assert pr["status"] == "open"
    assert pr["source_branch"] == "feature-branch"
    assert pr["target_branch"] == "main"


@pytest.mark.asyncio
async def test_create_pull_request_empty_title(async_db: AsyncSession, async_test_repo, async_test_user):
    """测试创建 PR 空标题"""
    with pytest.raises(ValidationException):
        await pull_request_service.create_pull_request(
            async_db, async_test_repo.id, async_test_user.id,
            title="",
            description="Description",
            source_branch="feature",
            target_branch="main"
        )


@pytest.mark.asyncio
async def test_create_pull_request_same_branches(async_db: AsyncSession, async_test_repo, async_test_user):
    """测试创建 PR 相同分支"""
    with pytest.raises(ValidationException):
        await pull_request_service.create_pull_request(
            async_db, async_test_repo.id, async_test_user.id,
            title="New PR",
            description="Description",
            source_branch="main",
            target_branch="main"
        )


@pytest.mark.asyncio
async def test_update_pull_request(async_db: AsyncSession, async_test_repo, test_pr: PullRequest, async_test_user):
    """测试更新 PR"""
    updated = await pull_request_service.update_pull_request(
        async_db, async_test_repo.id, test_pr.pr_number, async_test_user.id,
        title="Updated Title",
        description="Updated description"
    )
    assert updated["title"] == "Updated Title"
    assert updated["description"] == "Updated description"


@pytest.mark.asyncio
async def test_update_pull_request_not_found(async_db: AsyncSession, async_test_repo, async_test_user):
    """测试更新不存在的 PR"""
    with pytest.raises(NotFoundException):
        await pull_request_service.update_pull_request(
            async_db, async_test_repo.id, 999, async_test_user.id,
            title="Updated Title"
        )


@pytest.mark.asyncio
async def test_close_pull_request(async_db: AsyncSession, async_test_repo, test_pr: PullRequest, async_test_user):
    """测试关闭 PR"""
    closed = await pull_request_service.close_pull_request(
        async_db, async_test_repo.id, test_pr.pr_number, async_test_user.id
    )
    assert closed["status"] == "closed"


@pytest.mark.asyncio
async def test_close_pull_request_already_closed(async_db: AsyncSession, async_test_repo, test_pr: PullRequest, async_test_user):
    """测试关闭已关闭的 PR"""
    await pull_request_service.close_pull_request(async_db, async_test_repo.id, test_pr.pr_number, async_test_user.id)
    with pytest.raises(ValidationException):
        await pull_request_service.close_pull_request(async_db, async_test_repo.id, test_pr.pr_number, async_test_user.id)


@pytest.mark.asyncio
async def test_create_pr_comment(async_db: AsyncSession, async_test_repo, test_pr: PullRequest, async_test_user):
    """测试添加 PR 评论"""
    comment = await pull_request_service.create_pr_comment(
        async_db, async_test_repo.id, test_pr.pr_number, async_test_user.id,
        content="This is a PR comment"
    )
    assert comment["content"] == "This is a PR comment"


@pytest.mark.asyncio
async def test_create_pr_comment_empty_content(async_db: AsyncSession, async_test_repo, test_pr: PullRequest, async_test_user):
    """测试添加空内容评论"""
    with pytest.raises(ValidationException):
        await pull_request_service.create_pr_comment(
            async_db, async_test_repo.id, test_pr.pr_number, async_test_user.id,
            content=""
        )


@pytest.mark.asyncio
async def test_create_pr_review_approved(async_db: AsyncSession, async_test_repo, test_pr: PullRequest, async_test_user):
    """测试创建批准审查"""
    review = await pull_request_service.create_pr_review(
        async_db, async_test_repo.id, test_pr.pr_number, async_test_user.id,
        status="approved",
        comment="LGTM"
    )
    assert review["status"] == "approved"
    assert review["comment"] == "LGTM"


@pytest.mark.asyncio
async def test_create_pr_review_changes_requested(async_db: AsyncSession, async_test_repo, test_pr: PullRequest, async_test_user):
    """测试创建请求修改审查"""
    review = await pull_request_service.create_pr_review(
        async_db, async_test_repo.id, test_pr.pr_number, async_test_user.id,
        status="changes_requested",
        comment="Please fix this"
    )
    assert review["status"] == "changes_requested"


@pytest.mark.asyncio
async def test_create_pr_review_invalid_status(async_db: AsyncSession, async_test_repo, test_pr: PullRequest, async_test_user):
    """测试创建无效状态审查"""
    with pytest.raises(ValidationException):
        await pull_request_service.create_pr_review(
            async_db, async_test_repo.id, test_pr.pr_number, async_test_user.id,
            status="invalid_status"
        )


@pytest.mark.asyncio
async def test_list_pr_comments(async_db: AsyncSession, async_test_repo, test_pr: PullRequest, async_test_user):
    """测试获取 PR 评论列表"""
    # 添加评论
    await pull_request_service.create_pr_comment(
        async_db, async_test_repo.id, test_pr.pr_number, async_test_user.id,
        content="Comment 1"
    )
    await pull_request_service.create_pr_comment(
        async_db, async_test_repo.id, test_pr.pr_number, async_test_user.id,
        content="Comment 2"
    )

    comments = await pull_request_service.list_pr_comments(async_db, async_test_repo.id, test_pr.pr_number)
    assert len(comments) == 2


# =============================================================================
# F-013: git merge 操作测试
# =============================================================================

@pytest_asyncio.fixture
async def test_repo_with_git(async_db: AsyncSession, async_test_user):
    """
    创建带有物理 Git 仓库的测试仓库

    创建一个实际的 bare 仓库，用于测试 git merge 操作
    """
    import tempfile
    import os
    import subprocess

    from models.repository import Repository
    from utils.git_utils import get_repository_storage_path

    # 创建临时目录作为仓库根目录
    temp_dir = tempfile.mkdtemp()

    # 创建仓库记录
    repo = Repository(
        name="test-merge-repo",
        description="Test repository for merge",
        owner_id=async_test_user.id,
        is_public=True,
        path=f"{async_test_user.username}/test-merge-repo"
    )
    async_db.add(repo)
    await async_db.commit()
    await async_db.refresh(repo)

    # 创建物理 bare 仓库（使用临时目录覆盖默认 repo_root）
    logical_path = repo.path
    repo_path = get_repository_storage_path(logical_path, repo_root=temp_dir)
    os.makedirs(os.path.dirname(repo_path), exist_ok=True)

    # 初始化 bare 仓库，使用 main 作为默认分支
    subprocess.run(
        ["git", "init", "--bare", "--initial-branch=main", repo_path],
        check=True, capture_output=True
    )

    # 创建一个非 bare 的克隆用于添加提交
    clone_path = os.path.join(temp_dir, "clone")
    subprocess.run(
        ["git", "clone", repo_path, clone_path],
        check=True, capture_output=True
    )

    # 配置 git
    subprocess.run(
        ["git", "-C", clone_path, "config", "user.email", "test@example.com"],
        check=True, capture_output=True
    )
    subprocess.run(
        ["git", "-C", clone_path, "config", "user.name", "Test User"],
        check=True, capture_output=True
    )

    # 创建初始提交到 main 分支
    with open(os.path.join(clone_path, "README.md"), "w") as f:
        f.write("# Test Repository\n")
    subprocess.run(["git", "-C", clone_path, "add", "."], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", clone_path, "commit", "-m", "Initial commit"],
        check=True, capture_output=True
    )
    subprocess.run(["git", "-C", clone_path, "push", "origin", "main"], check=True, capture_output=True)

    # 创建 feature 分支并添加提交
    subprocess.run(
        ["git", "-C", clone_path, "checkout", "-b", "feature"],
        check=True, capture_output=True
    )
    with open(os.path.join(clone_path, "feature.txt"), "w") as f:
        f.write("Feature content\n")
    subprocess.run(["git", "-C", clone_path, "add", "."], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", clone_path, "commit", "-m", "Add feature"],
        check=True, capture_output=True
    )
    subprocess.run(["git", "-C", clone_path, "push", "origin", "feature"], check=True, capture_output=True)

    # 保持 repo.path 为逻辑路径，同时将 GitService.from_repository_id 重定向到临时目录
    # 通过 monkey-patch get_repository_storage_path 的 repo_root 或修改 config
    from core.config import get_config
    config = get_config()
    original_repo_root = config.storage.repo_root
    config.storage.repo_root = temp_dir

    yield repo

    # 恢复原始配置
    config.storage.repo_root = original_repo_root
    # 清理临时目录
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_merge_pr_performs_git_merge(async_db: AsyncSession, test_repo_with_git, async_test_user):
    """
    测试 PR 合并执行实际的 git merge 操作

    验证点：
    1. PR 合并后状态变为 merged
    2. 目标分支包含源分支的提交
    3. 合并提交被正确创建
    4. PR 记录包含合并提交哈希
    """
    import tempfile
    import os
    import subprocess

    from services import pull_request_service
    from utils.git_utils import GitService

    repo = test_repo_with_git

    # 创建 PR
    pr = await pull_request_service.create_pull_request(
        async_db, repo.id, async_test_user.id,
        title="Test Merge PR",
        description="This PR should be merged",
        source_branch="feature",
        target_branch="main"
    )
    assert pr["status"] == "open"
    pr_number = pr["pr_number"]

    # 使用 GitService 检查合并前的状态
    git_service = GitService(get_repository_storage_path(repo.path))

    # 验证 feature 分支存在且有提交
    assert git_service.branch_exists("feature"), "feature 分支应该存在"
    assert git_service.branch_exists("main"), "main 分支应该存在"

    # 获取合并前的 main 分支提交数
    main_commit_before = git_service.get_branch_commit("main")
    assert main_commit_before is not None, "main 分支应该有提交"

    # 执行 PR 合并
    merged_pr = await pull_request_service.merge_pull_request(
        async_db, repo.id, pr_number, async_test_user.id, merge_method="merge"
    )

    # 验证 PR 状态
    assert merged_pr["status"] == "merged", "PR 状态应该变为 merged"
    # merged_by 可能是用户对象或 ID
    merged_by_id = merged_pr["merged_by"]["id"] if isinstance(merged_pr["merged_by"], dict) else merged_pr["merged_by"]
    assert merged_by_id == async_test_user.id, "merged_by 应该设置为合并者"
    assert merged_pr["merged_commit_hash"] is not None, "应该有合并提交哈希"

    # 验证目标分支现在包含源分支的更改
    # 重新加载 GitService（因为仓库已更改）
    git_service = GitService(get_repository_storage_path(repo.path))
    main_commit_after = git_service.get_branch_commit("main")

    # main 分支应该有新的提交（合并提交）
    assert str(main_commit_after.id) != str(main_commit_before.id), \
        "main 分支应该有新的提交"

    # 验证合并提交有两个父提交（合并提交的特征）
    assert len(main_commit_after.parents) == 2, \
        "合并提交应该有两个父提交"

    print("✓ test_merge_pr_performs_git_merge 通过")


@pytest.mark.asyncio
async def test_squash_merge_creates_single_commit(async_db: AsyncSession, test_repo_with_git, async_test_user):
    """
    测试 squash merge 创建单个提交

    验证点：
    1. 使用 squash 方式合并 PR
    2. 目标分支只有一个新的提交（而不是多个）
    3. 新的提交只有一个父提交（不是合并提交）
    4. PR 状态正确更新
    """
    from services import pull_request_service
    from utils.git_utils import GitService

    repo = test_repo_with_git

    # 创建 PR
    pr = await pull_request_service.create_pull_request(
        async_db, repo.id, async_test_user.id,
        title="Test Squash Merge PR",
        description="This PR should be squash merged",
        source_branch="feature",
        target_branch="main"
    )
    assert pr["status"] == "open"
    pr_number = pr["pr_number"]

    # 使用 GitService 检查合并前的状态
    git_service = GitService(get_repository_storage_path(repo.path))

    # 获取合并前的 main 分支提交
    main_commit_before = git_service.get_branch_commit("main")
    assert main_commit_before is not None, "main 分支应该有提交"

    # 执行 squash merge
    merged_pr = await pull_request_service.merge_pull_request(
        async_db, repo.id, pr_number, async_test_user.id, merge_method="squash"
    )

    # 验证 PR 状态
    assert merged_pr["status"] == "merged", "PR 状态应该变为 merged"
    assert merged_pr["merged_commit_hash"] is not None, "应该有合并提交哈希"

    # 验证目标分支有新的提交
    git_service = GitService(get_repository_storage_path(repo.path))
    main_commit_after = git_service.get_branch_commit("main")

    # main 分支应该有新的提交
    assert str(main_commit_after.id) != str(main_commit_before.id), \
        "main 分支应该有新的提交"

    # 验证 squash 提交只有一个父提交（不是合并提交）
    assert len(main_commit_after.parents) == 1, \
        "squash 提交应该只有一个父提交"

    # 验证提交信息包含 PR 信息
    assert "Test Squash Merge PR" in main_commit_after.message, \
        "squash 提交信息应该包含 PR 标题"

    print("✓ test_squash_merge_creates_single_commit 通过")


@pytest.mark.asyncio
async def test_rebase_merge_replays_commits(async_db: AsyncSession, test_repo_with_git, async_test_user):
    """
    测试 rebase merge 重放提交

    验证点：
    1. 使用 rebase 方式合并 PR
    2. 源分支的提交被逐个重放到目标分支
    3. 每个提交的父提交是目标分支的前一个提交
    4. PR 状态正确更新
    """
    from services import pull_request_service
    from utils.git_utils import GitService

    repo = test_repo_with_git

    # 创建 PR
    pr = await pull_request_service.create_pull_request(
        async_db, repo.id, async_test_user.id,
        title="Test Rebase Merge PR",
        description="This PR should be rebase merged",
        source_branch="feature",
        target_branch="main"
    )
    assert pr["status"] == "open"
    pr_number = pr["pr_number"]

    # 使用 GitService 检查合并前的状态
    git_service = GitService(get_repository_storage_path(repo.path))

    # 获取合并前的 main 分支提交
    main_commit_before = git_service.get_branch_commit("main")
    assert main_commit_before is not None, "main 分支应该有提交"

    # 执行 rebase merge
    merged_pr = await pull_request_service.merge_pull_request(
        async_db, repo.id, pr_number, async_test_user.id, merge_method="rebase"
    )

    # 验证 PR 状态
    assert merged_pr["status"] == "merged", "PR 状态应该变为 merged"
    assert merged_pr["merged_commit_hash"] is not None, "应该有合并提交哈希"

    # 验证目标分支有新的提交
    git_service = GitService(get_repository_storage_path(repo.path))
    main_commit_after = git_service.get_branch_commit("main")

    # main 分支应该有新的提交
    assert str(main_commit_after.id) != str(main_commit_before.id), \
        "main 分支应该有新的提交"

    # 验证 rebase 后的提交只有一个父提交（不是合并提交）
    assert len(main_commit_after.parents) == 1, \
        "rebase 后的提交应该只有一个父提交"

    # 验证提交信息是源分支的提交信息（不是合并提交信息）
    assert "Add feature" in main_commit_after.message, \
        "rebase 提交信息应该是源分支的提交信息"

    print("✓ test_rebase_merge_replays_commits 通过")


@pytest_asyncio.fixture
async def test_repo_with_conflict(async_db: AsyncSession, async_test_user):
    """创建带有合并冲突的测试仓库"""
    import tempfile
    import os
    import subprocess
    from models.repository import Repository

    temp_dir = tempfile.mkdtemp()

    # 创建仓库记录
    repo = Repository(
        name="test-conflict-repo",
        description="Test repository for merge conflicts",
        owner_id=async_test_user.id,
        is_public=True,
        path=f"{async_test_user.username}/test-conflict-repo"
    )
    async_db.add(repo)
    await async_db.commit()
    await async_db.refresh(repo)

    # 创建物理 bare 仓库（使用临时目录覆盖默认 repo_root）
    repo_path = get_repository_storage_path(repo.path, repo_root=temp_dir)
    os.makedirs(os.path.dirname(repo_path), exist_ok=True)

    # 初始化 bare 仓库
    subprocess.run(
        ["git", "init", "--bare", "--initial-branch=main", repo_path],
        check=True, capture_output=True
    )

    # 创建克隆
    clone_path = os.path.join(temp_dir, "clone")
    subprocess.run(["git", "clone", repo_path, clone_path], check=True, capture_output=True)

    # 配置用户
    subprocess.run(["git", "-C", clone_path, "config", "user.email", "test@example.com"], check=True)
    subprocess.run(["git", "-C", clone_path, "config", "user.name", "Test User"], check=True)

    # 创建初始文件并提交
    with open(os.path.join(clone_path, "README.md"), "w") as f:
        f.write("# Test Repository\n\nInitial content\n")
    subprocess.run(["git", "-C", clone_path, "add", "."], check=True)
    subprocess.run(["git", "-C", clone_path, "commit", "-m", "Initial commit"], check=True)
    subprocess.run(["git", "-C", clone_path, "push", "origin", "main"], check=True)

    # 创建 feature 分支并修改同一文件
    subprocess.run(["git", "-C", clone_path, "checkout", "-b", "feature"], check=True)
    with open(os.path.join(clone_path, "README.md"), "w") as f:
        f.write("# Test Repository\n\nFeature branch content\n")  # 修改同一行
    subprocess.run(["git", "-C", clone_path, "add", "."], check=True)
    subprocess.run(["git", "-C", clone_path, "commit", "-m", "Feature change"], check=True)
    subprocess.run(["git", "-C", clone_path, "push", "origin", "feature"], check=True)

    # 回到 main 分支并修改同一文件（制造冲突）
    subprocess.run(["git", "-C", clone_path, "checkout", "main"], check=True)
    with open(os.path.join(clone_path, "README.md"), "w") as f:
        f.write("# Test Repository\n\nMain branch content\n")  # 修改同一行
    subprocess.run(["git", "-C", clone_path, "add", "."], check=True)
    subprocess.run(["git", "-C", clone_path, "commit", "-m", "Main change"], check=True)
    subprocess.run(["git", "-C", clone_path, "push", "origin", "main"], check=True)

    # 保持 repo.path 为逻辑路径，同时重定向 GitService 到临时目录
    from core.config import get_config
    config = get_config()
    original_repo_root = config.storage.repo_root
    config.storage.repo_root = temp_dir

    yield repo

    # 恢复原始配置
    config.storage.repo_root = original_repo_root
    # 清理
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_detect_merge_conflict(async_db: AsyncSession, test_repo_with_conflict, async_test_user):
    """
    测试合并冲突检测

    验证点：
    1. 创建有冲突的 PR
    2. 尝试合并时应该检测到冲突
    3. 抛出 ValidationException 并提示冲突
    4. PR 状态保持 open
    """
    from services import pull_request_service
    from core.exception import ValidationException

    repo = test_repo_with_conflict

    # 创建 PR
    pr = await pull_request_service.create_pull_request(
        async_db, repo.id, async_test_user.id,
        title="Test Conflict PR",
        description="This PR has conflicts",
        source_branch="feature",
        target_branch="main"
    )
    assert pr["status"] == "open"
    pr_number = pr["pr_number"]

    # 尝试合并应该抛出冲突异常
    with pytest.raises(ValidationException) as exc_info:
        await pull_request_service.merge_pull_request(
            async_db, repo.id, pr_number, async_test_user.id, merge_method="merge"
        )

    # 验证错误信息包含冲突提示
    assert "conflict" in str(exc_info.value).lower(), \
        "错误信息应该包含冲突提示"

    # 验证 PR 状态仍然是 open
    pr_after = await pull_request_service.get_pull_request(async_db, repo.id, pr_number)
    assert pr_after["status"] == "open", "PR 状态应该保持 open"

    print("✓ test_detect_merge_conflict 通过")


# =============================================================================
# F-046: PR 合并后自动创建 CI Build 记录
# =============================================================================

@pytest.mark.asyncio
async def test_merge_pr_creates_build_record(async_db: AsyncSession, test_repo_with_git, async_test_user):
    """
    测试 PR 合并后自动创建 Build 记录

    验证点：
    1. PR 合并成功
    2. 仓库对应的 Build 记录数量从 0 变为 1
    3. Build 状态为 pending
    """
    from services import pull_request_service
    from services.build_service import BuildService

    repo = test_repo_with_git

    # 合并前没有 Build 记录
    builds_before = await BuildService.get_builds_for_repository(async_db, repo.id)
    assert len(builds_before) == 0, "合并前不应该有 Build 记录"

    # 创建并合并 PR
    pr = await pull_request_service.create_pull_request(
        async_db, repo.id, async_test_user.id,
        title="Build Trigger PR",
        description="This PR should trigger a build",
        source_branch="feature",
        target_branch="main"
    )

    await pull_request_service.merge_pull_request(
        async_db, repo.id, pr["pr_number"], async_test_user.id, merge_method="merge"
    )

    # 验证 Build 记录已创建
    builds_after = await BuildService.get_builds_for_repository(async_db, repo.id)
    assert len(builds_after) == 1, "合并后应该自动创建一个 Build 记录"
    build = builds_after[0]
    assert build.status == "pending", "Build 初始状态应为 pending"
    assert build.branch == "main", "Build 分支应为目标分支 main"
    assert build.repo_id == repo.id, "Build 应关联到正确仓库"

    print("✓ test_merge_pr_creates_build_record 通过")


# =============================================================================
# F-039: PR 合并后重建搜索索引
# =============================================================================

@pytest.mark.asyncio
async def test_merge_pr_rebuilds_search_index(async_db: AsyncSession, test_repo_with_git, async_test_user):
    """
    测试 PR 合并后自动重建搜索索引

    验证点：
    1. PR 合并成功
    2. 仓库物理路径下生成 .perseus_search_index 目录
    """
    import os
    from services import pull_request_service
    from services.search_service import SearchService
    from utils.git_utils import get_repository_storage_path

    repo = test_repo_with_git

    # 创建并合并 PR
    pr = await pull_request_service.create_pull_request(
        async_db, repo.id, async_test_user.id,
        title="Search Index PR",
        description="This PR should rebuild search index",
        source_branch="feature",
        target_branch="main"
    )

    await pull_request_service.merge_pull_request(
        async_db, repo.id, pr["pr_number"], async_test_user.id, merge_method="merge"
    )

    # 验证搜索索引目录已创建
    repo_path = get_repository_storage_path(repo.path)
    index_path = os.path.join(repo_path, ".perseus_search_index")
    assert os.path.exists(index_path), "合并后应创建搜索索引目录"

    # 验证索引文件已生成
    index_db_path = os.path.join(index_path, "fts.db")
    assert os.path.exists(index_db_path), "搜索索引数据库文件应存在"

    print("✓ test_merge_pr_rebuilds_search_index 通过")
