import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from services.build_service import BuildService
from core.exception import NotFoundException
from tests.test_helpers import create_test_repo


class TestBuildService:

    async def test_create_build(self, async_db: AsyncSession, async_test_user):
        repo_id = uuid.uuid4()
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
            repo_id=uuid.uuid4(),
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
            repo_id=uuid.uuid4(),
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
            await BuildService.get_build(db=async_db, build_id=uuid.uuid4())

    async def test_list_builds_for_repository(self, async_db: AsyncSession, async_test_user):
        repo_id = uuid.uuid4()
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
        builds = await BuildService.get_builds_for_repository(db=async_db, repo_id=uuid.uuid4())
        assert builds == []

    async def test_list_builds_with_limit(self, async_db: AsyncSession, async_test_user):
        repo_id = uuid.uuid4()
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

    async def test_list_builds_filters_by_branch(self, async_db: AsyncSession, async_test_user):
        repo_id = uuid.uuid4()
        await BuildService.create_build(
            db=async_db, repo_id=repo_id, branch="main",
            commit_sha="abc1", triggered_by=async_test_user.id,
        )
        await BuildService.create_build(
            db=async_db, repo_id=repo_id, branch="feature/x",
            commit_sha="abc2", triggered_by=async_test_user.id,
        )
        await BuildService.create_build(
            db=async_db, repo_id=repo_id, branch="feature/x",
            commit_sha="abc3", triggered_by=async_test_user.id,
        )
        builds = await BuildService.get_builds_for_repository(
            db=async_db, repo_id=repo_id, branch="feature/x"
        )
        assert len(builds) == 2
        assert all(b.branch == "feature/x" for b in builds)

    async def test_list_builds_filters_by_status(self, async_db: AsyncSession, async_test_user):
        repo_id = uuid.uuid4()
        b1 = await BuildService.create_build(
            db=async_db, repo_id=repo_id, branch="main",
            commit_sha="abc1", triggered_by=async_test_user.id,
        )
        await BuildService.create_build(
            db=async_db, repo_id=repo_id, branch="main",
            commit_sha="abc2", triggered_by=async_test_user.id,
        )
        await BuildService.update_build_status(db=async_db, build_id=b1.id, status="success")
        builds = await BuildService.get_builds_for_repository(
            db=async_db, repo_id=repo_id, status="success"
        )
        assert len(builds) == 1
        assert builds[0].status == "success"

    async def test_update_build_status_to_running(self, async_db: AsyncSession, async_test_user):
        build = await BuildService.create_build(
            db=async_db,
            repo_id=uuid.uuid4(),
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
            repo_id=uuid.uuid4(),
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
            repo_id=uuid.uuid4(),
            branch="main",
            commit_sha="abc",
            triggered_by=async_test_user.id,
        )
        with pytest.raises(ValueError):
            await BuildService.update_build_status(
                db=async_db, build_id=build.id, status="invalid_status"
            )

    async def test_ensure_build_for_commit_creates_pending(self, async_db: AsyncSession, async_test_repo, async_test_user):
        """push 触发 build: 无历史 build 时应创建 pending build (F-046)"""
        build = await BuildService.ensure_build_for_commit(
            db=async_db,
            repo_id=async_test_repo.id,
            branch="main",
            commit_sha="abc123def456",
            triggered_by=async_test_user.id,
            commit_message="Push commit",
        )
        assert build is not None
        assert build.repo_id == async_test_repo.id
        assert build.branch == "main"
        assert build.commit_sha == "abc123def456"
        assert build.commit_message == "Push commit"
        assert build.status == "pending"
        assert build.triggered_by == async_test_user.id

    async def test_ensure_build_for_commit_dedup(self, async_db: AsyncSession, async_test_repo, async_test_user):
        """同 (repo, branch, commit) 重复触发应去重, 避免与 PR merge 重复建 build"""
        first = await BuildService.ensure_build_for_commit(
            db=async_db, repo_id=async_test_repo.id, branch="main",
            commit_sha="abc123", triggered_by=async_test_user.id,
        )
        assert first is not None
        second = await BuildService.ensure_build_for_commit(
            db=async_db, repo_id=async_test_repo.id, branch="main",
            commit_sha="abc123", triggered_by=async_test_user.id,
        )
        assert second is None
        builds = await BuildService.get_builds_for_repository(db=async_db, repo_id=async_test_repo.id)
        assert len(builds) == 1

    async def test_ensure_build_for_commit_allows_distinct_commits(self, async_db: AsyncSession, async_test_repo, async_test_user):
        """同分支不同 commit 应各自建 build"""
        await BuildService.ensure_build_for_commit(
            db=async_db, repo_id=async_test_repo.id, branch="main",
            commit_sha="abc1", triggered_by=async_test_user.id,
        )
        second = await BuildService.ensure_build_for_commit(
            db=async_db, repo_id=async_test_repo.id, branch="main",
            commit_sha="abc2", triggered_by=async_test_user.id,
        )
        assert second is not None
        builds = await BuildService.get_builds_for_repository(db=async_db, repo_id=async_test_repo.id)
        assert len(builds) == 2


