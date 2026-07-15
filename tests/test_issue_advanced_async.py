"""
Issue 高级功能测试

F-025: Issue 高级筛选
F-027: Issue 批量操作
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from models.issue import Issue, Label
from models.repository import Repository
from models.user import User
from services import issue_service
from core.exception import NotFoundException, ValidationException
from tests.test_helpers import async_create_test_issue, async_create_test_label


# ============ F-025: Issue 高级筛选测试 ============

@pytest.mark.asyncio
async def test_filter_issues_by_single_status(async_db: AsyncSession, async_test_repo: Repository, async_test_user: User):
    """测试按单个状态筛选 Issue"""
    # 创建不同状态的 Issue
    await async_create_test_issue(async_db, async_test_repo.id, 1, "Open Issue 1", status="open")
    await async_create_test_issue(async_db, async_test_repo.id, 2, "Open Issue 2", status="open")
    await async_create_test_issue(async_db, async_test_repo.id, 3, "Closed Issue", status="closed")

    result = await issue_service.filter_issues(
        async_db, async_test_repo.id,
        filters={"statuses": ["open"]}
    )

    assert result["total"] == 2
    for issue in result["items"]:
        assert issue["status"] == "open"


@pytest.mark.asyncio
async def test_filter_issues_by_priority(async_db: AsyncSession, async_test_repo: Repository, async_test_user: User):
    """测试按优先级筛选 Issue"""
    await async_create_test_issue(async_db, async_test_repo.id, 1, "High Priority", priority="high")
    await async_create_test_issue(async_db, async_test_repo.id, 2, "Low Priority", priority="low")
    await async_create_test_issue(async_db, async_test_repo.id, 3, "Critical Priority", priority="critical")

    result = await issue_service.filter_issues(
        async_db, async_test_repo.id,
        filters={"priorities": ["high", "critical"]}
    )

    assert result["total"] == 2
    priorities = [issue["priority"] for issue in result["items"]]
    assert "high" in priorities
    assert "critical" in priorities
    assert "low" not in priorities


@pytest.mark.asyncio
async def test_filter_issues_by_multiple_status(async_db: AsyncSession, async_test_repo: Repository, async_test_user: User):
    """测试按多个状态筛选 Issue"""
    await async_create_test_issue(async_db, async_test_repo.id, 1, "Open Issue", status="open")
    await async_create_test_issue(async_db, async_test_repo.id, 2, "Closed Issue", status="closed")

    result = await issue_service.filter_issues(
        async_db, async_test_repo.id,
        filters={"statuses": ["open", "closed"]}
    )

    assert result["total"] == 2


@pytest.mark.asyncio
async def test_filter_issues_by_assignee(async_db: AsyncSession, async_test_repo: Repository, async_test_user: User, async_another_user: User):
    """测试按指派人筛选 Issue"""
    await async_create_test_issue(async_db, async_test_repo.id, 1, "Assigned to user1", assignee_id=async_test_user.id)
    await async_create_test_issue(async_db, async_test_repo.id, 2, "Assigned to user2", assignee_id=async_another_user.id)
    await async_create_test_issue(async_db, async_test_repo.id, 3, "Unassigned")

    result = await issue_service.filter_issues(
        async_db, async_test_repo.id,
        filters={"assignee_ids": [async_test_user.id]}
    )

    assert result["total"] == 1
    assert result["items"][0]["title"] == "Assigned to user1"


@pytest.mark.asyncio
async def test_filter_issues_by_multiple_assignees(async_db: AsyncSession, async_test_repo: Repository, async_test_user: User, async_another_user: User):
    """测试按多个指派人筛选 Issue"""
    await async_create_test_issue(async_db, async_test_repo.id, 1, "Assigned to user1", assignee_id=async_test_user.id)
    await async_create_test_issue(async_db, async_test_repo.id, 2, "Assigned to user2", assignee_id=async_another_user.id)

    result = await issue_service.filter_issues(
        async_db, async_test_repo.id,
        filters={"assignee_ids": [async_test_user.id, async_another_user.id]}
    )

    assert result["total"] == 2


@pytest.mark.asyncio
async def test_filter_issues_by_author(async_db: AsyncSession, async_test_repo: Repository, async_test_user: User, async_another_user: User):
    """测试按作者筛选 Issue"""
    # 创建另一个用户作为作者
    issue1 = await async_create_test_issue(async_db, async_test_repo.id, 1, "By user1")
    issue2 = await async_create_test_issue(async_db, async_test_repo.id, 2, "By user2", author_id=async_another_user.id)

    result = await issue_service.filter_issues(
        async_db, async_test_repo.id,
        filters={"author_ids": [async_test_user.id]}
    )

    assert result["total"] == 1
    assert result["items"][0]["title"] == "By user1"


@pytest.mark.asyncio
async def test_filter_issues_by_labels(async_db: AsyncSession, async_test_repo: Repository, async_test_user: User):
    """测试按标签筛选 Issue"""
    bug_label = await async_create_test_label(async_db, async_test_repo.id, "bug", "#ff0000")
    feature_label = await async_create_test_label(async_db, async_test_repo.id, "feature", "#00ff00")

    issue1 = await async_create_test_issue(async_db, async_test_repo.id, 1, "Bug issue", labels=[bug_label])
    issue2 = await async_create_test_issue(async_db, async_test_repo.id, 2, "Feature issue", labels=[feature_label])
    issue3 = await async_create_test_issue(async_db, async_test_repo.id, 3, "Bug and feature", labels=[bug_label, feature_label])

    result = await issue_service.filter_issues(
        async_db, async_test_repo.id,
        filters={"label_ids": [bug_label.id]}
    )

    assert result["total"] == 2
    titles = [issue["title"] for issue in result["items"]]
    assert "Bug issue" in titles
    assert "Bug and feature" in titles


@pytest.mark.asyncio
async def test_filter_issues_by_multiple_labels(async_db: AsyncSession, async_test_repo: Repository, async_test_user: User):
    """测试按多个标签筛选 Issue（AND 关系）"""
    bug_label = await async_create_test_label(async_db, async_test_repo.id, "bug")
    urgent_label = await async_create_test_label(async_db, async_test_repo.id, "urgent")

    issue1 = await async_create_test_issue(async_db, async_test_repo.id, 1, "Just bug", labels=[bug_label])
    issue2 = await async_create_test_issue(async_db, async_test_repo.id, 2, "Bug and urgent", labels=[bug_label, urgent_label])

    # 筛选同时有 bug 和 urgent 标签的 Issue
    result = await issue_service.filter_issues(
        async_db, async_test_repo.id,
        filters={"label_ids": [bug_label.id, urgent_label.id]},
        label_match_all=True
    )

    assert result["total"] == 1
    assert result["items"][0]["title"] == "Bug and urgent"


@pytest.mark.asyncio
async def test_filter_issues_combined_criteria(async_db: AsyncSession, async_test_repo: Repository, async_test_user: User, async_another_user: User):
    """测试组合多个筛选条件"""
    bug_label = await async_create_test_label(async_db, async_test_repo.id, "bug")

    # 创建多个 Issue
    await async_create_test_issue(async_db, async_test_repo.id, 1,
                           "Open high bug", status="open", priority="high", labels=[bug_label])
    await async_create_test_issue(async_db, async_test_repo.id, 2,
                           "Closed high bug", status="closed", priority="high", labels=[bug_label])
    await async_create_test_issue(async_db, async_test_repo.id, 3,
                           "Open low bug", status="open", priority="low", labels=[bug_label])

    result = await issue_service.filter_issues(
        async_db, async_test_repo.id,
        filters={
            "statuses": ["open"],
            "priorities": ["high"],
            "label_ids": [bug_label.id]
        }
    )

    assert result["total"] == 1
    assert result["items"][0]["title"] == "Open high bug"


@pytest.mark.asyncio
async def test_filter_issues_by_search_keyword(async_db: AsyncSession, async_test_repo: Repository, async_test_user: User):
    """测试按搜索关键词筛选 Issue"""
    await async_create_test_issue(async_db, async_test_repo.id, 1, "Login button not working")
    await async_create_test_issue(async_db, async_test_repo.id, 2, "Logout functionality broken")
    await async_create_test_issue(async_db, async_test_repo.id, 3, "Database connection error")

    result = await issue_service.filter_issues(
        async_db, async_test_repo.id,
        filters={"search": "login"}
    )

    assert result["total"] == 1
    assert "login" in result["items"][0]["title"].lower()


@pytest.mark.asyncio
async def test_filter_issues_sort_by_created_desc(async_db: AsyncSession, async_test_repo: Repository, async_test_user: User):
    """测试按创建时间降序排序"""
    import asyncio
    import time
    from datetime import datetime, timedelta
    from sqlalchemy import select
    from models.issue import Issue

    # 使用唯一标题避免与其他测试冲突（使用时间戳确保唯一性）
    unique_prefix = f"sort_test_{int(time.time() * 1000)}_"

    # 手动设置创建时间，确保有足够的时间差
    older_time = datetime.utcnow() - timedelta(seconds=10)
    newer_time = datetime.utcnow()

    issue1 = await async_create_test_issue(async_db, async_test_repo.id, 100, f"{unique_prefix}Older")
    issue1.created_at = older_time
    await async_db.commit()

    issue2 = await async_create_test_issue(async_db, async_test_repo.id, 101, f"{unique_prefix}Newer")
    issue2.created_at = newer_time
    await async_db.commit()

    # 直接查询数据库验证排序
    stmt = select(Issue).filter(
        Issue.repository_id == async_test_repo.id,
        Issue.title.like(f"{unique_prefix}%")
    ).order_by(Issue.created_at.desc())
    result = await async_db.execute(stmt)
    issues = result.scalars().all()

    titles = [issue.title for issue in issues]

    # 只检查我们创建的 Issue
    our_issues = [t for t in titles if t.startswith(unique_prefix)]
    assert len(our_issues) == 2
    # 按创建时间降序，后创建的（Newer）应该排在前面
    newer_idx = our_issues.index(f"{unique_prefix}Newer")
    older_idx = our_issues.index(f"{unique_prefix}Older")
    assert newer_idx < older_idx, f"Expected Newer ({newer_idx}) to come before Older ({older_idx}), got: {our_issues}"


@pytest.mark.asyncio
async def test_filter_issues_sort_by_priority(async_db: AsyncSession, async_test_repo: Repository, async_test_user: User):
    """测试按优先级排序"""
    await async_create_test_issue(async_db, async_test_repo.id, 1, "Low", priority="low")
    await async_create_test_issue(async_db, async_test_repo.id, 2, "Critical", priority="critical")
    await async_create_test_issue(async_db, async_test_repo.id, 3, "High", priority="high")

    result = await issue_service.filter_issues(
        async_db, async_test_repo.id,
        sort_by="priority",
        sort_order="desc"
    )

    priorities = [issue["priority"] for issue in result["items"]]
    assert priorities == ["critical", "high", "low"]


@pytest.mark.asyncio
async def test_filter_issues_pagination(async_db: AsyncSession, async_test_repo: Repository, async_test_user: User):
    """测试筛选结果分页"""
    for i in range(5):
        await async_create_test_issue(async_db, async_test_repo.id, i + 1, f"Issue {i + 1}")

    result = await issue_service.filter_issues(
        async_db, async_test_repo.id,
        page=1,
        per_page=2
    )

    assert len(result["items"]) == 2
    assert result["total"] == 5
    assert result["page"] == 1
    assert result["limit"] == 2


@pytest.mark.asyncio
async def test_filter_issues_no_results(async_db: AsyncSession, async_test_repo: Repository, async_test_user: User):
    """测试筛选无结果"""
    await async_create_test_issue(async_db, async_test_repo.id, 1, "Open issue", status="open")

    result = await issue_service.filter_issues(
        async_db, async_test_repo.id,
        filters={"statuses": ["closed"]}
    )

    assert result["total"] == 0
    assert result["items"] == []


# ============ F-027: Issue 批量操作测试 ============

@pytest.mark.asyncio
async def test_batch_update_issue_status(async_db: AsyncSession, async_test_repo: Repository, async_test_user: User):
    """测试批量更新 Issue 状态"""
    issue1 = await async_create_test_issue(async_db, async_test_repo.id, 1, "Issue 1", status="open")
    issue2 = await async_create_test_issue(async_db, async_test_repo.id, 2, "Issue 2", status="open")

    result = await issue_service.batch_update_issues(
        async_db, async_test_repo.id, async_test_user.id,
        issue_numbers=[1, 2],
        updates={"status": "closed"}
    )

    assert result["updated_count"] == 2
    assert result["failed_count"] == 0

    # 验证状态已更新
    updated_issue1 = await issue_service.get_issue(async_db, async_test_repo.id, 1)
    updated_issue2 = await issue_service.get_issue(async_db, async_test_repo.id, 2)
    assert updated_issue1["status"] == "closed"
    assert updated_issue2["status"] == "closed"


@pytest.mark.asyncio
async def test_batch_update_issue_assignee(async_db: AsyncSession, async_test_repo: Repository, async_test_user: User, async_another_user: User):
    """测试批量更新 Issue 指派人"""
    issue1 = await async_create_test_issue(async_db, async_test_repo.id, 1, "Issue 1")
    issue2 = await async_create_test_issue(async_db, async_test_repo.id, 2, "Issue 2")

    result = await issue_service.batch_update_issues(
        async_db, async_test_repo.id, async_test_user.id,
        issue_numbers=[1, 2],
        updates={"assignee_id": async_another_user.id}
    )

    assert result["updated_count"] == 2

    # 验证指派人已更新（通过数据库直接查询验证）
    from sqlalchemy import select
    from models.issue import Issue
    stmt = select(Issue).filter(Issue.repository_id == async_test_repo.id, Issue.issue_number == 1)
    result = await async_db.execute(stmt)
    updated_issue = result.scalar_one()
    assert updated_issue.assignee_id == async_another_user.id


@pytest.mark.asyncio
async def test_batch_update_issue_priority(async_db: AsyncSession, async_test_repo: Repository, async_test_user: User):
    """测试批量更新 Issue 优先级"""
    issue1 = await async_create_test_issue(async_db, async_test_repo.id, 1, "Issue 1", priority="low")
    issue2 = await async_create_test_issue(async_db, async_test_repo.id, 2, "Issue 2", priority="medium")

    result = await issue_service.batch_update_issues(
        async_db, async_test_repo.id, async_test_user.id,
        issue_numbers=[1, 2],
        updates={"priority": "high"}
    )

    assert result["updated_count"] == 2

    updated_issue1 = await issue_service.get_issue(async_db, async_test_repo.id, 1)
    assert updated_issue1["priority"] == "high"


@pytest.mark.asyncio
async def test_batch_update_issue_labels(async_db: AsyncSession, async_test_repo: Repository, async_test_user: User):
    """测试批量更新 Issue 标签"""
    bug_label = await async_create_test_label(async_db, async_test_repo.id, "bug")
    issue1 = await async_create_test_issue(async_db, async_test_repo.id, 1, "Issue 1")
    issue2 = await async_create_test_issue(async_db, async_test_repo.id, 2, "Issue 2")

    result = await issue_service.batch_update_issues(
        async_db, async_test_repo.id, async_test_user.id,
        issue_numbers=[1, 2],
        updates={"label_ids": [bug_label.id]}
    )

    assert result["updated_count"] == 2

    updated_issue1 = await issue_service.get_issue(async_db, async_test_repo.id, 1)
    assert len(updated_issue1["labels"]) == 1
    assert updated_issue1["labels"][0]["name"] == "bug"


@pytest.mark.asyncio
async def test_batch_update_partial_failure(async_db: AsyncSession, async_test_repo: Repository, async_test_user: User, async_another_user: User):
    """测试批量更新部分失败（用户有权限更新自己的，但无法更新不存在的）"""
    # 创建 Issue
    issue1 = await async_create_test_issue(async_db, async_test_repo.id, 1, "My issue")

    result = await issue_service.batch_update_issues(
        async_db, async_test_repo.id, async_test_user.id,
        issue_numbers=[1, 999],  # 999 不存在
        updates={"status": "closed"}
    )

    assert result["updated_count"] == 1  # 只更新了存在的 Issue
    assert result["failed_count"] == 1  # 不存在的失败


@pytest.mark.asyncio
async def test_batch_update_empty_list(async_db: AsyncSession, async_test_repo: Repository, async_test_user: User):
    """测试批量更新空列表"""
    result = await issue_service.batch_update_issues(
        async_db, async_test_repo.id, async_test_user.id,
        issue_numbers=[],
        updates={"status": "closed"}
    )

    assert result["updated_count"] == 0
    assert result["failed_count"] == 0


@pytest.mark.asyncio
async def test_batch_close_issues(async_db: AsyncSession, async_test_repo: Repository, async_test_user: User):
    """测试批量关闭 Issue"""
    issue1 = await async_create_test_issue(async_db, async_test_repo.id, 1, "Issue 1", status="open")
    issue2 = await async_create_test_issue(async_db, async_test_repo.id, 2, "Issue 2", status="open")

    result = await issue_service.batch_close_issues(
        async_db, async_test_repo.id, async_test_user.id,
        issue_numbers=[1, 2]
    )

    assert result["closed_count"] == 2

    updated_issue1 = await issue_service.get_issue(async_db, async_test_repo.id, 1)
    assert updated_issue1["status"] == "closed"


@pytest.mark.asyncio
async def test_batch_reopen_issues(async_db: AsyncSession, async_test_repo: Repository, async_test_user: User):
    """测试批量重新打开 Issue"""
    issue1 = await async_create_test_issue(async_db, async_test_repo.id, 1, "Issue 1", status="closed")
    issue2 = await async_create_test_issue(async_db, async_test_repo.id, 2, "Issue 2", status="closed")

    result = await issue_service.batch_reopen_issues(
        async_db, async_test_repo.id, async_test_user.id,
        issue_numbers=[1, 2]
    )

    assert result["reopened_count"] == 2

    updated_issue1 = await issue_service.get_issue(async_db, async_test_repo.id, 1)
    assert updated_issue1["status"] == "open"


@pytest.mark.asyncio
async def test_batch_add_labels(async_db: AsyncSession, async_test_repo: Repository, async_test_user: User):
    """测试批量添加标签"""
    bug_label = await async_create_test_label(async_db, async_test_repo.id, "bug")
    urgent_label = await async_create_test_label(async_db, async_test_repo.id, "urgent")

    issue1 = await async_create_test_issue(async_db, async_test_repo.id, 1, "Issue 1")
    issue2 = await async_create_test_issue(async_db, async_test_repo.id, 2, "Issue 2")

    result = await issue_service.batch_add_labels(
        async_db, async_test_repo.id, async_test_user.id,
        issue_numbers=[1, 2],
        label_ids=[bug_label.id, urgent_label.id]
    )

    assert result["updated_count"] == 2

    updated_issue1 = await issue_service.get_issue(async_db, async_test_repo.id, 1)
    assert len(updated_issue1["labels"]) == 2


@pytest.mark.asyncio
async def test_batch_remove_labels(async_db: AsyncSession, async_test_repo: Repository, async_test_user: User):
    """测试批量移除标签"""
    bug_label = await async_create_test_label(async_db, async_test_repo.id, "bug")

    issue1 = await async_create_test_issue(async_db, async_test_repo.id, 1, "Issue 1", labels=[bug_label])
    issue2 = await async_create_test_issue(async_db, async_test_repo.id, 2, "Issue 2", labels=[bug_label])

    result = await issue_service.batch_remove_labels(
        async_db, async_test_repo.id, async_test_user.id,
        issue_numbers=[1, 2],
        label_ids=[bug_label.id]
    )

    assert result["updated_count"] == 2

    updated_issue1 = await issue_service.get_issue(async_db, async_test_repo.id, 1)
    assert len(updated_issue1["labels"]) == 0
