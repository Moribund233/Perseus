"""
PR Code Review API 集成测试

F-028: 逐行评论（含行级定位）
F-029: Review 状态流转（approve/changes_requested）
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from models.repository import Repository


def create_test_repo(db, owner_id: int, name: str = "test-repo") -> Repository:
    """创建测试仓库"""
    repo = Repository(
        name=name,
        path=f"testuser/{name}",
        description="Test repository",
        is_public=True,
        owner_id=owner_id,
        default_branch="main"
    )
    db.add(repo)
    db.commit()
    db.refresh(repo)
    return repo


def create_test_pr(db, repo_id: int, author_id: int, pr_number: int,
                   title: str, status: str = "open"):
    """创建测试 PR"""
    from models.pull_request import PullRequest
    pr = PullRequest(
        repository_id=repo_id,
        pr_number=pr_number,
        title=title,
        description=f"Description for {title}",
        source_branch="feature",
        target_branch="main",
        author_id=author_id,
        status=status
    )
    db.add(pr)
    db.commit()
    db.refresh(pr)
    return pr


# =============================================================================
# F-028: 逐行评论 API 测试
# =============================================================================

@pytest.mark.asyncio
async def test_create_pr_comment_api(
    test_client: TestClient, auth_headers: dict, db
):
    """
    测试创建 PR 评论 API

    验证点：
    1. 可以创建 PR 评论
    2. 返回正确的评论信息
    """
    repo = create_test_repo(db, owner_id=1)
    pr = create_test_pr(db, repo.id, author_id=1, pr_number=1, title="Test PR")

    response = test_client.post(
        f"/api/v1/repositories/{repo.id}/pull-requests/{pr.pr_number}/comments",
        json={
            "content": "This is a great PR!"
        },
        headers=auth_headers
    )

    assert response.status_code == 200, f"应该返回 200, 实际返回 {response.status_code}"
    data = response.json()
    assert data["content"] == "This is a great PR!"
    assert "author" in data

    print("✓ test_create_pr_comment_api 通过")


@pytest.mark.asyncio
async def test_create_inline_comment_api(
    test_client: TestClient, auth_headers: dict, db
):
    """
    测试创建行级评论 API

    验证点：
    1. 可以创建针对特定文件/行的评论
    2. 返回包含文件路径和行号的信息
    """
    repo = create_test_repo(db, owner_id=1)
    pr = create_test_pr(db, repo.id, author_id=1, pr_number=1, title="Test PR")

    response = test_client.post(
        f"/api/v1/repositories/{repo.id}/pull-requests/{pr.pr_number}/comments",
        json={
            "content": "This line needs refactoring",
            "file_path": "src/main.py",
            "line_number": 42,
            "commit_hash": "abc123def456"
        },
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["content"] == "This line needs refactoring"
    assert data["file_path"] == "src/main.py"
    assert data["line_number"] == 42
    assert data["commit_hash"] == "abc123def456"

    print("✓ test_create_inline_comment_api 通过")


@pytest.mark.asyncio
async def test_list_pr_comments_api(
    test_client: TestClient, auth_headers: dict, db
):
    """
    测试获取 PR 评论列表 API

    验证点：
    1. 可以获取 PR 的所有评论
    """
    repo = create_test_repo(db, owner_id=1)
    pr = create_test_pr(db, repo.id, author_id=1, pr_number=1, title="Test PR")

    # 创建两个评论
    for i in range(2):
        test_client.post(
            f"/api/v1/repositories/{repo.id}/pull-requests/{pr.pr_number}/comments",
            json={"content": f"Comment {i + 1}"},
            headers=auth_headers
        )

    # 获取列表
    response = test_client.get(
        f"/api/v1/repositories/{repo.id}/pull-requests/{pr.pr_number}/comments",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2

    print("✓ test_list_pr_comments_api 通过")


@pytest.mark.asyncio
async def test_create_pr_comment_empty_content(
    test_client: TestClient, auth_headers: dict, db
):
    """
    测试创建空内容的 PR 评论

    验证点：
    1. 空内容应该返回 400 错误
    """
    repo = create_test_repo(db, owner_id=1)
    pr = create_test_pr(db, repo.id, author_id=1, pr_number=1, title="Test PR")

    response = test_client.post(
        f"/api/v1/repositories/{repo.id}/pull-requests/{pr.pr_number}/comments",
        json={"content": ""},
        headers=auth_headers
    )

    assert response.status_code == 422, f"Pydantic 验证返回 422, 实际返回 {response.status_code}"

    print("✓ test_create_pr_comment_empty_content 通过")


@pytest.mark.asyncio
async def test_create_pr_comment_unauthorized(
    test_client: TestClient, db
):
    """
    测试未认证用户创建 PR 评论

    验证点：
    1. 未认证用户收到 401
    """
    repo = create_test_repo(db, owner_id=1)
    pr = create_test_pr(db, repo.id, author_id=1, pr_number=1, title="Test PR")

    response = test_client.post(
        f"/api/v1/repositories/{repo.id}/pull-requests/{pr.pr_number}/comments",
        json={"content": "Comment"}
    )

    assert response.status_code == 401

    print("✓ test_create_pr_comment_unauthorized 通过")


# =============================================================================
# F-029: Review 状态流转 API 测试
# =============================================================================

@pytest.mark.asyncio
async def test_approve_pr_review_api(
    test_client: TestClient, auth_headers: dict, db
):
    """
    测试 PR 审查批准 API

    验证点：
    1. 可以提交 approved 审查
    """
    repo = create_test_repo(db, owner_id=1)
    pr = create_test_pr(db, repo.id, author_id=1, pr_number=1, title="Test PR")

    response = test_client.post(
        f"/api/v1/repositories/{repo.id}/pull-requests/{pr.pr_number}/reviews",
        json={
            "status": "approved",
            "comment": "LGTM!"
        },
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "approved"
    assert data["comment"] == "LGTM!"

    print("✓ test_approve_pr_review_api 通过")


@pytest.mark.asyncio
async def test_request_changes_review_api(
    test_client: TestClient, auth_headers: dict, db
):
    """
    测试 PR 审查请求变更 API

    验证点：
    1. 可以提交 changes_requested 审查
    """
    repo = create_test_repo(db, owner_id=1)
    pr = create_test_pr(db, repo.id, author_id=1, pr_number=1, title="Test PR")

    response = test_client.post(
        f"/api/v1/repositories/{repo.id}/pull-requests/{pr.pr_number}/reviews",
        json={
            "status": "changes_requested",
            "comment": "Please fix the naming convention"
        },
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "changes_requested"
    assert data["comment"] == "Please fix the naming convention"

    print("✓ test_request_changes_review_api 通过")


@pytest.mark.asyncio
async def test_review_update_existing(
    test_client: TestClient, auth_headers: dict, db
):
    """
    测试更新已有审查（同用户再次审查）

    验证点：
    1. 同用户再次审查会更新已有记录而非新建
    """
    repo = create_test_repo(db, owner_id=1)
    pr = create_test_pr(db, repo.id, author_id=1, pr_number=1, title="Test PR")

    # 先提交 changes_requested
    test_client.post(
        f"/api/v1/repositories/{repo.id}/pull-requests/{pr.pr_number}/reviews",
        json={
            "status": "changes_requested",
            "comment": "Please fix"
        },
        headers=auth_headers
    )

    # 再次提交 approved（更新）
    response = test_client.post(
        f"/api/v1/repositories/{repo.id}/pull-requests/{pr.pr_number}/reviews",
        json={
            "status": "approved",
            "comment": "Looks good now"
        },
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "approved"
    assert data["comment"] == "Looks good now"

    print("✓ test_review_update_existing 通过")


@pytest.mark.asyncio
async def test_review_invalid_status(
    test_client: TestClient, auth_headers: dict, db
):
    """
    测试无效的审查状态

    验证点：
    1. 无效状态返回 400
    """
    repo = create_test_repo(db, owner_id=1)
    pr = create_test_pr(db, repo.id, author_id=1, pr_number=1, title="Test PR")

    response = test_client.post(
        f"/api/v1/repositories/{repo.id}/pull-requests/{pr.pr_number}/reviews",
        json={
            "status": "invalid_status",
            "comment": "test"
        },
        headers=auth_headers
    )

    assert response.status_code == 400

    print("✓ test_review_invalid_status 通过")


@pytest.mark.asyncio
async def test_review_unauthorized(
    test_client: TestClient, db
):
    """
    测试未认证用户提交审查

    验证点：
    1. 未认证用户收到 401
    """
    repo = create_test_repo(db, owner_id=1)
    pr = create_test_pr(db, repo.id, author_id=1, pr_number=1, title="Test PR")

    response = test_client.post(
        f"/api/v1/repositories/{repo.id}/pull-requests/{pr.pr_number}/reviews",
        json={
            "status": "approved",
            "comment": "LGTM"
        }
    )

    assert response.status_code == 401

    print("✓ test_review_unauthorized 通过")