class TestBuildController:

    def test_create_build_via_api(self, test_client: TestClient, auth_headers: dict, db):
        repo = create_test_repo(db)
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
        repo = create_test_repo(db)
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
        repo = create_test_repo(db)
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

    def test_list_builds_filter_by_branch_via_api(self, test_client: TestClient, auth_headers: dict, db):
        repo = create_test_repo(db)
        test_client.post(
            f"/api/v1/repositories/{repo.id}/builds",
            json={"branch": "main", "commit_sha": "abc1"},
            headers=auth_headers,
        )
        test_client.post(
            f"/api/v1/repositories/{repo.id}/builds",
            json={"branch": "feature/x", "commit_sha": "abc2"},
            headers=auth_headers,
        )
        response = test_client.get(
            f"/api/v1/repositories/{repo.id}/builds",
            params={"branch": "feature/x"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["branch"] == "feature/x"

    def test_update_build_status_via_api(self, test_client: TestClient, auth_headers: dict, db):
        repo = create_test_repo(db)
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
        repo = create_test_repo(db)
        response = test_client.post(
            f"/api/v1/repositories/{repo.id}/builds",
            json={"branch": "main", "commit_sha": "abc"},
        )
        assert response.status_code == 401

    def test_list_builds_requires_auth(self, test_client: TestClient, db):
        repo = create_test_repo(db)
        response = test_client.get(f"/api/v1/repositories/{repo.id}/builds")
        assert response.status_code == 401

    def test_get_build_not_found(self, test_client: TestClient, auth_headers: dict, db):
        repo = create_test_repo(db)
        response = test_client.get(
            f"/api/v1/repositories/{repo.id}/builds/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
        )
        assert response.status_code == 404

    def test_update_build_via_signature(self, test_client: TestClient, auth_headers: dict, db):
        """外部 CI runner 可用 X-Perseus-Signature (HMAC-SHA256) 回调, 无需用户 token"""
        from services.webhook_service import generate_signature
        repo = create_test_repo(db)
        repo.ci_secret = "test-ci-secret"
        db.commit()
        create_resp = test_client.post(
            f"/api/v1/repositories/{repo.id}/builds",
            json={"branch": "main", "commit_sha": "abc"},
            headers=auth_headers,
        )
        build_id = create_resp.json()["id"]
        body = '{"status": "running"}'
        response = test_client.patch(
            f"/api/v1/repositories/{repo.id}/builds/{build_id}",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Perseus-Signature": generate_signature(body, "test-ci-secret"),
            },
        )
        assert response.status_code == 200
        assert response.json()["status"] == "running"

    def test_update_build_signature_rejected_when_wrong(self, test_client: TestClient, auth_headers: dict, db):
        """签名错误时外部回调应被拒绝"""
        from services.webhook_service import generate_signature
        repo = create_test_repo(db)
        repo.ci_secret = "test-ci-secret"
        db.commit()
        create_resp = test_client.post(
            f"/api/v1/repositories/{repo.id}/builds",
            json={"branch": "main", "commit_sha": "abc"},
            headers=auth_headers,
        )
        build_id = create_resp.json()["id"]
        body = '{"status": "running"}'
        response = test_client.patch(
            f"/api/v1/repositories/{repo.id}/builds/{build_id}",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Perseus-Signature": generate_signature(body, "wrong-secret"),
            },
        )
        assert response.status_code == 403

    def test_update_build_signature_rejected_when_no_secret(self, test_client: TestClient, auth_headers: dict, db):
        """仓库未配置 ci_secret 时, 即使带签名头也应拒绝外部回调"""
        from services.webhook_service import generate_signature
        repo = create_test_repo(db)
        create_resp = test_client.post(
            f"/api/v1/repositories/{repo.id}/builds",
            json={"branch": "main", "commit_sha": "abc"},
            headers=auth_headers,
        )
        build_id = create_resp.json()["id"]
        body = '{"status": "running"}'
        response = test_client.patch(
            f"/api/v1/repositories/{repo.id}/builds/{build_id}",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Perseus-Signature": generate_signature(body, "test-ci-secret"),
            },
        )
        assert response.status_code == 403

    def test_update_build_requires_auth_or_signature(self, test_client: TestClient, auth_headers: dict, db):
        """无签名头也无用户 token 时回调应被拒绝"""
        repo = create_test_repo(db)
        create_resp = test_client.post(
            f"/api/v1/repositories/{repo.id}/builds",
            json={"branch": "main", "commit_sha": "abc"},
            headers=auth_headers,
        )
        build_id = create_resp.json()["id"]
        response = test_client.patch(
            f"/api/v1/repositories/{repo.id}/builds/{build_id}",
            json={"status": "running"},
        )
        assert response.status_code == 401
