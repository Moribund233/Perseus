"""协作会话级角色覆盖层测试 (collab_session_controller + 内部回调强制执行)

会话级覆盖层 (3.5 / M2 余项):
- 发起人 (仓库 owner/admin) 可对某会话成员改权限 (read/write) 或踢出;
- 覆盖优先于仓库角色与邀请 token: 踢出 → 403; 覆盖 read → 禁写; 覆盖 write → 放行;
- 清空覆盖 (scope=null) 后回落到仓库角色;
- 同时修复 "viewer"/"readonly" 角色不一致: readonly 成员应能加入会话。
"""
import uuid

import pytest

from controller.collab_internal_controller import (
    INTERNAL_SECRET_ENV,
    INTERNAL_SECRET_HEADER,
    make_doc_key,
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


def _bearer(user):
    return {"Authorization": f"Bearer {_token_for(user)}"}


def _add_member(db, repo, user, role):
    db.add(RepositoryMember(
        repository_id=repo.id, user_id=user.id, role=role, is_active=True
    ))
    db.commit()


def _other_user(db, username="repoowner", email="owner@example.com"):
    """独立的仓库 owner 用户 (避免 test_user 因 owner 身份恒有写权限)"""
    from models.user import User

    user = User(
        username=username,
        email=email,
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


class TestCollabSessionOverride:
    def _set_permission(self, client, host, repo, target, doc_key, scope):
        return client.post(
            f"/api/v1/repositories/{repo.id}/collab/sessions/permission",
            json={"doc_key": doc_key, "user_id": str(target.id), "scope": scope},
            headers=_bearer(host),
        )

    def _kick(self, client, host, repo, target, doc_key):
        return client.post(
            f"/api/v1/repositories/{repo.id}/collab/sessions/kick",
            json={"doc_key": doc_key, "user_id": str(target.id)},
            headers=_bearer(host),
        )

    def _auth(self, client, user, repo, branch="main", path="src/app.py"):
        return client.post(
            "/api/v1/collab/auth",
            json={"token": _token_for(user), "docKey": make_doc_key(str(repo.id), branch, path)},
            headers=_headers(),
        )

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

    # ---------- 端点权限门禁 ----------

    def test_permission_requires_host_role(self, test_client, db, test_user, internal_env):
        owner = _other_user(db)
        repo = create_test_repo(db, name="sess-perm-forbidden", owner_id=owner.id, is_public=False)
        _add_member(db, repo, test_user, "developer")
        key = make_doc_key(str(repo.id), "main", "src/app.py")
        resp = self._set_permission(test_client, test_user, repo, owner, key, "read")
        assert resp.status_code == 403

    def test_kick_requires_host_role(self, test_client, db, test_user, internal_env):
        owner = _other_user(db)
        repo = create_test_repo(db, name="sess-kick-forbidden", owner_id=owner.id, is_public=False)
        _add_member(db, repo, test_user, "developer")
        key = make_doc_key(str(repo.id), "main", "src/app.py")
        resp = self._kick(test_client, test_user, repo, owner, key)
        assert resp.status_code == 403

    def test_dockey_mismatch_rejected(self, test_client, db, test_user, internal_env):
        owner = test_user
        repo = create_test_repo(db, name="sess-dockey-mismatch", owner_id=owner.id)
        other_repo = create_test_repo(db, name="sess-dockey-other", owner_id=owner.id)
        foreign_key = make_doc_key(str(other_repo.id), "main", "a.py")
        resp = self._set_permission(test_client, owner, repo, owner, foreign_key, "read")
        assert resp.status_code == 400

    # ---------- 踢出即时生效 ----------

    def test_kick_then_auth_denied(self, test_client, db, test_user, internal_env):
        owner = _other_user(db)
        repo = create_test_repo(db, name="sess-kick-auth", owner_id=owner.id, is_public=False)
        _add_member(db, repo, test_user, "developer")
        key = make_doc_key(str(repo.id), "main", "src/app.py")

        assert self._auth(test_client, test_user, repo).status_code == 200
        assert self._kick(test_client, owner, repo, test_user, key).status_code == 200
        assert self._auth(test_client, test_user, repo).status_code == 403

    def test_kick_then_save_denied(self, test_client, db, test_user, internal_env, monkeypatch):
        owner = _other_user(db)
        repo = create_test_repo(db, name="sess-kick-save", owner_id=owner.id, is_public=False)
        _add_member(db, repo, test_user, "developer")
        key = make_doc_key(str(repo.id), "main", "src/app.py")
        monkeypatch.setattr(
            "services.repository_browser_service.commit_file",
            lambda *a, **k: {"commit_id": "abc1234"},
        )

        assert self._kick(test_client, owner, repo, test_user, key).status_code == 200
        assert self._save(test_client, test_user, repo).status_code == 403

    # ---------- 改权限即时生效 ----------

    def test_read_override_blocks_write_allows_read(self, test_client, db, test_user, internal_env):
        owner = _other_user(db)
        repo = create_test_repo(db, name="sess-read-override", owner_id=owner.id, is_public=False)
        _add_member(db, repo, test_user, "developer")
        key = make_doc_key(str(repo.id), "main", "src/app.py")

        assert self._set_permission(test_client, owner, repo, test_user, key, "read").status_code == 200

        auth = self._auth(test_client, test_user, repo)
        assert auth.status_code == 200
        assert auth.json()["can_write"] is False
        assert self._save(test_client, test_user, repo).status_code == 403

    def test_write_override_grants_write_to_non_member(self, test_client, db, test_user, internal_env):
        owner = _other_user(db)
        repo = create_test_repo(db, name="sess-write-override", owner_id=owner.id, is_public=False)
        key = make_doc_key(str(repo.id), "main", "src/app.py")

        # 非成员: 默认无权
        assert self._auth(test_client, test_user, repo).status_code == 403
        assert self._set_permission(test_client, owner, repo, test_user, key, "write").status_code == 200

        auth = self._auth(test_client, test_user, repo)
        assert auth.status_code == 200
        assert auth.json()["can_write"] is True

    def test_clear_override_restores_role(self, test_client, db, test_user, internal_env):
        owner = _other_user(db)
        repo = create_test_repo(db, name="sess-clear-override", owner_id=owner.id, is_public=False)
        _add_member(db, repo, test_user, "developer")
        key = make_doc_key(str(repo.id), "main", "src/app.py")

        assert self._set_permission(test_client, owner, repo, test_user, key, "read").status_code == 200
        assert self._auth(test_client, test_user, repo).json()["can_write"] is False

        assert self._set_permission(test_client, owner, repo, test_user, key, None).status_code == 200
        assert self._auth(test_client, test_user, repo).json()["can_write"] is True

    def test_kick_overrides_invite_write(self, test_client, db, test_user, internal_env):
        """被踢出后即使持 write 邀请 token 也被拒 (覆盖优先于邀请)"""
        from services.collab_invite_service import create_invite_token

        owner = _other_user(db)
        repo = create_test_repo(db, name="sess-kick-invite", owner_id=owner.id, is_public=False)
        key = make_doc_key(str(repo.id), "main", "src/app.py")
        invite = create_invite_token(key, "write", owner.id, owner.username)

        resp = test_client.post(
            "/api/v1/collab/auth",
            json={"token": _token_for(test_user), "docKey": key, "invite_token": invite["token"]},
            headers=_headers(),
        )
        assert resp.status_code == 200
        assert resp.json()["can_write"] is True

        assert self._kick(test_client, owner, repo, test_user, key).status_code == 200
        denied = test_client.post(
            "/api/v1/collab/auth",
            json={"token": _token_for(test_user), "docKey": key, "invite_token": invite["token"]},
            headers=_headers(),
        )
        assert denied.status_code == 403


class TestReadonlyRoleConsistency:
    def test_readonly_member_can_join(self, test_client, db, test_user, internal_env):
        owner = _other_user(db)
        repo = create_test_repo(db, name="sess-readonly-role", owner_id=owner.id, is_public=False)
        _add_member(db, repo, test_user, "readonly")

        resp = test_client.post(
            "/api/v1/collab/auth",
            json={
                "token": _token_for(test_user),
                "docKey": make_doc_key(str(repo.id), "main", "src/app.py"),
            },
            headers=_headers(),
        )
        assert resp.status_code == 200
        assert resp.json()["can_write"] is False
