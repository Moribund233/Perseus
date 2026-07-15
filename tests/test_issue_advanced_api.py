"""
Issue 高级功能 API 集成测试

F-025: Issue 高级筛选
F-027: Issue 批量操作
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.test_helpers import create_test_repo, create_test_issue


# =============================================================================
# F-025: Issue 高级筛选 API 测试
# =============================================================================

@pytest.mark.asyncio
async def test_filter_issues_api_basic(
    test_client: TestClient, auth_headers: dict, db
):
    """
    测试高级筛选 API 基本功能

    验证点：
    1. 可以按多个条件筛选 Issue
    2. 返回符合条件的结果
    """
    repo = create_test_repo(db)

    # 创建测试数据
    for i in range(5):
        status = "open" if i < 3 else "closed"
        priority = "high" if i % 2 == 0 else "low"
        create_test_issue(db, repo.id, issue_number=i + 1,
                          title=f"Issue {i + 1}", status=status, priority=priority)

    # 按状态筛选
    response = test_client.post(
        f"/api/v1/repositories/{repo.id}/issues/filter",
        json={
            "statuses": ["open"]
        },
        headers=auth_headers
    )
    assert response.status_code == 200, f"应该返回 200, 实际返回 {response.status_code}"
    data = response.json()
    assert data["total"] == 3
    for item in data["items"]:
        assert item["status"] == "open"

    print("✓ test_filter_issues_api_basic 通过")


@pytest.mark.asyncio
async def test_filter_issues_api_multi_criteria(
    test_client: TestClient, auth_headers: dict, db
):
    """
    测试高级筛选 API 多条件组合

    验证点：
    1. 可以按状态 + 优先级组合筛选
    """
    repo = create_test_repo(db)

    # 创建测试数据
    for i in range(5):
        status = "open" if i < 4 else "closed"
        priority = "high" if i % 2 == 0 else "low"
        create_test_issue(db, repo.id, issue_number=i + 1,
                          title=f"Issue {i + 1}", status=status, priority=priority)

    # 按状态 + 优先级组合筛选
    response = test_client.post(
        f"/api/v1/repositories/{repo.id}/issues/filter",
        json={
            "statuses": ["open"],
            "priorities": ["high"]
        },
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    # open 且 high 的有 2 个（issue 1, 3）
    assert data["total"] == 2

    print("✓ test_filter_issues_api_multi_criteria 通过")


@pytest.mark.asyncio
async def test_filter_issues_api_search(
    test_client: TestClient, auth_headers: dict, db
):
    """
    测试高级筛选 API 搜索功能

    验证点：
    1. 可以按关键词搜索标题和描述
    """
    repo = create_test_repo(db)

    create_test_issue(db, repo.id, issue_number=1,
                      title="Bug: Login fails")
    create_test_issue(db, repo.id, issue_number=2,
                      title="Feature: Add dark mode")

    response = test_client.post(
        f"/api/v1/repositories/{repo.id}/issues/filter",
        json={
            "search": "Login"
        },
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert "Login" in data["items"][0]["title"]

    print("✓ test_filter_issues_api_search 通过")


@pytest.mark.asyncio
async def test_filter_issues_api_sort_by_priority(
    test_client: TestClient, auth_headers: dict, db
):
    """
    测试高级筛选 API 按优先级排序

    验证点：
    1. 可以按优先级排序
    """
    repo = create_test_repo(db)

    create_test_issue(db, repo.id, issue_number=1,
                      title="Low priority", priority="low")
    create_test_issue(db, repo.id, issue_number=2,
                      title="Critical", priority="critical")
    create_test_issue(db, repo.id, issue_number=3,
                      title="High priority", priority="high")

    response = test_client.post(
        f"/api/v1/repositories/{repo.id}/issues/filter?sort_by=priority&sort_order=desc",
        json={},
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    # 按优先级降序：critical > high > low
    assert data["items"][0]["priority"] == "critical"
    assert data["items"][1]["priority"] == "high"
    assert data["items"][2]["priority"] == "low"

    print("✓ test_filter_issues_api_sort_by_priority 通过")


# =============================================================================
# F-027: Issue 批量操作 API 测试
# =============================================================================

@pytest.mark.asyncio
async def test_batch_close_issues_api(
    test_client: TestClient, auth_headers: dict, db
):
    """
    测试批量关闭 Issue API

    验证点：
    1. 可以批量关闭多个 Issue
    """
    repo = create_test_repo(db)

    create_test_issue(db, repo.id, issue_number=1, title="Issue 1")
    create_test_issue(db, repo.id, issue_number=2, title="Issue 2")
    create_test_issue(db, repo.id, issue_number=3, title="Issue 3")

    response = test_client.post(
        f"/api/v1/repositories/{repo.id}/issues/batch/close",
        json={
            "issue_numbers": [1, 2]
        },
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["closed_count"] == 2

    print("✓ test_batch_close_issues_api 通过")


@pytest.mark.asyncio
async def test_batch_reopen_issues_api(
    test_client: TestClient, auth_headers: dict, db
):
    """
    测试批量重新打开 Issue API

    验证点：
    1. 可以批量重新打开多个 Issue
    """
    repo = create_test_repo(db)

    create_test_issue(db, repo.id, issue_number=1,
                      title="Issue 1", status="closed")
    create_test_issue(db, repo.id, issue_number=2,
                      title="Issue 2", status="closed")

    response = test_client.post(
        f"/api/v1/repositories/{repo.id}/issues/batch/reopen",
        json={
            "issue_numbers": [1, 2]
        },
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["reopened_count"] == 2

    print("✓ test_batch_reopen_issues_api 通过")


@pytest.mark.asyncio
async def test_batch_update_issues_api(
    test_client: TestClient, auth_headers: dict, db
):
    """
    测试批量更新 Issue API

    验证点：
    1. 可以批量更新 Issue 的优先级
    """
    repo = create_test_repo(db)

    create_test_issue(db, repo.id, issue_number=1, title="Issue 1")
    create_test_issue(db, repo.id, issue_number=2, title="Issue 2")

    response = test_client.patch(
        f"/api/v1/repositories/{repo.id}/issues/batch",
        json={
            "issue_numbers": [1, 2],
            "updates": {
                "priority": "high"
            }
        },
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["updated_count"] == 2

    print("✓ test_batch_update_issues_api 通过")


@pytest.mark.asyncio
async def test_batch_update_issues_unauthorized(
    test_client: TestClient, db
):
    """
    测试未认证用户批量操作

    验证点：
    1. 未认证用户收到 401
    """
    repo = create_test_repo(db)

    response = test_client.post(
        f"/api/v1/repositories/{repo.id}/issues/batch/close",
        json={"issue_numbers": [1]}
    )
    assert response.status_code == 401

    print("✓ test_batch_update_issues_unauthorized 通过")
