import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from models.repository import Repository
from services.build_service import BuildService
from core.exception import NotFoundException


def create_test_repo(db, owner_id: int, name: str = "test-build-repo") -> Repository:
    repo = Repository(
        name=name,
        path=f"testuser/{name}",
        description="Test repository for builds",
        is_public=True,
        owner_id=owner_id,
        default_branch="main"
    )
    db.add(repo)
    db.commit()
    db.refresh(repo)
    return repo


class TestBuildService:

    async def test_create_build(self, async_db: AsyncSession, async_test_user):
        repo_id = 1
        build = await BuildService.create_build(
            db=async_db,
            repo_id=repo_id,
            branch="main",
            commit_sha="abc123def456",
            triggered_by=async_test_user.id,
            commit_message="Initial commit",
        )
        assert build.id is not None
        assert build.repo_id == repo_id
        assert build.branch == "main"
        assert build.commit_sha == "abc123def456"
        assert build.status == "pending"
        assert build.triggered_by == async_test_user.id
        assert build.commit_message == "Initial commit"

    async def test_create_build_sets_timestamps(self, async_db: AsyncSession, async_test_user):
        build = await BuildService.create_build(
            db=async_db,
            repo_id=1,
            branch="main",
            commit_sha="abc",
            triggered_by=async_test_user.id,
        )
        assert build.created_at is not None
        assert build.started_at is None
        assert build.finished_at is None

    async def test_get_build_success(self, async_db: AsyncSession, async_test_user):
        build = await BuildService.create_build(
            db=async_db,
            repo_id=1,
            branch="main",
            commit_sha="abc",
            triggered_by=async_test_user.id,
        )
        found = await BuildService.get_build(db=async_db, build_id=build.id)
        assert found is not None
        assert found.id == build.id
        assert found.status == "pending"

    async def test_get_build_not_found(self, async_db: AsyncSession):
        with pytest.raises(NotFoundException):
            await BuildService.get_build(db=async_db, build_id=99999)

    async def test_list_builds_for_repository(self, async_db: AsyncSession, async_test_user):
        repo_id = 42
        for i in range(3):
            await BuildService.create_build(
                db=async_db,
                repo_id=repo_id,
                branch="main",
                commit_sha=f"abc{i}",
                triggered_by=async_test_user.id,
            )
        builds = await BuildService.get_builds_for_repository(
            db=async_db, repo_id=repo_id
        )
        assert len(builds) == 3
        for i in range(len(builds) - 1):
            assert builds[i].created_at >= builds[i + 1].created_at

    async def test_list_builds_empty_repo(self, async_db: AsyncSession):
        builds = await BuildService.get_builds_for_repository(db=async_db, repo_id=999)
        assert builds == []

    async def test_list_builds_with_limit(self, async_db: AsyncSession, async_test_user):
        repo_id = 7
        for i in range(5):
            await BuildService.create_build(
                db=async_db,
                repo_id=repo_id,
                branch="main",
                commit_sha=f"abc{i}",
                triggered_by=async_test_user.id,
            )
        builds = await BuildService.get_builds_for_repository(
            db=async_db, repo_id=repo_id, limit=2
        )
        assert len(builds) == 2

    async def test_update_build_status_to_running(self, async_db: AsyncSession, async_test_user):
        build = await BuildService.create_build(
            db=async_db,
            repo_id=1,
            branch="main",
            commit_sha="abc",
            triggered_by=async_test_user.id,
        )
        updated = await BuildService.update_build_status(
            db=async_db, build_id=build.id, status="running"
        )
        assert updated.status == "running"
        assert updated.started_at is not None

    async def test_update_build_status_to_success(self, async_db: AsyncSession, async_test_user):
        build = await BuildService.create_build(
            db=async_db,
            repo_id=1,
            branch="main",
            commit_sha="abc",
            triggered_by=async_test_user.id,
        )
        await BuildService.update_build_status(db=async_db, build_id=build.id, status="running")
        updated = await BuildService.update_build_status(
            db=async_db, build_id=build.id, status="success"
        )
        assert updated.status == "success"
        assert updated.finished_at is not None

    async def test_update_build_invalid_status(self, async_db: AsyncSession, async_test_user):
        build = await BuildService.create_build(
            db=async_db,
            repo_id=1,
            branch="main",
            commit_sha="abc",
            triggered_by=async_test_user.id,
        )
        with pytest.raises(ValueError):
            await BuildService.update_build_status(
                db=async_db, build_id=build.id, status="invalid_status"
            )


class TestBuildController:

    def test_create_build_via_api(self, test_client: TestClient, auth_headers: dict, db):
        repo = create_test_repo(db, owner_id=1)
        response = test_client.post(
            f"/api/v1/repositories/{repo.id}/builds",
            json={
                "branch": "main",
                "commit_sha": "abc123def456",
                "commit_message": "Test commit",
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "pending"
        assert data["branch"] == "main"
        assert data["commit_sha"] == "abc123def456"
        assert data["commit_message"] == "Test commit"

    def test_list_builds_via_api(self, test_client: TestClient, auth_headers: dict, db):
        repo = create_test_repo(db, owner_id=1)
        for i in range(3):
            test_client.post(
                f"/api/v1/repositories/{repo.id}/builds",
                json={"branch": f"branch-{i}", "commit_sha": f"abc{i}", "commit_message": f"Commit {i}"},
                headers=auth_headers,
            )
        response = test_client.get(
            f"/api/v1/repositories/{repo.id}/builds",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

    def test_get_build_via_api(self, test_client: TestClient, auth_headers: dict, db):
        repo = create_test_repo(db, owner_id=1)
        create_resp = test_client.post(
            f"/api/v1/repositories/{repo.id}/builds",
            json={"branch": "main", "commit_sha": "abc", "commit_message": "Test"},
            headers=auth_headers,
        )
        build_id = create_resp.json()["id"]
        response = test_client.get(
            f"/api/v1/repositories/{repo.id}/builds/{build_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["id"] == build_id

    def test_update_build_status_via_api(self, test_client: TestClient, auth_headers: dict, db):
        repo = create_test_repo(db, owner_id=1)
        create_resp = test_client.post(
            f"/api/v1/repositories/{repo.id}/builds",
            json={"branch": "main", "commit_sha": "abc"},
            headers=auth_headers,
        )
        build_id = create_resp.json()["id"]
        response = test_client.patch(
            f"/api/v1/repositories/{repo.id}/builds/{build_id}",
            json={"status": "running"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["status"] == "running"

    def test_create_build_requires_auth(self, test_client: TestClient, db):
        repo = create_test_repo(db, owner_id=1)
        response = test_client.post(
            f"/api/v1/repositories/{repo.id}/builds",
            json={"branch": "main", "commit_sha": "abc"},
        )
        assert response.status_code == 401

    def test_list_builds_requires_auth(self, test_client: TestClient, db):
        repo = create_test_repo(db, owner_id=1)
        response = test_client.get(f"/api/v1/repositories/{repo.id}/builds")
        assert response.status_code == 401

    def test_get_build_not_found(self, test_client: TestClient, auth_headers: dict, db):
        repo = create_test_repo(db, owner_id=1)
        response = test_client.get(
            f"/api/v1/repositories/{repo.id}/builds/99999",
            headers=auth_headers,
        )
        assert response.status_code == 404
