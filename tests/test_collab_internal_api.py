"""协作编辑内部回调控制器测试 (collab_internal_controller)"""
import asyncio
import uuid
from unittest.mock import AsyncMock, Mock

import pytest

from controller.collab_internal_controller import (
    INTERNAL_SECRET_ENV,
    INTERNAL_SECRET_HEADER,
    make_doc_key,
    parse_doc_key,
)
from models.repository_member import RepositoryMember
from services.token_service import create_access_token
from tests.test_helpers import create_test_repo

SECRET = "test-internal-secret"


def _headers(secret=SECRET):
    return {INTERNAL_SECRET_HEADER: secret}


def _token_for(user):
    return create_access_token({
        "sub": str(user.id),
        "username": user.username,
        "is_admin": user.is_admin,
    })


def _add_member(db, repo, user, role):
    db.add(RepositoryMember(
        repository_id=repo.id, user_id=user.id, role=role, is_active=True
    ))
    db.commit()


def _other_user(db):
    """独立的仓库 owner 用户 (避免 test_user 因 owner 身份恒有写权限)"""
    from models.user import User

    user = User(
        username="repoowner",
        email="owner@example.com",
        password="hashed_owner_password",
        full_name="Repo Owner",
        is_active=True,
        is_admin=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def internal_env(monkeypatch):
    monkeypatch.setenv(INTERNAL_SECRET_ENV, SECRET)


# ==================== docKey 解析 ====================


class TestDocKey:
    def test_roundtrip(self):
        repo_id, branch, path = uuid.uuid4(), "main", "src/app.py"
        key = make_doc_key(str(repo_id), branch, path)
        assert parse_doc_key(key) == (repo_id, branch, path)

    def test_branch_with_slash(self):
        repo_id = uuid.uuid4()
        key = make_doc_key(str(repo_id), "feature/x", "a.txt")
        assert parse_doc_key(key)[1] == "feature/x"

    def test_path_with_colon(self):
        repo_id = uuid.uuid4()
        key = make_doc_key(str(repo_id), "main", "dir/a:b.txt")
        assert parse_doc_key(key)[2] == "dir/a:b.txt"

    def test_leading_slash_stripped(self):
        repo_id = uuid.uuid4()
        key = make_doc_key(str(repo_id), "main", "/a.txt")
        assert parse_doc_key(key)[2] == "a.txt"

    @pytest.mark.parametrize("bad", ["", "onlytwo:parts", "notauuid:main:a.txt", f"{uuid.uuid4()}::a.txt"])
    def test_invalid_rejected(self, bad):
        with pytest.raises(Exception):
            parse_doc_key(bad)


# ==================== 内部密钥门禁 ====================


class TestInternalSecret:
    def test_disabled_without_secret(self, test_client, monkeypatch):
        monkeypatch.delenv(INTERNAL_SECRET_ENV, raising=False)
        resp = test_client.post("/api/v1/collab/auth", json={"token": "x", "docKey": "a:b:c"})
        assert resp.status_code == 503

    def test_wrong_secret_rejected(self, test_client, internal_env):
        resp = test_client.post(
            "/api/v1/collab/auth",
            json={"token": "x", "docKey": "a:b:c"},
            headers=_headers("wrong"),
        )
        assert resp.status_code == 403

    def test_missing_secret_header(self, test_client, internal_env):
        resp = test_client.post("/api/v1/collab/auth", json={"token": "x", "docKey": "a:b:c"})
        assert resp.status_code == 403


# ==================== /collab/auth ====================


class TestCollabAuth:
    def _auth(self, client, user, repo, branch="main", path="src/app.py"):
        return client.post(
            "/api/v1/collab/auth",
            json={"token": _token_for(user), "docKey": make_doc_key(str(repo.id), branch, path)},
            headers=_headers(),
        )

    def test_developer_can_write(self, test_client, db, test_user, internal_env):
        repo = create_test_repo(db, name="auth-dev-repo", owner_id=_other_user(db).id, is_public=False)
        _add_member(db, repo, test_user, "developer")
        resp = self._auth(test_client, test_user, repo)
        assert resp.status_code == 200
        data = resp.json()
        assert data["can_write"] is True
        assert data["username"] == test_user.username
        assert data["branch"] == "main"

    def test_viewer_readonly(self, test_client, db, test_user, internal_env):
        repo = create_test_repo(db, name="auth-viewer-repo", owner_id=_other_user(db).id)
        _add_member(db, repo, test_user, "viewer")
        resp = self._auth(test_client, test_user, repo)
        assert resp.status_code == 200
        assert resp.json()["can_write"] is False

    def test_non_member_private_repo_403(self, test_client, db, test_user, internal_env):
        repo = create_test_repo(db, name="auth-private-repo", owner_id=_other_user(db).id, is_public=False)
        resp = self._auth(test_client, test_user, repo)
        assert resp.status_code == 403

    def test_owner_can_access(self, test_client, db, test_user, internal_env):
        repo = create_test_repo(db, name="auth-owner-repo", owner_id=test_user.id)
        resp = self._auth(test_client, test_user, repo)
        assert resp.status_code == 200
        assert resp.json()["can_write"] is True

    def test_invalid_token_401(self, test_client, db, test_user, internal_env):
        repo = create_test_repo(db, name="auth-token-repo", owner_id=test_user.id)
        resp = test_client.post(
            "/api/v1/collab/auth",
            json={"token": "not-a-valid-token", "docKey": make_doc_key(str(repo.id), "main", "a.py")},
            headers=_headers(),
        )
        assert resp.status_code == 401

    def test_repo_not_found_404(self, test_client, db, test_user, internal_env):
        key = make_doc_key(str(uuid.uuid4()), "main", "a.py")
        resp = test_client.post(
            "/api/v1/collab/auth", json={"token": _token_for(test_user), "docKey": key},
            headers=_headers(),
        )
        assert resp.status_code == 404

    def test_bad_dockey_400(self, test_client, db, test_user, internal_env):
        resp = test_client.post(
            "/api/v1/collab/auth", json={"token": _token_for(test_user), "docKey": "bad"},
            headers=_headers(),
        )
        assert resp.status_code == 400


# ==================== /collab/doc ====================


class TestCollabDoc:
    def test_load_success(self, test_client, db, test_user, internal_env, monkeypatch):
        repo = create_test_repo(db, name="doc-repo", owner_id=test_user.id)
        mock = AsyncMock(return_value={"is_binary": False, "content": "hello world"})
        monkeypatch.setattr("services.repository_browser_service.get_blob_content", mock)
        resp = test_client.get(
            "/api/v1/collab/doc",
            params={"docKey": make_doc_key(str(repo.id), "main", "src/app.py")},
            headers=_headers(),
        )
        assert resp.status_code == 200
        assert resp.json()["content"] == "hello world"
        args, kwargs = mock.call_args
        assert kwargs.get("ref") == "main" or args[1:3] == ("main", "src/app.py")

    def test_binary_file_415(self, test_client, db, test_user, internal_env, monkeypatch):
        repo = create_test_repo(db, name="doc-bin-repo", owner_id=test_user.id)
        monkeypatch.setattr(
            "services.repository_browser_service.get_blob_content",
            AsyncMock(return_value={"is_binary": True, "content": ""}),
        )
        resp = test_client.get(
            "/api/v1/collab/doc",
            params={"docKey": make_doc_key(str(repo.id), "main", "img.png")},
            headers=_headers(),
        )
        assert resp.status_code == 415

    def test_missing_file_404(self, test_client, db, test_user, internal_env, monkeypatch):
        from core.exception import NotFoundException

        repo = create_test_repo(db, name="doc-missing-repo", owner_id=test_user.id)
        monkeypatch.setattr(
            "services.repository_browser_service.get_blob_content",
            AsyncMock(side_effect=NotFoundException(detail="file not found")),
        )
        resp = test_client.get(
            "/api/v1/collab/doc",
            params={"docKey": make_doc_key(str(repo.id), "main", "gone.py")},
            headers=_headers(),
        )
        assert resp.status_code == 404


# ==================== /collab/save ====================


class TestCollabSave:
    def _save(self, client, user, repo, content="new content"):
        return client.post(
            "/api/v1/collab/save",
            json={
                "token": _token_for(user),
                "docKey": make_doc_key(str(repo.id), "main", "src/app.py"),
                "content": content,
                "message": "collab save test",
            },
            headers=_headers(),
        )

    def test_save_success(self, test_client, db, test_user, internal_env, monkeypatch):
        repo = create_test_repo(db, name="save-repo", owner_id=test_user.id)
        mock = AsyncMock(return_value={"commit_id": "abc1234"})
        monkeypatch.setattr("services.repository_browser_service.commit_file", mock)
        resp = self._save(test_client, test_user, repo)
        assert resp.status_code == 200
        data = resp.json()
        assert data["commit_id"] == "abc1234"
        assert data["saved_by"] == test_user.username
        # 作者信息以 full_name/username + email 传入
        args, _ = mock.call_args
        assert args[4] == (test_user.full_name or test_user.username)
        assert args[5] == test_user.email

    def test_save_viewer_403(self, test_client, db, test_user, internal_env):
        repo = create_test_repo(db, name="save-viewer-repo", owner_id=_other_user(db).id)
        _add_member(db, repo, test_user, "viewer")
        resp = self._save(test_client, test_user, repo)
        assert resp.status_code == 403

    def test_save_content_too_large_413(self, test_client, db, test_user, internal_env):
        repo = create_test_repo(db, name="save-big-repo", owner_id=test_user.id)
        resp = self._save(test_client, test_user, repo, content="x" * (2_000_001))
        assert resp.status_code == 413

    def test_save_triggers_incremental_index_update(self, test_client, db, test_user, internal_env, monkeypatch):
        """collab save 后应增量更新搜索索引 (单文件, 经 to_thread 离开事件循环)"""
        repo = create_test_repo(db, name="save-index-repo", owner_id=test_user.id)
        monkeypatch.setattr(
            "services.repository_browser_service.commit_file",
            AsyncMock(return_value={"commit_id": "abc123", "branch": "main", "path": "src/app.py"}),
        )

        from services.search_service import SearchService

        fake_service = Mock()
        fake_service.update_files = Mock(return_value=None)
        monkeypatch.setattr("controller.collab_internal_controller.SearchService", fake_service)

        to_thread_targets = []

        async def fake_to_thread(fn, *args, **kwargs):
            to_thread_targets.append(fn)
            return fn(*args, **kwargs)

        monkeypatch.setattr(asyncio, "to_thread", fake_to_thread)

        resp = self._save(test_client, test_user, repo, content="def collab_indexed():\n    pass\n")
        assert resp.status_code == 200

        assert fake_service.update_files.called, "collab save 应触发索引增量更新"
        args = fake_service.update_files.call_args[0]
        assert args[1] == ["src/app.py"], "索引更新应只覆盖本次保存的单个文件"
        assert fake_service.update_files in to_thread_targets, \
            "索引更新应经 to_thread 调用, 避免阻塞事件循环"
