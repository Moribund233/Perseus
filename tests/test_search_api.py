"""
搜索 API 端点测试

验证搜索控制器层的所有端点
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from models.repository import Repository
from utils.git_utils import init_bare_repo, get_repository_storage_path


def create_test_repo(db, owner_id: int, name: str = "test-repo") -> Repository:
    """创建测试仓库（含物理 Git 仓库初始化）"""
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
    physical_path = get_repository_storage_path(repo.path)
    init_bare_repo(physical_path)
    return repo


class TestSearchAPI:
    def test_search_code(self, test_client: TestClient, auth_headers: dict, db):
        repo = create_test_repo(db, 1, name="search-test-repo")

        response = test_client.get(
            f"/api/v1/repositories/{repo.id}/search",
            params={"q": "def"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "query" in data
        assert "results" in data
        assert "total_count" in data
        assert "truncated" in data

    def test_search_code_with_path(self, test_client: TestClient, auth_headers: dict, db):
        repo = create_test_repo(db, 1, name="search-path-repo")

        response = test_client.get(
            f"/api/v1/repositories/{repo.id}/search",
            params={"q": "def", "path": "."},
            headers=auth_headers,
        )
        assert response.status_code == 200

    def test_search_requires_query(self, test_client: TestClient, auth_headers: dict, db):
        repo = create_test_repo(db, 1, name="search-noquery-repo")

        response = test_client.get(
            f"/api/v1/repositories/{repo.id}/search",
            headers=auth_headers,
        )
        assert response.status_code == 422  # Validation error

    def test_search_requires_auth(self, test_client: TestClient, db):
        repo = create_test_repo(db, 1, name="search-auth-repo")

        response = test_client.get(
            f"/api/v1/repositories/{repo.id}/search",
            params={"q": "def"},
        )
        assert response.status_code == 401
