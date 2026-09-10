"""
搜索 API 端点测试

验证搜索控制器层的所有端点
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from models.repository import Repository
from models.issue import Issue
from models.pull_request import PullRequest
from utils.git_utils import init_bare_repo, get_repository_storage_path
from tests.test_helpers import create_test_repo as _create_test_repo


def create_test_repo(db, name: str = "test-repo") -> Repository:
    """创建测试仓库（含物理 Git 仓库初始化）"""
    repo = _create_test_repo(db, name=name)
    physical_path = get_repository_storage_path(repo.path)
    init_bare_repo(physical_path)
    return repo


class TestSearchAPI:
    def test_search_code(self, test_client: TestClient, auth_headers: dict, db):
        repo = create_test_repo(db, name="search-test-repo")

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
        repo = create_test_repo(db, name="search-path-repo")

        response = test_client.get(
            f"/api/v1/repositories/{repo.id}/search",
            params={"q": "def", "path": "."},
            headers=auth_headers,
        )
        assert response.status_code == 200

    def test_search_requires_query(self, test_client: TestClient, auth_headers: dict, db):
        repo = create_test_repo(db, name="search-noquery-repo")

        response = test_client.get(
            f"/api/v1/repositories/{repo.id}/search",
            headers=auth_headers,
        )
        assert response.status_code == 422  # Validation error

    def test_search_requires_auth(self, test_client: TestClient, db):
        repo = create_test_repo(db, name="search-auth-repo")

        response = test_client.get(
            f"/api/v1/repositories/{repo.id}/search",
            params={"q": "def"},
        )
        assert response.status_code == 401


class TestGlobalSearchAPI:
    """全局聚合搜索（仓库/Issue/PR）端点测试"""

    def _create_repo(self, db, user, name: str, is_public: bool = True, description: str = None) -> Repository:
        repo = Repository(
            name=name,
            path=f"{user.username}/{name}",
            description=description,
            is_public=is_public,
            owner_id=user.id,
        )
        db.add(repo)
        db.commit()
        db.refresh(repo)
        return repo

    def test_global_search_repositories(self, test_client: TestClient, auth_headers: dict, db, test_user):
        self._create_repo(db, test_user, "global-search-repo", description="a searchable repo")
        self._create_repo(db, test_user, "unrelated-repo")

        response = test_client.get(
            "/api/v1/search/global",
            params={"q": "global-search"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "global-search"
        paths = [r["path"] for r in data["repositories"]]
        assert f"{test_user.username}/global-search-repo" in paths
        assert f"{test_user.username}/unrelated-repo" not in paths
        assert data["issues"] == []
        assert data["pull_requests"] == []

    def test_global_search_issues(self, test_client: TestClient, auth_headers: dict, db, test_user):
        repo = self._create_repo(db, test_user, "issue-search-repo")
        issue = Issue(
            repository_id=repo.id,
            issue_number=1,
            title="Fix cleanup logic",
            description="cleanup the temp files",
            author_id=test_user.id,
        )
        db.add(issue)
        db.commit()

        response = test_client.get(
            "/api/v1/search/global",
            params={"q": "cleanup"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["issues"]) == 1
        hit = data["issues"][0]
        assert hit["issue_number"] == 1
        assert hit["title"] == "Fix cleanup logic"
        assert hit["repository_path"] == f"{test_user.username}/issue-search-repo"

    def test_global_search_pull_requests(self, test_client: TestClient, auth_headers: dict, db, test_user):
        repo = self._create_repo(db, test_user, "pr-search-repo")
        pr = PullRequest(
            repository_id=repo.id,
            pr_number=1,
            title="Add graphql endpoint",
            description="expose graphql",
            source_branch="feat/graphql",
            target_branch="main",
            author_id=test_user.id,
        )
        db.add(pr)
        db.commit()

        response = test_client.get(
            "/api/v1/search/global",
            params={"q": "graphql"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["pull_requests"]) == 1
        hit = data["pull_requests"][0]
        assert hit["pr_number"] == 1
        assert hit["repository_name"] == "pr-search-repo"

    def test_global_search_private_repo_excluded(self, test_client: TestClient, auth_headers: dict, db, test_user, admin_user):
        # 私有仓库属于其他用户且无成员关系 → 不应出现在结果中
        self._create_repo(db, admin_user, "admin-private-repo", is_public=False)
        self._create_repo(db, test_user, "my-public-repo", is_public=True)

        response = test_client.get(
            "/api/v1/search/global",
            params={"q": "repo"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        paths = [r["path"] for r in data["repositories"]]
        assert f"{admin_user.username}/admin-private-repo" not in paths
        assert f"{test_user.username}/my-public-repo" in paths

    def test_global_search_per_type_limit(self, test_client: TestClient, auth_headers: dict, db, test_user):
        for i in range(3):
            self._create_repo(db, test_user, f"limit-repo-{i}")

        response = test_client.get(
            "/api/v1/search/global",
            params={"q": "limit-repo", "per_type": 2},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["repositories"]) <= 2

    def test_global_search_requires_auth(self, test_client: TestClient, db, test_user):
        self._create_repo(db, test_user, "auth-global-repo")

        response = test_client.get(
            "/api/v1/search/global",
            params={"q": "auth-global"},
        )
        assert response.status_code == 401

    def test_global_search_requires_query(self, test_client: TestClient, auth_headers: dict, db):
        response = test_client.get(
            "/api/v1/search/global",
            headers=auth_headers,
        )
        assert response.status_code == 422
