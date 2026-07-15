"""
Release API 集成测试

验证 Release 控制器层的所有端点
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from models.repository import Repository
from utils.git_utils import init_bare_repo, get_repository_storage_path
from tests.test_helpers import create_test_repo as _create_test_repo


def create_test_repo(db, name: str = "test-repo") -> Repository:
    """创建测试仓库（含物理 Git 仓库初始化）"""
    repo = _create_test_repo(db, name=name)
    physical_path = get_repository_storage_path(repo.path)
    init_bare_repo(physical_path)
    return repo


# =============================================================================
# Release CRUD
# =============================================================================

def test_create_release_success(test_client: TestClient, auth_headers: dict, db):
    """测试成功创建 Release"""
    repo = create_test_repo(db)

    response = test_client.post(
        f"/api/v1/repositories/{repo.id}/releases",
        json={
            "tag_name": "v1.0.0",
            "name": "Version 1.0.0",
            "description": "## Changes\n- Initial release",
            "is_prerelease": False
        },
        headers=auth_headers
    )

    assert response.status_code == 201
    data = response.json()
    assert data["tag_name"] == "v1.0.0"
    assert data["name"] == "Version 1.0.0"
    assert data["description"] == "## Changes\n- Initial release"
    assert data["is_draft"] is False
    assert data["is_prerelease"] is False
    assert data["release_number"] >= 1


def test_create_release_requires_auth(test_client: TestClient, db):
    """测试未认证用户不能创建 Release"""
    repo = create_test_repo(db)

    response = test_client.post(
        f"/api/v1/repositories/{repo.id}/releases",
        json={
            "tag_name": "v1.0.0",
            "name": "Version 1.0.0"
        }
    )

    assert response.status_code == 401


def test_create_release_duplicate_tag(test_client: TestClient, auth_headers: dict, db):
    """测试重复标签名创建 Release 失败"""
    repo = create_test_repo(db)

    # 第一次成功
    test_client.post(
        f"/api/v1/repositories/{repo.id}/releases",
        json={"tag_name": "v1.0.0", "name": "Version 1.0.0"},
        headers=auth_headers
    )

    # 第二次失败
    response = test_client.post(
        f"/api/v1/repositories/{repo.id}/releases",
        json={"tag_name": "v1.0.0", "name": "Version 1.0.0"},
        headers=auth_headers
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_list_releases(async_db: AsyncSession, async_test_user):
    """测试获取 Release 列表"""
    from models.repository import Repository as RepoModel
    from services import release_service

    repo = RepoModel(
        name="test-repo", path="testuser/test-repo",
        description="Test repository", is_public=True,
        owner_id=async_test_user.id, default_branch="main"
    )
    async_db.add(repo)
    await async_db.commit()
    await async_db.refresh(repo)
    repo_path = get_repository_storage_path(repo.path)
    init_bare_repo(repo_path)

    await release_service.create_release(
        async_db, repo.id, author_id=async_test_user.id, tag_name="v1.0.0",
        name="Version 1.0.0", commit_hash="0000000000000000000000000000000000000000",
        create_git_tag=False, repo_path=repo_path
    )
    await release_service.create_release(
        async_db, repo.id, author_id=async_test_user.id, tag_name="v2.0.0",
        name="Version 2.0.0", commit_hash="0000000000000000000000000000000000000000",
        create_git_tag=False, repo_path=repo_path
    )

    result = await release_service.list_releases(async_db, repo.id)
    assert result["total"] == 2
    assert len(result["items"]) == 2


def test_get_release_by_number(test_client: TestClient, auth_headers: dict, db):
    """测试根据编号获取 Release 详情"""
    repo = create_test_repo(db)

    create_resp = test_client.post(
        f"/api/v1/repositories/{repo.id}/releases",
        json={"tag_name": "v1.0.0", "name": "Version 1.0.0"},
        headers=auth_headers
    )
    release_number = create_resp.json()["release_number"]

    response = test_client.get(
        f"/api/v1/repositories/{repo.id}/releases/{release_number}",
        headers=auth_headers
    )

    assert response.status_code == 200
    assert response.json()["tag_name"] == "v1.0.0"


def test_get_release_by_tag(test_client: TestClient, auth_headers: dict, db):
    """测试根据标签名称获取 Release"""
    repo = create_test_repo(db)

    test_client.post(
        f"/api/v1/repositories/{repo.id}/releases",
        json={"tag_name": "v1.0.0", "name": "Version 1.0.0"},
        headers=auth_headers
    )

    response = test_client.get(
        f"/api/v1/repositories/{repo.id}/releases/tag/v1.0.0",
        headers=auth_headers
    )

    assert response.status_code == 200
    assert response.json()["tag_name"] == "v1.0.0"


def test_update_release(test_client: TestClient, auth_headers: dict, db):
    """测试更新 Release"""
    repo = create_test_repo(db)

    create_resp = test_client.post(
        f"/api/v1/repositories/{repo.id}/releases",
        json={"tag_name": "v1.0.0", "name": "Version 1.0.0"},
        headers=auth_headers
    )
    release_number = create_resp.json()["release_number"]

    response = test_client.patch(
        f"/api/v1/repositories/{repo.id}/releases/{release_number}",
        json={"name": "Updated Title", "description": "Updated description"},
        headers=auth_headers
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Updated Title"
    assert response.json()["description"] == "Updated description"


def test_delete_release(test_client: TestClient, auth_headers: dict, db):
    """测试删除 Release"""
    repo = create_test_repo(db)

    create_resp = test_client.post(
        f"/api/v1/repositories/{repo.id}/releases",
        json={"tag_name": "v1.0.0", "name": "Version 1.0.0"},
        headers=auth_headers
    )
    release_number = create_resp.json()["release_number"]

    response = test_client.delete(
        f"/api/v1/repositories/{repo.id}/releases/{release_number}",
        headers=auth_headers
    )

    assert response.status_code == 204


def test_get_release_not_found(test_client: TestClient, auth_headers: dict, db):
    """测试获取不存在的 Release 返回 404"""
    repo = create_test_repo(db)

    response = test_client.get(
        f"/api/v1/repositories/{repo.id}/releases/99999",
        headers=auth_headers
    )

    assert response.status_code == 404


# =============================================================================
# Release Asset 管理
# =============================================================================

def test_add_release_asset(test_client: TestClient, auth_headers: dict, db):
    """测试添加 Release 附件"""
    repo = create_test_repo(db)

    create_resp = test_client.post(
        f"/api/v1/repositories/{repo.id}/releases",
        json={"tag_name": "v1.0.0", "name": "Version 1.0.0"},
        headers=auth_headers
    )
    release_number = create_resp.json()["release_number"]

    response = test_client.post(
        f"/api/v1/repositories/{repo.id}/releases/{release_number}/assets",
        json={
            "name": "release.zip",
            "file_path": "/tmp/release.zip",
            "file_size": 1024,
            "content_type": "application/zip"
        },
        headers=auth_headers
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "release.zip"
    assert data["file_size"] == 1024
    assert data["content_type"] == "application/zip"


def test_delete_release_asset(test_client: TestClient, auth_headers: dict, db):
    """测试删除 Release 附件"""
    repo = create_test_repo(db)

    create_resp = test_client.post(
        f"/api/v1/repositories/{repo.id}/releases",
        json={"tag_name": "v1.0.0", "name": "Version 1.0.0"},
        headers=auth_headers
    )
    release_number = create_resp.json()["release_number"]

    # 先添加附件
    asset_resp = test_client.post(
        f"/api/v1/repositories/{repo.id}/releases/{release_number}/assets",
        json={
            "name": "release.zip",
            "file_path": "/tmp/release.zip",
            "file_size": 1024
        },
        headers=auth_headers
    )
    asset_id = asset_resp.json()["id"]

    # 删除附件
    response = test_client.delete(
        f"/api/v1/repositories/{repo.id}/releases/{release_number}/assets/{asset_id}",
        headers=auth_headers
    )

    assert response.status_code == 204
