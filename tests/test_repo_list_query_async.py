"""
仓库列表查询功能测试

测试 G-004~G-007: 分页、排序、搜索、可见性筛选
"""
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from models.repository import Repository
from models.user import User
from services import repository_service


@pytest_asyncio.fixture
async def multi_repos(async_db: AsyncSession, async_test_user: User):
    """创建15个测试仓库，用于分页、排序、搜索、筛选测试"""
    repos = []
    for i in range(15):
        r = Repository(
            name=f"repo-{i:03d}",
            path=f"{async_test_user.username}/repo-{i:03d}",
            description=f"Description for repo {i}" if i % 2 == 0 else None,
            owner_id=async_test_user.id,
            is_public=(i % 3 != 0),
        )
        repos.append(r)
    async_db.add_all(repos)
    await async_db.commit()
    for r in repos:
        await async_db.refresh(r)
    return repos


@pytest.mark.asyncio
async def test_repo_list_pagination(async_db: AsyncSession, multi_repos):
    """G-004: 测试分页功能"""
    page1 = await repository_service.get_repositories(async_db, page=1, limit=5)
    assert len(page1["items"]) == 5
    assert page1["page"] == 1
    assert page1["total"] == 15
    assert page1["has_next"] is True
    assert page1["has_prev"] is False
    assert page1["pages"] == 3

    page2 = await repository_service.get_repositories(async_db, page=2, limit=5)
    assert len(page2["items"]) == 5
    assert page2["page"] == 2
    assert page2["has_next"] is True
    assert page2["has_prev"] is True

    page4 = await repository_service.get_repositories(async_db, page=4, limit=5)
    assert len(page4["items"]) == 0
    assert page4["has_next"] is False
    assert page4["has_prev"] is True


@pytest.mark.asyncio
async def test_repo_list_sorting(async_db: AsyncSession, multi_repos):
    """G-005: 测试排序功能"""
    result = await repository_service.get_repositories(async_db, sort="name", order="asc")
    names = [r["name"] for r in result["items"]]
    assert names == sorted(names)

    result_desc = await repository_service.get_repositories(async_db, sort="name", order="desc")
    names_desc = [r["name"] for r in result_desc["items"]]
    assert names_desc == sorted(names_desc, reverse=True)

    result_updated = await repository_service.get_repositories(async_db, sort="updated_at", order="desc")
    assert len(result_updated["items"]) > 0


@pytest.mark.asyncio
async def test_repo_list_search(async_db: AsyncSession, multi_repos):
    """G-006: 测试搜索功能"""
    result = await repository_service.get_repositories(async_db, q="repo-00")
    assert len(result["items"]) >= 1
    for item in result["items"]:
        assert "repo-00" in item["name"] or "repo-00" in (item.get("description") or "")

    result = await repository_service.get_repositories(async_db, q="nonexistent")
    assert len(result["items"]) == 0


@pytest.mark.asyncio
async def test_repo_list_visibility_filter(async_db: AsyncSession, multi_repos):
    """G-007: 测试可见性筛选"""
    public = await repository_service.get_repositories(async_db, is_public=True)
    assert len(public["items"]) > 0
    assert all(r["is_public"] for r in public["items"])

    private = await repository_service.get_repositories(async_db, is_public=False)
    assert len(private["items"]) > 0
    assert all(not r["is_public"] for r in private["items"])

    total = public["total"] + private["total"]
    assert total == 15


@pytest.mark.asyncio
async def test_repo_list_combined_query(async_db: AsyncSession, multi_repos):
    """测试组合查询：搜索 + 筛选 + 排序 + 分页"""
    result = await repository_service.get_repositories(
        async_db, q="repo", is_public=True, sort="name", order="asc", page=1, limit=3
    )
    assert len(result["items"]) <= 3
    assert result["page"] == 1
    assert all(r["is_public"] for r in result["items"])

    names = [r["name"] for r in result["items"]]
    assert names == sorted(names)


@pytest.mark.asyncio
async def test_repo_list_default_params(async_db: AsyncSession, multi_repos):
    """测试默认参数：不传参时使用默认值"""
    result = await repository_service.get_repositories(async_db)
    assert result["page"] == 1
    assert result["limit"] == 20
    assert result["total"] == 15
    assert len(result["items"]) == 15
